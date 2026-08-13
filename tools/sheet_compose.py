"""sheet_compose — assemble rendered panels into a dailies sheet.

    <venv-python> tools\\sheet_compose.py <out-dir>/panels.json

Separate from the renderers because Blender's bundled Python carries no PIL. A renderer
writes `panels.json`; this reads it and composites. Nothing irreversible waits on this step,
which is why a two-step is acceptable here and would not be for a gate.

**Panels are pasted at their rendered size and never resampled.** Every camera in a row
shares one orthographic scale, so a millimetre of character is the same number of pixels in
every panel of that row and the joint insets are true 1:1. Resizing here to make a row fit
would silently destroy both properties, so a row that is too wide makes the sheet wider
rather than making the panels smaller.

The spec is generic: a title, a subtitle, and a list of rows, each row a title and a list of
panels. A panel names a body render and optionally an overlay to composite over it.
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

BG, INK, SUB = (22, 22, 24), (238, 238, 240), (166, 166, 172)
FONT_DIR = r"C:\Windows\Fonts"
PAD, LABEL_H, ROW_TITLE_H, TITLE_H = 26, 54, 46, 150


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def _panel(spec):
    im = Image.open(spec["body"]).convert("RGBA")
    if spec.get("overlay"):
        ov = Image.open(spec["overlay"]).convert("RGBA")
        alpha = float(spec.get("overlay_alpha", 0.92))
        ov.putalpha(ov.getchannel("A").point(lambda v: int(v * alpha)))
        im = Image.alpha_composite(im, ov)
    return im.convert("RGB")


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    f_title, f_row, f_lab = (_font("arialbd.ttf", 44), _font("arialbd.ttf", 30),
                             _font("arial.ttf", 26))

    rows = [(r["title"], [(_panel(p), p.get("label", "")) for p in r["panels"]])
            for r in spec["rows"]]

    # The sheet is as wide as its widest ROW **or its longest line of text**. Sizing to the
    # panels alone silently crops every title and label that overruns them, which on a sheet
    # whose whole job is carrying gate numbers to a human means the numbers are the first
    # thing to disappear — and a cropped sheet still saves, still opens, and looks fine.
    ruler = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def _text_w(s, font):
        return ruler.textlength(s, font=font) if s else 0

    text_w = max(
        [_text_w(spec["title"], f_title), _text_w(spec.get("subtitle", ""), f_lab)]
        + [_text_w(t, f_row) for t, _ in rows]
        + [_text_w(lab, f_lab) for _, panels in rows for _, lab in panels])
    width = max(
        max(PAD + sum(im.width + PAD for im, _ in panels) for _, panels in rows),
        int(PAD + text_w + PAD) + 6)
    height = TITLE_H + sum(ROW_TITLE_H + panels[0][0].height + LABEL_H + PAD
                           for _, panels in rows) + PAD
    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)

    d.text((PAD, 30), spec["title"], font=f_title, fill=INK)
    d.text((PAD, 88), spec.get("subtitle", ""), font=f_lab, fill=SUB)

    y = TITLE_H
    for title, panels in rows:
        d.text((PAD, y), title, font=f_row, fill=INK)
        y += ROW_TITLE_H
        x = PAD
        for im, label in panels:
            sheet.paste(im, (x, y))
            if label:
                d.text((x + 6, y + im.height + 12), label, font=f_lab, fill=SUB)
            x += im.width + PAD
        y += panels[0][0].height + LABEL_H + PAD

    path = os.path.join(spec["out"], spec.get("filename", "sheet.png"))
    sheet.save(path)
    print("SHEET_OK " + path)


if __name__ == "__main__":
    main()
