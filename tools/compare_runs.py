#!/usr/bin/env python
"""compare_runs — G3's instrument. Compares two run directories **pixel by pixel**.

    python tools/compare_runs.py --a=<run_a> --b=<run_b> --out=<report.json>

A PNG byte-hash mismatch is **not** evidence a render changed — facet false-halted on
that twice. So this compares decoded pixels and reports per-channel max and mean
absolute difference, plus where any difference lives. It **reports; it does not halt**:
G3 is a measurement, not an andon, and the spec says do not halt on nonzero without
inspecting where it lives.

Byte hashes are still reported alongside, because the difference between "the bytes
differ" and "the pixels differ" is itself the finding facet paid for.

Runs outside Blender (Pillow is not in Blender's python), which also makes the decoder
a different implementation from the writer.
"""

import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _load(path):
    img = Image.open(path)
    arr = np.array(img)
    if arr.dtype == bool:
        arr = arr.astype(np.uint8) * 255
    return arr.astype(np.int32)


def compare_channel(dir_a, dir_b):
    names_a = sorted(f for f in os.listdir(dir_a) if f.endswith(".png"))
    names_b = sorted(f for f in os.listdir(dir_b) if f.endswith(".png"))
    rec = {
        "frames_a": len(names_a),
        "frames_b": len(names_b),
        "frames_compared": 0,
        "max_abs_diff": 0,
        "mean_abs_diff": 0.0,
        "n_frames_with_any_pixel_difference": 0,
        "n_frames_with_byte_difference": 0,
        "worst_frame": None,
        "shape_mismatch": [],
    }
    if names_a != names_b:
        rec["name_mismatch"] = {
            "only_in_a": sorted(set(names_a) - set(names_b))[:8],
            "only_in_b": sorted(set(names_b) - set(names_a))[:8],
        }

    shared = [n for n in names_a if n in set(names_b)]
    total, npx = 0.0, 0
    for name in shared:
        pa, pb = os.path.join(dir_a, name), os.path.join(dir_b, name)
        if _sha256(pa) != _sha256(pb):
            rec["n_frames_with_byte_difference"] += 1
        a, b = _load(pa), _load(pb)
        if a.shape != b.shape:
            rec["shape_mismatch"].append({"frame": name, "a": list(a.shape), "b": list(b.shape)})
            continue
        d = np.abs(a - b)
        rec["frames_compared"] += 1
        mx = int(d.max())
        if mx > 0:
            rec["n_frames_with_any_pixel_difference"] += 1
            if rec["worst_frame"] is None or mx > rec["max_abs_diff"]:
                ys, xs = np.nonzero(d.reshape(d.shape[0], -1))
                rec["worst_frame"] = {
                    "frame": name,
                    "max_abs_diff": mx,
                    "n_differing_px": int((d > 0).sum()),
                    "first_differing_row": int(ys.min()) if ys.size else None,
                }
        rec["max_abs_diff"] = max(rec["max_abs_diff"], mx)
        total += float(d.sum())
        npx += int(d.size)
    rec["mean_abs_diff"] = (total / npx) if npx else None
    return rec


def compare_runs(run_a, run_b):
    chans_a = {d for d in os.listdir(run_a) if os.path.isdir(os.path.join(run_a, d))}
    chans_b = {d for d in os.listdir(run_b) if os.path.isdir(os.path.join(run_b, d))}
    shared = sorted(c for c in chans_a & chans_b if c != "master")

    report = {
        "run_a": os.path.abspath(run_a),
        "run_b": os.path.abspath(run_b),
        "channels_only_in_a": sorted(chans_a - chans_b),
        "channels_only_in_b": sorted(chans_b - chans_a),
        "channels": {},
    }
    for c in shared:
        report["channels"][c] = compare_channel(
            os.path.join(run_a, c), os.path.join(run_b, c)
        )

    report["verdict_inputs"] = {
        "max_abs_diff_any_channel": max(
            (v["max_abs_diff"] for v in report["channels"].values()), default=None
        ),
        "channels_with_any_pixel_difference": sorted(
            c for c, v in report["channels"].items()
            if v["n_frames_with_any_pixel_difference"] > 0
        ),
        "channels_with_byte_difference": sorted(
            c for c, v in report["channels"].items()
            if v["n_frames_with_byte_difference"] > 0
        ),
    }
    return report


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    args = {}
    for token in argv:
        key, _, value = token[2:].partition("=")
        args[key] = value
    report = compare_runs(args["a"], args["b"])
    if "out" in args:
        os.makedirs(os.path.dirname(os.path.abspath(args["out"])), exist_ok=True)
        with open(args["out"], "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    print("COMPARE " + json.dumps(report["verdict_inputs"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
