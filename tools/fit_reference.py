#!/usr/bin/env python
"""fit_reference — put a reference image into a generator's frame without losing the figure.

    python tools\\fit_reference.py --src=<twin.png> --out=<dir> --width=832 --height=480
                                   [--mode=letterbox] [--pad=auto]

**Why this exists, measured 2026-08-12.** `WanAnimateToVideo` does not letterbox its
`reference_image`; it calls `comfy.utils.common_upscale(..., "area", "center")`, which
crops the longer axis symmetrically and then resizes. Read from the core source, and the
consequence for E08's reference is arithmetic: the Director-approved twin is 352x1024
(aspect 0.344) and the frame is 832x480 (aspect 1.733), so the node keeps

    y = round((1024 - 1024 * (0.344 / 1.733)) / 2) = 410

and hands the model rows 410..613 — **204 of 1024 rows, 19.9% of the figure**. That band is
the hips and thighs. No head, no face, no hands. An identity reference with no face in it is
not an identity reference, and nothing in the chain errors: the node resizes cleanly, the
graph validates, the run completes.

**The Director ruled letterbox** (2026-08-12), so the whole figure reaches the model and the
cost is flat margin rather than a missing head.

**This is a DERIVED image and the record says so.** The source hash and the derived hash both
ride the provenance, the transform is stated in full, and the source file is never written
to. A reference set is meant to be locked and reused verbatim across shots (G14), so the
derivation belongs in a tool that reproduces it byte-for-byte rather than in a session.

`--pad=auto` samples the source's own border, so the margin matches the plate the figure was
photographed against instead of introducing a colour the model has to interpret. A black pad
would read as scene content; a colour picked by eye would be a global constant governing a
local feature.

Compensator (NAMED_COMPENSATORS): writes a PNG and a JSON under `outputs/`. Compensator:
delete them; owner: the executor session. The source is opened read-only.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "E08.1"

#: How wide a border strip `--pad=auto` reads, as a fraction of the shorter side. A fraction
#: of the image's own size rather than a pixel count, so it does not encode this one asset.
BORDER_FRAC = 0.04


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--mode", default="letterbox", choices=("letterbox",))
    ap.add_argument("--pad", default="auto",
                    help="'auto' samples the source's own border; or R,G,B (argparse eats "
                         "leading minus signs, so pass flags as --flag=value)")
    return ap.parse_args(argv)


def border_colour(img, frac=BORDER_FRAC):
    """The median colour of the source's own outer border, as an RGB triple.

    Median rather than mean: a figure that touches an edge would drag a mean toward its own
    colour, and the point is to match the PLATE. Sampled from all four edges so a vignette
    on one side does not decide it alone.
    """
    h, w = img.shape[:2]
    t = max(1, int(round(min(h, w) * frac)))
    strips = [img[:t], img[-t:], img[:, :t].reshape(-1, img.shape[2])[None],
              img[:, -t:].reshape(-1, img.shape[2])[None]]
    px = np.concatenate([s.reshape(-1, img.shape[2]) for s in strips], axis=0)
    return tuple(int(v) for v in np.median(px, axis=0))


def letterbox(img, width, height, pad):
    """Scale to fit INSIDE the frame and centre on a pad of `pad`. Nothing is cropped.

    Returns (out, placement). The scale is `min(width/w, height/h)` — the "contain" fit — so
    every source pixel survives; `common_upscale`'s "center" crop is the "cover" fit, which
    is what discards 80% of a portrait figure in a landscape frame.
    """
    import cv2

    h, w = img.shape[:2]
    if h <= 0 or w <= 0:
        raise ArmatureError(f"degenerate source image of shape {img.shape}")
    s = min(width / w, height / h)
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_CUBIC
    fit = cv2.resize(img, (nw, nh), interpolation=interp)
    out = np.empty((height, width, img.shape[2]), dtype=img.dtype)
    out[:] = np.array(pad, dtype=img.dtype)
    ox, oy = (width - nw) // 2, (height - nh) // 2
    out[oy:oy + nh, ox:ox + nw] = fit
    covered = (nw * nh) / float(width * height)
    return out, {"scale": s, "fitted_size": [nw, nh], "offset": [ox, oy],
                 "figure_fraction_of_frame": covered,
                 "margin_fraction_of_frame": 1.0 - covered}


def node_crop_that_this_avoids(w, h, width, height):
    """What `common_upscale(..., 'center')` would have kept. Reported, not performed.

    Recorded in the provenance so the report can state the alternative in numbers instead of
    in prose, and so a later reader can see why the derivation was made at all.
    """
    old_aspect, new_aspect = w / h, width / height
    x = y = 0
    if old_aspect > new_aspect:
        x = round((w - w * (new_aspect / old_aspect)) / 2)
    elif old_aspect < new_aspect:
        y = round((h - h * (old_aspect / new_aspect)) / 2)
    kw, kh = w - 2 * x, h - 2 * y
    return {"crop_x": x, "crop_y": y, "kept_size": [kw, kh],
            "kept_fraction_of_source_area": (kw * kh) / float(w * h),
            "kept_fraction_of_source_height": kh / float(h),
            "source": ("comfy/utils.py::common_upscale, crop='center', fetched 2026-08-12")}


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main(argv=None):
    a = parse_args(argv)
    import cv2

    out_dir = os.path.abspath(a.out)
    os.makedirs(out_dir, exist_ok=True)

    img = cv2.imread(a.src, cv2.IMREAD_COLOR)
    if img is None:
        raise ArmatureError(f"cv2 could not read {a.src}")
    h, w = img.shape[:2]

    if a.pad == "auto":
        pad = border_colour(img)
        pad_source = f"median of the source's own outer {BORDER_FRAC:.0%} border"
    else:
        parts = [int(v) for v in a.pad.split(",")]
        if len(parts) != 3:
            raise ArmatureError(f"--pad must be 'auto' or R,G,B; got {a.pad!r}")
        pad = tuple(parts[::-1])          # the caller says RGB; cv2 arrays are BGR
        pad_source = f"caller-supplied RGB {parts}"

    fitted, placement = letterbox(img, a.width, a.height, pad)
    stem = os.path.splitext(os.path.basename(a.src))[0]
    dst = os.path.join(out_dir, f"{stem}_fit_{a.width}x{a.height}.png")
    if not cv2.imwrite(dst, fitted):
        raise ArmatureError(f"cv2 refused to write {dst}")

    rec = {
        "tool": "fit_reference", "tool_version": TOOL_VERSION, "mode": a.mode,
        "source": {"path": os.path.abspath(a.src), "sha256": _sha256(a.src),
                   "size": [w, h], "aspect": w / h},
        "derived": {"path": dst, "sha256": _sha256(dst), "size": [a.width, a.height],
                    "aspect": a.width / a.height},
        "transform": dict(placement, pad_bgr=[int(v) for v in pad], pad_source=pad_source,
                          note=("contain-fit: scale = min(width/w, height/h); nothing is "
                                "cropped, every source pixel survives")),
        "what_the_node_would_have_done_instead": node_crop_that_this_avoids(
            w, h, a.width, a.height),
        "ruling": ("the Director ruled letterbox on 2026-08-12, after the center-crop's "
                   "consequence was measured and shown: the whole figure reaches the model "
                   "and the cost is flat margin rather than a missing head"),
    }
    rpath = os.path.join(out_dir, f"{stem}_fit_provenance.json")
    with open(rpath, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)

    print("FIT_REFERENCE_OK " + json.dumps({
        "out": dst, "sha256": rec["derived"]["sha256"][:32],
        "figure_fraction": round(placement["figure_fraction_of_frame"], 4),
        "node_would_have_kept": rec["what_the_node_would_have_done_instead"][
            "kept_fraction_of_source_height"],
        "provenance": rpath}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
