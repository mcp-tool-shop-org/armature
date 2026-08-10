#!/usr/bin/env python
"""analyze_p3 — the sign and shape of the normalization difference.

    python tools/analyze_p3.py --run=<run dir> --out=<p3_sign.json>

`stage_render` records P3's magnitude. This records its **direction**: whether the
per-shot window makes near surfaces darker and far surfaces lighter, and where the
crossover sits. Measured in the 8-bit space that actually ships, from the emitted PNGs
— not from the float masters — because 8-bit is what a consumer sees (F19: the
conditioning image is an RGB PNG, hard-capped at 8 bits).

Reports both normalizations. Chooses neither.
"""

import json
import os
import sys

import numpy as np
from PIL import Image


def _arr(path):
    img = Image.open(path)
    a = np.array(img)
    return a.astype(bool) if img.mode == "1" else a.astype(np.int16)


def analyze(run_dir):
    manifest = json.load(open(os.path.join(run_dir, "manifest.json"), encoding="utf-8"))
    count = manifest["frame_count"]

    frames, all_signed, all_dpf = [], [], []
    for i in range(count):
        name = f"{i:05d}.png"
        mask = _arr(os.path.join(run_dir, "mask", name))
        d_pf = _arr(os.path.join(run_dir, "depth_perframe", name))[mask]
        d_ps = _arr(os.path.join(run_dir, "depth_pershot", name))[mask]
        signed = (d_ps - d_pf).astype(np.int32)

        # Split the frame's geometry at its own median depth: "near half" and "far
        # half" are per-frame quantities, not a global brightness constant.
        med = int(np.median(d_pf))
        near, far = d_pf > med, d_pf < med
        frames.append({
            "frame": i,
            "n_px": int(mask.sum()),
            "median_d_perframe": med,
            "mean_signed_near_half": float(signed[near].mean()) if near.any() else None,
            "mean_signed_far_half": float(signed[far].mean()) if far.any() else None,
            "mean_abs_levels": float(np.abs(signed).mean()),
            "max_abs_levels": int(np.abs(signed).max()),
            "frac_darker": float((signed < 0).mean()),
            "frac_lighter": float((signed > 0).mean()),
        })
        all_signed.append(signed)
        all_dpf.append(d_pf)

    signed = np.concatenate(all_signed)
    dpf = np.concatenate(all_dpf)

    # crossover: the per-frame depth level at which the sign flips
    order = np.argsort(dpf)
    dpf_s, signed_s = dpf[order], signed[order]
    crossover = None
    flips = np.flatnonzero(np.diff(np.sign(np.maximum.accumulate(np.where(signed_s > 0, 1, -1)))))
    bins = np.arange(0, 257, 8)
    means = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        sel = (dpf >= lo) & (dpf < hi)
        means.append({"d_perframe_bin": [int(lo), int(hi)],
                      "n_px": int(sel.sum()),
                      "mean_signed_levels": float(signed[sel].mean()) if sel.any() else None})
    for a, b in zip(means[:-1], means[1:]):
        if a["mean_signed_levels"] is None or b["mean_signed_levels"] is None:
            continue
        if a["mean_signed_levels"] > 0 >= b["mean_signed_levels"]:
            crossover = int(b["d_perframe_bin"][0])
            break

    per_frame_dir = {
        "frames_where_near_half_is_darker": sum(
            1 for f in frames if f["mean_signed_near_half"] is not None and f["mean_signed_near_half"] < 0
        ),
        "frames_where_far_half_is_lighter": sum(
            1 for f in frames if f["mean_signed_far_half"] is not None and f["mean_signed_far_half"] > 0
        ),
        "n_frames": count,
    }

    return {
        "run": os.path.abspath(run_dir),
        "unit": "8-bit levels of the emitted PNG; positive = per-shot is lighter",
        "n_geometry_px_total": int(signed.size),
        "mean_abs_levels": float(np.abs(signed).mean()),
        "max_abs_levels": int(np.abs(signed).max()),
        "mean_signed_levels": float(signed.mean()),
        "frac_darker_under_per_shot": float((signed < 0).mean()),
        "frac_lighter_under_per_shot": float((signed > 0).mean()),
        "frac_identical": float((signed == 0).mean()),
        "crossover_d_perframe_level": crossover,
        "direction": per_frame_dir,
        "binned_mean_signed": means,
        "per_frame": frames,
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    args = {}
    for token in argv:
        key, _, value = token[2:].partition("=")
        args[key] = value
    report = analyze(args["run"])
    if "out" in args:
        os.makedirs(os.path.dirname(os.path.abspath(args["out"])), exist_ok=True)
        with open(args["out"], "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    print("P3_SIGN " + json.dumps({
        k: report[k] for k in (
            "mean_abs_levels", "max_abs_levels", "mean_signed_levels",
            "frac_darker_under_per_shot", "frac_lighter_under_per_shot",
            "crossover_d_perframe_level", "direction",
        )
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
