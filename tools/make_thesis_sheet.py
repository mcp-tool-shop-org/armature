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
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,8,16,24,32")
    ap.add_argument("--tile-height", type=int, default=300)
    ap.add_argument("--meta", default=None)
    a = ap.parse_args()

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

    rows = [("CONTROL   depth, per-shot, near-bright", a.control, cn)]
    for lab, d in arms:
        rows.append((f"OUTPUT  {lab}", d, listing(d)))

    tw = fit(_rgb(os.path.join(a.control, cn[0]))).width
    ref = fit(_rgb(a.reference))
    width = MARGIN + len(idx) * (tw + MARGIN) + ref.width + MARGIN * 2
    height = HDR + len(rows) * (LABEL_H + th + LABEL_H + MARGIN) + MARGIN

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6), "E02 THESIS PANEL   -   same control, same prompt, same reference."
                        "   A1a HAS control_video.  A2 HAS NONE.", fill=FG)

    y = HDR
    for title, ddir, names in rows:
        d.text((MARGIN, y), title, fill=FG)
        x = MARGIN
        for fi in idx:
            if fi >= len(names):
                continue
            t = fit(_rgb(os.path.join(ddir, names[fi])))
            sheet.paste(t, (x, y + LABEL_H))
            az = 360.0 * fi / len(cn)
            d.text((x, y + LABEL_H + th + 2), f"f{fi:03d}  az {az:.0f}d", fill=DIM)
            x += tw + MARGIN
        if title.startswith("CONTROL"):
            sheet.paste(ref, (x, y + LABEL_H))
            d.text((x, y + LABEL_H + th + 2), "REFERENCE (both arms)", fill=DIM)
        y += LABEL_H + th + LABEL_H + MARGIN

    sheet.save(a.out)
    print(f"THESIS_SHEET {a.out} {sheet.width}x{sheet.height}")


if __name__ == "__main__":
    main()
