#!/usr/bin/env python
"""measure_floor — the provider's repeat variance, per frame index.

    python tools/measure_floor.py --runs=A0r1,A0r2,A0r3 [--early=0-4] [--late=29-32]

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
"""

import argparse
import itertools
import json
import os
import statistics as st
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402


class FloorError(ArmatureError):
    """The floor could not be measured over the population that was asked for."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


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


def _stack(run_dir, sub="lossless"):
    d = os.path.join(run_dir, sub)
    names = sorted(n for n in os.listdir(d) if n.endswith(".png"))
    return [np.array(Image.open(os.path.join(d, n)).convert("RGB")).astype(np.int16) for n in names]


def _span(text):
    a, _, b = text.partition("-")
    return list(range(int(a), int(b) + 1))


def pair_stats(A, B, big=8):
    """Per-frame stats for one pair of runs.

    The length check is here rather than only at the call site because `zip` is here:
    a truncating pair is produced by this function, so this is where it is refused.
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
        out.append({
            "frame": i,
            "max": int(d.max()),
            "mean": float(d.mean()),
            "pct_gt": float(100.0 * (d > big).mean()),
            "identical": bool(d.max() == 0),
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--root", default="outputs/E02/runs")
    ap.add_argument("--early", default="0-4")
    ap.add_argument("--late", default="29-32")
    ap.add_argument("--big", type=int, default=8)
    ap.add_argument("--out", default="outputs/E02/floor.json")
    a = ap.parse_args(argv)

    # ---- ANDON, before a single PNG is opened: distinct runs, at least two of them.
    runs = check_runs([r for r in a.runs.split(",") if r])
    stacks = {r: _stack(os.path.join(a.root, r)) for r in runs}
    # ---- ANDON, before a single pair is compared: one verified frame count, not run[0]'s.
    n = common_frame_count(stacks)
    early, late = _span(a.early), _span(a.late)

    pairs = {}
    for x, y in itertools.combinations(runs, 2):
        pairs[f"{x}|{y}"] = pair_stats(stacks[x], stacks[y], a.big)

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

    print("THE SHAPE — per-frame max |delta|, every frame, first pair listed per column")
    print("  frame :  " + " ".join(f"{i:>3}" for i in range(n)))
    for k, ps in pairs.items():
        print(f"  {k[:12]:<12}: " + " ".join(f"{p['max']:>3}" for p in ps))
    print()

    def window(ps, idx):
        m = [ps[i]["max"] for i in idx if i < len(ps)]
        g = [ps[i]["pct_gt"] for i in idx if i < len(ps)]
        return m, g

    print(f"EARLY (frames {a.early}) vs LATE (frames {a.late}) — reported separately, always")
    rows = []
    for k, ps in pairs.items():
        em, eg = window(ps, early)
        lm, lg = window(ps, late)
        rows.append((k, em, eg, lm, lg))
        print(f"  {k}")
        print(f"    early  max|d|: min {min(em):>3} median {int(st.median(em)):>3} max {max(em):>3}"
              f"   |  px >{a.big}: {st.mean(eg):.3f}%")
        print(f"    late   max|d|: min {min(lm):>3} median {int(st.median(lm)):>3} max {max(lm):>3}"
              f"   |  px >{a.big}: {st.mean(lg):.3f}%")

    allmax = [p["max"] for ps in pairs.values() for p in ps]
    allpct = [p["pct_gt"] for ps in pairs.values() for p in ps]
    ndiff = sum(1 for ps in pairs.values() for p in ps if not p["identical"])
    print()
    print("WHOLE-CLIP SCALAR — recorded only so it can be compared with the codec-contaminated")
    print("                    first pass. It is NOT the floor; the per-index shape above is.")
    print(f"  frames differing : {ndiff} of {n * len(pairs)}")
    print(f"  per-frame max|d| : min {min(allmax)} · median {int(st.median(allmax))} · max {max(allmax)}")
    print(f"  px differing >{a.big}  : {st.mean(allpct):.3f}%")

    payload = {
        "runs": runs, "n_frames": n, "big_threshold": a.big,
        "frames_per_run": {r: len(s) for r, s in stacks.items()},
        "early_window": early, "late_window": late,
        "pairs": pairs,
        "whole_clip": {
            "frames_differing": ndiff, "of": n * len(pairs),
            "max_min": min(allmax), "max_median": st.median(allmax), "max_max": max(allmax),
            "pct_gt_big_mean": st.mean(allpct),
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print(f"\nwrote {a.out}")
    return payload


if __name__ == "__main__":
    main()
