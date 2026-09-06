#!/usr/bin/env python
"""invert_frames — write the near-dark polarity of a rendered control channel.

    <venv-python> tools/invert_frames.py --frames=<src dir> --out=<dst dir> [--expect=33]

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
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encode_control import runtime_provenance  # noqa: E402

from armature_core import pngio, shotspec  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

class InvertError(ArmatureError):
    """The source frames are not the kind of image this transform is defined for.

    Carries an evidence dict, like every other refusal in this repo: the measurement
    that fired it is the useful half.

    **WAVE 25 (F-b2c7b15a): it declares its gate id**, for `EncodeFailure`'s reason —
    `run_tool_main` reads `getattr(exc, "gate", None)`, so a class with no class-level
    `gate` prints `"gate": null` wherever the raise site's own dict does not carry one, and
    the three population refusals below carried none. This is the same shape on the
    INVERTED control sequence that `encode_control` is on the control video.
    """

    gate = "INVERT"


def frame_population(src, expect=None):
    """The NUMBERED frames of `src`, in index order, and a refusal for anything else.

    The twin of `encode_control.frame_population`, and it exists for the same measured
    reason: `render_pose_sticks` writes a `strip_every{N}.png` contact sheet into the
    directory it just filled with `NNNNN.png` frames, so a bare `*.png` listing sorts
    the stray last and inverts it as if it were the final frame of the shot. The
    receipt then names it as a frame, and `--expect` counts it toward the declared
    length. `gate_b_frames.frame_paths` caught this class on 2026-08-12 and filtered;
    a filter is right for a diagnostic and wrong here, because these files become an
    upload — so a PNG the numbering cannot name raises and is carried as evidence.

    `expect` pins the population to `shotspec.frame_names`, the spec's own names,
    rather than to a length any five files would satisfy.
    """
    if not os.path.isdir(src):
        raise InvertError(f"{src} is not a directory of frames",
                          {"gate": "FRAMES", "andon": "InvertError",
                           "clause": "frames_dir_is_not_a_directory", "src": src})
    pngs = sorted(n for n in os.listdir(src) if n.lower().endswith(".png"))
    numbered = [n for n in pngs if os.path.splitext(n)[0].isdigit()]
    unexpected = [n for n in pngs if n not in set(numbered)]
    names = sorted(numbered, key=lambda n: int(os.path.splitext(n)[0]))
    if unexpected:
        raise InvertError(
            f"{src} holds {len(unexpected)} PNG(s) that are not numbered frames "
            f"({', '.join(unexpected[:8])}); inverting one produces an extra frame that "
            f"the receipt then names as part of the shot",
            {"gate": "FRAMES", "andon": "InvertError",
             "clause": "stray_png_in_the_frame_population",
             "src": src, "unexpected": unexpected, "frames": names},
        )
    if not names:
        raise InvertError(
            f"no NNNNN.png frames in {src}; there is nothing to invert",
            {"gate": "FRAMES", "andon": "InvertError",
             "clause": "no_numbered_frames_to_invert",
             "src": src, "png_files": pngs},
        )
    if expect is not None:
        want = shotspec.frame_names(expect, "png")
        if names != want:
            raise InvertError(
                f"{src} holds {len(names)} frames, expected {expect} named as the spec "
                f"names them; a short or renumbered control directory becomes a short "
                f"batch with no error anywhere downstream",
                {"gate": "FRAMES", "andon": "InvertError",
                 "clause": "population_is_not_the_spec_names",
                 "src": src, "found": names, "expected": want,
                 "missing": [n for n in want if n not in set(names)],
                 "unexpected": [n for n in names if n not in set(want)]},
            )
    return names


def _read_u8_gray(path):
    """Read one control frame as a 2-D uint8 array, or raise saying which way it is wrong."""
    im = Image.open(path)
    # Every refusal below carries the measurement that fired it. `InvertError`'s own class
    # docstring says it does — "Carries an evidence dict, like every other refusal in this
    # repo" — and these five each called it with the message alone, so `e.evidence` was
    # `{}` on all of them while `frame_population`'s three in the same file carried one.
    # The first of them is the alpha-law refusal, the one that refuses inverting opacity:
    # a halt on a control directory reached the run record with nothing machine-readable
    # behind it.
    if im.mode in ("RGBA", "LA", "PA"):
        raise InvertError(
            f"{path}: mode {im.mode!r} carries alpha; `255 - x` over an alpha channel "
            f"inverts opacity, not polarity",
            {"gate": "READ", "andon": "InvertError",
             "clause": "frame_carries_an_alpha_channel",
             "path": path, "mode": im.mode},
        )
    if im.mode == "P":
        raise InvertError(
            f"{path}: mode 'P' is palette-indexed; inverting an index is not inverting "
            f"a value",
            {"gate": "READ", "andon": "InvertError",
             "clause": "frame_is_palette_indexed",
             "path": path, "mode": im.mode},
        )
    arr = np.array(im)
    if arr.dtype != np.uint8:
        raise InvertError(
            f"{path}: dtype {arr.dtype}; `255 - x` is the polarity flip only for 8-bit data",
            {"gate": "READ", "andon": "InvertError",
             "clause": "frame_is_not_eight_bit",
             "path": path, "mode": im.mode, "dtype": str(arr.dtype),
             "shape": [int(v) for v in arr.shape]},
        )
    if arr.ndim == 3:
        if arr.shape[2] != 3 or not (arr[..., 0] == arr[..., 1]).all() \
                or not (arr[..., 1] == arr[..., 2]).all():
            raise InvertError(
                f"{path}: 3-channel and not R=G=B; this tool inverts a grayscale channel",
                {"gate": "READ", "andon": "InvertError",
                 "clause": "frame_is_colour_not_grayscale",
                 "path": path, "mode": im.mode, "dtype": str(arr.dtype),
                 "shape": [int(v) for v in arr.shape]},
            )
        arr = arr[..., 0]
    elif arr.ndim != 2:
        raise InvertError(f"{path}: unsupported array shape {arr.shape}",
                          {"gate": "READ", "andon": "InvertError",
                           "clause": "frame_array_shape_is_unsupported",
                           "path": path, "mode": im.mode, "dtype": str(arr.dtype),
                           "shape": [int(v) for v in arr.shape]})
    return np.ascontiguousarray(arr)


def gate_out_directory(dst):
    """ANDON — `--out` is not a directory that already holds a control population.

    F-7f59629f's second half, wave 22. Re-running into a re-used `--out` was measured on
    `e8263a3`: a first clean run wrote 4 inverted frames and `<out>.receipt.json`; a second,
    REFUSED run (frame 2 RGBA) overwrote frames 0-1 and left 2-3 from the first. The
    directory then read as a complete, spec-length control sequence to every consumer —
    `encode_control.frame_population(<dir>, expect=4)` returned all four names, no stray, no
    short-population refusal — while its four frames came from two different arms (measured
    modal bytes 215, 214 from the refused run beside 53, 52 from the prior one), and the
    FIRST run's receipt was still on disk asserting `n_frames: 4` and an
    `out_pixels_sha256` that no longer described the directory (recorded
    `bc81b9fe7203fe0f12df00c8...`, recomputed over the four files
    `956a0478ec9e0fb8d6fd9f90...`). Gate R compares the frames a tool loaded against their
    own decode and is blind to which RUN wrote them.

    The shape is `make_review_clip.gate_out_directory`'s, one tool over.
    """
    dst_abs = os.path.abspath(dst)
    ev = {"gate": "OUT", "andon": "InvertError", "out": dst_abs,
          "convention": "an inverted control sequence is written into a directory of its own"}
    if os.path.isdir(dst_abs):
        numbered = sorted(n for n in os.listdir(dst_abs)
                          if n.lower().endswith(".png")
                          and os.path.splitext(n)[0].isdigit())
        if numbered:
            raise InvertError(
                f"--out {dst_abs} already holds {len(numbered)} numbered frame(s); a run "
                f"refused part-way through would leave a directory whose frames come from "
                f"two different arms, and every count, every stray check and Gate R stay "
                f"green on it",
                dict(ev, clause="out_directory_already_holds_frames",
                     numbered_frames=numbered[:16], n_numbered=len(numbered)))
    ev["verdict"] = "an inverted-control directory of its own"
    return ev


def invert_dir(src, dst, expect=None):
    """Write `255 - x` of every PNG in `src` into `dst`. Returns the receipt dict.

    **Every frame is READ AND ACCEPTED before the first byte is written.** F-7f59629f, wave
    22. `os.makedirs(dst)` used to sit above the loop and each frame was written inside it,
    while `_read_u8_gray` can refuse frame i+1 on four clauses (alpha, palette, non-uint8,
    3-channel-not-R=G=B). A mid-loop refusal therefore left a PARTIAL control directory on
    disk with no receipt and no marker. Measured on `e8263a3` through the real CLI on a
    4-frame source whose frame 2 is RGBA: exit 1, stdout empty, and `--out` holding
    `00000.png` and `00001.png`.

    The read pass is repeated rather than kept, for the reason `render_pose_sticks` records
    for its own draw: holding n arrays costs `n * h * w` bytes and a long control sequence
    is exactly when this tool is used, while `_read_u8_gray` is pure, so the second pass
    reads the same bytes. The cost is one extra decode per frame; the property bought is
    that `--out` does not exist at all unless every frame was accepted.

    The ratchet that exists to catch this could not see the tool: measured with
    `tests/_census_nodes.refusal_and_write_lines`, `invert_frames` returned `gates={}` —
    all five refusals sit two hops below `main` (`main` -> `invert_dir` ->
    `frame_population` / `_read_u8_gray`) and the per-frame write is `pngio.write_png`,
    neither of the two spellings that census recognises. Keying it on behaviour is the
    tests domain's half and is named in the seams inbox.
    """
    names = frame_population(src, expect=expect)

    # ---- ANDON, before `os.makedirs`: the destination is not a used control directory.
    gate_out_directory(dst)

    # ---- READ PASS. Every one of `_read_u8_gray`'s four clauses fires here, above the
    #      first write, so a refused run leaves `--out` absent rather than partial.
    for n in names:
        _read_u8_gray(os.path.join(src, n))

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
    ap = argparse.ArgumentParser(
        description="write the near-dark polarity of a rendered control channel, with a "
                    "receipt naming every frame it inverted",
        epilog=HALT_EPILOG)
    ap.add_argument("--frames", required=True,
                    help="the source channel directory of NNNNN.png frames, read only")
    ap.add_argument("--out", required=True,
                    help="directory for the inverted frames; its receipt is written beside "
                         "it as <out>.receipt.json")
    ap.add_argument("--expect", type=int, default=None,
                    help="the frame count the spec declares; the directory's numbered "
                         "frames must be exactly shotspec.frame_names(expect, 'png')")
    a = ap.parse_args(argv)

    receipt = invert_dir(a.frames, a.out, expect=a.expect)
    with open(a.out.rstrip("/\\") + ".receipt.json", "w", encoding="utf-8") as fh:
        receipt.update(runtime_provenance())
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
    # WAVE 22, SEAM 1 (F-7f59629f's second half): the ONE `__main__` halt handler, adopted
    # BY IMPORT. This module produces a control sequence that is encoded and uploaded, and
    # every one of its refusals — the four `_read_u8_gray` clauses, the population clause
    # and the new `out_directory_already_holds_frames` — exited 1 with stdout empty, which
    # is "the environment broke, retry" to a chain routing on exit codes.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "INVERT_FRAMES")
