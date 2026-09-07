#!/usr/bin/env python
"""make_gate0_sheet — the control | output | reference | provenance panel.

    <venv-python> tools/make_gate0_sheet.py --run=<control dir> --frames-dir=<output frames>
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
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import json
import os
import sys
import textwrap

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from composite_reference import parse_plate  # noqa: E402
from measure_lift import gate_listing_pairing  # noqa: E402
from sheet_compose import (SHEET_PLATE, SheetPopulationError,  # noqa: E402
                           font as sheet_font, frames_by_number, load_rgb_over_plate,
                           max_text_width, require_frames)

MARGIN = 10
LABEL_H = 18
HDR_H = 22
LINE_H = 16
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (140, 140, 150)
MISSING = "NOT RECORDED"
PROV_FONT_SIZE = 13
HDR_FONT_SIZE = 15



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

def _rgb(path, plate=SHEET_PLATE):
    """One tile, composited over the NAMED plate. See `sheet_compose.SHEET_PLATE`."""
    return load_rgb_over_plate(path, plate)[0]


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


def _sha_text(*candidates):
    """First non-empty candidate, truncated; else NOT RECORDED (F-6f968906)."""
    for c in candidates:
        if c in (None, "", MISSING):
            continue
        return str(c)[:32]
    return MISSING


def reference_display(meta):
    """Short form for the provenance `reference` line (F-061259da).

    A dict `{"path": ..., "sha256": ...}` used to render as the whole dict and overrun the
    column; a long absolute path did the same. Basename (or the path key's basename) is
    what a reader needs to identify the file; the sha rides the next line.
    """
    ref = meta.get("reference_image")
    if not ref:
        return "NONE (recorded absent)"
    if isinstance(ref, dict):
        path = ref.get("path") or ref.get("file") or ""
        if path:
            return os.path.basename(str(path))
        sha = ref.get("sha256")
        return (str(sha)[:32] if sha else MISSING)
    return os.path.basename(str(ref))


def provenance_lines(meta, output_sha=None, control_sha=None, reference_sha=None):
    """Every line of the provenance panel, derived from the run's record. A value the
    record does not carry prints `NOT RECORDED`. This panel used to bake E02-era
    literals — model, sampler line, a control denominator, a Gate R route claim and a
    bridge-fidelity note — the stale-label defect whose third sighting (E11) named this
    fix.

    F-6f968906: also prints `output sha` and per-input `control sha` / `reference sha`,
    the shape `make_e13_sheet.provenance_lines` already writes — from the record when
    present, else `NOT RECORDED`, or from the optional overrides the caller measured.
    """
    models = _get(meta, "models", default={})
    models = models if isinstance(models, dict) else {}
    ctl = meta.get("control")
    is_ctl = isinstance(ctl, dict)
    ctl_d = ctl if is_ctl else {}
    ref = meta.get("reference_image")
    ref_d = ref if isinstance(ref, dict) else {}

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
        f"output sha     {_sha_text(output_sha, meta.get('output_sha256'), meta.get('clip_sha256'))}",
        "",
        f"control bridge {cv('bridge') if is_ctl else (str(ctl) if ctl else 'NONE - no control_video recorded')}",
        f"normalization  {cv('normalization')}",
        f"polarity       {cv('polarity')}",
        f"distinct imgs  {cv('distinct_images')} of {cv('total_images')}",
        f"control sha    {_sha_text(control_sha, ctl_d.get('video_sha256'), ctl_d.get('source_frames_sha256'), meta.get('control_sha256'))}",
        f"reference      {reference_display(meta)}",
        f"reference sha  {_sha_text(reference_sha, ref_d.get('sha256'), meta.get('reference_sha256'))}",
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


def build(control_dir, frames_dir, reference, meta, frame_idx, tile_h=416, captions=None,
          plate=SHEET_PLATE):
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
    cnames = sorted(n for n in os.listdir(control_dir) if n.lower().endswith(".png"))
    onames = sorted(n for n in os.listdir(frames_dir) if n.lower().endswith(".png"))
    # ---- ANDON. The control and output listings were two populations indexed by the same
    #      `fi`, with nothing checking they name the same frames; and a requested index
    #      past either was dropped in SILENCE (`continue`), on the panel the whole judging
    #      discipline rests on. `make_identity_sheet` was given this refusal in wave 3.
    #      WAVE 25 (F-2f2c19a9): the POPULATION gate now fires FIRST. `frames_by_number` —
    #      the ONE home for "the numbered frame population, with a stray refusal" — ran two
    #      lines BELOW this pairing gate, so a `strip_every8.png` in the control directory
    #      and not the output one was refused as a listing disagreement rather than as the
    #      stray it is, naming an andon that is not the condition. `render_pose_sticks`
    #      writes that file beside its `NNNNN.png` frames, so it is ordinary output.
    cby = frames_by_number(cnames, where=control_dir, what="control frame(s)")
    oby = frames_by_number(onames, where=frames_dir, what="output frame(s)")
    gate_listing_pairing({"control": cnames, "output": onames})
    # ---- and the bound is the frames' own NUMBERS, not their POSITION in the listing.
    #      Measured 2026-09-04 on a control and output both numbered 00001..00003 with
    #      `--frames=0,1,2`: exit 0, a sheet written, tiles captioned f000/f001/f002 cut
    #      from 00001/00002/00003 — on a run that holds no frame 0 — while `--frames=3`,
    #      the frame the run DOES hold, was refused. The flag read backwards from what its
    #      own caption promises. `sheet_compose.require_frames`'s `numbers=` mode was built
    #      in wave 10 for exactly this and landed in one of six callers
    #      (`make_identity_sheet`); this is the panel the whole judging discipline rests on.
    require_frames(frame_idx, cnames, what="control frame(s)", where=control_dir,
                   numbers=sorted(cby))
    require_frames(frame_idx, onames, what="output frame(s)", where=frames_dir,
                   numbers=sorted(oby))
    ref = _rgb(reference, plate) if reference else None

    def fit(im):
        s = tile_h / im.height
        return im.resize((max(1, round(im.width * s)), tile_h), Image.LANCZOS)

    cols = []
    for fi in frame_idx:
        # Indexed by NUMBER, not by position: `cnames[fi]` depends on where the run's
        # numbering starts and on what else happens to be in the directory.
        c = fit(_rgb(os.path.join(control_dir, cby[fi]), plate))
        o = fit(_rgb(os.path.join(frames_dir, oby[fi]), plate))
        cols.append((frame_caption(fi, captions), c, o))

    rtile = fit(ref) if ref is not None else None
    ref_w = rtile.width if rtile is not None else 220
    tile_w = cols[0][1].width
    # F-7f9eb100: same resolved TrueType face as dailies/`sheet_compose`, not PIL's
    # default bitmap — overflow budgets must match what CI actually renders.
    f_body = sheet_font("arial.ttf", PROV_FONT_SIZE)
    f_hdr = sheet_font("arial.ttf", HDR_FONT_SIZE)
    lines = provenance_lines(meta)
    # F-061259da: size the provenance column to the measured text, not a fixed +430.
    prov_w = int(max_text_width(
        [(ln, f_body) for ln in lines if ln]
        + [("PROVENANCE", f_hdr), (header_text(meta), f_hdr)]))
    tile_row_w = MARGIN + len(cols) * (tile_w + MARGIN) + ref_w + MARGIN + prov_w + MARGIN
    width = max(tile_row_w, int(MARGIN + max_text_width([(header_text(meta), f_hdr)])
                                + MARGIN))
    y0 = HDR_H + MARGIN
    tile_h_driven = HDR_H + MARGIN + LABEL_H + tile_h + LABEL_H + tile_h + LABEL_H + MARGIN * 3
    # F-0cd6a323: provenance can outgrow the tile column at small tile_h.
    prov_driven = y0 + LABEL_H + LINE_H * len(lines) + MARGIN
    height = max(tile_h_driven, prov_driven)

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6), header_text(meta), fill=FG, font=f_hdr)

    ctl_meta = meta.get("control")
    ctl_desc = (ctl_meta.get("polarity", MISSING) if isinstance(ctl_meta, dict)
                else "NONE - this arm has no control_video")
    d.text((MARGIN, y0), f"CONTROL  ({ctl_desc})", fill=DIM, font=f_body)
    y1 = y0 + LABEL_H + tile_h + LABEL_H
    d.text((MARGIN, y1), output_heading(meta), fill=DIM, font=f_body)

    x = MARGIN
    for label, c, o in cols:
        sheet.paste(c, (x, y0 + LABEL_H))
        d.text((x, y0 + LABEL_H + tile_h + 2), label, fill=DIM, font=f_body)
        sheet.paste(o, (x, y1 + LABEL_H))
        d.text((x, y1 + LABEL_H + tile_h + 2), label, fill=DIM, font=f_body)
        x += tile_w + MARGIN

    d.text((x, y0), "REFERENCE", fill=DIM, font=f_body)
    if rtile is not None:
        sheet.paste(rtile, (x, y0 + LABEL_H))
        d.text((x, y0 + LABEL_H + tile_h + 2), os.path.basename(reference),
               fill=DIM, font=f_body)
    else:
        # Named as deliberately absent. NOT a blank tile that could read as a missing file.
        for i, ln in enumerate(reference_absent_lines(meta)):
            d.text((x, y0 + LABEL_H + 6 + i * LINE_H), ln, fill=DIM, font=f_body)

    px = x + ref_w + MARGIN
    d.text((px, y0), "PROVENANCE", fill=DIM, font=f_hdr)
    yy = y0 + LABEL_H
    for ln in lines:
        d.text((px, yy), ln, fill=DIM if not ln.startswith("Gate") else FG, font=f_body)
        yy += LINE_H
    return sheet


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the Gate 0 panel — control | output | reference | provenance — "
                    "produced before any metric is quoted",
        epilog=HALT_EPILOG)
    ap.add_argument("--run", required=True,
                    help="the control run directory; its channel frames are the control "
                         "column and its manifest supplies the azimuths")
    ap.add_argument("--frames-dir", required=True,
                    help="the run's returned output frames, the output column")
    # `none` is a real value, not a missing argument: E03's arms deliberately carry no
    # reference image, and the sheet says so in the column rather than leaving it blank.
    ap.add_argument("--reference", required=True,
                    help="path to the reference plate, or the literal 'none'")
    ap.add_argument("--meta", required=True,
                    help="the run's payload record; every provenance line is read off it")
    ap.add_argument("--out", required=True, help="the sheet image to write")
    ap.add_argument("--frames", default="0,8,16,24",
                    help="the frame indices every column is sampled at (argparse eats "
                         "leading minus signs: pass as --frames=0,8,16)")
    ap.add_argument("--captions", default=None,
                    help="optional 'idx=text,idx=text' per-frame labels, replacing azimuth")
    # DECLARED, not only read. `main` read `a.sheet_plate` and this line did not exist:
    # measured 2026-09-04, every invocation of this tool died with
    # `AttributeError: 'Namespace' object has no attribute 'sheet_plate'` before
    # `os.makedirs` and before a tile was cut — on the one panel Gate 0 says no number may
    # be quoted without. The four sibling sheets took the same wave-8 change and each
    # added the flag; this one got the call site alone, and no test drove `main`.
    ap.add_argument("--sheet-plate", default=",".join(str(v) for v in SHEET_PLATE),
                    help="R,G,B of the plate an RGBA tile is composited over before it is "
                         "drawn. Named and recorded, never assumed: the reference column "
                         "of a panel must not show the character against a plate the "
                         "route did not submit")
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
    plate = parse_plate(a.sheet_plate, SheetPopulationError, flag="--sheet-plate")
    # ---- the output directory is created only once every in-tool andon above
    #      has fired -- the plate parse included.
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet = build(a.run, a.frames_dir, reference, meta, idx, captions=captions,
                  plate=plate)
    sheet.save(a.out)
    print(f"GATE0_SHEET {a.out} {sheet.width}x{sheet.height} "
          f"plate={tuple(int(v) for v in plate)}")
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MAKE_GATE0_SHEET")
