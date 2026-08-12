#!/usr/bin/env python
r"""make_startframe_sheet — Gate 0 for a route whose only conditioning is one image.

    python tools\make_startframe_sheet.py --start=<start_frame.png>
           --frames=<lossless dir> --meta=<payload record.json> --out=<sheet.png>
           [--at=0,8,16,32,48,64] [--measurements=<measure_clip.json>] [--prompt-id=...]

Gate 0's rule is unchanged: **no number is quoted for an arm until this sheet exists.** The
columns change because the route does. There is no control channel to show — that absence
IS the experiment — so the panel is

    START FRAME (the authored conditioning image) | OUTPUT at chosen frames | PROVENANCE

**Why this is a new tool rather than a flag on `make_gate0_sheet`.** That sheet's
provenance panel carries E02-era literals: `Wan 2.1 VACE 14B fp16`, `uni_pc / simple / 30
steps / cfg 6`, `distinct imgs ... of 33`, and a bridge-fidelity note about a control
channel. Pointed at any later run it would print those beside that run's seed — a report
containing a placeholder shaped like evidence, which is the exact defect E10's closing
lesson names: *a tool that names an experiment in a literal is a tool that will lie the
first time it is reused.* Nothing here is a literal. Every provenance line is read from the
run's own payload record, and a value the record does not carry prints `NOT RECORDED`
rather than a plausible default.

Sheets locate; full size decides. Output tiles are the frames' own pixels scaled by one
factor, and the scale is printed on the sheet.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw  # noqa: E402

MARGIN = 10
LABEL_H = 18
HDR_H = 24
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (140, 140, 150)
MISSING = "NOT RECORDED"


def _rgb(path):
    im = Image.open(path)
    if im.mode == "RGBA":
        flat = Image.new("RGB", im.size, (0, 0, 0))
        flat.paste(im, mask=im.split()[3])
        return flat
    return im.convert("RGB")


def _get(meta, *path, default=MISSING):
    """Walk a dotted path through the record, or return `NOT RECORDED`.

    The default is a string that cannot be mistaken for a measurement. A sheet that
    printed `0`, `-`, or an empty cell for a value nobody recorded would be asserting
    something about the run.
    """
    cur = meta
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur if cur is not None else default


def provenance_lines(meta, prompt_id=None, measurements=None):
    """Every line of the provenance column, derived from the record. No literals.

    The one value not in the payload record is the `prompt_id`, which does not exist until
    the run is submitted; it is passed in and prints `NOT RECORDED` when it is not.
    """
    models = _get(meta, "models", default={})
    models = models if isinstance(models, dict) else {}
    traj = _get(meta, "trajectory", default={})
    traj = traj if isinstance(traj, dict) else {}

    def tv(name):
        rec = traj.get(name)
        return rec.get("value") if isinstance(rec, dict) else MISSING

    lines = [
        f"experiment     {_get(meta, 'experiment')}",
        f"route          {_get(meta, 'route')}",
        f"prompt_id      {prompt_id or MISSING}",
        "",
        f"unet (high)    {models.get('unet_high_noise', models.get('unet', MISSING))}",
        f"unet (low)     {models.get('unet_low_noise', MISSING)}",
        f"text encoder   {models.get('clip', MISSING)}",
        f"vae            {models.get('vae', MISSING)}",
        f"loras          {models.get('loras', MISSING)}",
        "",
        f"frame          {_get(meta, 'resolution')} x {_get(meta, 'length')} "
        f"@ {_get(meta, 'fps')} fps",
        f"seed           {_get(meta, 'seed')}",
        f"steps          {tv('steps')}   split at {tv('split_step')}",
        f"cfg            {tv('cfg')}   shift {tv('shift')}",
        f"sampler        {tv('sampler_name')} / {tv('scheduler')}",
        f"payload sha256 {str(_get(meta, 'payload_sha256', default=''))[:32]}",
        "",
        f"start image    {_get(meta, 'start_image', 'server_name')}",
        f"fit            {_get(meta, 'start_image', 'fit')}",
        "",
        f"Gate PIN       {_get(meta, 'gate_PIN', 'verdict')}",
        f"Gate S         {_get(meta, 'gate_S', 'verdict')}",
        f"Gate L         {_get(meta, 'gate_L', 'verdict')}",
        f"Gate ROUTE     {_get(meta, 'gate_ROUTE_built', 'verdict')}",
        f"Gate B         {_get(meta, 'gate_B', default='NOT YET RUN')}",
        "",
        "NO DRIVING SIGNAL — no pose video, no control video,",
        "no reference image, no clip-vision. Checked in code by",
        "build_i2v_payload.verify_topology, not by reading.",
    ]
    if isinstance(measurements, dict):
        lines += ["", "MEASURED (diagnostics; they gate nothing)"]
        for k, v in measurements.items():
            lines.append(f"{k:<14} {v}")
    return lines


def build(start_path, frame_paths, indices, meta, prompt_id=None, measurements=None,
          captions=None, scale=0.5):
    start = _rgb(start_path)
    tiles = []
    for fi in indices:
        if fi >= len(frame_paths):
            continue
        tiles.append((fi, _rgb(frame_paths[fi])))
    if not tiles:
        raise SystemExit("no output frames at the requested indices; the sheet would be "
                         "a picture of the start frame beside nothing")

    def fit(im):
        return im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                         Image.LANCZOS)

    stile = fit(start)
    otiles = [(fi, fit(im)) for fi, im in tiles]
    tw, th = otiles[0][1].width, otiles[0][1].height

    per_row = 3
    rows = (len(otiles) + per_row - 1) // per_row
    grid_w = per_row * (tw + MARGIN)
    lines = provenance_lines(meta, prompt_id, measurements)

    width = MARGIN + stile.width + MARGIN + grid_w + 470
    height = max(HDR_H + MARGIN + LABEL_H + stile.height + MARGIN,
                 HDR_H + MARGIN + rows * (LABEL_H + th + LABEL_H) + MARGIN,
                 HDR_H + MARGIN + len(lines) * 15 + MARGIN)

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6),
           f"{_get(meta, 'experiment')}  -  GATE 0 SHEET   "
           f"start frame | output | provenance      "
           f"(tiles at {scale:g}x of {start.width}x{start.height}; "
           f"sheets locate, full size decides)", fill=FG)

    y0 = HDR_H + MARGIN
    d.text((MARGIN, y0), "START FRAME  (the GLB, staged and rendered - the only image "
                         "conditioning)", fill=DIM)
    sheet.paste(stile, (MARGIN, y0 + LABEL_H))
    d.text((MARGIN, y0 + LABEL_H + stile.height + 2),
           os.path.basename(start_path), fill=DIM)

    gx = MARGIN + stile.width + MARGIN
    d.text((gx, y0), "OUTPUT  (everything below frame 0 is the model's)", fill=DIM)
    for i, (fi, im) in enumerate(otiles):
        cx = gx + (i % per_row) * (tw + MARGIN)
        cy = y0 + LABEL_H + (i // per_row) * (LABEL_H + th + LABEL_H)
        sheet.paste(im, (cx, cy))
        cap = f"f{fi:03d}"
        if captions and fi in captions:
            cap += f"  {captions[fi]}"
        d.text((cx, cy + th + 2), cap, fill=DIM)

    px = gx + grid_w + MARGIN
    d.text((px, y0), "PROVENANCE", fill=DIM)
    yy = y0 + LABEL_H
    for ln in lines:
        d.text((px, yy), ln, fill=FG if ln.startswith(("Gate", "NO DRIVING")) else DIM)
        yy += 15
    return sheet


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--at", default="0,8,16,32,48,64",
                    help="frame indices (argparse eats leading minus signs: --at=0,8,16)")
    ap.add_argument("--prompt-id", default=None)
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--captions", default=None, help="idx=text,idx=text")
    ap.add_argument("--measurements", default=None,
                    help="a measure_clip record; a few of its headline numbers are "
                         "printed under the provenance, labelled as diagnostics")
    a = ap.parse_args(argv)

    with open(a.meta, encoding="utf-8") as fh:
        meta = json.load(fh)

    names = [n for n in os.listdir(a.frames)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    paths = [os.path.join(a.frames, n)
             for n in sorted(names, key=lambda n: int(os.path.splitext(n)[0]))]

    measurements = None
    if a.measurements:
        with open(a.measurements, encoding="utf-8") as fh:
            rec = json.load(fh)
        arm = rec["arms"][0]
        measurements = {
            "frames": f"{arm['n_frames']}, {arm['distinct']['n_distinct']} distinct",
            "d(frame) med": round(arm["frame_deltas"]["stats"]["median"], 3),
            "d(luma) med": round(arm["luma"]["stats"]["median"], 3),
            "corr to f0": round(arm["similarity_to_first"]["per_frame_correlation"][-1], 4),
            "horizon": f"found on {arm['horizon']['n_found']}/{arm['n_frames']}",
        }

    captions = None
    if a.captions:
        captions = {}
        for part in a.captions.split(","):
            k, _, v = part.partition("=")
            captions[int(k)] = v

    idx = [int(v) for v in a.at.split(",") if v.strip()]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet = build(a.start, paths, idx, meta, prompt_id=a.prompt_id,
                  measurements=measurements, captions=captions, scale=a.scale)
    sheet.save(a.out)
    print(f"STARTFRAME_SHEET {a.out} {sheet.width}x{sheet.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
