"""Cast-survey sheet: one row per subject — full 3/4 front, full back, head front,
head back, and a stats label. Consumes preview_glb.py output.

python make_cast_sheet.py --dir <preview_out> --names a,b,c --title "..." --out sheet.png

Diagnostic presentation tool, not a pipeline gate. Dailies standard: uniform panel
scale across rows, labels readable at review distance, no internal gate states.
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

FULL_H = 440
HEAD_H = 440
PAD = 14
LABEL_H = 56
BG = (238, 238, 240)
INK = (20, 20, 24)
SUB = (90, 90, 100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--names", required=True, help="comma-separated subject names, row order")
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    font_b = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 30)
    font_r = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)

    rows = []
    for name in [n.strip() for n in args.names.split(",") if n.strip()]:
        panels = []
        for suf in ("full_a", "full_b", "head_a", "head_b"):
            im = Image.open(os.path.join(args.dir, f"{name}_{suf}.png")).convert("RGB")
            h = FULL_H if suf.startswith("full") else HEAD_H
            panels.append(im.resize((round(im.width * h / im.height), h), Image.LANCZOS))
        with open(os.path.join(args.dir, f"{name}_stats.json")) as f:
            st = json.load(f)
        arm_txt = "no armature" if not st["armatures"] else \
            f"armature: {st['armatures'][0][1]} bones ({', '.join(st['armatures'][0][2][:3])}...)"
        tex = [i for i in st["images"] if i[1][0] > 0]
        label = (f"{name}   -   {st['triangles']:,} tris, {st['mesh_objects']} mesh obj, "
                 f"{st['materials']} mats, {len(tex)} tex ({', '.join(str(t[1][0]) for t in tex[:3])} px), "
                 f"{st['empties']} empties, {arm_txt}")
        rows.append((panels, label))

    row_w = max(sum(p.width for p in panels) + PAD * 5 for panels, _ in rows)
    title_h = 74
    sheet = Image.new("RGB", (row_w, title_h + sum(FULL_H + LABEL_H + PAD * 2 for _ in rows)), BG)
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 18), args.title, font=font_b, fill=INK)
    y = title_h
    for panels, label in rows:
        x = PAD
        for p in panels:
            sheet.paste(p, (x, y))
            x += p.width + PAD
        d.text((PAD, y + FULL_H + 10), label, font=font_r, fill=SUB)
        y += FULL_H + LABEL_H + PAD * 2
    sheet.save(args.out)
    print("SHEET_OK", args.out, sheet.size)


if __name__ == "__main__":
    main()
