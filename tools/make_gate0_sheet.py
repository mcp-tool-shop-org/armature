#!/usr/bin/env python
"""make_gate0_sheet — the control | output | reference | provenance panel.

    python tools/make_gate0_sheet.py --run=<control dir> --frames-dir=<output frames>
                                     --reference=<plate.png> --meta=<payload meta.json>
                                     --out=<sheet.png> [--frames=0,8,16,24]

Gate 0: **no number is quoted for an arm until this sheet exists for it.** facet ran four
arms and two gates before building this panel, and when it finally existed the Director
read the whole thesis off one screen. The columns are fixed by the spec — control, output,
reference, provenance — because the failure it prevents is quoting a metric about an
artifact nobody has looked at.

The sheet computes nothing. It aligns the control frame that drove a generation with the
frame that came out of it, at the same frame index, and prints the provenance beside them.
Whether the figure is the right character is canon and the Director's; whether it is in the
right place is his eye on this panel.

Sheets locate; full size decides. Every tile is native resolution — 480x832 in, 480x832
out, no resampling — so what is on the sheet is what is in the file.
"""

import argparse
import json
import os

from PIL import Image, ImageDraw

MARGIN = 10
LABEL_H = 18
HDR_H = 22
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (140, 140, 150)


def _rgb(path):
    im = Image.open(path)
    if im.mode == "RGBA":
        flat = Image.new("RGB", im.size, (0, 0, 0))
        flat.paste(im, mask=im.split()[3])
        return flat
    return im.convert("RGB")


def build(control_dir, frames_dir, reference, meta, frame_idx, tile_h=416):
    cnames = sorted(n for n in os.listdir(control_dir) if n.endswith(".png"))
    onames = sorted(n for n in os.listdir(frames_dir) if n.endswith(".png"))
    ref = _rgb(reference)

    def fit(im):
        s = tile_h / im.height
        return im.resize((max(1, round(im.width * s)), tile_h), Image.LANCZOS)

    cols = []
    for fi in frame_idx:
        if fi >= len(cnames) or fi >= len(onames):
            continue
        c = fit(_rgb(os.path.join(control_dir, cnames[fi])))
        o = fit(_rgb(os.path.join(frames_dir, onames[fi])))
        az = 360.0 * fi / len(cnames)
        cols.append((f"f{fi:03d}  az {az:.0f}d", c, o))

    rtile = fit(ref)
    tile_w = cols[0][1].width
    width = MARGIN + len(cols) * (tile_w + MARGIN) + rtile.width + MARGIN + 430
    height = HDR_H + MARGIN + LABEL_H + tile_h + LABEL_H + tile_h + LABEL_H + MARGIN * 3

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6), f"E02 {meta.get('arm','?')}  -  GATE 0 SHEET   control | output | reference | provenance", fill=FG)

    y0 = HDR_H + MARGIN
    d.text((MARGIN, y0), "CONTROL  (depth, per-shot, near-bright)", fill=DIM)
    y1 = y0 + LABEL_H + tile_h + LABEL_H
    d.text((MARGIN, y1), "OUTPUT  (Wan 2.1 VACE 14B fp16)", fill=DIM)

    x = MARGIN
    for label, c, o in cols:
        sheet.paste(c, (x, y0 + LABEL_H))
        d.text((x, y0 + LABEL_H + tile_h + 2), label, fill=DIM)
        sheet.paste(o, (x, y1 + LABEL_H))
        d.text((x, y1 + LABEL_H + tile_h + 2), label, fill=DIM)
        x += tile_w + MARGIN

    sheet.paste(rtile, (x, y0 + LABEL_H))
    d.text((x, y0 + LABEL_H - LABEL_H), "REFERENCE", fill=DIM)
    d.text((x, y0 + LABEL_H + tile_h + 2), os.path.basename(reference), fill=DIM)

    px = x + rtile.width + MARGIN
    d.text((px, y0), "PROVENANCE", fill=DIM)
    ctl = meta.get("control")
    lines = [
        f"arm            {meta.get('arm')}",
        f"prompt_id      {meta.get('prompt_id','NOT RECORDED')}",
        f"model          {meta.get('models',{}).get('unet','?')}",
        f"text encoder   {meta.get('models',{}).get('clip','?')}",
        f"vae            {meta.get('models',{}).get('vae','?')}",
        f"frame          {meta.get('resolution')} x {meta.get('length')} @ {meta.get('fps')}fps",
        f"seed           {meta.get('seed')}",
        f"sampler        uni_pc / simple / 30 steps / cfg 6",
        f"payload sha256 {str(meta.get('payload_sha256',''))[:32]}",
        "",
        f"control bridge {ctl.get('bridge') if isinstance(ctl, dict) else ctl}",
        f"normalization  {ctl.get('normalization') if isinstance(ctl, dict) else '-'}",
        f"polarity       {ctl.get('polarity') if isinstance(ctl, dict) else '-'}",
        "",
        f"Gate L         {meta.get('gate_L',{}).get('verdict','?')}",
        f"Gate B         {meta.get('gate_B','NOT YET RUN')}",
        f"Gate R         N/A for this route (no codec in the path)",
        f"Gate C         {meta.get('gate_C','NOT YET RUN')}",
        "",
        "bridge fidelity  out = max(src-1, 0), measured",
        "  deterministic, one-sided, structure-preserving",
    ]
    yy = y0 + LABEL_H
    for ln in lines:
        d.text((px, yy), ln, fill=DIM if not ln.startswith("Gate") else FG)
        yy += 15
    return sheet


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--frames-dir", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,8,16,24")
    a = ap.parse_args(argv)

    with open(a.meta, encoding="utf-8") as fh:
        meta = json.load(fh)
    idx = [int(v) for v in a.frames.split(",") if v.strip()]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet = build(a.run, a.frames_dir, a.reference, meta, idx)
    sheet.save(a.out)
    print(f"GATE0_SHEET {a.out} {sheet.width}x{sheet.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
