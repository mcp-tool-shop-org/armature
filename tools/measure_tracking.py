#!/usr/bin/env python
"""measure_tracking — the timing-correlation statistic, as an instrument.

    python tools/measure_tracking.py --run=<frames_dir> --control=<frames_dir> \
        --label=A1a --out=<report.json>
    python tools/measure_tracking.py --anchor          # reproduce E02's published figures

**Why this file exists.** E02 published +0.521 for A1a and +0.581 for A1b and left the
0.060 gap unruled. Those numbers were computed inline during that session and were never
written down as code, so the single statistic E04 exists to put a floor under could not be
recomputed from the repo. *A recipe that does not reproduce its output is not a recipe* —
so before E04 quotes the statistic, the statistic gets a file.

## The definition, pinned

Per-frame temporal energy, then Pearson correlation against the control's own profile::

    d(t) = mean |frame(t) - frame(t-1)|       for t = 1 .. n-1      (n-1 values)
    r    = pearson( d_run , d_control )

**Grayscale, and that is not a detail.** Frames are read through `PIL.Image.convert("L")`
(ITU-R 601-2 luma, `0.299R + 0.587G + 0.114B`). Read the same frames in RGB and the same
arms give +0.558 / +0.585 instead of +0.521 / +0.581 — a 0.037 shift on A1a, which is
*over half* the 0.060 gap E02 could not read. The colour mode is therefore part of the
statistic's definition rather than an implementation choice, and `test_measure_tracking.py`
pins it with a fixture whose two modes disagree by construction.

## Floor and ceiling, stated before any number is read

* An arm whose energy profile is proportional to the control's gives **+1.000**.
* An arm ignoring the control gives **~0** (E02 measured the no-control arm at -0.065).
* Re-running one submission gives the *same value to every decimal* — measured, not
  assumed: A0r1/r2/r3 are three identical submissions and all three return
  +0.5206918475. **That is the fixed-seed floor, and it is exactly zero.** The floor for
  drawing a *different sample* — a different seed — is a different quantity, is not this
  one, and is what E04 was commissioned to measure.

## What it is not

A diagnostic. It says whether two clips move at the same *moments*; it says nothing about
whether the figure is in the same *place*, and nothing about whether it is the same
character. **It gates nothing**, and identity is the Director's by eye.

## The control profile is polarity-blind, by construction and by measurement

`d(t)` is built from absolute differences, so a full-image `255 - x` leaves it unchanged:
inverting every pixel negates every delta and `abs` undoes it. Measured on E02's own
control pair, the near-bright and near-dark profiles agree to **0.0 over all 32 deltas**.
So both E04 conditions correlate against the *same* reference profile, and any difference
between them lives entirely in the outputs.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402
from sheet_compose import frames_by_number  # noqa: E402

TOOL_VERSION = "E04.1"

#: E02's published figures, and the frames each was computed from. The anchor leg checks
#: every one of them. `A1a` is recorded against **A0r1's lossless frames** deliberately:
#: A1a itself ran before the lossless tap existed (its payload has no node 302), so the
#: only lossless capture of that condition is A0, which is A1a's payload plus the tap and
#: nothing else. A1a's own H.264 frames return +0.545, not +0.521.
E02_PUBLISHED = {
    "A1a": {"value": 0.521, "run": "A0r1/lossless", "control": "control_480x832/depth_pershot"},
    "A1b": {"value": 0.581, "run": "A1b/lossless",
            "control": "control_480x832/depth_pershot_inverted"},
    "A2": {"value": -0.064, "run": "A2/lossless", "control": "control_480x832/depth_pershot"},
}
#: Cross-arm figures E02 also published, checked by the same leg.
E02_PUBLISHED_CROSS = {("A1a", "A1b"): 0.343, ("A1a", "A2"): -0.113}

ANCHOR_TOLERANCE = 0.0005  # published to 3 decimals; this is half a unit in the last place

#: The exit code for "the anchor could not check anything". Distinct from 0 (checked and
#: reproduced) and from the 2 a raised `AnchorMismatch` earns through the caller's own halt
#: handling, because "could not check" and "checked and passed" are different answers and a
#: caller that branches on the code is asking which one happened.
ANCHOR_ABSENT_EXIT = 3


# ---- `_CarriesEvidence` was here, and is DELETED (wave 16, F-13333ef4).
#
# It was introduced in wave 14 as a private base giving the two classes below the
# `(message, evidence=None)` shape, on the stated premise that "`ArmatureError` defines
# none". Measured in this worktree on 2026-09-04, that premise is FALSE: the wave-14 merge
# put `__init__(self, message, evidence=None)` on the base itself
# (`armature_core/errors.py::ArmatureError.__init__`), storing the dict AS PASSED.
#
# What survived the premise was a behaviour CHANGE the base rules against. Measured:
# `ArmatureError('m').evidence is None` while `TrackingError('m').evidence == {}` -- and
# `errors.py:27-33` states that the null is the honest record for a plain refusal
# ("`evidence: null` beside `gate: null` ... The defect was never the null"). An AST walk
# over `tools/*.py` for `raise _CarriesEvidence(` found ZERO sites, so the class's only
# remaining effect was that contradiction, in a domain where all thirty plain-refusal
# classes had made the same one.
#
# Both classes below now derive `ArmatureError` directly and define no `__init__`:
# inheritance already gives them the two-argument shape, and a bare-message refusal from
# either of them prints `"evidence": null` in its halt record, as the contract says it must.


class TrackingError(ArmatureError):
    """The statistic could not be computed on what was handed to it."""


class AnchorMismatch(ArmatureError):
    """The instrument does not reproduce E02's published figures.

    Not cosmetic. E04 exists to put a floor under two numbers E02 published; an
    instrument that returns something *else* on E02's own runs is measuring a different
    quantity, and every E04 number computed with it would be a floor under a statistic
    nobody quoted. The anchor leg raises rather than warns for that reason.
    """


def _frame_names(d):
    """Sorted frame names, with the check that makes lexical sort mean frame order.

    Lexical sort is frame order only while every name is the same width — `1.png`,
    `2.png`, `10.png` sorts 1, 10, 2 and would silently scramble the time axis into a
    profile that still has the right length and still correlates to *something*. That is
    the failure this check exists to catch, so it raises instead of sorting cleverly:
    the repo's frame writers all zero-pad, so a ragged directory is a sign the input is
    not what the caller thinks it is.

    **WAVE 25 (F-2f2c19a9): the ANDON is on the direction the fixed-width check does not
    bound.** This function listed `*.png` and then guarded a DIFFERENT property — that every
    name is the same LENGTH — which is a diagnostic standing where the invariant's own andon
    belongs. Measured on `580af47` in this worktree on three synthetic control directories:
    `00000..00003.png` gave four names; adding `strip_every8.png` was refused, but for the
    RAGGED-WIDTH reason, i.e. by accident of that stray's length; adding `plate.png` — nine
    characters, the same width as `00001.png` — was admitted in SILENCE and became a sample
    of the temporal-energy profile the timing correlation is computed from, and was hashed
    into `_manifest_sha256` as part of the recorded provenance. `render_pose_sticks` writes
    `strip_every{N}.png` into the same directory as its `NNNNN.png` control frames
    (render_pose_sticks.py:335), so a control directory holding a non-frame PNG is the
    pipeline's own ordinary output, not a hypothetical.

    `sheet_compose.frames_by_number` is the ONE home for "the numbered frame population,
    with a stray refusal" — eight instruments in this domain carry that refusal already — so
    it is adopted by import rather than spelled a ninth time. The fixed-width check STAYS,
    because it catches a different defect (a ragged zero-pad among names that are all
    numbered), and it now runs on a population that is already known to be frames.
    """
    if not os.path.isdir(d):
        raise TrackingError(
            f"no such frame directory: {d}",
            {"gate": "FRAMES", "andon": "TrackingError",
             "clause": "frames_dir_is_not_a_directory", "frames_dir": d})
    pngs = sorted(n for n in os.listdir(d) if n.lower().endswith(".png"))
    # ---- ANDON on the population itself, through the ONE home, before anything is read.
    frames_by_number(pngs, where=d, what="frames", exc=TrackingError,
                     evidence={"andon": "TrackingError",
                               "clause": "stray_png_in_the_frame_population"})
    names = pngs
    if not names:
        raise TrackingError(
            f"no PNG frames in {d}",
            {"gate": "FRAMES", "andon": "TrackingError",
             "clause": "no_numbered_frames_to_measure", "frames_dir": d})
    widths = {len(n) for n in names}
    if len(widths) != 1:
        raise TrackingError(
            f"{d}: frame names are not a fixed width ({sorted(widths)}), so sorting them "
            f"lexically would not put them in frame order; e.g. {names[:4]}",
            {"gate": "FRAMES", "andon": "TrackingError",
             "clause": "frame_names_are_not_a_fixed_width",
             "frames_dir": d, "widths": sorted(widths), "frames": names[:8]}
        )
    return names


def load_profile(frames_dir):
    """Temporal-energy profile of a frame directory: n-1 values, one per adjacent pair."""
    names = _frame_names(frames_dir)
    if len(names) < 3:
        raise TrackingError(
            f"{frames_dir}: {len(names)} frame(s); a correlation over fewer than two "
            f"deltas is degenerate"
        )
    stack = np.stack([
        np.asarray(Image.open(os.path.join(frames_dir, n)).convert("L"), dtype=np.float64)
        for n in names
    ])
    profile = np.abs(np.diff(stack, axis=0)).mean(axis=(1, 2))
    return profile, names


def pearson(x, y):
    """Pearson r, with the constant-input case raised rather than returned as nan.

    A clip whose every frame is identical has a zero-variance profile, and `np.corrcoef`
    returns nan for it with a RuntimeWarning that a batch run would scroll past. Nan is
    not a low correlation — it is the absence of a measurement — and a report that
    printed it beside real numbers would invite it to be read as one.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.shape != y.shape:
        raise TrackingError(f"profiles have different lengths: {x.shape} vs {y.shape}")
    for name, v in (("run", x), ("control", y)):
        if not np.isfinite(v).all():
            raise TrackingError(f"{name} profile carries non-finite values")
        if v.std() == 0:
            raise TrackingError(
                f"the {name} profile is constant — every frame differs from its "
                f"neighbour by the same amount, so there is no timing to correlate. "
                f"A correlation is undefined here, not low."
            )
    return float(np.corrcoef(x, y)[0, 1])


def _manifest_sha256(frames_dir, names):
    """One digest over the frames actually read, so a report names its own inputs."""
    h = hashlib.sha256()
    for n in names:
        with open(os.path.join(frames_dir, n), "rb") as fh:
            h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def measure(run_dir, control_dir, label=None):
    """The statistic for one run against one control, with its provenance."""
    run_profile, run_names = load_profile(run_dir)
    ctl_profile, ctl_names = load_profile(control_dir)
    if len(run_names) != len(ctl_names):
        raise TrackingError(
            f"frame counts differ: run {run_dir} has {len(run_names)}, control "
            f"{control_dir} has {len(ctl_names)}; the two profiles are not the same axis"
        )
    return {
        "tool": "measure_tracking",
        "tool_version": TOOL_VERSION,
        "label": label,
        "statistic": "pearson(temporal_energy(run), temporal_energy(control))",
        "colour_mode": "L (PIL ITU-R 601-2 luma)",
        "timing_correlation": pearson(run_profile, ctl_profile),
        "n_frames": len(run_names),
        "n_deltas": len(run_profile),
        "run": {
            "dir": run_dir,
            "frames": len(run_names),
            "manifest_sha256": _manifest_sha256(run_dir, run_names),
            "energy_profile": [float(v) for v in run_profile],
        },
        "control": {
            "dir": control_dir,
            "frames": len(ctl_names),
            "manifest_sha256": _manifest_sha256(control_dir, ctl_names),
            "energy_profile": [float(v) for v in ctl_profile],
        },
    }


# --------------------------------------------------------------------- the anchor leg

def anchor(e02_root="outputs/E02", tolerance=ANCHOR_TOLERANCE):
    """Recompute E02's five published figures. Raises `AnchorMismatch` on any miss.

    Returns a rows list. If E02's runs are not on disk — they are gitignored output —
    this returns `None` rather than passing vacuously, because an anchor that reports
    green when it read nothing is worse than no anchor.
    """
    runs = os.path.join(e02_root, "runs")
    if not os.path.isdir(runs):
        return None

    def d(rel):
        return os.path.join(runs, rel) if "/" in rel and not rel.startswith("control") \
            else os.path.join(e02_root, rel)

    profiles, rows = {}, []
    for arm, rec in E02_PUBLISHED.items():
        run_dir, ctl_dir = d(rec["run"]), os.path.join(e02_root, rec["control"])
        if not (os.path.isdir(run_dir) and os.path.isdir(ctl_dir)):
            return None
        p, _ = load_profile(run_dir)
        c, _ = load_profile(ctl_dir)
        profiles[arm] = p
        got = pearson(p, c)
        rows.append({
            "row": f"{arm} vs control", "published": rec["value"], "recomputed": got,
            "delta": abs(got - rec["value"]), "frames": rec["run"],
        })
    for (a, b), pub in E02_PUBLISHED_CROSS.items():
        got = pearson(profiles[a], profiles[b])
        rows.append({
            "row": f"corr({a}, {b})", "published": pub, "recomputed": got,
            "delta": abs(got - pub), "frames": f"{E02_PUBLISHED[a]['run']} | "
                                               f"{E02_PUBLISHED[b]['run']}",
        })

    missed = [r for r in rows if r["delta"] > tolerance]
    if missed:
        raise AnchorMismatch(
            "the instrument does not reproduce E02's published figures, so it is not "
            "measuring what E02 measured: "
            + "; ".join(f"{m['row']} published {m['published']:+.3f} recomputed "
                        f"{m['recomputed']:+.4f}" for m in missed)
        )
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the timing-correlation statistic between an output and the control "
                    "that drove it, as an instrument — a diagnostic, not a verdict")
    ap.add_argument("--run", help="directory of output frames (use the LOSSLESS tap)")
    ap.add_argument("--control", help="directory of control frames")
    ap.add_argument("--label",
                    help="what this pairing is called in the record and the printed row")
    ap.add_argument("--out",
                    help="where to write the JSON report; omitted, the numbers only reach "
                         "stdout")
    ap.add_argument("--anchor", action="store_true",
                    help="reproduce E02's published figures and raise on any miss")
    ap.add_argument("--allow-absent", action="store_true",
                    help="with --anchor: exit 0 when E02's runs are not on disk, instead "
                         "of the ANCHOR_ABSENT_EXIT code. Names itself in the printed "
                         "line, so a green anchor that read nothing says so")
    ap.add_argument("--e02-root", default="outputs/E02",
                    help="with --anchor: the directory E02's published runs are read from")
    a = ap.parse_args(argv)

    if a.anchor:
        rows = anchor(a.e02_root)
        if rows is None:
            # The stdout line was already honest and follows the repo's NOT-YET-RUN rule;
            # the EXIT CODE was not. All three outcomes a caller can read were spelled 0:
            # "the instrument reproduces E02's figures", "the anchor never ran", and only
            # a raised AnchorMismatch distinguished a real miss. `outputs/` is gitignored
            # BY DESIGN, so "the runs are absent" is the DEFAULT state of any fresh clone,
            # CI runner or swarm worktree -- a verify chain would have recorded a green
            # anchor for an instrument that opened no file, and every later
            # timing-correlation number would be quoted against a calibration nobody
            # performed.
            print("ANCHOR NOT YET RUN — E02's runs are not on disk (gitignored output); "
                  f"looked under {a.e02_root}"
                  + ("; exit 0 because --allow-absent was given" if a.allow_absent
                     else f"; exiting {ANCHOR_ABSENT_EXIT} — pass --allow-absent to make "
                          f"this an optional step"))
            return 0 if a.allow_absent else ANCHOR_ABSENT_EXIT
        print(f"ANCHOR — E02's published figures, recomputed (tolerance {ANCHOR_TOLERANCE})")
        for r in rows:
            print(f"  {r['row']:<22} published {r['published']:+.3f}   "
                  f"recomputed {r['recomputed']:+.4f}   |d| {r['delta']:.4f}   "
                  f"[{r['frames']}]")
        print(f"  => {len(rows)} of {len(rows)} rows reproduce")
        return 0

    if not (a.run and a.control):
        # ---- WAVE 25 (F-314625be): the LAST `ap.error` call site under `tools/`, and the
        #      shape the repo measured, named and closed everywhere else one wave ago
        #      (`render_turnaround.py:452-466`, F-0befca53). `ap.error` raises
        #      `SystemExit(2)` from inside `main` and argparse prints a usage line on
        #      stderr: measured on `580af47` with the repo venv,
        #      `python tools/measure_tracking.py --label=x` -> rc 2, stdout EMPTY, stderr
        #      `measure_tracking.py: error: --run and --control are required unless
        #      --anchor is given`. 2 is the code this repo's halt contract reserves for "a
        #      gate decided", so a caller or a verify chain branching on 2 read an argparse
        #      usage error from the timing-correlation instrument as a fired andon, with no
        #      sentinel line, no gate id and no clause to tell the two apart. This module's
        #      own `ANCHOR_ABSENT_EXIT = 3` already shows it knows a distinct outcome needs
        #      a distinct code. The CODE is unchanged — 2 was and is correct for a refusal;
        #      what changes is that the refusal now carries a `MEASURE_TRACKING_HALT` line.
        #      The condition is a real invariant argparse cannot express, which is why it
        #      was hand-rolled here in the first place.
        raise TrackingError(
            "--run and --control are required unless --anchor is given",
            {"gate": "ARGS", "andon": "TrackingError", "clause": "missing_required",
             "flags": ["--run", "--control", "--anchor"],
             "run": a.run, "control": a.control, "anchor": bool(a.anchor)})
    rec = measure(a.run, a.control, a.label)
    print("MEASURE_TRACKING " + json.dumps({
        "label": rec["label"], "timing_correlation": round(rec["timing_correlation"], 6),
        "n_frames": rec["n_frames"], "run": rec["run"]["dir"]}))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=1)
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MEASURE_TRACKING")
