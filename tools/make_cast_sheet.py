"""Cast-survey sheet: one row per subject — full 3/4 front, full back, head front,
head back, and a stats label. Consumes preview_glb.py output.

python make_cast_sheet.py --dir <preview_out> --names a,b,c --title "..." --out sheet.png

Diagnostic presentation tool, not a pipeline gate. Dailies standard: uniform panel
scale across rows, labels readable at review distance, no internal gate states.

Two things carried across from `sheet_compose`, which had already paid for both: the sheet
is as wide as its longest LABEL as well as its widest row (the stats line is the whole
point of this sheet and was the first thing cropped), and the typeface is resolved through
an explicit search that raises when nothing is found rather than through two absolute
`C:\\Windows\\Fonts` literals that a POSIX runner turns into relative strings.
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def _font(name, size):
    """The face, resolved at CALL time through `sheet_compose`'s one implementation —
    `from sheet_compose import font as _font` bound the function OBJECT at import, so this
    module held a different callable from the one `sheet_compose` itself calls."""
    import sheet_compose

    return sheet_compose._font(name, size)

from sheet_compose import max_text_width  # noqa: E402

FULL_H = 440
HEAD_H = 440
PAD = 14
LABEL_H = 56
BG = (238, 238, 240)
INK = (20, 20, 24)
SUB = (90, 90, 100)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--names", required=True, help="comma-separated subject names, row order")
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    font_b = _font("arialbd.ttf", 30)
    font_r = _font("arial.ttf", 24)

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

    # As wide as the widest row **or the longest string drawn on it** — the stats label is
    # this sheet's whole payload and was cropped from the right, which is where the numbers
    # sit. sheet_compose.max_text_width is the one implementation.
    text_w = max_text_width([(args.title, font_b)] + [(lab, font_r) for _, lab in rows])
    row_w = max(max(sum(p.width for p in panels) + PAD * 5 for panels, _ in rows),
                int(PAD + text_w + PAD))
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
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)  # scripts create their own output directories
    sheet.save(args.out)
    # Its OWN token. `SHEET_OK` was printed by four tools -- this one, make_e13_sheet,
    # rig_sheet_compose and sheet_compose -- and it was the only shared success sentinel in
    # the tree, so a caller grepping a log for it could not say which panel was produced.
    # E07-the-skeleton.md:202-205 names SHEET_OK in the list of tokens the pipeline keys on.
    print("CAST_SHEET_OK", args.out, sheet.size, f"font={font_r.path}")
    return args.out


if __name__ == "__main__":
    main()
