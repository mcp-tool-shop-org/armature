#!/usr/bin/env python
r"""make_pick_sheet — Gate PLATE's instrument: candidate plates, side by side, for the eye.

    python tools\make_pick_sheet.py --frames=<lossless dir> --at=12,20,24,30,38,57
           --target=1024x576 --visible-rows=0,182 --out=<sheet.png> [--scale=0.6]

Gate PLATE is a human gate: which picture of a world this generation is conditioned on is
the Director's call, and it blocks all spend until he makes it. This tool builds the thing
he makes it from.

**Every label is derived from the frames themselves.** Nothing here is typed in and nothing
is a literal — the same rule `make_startframe_sheet` was split out to enforce, for the same
reason: *a tool that names an experiment in a literal is a tool that will lie the first time
it is reused.* A value the inputs do not carry prints `NOT RECORDED` rather than a plausible
default.

**The two geometry facts the pick turns on, drawn rather than described.** A candidate lifted
from one generation is rarely the frame of the next, so a cover fit crops it (see
`armature_core.startframe.cover_fit`); and only the part of the target frame the authored
master leaves transparent will show the plate at all. Both are marked on every tile and
printed in rows, in the candidate's OWN pixel coordinates, because a Director choosing
between six pictures should not have to do the arithmetic to know which parts of them
survive.

Sheets locate; full size decides. Tiles are the frames' own pixels at one printed scale.

Compensator (NAMED_COMPENSATORS): writes one PNG and one JSON. Compensator: delete them;
owner: the executor session. Inputs are opened read-only.
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import startframe as SF  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "E12.1"

MARGIN = 10
LABEL_H = 16
HDR_H = 26
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (140, 140, 150)
CROP_INK = (255, 96, 96)
BAND_INK = (96, 220, 255)
MISSING = "NOT RECORDED"


def sharpness(gray):
    """Variance of a discrete Laplacian — the standard focus measure.

    Reported, never ranked across brightness levels: the operator is a second difference of
    intensity, so halving a frame's contrast quarters this number without anything going out
    of focus. The clip this was built for darkens by a factor of five from end to end, which
    is exactly the case where a naive ranking would call the dark half blurry. The sheet
    prints luma beside it so the reader can see when that is happening.
    """
    a = gray.astype(np.float64)
    lap = (-4.0 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:])
    return float(lap.var())


def motion(gray, prev_gray):
    """Mean absolute difference from the previous frame — the motion-blur proxy.

    None when there is no previous frame, which prints as `NOT RECORDED`: frame 0 of a clip
    has no predecessor, and a zero there would read as the stillest frame in the run.
    """
    if prev_gray is None:
        return None
    if gray.shape != prev_gray.shape:
        raise ArmatureError(
            f"a frame and its predecessor are different sizes ({gray.shape} against "
            f"{prev_gray.shape}); their difference is not a motion measurement")
    return float(np.abs(gray.astype(np.float64) - prev_gray.astype(np.float64)).mean())


def _gray(im):
    return np.asarray(im.convert("L"))


def frame_paths(frames_dir):
    names = [n for n in os.listdir(frames_dir)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    if not names:
        raise ArmatureError(f"no NNNNN.png frames in {frames_dir}")
    return {int(os.path.splitext(n)[0]): os.path.join(frames_dir, n) for n in names}


def source_rows_of(target_rows, geom):
    """Map a row band in the TARGET frame back to rows of the source candidate.

    The band the Director is choosing content for is defined on the frame the model will be
    handed; the picture in front of him is the candidate at its own size. Without this map
    the two are different coordinate systems and the marked band would be off by the crop.
    """
    y0, y1 = target_rows
    oy = geom["crop_offset"][1]
    s = geom["scale"]
    return ((y0 + oy) / s, (y1 + oy) / s)


def measure(frames_dir, indices):
    """Every candidate's derived numbers, plus the previous frame each one needs.

    The size check comes FIRST, before any arithmetic. One cover fit describes one source
    size, so a mixed-size set would draw the red and blue rectangles correctly on some tiles
    and wrongly on others with nothing to say which — and the reader would be judging bar
    content that does not survive into the frame.
    """
    paths = frame_paths(frames_dir)
    for i in indices:
        if i not in paths:
            lo, hi = min(paths), max(paths)
            raise ArmatureError(
                f"frame {i} is not in {frames_dir} ({len(paths)} frames, {lo}..{hi})")
    wanted = sorted({i for i in indices} | {i - 1 for i in indices if (i - 1) in paths})
    sizes = {i: Image.open(paths[i]).size for i in wanted}
    distinct = sorted(set(sizes.values()))
    if len(distinct) != 1:
        raise ArmatureError(
            f"the frames are not all one size ({distinct}); one cover fit cannot describe "
            f"all of them and the marked bands would be wrong on some tiles",
            )

    out = []
    for i in indices:
        im = Image.open(paths[i])
        g = _gray(im)
        prev = _gray(Image.open(paths[i - 1])) if (i - 1) in paths else None
        out.append({
            "index": i, "path": paths[i], "size": list(im.size),
            "sharpness": sharpness(g), "motion": motion(g, prev),
            "mean_luma": float(g.mean()),
            "motion_reference": (i - 1) if prev is not None else None,
        })
    return out


def source_run(record_path):
    """The generation these candidates came out of, read from its own payload record.

    Read, never typed. The one time this line was going to be passed in by hand, the hand
    typed a prompt_id that did not exist — a placeholder shaped like evidence, on the sheet
    that a spending decision gets made from. `NOT RECORDED` is what a missing record prints.
    """
    if not record_path:
        return {"prompt_id": MISSING, "seed": MISSING, "record": MISSING}
    with open(record_path, encoding="utf-8") as fh:
        rec = json.load(fh)
    return {"prompt_id": rec.get("prompt_id") or MISSING,
            "seed": rec.get("seed", MISSING),
            "resolution": rec.get("resolution", MISSING),
            "length": rec.get("length", MISSING),
            "record": os.path.abspath(record_path)}


def provenance_lines(rec):
    g = rec["cover_fit"]
    tb, sb = rec["visible_rows_target"], rec["visible_rows_source"]
    run = rec.get("source_run") or {}
    return [
        f"source run     {run.get('prompt_id', MISSING)}",
        f"source seed    {run.get('seed', MISSING)}",
        f"frames dir     {os.path.basename(rec['frames_dir'])}",
        f"frames present {rec['n_frames']}",
        f"candidate size {rec['source_size'][0]}x{rec['source_size'][1]}",
        f"target frame   {g['target_size'][0]}x{g['target_size'][1]}",
        "",
        "COVER FIT  (make_plate; never pads)",
        f"scale          {g['scale']:.6f}",
        f"resized to     {g['resized_size'][0]}x{g['resized_size'][1]}",
        f"crop box       {g['crop_box']}",
        f"drops          {g['dropped_px_resized']['x']} cols, "
        f"{g['dropped_px_resized']['y']} rows",
        f"of source area {g['kept_fraction_of_source_area']:.4f} kept",
        "",
        "VISIBLE BAND  (where a plate shows at all)",
        f"target rows    {tb[0]}..{tb[1]} of {g['target_size'][1]}",
        f"candidate rows {sb[0]:.1f}..{sb[1]:.1f} of {rec['source_size'][1]}",
        f"band fraction  {rec['band_fraction_of_target']:.4f} of the frame's rows",
        "",
        "RED   the cover crop - outside it is discarded",
        "BLUE  the visible band - only this shows in the",
        "      submitted frame; the rest is covered by the",
        "      authored master and its floor",
        "",
        "sharpness = variance of a discrete Laplacian.",
        "It scales with CONTRAST, so it ranks frames within",
        "a brightness band, never across one - read it",
        "beside luma, not instead of it.",
        "motion = mean |delta| from the previous frame.",
        "",
        "DIAGNOSTICS. They locate candidates; they do not",
        "rank them and they decide nothing. Gate PLATE is",
        "the Director's eye.",
    ]


def build(cands, rec, scale=0.6, title=None, per_row=3):
    tiles = []
    for c in cands:
        im = Image.open(c["path"]).convert("RGB")
        tiles.append((c, im.resize((max(1, round(im.width * scale)),
                                    max(1, round(im.height * scale))), Image.LANCZOS)))
    tw, th = tiles[0][1].width, tiles[0][1].height
    rows = (len(tiles) + per_row - 1) // per_row

    lines = provenance_lines(rec)
    grid_w = per_row * (tw + MARGIN)
    width = MARGIN + grid_w + 400
    height = max(HDR_H + MARGIN + rows * (th + 2 * LABEL_H + MARGIN) + MARGIN,
                 HDR_H + MARGIN + len(lines) * 15 + MARGIN)

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6), (title or "GATE PLATE - candidate plates")
           + f"      (tiles at {scale:g}x of "
             f"{rec['source_size'][0]}x{rec['source_size'][1]}; "
             f"sheets locate, full size decides)", fill=FG)

    g = rec["cover_fit"]
    sb = rec["visible_rows_source"]
    # The crop, in the candidate's own pixels, then scaled to the tile.
    crop_top = (g["crop_offset"][1]) / g["scale"]
    crop_bot = (g["crop_offset"][1] + g["target_size"][1]) / g["scale"]
    crop_l = (g["crop_offset"][0]) / g["scale"]
    crop_r = (g["crop_offset"][0] + g["target_size"][0]) / g["scale"]

    for i, (c, im) in enumerate(tiles):
        cx = MARGIN + (i % per_row) * (tw + MARGIN)
        cy = HDR_H + MARGIN + (i // per_row) * (th + 2 * LABEL_H + MARGIN)
        sheet.paste(im, (cx, cy))
        d.rectangle([cx + crop_l * scale, cy + crop_top * scale,
                     cx + min(crop_r, c["size"][0]) * scale - 1,
                     cy + min(crop_bot, c["size"][1]) * scale - 1], outline=CROP_INK)
        d.rectangle([cx, cy + sb[0] * scale,
                     cx + tw - 1, cy + sb[1] * scale], outline=BAND_INK)
        mot = MISSING if c["motion"] is None else f"{c['motion']:.3f}"
        d.text((cx, cy + th + 2), f"f{c['index']:03d}", fill=FG)
        d.text((cx, cy + th + 2 + LABEL_H),
               f"sharp {c['sharpness']:.0f}   motion {mot}   luma {c['mean_luma']:.1f}",
               fill=DIM)

    px = MARGIN + grid_w + MARGIN
    yy = HDR_H + MARGIN
    for ln in lines:
        d.text((px, yy), ln,
               fill=FG if ln.startswith(("COVER", "VISIBLE", "DIAGNOSTICS")) else DIM)
        yy += 15
    return sheet


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--at", required=True,
                    help="candidate frame indices (argparse eats leading minus signs: "
                         "pass flags as --flag=value)")
    ap.add_argument("--target", required=True, help="the generation's frame, WxH")
    ap.add_argument("--visible-rows", required=True,
                    help="y0,y1 of the target frame that a plate actually shows in")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=0.6)
    ap.add_argument("--title", default=None)
    ap.add_argument("--source-record", default=None,
                    help="the payload record of the generation these frames came out of; "
                         "its prompt_id and seed are READ onto the sheet, never typed")
    return ap.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    tw, _, thh = a.target.partition("x")
    target = (int(tw), int(thh))
    vr = [int(v) for v in a.visible_rows.split(",")]
    if len(vr) != 2 or not (0 <= vr[0] < vr[1] <= target[1]):
        raise ArmatureError(
            f"--visible-rows must be y0,y1 inside 0..{target[1]}; got {a.visible_rows!r}")

    indices = [int(v) for v in a.at.split(",") if v.strip()]
    cands = measure(a.frames, indices)      # raises if the frames are not all one size
    src = list(cands[0]["size"])

    geom = SF.cover_fit(src[0], src[1], target[0], target[1])
    rec = {
        "tool": "make_pick_sheet", "tool_version": TOOL_VERSION,
        "frames_dir": os.path.abspath(a.frames),
        "n_frames": len(frame_paths(a.frames)),
        "source_size": src, "target_size": list(target),
        "cover_fit": geom,
        "source_run": source_run(a.source_record),
        "visible_rows_target": vr,
        "visible_rows_source": list(source_rows_of(vr, geom)),
        "band_fraction_of_target": (vr[1] - vr[0]) / float(target[1]),
        "candidates": cands,
        "status": ("DIAGNOSTIC - Gate PLATE is a human gate; nothing here ranks the "
                   "candidates or decides between them"),
    }

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    build(cands, rec, scale=a.scale, title=a.title).save(a.out)
    rpath = os.path.splitext(a.out)[0] + ".json"
    with open(rpath, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)

    print("PICK_SHEET " + json.dumps({
        "out": a.out, "record": rpath, "candidates": indices,
        "source_size": src, "target_size": list(target),
        "visible_rows_target": vr,
        "visible_rows_source": [round(v, 1) for v in rec["visible_rows_source"]]},
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
