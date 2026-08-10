#!/usr/bin/env python
"""make_sheet — the panel the Director reads the run off.

    python tools/make_sheet.py --run=<run dir> --out=<sheet.png> [--frames=0,8,16,24]

facet ran four arms and two gates before building its comparison sheet, and when the
sheet finally existed the Director read the whole thesis off one panel. E01 generates
nothing, so there is no *output* or *reference* column yet — what exists is the
**control** stack and its **provenance**, and those are what this lays out.

Sheets locate; full size decides. Every tile here is written at native resolution with
no resampling, so what is on the sheet is what is in the file.

Runs outside Blender (Pillow).
"""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

MARGIN = 8
LABEL_H = 18
HEADER_H = 74


def _load_rgb(path):
    img = Image.open(path)
    if img.mode == "1":
        img = img.convert("L")
    return img.convert("RGB")


def build_sheet(run_dir, frames=None, channels=None):
    manifest = json.load(open(os.path.join(run_dir, "manifest.json"), encoding="utf-8"))
    count = manifest["frame_count"]
    if frames is None:
        n = min(5, count)
        frames = [round(i * (count - 1) / max(n - 1, 1)) for i in range(n)]
    if channels is None:
        channels = [c for c in manifest["channel_dirs"] if os.path.isdir(os.path.join(run_dir, c))]

    first = _load_rgb(os.path.join(run_dir, channels[0], f"{frames[0]:05d}.png"))
    tw, th = first.size

    cols, rows = len(channels), len(frames)
    W = MARGIN + cols * (tw + MARGIN)
    H = HEADER_H + MARGIN + rows * (th + LABEL_H + MARGIN)
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)

    p3 = manifest.get("p3") or {}
    prov = manifest.get("provenance", {})
    header = [
        f"{manifest['spec']['name']}  ·  {os.path.basename(manifest['asset']['path'])}"
        f"  ·  sha256 {manifest['asset']['sha256'][:16]}…",
        f"{manifest['resolution'][0]}x{manifest['resolution'][1]}  ·  {count} frames  ·  "
        f"generator {manifest['generator_profile']['name']} "
        f"(/{manifest['generator_profile']['dim_divisor']}, "
        f"{manifest['generator_profile']['frame_form']})  ·  "
        f"engine {manifest['spec']['render']['engine']} @ {manifest['spec']['render']['samples']} spp"
        f"  ·  Blender {prov.get('version', '?')}",
        f"G1 {manifest['gates']['G1']['verdict']} · G2 {manifest['gates']['G2']['verdict']} · "
        f"G4 {manifest['gates']['G4']['verdict']} (max delta "
        f"{manifest['gates']['G4']['max_delta_px']} px) · G5 {manifest['gates']['G5']['verdict']}",
        (
            "P3 mean |per-frame - per-shot| on geometry = "
            f"{p3.get('pixel_weighted_mean_abs'):.4f} "
            f"({p3.get('pixel_weighted_mean_abs') * 255:.1f}/255)  ·  worst frame "
            f"{p3.get('worst_frame_index')} = {p3.get('worst_frame_mean_abs'):.4f}  ·  "
            f"z-range swing {p3.get('z_range_swing'):.3f}x"
        ) if p3.get("pixel_weighted_mean_abs") is not None else "P3 NOT COMPUTED",
    ]
    for i, line in enumerate(header):
        draw.text((MARGIN, 6 + i * 16), line, fill=(215, 215, 220))

    for r, f in enumerate(frames):
        y = HEADER_H + MARGIN + r * (th + LABEL_H + MARGIN)
        for c, chan in enumerate(channels):
            x = MARGIN + c * (tw + MARGIN)
            path = os.path.join(run_dir, chan, f"{f:05d}.png")
            if not os.path.isfile(path):
                draw.rectangle([x, y, x + tw, y + th], outline=(90, 40, 40))
                draw.text((x + 4, y + 4), "MISSING", fill=(220, 90, 90))
            else:
                sheet.paste(_load_rgb(path), (x, y))
            label = f"{chan}  f{f:03d}"
            if chan == "p3_diff":
                stats = next((s for s in p3.get("per_frame", []) if s["frame"] == f), None)
                if stats:
                    label += f"  mean {stats['mean_abs']:.3f}  max {stats['max_abs']:.3f}"
            draw.text((x + 2, y + th + 3), label, fill=(170, 170, 178))
    return sheet


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    args = {}
    for token in argv:
        key, _, value = token[2:].partition("=")
        args[key] = value
    frames = [int(v) for v in args["frames"].split(",")] if args.get("frames") else None
    channels = args["channels"].split(",") if args.get("channels") else None
    sheet = build_sheet(args["run"], frames=frames, channels=channels)
    out = args["out"]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sheet.save(out)
    print("SHEET " + json.dumps({"path": os.path.abspath(out), "size": list(sheet.size)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
