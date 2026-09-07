#!/usr/bin/env python
"""measure_floor — the provider's repeat variance, per frame index.

    <venv-python> tools/measure_floor.py --runs=A0r1,A0r2,A0r3 [--early=0-4] [--late=29-32]

A0. Three identical submissions, same seed, same payload — so every difference between
them is the provider, not us.

**CORRECTED 2026-08-10 (E04). The rationale below was measuring the codec, not the
provider.** It read, and this is kept rather than deleted because the correction is more
useful than the original:

    "**The floor is not a scalar.** The first pass through this data showed the early
    frames of a clip agreeing almost exactly while the late frames diverged badly, which
    means a single number would understate the floor at the end of a clip and overstate
    it at the start."

**That early/late shape was H.264.** E02's A0 re-measured the same three submissions on
the lossless VAEDecode tap and found **33 of 33 frames identical in all 3 pairs — the
fixed-seed floor is exactly zero, at every frame index, early and late alike.** There is
no shape to report because there is no divergence to have a shape. The observed early/late
gradient was the encoder's, and it disappeared when the encoder left the path.

**Why the per-index reporting stays anyway.** It is now the instrument that *proves* the
floor is flat rather than an instrument that assumes it is not: a scalar mean of zero and
a per-index row of zeros look identical on a good run and differ completely on a bad one,
and this tool must be able to catch the day a provider stops being deterministic. The
EARLY/LATE rows stay for the same reason — they are how a returning gradient would
announce itself. **What must not be inherited is the claim that the gradient is there.**

⚠ **This is the fixed-seed floor and nothing else.** Zero here means *re-running one
submission* costs nothing. It says nothing about the spread across *different seeds*,
which is a separate quantity measured by E04, and nothing about any statistic other than
the pixel one — the timing correlation has its own floor and its own instrument
(`measure_tracking.py`).

Read on the **lossless** frames only (`lossless/`, the VAEDecode tap). The earlier floor
came through H.264 on both sides; on this rig the codec alone moves a single generation's
frames by a per-frame max of 43-64, which is the same order as the whole floor being
measured. A floor measured through that is a moving denominator.

Every NUMBER here is a diagnostic. Nothing raises on a difference, nothing grades an arm —
this is the denominator every later number is read against.

**What does raise, and why it is not a verdict.** Two ways this tool produced a perfect
zero floor from a comparison it never made, both measured 2026-09-03:

* `pair_stats` paired frames with `zip(A, B)`, which truncates to the shorter run, and `n`
  came from the first run alone. r1 of 5 frames against r2 of 9 (whose last four differ
  wildly) printed `2 runs · 5 frames · 1 pairs`, `frames identical: 5/5`, `pair
  bit-identical overall: YES`, and wrote the same into floor.json. Four frames were never
  opened. The day a provider returns a short or long re-run is the day this instrument
  exists for, and that is the day it would report a flawless floor.
* `itertools.combinations` ran over the raw `--runs` list with no distinctness check, so
  `--runs=r2,r2` compared one decode with itself and printed `1 of 1 pairs are
  bit-identical`.

So the runs must be distinct and at least two (`check_runs`, before any stack is loaded),
and every run must carry the same frame count (`common_frame_count`, before any pair is
compared). Neither is a judgement about the pixels; both are refusals to describe a
population nobody measured.

**And a third, 2026-09-03: the EARLY and LATE windows were literals.** `--early` and
`--late` defaulted to `0-4` and `29-32` -- E02's 33-frame clip typed into the tool, a global
constant governing a local feature. Two directions, both measured. Two 31-frame runs printed
`EARLY (frames 0-4) vs LATE (frames 29-32)` with the late row computed over TWO frames and
`"late_window": [29,30,31,32]` recorded beside it: the window named four frames and the
number under it was measured over two, in the instrument that is the denominator every later
number is read against. Two 17-frame runs (a generator-legal 4n+1 bucket) died at
`min() iterable argument is empty` after every PNG had been loaded, writing no floor.json.

`bound_windows` derives both ends from the run's OWN frame count (`WINDOW_FRACTION` of it at
each end) when nothing is asked for, and refuses an explicit window naming a frame the run
does not carry -- naming the request, `n`, and the out-of-range indices. `early_window` and
`late_window` in the record are the REALISED lists, and `window_source` says of each whether
it was derived or requested.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import itertools
import json
import os
import statistics as st
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encode_control import runtime_provenance  # noqa: E402

from armature_core import shotspec  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402


#: How much of a run each end-window covers, as a fraction of that run's OWN frame count.
#: E02's defaults were the literals `0-4` and `29-32` -- five frames at one end of a
#: 33-frame clip and four at the other. 5/33 keeps that size where it came from and makes
#: it mean the same thing on a run of any length.
WINDOW_FRACTION = 5.0 / 33.0



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

class FloorError(ArmatureError):
    """The floor could not be measured over the population that was asked for."""


def gate_floor_overwrite(out, overwrite):
    """Refuse a silent replace of an existing floor record (F-a28128a4).

    Same contract as wave-28's builders/instruments overwrite family: flag ``--overwrite``,
    clause ``output_already_exists``, success keys ``out_dir_pre_existed`` / ``overwrote``.
    No second helper home in armature_core (wave-28 seed 1) — spelled here, the one writer.
    """
    if not os.path.isfile(out):
        return False, None
    prior = None
    try:
        with open(out, encoding="utf-8") as fh:
            prior = json.load(fh)
    except (OSError, json.JSONDecodeError):
        prior = None
    if not overwrite:
        prior_runs = prior.get("runs") if isinstance(prior, dict) else None
        prior_n = prior.get("n_frames") if isinstance(prior, dict) else None
        raise FloorError(
            f"{os.path.abspath(out)}: already on disk from an earlier run "
            f"(runs={prior_runs!r}, n_frames={prior_n}); this run would replace what is "
            f"there. Pass --overwrite to replace it, or point --out at a path of its own",
            {"clause": "output_already_exists", "out": os.path.abspath(out),
             "already_present": [os.path.basename(out)],
             "prior_runs": prior_runs, "prior_n_frames": prior_n,
             "prior_mtime": os.path.getmtime(out), "flag": "--overwrite"},
        )
    return True, prior if isinstance(prior, dict) else None


def check_runs(runs):
    """Distinct, and at least two of them. Raises before any stack is loaded."""
    seen, repeated = set(), []
    for r in runs:
        if r in seen and r not in repeated:
            repeated.append(r)
        seen.add(r)
    if repeated:
        raise FloorError(
            f"--runs repeats {', '.join(repeated)}; a pair of a run with itself is "
            f"bit-identical by construction and would be published as a zero floor",
            {"runs": list(runs), "repeated": repeated},
        )
    if len(runs) < 2:
        raise FloorError(
            f"repeat variance needs at least two distinct runs; {len(runs)} given",
            {"runs": list(runs)},
        )
    return list(runs)


def common_frame_count(stacks):
    """The frame count every run carries, or raise naming the runs that disagree."""
    per_run = {r: len(s) for r, s in stacks.items()}
    counts = sorted(set(per_run.values()))
    if len(counts) != 1:
        modal = max(counts, key=lambda c: list(per_run.values()).count(c))
        odd = sorted(r for r, c in per_run.items() if c != modal)
        raise FloorError(
            f"the runs do not carry the same number of frames "
            f"({', '.join(f'{r}={c}' for r, c in sorted(per_run.items()))}); "
            f"{', '.join(odd)} disagree with {modal}. Pairing them would truncate to the "
            f"shorter run and report the floor over a population nobody described",
            {"frames_per_run": per_run, "counts": counts, "modal": modal,
             "runs_disagreeing": odd},
        )
    if counts[0] == 0:
        raise FloorError(
            "every run holds zero frames; a floor over no pixels is not a measurement",
            {"frames_per_run": per_run},
        )
    return counts[0]


def common_frame_names(names_per_run):
    """ANDON — every run names the SAME frames, or raise naming the disagreement.

    The names were computed and thrown away. `frame_population` derives each run's
    NUMBERED names, `_stack` used them only to open files, and `common_frame_count`
    compared COUNTS across runs and nothing else — so no clause anywhere compared run A's
    names with run B's, on the instrument whose docstring calls itself "the denominator
    every later number is read against".

    Measured 2026-09-04: `r1` numbered 00000..00004 against `r2` numbered 00001..00005,
    each frame's pixels a function of its own frame NUMBER (a deterministic provider),
    exit 0, "frames identical: 0/5", `max|d| 20` on every index, and floor.json keying
    `pairs[].frame` by POSITION. A deterministic provider read as noisy, and every later
    arm would be graded against that floor.

    This is the refusal `compare_runs.compare_channel` already raises for the same reason
    (`names_a != names_b`) and `measure_lift.gate_pairing` implements as a gate.
    """
    runs = list(names_per_run)
    base = runs[0]
    truth = list(names_per_run[base])
    odd = [r for r in runs[1:] if list(names_per_run[r]) != truth]

    def unique_to(r):
        others = set()
        for o in runs:
            if o != r:
                others |= set(names_per_run[o])
        return sorted(set(names_per_run[r]) - others)[:16]

    ev = {"gate": "NAMES", "runs": runs, "against": base,
          "frames_per_run": {r: list(v)[:32] for r, v in names_per_run.items()},
          "runs_disagreeing": odd,
          "only_in": {r: unique_to(r) for r in runs}}
    if odd:
        raise FloorError(
            f"the runs do not name the same frames ({', '.join(odd)} disagree with "
            f"{base}); the pairs would be built by POSITION, so a deterministic provider "
            f"reads as noisy and the floor every later arm is graded against is measured "
            f"between frames that were never the same moment", ev)
    ev["verdict"] = f"all {len(runs)} runs name the same {len(truth)} frames"
    return truth, ev


def frame_population(d, expect=None):
    """The NUMBERED frames of one run's channel directory, in index order, or raise.

    The twin of `encode_control.frame_population` and `invert_frames.frame_population`,
    carrying THEIR refusal rather than a third implementation of it, and it exists for
    the same measured reason: `render_pose_sticks` writes a `strip_every{N}.png` contact
    sheet into the very directory it just filled with `NNNNN.png` frames.

    **Why a refusal and not the filter its two diagnostic siblings use.**
    `gate_b_frames.frame_paths` and `measure_clip.frame_paths` drop a stray silently,
    which is right for a diagnostic that describes one run. This tool publishes the
    DENOMINATOR every later difference is read against, so a directory holding a file
    this tool cannot name is a directory whose contents nobody has stated. Measured
    2026-09-04 on two synthetic runs of 8 numbered frames plus one `strip_every8.png`
    each: the bare `*.png` listing returned 9, `common_frame_count` returned 9, and the
    derived LATE window was `[8]` — the contact sheet. Byte-identical across runs, it
    also contributed an `identical: True` pair and lowered the published floor.

    The `.png` match is case-insensitive, agreeing with `fetch_run.verify_downloads`
    (which sweeps `00099.PNG` as a downloaded frame) and with the two upload-feeding
    siblings: a population that cannot see a file the fetcher counted would report the
    floor over fewer frames than were downloaded.

    `expect` pins the population to `shotspec.frame_names`, the spec's own names, rather
    than to a length any N files would satisfy.
    """
    if not os.path.isdir(d):
        raise FloorError(f"{d} is not a directory of frames", {"channel_dir": d})
    pngs = sorted(n for n in os.listdir(d) if n.lower().endswith(".png"))
    numbered = [n for n in pngs if os.path.splitext(n)[0].isdigit()]
    unexpected = [n for n in pngs if n not in set(numbered)]
    names = sorted(numbered, key=lambda n: int(os.path.splitext(n)[0]))
    if unexpected:
        raise FloorError(
            f"{d} holds {len(unexpected)} PNG(s) that are not numbered frames "
            f"({', '.join(unexpected[:8])}); a stray sorts into the population and "
            f"becomes a frame of the run the noise floor is measured over",
            {"channel_dir": d, "unexpected": unexpected, "frames": names},
        )
    if not names:
        raise FloorError(
            f"no NNNNN.png frames in {d}; a floor over no frames is not a measurement",
            {"channel_dir": d, "png_files": pngs},
        )
    if expect is not None:
        want = shotspec.frame_names(expect, "png")
        if names != want:
            raise FloorError(
                f"{d} holds {len(names)} frame(s) and the spec names {len(want)}; the "
                f"floor would be published over a population the spec does not describe",
                {"channel_dir": d, "found": names, "expected": want,
                 "missing": [n for n in want if n not in set(names)],
                 "unexpected": [n for n in names if n not in set(want)]},
            )
    return names


def _stack(run_dir, sub="lossless", expect=None):
    """`(names, frames)` for one run.

    It used to return the arrays alone. The names were derived one line above and dropped
    on the floor, which is how two runs naming different frames were paired by POSITION
    with nothing in the record saying so — see `common_frame_names`.
    """
    d = os.path.join(run_dir, sub)
    names = frame_population(d, expect=expect)
    return names, [np.array(Image.open(os.path.join(d, n)).convert("RGB")).astype(np.int16)
                   for n in names]


def _span(text, name):
    """`"a-b"` inclusive, or raise naming the flag and the shape it wanted.

    Every other way of getting a window wrong in this file raises `FloorError` with an
    evidence dict naming `requested`, `n_frames` and `out_of_range`. A malformed span
    escaped all of it: measured 2026-09-04, `bound_windows(33, '5', None)` — the
    plausible operator typo, one number instead of a span — died on
    `ValueError: invalid literal for int() with base 10: ''`, naming neither the flag
    nor the expected shape, and `'abc-def'` did the same.
    """
    parts = str(text).split("-")
    ev = {"window": name, "requested_text": text, "expected_shape": "a-b"}
    if len(parts) != 2 or not all(p.strip().lstrip("+").isdigit() for p in parts):
        raise FloorError(
            f"--{name}={text!r} is not a window; it must be written a-b, two frame "
            f"indices inclusive (argparse eats leading minus signs, so pass "
            f"--{name}=0-4)", ev)
    a, b = int(parts[0]), int(parts[1])
    if b < a:
        raise FloorError(
            f"--{name}={text!r} ends before it begins; a window of no frames would be "
            f"reported under a heading naming two", dict(ev, first=a, last=b))
    return list(range(a, b + 1))


def derive_window(n, fraction=WINDOW_FRACTION):
    """The EARLY and LATE index lists for a run of `n` frames, from `n` alone.

    A fraction of the structure's own size rather than a frame-count constant: the same
    fraction means the same thing on a 17-frame bucket and on a 121-frame one, where
    `0-4` / `29-32` meant one experiment's clip and nothing else. Both ends are the SAME
    size, which the literals were not (five frames early against four late) -- two windows
    of different sizes are not comparable rows.
    """
    k = max(1, min(n, int(round(n * fraction))))
    return list(range(k)), list(range(n - k, n))


def bound_windows(n, early_text=None, late_text=None, fraction=WINDOW_FRACTION):
    """The realised EARLY and LATE windows for a run of `n` frames, or raise naming why.

    Returns `(early, late, source)`, where `source` says of each window whether it was
    derived from `n` or requested. Raises before any pair is read: a window naming frames
    the run does not carry produces a row of numbers under a heading that describes a
    different population, which is exactly what was measured on the 31-frame pair.
    """
    derived_early, derived_late = derive_window(n, fraction)
    windows, source = {}, {}
    for name, text, derived in (("early", early_text, derived_early),
                                ("late", late_text, derived_late)):
        if text is None:
            windows[name] = derived
            source[name] = (f"derived from this run's own {n} frames at "
                            f"{fraction:.1%} of it per end")
            continue
        idx = _span(text, name)
        bad = [i for i in idx if i < 0 or i >= n]
        if not idx or bad:
            raise FloorError(
                f"--{name}={text} names frame(s) {bad} on a run of {n}; the row under "
                f"that heading would be computed over "
                f"{len([i for i in idx if 0 <= i < n])} of the {len(idx)} frames the "
                f"record names beside it",
                {"window": name, "requested_text": text, "requested": idx,
                 "n_frames": n, "out_of_range": bad,
                 "realised": [i for i in idx if 0 <= i < n]})
        windows[name] = idx
        source[name] = f"requested as --{name}={text}"
    both = sorted(set(windows["early"]) & set(windows["late"]))
    if both:
        raise FloorError(
            f"the early and late windows overlap on frame(s) {both} of a {n}-frame run; "
            f"EARLY and LATE would print two rows of the same numbers under two headings "
            f"that claim to be the two ends of the clip",
            {"n_frames": n, "early": windows["early"], "late": windows["late"],
             "overlap": both, "window_source": source})
    # ---- ANDON on the direction the arithmetic does NOT bound. `derive_window` computes
    #      `k` once and uses it at both ends, so on the derived path the equality cannot
    #      be violated and the invariant its docstring states was unenforced exactly where
    #      the defect arrived: measured 2026-09-04, `bound_windows(33, '0-4', '29-32')`
    #      returned an early of five frames and a late of four with no refusal — the
    #      literals this module's docstring records as the defect, accepted verbatim from
    #      the command line.
    if len(windows["early"]) != len(windows["late"]):
        raise FloorError(
            f"the EARLY window covers {len(windows['early'])} frame(s) and the LATE "
            f"window {len(windows['late'])} on a {n}-frame run; two windows of different "
            f"sizes are not comparable rows, and the record would name them as the two "
            f"ends of one clip",
            {"n_frames": n, "early": windows["early"], "late": windows["late"],
             "n_early": len(windows["early"]), "n_late": len(windows["late"]),
             "window_source": source})
    return windows["early"], windows["late"], source


def pair_stats(A, B, big=8, names=None):
    """Per-frame stats for one pair of runs.

    The length check is here rather than only at the call site because `zip` is here:
    a truncating pair is produced by this function, so this is where it is refused.

    `names` keys each row by the FILE's own frame number rather than by its position in
    the listing — a position depends on what else is in the directory and on where the
    run's numbering starts, and is not a thing a later reader can look up.

    **A pixel is a position, not a sample.** `pct_gt` was `100 * (d > big).mean()` over an
    (H, W, C) array and every heading above it read `px >{big}`. Measured 2026-09-04 on a
    pair differing in exactly one of three channels on every pixel: the tool printed
    33.333% where 100% of the pixels differ. Both quantities are now reported under their
    own names with `samples_per_pixel` beside them, which is the correction
    `compare_runs` already carries.
    """
    if len(A) != len(B):
        raise FloorError(
            f"a pair of {len(A)} and {len(B)} frames cannot be compared frame for "
            f"frame; zip would truncate to {min(len(A), len(B))} and the frames past "
            f"that would never be opened",
            {"n_a": len(A), "n_b": len(B)},
        )
    out = []
    for i, (a, b) in enumerate(zip(A, B)):
        d = np.abs(a - b)
        spp = int(d.shape[2]) if d.ndim == 3 else 1
        over = d > big
        px_over = over.any(axis=-1) if d.ndim == 3 else over
        number = i
        if names is not None:
            stem = os.path.splitext(str(names[i]))[0]
            number = int(stem) if stem.isdigit() else i
        out.append({
            "frame": number,
            "file": str(names[i]) if names is not None else None,
            "max": int(d.max()),
            "mean": float(d.mean()),
            "samples_per_pixel": spp,
            "pct_px_gt": float(100.0 * px_over.mean()),
            "pct_samples_gt": float(100.0 * over.mean()),
            "identical": bool(d.max() == 0),
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the provider's repeat variance per frame index — the noise floor "
                    "every one-run gap has to be read against",
        epilog=HALT_EPILOG)
    ap.add_argument("--runs", required=True,
                    help="comma-separated run names to compare; at least two DISTINCT "
                         "names, since a floor needs repeats of the same request")
    ap.add_argument("--root", default="outputs/E02/runs",
                    help="cwd-relative directory the run names are resolved under "
                         "(default: outputs/E02/runs)")
    ap.add_argument("--early", default=None,
                    help="a-b, inclusive. Omitted, the window is derived from the run's "
                         "own frame count (argparse eats leading minus signs, so pass "
                         "--early=0-4)")
    ap.add_argument("--late", default=None,
                    help="a-b, inclusive. Omitted, the window is derived from the run's "
                         "own frame count")
    ap.add_argument("--big", type=int, default=8,
                    help="the per-pixel absolute difference at or above which a pixel is "
                         "counted BIG (default 8, on 0-255 levels)")
    ap.add_argument("--expect", type=int, default=None,
                    help="the frame count the spec declares; every run's numbered frames "
                         "must be exactly shotspec.frame_names(expect, 'png')")
    ap.add_argument("--out", default="outputs/E02/floor.json",
                    help="cwd-relative path the floor record is written to "
                         "(default: outputs/E02/floor.json). An existing file is refused "
                         "unless --overwrite is passed")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace an existing --out floor record. WITHOUT it the run "
                         "REFUSES rather than overwriting, by name "
                         "(clause output_already_exists), before any write")
    a = ap.parse_args(argv)

    # ---- ANDON, before a single PNG is opened: distinct runs, at least two of them.
    runs = check_runs([r for r in a.runs.split(",") if r])
    # ---- ANDON, before a single pair is compared: each run's population is its
    #      NUMBERED frames and nothing else. A contact strip beside them is refused.
    loaded = {r: _stack(os.path.join(a.root, r), expect=a.expect) for r in runs}
    names_per_run = {r: v[0] for r, v in loaded.items()}
    stacks = {r: v[1] for r, v in loaded.items()}
    # ---- ANDON, before a single pair is compared: one verified frame count, not run[0]'s.
    n = common_frame_count(stacks)
    # ---- ANDON, before a single pair is compared: the runs name the SAME frames. The
    #      names were derived per run and DISCARDED; nothing compared them across runs,
    #      so two runs of equal length numbered 0..4 and 1..5 were paired by position.
    frame_names, gate_names = common_frame_names(names_per_run)
    # ---- ANDON, before a single pair is compared: the windows are bounded by THIS run.
    early, late, window_source = bound_windows(n, a.early, a.late)

    pairs = {}
    for x, y in itertools.combinations(runs, 2):
        pairs[f"{x}|{y}"] = pair_stats(stacks[x], stacks[y], a.big, names=frame_names)

    print(f"A0 — repeat variance on LOSSLESS frames · {len(runs)} runs · {n} frames · "
          f"{len(pairs)} pairs")
    print()
    print("P1 clause A — bit-identical pairs")
    for k, ps in pairs.items():
        ident = sum(1 for p in ps if p["identical"])
        print(f"  {k:<14} frames identical: {ident:>2}/{n}   "
              f"pair bit-identical overall: {'YES' if ident == n else 'NO'}")
    nbit = sum(1 for ps in pairs.values() if all(p['identical'] for p in ps))
    print(f"  => {nbit} of {len(pairs)} pairs are bit-identical")
    print()

    # F-7586ba2d: band the table so an ordinary terminal keeps digit columns aligned.
    print("THE SHAPE — per-frame max |delta|, every frame, first pair listed per column")
    SHAPE_BAND = 16
    for start in range(0, n, SHAPE_BAND):
        end = min(n, start + SHAPE_BAND)
        print("  frame :  " + " ".join(f"{i:>3}" for i in range(start, end)))
        for k, ps in pairs.items():
            print(f"  {k[:12]:<12}: "
                  + " ".join(f"{p['max']:>3}" for p in ps[start:end]))
        if end < n:
            print()
    print()

    def window(ps, idx):
        # No `if i < len(ps)` filter: every index here was bounded against n by
        # `bound_windows` before a pair was compared. That filter is what let a window
        # report over fewer frames than the heading above it named.
        #
        # `idx` indexes the POSITION in this pair's rows, which `bound_windows` bounded
        # against n; the row it lands on names its own frame number.
        return ([ps[i]["max"] for i in idx],
                [ps[i]["pct_px_gt"] for i in idx],
                [ps[i]["pct_samples_gt"] for i in idx])

    def window_numbers(idx):
        """The FILE numbers at those positions. `--early`/`--late` name POSITIONS in the
        run (bounded against `n` by `bound_windows`); the heading names the frames those
        positions actually are, which on a run numbered from anything but 0 is not the
        same list."""
        out = []
        for i in idx:
            stem = os.path.splitext(str(frame_names[i]))[0]
            out.append(int(stem) if stem.isdigit() else i)
        return out

    def heading(name, idx):
        num = window_numbers(idx)
        return f"{name} (frames {num[0]}-{num[-1]}, {len(idx)} of {n})"

    print(f"{heading('EARLY', early)} vs {heading('LATE', late)} - reported separately, "
          f"always")
    print(f"  windows: early {window_source['early']}; late {window_source['late']}")
    rows = []
    for k, ps in pairs.items():
        em, egp, egs = window(ps, early)
        lm, lgp, lgs = window(ps, late)
        rows.append((k, em, egp, egs, lm, lgp, lgs))
        print(f"  {k}")
        print(f"    early  max|d|: min {min(em):>3} median {int(st.median(em)):>3} max {max(em):>3}"
              f"   |  px >{a.big}: {st.mean(egp):.3f}%"
              f"   |  samples >{a.big}: {st.mean(egs):.3f}%")
        print(f"    late   max|d|: min {min(lm):>3} median {int(st.median(lm)):>3} max {max(lm):>3}"
              f"   |  px >{a.big}: {st.mean(lgp):.3f}%"
              f"   |  samples >{a.big}: {st.mean(lgs):.3f}%")

    allmax = [p["max"] for ps in pairs.values() for p in ps]
    # Two quantities, two names. `px` and `samples` differ by the channel count, and the
    # single number this file used to print was the sample fraction under a `px` heading.
    allpct_px = [p["pct_px_gt"] for ps in pairs.values() for p in ps]
    allpct_samples = [p["pct_samples_gt"] for ps in pairs.values() for p in ps]
    spp = sorted({p["samples_per_pixel"] for ps in pairs.values() for p in ps})
    ndiff = sum(1 for ps in pairs.values() for p in ps if not p["identical"])
    print()
    print("WHOLE-CLIP SCALAR — recorded only so it can be compared with the codec-contaminated")
    print("                    first pass. It is NOT the floor; the per-index shape above is.")
    print(f"  frames differing : {ndiff} of {n * len(pairs)}")
    print(f"  per-frame max|d| : min {min(allmax)} · median {int(st.median(allmax))} · max {max(allmax)}")
    print(f"  px differing >{a.big}  : {st.mean(allpct_px):.3f}%  "
          f"(a pixel is a position: counted once however many channels differ)")
    print(f"  samples >{a.big}       : {st.mean(allpct_samples):.3f}%  "
          f"(samples_per_pixel {spp})")

    payload = {
        "runs": runs, "n_frames": n, "big_threshold": a.big, "expect": a.expect,
        "frames_per_run": {r: len(s) for r, s in stacks.items()},
        # The REALISED names, per run and shared. They were derived and discarded, which
        # is how two runs naming different frames were paired by position.
        "frame_names": frame_names,
        "frame_names_per_run": names_per_run,
        "gate_NAMES": gate_names,
        # The REALISED index lists, which `bound_windows` has already proved are frames
        # this run carries -- never the requested text.
        "early_window": early, "late_window": late, "window_source": window_source,
        # The positions above, resolved to the frame numbers on the files — the heading
        # printed positions under the word "frames".
        "early_window_frames": window_numbers(early),
        "late_window_frames": window_numbers(late),
        "window_fraction": WINDOW_FRACTION,
        "pairs": pairs,
        "whole_clip": {
            "frames_differing": ndiff, "of": n * len(pairs),
            "max_min": min(allmax), "max_median": st.median(allmax), "max_max": max(allmax),
            "samples_per_pixel": spp,
            "pct_px_gt_big_mean": st.mean(allpct_px),
            "pct_samples_gt_big_mean": st.mean(allpct_samples),
        },
    }
    # F-a28128a4: refuse a silent replace of the published floor; --overwrite says so.
    prior_mtime = os.path.getmtime(a.out) if os.path.isfile(a.out) else None
    pre_existed, prior = gate_floor_overwrite(a.out, a.overwrite)
    payload["out_dir_pre_existed"] = pre_existed
    payload["overwrote"] = [os.path.basename(a.out)] if pre_existed else []
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        payload.update(runtime_provenance())
        json.dump(payload, fh, indent=1)
    if pre_existed and prior is not None:
        when = (time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(prior_mtime))
                if prior_mtime is not None else "UNKNOWN")
        print(
            f"\nwrote {a.out}  runs={runs}  n_frames={n}  "
            f"replacing a record of runs={prior.get('runs')!r} "
            f"n_frames={prior.get('n_frames')!r} written {when}"
        )
    else:
        print(f"\nwrote {a.out}  runs={runs}  n_frames={n}")
    return payload


def _cli(argv=None):
    """The process entry point: an exit code, beside the floor record `main` returns.

    WAVE 25, F-68f3fb4b — the shape `composite_reference._cli` took in wave 22, for the
    same reason.

    `main` returns the floor payload and `tests/test_measure_floor.py` reads it
    (`rec = MF.main([...])`) at eight sites, so the payload stays the return value. This is
    the repeat-variance denominator this module's own docstring says every later number is
    read against.

    `main` keeps returning the floor record; this wrapper is what `run_tool_main` runs, so the
    process gets 0 on success, 2 on a typed refusal and 1 on a crash.
    """
    main(argv)
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(_cli, "MEASURE_FLOOR")
