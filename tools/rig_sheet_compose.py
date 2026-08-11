"""rig_sheet_compose — assemble the panels `make_rig_sheet.py` rendered into the sheet.

    <venv-python> tools\\rig_sheet_compose.py <out-dir>/panels.json

Separate from the renderer because Blender's bundled Python carries no PIL. The renderer
writes `panels.json`; this reads it and composites. Nothing irreversible waits on this step,
which is why a two-step is acceptable here and would not be for a gate.

**Panels are pasted at their rendered size and never resampled.** Every camera in a row
shares one orthographic scale, so a millimetre of character is the same number of pixels in
every panel of that row, and the joint insets are true 1:1. Resizing here to make a row fit
would silently destroy both properties.
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

BG, INK, SUB = (22, 22, 24), (238, 238, 240), (166, 166, 172)
FONT_DIR = r"C:\Windows\Fonts"


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def over(body_path, bones_path, alpha=0.92):
    a = Image.open(body_path).convert("RGBA")
    b = Image.open(bones_path).convert("RGBA")
    b.putalpha(b.getchannel("A").point(lambda v: int(v * alpha)))
    return Image.alpha_composite(a, b).convert("RGB")


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    g = spec["geometry"]
    PAD, LABEL_H, TITLE_H = g["pad"], g["label_h"], g["title_h"]
    last = g["probe_frames"]

    f_title, f_head, f_lab = _font("arialbd.ttf", 44), _font("arialbd.ttf", 30), \
        _font("arial.ttf", 26)

    row_a = [(over(*spec["full"][tag]), label) for tag, _, label in spec["views"]]
    row_b = [(Image.open(spec["arc"]["1"]).convert("RGB"), "frame 1 — the bind pose"),
             (Image.open(spec["arc"][str(last)]).convert("RGB"),
              f"frame {last} — the end of the authored arc")]
    row_c = [(over(*spec["insets"][n]), n) for n in spec["joint_order"]]

    rows = [("The figure, with the skeleton in place", row_a),
            ("The authored arc, body only", row_b),
            (f"At 1:1 — the deforming joints, character's {spec['side']} side", row_c)]

    W = max(PAD + sum(im.width + PAD for im, _ in row) for _, row in rows)
    H = TITLE_H + sum(44 + row[0][0].height + LABEL_H + PAD for _, row in rows) + PAD
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    p = spec["probe"]
    d.text((PAD, 30), "E07 — the skeleton on the performer", font=f_title, fill=INK)
    d.text((PAD, 88),
           f"22 named bones placed from landmarks measured on the mesh  ·  the arc is "
           f"E03's: the +X-side arm ({p['which_arm_is_on_plus_x']}), 0°→90° about +Y, "
           f"{p['frames']} keys at {p['fps']} fps",
           font=f_lab, fill=SUB)

    y = TITLE_H
    for title, row in rows:
        d.text((PAD, y), title, font=f_head, fill=INK)
        y += 44
        x = PAD
        for im, label in row:
            sheet.paste(im, (x, y))
            d.text((x + 6, y + im.height + 12), label, font=f_lab, fill=SUB)
            x += im.width + PAD
        y += row[0][0].height + LABEL_H + PAD

    path = os.path.join(spec["out"], "E07-rig-sheet.png")
    sheet.save(path)
    print("SHEET_OK " + path)


if __name__ == "__main__":
    main()
