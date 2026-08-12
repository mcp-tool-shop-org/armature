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

Sheets locate; full size decides. Every tile is native resolution — frames go on the
sheet at their own size, no resampling — so what is on the sheet is what is in the file.

**2026-08-12 — the literals are gone.** The provenance panel carried E02-era literals
(a model name, a sampler line, "of 33", a Gate R route claim, a bridge-fidelity note),
the header defaulted a missing experiment name to "E02", the reference-absent column
baked E03's rationale, and the default caption derived an azimuth from an orbit the tool
assumed. The E11 report logged the third stale-label sighting and named this fix. Every
line now derives from the run's own record, and a value the record does not carry prints
`NOT RECORDED` — the `make_startframe_sheet` convention, whose docstring records why it
was born separate.
"""

import argparse
import json
import os
import textwrap

from PIL import Image, ImageDraw

MARGIN = 10
LABEL_H = 18
HDR_H = 22
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
    """Walk a dotted path through the record, or return `NOT RECORDED` — a string that
    cannot be mistaken for a measurement (the `make_startframe_sheet` convention)."""
    cur = meta
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur if cur is not None else default


def header_text(meta):
    """The sheet header, derived. The old header defaulted a missing experiment name to
    "E02" — a fallback that names an experiment is a placeholder shaped like evidence."""
    return (f"{_get(meta, 'experiment')} {_get(meta, 'arm')}  -  "
            f"GATE 0 SHEET   control | output | reference | provenance")


def output_heading(meta):
    """The OUTPUT column heading, from the record. It used to bake E02's model name."""
    return f"OUTPUT  ({_get(meta, 'models', 'unet')})"


def frame_caption(fi, captions=None):
    """Per-frame caption. The old default derived an azimuth from the frame count — an
    orbit assumption baked into the tool, printing angles that never happened on any
    non-orbiting run. Azimuth (or anything else) now arrives only via `captions`."""
    if captions is not None and fi in captions:
        return f"f{fi:03d}  {captions[fi]}"
    return f"f{fi:03d}"


def reference_absent_lines(meta):
    """The reference column when the run deliberately carries none. The old block baked
    E03's rationale into every such sheet; the reason now comes from the run's record
    (`reference_absent_reason`) or prints `NOT RECORDED`."""
    return (["NONE - deliberately", "absent, not a gap.", ""]
            + textwrap.wrap(f"reason: {_get(meta, 'reference_absent_reason')}", width=20))


def provenance_lines(meta):
    """Every line of the provenance panel, derived from the run's record. A value the
    record does not carry prints `NOT RECORDED`. This panel used to bake E02-era
    literals — model, sampler line, a control denominator, a Gate R route claim and a
    bridge-fidelity note — the stale-label defect whose third sighting (E11) named this
    fix."""
    models = _get(meta, "models", default={})
    models = models if isinstance(models, dict) else {}
    ctl = meta.get("control")
    is_ctl = isinstance(ctl, dict)
    ctl_d = ctl if is_ctl else {}

    def cv(key):
        return ctl_d.get(key, MISSING) if is_ctl else "-"

    lines = [
        f"arm            {_get(meta, 'arm')}",
        f"prompt_id      {_get(meta, 'prompt_id')}",
        f"model          {models.get('unet', MISSING)}",
        f"text encoder   {models.get('clip', MISSING)}",
        f"vae            {models.get('vae', MISSING)}",
        f"frame          {_get(meta, 'resolution')} x {_get(meta, 'length')} @ "
        f"{_get(meta, 'fps')}fps",
        f"seed           {_get(meta, 'seed')}",
        f"sampler        {_get(meta, 'sampler_name')} / {_get(meta, 'scheduler')} / "
        f"{_get(meta, 'steps')} steps / cfg {_get(meta, 'cfg')}",
        f"payload sha256 {str(_get(meta, 'payload_sha256', default=''))[:32]}",
        "",
        f"control bridge {cv('bridge') if is_ctl else (str(ctl) if ctl else 'NONE - no control_video recorded')}",
        f"normalization  {cv('normalization')}",
        f"polarity       {cv('polarity')}",
        f"distinct imgs  {cv('distinct_images')} of {cv('total_images')}",
        f"reference      {meta.get('reference_image') or 'NONE (recorded absent)'}",
        "",
        f"Gate L         {_get(meta, 'gate_L', 'verdict')}",
        f"Gate B         {_get(meta, 'gate_B', default='NOT YET RUN')}",
        f"Gate R         {_get(meta, 'gate_R')}",
        f"Gate C         {_get(meta, 'gate_C', default='NOT YET RUN')}",
        f"Gate 6         {_get(meta, 'gate_G6')}",
    ]
    if is_ctl:
        lines += ["", f"bridge fidelity {ctl_d.get('bridge_fidelity', MISSING)}"]
    return lines


def build(control_dir, frames_dir, reference, meta, frame_idx, tile_h=416, captions=None):
    """Assemble the panel.

    `reference` may be None. E03 runs with **no reference image at all** — held constant
    (absent) across all three arms, which is legal (`WanVaceToVideo.reference_image` is
    `required: false`, measured) and correct, because its subject carries no identity for a
    reference to preserve. The column is then labelled as deliberately absent rather than
    filled with a stand-in: a sheet must not contain a placeholder shaped like evidence.

    `captions` adds a per-frame label beside the frame index. The default is the bare
    index: the tool used to compute an azimuth from the frame count, which was E02's
    orbit baked in — on a run that does not orbit it printed angles that never happened.
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
        cols.append((frame_caption(fi, captions), c, o))

    rtile = fit(ref) if ref is not None else None
    ref_w = rtile.width if rtile is not None else 220
    tile_w = cols[0][1].width
    width = MARGIN + len(cols) * (tile_w + MARGIN) + ref_w + MARGIN + 430
    height = HDR_H + MARGIN + LABEL_H + tile_h + LABEL_H + tile_h + LABEL_H + MARGIN * 3

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6), header_text(meta), fill=FG)

    y0 = HDR_H + MARGIN
    ctl_meta = meta.get("control")
    ctl_desc = (ctl_meta.get("polarity", MISSING) if isinstance(ctl_meta, dict)
                else "NONE - this arm has no control_video")
    d.text((MARGIN, y0), f"CONTROL  ({ctl_desc})", fill=DIM)
    y1 = y0 + LABEL_H + tile_h + LABEL_H
    d.text((MARGIN, y1), output_heading(meta), fill=DIM)

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
        for i, ln in enumerate(reference_absent_lines(meta)):
            d.text((x, y0 + LABEL_H + 6 + i * 15), ln, fill=DIM)

    px = x + ref_w + MARGIN
    d.text((px, y0), "PROVENANCE", fill=DIM)
    yy = y0 + LABEL_H
    for ln in provenance_lines(meta):
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
