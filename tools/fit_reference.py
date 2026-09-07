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

**The authored-RGBA law, carried at last (measured 2026-09-03).** The source was read with
`cv2.IMREAD_COLOR`, which returns 3-channel BGR and DROPS a 4th channel with no refusal and
no record — and `--pad=auto` then derived the letterbox pad from the median of the source's
outer border, which on an authored RGBA master is the RGB sitting UNDER alpha=0. Measured: a
128x256 RGBA master with alpha extrema (0, 255) over a hidden RGB of (128, 128, 128)
produced an RGB fit whose pad pixel was (128, 128, 128), recorded as
`"pad_source": "median of the source's own outer 4% border"` with the word `alpha` nowhere
in the provenance. `fit_reference` output is the reference image E08 and E10 both submitted,
and CLAUDE.md already names these pads as the standing suspect for E08's washed bands.

So the read is `IMREAD_UNCHANGED`, a 4-channel source refuses unless `--alpha-over=R,G,B`
names the plate (`composite_reference.compose_over_named_plate` — the one implementation,
shared with `encode_control`, `make_plate` and `pack_pose_pack`), and on such a source the
pad IS that plate: `--pad=auto`'s border sample is never taken from behind transparency. The
source's channel count, alpha extrema and composite choice ride the provenance beside
`pad_bgr`.

Compensator (NAMED_COMPENSATORS): writes a PNG and a JSON under `outputs/`. Compensator:
delete them; owner: the executor session. The source is opened read-only.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encode_control import runtime_provenance  # noqa: E402

from armature_core.errors import ArmatureError  # noqa: E402
from armature_core.gates import (  # noqa: E402
    GENERATOR_PROFILES, g1_generator_legality, resolve_generator)
from composite_reference import (  # noqa: E402
    compose_over_named_plate, parse_plate)

TOOL_VERSION = "E08.2"



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

class FitReferenceError(ArmatureError):
    """The fit cannot be made honestly — the alpha law, or a degenerate source."""

#: How wide a border strip `--pad=auto` reads, as a fraction of the shorter side. A fraction
#: of the image's own size rather than a pixel count, so it does not encode this one asset.
BORDER_FRAC = 0.04


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="letterbox a reference image into a generator's frame without losing "
                    "the figure, and record the derivation",
        epilog=HALT_EPILOG)
    ap.add_argument("--src", required=True,
                    help="the reference master to fit; read RGBA, never written to")
    ap.add_argument("--out", required=True,
                    help="directory for the fitted image and its provenance JSON")
    # WAVE 28 (F-01f7eda9): these two decide the pixel size of the image a paid run
    # SUBMITS and carried no help at all, in a parser whose `--pad` and `--alpha-over`
    # carry two of the best help strings in the domain. CLAUDE.md's generator-legality
    # rule — every video model constrains resolution and frame count, and the constraint
    # is recorded per model in the spec that first uses it — reached the operator nowhere
    # in this tool, and the defaults are E08-era literals with no note of the route they
    # came from. The legality table itself is `armature_core.gates.GENERATOR_PROFILES`,
    # enforced by `gates.g1_generator_legality`; naming it here is what points an operator
    # fitting for a different route at the rule their route is actually held to.
    ap.add_argument("--width", type=int, default=832,
                    help="frame width in pixels. The default 832 is E08's WanAnimate frame "
                         "(832x480), not a universal legal size: every video model "
                         "constrains resolution, and the per-model rule this repo holds is "
                         "armature_core.gates.GENERATOR_PROFILES (wan-vace and "
                         "wan-fun-control both require width and height divisible by 16), "
                         "enforced by gates.g1_generator_legality. Fitting for another "
                         "route means reading that route's row in the spec that introduced "
                         "it")
    ap.add_argument("--height", type=int, default=480,
                    help="frame height in pixels. The default 480 is the other half of "
                         "E08's 832x480 WanAnimate frame; see --width for the per-model "
                         "legality table these two are checked against")
    # F-c3572bf5: without --route this tool happily wrote an illegal plate that Gate G1
    # only refused later at control export / payload build. When set, G1 runs HERE.
    ap.add_argument("--route", default=None, choices=sorted(GENERATOR_PROFILES),
                    help="generator profile to hold the fit against via "
                         "gates.g1_generator_legality before writing. Omitted, bare "
                         "--width/--height stay exploratory and ungated (F-c3572bf5)")
    ap.add_argument("--length", type=int, default=None,
                    help="frame count checked with --route. Omitted under --route, the "
                         "profile's frame_residue is used as a legal placeholder so a "
                         "reference fit that does not author a clip still exercises G1 "
                         "on width/height (F-c3572bf5)")
    ap.add_argument("--mode", default="letterbox", choices=("letterbox",),
                    help="how the source is fitted. Only 'letterbox' exists, and that is "
                         "the Director's 2026-08-12 ruling: the node's own centre-crop "
                         "handed the model 19.9 percent of the figure and no face")
    ap.add_argument("--pad", default="auto",
                    help="'auto' samples the source's own border; or R,G,B (argparse eats "
                         "leading minus signs, so pass flags as --flag=value). On an RGBA "
                         "source 'auto' resolves to the --alpha-over plate, never to the "
                         "border behind the alpha")
    ap.add_argument("--alpha-over", default=None,
                    help="R,G,B of the plate an RGBA source is composited over. Without "
                         "it an alpha channel is a refusal, not a silent drop")
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
        raise FitReferenceError(
            f"degenerate source image of shape {img.shape}",
            {"gate": "SOURCE", "andon": "FitReferenceError",
             "clause": "source_image_has_a_zero_dimension",
             "shape": [int(v) for v in img.shape]})
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

    # UNCHANGED, not COLOR: a 4th channel must reach the law below rather than being
    # dropped by the decoder before anything can refuse it.
    raw = cv2.imread(a.src, cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise FitReferenceError(
            f"cv2 could not read {a.src}",
            {"gate": "READ", "andon": "FitReferenceError",
             "clause": "cv2_could_not_read_the_source", "flag": "--src",
             "src": os.path.abspath(a.src)})
    if raw.ndim == 2:
        raw = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
    plate_bgr = None
    plate_rgb = parse_plate(a.alpha_over, FitReferenceError)
    if plate_rgb is not None:
        plate_bgr = tuple(plate_rgb[::-1])       # the caller says RGB; cv2 arrays are BGR
    # ---- ANDON. One implementation of the authored-RGBA law, shared with encode_control,
    #      make_plate and pack_pose_pack.
    img, alpha_record = compose_over_named_plate(
        raw, plate_bgr, label=os.path.abspath(a.src), exc=FitReferenceError,
        extra_evidence={"src": os.path.abspath(a.src), "tool": "fit_reference"},
        channel_order="BGR")
    h, w = img.shape[:2]

    if a.pad == "auto" and alpha_record["alpha_present"]:
        # The border `auto` would sample is, on an authored master, precisely the part the
        # author made invisible. The pad is the plate the composite was already made over.
        pad = plate_bgr
        pad_source = (f"the named plate --alpha-over={','.join(str(v) for v in plate_rgb)}; "
                      f"the source is RGBA and its border is what alpha hides")
    elif a.pad == "auto":
        pad = border_colour(img)
        pad_source = f"median of the source's own outer {BORDER_FRAC:.0%} border"
    else:
        # ---- F-3092e646, wave 22: this was `parts = [int(v) for v in a.pad.split(",")]`
        #      with the cast ABOVE the length check and no 0-255 range check, eleven lines
        #      below `--alpha-over`, which goes through the ONE parser and gets a typed
        #      refusal with an evidence dict for exactly this class of value. Measured on
        #      `e8263a3` through the real CLI on an RGB source: `--pad=a,b,c` exited 1 with
        #      an untyped `ValueError: invalid literal for int() with base 10: 'a'`;
        #      `--pad=999,-5,0` exited 1 with an untyped
        #      `OverflowError: Python integer -5 out of bounds for uint8`, raised from
        #      `letterbox`'s `out[:] = np.array(pad, dtype=img.dtype)` on numpy 2.5.2. Both
        #      refuse above `os.makedirs`, so nothing was stranded — the defect is that a
        #      refusal on the PAID path read as a crash: exit 1, no `FIT_REFERENCE` line,
        #      and none of the flag, the value or a clause in a machine-readable field.
        #      On a numpy that WRAPS instead of raising, the same input letterboxes in a
        #      colour the record does not name: the provenance writes
        #      `pad_bgr=[int(v) for v in pad]` from this tuple, which is the exact defect
        #      `composite_reference`'s own comment records as fixed THERE (`--plate=999,-5,0`
        #      clipped to [255,0,0] while the record said [999,-5,0]).
        parts = list(parse_plate(a.pad, FitReferenceError, flag="--pad"))
        pad = tuple(parts[::-1])          # the caller says RGB; cv2 arrays are BGR
        pad_source = f"caller-supplied RGB {parts}"

    # F-c3572bf5: when --route is set, G1 fires BEFORE the write so an illegal plate
    # never lands with provenance claiming a finished fit.
    route_record = None
    if a.route:
        profile = resolve_generator(a.route)
        length = a.length if a.length is not None else int(profile.frame_residue)
        length_source = ("caller" if a.length is not None
                         else "frame_residue_placeholder")
        g1_generator_legality(a.width, a.height, length, a.route)
        route_record = {
            "route": a.route,
            "profile": profile.as_dict(),
            "profile_source": profile.source,
            "length_checked": length,
            "length_source": length_source,
            "g1": "checked",
        }

    fitted, placement = letterbox(img, a.width, a.height, pad)
    stem = os.path.splitext(os.path.basename(a.src))[0]
    # ---- the output directory is created only once every in-tool andon above has
    #      fired. A refused run that has already made its directory leaves an empty
    #      one behind, which a later reader -- or a re-run into the same --out --
    #      reads as an attempt that produced nothing rather than one that was refused.
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, f"{stem}_fit_{a.width}x{a.height}.png")
    if not cv2.imwrite(dst, fitted):
        raise FitReferenceError(
            f"cv2 refused to write {dst}",
            {"gate": "WRITE", "andon": "FitReferenceError",
             "clause": "cv2_refused_the_write", "dst": os.path.abspath(dst),
             "out": out_dir})

    rec = {
        "tool": "fit_reference", "tool_version": TOOL_VERSION, "mode": a.mode,
        "source": dict({"path": os.path.abspath(a.src), "sha256": _sha256(a.src),
                        "size": [w, h], "aspect": w / h}, **alpha_record),
        "derived": {"path": dst, "sha256": _sha256(dst), "size": [a.width, a.height],
                    "aspect": a.width / a.height},
        "transform": dict(placement, pad_bgr=[int(v) for v in pad], pad_source=pad_source,
                          alpha_disposition=alpha_record["alpha_disposition"],
                          note=("contain-fit: scale = min(width/w, height/h); nothing is "
                                "cropped, every source pixel survives")),
        "what_the_node_would_have_done_instead": node_crop_that_this_avoids(
            w, h, a.width, a.height),
        "ruling": ("the Director ruled letterbox on 2026-08-12, after the center-crop's "
                   "consequence was measured and shown: the whole figure reaches the model "
                   "and the cost is flat margin rather than a missing head"),
    }
    if route_record is not None:
        rec["generator_route"] = route_record
    rpath = os.path.join(out_dir, f"{stem}_fit_provenance.json")
    with open(rpath, "w", encoding="utf-8") as fh:
        rec.update(runtime_provenance())
        json.dump(rec, fh, indent=2)

    print("FIT_REFERENCE_OK " + json.dumps({
        "out": dst, "sha256": rec["derived"]["sha256"][:32],
        "figure_fraction": round(placement["figure_fraction_of_frame"], 4),
        "node_would_have_kept": rec["what_the_node_would_have_done_instead"][
            "kept_fraction_of_source_height"],
        "provenance": rpath}))
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "FIT_REFERENCE")
