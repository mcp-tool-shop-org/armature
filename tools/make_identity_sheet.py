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
from sheet_compose import SheetPopulationError, require_frames  # noqa: E402

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

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def _load_rgb(path):
    im = Image.open(path)
    if im.mode == "RGBA":
        flat = Image.new("RGB", im.size, (0, 0, 0))
        flat.paste(im, mask=im.split()[3])
        return flat
    return im.convert("RGB")


def _fit(im, h):
    if im.height == h:
        return im, 1.0
    s = h / im.height
    return im.resize((max(1, round(im.width * s)), h), Image.LANCZOS), s


def rows_for(run_dir, plates, frames, tile_h=360, channel="normal"):
    """The sheet's rows, or raise naming what the run does not carry."""
    rows = []

    plate_tiles = []
    for p in plates:
        im = _load_rgb(p)
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
    names = sorted(n for n in os.listdir(cdir) if n.endswith(".png"))
    # ---- every requested index must EXIST. Dropping one silently shows the Director
    #      fewer angles than were asked for, on the panel where identity is judged. The
    #      refusal written here in wave 3 now lives in `sheet_compose.require_frames`,
    #      because four sibling sheets needed the same one and had none.
    require_frames(frames, names, what=f"{channel!r} frame(s)", where=cdir,
                   exc=IdentitySheetError)

    mesh_tiles = []
    for fi in frames:
        im = _load_rgb(os.path.join(cdir, names[fi]))
        t, s = _fit(im, tile_h)
        az = 360.0 * fi / len(names)
        mesh_tiles.append((t, f"f{fi:03d}  az {az:.0f}d  @{s:.2f}x"))
    # The orbit length is the RUN's, not a literal 33. The azimuth beside each tile was
    # already computed from len(names), so the label used to contradict its own row.
    rows.append((f"THE MESH, {os.path.basename(run_dir)}  -  {channel} channel, "
                 f"{len(names)}-frame orbit", mesh_tiles))
    return rows


def build(run_dir, plates, frames, tile_h=360, channel="normal"):
    rows = rows_for(run_dir, plates, frames, tile_h=tile_h, channel=channel)

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
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--plates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,8,16,24")
    ap.add_argument("--channel", default="normal")
    ap.add_argument("--tile-height", type=int, default=360)
    a = ap.parse_args(argv)

    plates = [p for p in a.plates.split(",") if p]
    frames = [int(v) for v in a.frames.split(",") if v.strip()]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet = build(a.run, plates, frames, tile_h=a.tile_height, channel=a.channel)
    sheet.save(a.out)
    print(f"IDENTITY_SHEET {a.out} {sheet.width}x{sheet.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
