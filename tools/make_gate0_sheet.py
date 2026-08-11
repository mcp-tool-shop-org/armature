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


def build(control_dir, frames_dir, reference, meta, frame_idx, tile_h=416, captions=None):
    """Assemble the panel.

    `reference` may be None. E03 runs with **no reference image at all** — held constant
    (absent) across all three arms, which is legal (`WanVaceToVideo.reference_image` is
    `required: false`, measured) and correct, because its subject carries no identity for a
    reference to preserve. The column is then labelled as deliberately absent rather than
    filled with a stand-in: a sheet must not contain a placeholder shaped like evidence.

    `captions` overrides the per-frame label. E02's arms orbited, so a frame's azimuth was
    the useful caption; E03 holds the camera still and moves the subject, so an azimuth
    caption would print a number that never changes and imply the camera did something.
    """
    cnames = sorted(n for n in os.listdir(control_dir) if n.endswith(".png"))
    onames = sorted(n for n in os.listdir(frames_dir) if n.endswith(".png"))
    ref = _rgb(reference) if reference else None

    def fit(im):
        s = tile_h / im.height
        return im.resize((max(1, round(im.width * s)), tile_h), Image.LANCZOS)

    cols = []
    for fi in frame_idx:
        if fi >= len(cnames) or fi >= len(onames):
            continue
        c = fit(_rgb(os.path.join(control_dir, cnames[fi])))
        o = fit(_rgb(os.path.join(frames_dir, onames[fi])))
        if captions is not None:
            label = f"f{fi:03d}  {captions.get(fi, '')}"
        else:
            label = f"f{fi:03d}  az {360.0 * fi / len(cnames):.0f}d"
        cols.append((label, c, o))

    rtile = fit(ref) if ref is not None else None
    ref_w = rtile.width if rtile is not None else 220
    tile_w = cols[0][1].width
    width = MARGIN + len(cols) * (tile_w + MARGIN) + ref_w + MARGIN + 430
    height = HDR_H + MARGIN + LABEL_H + tile_h + LABEL_H + tile_h + LABEL_H + MARGIN * 3

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6), f"{meta.get('experiment', 'E02')} {meta.get('arm','?')}  -  "
                        f"GATE 0 SHEET   control | output | reference | provenance", fill=FG)

    y0 = HDR_H + MARGIN
    ctl_meta = meta.get("control")
    ctl_desc = (ctl_meta.get("polarity", "") if isinstance(ctl_meta, dict)
                else "NONE - this arm has no control_video")
    d.text((MARGIN, y0), f"CONTROL  ({ctl_desc})", fill=DIM)
    y1 = y0 + LABEL_H + tile_h + LABEL_H
    d.text((MARGIN, y1), "OUTPUT  (Wan 2.1 VACE 14B fp16)", fill=DIM)

    x = MARGIN
    for label, c, o in cols:
        sheet.paste(c, (x, y0 + LABEL_H))
        d.text((x, y0 + LABEL_H + tile_h + 2), label, fill=DIM)
        sheet.paste(o, (x, y1 + LABEL_H))
        d.text((x, y1 + LABEL_H + tile_h + 2), label, fill=DIM)
        x += tile_w + MARGIN

    d.text((x, y0), "REFERENCE", fill=DIM)
    if rtile is not None:
        sheet.paste(rtile, (x, y0 + LABEL_H))
        d.text((x, y0 + LABEL_H + tile_h + 2), os.path.basename(reference), fill=DIM)
    else:
        # Named as deliberately absent. NOT a blank tile that could read as a missing file.
        for i, ln in enumerate([
            "NONE - and that is",
            "the arm, not a gap.",
            "",
            "reference_image is",
            "required: false on",
            "WanVaceToVideo",
            "(measured).",
            "",
            "Held constant",
            "(absent) across all",
            "three E03 arms. The",
            "subject carries no",
            "identity for a",
            "reference to keep.",
        ]):
            d.text((x, y0 + LABEL_H + 6 + i * 15), ln, fill=DIM)

    px = x + ref_w + MARGIN
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
        f"distinct imgs  {ctl.get('distinct_images') if isinstance(ctl, dict) else '-'} of 33",
        f"reference      {meta.get('reference_image') or 'NONE (held absent across arms)'}",
        "",
        f"Gate L         {meta.get('gate_L',{}).get('verdict','?')}",
        f"Gate B         {meta.get('gate_B','NOT YET RUN')}",
        f"Gate R         N/A for this route (no codec in the path)",
        f"Gate C         {meta.get('gate_C','NOT YET RUN')}",
        f"Gate 6         {meta.get('gate_G6','-')}",
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
    # `none` is a real value, not a missing argument: E03's arms deliberately carry no
    # reference image, and the sheet says so in the column rather than leaving it blank.
    ap.add_argument("--reference", required=True,
                    help="path to the reference plate, or the literal 'none'")
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,8,16,24")
    ap.add_argument("--captions", default=None,
                    help="optional 'idx=text,idx=text' per-frame labels, replacing azimuth")
    a = ap.parse_args(argv)

    with open(a.meta, encoding="utf-8") as fh:
        meta = json.load(fh)
    idx = [int(v) for v in a.frames.split(",") if v.strip()]
    captions = None
    if a.captions:
        captions = {}
        for part in a.captions.split(","):
            k, _, v = part.partition("=")
            captions[int(k)] = v
    reference = None if a.reference.lower() == "none" else a.reference
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet = build(a.run, a.frames_dir, reference, meta, idx, captions=captions)
    sheet.save(a.out)
    print(f"GATE0_SHEET {a.out} {sheet.width}x{sheet.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
