#!/usr/bin/env python
"""make_lift_sheet — source | what the detector saw | the rig performing the lift.

    python tools/make_lift_sheet.py --source=<render dir> --detection=<detection_raw.json>
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

This tool computes nothing and judges nothing.
"""

import argparse
import json
import os

import numpy as np
from PIL import Image, ImageDraw

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


def _rgb(path):
    im = Image.open(path)
    if im.mode == "RGBA":
        flat = Image.new("RGB", im.size, (0, 0, 0))
        flat.paste(im, mask=im.split()[3])
        return flat
    return im.convert("RGB")


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
        raise SystemExit("no subject pixels found in any frame; nothing to show")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--detection", required=True)
    ap.add_argument("--lifted", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,16,32,48,64")
    ap.add_argument("--tile-h", type=int, default=420)
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
    ap.add_argument("--lifted-camera", default=None,
                    help="the render_performer camera behind the lifted column; "
                         "printed on the sheet and in the sidecar. Absent = NOT RECORDED.")
    a = ap.parse_args()

    idx = [int(v) for v in a.frames.split(",") if v.strip() != ""]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    src = sorted(n for n in os.listdir(a.source) if n.endswith(".png") and n[0].isdigit())
    lif = sorted(n for n in os.listdir(a.lifted) if n.endswith(".png") and n[0].isdigit())
    with open(a.detection, encoding="utf-8") as fh:
        det = json.load(fh)["rows"]

    src_paths = [os.path.join(a.source, src[i]) for i in idx]
    lif_paths = [os.path.join(a.lifted, lif[i]) for i in idx]
    full_size = _rgb(src_paths[0]).size
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
        im = _rgb(path).crop(box)
        if overlay is not None:
            im = draw_landmarks(im, overlay[0], overlay[1], box, full_size)
        s = a.tile_h / im.height
        return im.resize((max(1, round(im.width * s)), a.tile_h), Image.LANCZOS)

    rows = []
    for i in idx:
        row = [tile(os.path.join(a.source, src[i]), box_s),
               tile(os.path.join(a.source, src[i]), box_s,
                    overlay=(det[i]["image"], det[i]["visibility"])
                    if det[i]["fired"] else None),
               tile(os.path.join(a.lifted, lif[i]), box_l)]
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
                   "crop_box_source": list(box_s), "crop_box_lifted": list(box_l),
                   "source_camera": a.source_camera or MISSING,
                   "lifted_camera": a.lifted_camera or MISSING,
                   "source": os.path.abspath(a.source),
                   "lifted": os.path.abspath(a.lifted),
                   "detection": os.path.abspath(a.detection),
                   "sheet": os.path.abspath(a.out)}, fh, indent=2)
    print("MAKE_LIFT_SHEET_OK " + json.dumps({"out": os.path.abspath(a.out),
                                              "frames": idx, "crop_source": list(box_s),
                   "crop_lifted": list(box_l)}))


if __name__ == "__main__":
    main()
