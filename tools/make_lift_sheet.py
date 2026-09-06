#!/usr/bin/env python
"""make_lift_sheet — source | what the detector saw | the rig performing the lift.

    <venv-python> tools/make_lift_sheet.py --source=<render dir> --detection=<detection_raw.json>
                                    --lifted=<render dir> --out=<sheet.png>
                                    [--frames=0,16,32,48,64]

The panel this experiment is read off, and it exists **before any number is quoted** — Gate
0's rule, which facet earned by running four arms and two gates without one. The columns
are fixed by what has to be told apart:

* **source** — the frame the detector was handed.
* **detector** — the same frame with the 33 image-space landmarks drawn on it. This column
  is not decoration. `visibility` numbers look perfectly healthy when a detector has locked
  onto a shadow or a floor seam, and nothing numeric in this chain would notice; the only
  instrument that catches it is a person looking at where the dots landed.
* **lifted** — the performer's own rig performing the solved rotations, rendered on
  `render_performer`'s own camera. That camera is NOT necessarily the source's — E09
  measured exactly that (a frontal generated donor beside the banked three-quarter
  camera, az 225 / elev 6), so comparing the columns can take a mental rotation. The
  sheet prints each camera when told (`--source-camera`, `--lifted-camera`) and
  `NOT RECORDED` when not; it never claims the cameras match.

**The tiles are cropped, and the crop is measured rather than composed.** The figure covers
about 2% of a 1920x1080 frame, so a full-frame contact sheet would show a thumbnail of a
mannequin and settle nothing. The crop box is the union of the subject's own pixels across
the frames shown — found by differencing against the render's empty plate, so it comes from
the render and not from the detector whose work is on trial. Every tile uses the same box.

Sheets locate; full size decides. The crop is recorded in the sidecar, and the uncropped
frames stay on disk at 1920x1080 for the Director's zoom.

**The three columns are PAIRED, not zipped (measured 2026-09-03).** The source listing,
the lifted listing and the detection rows were three independent populations indexed by the
same `i` from `--frames`, with no check that any two of them named the same frames and no
bounds check at all. A source numbered 00000..00004 beside a lifted directory holding the
SAME five renders numbered 00001..00005 composed a sheet whose row `f000` showed source
`00000.png` next to lifted `00001.png`, printed `MAKE_LIFT_SHEET_OK`, and wrote a sidecar
recording only the requested indices — no file name anywhere in it. Exit 0. That is the
off-by-one `measure_lift.gate_pairing` exists for, and the reason its docstring compares
file NAMES: `detect()` sets each row's `frame` to the enumeration index, so
`[r['frame'] for r in rows]` is `range(n)` however the directory is numbered.

So `gate_listing_pairing` (the same gate, one implementation) runs before a tile is cut,
`require_frames` refuses a requested index past any population instead of raising
`IndexError` from a list subscript, and the sidecar records the file each column actually
loaded rather than the index that was asked for.

This tool computes nothing and judges nothing.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from composite_reference import parse_plate  # noqa: E402
from measure_lift import as_pairing_rows, gate_listing_pairing  # noqa: E402
from sheet_compose import (SHEET_PLATE, SheetPopulationError,  # noqa: E402
                           frames_by_number, load_rgb_over_plate, require_frames)

MARGIN = 12
LABEL_H = 20
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (140, 140, 150)
MISSING = "NOT RECORDED"

#: The BlazePose skeleton, for drawing only. Not a convention any model consumes — the
#: driving-signal convention is a separate thing entirely and lives in `armature_core`.
EDGES = ((11, 12), (11, 23), (12, 24), (23, 24),
         (11, 13), (13, 15), (15, 19), (12, 14), (14, 16), (16, 20),
         (23, 25), (25, 27), (27, 31), (24, 26), (26, 28), (28, 32),
         (0, 11), (0, 12), (7, 0), (8, 0))



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

def _rgb(path, plate=SHEET_PLATE):
    """One tile, composited over the NAMED plate. See `sheet_compose.SHEET_PLATE`."""
    return load_rgb_over_plate(path, plate)[0]


def default_labels(full_size):
    """Column headings derived from the frames actually loaded — never a baked size.

    The first heading used to read "source render 1920x1080" as a literal; pointed at an
    832x480 generated clip it labelled frames with a resolution they do not have.
    """
    w, h = full_size
    return [f"source {w}x{h}",
            "what the detector saw (33 landmarks)",
            "the rig performing the solved lift"]


def camera_note(source_camera=None, lifted_camera=None):
    """The sheet's camera line. Identity is never claimed; an unknown camera says so.

    E09 §26: this tool claimed the lifted column was "on the identical camera" while the
    runs it served compared a frontal donor against the banked az-225 render. The honest
    line carries what was passed in, and NOT RECORDED for what was not.
    """
    return (f"cameras: source {source_camera or MISSING} | "
            f"lifted {lifted_camera or MISSING}")


def subject_box(frame_paths, empty_plate, pad=0.10):
    """The union of the subject's own pixels over the frames shown, plus a margin.

    Measured against the empty plate — the same camera, lights and floor with the character
    hidden — so a floor or a background gradient cannot widen the box, and the detector has
    no say in what gets shown.
    """
    base = np.asarray(_rgb(empty_plate), dtype=np.int16)
    x0, y0, x1, y1 = None, None, None, None
    for p in frame_paths:
        px = np.asarray(_rgb(p), dtype=np.int16)
        mask = np.abs(px - base).max(axis=2) > 1
        ys, xs = np.nonzero(mask)
        if not len(xs):
            continue
        bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
        x0 = bx0 if x0 is None else min(x0, bx0)
        x1 = bx1 if x1 is None else max(x1, bx1)
        y0 = by0 if y0 is None else min(y0, by0)
        y1 = by1 if y1 is None else max(y1, by1)
    if x0 is None:
        raise SheetPopulationError(
            f"no subject pixels found in any of the {len(list(frame_paths))} frame(s) "
            f"against {os.path.basename(str(empty_plate))}; the crop box would be the "
            f"whole frame or nothing, and neither is the subject",
            {"gate": "SUBJECT_BOX", "empty_plate": str(empty_plate),
             "n_frames": len(list(frame_paths))})
    h, w = base.shape[:2]
    mx, my = int(pad * (x1 - x0)), int(pad * (y1 - y0))
    return (max(0, int(x0) - mx), max(0, int(y0) - my),
            min(w, int(x1) + mx + 1), min(h, int(y1) + my + 1))


def draw_landmarks(im, image_landmarks, visibility, box, full_size):
    """The 33 detected points, in the crop's own pixel space. Colour carries visibility so
    a confidently-placed point and a guessed one do not look the same.

    MediaPipe returns image landmarks normalised to the frame, so they are scaled by the
    FULL frame and then shifted by the crop's origin — the full size is passed in rather
    than written down here, because a hard-coded 1920x1080 would silently mis-place every
    dot the day this renders at another resolution.
    """
    d = ImageDraw.Draw(im)
    bx0, by0, _, _ = box
    fw, fh = full_size
    pts = [(x * fw - bx0, y * fh - by0) for x, y in image_landmarks]
    for a, b in EDGES:
        d.line([pts[a], pts[b]], fill=(70, 200, 255), width=2)
    for i, (px, py) in enumerate(pts):
        v = visibility[i]
        c = (int(255 * (1 - v)), int(90 + 165 * v), 60)
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=c, outline=(20, 20, 20))
    return im


def main(argv=None):
    """The sheet, or a refusal. Returns 0 so `SystemExit(main())` pins SUCCESS too.

    `argv` was not a parameter: four of the five panel tools took one and this one read
    `sys.argv` directly, so the suite could only drive it through a monkeypatched
    `sys.argv` in a subprocess — which is why no test drove any sheet's `main` end to end
    and a sibling shipped a call site with no flag (wave 10, rule 3).
    """
    ap = argparse.ArgumentParser(
        description="source | what the detector saw | the rig performing the lift — the "
                    "three columns that say whether a lift is the same performance",
        epilog=HALT_EPILOG)
    ap.add_argument("--source", required=True,
                    help="the source frame directory the lift was taken FROM")
    ap.add_argument("--detection", required=True,
                    help="the detector's raw record (detection_raw.json), drawn as the "
                         "middle column")
    ap.add_argument("--lifted", required=True,
                    help="the render_performer frames of the rig performing the lift")
    ap.add_argument("--out", required=True, help="the sheet image to write")
    ap.add_argument("--frames", default="0,16,32,48,64",
                    help="the frame indices all three columns are sampled at (argparse "
                         "eats leading minus signs: pass as --frames=0,16,32)")
    ap.add_argument("--tile-h", type=int, default=420,
                    help="height each tile is drawn at, in pixels")
    ap.add_argument("--source-uncropped", action="store_true",
                    help="show the source column at full frame. Use when the source is a "
                         "GENERATED clip: there is no empty plate to difference against, "
                         "and cropping to the detector's own landmarks would let the "
                         "instrument on trial choose what the Director gets to see.")
    ap.add_argument("--labels", default=None,
                    help="three comma-separated column headings")
    ap.add_argument("--source-camera", default=None,
                    help="the source clip's camera, as its own recipe records it; "
                         "printed on the sheet and in the sidecar. Absent = NOT RECORDED.")
    ap.add_argument("--sheet-plate", default=",".join(str(v) for v in SHEET_PLATE),
                    help="R,G,B of the plate an RGBA tile is composited over before it "
                         "is drawn; printed on the OK line and recorded in the sidecar")
    ap.add_argument("--lifted-camera", default=None,
                    help="the render_performer camera behind the lifted column; "
                         "printed on the sheet and in the sidecar. Absent = NOT RECORDED.")
    a = ap.parse_args(argv)

    idx = [int(v) for v in a.frames.split(",") if v.strip() != ""]

    plate = parse_plate(a.sheet_plate, SheetPopulationError, flag="--sheet-plate")

    src = sorted(n for n in os.listdir(a.source)
                 if n.lower().endswith(".png") and n[0].isdigit())
    lif = sorted(n for n in os.listdir(a.lifted)
                 if n.lower().endswith(".png") and n[0].isdigit())
    with open(a.detection, encoding="utf-8") as fh:
        det = json.load(fh)["rows"]

    # ---- ANDON, before a tile is cut: the three columns name the SAME frames.
    pairing = gate_listing_pairing({"source": src, "lifted": lif, "detection": det})
    # ---- and every requested frame NUMBER exists in each of them. By NUMBER, not by
    #      position: a run numbered 00001..00003 accepted `--frames=0,1,2` and drew
    #      00001/00002/00003 under the captions f000/f001/f002, while refusing
    #      `--frames=3`, the frame it does hold. `sheet_compose.require_frames`'s
    #      `numbers=` mode was built in wave 10 and landed in one of six callers.
    sby = frames_by_number(src, where=a.source, what="source frame(s)",
                           exc=SheetPopulationError)
    lby = frames_by_number(lif, where=a.lifted, what="lifted frame(s)",
                           exc=SheetPopulationError)
    # The detection rows keyed by the NUMBER they name, through `measure_lift`'s own
    # reader — a row may name its `file` and not its `frame`, and the pairing gate above
    # has already compared the three populations through that same reader.
    dby = {}
    for _row, _pr in zip(det, as_pairing_rows(det)):
        _stem = os.path.splitext(str(_pr["file"]))[0]
        if _stem.isdigit():
            dby[int(_stem)] = _row
    require_frames(idx, src, what="numbered source frame(s)", where=a.source,
                   numbers=sorted(sby))
    require_frames(idx, lif, what="numbered lifted frame(s)", where=a.lifted,
                   numbers=sorted(lby))
    require_frames(idx, det, what="detection row(s)", where=a.detection,
                   numbers=sorted(dby))

    # ---- the output directory is created only once every in-tool andon above has
    #      fired. A refused run that has already made its directory leaves an empty
    #      one behind, which a later reader -- or a re-run into the same --out --
    #      reads as an attempt that produced nothing rather than one that was refused.
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    src_paths = [os.path.join(a.source, sby[i]) for i in idx]
    lif_paths = [os.path.join(a.lifted, lby[i]) for i in idx]
    full_size = _rgb(src_paths[0], plate).size
    box_l = subject_box(lif_paths, os.path.join(a.lifted, "empty_plate.png"))

    if a.source_uncropped:
        box_s = (0, 0, full_size[0], full_size[1])
    else:
        box_s = subject_box(src_paths, os.path.join(a.source, "empty_plate.png"))
        # ONE box across both columns, so a limb that moved is not confused with a crop
        # that did. Only possible when the two are the same camera on the same rig.
        box_s = box_l = (min(box_s[0], box_l[0]), min(box_s[1], box_l[1]),
                         max(box_s[2], box_l[2]), max(box_s[3], box_l[3]))

    def tile(path, box, overlay=None):
        im = _rgb(path, plate).crop(box)
        if overlay is not None:
            im = draw_landmarks(im, overlay[0], overlay[1], box, full_size)
        s = a.tile_h / im.height
        return im.resize((max(1, round(im.width * s)), a.tile_h), Image.LANCZOS)

    rows = []
    for i in idx:
        row = [tile(os.path.join(a.source, sby[i]), box_s),
               tile(os.path.join(a.source, sby[i]), box_s,
                    overlay=(dby[i]["image"], dby[i]["visibility"])
                    if dby[i]["fired"] else None),
               tile(os.path.join(a.lifted, lby[i]), box_l)]
        rows.append((i, row))

    widths = [max(r[1][c].width for r in rows) for c in range(3)]
    xs, acc = [], MARGIN
    for w in widths:
        xs.append(acc)
        acc += w + MARGIN
    W = acc
    H = MARGIN + LABEL_H + len(rows) * (a.tile_h + LABEL_H + MARGIN)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    labels = a.labels.split(",") if a.labels else default_labels(full_size)
    for c, name in enumerate(labels[:3]):
        d.text((xs[c], 4), name.strip(), fill=FG)

    y = MARGIN + LABEL_H
    for i, row in rows:
        for c, im in enumerate(row):
            sheet.paste(im, (xs[c], y))
            if c == 0:
                d.text((xs[c] + 4, y + a.tile_h + 3), f"frame {i:03d}", fill=DIM)
        y += a.tile_h + LABEL_H + MARGIN
    note = (f"source shown UNCROPPED at {full_size[0]}x{full_size[1]} (a generated clip has "
            f"no empty plate to difference against); lifted cropped "
            f"x{box_l[0]}-{box_l[2]} y{box_l[1]}-{box_l[3]}"
            if a.source_uncropped else
            f"crop x{box_s[0]}-{box_s[2]} y{box_s[1]}-{box_s[3]} — union of subject pixels "
            f"vs the empty plate")
    d.text((MARGIN, H - LABEL_H + 2),
           note + "; " + camera_note(a.source_camera, a.lifted_camera)
           + "; full frames on disk uncropped", fill=DIM)
    sheet.save(a.out)

    with open(os.path.splitext(a.out)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump({"tool": "make_lift_sheet", "frames": idx,
                   # The RGB composite is a deliberate, recorded choice; the sidecar is
                   # where the panel says which plate it drew the character against.
                   "sheet_plate_rgb_srgb": [int(v) for v in plate],
                   # The FILE each column loaded, not the index that was asked for: the
                   # sidecar of the mis-paired run named [0,1,2] and nothing else.
                   "rows": [{"frame": i,
                             "source": os.path.abspath(os.path.join(a.source, sby[i])),
                             "lifted": os.path.abspath(os.path.join(a.lifted, lby[i])),
                             "detection_row": i} for i in idx],
                   "gate_PAIRING": {k: v.get("verdict") for k, v in pairing.items()},
                   "crop_box_source": list(box_s), "crop_box_lifted": list(box_l),
                   "source_camera": a.source_camera or MISSING,
                   "lifted_camera": a.lifted_camera or MISSING,
                   "source": os.path.abspath(a.source),
                   "lifted": os.path.abspath(a.lifted),
                   "detection": os.path.abspath(a.detection),
                   "sheet": os.path.abspath(a.out)}, fh, indent=2)
    print("MAKE_LIFT_SHEET_OK " + json.dumps({"out": os.path.abspath(a.out),
                                              "sheet_plate": [int(v) for v in plate],
                                              "frames": idx, "crop_source": list(box_s),
                   "crop_lifted": list(box_l)}))
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MAKE_LIFT_SHEET")
