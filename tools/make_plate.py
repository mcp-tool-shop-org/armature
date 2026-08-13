#!/usr/bin/env python
r"""make_plate — turn a picked still into the plate that stands behind the performer.

    python tools\make_plate.py --frames=<lossless dir> --index=32 --width=1024 --height=576
           --out=<dir> --why="..." [--prompt-id=...] [--source-note="..."]
    python tools\make_plate.py --src=<photograph.png> --width=1024 --height=576
           --out=<dir> --why="..."

E12's commission. A scene-bearing start frame needs a picture of the world to composite the
authored RGBA over, and that picture is almost never already the generation's frame: a still
lifted from an earlier clip carries that clip's resolution and aspect, and a photograph
carries a camera's. This tool does the conversion **once**, writes it as an artifact with its
own hash, and records the transform — so the plate the model finally sees is a file somebody
can open and a derivation somebody can repeat, rather than a resize that happened inside a
render script and left no trace.

**Cover, never contain — and that is a rule, not a default.** `armature_core.startframe
.cover_fit` carries the reasoning; the short form is that the sibling fitter
(`fit_reference`) pads on purpose because its subject is an identity reference the Director
ruled must arrive whole, while a padded BACKDROP puts invented bands into the conditioning
image. This repo has that disease on file twice. So the overhang is cropped, and what was
cropped is in the provenance in both source and resized pixels.

**The plate is a DERIVED image and the record says so.** Source path and hash, derived path
and hash, the full transform, and the caller's stated reason all ride the sidecar. The
source is opened read-only and never written to.

Prints `MAKE_PLATE_OK`.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing a PNG and a JSON
under `outputs/`. Compensator: delete them; owner: the executor session.
"""

import argparse
import hashlib
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import startframe as SF  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "E12.1"


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=None,
                    help="a single image to use as the plate (argparse eats leading minus "
                         "signs: pass flags as --flag=value)")
    ap.add_argument("--frames", default=None,
                    help="a directory of NNNNN.png frames; use with --index")
    ap.add_argument("--index", type=int, default=None,
                    help="which frame of --frames to lift, by its own filename number")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--why", default=None,
                    help="one sentence, into the provenance, on why THIS plate. Required — "
                         "a backdrop nobody wrote down a reason for is a leftover")
    ap.add_argument("--prompt-id", default=None,
                    help="the generation the source frame came out of, when it came from one")
    ap.add_argument("--source-note", default=None,
                    help="free text about the source's own provenance, e.g. a photograph's "
                         "owner and date")
    ap.add_argument("--anchor", default="centre",
                    help="where the cover crop sits: top | centre | bottom, or a pair "
                         "x,y of fractions in 0..1. Only a band of the target frame is ever "
                         "visible behind the performer, so this decides which part of the "
                         "plate reaches the model at all - a recorded composite choice "
                         "under the alpha law, not a default to leave unstated")
    ap.add_argument("--visible-rows", default=None,
                    help="y0,y1 of the TARGET frame that a plate actually shows in; the "
                         "record then states which source rows land inside it")
    ap.add_argument("--band-carries", default=None,
                    help="one sentence, into the provenance, on what is actually inside "
                         "that band - the thing the anchor was chosen for")
    return ap.parse_args(argv)


#: Named anchors, as (x, y) fractions. Vertical only by name: a cover fit drops one axis,
#: and every plate this tool has met so far drops rows.
ANCHORS = {"top": (0.5, 0.0), "centre": (0.5, 0.5), "bottom": (0.5, 1.0)}


def parse_anchor(text):
    """`top|centre|bottom` or `x,y` -> a pair of fractions. No silent default."""
    if text in ANCHORS:
        return ANCHORS[text]
    parts = [p.strip() for p in str(text).split(",")]
    if len(parts) != 2:
        raise ArmatureError(
            f"--anchor must be one of {sorted(ANCHORS)} or a pair `x,y` of fractions in "
            f"0..1; got {text!r}")
    try:
        return tuple(float(p) for p in parts)
    except ValueError:
        raise ArmatureError(f"--anchor carries a non-number: {text!r}") from None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def resolve_source(src, frames, index):
    """The one source file, or a halt naming which half of the choice is missing.

    Two ways in because the spec allows two plate origins — a still from a clip we generated
    and own, or a photograph the Director owns. Neither is the default, and supplying both
    is a caller who has not decided.
    """
    if bool(src) == bool(frames):
        raise ArmatureError(
            "name exactly one source: --src=<image> for a picked file, or --frames=<dir> "
            "--index=N to lift a frame out of a clip")
    if src:
        if not os.path.isfile(src):
            raise ArmatureError(f"no such plate source: {src}")
        return os.path.abspath(src), {"kind": "file"}

    if index is None:
        raise ArmatureError("--frames needs --index: which frame of the clip is the plate")
    names = [n for n in os.listdir(frames)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    if not names:
        raise ArmatureError(f"no NNNNN.png frames in {frames}")
    by_number = {int(os.path.splitext(n)[0]): n for n in names}
    if index not in by_number:
        lo, hi = min(by_number), max(by_number)
        raise ArmatureError(
            f"frame {index} is not in {frames} (it holds {len(by_number)} frames, "
            f"{lo}..{hi}). A plate lifted from a frame that does not exist would silently "
            f"become whichever frame sorted nearest")
    path = os.path.abspath(os.path.join(frames, by_number[index]))
    return path, {"kind": "clip_frame", "frame_index": index,
                  "frames_dir": os.path.abspath(frames), "n_frames": len(by_number)}


def cover(img, width, height, anchor=(0.5, 0.5)):
    """Resize-then-crop `img` to exactly `width x height`. Returns (out, geometry).

    The geometry is `startframe.cover_fit`'s, computed before anything is resampled, so the
    numbers in the record are the numbers the pixels were actually put through.
    """
    h, w = img.shape[:2]
    geom = SF.cover_fit(w, h, width, height, anchor_x=anchor[0], anchor_y=anchor[1])
    nw, nh = geom["resized_size"]
    interp = cv2.INTER_AREA if geom["scale"] < 1.0 else cv2.INTER_CUBIC
    resized = cv2.resize(img, (nw, nh), interpolation=interp)
    x0, y0, x1, y1 = geom["crop_box"]
    out = resized[y0:y1, x0:x1]
    if out.shape[0] != height or out.shape[1] != width:
        raise ArmatureError(
            f"the cover crop produced {out.shape[1]}x{out.shape[0]}, not {width}x{height}; "
            f"geometry {geom}")
    return np.ascontiguousarray(out), dict(geom, interpolation=(
        "INTER_AREA" if geom["scale"] < 1.0 else "INTER_CUBIC"))


def main(argv=None):
    a = parse_args(argv)
    if not a.why or not a.why.strip():
        raise ArmatureError(
            "--why is required: the plate is the world this generation is conditioned on, "
            "and a choice nobody wrote down is indistinguishable from a leftover")

    src_path, origin = resolve_source(a.src, a.frames, a.index)
    out_dir = os.path.abspath(a.out)
    os.makedirs(out_dir, exist_ok=True)          # scripts create their own output directories

    img = cv2.imread(src_path, cv2.IMREAD_COLOR)
    if img is None:
        raise ArmatureError(f"cv2 could not read {src_path}")
    sh, sw = img.shape[:2]

    anchor = parse_anchor(a.anchor)
    fitted, geom = cover(img, a.width, a.height, anchor=anchor)
    dst = os.path.join(out_dir, "plate.png")
    if not cv2.imwrite(dst, fitted):
        raise ArmatureError(f"cv2 refused to write {dst}")

    band = None
    if a.visible_rows:
        vr = [int(v) for v in a.visible_rows.split(",")]
        if len(vr) != 2 or not (0 <= vr[0] < vr[1] <= a.height):
            raise ArmatureError(
                f"--visible-rows must be y0,y1 inside 0..{a.height}; got "
                f"{a.visible_rows!r}")
        band = {"target_rows": vr,
                "source_rows": SF.band_source_rows(vr, geom),
                "fraction_of_target_rows": (vr[1] - vr[0]) / float(a.height),
                "carries": a.band_carries or "NOT RECORDED",
                "note": ("the band is the whole of what this plate contributes: outside it "
                         "the authored master and its floor are opaque")}

    rec = {
        "tool": "make_plate", "tool_version": TOOL_VERSION,
        "why": a.why,
        "anchor": {"requested": a.anchor, "fractions": list(anchor),
                   "why_it_is_a_choice": (
                       "only the band shows, so the anchor decides which part of the plate "
                       "reaches the model at all - recorded under THE ALPHA LAW beside the "
                       "composite colour")},
        "visible_band": band,
        "source": dict(origin, path=src_path, sha256=_sha256(src_path),
                       size=[sw, sh], aspect=sw / sh,
                       prompt_id=a.prompt_id, note=a.source_note),
        "derived": {"path": dst, "sha256": _sha256(dst),
                    "size": [a.width, a.height], "aspect": a.width / a.height},
        "transform": geom,
        "law": ("cover, never contain — a padded backdrop puts invented bands into the "
                "conditioning image; see armature_core.startframe.cover_fit"),
    }
    rpath = os.path.join(out_dir, "plate_provenance.json")
    with open(rpath, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)

    print("MAKE_PLATE_OK " + json.dumps({
        "plate": dst, "sha256": rec["derived"]["sha256"][:32],
        "source": src_path, "source_size": [sw, sh],
        "size": [a.width, a.height], "scale": round(geom["scale"], 6),
        "anchor": list(anchor), "crop_offset": geom["crop_offset"],
        "dropped_px_resized": geom["dropped_px_resized"],
        "kept_fraction_of_source_area": round(geom["kept_fraction_of_source_area"], 6),
        "band_source_rows": ([round(v, 1) for v in band["source_rows"]] if band else None),
        "provenance": rpath}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
