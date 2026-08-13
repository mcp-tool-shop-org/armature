#!/usr/bin/env python
"""make_thesis_sheet — control vs controlled-output vs no-control-output, one panel.

    python tools/make_thesis_sheet.py --control=<dir> --arms=A1a:<dir>,A2:<dir>
                                      --reference=<plate.png> --out=<sheet.png>

The panel E02 exists to produce. The A1a sheet on its own shows a turning armored figure
that follows the control — and that is **unfalsifiable without A2**, because the model may
produce a turning armored figure from the prompt and the reference alone. A2 is the same
prompt, the same reference, and no `control_video`. Putting the two output rows under the
same control row is what turns a demonstration into evidence.

Computes nothing, decides nothing, quotes no metric. Whether the figure is in the same
place at the same time is P3, and P3 is judged by eye on this panel at full size.
"""

import argparse
import json
import os

from PIL import Image, ImageDraw

MARGIN = 10
LABEL_H = 17
HDR = 24
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (145, 145, 155)


def _rgb(p):
    im = Image.open(p)
    if im.mode == "RGBA":
        f = Image.new("RGB", im.size, (0, 0, 0))
        f.paste(im, mask=im.split()[3])
        return f
    return im.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--arms", required=True, help="LABEL:dir,LABEL:dir")
    ap.add_argument("--reference", required=True,
                    help="path to the reference plate, or the literal 'none'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,8,16,24,32")
    ap.add_argument("--tile-height", type=int, default=300)
    ap.add_argument("--meta", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--control-label", default="CONTROL   depth, per-shot, near-bright")
    ap.add_argument("--captions", default=None,
                    help="'idx=text,idx=text' per-frame labels, replacing the frame index")
    # Azimuth is opt-in as of E14. It used to be the DEFAULT caption, computed as
    # 360*i/len(frames) — true for a turnaround, and a fabricated number on every video
    # route, where the frames are time and not a camera orbit. E10's closing lesson names
    # this class: a tool that bakes one experiment's meaning into a literal will lie the
    # first time it is reused, and it lies in a caption a reader has no reason to doubt.
    ap.add_argument("--azimuth-captions", action="store_true",
                    help="label frames as turnaround azimuth (only true for a turnaround)")
    ap.add_argument("--no-reference-note", default=None,
                    help="pipe-separated lines drawn when --reference=none")
    a = ap.parse_args()

    captions = None
    if a.captions:
        captions = {}
        for part in a.captions.split(","):
            k, _, v = part.partition("=")
            captions[int(k)] = v

    idx = [int(v) for v in a.frames.split(",") if v.strip()]
    th = a.tile_height
    arms = []
    for tok in a.arms.split(","):
        lab, _, d = tok.partition(":")
        arms.append((lab, d))

    def listing(d):
        return sorted(n for n in os.listdir(d) if n.endswith(".png"))

    cn = listing(a.control)

    def fit(im):
        s = th / im.height
        return im.resize((max(1, round(im.width * s)), th), Image.LANCZOS)

    rows = [(a.control_label, a.control, cn)]
    for lab, d in arms:
        rows.append((f"OUTPUT  {lab}", d, listing(d)))

    tw = fit(_rgb(os.path.join(a.control, cn[0]))).width
    # `none` is a real value: E03's arms deliberately carry no reference image.
    ref = None if a.reference.lower() == "none" else fit(_rgb(a.reference))
    ref_w = ref.width if ref is not None else 260
    width = MARGIN + len(idx) * (tw + MARGIN) + ref_w + MARGIN * 2
    height = HDR + len(rows) * (LABEL_H + th + LABEL_H + MARGIN) + MARGIN

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6), a.title or ("E02 THESIS PANEL   -   same control, same prompt, "
                                    "same reference.   A1a HAS control_video.  A2 HAS NONE."),
           fill=FG)

    y = HDR
    for row_i, (title, ddir, names) in enumerate(rows):
        d.text((MARGIN, y), title, fill=FG)
        x = MARGIN
        for fi in idx:
            if fi >= len(names):
                continue
            t = fit(_rgb(os.path.join(ddir, names[fi])))
            sheet.paste(t, (x, y + LABEL_H))
            if captions is not None:
                cap = f"f{fi:03d}  {captions.get(fi, '')}"
            elif a.azimuth_captions:
                cap = f"f{fi:03d}  az {360.0 * fi / len(cn):.0f}d"
            else:
                cap = f"f{fi:03d}"
            d.text((x, y + LABEL_H + th + 2), cap, fill=DIM)
            x += tw + MARGIN
        # The reference rides the FIRST row, whatever that row is called. This was
        # `title.startswith("CONTROL")` until E14, where the first row is a BASELINE rather
        # than a control — and the reference plate was silently not drawn at all. A sheet
        # that omits the reference on a label mismatch is the panel this repo requires,
        # missing the third of its four columns, with nothing saying so.
        if row_i == 0:
            if ref is not None:
                sheet.paste(ref, (x, y + LABEL_H))
                d.text((x, y + LABEL_H + th + 2), "REFERENCE (all arms)", fill=DIM)
            else:
                for i, ln in enumerate(
                        (a.no_reference_note or "REFERENCE: NONE.").split("|")):
                    d.text((x, y + LABEL_H + 4 + i * 15), ln, fill=DIM)
        y += LABEL_H + th + LABEL_H + MARGIN

    sheet.save(a.out)
    print(f"THESIS_SHEET {a.out} {sheet.width}x{sheet.height}")


if __name__ == "__main__":
    main()
