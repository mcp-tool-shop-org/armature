"""rig_sheet_compose — assemble the panels `make_rig_sheet.py` rendered into the sheet.

    <venv-python> tools\\rig_sheet_compose.py <out-dir>/panels.json

Separate from the renderer because Blender's bundled Python carries no PIL. The renderer
writes `panels.json`; this reads it and composites. Nothing irreversible waits on this step,
which is why a two-step is acceptable here and would not be for a gate.

**Panels are pasted at their rendered size and never resampled.** Every camera in a row
shares one orthographic scale, so a millimetre of character is the same number of pixels in
every panel of that row, and the joint insets are true 1:1. Resizing here to make a row fit
would silently destroy both properties.

**The sheet is as wide as its longest line of text, too.** `W` was the widest PANEL ROW and
ignored every string drawn on it — while the subtitle below is a ~150-character line carrying
the arm, the arc range, the key count and the fps. `sheet_compose` computes exactly this and
records why ("a cropped sheet still saves, still opens, and looks fine"); the fix was written
there and never carried here. The width computation and the typeface resolution are now
imported from that module rather than re-derived, so there is one of each.
"""

import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sheet_compose  # noqa: E402
from sheet_compose import font as _font  # noqa: E402
from sheet_compose import max_text_width  # noqa: E402

BG, INK, SUB = (22, 22, 24), (238, 238, 240), (166, 166, 172)

#: Kept as a name for callers; the search is `sheet_compose.font_search_paths()`.
FONT_DIR = sheet_compose.FONT_DIR


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

    p = spec["probe"]
    title_text = "E07 — the skeleton on the performer"
    subtitle = (f"22 named bones placed from landmarks measured on the mesh  ·  the arc is "
                f"E03's: the +X-side arm ({p['which_arm_is_on_plus_x']}), 0°→90° about +Y, "
                f"{p['frames']} keys at {p['fps']} fps")

    # As wide as the widest ROW **or the longest line of text** — sheet_compose's rule,
    # carried across at last. The numbers are what a cropped sheet loses first.
    text_w = max_text_width(
        [(title_text, f_title), (subtitle, f_lab)]
        + [(t, f_head) for t, _ in rows]
        + [(lab, f_lab) for _, row in rows for _, lab in row])
    W = max(max(PAD + sum(im.width + PAD for im, _ in row) for _, row in rows),
            int(PAD + text_w + PAD) + 6)
    # A row is as tall as its TALLEST panel, not as its first: panels are never resampled.
    row_heights = [max(im.height for im, _ in row) for _, row in rows]
    H = TITLE_H + sum(44 + rh + LABEL_H + PAD for rh in row_heights) + PAD
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    d.text((PAD, 30), title_text, font=f_title, fill=INK)
    d.text((PAD, 88), subtitle, font=f_lab, fill=SUB)

    y = TITLE_H
    for (title, row), row_h in zip(rows, row_heights):
        d.text((PAD, y), title, font=f_head, fill=INK)
        y += 44
        x = PAD
        for im, label in row:
            sheet.paste(im, (x, y))
            d.text((x + 6, y + row_h + 12), label, font=f_lab, fill=SUB)
            x += im.width + PAD
        y += row_h + LABEL_H + PAD

    os.makedirs(spec["out"], exist_ok=True)  # scripts create their own output directories
    path = os.path.join(spec["out"], "E07-rig-sheet.png")
    sheet.save(path)
    print(f"SHEET_OK {path} font={f_lab.path}")


if __name__ == "__main__":
    main()
