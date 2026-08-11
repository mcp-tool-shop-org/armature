#!/usr/bin/env python
"""invert_frames — write the near-dark polarity of a rendered control channel.

    python tools/invert_frames.py --frames=<src dir> --out=<dst dir> [--expect=33]

E02's A1b is **one operation on A1a**: full-image `255 - x` on the same geometry, the
same normalisation and the same frames. The video bridge could do this in memory
(`encode_control.load_frames(invert=True)`), but that bridge is dead — the PNG-batch
bridge uploads *files*, so the inverted polarity has to exist on disk. This tool is the
recorded, re-runnable step that puts it there rather than an inline transform that leaves
no receipt.

**Why the plain inversion is also the semantically correct near-dark map.** The exporter
writes background as 0 and near-bright depth over it, so black already means "far". After
`255 - x` the background is 255 and near is 0 — which in the near-dark convention still
reads "far". The two arms therefore differ by exactly one transform and by nothing else.

**What raises, and why those directions.** Inverting a uint8 image is an involution and
cannot fail, so nothing checks it — a check that cannot fail is not a check. What *can*
fail is inverting the wrong kind of array: a 16-bit depth PNG (`255 - 40000` is nonsense),
or an image carrying alpha (inverting opacity is not a polarity flip), or a palette image
(inverting an index is not inverting a value). Those are the unbounded directions, and
they are what `_read_u8_gray` raises on.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import pngio  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402


class InvertError(ArmatureError):
    """The source frames are not the kind of image this transform is defined for."""


def _read_u8_gray(path):
    """Read one control frame as a 2-D uint8 array, or raise saying which way it is wrong."""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "PA"):
        raise InvertError(
            f"{path}: mode {im.mode!r} carries alpha; `255 - x` over an alpha channel "
            f"inverts opacity, not polarity"
        )
    if im.mode == "P":
        raise InvertError(
            f"{path}: mode 'P' is palette-indexed; inverting an index is not inverting "
            f"a value"
        )
    arr = np.array(im)
    if arr.dtype != np.uint8:
        raise InvertError(
            f"{path}: dtype {arr.dtype}; `255 - x` is the polarity flip only for 8-bit data"
        )
    if arr.ndim == 3:
        if arr.shape[2] != 3 or not (arr[..., 0] == arr[..., 1]).all() \
                or not (arr[..., 1] == arr[..., 2]).all():
            raise InvertError(
                f"{path}: 3-channel and not R=G=B; this tool inverts a grayscale channel"
            )
        arr = arr[..., 0]
    elif arr.ndim != 2:
        raise InvertError(f"{path}: unsupported array shape {arr.shape}")
    return np.ascontiguousarray(arr)


def invert_dir(src, dst, expect=None):
    """Write `255 - x` of every PNG in `src` into `dst`. Returns the receipt dict."""
    names = sorted(n for n in os.listdir(src) if n.lower().endswith(".png"))
    if not names:
        raise InvertError(f"no PNG frames in {src}; there is nothing to invert")
    if expect is not None and len(names) != expect:
        raise InvertError(
            f"{src} holds {len(names)} frames, expected {expect}; a short control "
            f"directory becomes a short batch with no error anywhere downstream"
        )

    os.makedirs(dst, exist_ok=True)  # scripts create their own output directories
    src_h, dst_h = hashlib.sha256(), hashlib.sha256()
    stats, shape = [], None
    for n in names:
        a = _read_u8_gray(os.path.join(src, n))
        if shape is None:
            shape = a.shape
        b = (255 - a).astype(np.uint8)
        src_h.update(a.tobytes())
        dst_h.update(b.tobytes())
        pngio.write_png(os.path.join(dst, n), b, bit_depth=8)
        stats.append({
            "frame": n,
            "src_min": int(a.min()), "src_max": int(a.max()),
            "out_min": int(b.min()), "out_max": int(b.max()),
            "src_modal": int(np.bincount(a.ravel(), minlength=256).argmax()),
            "out_modal": int(np.bincount(b.ravel(), minlength=256).argmax()),
        })

    return {
        "tool": "invert_frames",
        "transform": "255 - x, full image, 8-bit",
        "src": os.path.abspath(src),
        "dst": os.path.abspath(dst),
        "n_frames": len(names),
        "frame_names": names,
        "resolution": [int(shape[1]), int(shape[0])],
        "src_pixels_sha256": src_h.hexdigest(),
        "out_pixels_sha256": dst_h.hexdigest(),
        "per_frame": stats,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect", type=int, default=None)
    a = ap.parse_args(argv)

    receipt = invert_dir(a.frames, a.out, expect=a.expect)
    with open(a.out.rstrip("/\\") + ".receipt.json", "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2)
    print("INVERT_FRAMES " + json.dumps({
        "out": receipt["dst"],
        "n_frames": receipt["n_frames"],
        "resolution": receipt["resolution"],
        "src_pixels_sha256": receipt["src_pixels_sha256"][:16],
        "out_pixels_sha256": receipt["out_pixels_sha256"][:16],
        "src_modal_f0": receipt["per_frame"][0]["src_modal"],
        "out_modal_f0": receipt["per_frame"][0]["out_modal"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
