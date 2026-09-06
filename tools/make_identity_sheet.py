#!/usr/bin/env python
"""make_identity_sheet — put the candidate reference plates beside the mesh.

    python tools/make_identity_sheet.py --run=<control run> --plates=<a.png,b.png,...>
                                        --out=<sheet.png> [--frames=0,8,16,24]

E02 needs a `reference_image`, and four plates sit beside the subject GLB with matching
filename stems. **A shared stem is not evidence.** E01's whole lesson was that a name
("longsword_hero", "_rigged") is a claim, not a measurement, and this repo has been
burned by that twice. Whether the man in the plates is the man in the mesh is canon —
no metric approximates it, so this tool computes nothing and decides nothing. It lays
the two next to each other at comparable angles and stops, because the judgement is the
Director's.

The mesh row uses the **normal** channel rather than depth or mask: normals read as
form to an eye (brow, jaw, shoulder, belt line), where depth reads as a smooth ramp and
mask reads as a black cut-out. The point is to show what shape the geometry actually is.

Sheets locate; full size decides. Tiles are downscaled to a common height so the rows
line up, and the scale factor is printed on every tile so nobody mistakes this panel for
the artifact.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402
from composite_reference import parse_plate  # noqa: E402
from sheet_compose import (SHEET_PLATE, SheetPopulationError,  # noqa: E402
                           frames_by_number, load_rgb_over_plate, require_frames)

MARGIN = 10
LABEL_H = 20
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (140, 140, 150)


class IdentitySheetError(SheetPopulationError):
    """The sheet cannot show what it was asked to show, and would not have said so.

    `if fi >= len(names): continue` dropped every requested index past the end of the
    directory and there was no guard on an empty row, so a 2-frame run asked for
    frames 0, 8, 16 and 24 produced a one-tile sheet, printed IDENTITY_SHEET and exited
    0. The panel the Director is asked "is this the same man?" on must not quietly show
    fewer angles than were requested.
    """


def _load_rgb(path, plate=SHEET_PLATE):
    """One tile, composited over the NAMED plate. See `sheet_compose.SHEET_PLATE`."""
    return load_rgb_over_plate(path, plate)[0]


def _fit(im, h):
    if im.height == h:
        return im, 1.0
    s = h / im.height
    return im.resize((max(1, round(im.width * s)), h), Image.LANCZOS), s


def _numbered_population(cdir, channel):
    """`(names, {frame NUMBER: path})` for one channel directory, or raise naming the stray.

    The refusal five siblings already carry, in the shape this sheet needs. It raises
    rather than filtering because the file it would drop — or draw — is shown to the
    Director as a frame of this run.
    """
    pngs = sorted(n for n in os.listdir(cdir) if n.lower().endswith(".png"))
    # The refusal is now `sheet_compose.frames_by_number` -- ONE implementation for the six
    # `require_frames` callers, lifted there by the wave-12 amend rather than kept as a
    # sixth copy of the same walk. The evidence keys this sheet's own reader expects
    # (`channel_dir`, `channel`) ride through as extra evidence.
    by_name = frames_by_number(pngs, where=cdir, what="frames", exc=IdentitySheetError,
                               evidence={"channel_dir": cdir, "channel": channel})
    names = [by_name[n] for n in sorted(by_name)]
    return names, {n: os.path.join(cdir, by_name[n]) for n in sorted(by_name)}


def rows_for(run_dir, plates, frames, tile_h=360, channel="normal",
             azimuth_captions=False, plate=SHEET_PLATE):
    """The sheet's rows, or raise naming what the run does not carry."""
    rows = []

    plate_tiles = []
    for p in plates:
        im = _load_rgb(p, plate)
        t, s = _fit(im, tile_h)
        plate_tiles.append((t, f"{os.path.basename(p)}  {im.width}x{im.height} @{s:.2f}x"))
    if not plate_tiles:
        raise IdentitySheetError(
            "no reference plates were given; the sheet's question is a comparison and "
            "half of it would be missing", {"plates": list(plates)})
    rows.append(("CANDIDATE REFERENCE PLATES  -  is this the same man?", plate_tiles))

    cdir = os.path.join(run_dir, channel)
    if not os.path.isdir(cdir):
        raise IdentitySheetError(
            f"{cdir} is not a directory; the {channel!r} channel of this run was never "
            f"written", {"run_dir": run_dir, "channel": channel, "channel_dir": cdir})
    # ---- ANDON, before a tile is cut: the population is this channel's NUMBERED frames
    #      and nothing else. The bare `*.png` listing took `render_pose_sticks`'
    #      `strip_every{N}.png` contact sheet — written into the very directory it has
    #      just filled — as a member, and `names[fi]` then drew it as a tile. Measured
    #      2026-09-04 on `00001,00002,00003 + strip_every8.png` with `--frames=0,3`:
    #      exit 0, row title "4-frame orbit", the tile captioned `f003 az 270d` cut from
    #      the contact sheet. The refusal is the one five siblings already carry
    #      (`encode_control.frame_population`, `invert_frames.frame_population`,
    #      `measure_floor.frame_population`, `measure_arm._load_frames`,
    #      `gate_b_frames.frame_paths`) — a stray is NAMED, never filtered in silence,
    #      because the tile it produces is shown to the Director as a frame of this run.
    names, by_number = _numbered_population(cdir, channel)
    # ---- and every requested frame NUMBER must exist. Keyed by the number in the file
    #      name, not by a position in a listing: on a run numbered from 1 the positional
    #      index put the run's first file under the caption `f000`, a frame the run does
    #      not hold — the distinction `make_crop_strip.frames_by_number` was given for
    #      the same reason, on the panel whose row title asks "is this the same man?".
    require_frames(frames, names, what=f"{channel!r} frame(s)", where=cdir,
                   exc=IdentitySheetError, numbers=sorted(by_number))

    order = sorted(by_number)
    mesh_tiles = []
    for fi in frames:
        im = _load_rgb(by_number[fi], plate)
        t, s = _fit(im, tile_h)
        # Azimuth is OPT-IN, as of wave 8. It used to be computed unconditionally as
        # 360*fi/len(names) and printed on every tile, with "orbit" in the row title —
        # E02's turnaround baked into the tool, on the panel whose own row title asks the
        # Director "is this the same man?". Measured 2026-09-04 on a 16-frame VIDEO clip
        # (time, not a camera orbit) with --frames=0,4,8,12: the tiles came back labelled
        # `f000 az 0d`, `f004 az 90d`, `f008 az 180d`, `f012 az 270d` under a row headed
        # "16-frame orbit" — four camera angles that never happened, in a caption a reader
        # has no reason to doubt. Both siblings had this removed in wave 6 and say so in
        # their own source (`make_gate0_sheet.frame_caption`,
        # `make_thesis_sheet --azimuth-captions`); this was the third member of the family
        # and was not swept.
        if azimuth_captions:
            # The frame's POSITION in this run's own orbit, not its number: a run
            # numbered 1..4 has four positions, and `360*fi/len(names)` printed 270d for
            # the third of them.
            az = 360.0 * order.index(fi) / len(order)
            mesh_tiles.append((t, f"f{fi:03d}  az {az:.0f}d  @{s:.2f}x"))
        else:
            mesh_tiles.append((t, f"f{fi:03d}  @{s:.2f}x"))
    shape = "frame orbit" if azimuth_captions else "frame run"
    rows.append((f"THE MESH, {os.path.basename(run_dir)}  -  {channel} channel, "
                 f"{len(names)}-{shape}", mesh_tiles))
    return rows


def build(run_dir, plates, frames, tile_h=360, channel="normal",
          azimuth_captions=False, plate=SHEET_PLATE):
    rows = rows_for(run_dir, plates, frames, tile_h=tile_h, channel=channel,
                    azimuth_captions=azimuth_captions, plate=plate)

    width = MARGIN
    for _, tiles in rows:
        w = MARGIN + sum(t.width + MARGIN for t, _ in tiles)
        width = max(width, w)
    height = MARGIN + sum(LABEL_H + tile_h + LABEL_H + MARGIN for _ in rows)

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    y = MARGIN
    for title, tiles in rows:
        d.text((MARGIN, y), title, fill=FG)
        y += LABEL_H
        x = MARGIN
        for t, label in tiles:
            sheet.paste(t, (x, y))
            d.text((x, y + t.height + 4), label, fill=DIM)
            x += t.width + MARGIN
        y += tile_h + LABEL_H + MARGIN
    return sheet


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="put the candidate reference plates beside the mesh, so the identity "
                    "question is answered by the eye against the thing it conditions")
    ap.add_argument("--run", required=True,
                    help="the control run directory whose channel frames show the mesh")
    ap.add_argument("--plates", required=True,
                    help="comma-separated candidate reference images, in column order")
    ap.add_argument("--out", required=True, help="the sheet image to write")
    ap.add_argument("--frames", default="0,8,16,24",
                    help="the run frame indices the mesh row is sampled at (argparse eats "
                         "leading minus signs: pass as --frames=0,8,16)")
    ap.add_argument("--channel", default="normal",
                    help="which control channel of the run to show the mesh in "
                         "(default normal)")
    ap.add_argument("--tile-height", type=int, default=360,
                    help="height each tile is drawn at, in pixels")
    # A turnaround run orbits and a video run does not. The caption says so only when the
    # caller says it is true.
    ap.add_argument("--azimuth-captions", action="store_true",
                    help="label frames as turnaround azimuth and call the row an orbit "
                         "(only true for a turnaround)")
    ap.add_argument("--sheet-plate", default=",".join(str(v) for v in SHEET_PLATE),
                    help="R,G,B of the plate an RGBA tile is composited over before it is "
                         "drawn. Named and recorded, never assumed: the reference column "
                         "of a panel must not show the character against a plate the "
                         "route did not submit")
    a = ap.parse_args(argv)

    plates = [p for p in a.plates.split(",") if p]
    frames = [int(v) for v in a.frames.split(",") if v.strip()]
    plate = parse_plate(a.sheet_plate, IdentitySheetError, flag="--sheet-plate")
    # ---- the output directory is created only once every in-tool andon above
    #      has fired -- the plate parse included.
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet = build(a.run, plates, frames, tile_h=a.tile_height, channel=a.channel,
                  azimuth_captions=a.azimuth_captions, plate=plate)
    sheet.save(a.out)
    print(f"IDENTITY_SHEET {a.out} {sheet.width}x{sheet.height} "
          f"plate={tuple(int(v) for v in plate)} "
          f"azimuth_captions={bool(a.azimuth_captions)}")
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MAKE_IDENTITY_SHEET")
