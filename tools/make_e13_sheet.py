#!/usr/bin/env python
"""make_e13_sheet — the composed route's panel: references | output | provenance.

    <venv-python> tools\\make_e13_sheet.py --arm=A1 --seed=2026081351 \\
        --refs=outputs/E13/A1_refs/A1-reference-record.json \\
        --frames=outputs/E13/frames/A1-seed2026081351 \\
        --payload=outputs/E13/route/E13-A1-seed2026081351-payload-record.json \\
        --prompt-id=... --out=outputs/E13/sheets/E13-A1-seed1.png

facet ran four arms and two gates before it built a sheet like this, and when the sheet
finally existed the Director read the whole thesis off one panel. So it is built **before
any number is quoted**, and it carries its own provenance rather than depending on a caption.

Three bands, in the order the shot was made:

  references   what was handed to the tier — the four composited kit plates (A1), or
               sampled frames of the constructed reference clip (A2), each labelled with
               the SLOT it was sent in. `characterN` <-> slot binding is NOT VISIBLE, so
               the sheet shows what was SENT and claims nothing about what bound.
  output       what the model returned, sampled across the clip
  provenance   hashes, seed, prompt_id, gates, meters — every line derived from the run's
               own records, with `NOT RECORDED` where a record does not carry it

**Sheets locate; full size decides.** Tiles here are scaled to a common width so the bands
line up; the full-resolution frames stay on disk and are what the Director's eye reads.

Compensator (NAMED_COMPENSATORS): writes one PNG under `outputs/`. Compensator: delete it;
owner: the executor session. Inputs are read-only.
"""

import argparse
import glob
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TOOL_VERSION = "E13.1"

MARGIN = 10
LABEL_H = 16
BAND_H = 22
REF_W = 200
OUT_W = 320
BG = (24, 24, 26)
FG = (232, 232, 232)
DIM = (150, 150, 155)


def _fit(img, width):
    w, h = img.size
    return img.resize((width, max(1, round(h * width / w))), Image.LANCZOS)


def provenance_lines(payload, prompt_id, output_sha, refs, extra=None):
    """Every line derived from the run's own records; `NOT RECORDED` where absent.

    The fallback is the point: CLAUDE.md forbids a report carrying a placeholder shaped
    like evidence, so a missing field prints as missing rather than as a plausible value.
    """
    def g(d, *path, default="NOT RECORDED"):
        cur = d
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur if cur not in (None, "") else default

    p = payload.get("payload", {}) if isinstance(payload, dict) else {}
    lines = [
        f"experiment   {g(payload, 'experiment')}   arm {g(payload, 'arm')}",
        f"tier         {g(payload, 'tier')}",
        f"prompt_id    {prompt_id or 'NOT RECORDED'}",
        f"seed         {g(payload, 'seed')}   registered in {os.path.basename(str(g(payload, 'seed_registration', default='NOT RECORDED')))}",
        f"resolution   {p.get('model.resolution', 'NOT RECORDED')}  "
        f"ratio {p.get('model.ratio', 'NOT RECORDED')}  "
        f"duration {p.get('model.duration', 'NOT RECORDED')}s",
        f"watermark    {p.get('watermark', 'NOT RECORDED')}  (requested off)",
        f"negative     {str(p.get('model.negative_prompt', 'NOT RECORDED'))[:70]}",
        f"prompt sha   {str(g(payload, 'prompt_sha256'))[:32]}",
        f"output sha   {(output_sha or 'NOT RECORDED')[:32]}",
        f"slot order   {', '.join(g(payload, 'slot_order', default=[])) or 'NOT RECORDED'}",
        "slot binding characterN <-> slot is NOT VISIBLE; what is shown is what was SENT",
    ]
    for r in refs:
        lines.append(f"  {r['slot']:<7} {r['label']:<22} {r['sha'][:16]}")
    gates = g(payload, "gates", default={})
    if isinstance(gates, dict):
        for name in ("S_build_time", "CEILING_one_paid_node"):
            v = gates.get(name, {})
            lines.append(f"gate {name:<22} {v.get('verdict', 'NOT RECORDED')}")
        route = gates.get("ROUTE", {})
        lines.append(f"gate ROUTE                 {route.get('verdict', 'NOT RECORDED')}")
        lines.append(f"gate L                     {route.get('frame_legality_verdict', 'NOT RECORDED')}")
        lines.append(f"gate PAIR                  {str(g(payload, 'gate_pair_note'))[:64]}")
    for line in (extra or []):
        lines.append(line)
    return lines


def build(arm, ref_images, ref_labels, frame_paths, frame_labels, prov_lines, title):
    refs = [_fit(Image.open(p).convert("RGB"), REF_W) for p in ref_images]
    outs = [_fit(Image.open(p).convert("RGB"), OUT_W) for p in frame_paths]

    ref_h = max((im.size[1] for im in refs), default=0)
    out_h = max((im.size[1] for im in outs), default=0)
    per_row = max(1, min(len(outs), 4))
    rows = (len(outs) + per_row - 1) // per_row

    W = max(MARGIN + len(refs) * (REF_W + MARGIN),
            MARGIN + per_row * (OUT_W + MARGIN), 900)
    prov_h = MARGIN + len(prov_lines) * 14 + MARGIN
    H = (BAND_H + MARGIN + BAND_H + ref_h + LABEL_H + MARGIN
         + BAND_H + rows * (out_h + LABEL_H + MARGIN) + MARGIN + BAND_H + prov_h)

    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    y = 4
    d.text((MARGIN, y), title, fill=FG)
    y += BAND_H + MARGIN

    d.text((MARGIN, y), "REFERENCES — what was sent, in slot order", fill=DIM)
    y += BAND_H
    x = MARGIN
    for im, lab in zip(refs, ref_labels):
        sheet.paste(im, (x, y))
        d.text((x, y + im.size[1] + 2), lab[:34], fill=DIM)
        x += REF_W + MARGIN
    y += ref_h + LABEL_H + MARGIN

    d.text((MARGIN, y), "OUTPUT — sampled frames (full size on disk decides)", fill=DIM)
    y += BAND_H
    for r in range(rows):
        x = MARGIN
        for c in range(per_row):
            i = r * per_row + c
            if i >= len(outs):
                break
            sheet.paste(outs[i], (x, y))
            d.text((x, y + outs[i].size[1] + 2), frame_labels[i][:44], fill=DIM)
            x += OUT_W + MARGIN
        y += out_h + LABEL_H + MARGIN

    d.text((MARGIN, y), "PROVENANCE", fill=DIM)
    y += BAND_H
    for line in prov_lines:
        d.text((MARGIN, y), line[:150], fill=FG)
        y += 14
    return sheet


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--frames", required=True, help="the extracted output frames dir")
    ap.add_argument("--payload", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--refs", default=None, help="A1: the reference record JSON")
    ap.add_argument("--ref-frames", default=None,
                    help="A2: the reference CLIP's frames dir (sampled)")
    ap.add_argument("--prompt-id", default=None)
    ap.add_argument("--sample", default="0,37,75,112,149",
                    help="output frame indices (argparse eats leading minus signs)")
    a = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    with open(a.payload, encoding="utf-8") as fh:
        payload = json.load(fh)
    fr = json.load(open(os.path.join(a.frames, "frames.json"), encoding="utf-8"))

    ref_images, ref_labels, ref_rows = [], [], []
    if a.refs:
        rec = json.load(open(a.refs, encoding="utf-8"))
        for v in rec["views"]:
            ref_images.append(v["composited"])
            ref_labels.append(f"{v['slot']}  {v['view']}  az {v.get('azimuth_deg')}")
            ref_rows.append({"slot": v["slot"], "label": f"{v['view']} (kit)",
                             "sha": v["composited_sha256"]})
    elif a.ref_frames:
        paths = sorted(glob.glob(os.path.join(a.ref_frames, "*.png")))
        picks = [0, len(paths) // 3, 2 * len(paths) // 3, len(paths) - 1]
        for i in picks:
            ref_images.append(paths[i])
            ref_labels.append(f"video1  constructed clip f{i}")
        ref_rows.append({"slot": "video1", "label": f"constructed clip ({len(paths)}f)",
                         "sha": "see cascade_decode_compare.json"})

    idx = [int(v) for v in a.sample.split(",")]
    frame_paths = [os.path.join(a.frames, f"{i:05d}.png") for i in idx]
    frame_labels = [f"f{i}  ({fr['stream']['width']}x{fr['stream']['height']} "
                    f"@ {fr['stream']['fps']} fps)" for i in idx]

    prov = provenance_lines(
        payload, a.prompt_id, fr.get("clip_sha256"), ref_rows,
        extra=[f"clip         {fr['n_frames']} frames, {fr['distinct_frames']} distinct, "
               f"{fr['clip_bytes']} bytes",
               f"stream       {fr['stream']['line'][:110]}"])

    title = (f"E13 {a.arm} seed {a.seed} — references | output | provenance   "
             f"(diagnostics only; the Director's eye is the verdict)")
    sheet = build(a.arm, ref_images, ref_labels, frame_paths, frame_labels, prov, title)
    sheet.save(a.out)
    print(f"SHEET_OK {a.out}  {sheet.size[0]}x{sheet.size[1]}")
    return a.out


if __name__ == "__main__":
    main()
