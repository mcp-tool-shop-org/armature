#!/usr/bin/env python
"""measure_smoothness — how big a step the driving signal takes, per keypoint, per frame.

    python tools\\measure_smoothness.py --a=<keypoints.json> --b=<keypoints.json>
           --out=<record.json> [--label-a=E08 --label-b=E10]

E10's attribution instrument. The Director's eye named E08's motion choppy; the lever
under test is driving density, and this is the measurement that makes the attribution
causal rather than a vibe — if the painted result changes, this says whether the signal
the model was shown changed, and by how much.

**A DIAGNOSTIC. It gates nothing and decides nothing.** Metrics are diagnostics; the
Director's eye is the judge.

--------------------------------------------------------------------------------
Two units, because one of them would be a lie by omission

The second difference of a keypoint's pixel path, `p[i+2] - 2p[i+1] + p[i]`, is reported
in **px/frame²** and in **px/s²**, and they answer different questions:

* **px/frame²** is what the MODEL experiences: how far a joint's motion changes from one
  driving frame to the next. This is the quantity densification is aimed at.
* **px/s²** is what the PERFORMANCE does: the same path's acceleration in wall clock. It
  is (px/frame²) × fps², and on a resampling that preserves the path it should be roughly
  unchanged — because the path IS unchanged.

Reporting only the first would let a fall of a third read as "the motion got smoother",
when what happened is that the same motion is shown in smaller steps. Reporting only the
second would hide the thing the experiment is about. Ask of a metric what value it takes
when the hypothesis is false: a densification that changed nothing about the path moves the
per-frame number and leaves the per-second number alone, which is exactly what these two
together can tell apart.

**What the arm can and cannot move** (the "grade an arm only on what it can move" law):
per-frame, an arm that did nothing scores 1.0 against its own baseline and a perfectly
dense arm scores 0; the metric can move. Per-second, both ends score ~1.0 — so that column
is a control, not a score, and it is labelled as one.

Distributions, never a single mean: slerp between adjacent keys leaves the source's own
turns exactly where they were and adds samples between them, so a mean and a max move for
different reasons and a report that quoted one number would hide which.

Compensator (NAMED_COMPENSATORS): writes one JSON under `outputs/`. Compensator: delete the
file; owner: the executor session. Both inputs are opened read-only.

Prints `MEASURE_SMOOTHNESS_OK`.
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "E10.1"

#: `second_differences` reads `p[i]`, `p[i+1]` and `p[i+2]`, so a record with fewer than
#: three frames has no second difference at all — not a small one, none. Named here rather
#: than left implicit in a `range(len(series) - 2)` that silently yields nothing.
MIN_FRAMES_FOR_SECOND_DIFFERENCE = 3


class SmoothnessInputError(ArmatureError):
    """The two records do not describe the same population, so no ratio between them means
    anything.

    Carries the two lists that disagree — the useful half of the refusal.
    """


def check_records(ra, rb, label_a="A", label_b="B"):
    """Refuse two records whose keypoints are not the same keypoints, in the same order.

    `main` already refuses different resolutions and different cameras. It then took
    `names = ra['keypoint_names']` and labelled BOTH arms of the per-keypoint table with
    it, so nothing anywhere compared the two conventions. AAPose-20 and OpenPose-18
    ordering, and the left/right convention between them, are live hazards in this repo:
    under a permuted convention a wrist's second differences are divided by an elbow's
    under a single joint name, in the instrument E10 uses to make its densification
    attribution causal rather than a vibe.

    Both directions are checked, plus the record's internal agreement between its names
    and the keypoints its own frames carry — a short name list would silently truncate
    the table rather than fail.
    """
    na, nb = ra.get("keypoint_names"), rb.get("keypoint_names")
    ka = len(ra["body"][0]) if ra.get("body") else 0
    kb = len(rb["body"][0]) if rb.get("body") else 0
    ev = {"keypoint_names_a": na, "keypoint_names_b": nb,
          "n_keypoints_a": ka, "n_keypoints_b": kb,
          "label_a": label_a, "label_b": label_b}

    for label, names, k in ((label_a, na, ka), (label_b, nb, kb)):
        if not isinstance(names, list):
            raise SmoothnessInputError(
                f"record {label} carries no keypoint_names; the per-keypoint table "
                f"would be labelled by position alone", ev)
        if len(names) != k:
            raise SmoothnessInputError(
                f"record {label} names {len(names)} keypoint(s) and its frames carry "
                f"{k}; a table built from the shorter of the two is a table over a "
                f"population the record never described", ev)
    if ka != kb:
        raise SmoothnessInputError(
            f"the two records carry {ka} and {kb} keypoints per frame; a ratio between "
            f"them would divide one joint's second differences by another's", ev)
    if na != nb:
        differing = [i for i, (x, y) in enumerate(zip(na, nb)) if x != y]
        raise SmoothnessInputError(
            f"the two records name their keypoints differently at index "
            f"{differing[:8]} ({[na[i] for i in differing[:8]]} vs "
            f"{[nb[i] for i in differing[:8]]}); the per-keypoint table labels BOTH arms "
            f"with the first record's names, so the ratios would compare different joints "
            f"under one joint name", {**ev, "differing_indices": differing})

    # ---- the axis the three refusals above leave open: how many FRAMES each record has.
    #      `second_differences` needs three, so a record with two or fewer makes every
    #      pooled second-difference statistic `None` (`stats([])` returns `None`), and the
    #      success line then dereferenced `.items()` on it. Measured on this branch with
    #      two 2-frame records that pass every refusal above (matching resolution, camera,
    #      keypoint names and counts): `AttributeError: 'NoneType' object has no attribute
    #      'items'`, with the diagnostic payload ALREADY written to `--out` — a complete
    #      record on disk, no `MEASURE_SMOOTHNESS_OK` line, and a bare AttributeError
    #      naming neither the input nor the frame count that caused it (F-1fb7ba1c). The
    #      honest answer is a refusal by name: a second difference over fewer than three
    #      samples is undefined, not zero.
    for label, rec, path_key in ((label_a, ra, "a"), (label_b, rb, "b")):
        n_frames = len(rec.get("body") or ())
        if n_frames < MIN_FRAMES_FOR_SECOND_DIFFERENCE:
            raise SmoothnessInputError(
                f"record {label} carries {n_frames} frame(s); a second difference is "
                f"|p[i+2] - 2p[i+1] + p[i]| and is undefined below "
                f"{MIN_FRAMES_FOR_SECOND_DIFFERENCE}, so every pooled statistic this tool "
                f"reports would be null and the ratio between them would be null over null",
                {**ev, "gate": "FRAMES", "andon": "SmoothnessInputError",
                 "clause": "too_few_frames_for_a_second_difference",
                 "record": path_key, "label": label, "frames": n_frames,
                 "frames_declared": rec.get("frames"),
                 "minimum": MIN_FRAMES_FOR_SECOND_DIFFERENCE})
    return list(na)


def second_differences(series):
    """|p[i+2] - 2p[i+1] + p[i]| per step, for one keypoint's (x, y) pixel path."""
    out = []
    for i in range(len(series) - 2):
        ax = series[i + 2][0] - 2.0 * series[i + 1][0] + series[i][0]
        ay = series[i + 2][1] - 2.0 * series[i + 1][1] + series[i][1]
        out.append(math.hypot(ax, ay))
    return out


def first_differences(series):
    """|p[i+1] - p[i]| per step. The velocity whose change the second difference is."""
    return [math.hypot(series[i + 1][0] - series[i][0],
                       series[i + 1][1] - series[i][1])
            for i in range(len(series) - 1)]


def stats(values):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    return {"n": n, "min": s[0], "median": s[n // 2],
            "mean": sum(s) / n,
            "p90": s[min(n - 1, int(round(0.9 * (n - 1))))],
            "max": s[-1]}


def per_keypoint(record):
    """`{index: [(x, y)]}` for the 20 body keypoints of a projected-keypoint record."""
    body = record["body"]
    n_kp = len(body[0])
    return {k: [(f[k][0], f[k][1]) for f in body] for k in range(n_kp)}


def measure(record, fps):
    """Second and first differences per body keypoint, in both units."""
    paths = per_keypoint(record)
    dt = 1.0 / float(fps)
    out = {}
    for k, path in paths.items():
        second = second_differences(path)
        first = first_differences(path)
        out[k] = {
            "second_px_per_frame2": stats(second),
            "second_px_per_s2": stats([v / (dt * dt) for v in second]),
            "first_px_per_frame": stats(first),
            "first_px_per_s": stats([v / dt for v in first]),
        }
    return out


def pooled(record, fps):
    """Every keypoint's steps pooled into one distribution, both units."""
    paths = per_keypoint(record)
    second, first = [], []
    for path in paths.values():
        second.extend(second_differences(path))
        first.extend(first_differences(path))
    dt = 1.0 / float(fps)
    return {
        "second_px_per_frame2": stats(second),
        "second_px_per_s2": stats([v / (dt * dt) for v in second]),
        "first_px_per_frame": stats(first),
        "first_px_per_s": stats([v / dt for v in first]),
    }


def ratios(a, b):
    """b / a, field by field, for two `stats` dicts. `None` where a is zero."""
    if not a or not b:
        return None
    return {k: (b[k] / a[k] if isinstance(a.get(k), float) and a[k] else None)
            for k in ("min", "median", "mean", "p90", "max")}


def _summarisable(block, what, label, record, path):
    """`block`, or refuse by name because `stats`/`ratios` had nothing to compute over.

    `stats([])` is `None` and `ratios(a, b)` is `None` when either side is falsy — both
    documented, both reachable, and the success line dereferenced `.items()` on them
    anyway. The frame refusal in `check_records` closes the case that produced this in
    practice (a record with fewer than three frames); this is the andon on the direction
    that check does not bound — any other route to an empty distribution, a record whose
    `body` frames carry zero keypoints among them. A refusal names the block and the
    record; an `AttributeError` names neither.
    """
    if block is None:
        raise SmoothnessInputError(
            f"{what} came back with nothing to summarise for {label}; `stats`/`ratios` "
            f"return None over an empty distribution, and the success line would report a "
            f"measurement that was never computed",
            {"gate": "SUMMARY", "andon": "SmoothnessInputError",
             "clause": "no_distribution_to_summarise", "block": what, "label": label,
             "path": os.path.abspath(path),
             "frames": len(record.get("body") or ()),
             "keypoints": len((record.get("body") or [[]])[0])})
    return block


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="how big a step the driving signal takes, per keypoint, per frame — "
                    "the two records side by side")
    ap.add_argument("--a", required=True, help="the baseline keypoints.json")
    ap.add_argument("--b", required=True, help="the densified keypoints.json")
    ap.add_argument("--out", required=True, help="the comparison JSON to write")
    ap.add_argument("--label-a", default="A", help="what --a is called in the record")
    ap.add_argument("--label-b", default="B", help="what --b is called in the record")
    a = ap.parse_args(argv)

    with open(a.a, encoding="utf-8") as fh:
        ra = json.load(fh)
    with open(a.b, encoding="utf-8") as fh:
        rb = json.load(fh)

    if ra["resolution"] != rb["resolution"]:
        raise SmoothnessInputError(
            f"the two records are projected at different resolutions "
            f"({ra['resolution']} vs {rb['resolution']}); a pixel comparison across "
            f"resolutions measures the resolution",
            {"gate": "RESOLUTION", "resolution_a": ra["resolution"],
             "resolution_b": rb["resolution"], "a": a.a, "b": a.b})
    if ra["camera"]["radius"] != rb["camera"]["radius"] or \
            ra["camera"]["target"] != rb["camera"]["target"]:
        raise SmoothnessInputError(
            "the two records were projected through different cameras; the difference "
            "measured would include the composition",
            {"gate": "CAMERA", "camera_a": ra["camera"], "camera_b": rb["camera"],
             "a": a.a, "b": a.b})

    # ---- the same style of refusal as the two above, on the axis they left open.
    names = check_records(ra, rb, label_a=a.label_a, label_b=a.label_b)

    fa, fb = ra["fps"], rb["fps"]
    pa, pb = pooled(ra, fa), pooled(rb, fb)
    ka, kb = measure(ra, fa), measure(rb, fb)

    per_kp = {}
    for k in ka:
        per_kp[names[k]] = {
            a.label_a: ka[k], a.label_b: kb[k],
            "ratio_second_px_per_frame2": ratios(ka[k]["second_px_per_frame2"],
                                                 kb[k]["second_px_per_frame2"]),
            "ratio_second_px_per_s2": ratios(ka[k]["second_px_per_s2"],
                                             kb[k]["second_px_per_s2"]),
        }
    rose = [n for n, v in per_kp.items()
            if (v["ratio_second_px_per_frame2"] or {}).get("median") is not None
            and v["ratio_second_px_per_frame2"]["median"] > 1.0]

    payload = {
        "tool": "measure_smoothness", "tool_version": TOOL_VERSION,
        "status": "DIAGNOSTIC — gates nothing, decides nothing",
        "inputs": {
            a.label_a: {"path": os.path.abspath(a.a), "frames": ra["frames"],
                        "fps": fa, "resolution": ra["resolution"]},
            a.label_b: {"path": os.path.abspath(a.b), "frames": rb["frames"],
                        "fps": fb, "resolution": rb["resolution"]},
        },
        "units": {
            "px_per_frame2": ("what the MODEL experiences: how much a joint's per-frame "
                              "step changes from one driving frame to the next"),
            "px_per_s2": ("what the PERFORMANCE does: the same path's acceleration in wall "
                          "clock. A CONTROL, not a score — a resampling that preserves the "
                          "path leaves it alone, and both a do-nothing arm and a perfect "
                          "arm read the same here"),
        },
        "pooled": {a.label_a: pa, a.label_b: pb,
                   "ratio_second_px_per_frame2": ratios(pa["second_px_per_frame2"],
                                                        pb["second_px_per_frame2"]),
                   "ratio_second_px_per_s2": ratios(pa["second_px_per_s2"],
                                                    pb["second_px_per_s2"]),
                   "ratio_first_px_per_frame": ratios(pa["first_px_per_frame"],
                                                      pb["first_px_per_frame"])},
        "per_keypoint": per_kp,
        "keypoints_whose_per_frame_median_ROSE": rose,
    }
    # ---- the success line is BUILT before the record is written, and it refuses rather
    #      than dereferencing a `None`. Every `.items()` below is on a value `stats` or
    #      `ratios` may legitimately return `None` for; building the line first means a
    #      refusal here leaves no payload on disk to be mistaken for a finished run
    #      (F-1fb7ba1c).
    ok_line = {
        "out": os.path.abspath(a.out),
        "pooled_second_px_per_frame2": {
            a.label_a: {k: round(v, 4) for k, v in _summarisable(
                pa["second_px_per_frame2"], "pooled second_px_per_frame2",
                a.label_a, ra, a.a).items() if k != "n"},
            a.label_b: {k: round(v, 4) for k, v in _summarisable(
                pb["second_px_per_frame2"], "pooled second_px_per_frame2",
                a.label_b, rb, a.b).items() if k != "n"},
            "ratio": {k: (round(v, 4) if v else v) for k, v in _summarisable(
                payload["pooled"]["ratio_second_px_per_frame2"],
                "pooled ratio_second_px_per_frame2", f"{a.label_a}/{a.label_b}",
                ra, a.a).items()}},
        "pooled_second_px_per_s2_ratio": {
            k: (round(v, 4) if v else v) for k, v in _summarisable(
                payload["pooled"]["ratio_second_px_per_s2"],
                "pooled ratio_second_px_per_s2", f"{a.label_a}/{a.label_b}",
                ra, a.a).items()},
        "keypoints_that_rose": rose}

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print("MEASURE_SMOOTHNESS_OK " + json.dumps(ok_line))
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MEASURE_SMOOTHNESS")
