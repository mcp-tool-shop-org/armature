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

TOOL_VERSION = "E10.1"


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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="the baseline keypoints.json")
    ap.add_argument("--b", required=True, help="the densified keypoints.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    a = ap.parse_args(argv)

    with open(a.a, encoding="utf-8") as fh:
        ra = json.load(fh)
    with open(a.b, encoding="utf-8") as fh:
        rb = json.load(fh)

    if ra["resolution"] != rb["resolution"]:
        raise SystemExit(f"the two records are projected at different resolutions "
                         f"({ra['resolution']} vs {rb['resolution']}); a pixel comparison "
                         f"across resolutions measures the resolution")
    if ra["camera"]["radius"] != rb["camera"]["radius"] or \
            ra["camera"]["target"] != rb["camera"]["target"]:
        raise SystemExit("the two records were projected through different cameras; the "
                         "difference measured would include the composition")

    fa, fb = ra["fps"], rb["fps"]
    pa, pb = pooled(ra, fa), pooled(rb, fb)
    ka, kb = measure(ra, fa), measure(rb, fb)

    names = ra["keypoint_names"]
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
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print("MEASURE_SMOOTHNESS_OK " + json.dumps({
        "out": os.path.abspath(a.out),
        "pooled_second_px_per_frame2": {
            a.label_a: {k: round(v, 4) for k, v in pa["second_px_per_frame2"].items()
                        if k != "n"},
            a.label_b: {k: round(v, 4) for k, v in pb["second_px_per_frame2"].items()
                        if k != "n"},
            "ratio": {k: (round(v, 4) if v else v) for k, v in
                      payload["pooled"]["ratio_second_px_per_frame2"].items()}},
        "pooled_second_px_per_s2_ratio": {
            k: (round(v, 4) if v else v) for k, v in
            payload["pooled"]["ratio_second_px_per_s2"].items()},
        "keypoints_that_rose": rose}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
