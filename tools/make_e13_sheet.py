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

from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "E13.1"


class E13SheetError(ArmatureError):
    """This sheet cannot be built from what it was pointed at.

    The file declared NO typed refusal at all before wave 16, which is also why the
    write-ordering ratchet in `tests/test_instrument_write_ordering.py` had no entry for it:
    a module enters that census only when it both refuses and writes, and this one only
    wrote. It defines no `__init__` — the base stores what it is passed
    (`armature_core/errors.py::ArmatureError.__init__`).
    """


def reference_picks(n):
    """The frame indices sampled from the constructed reference clip — N of them, distinct.

    F-9297b54f, wave 16. This was the literal `[0, n // 3, 2 * n // 3, n - 1]`, inlined and
    indexed with no emptiness check. Measured on the base tree: for `n == 0` the first pick
    is `paths[0]`, a bare `IndexError` after `os.makedirs` has already run; for `n` of 1, 2
    and 3 the picks are `[0,0,0,0]`, `[0,0,1,1]` and `[0,1,2,2]`, so the REFERENCES band
    showed 4, 2 and 3 DISTINCT panels under four headings — four slots that are not four
    samples. Each panel is captioned with its own index and `ref_rows` records
    `constructed clip (Nf)`, so the duplication was visible rather than hidden, which is why
    the finding is LOW; it is still a band whose slot count asserts a sample count it does
    not have.

    Four samples on a clip long enough to carry four; N on a clip that is not.
    """
    if n <= 0:
        return []
    return sorted({0, n // 3, 2 * n // 3, n - 1})

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


def _sample_indices(text):
    """`--sample` as a list of frame indices, refusing by NAME above the cast.

    F-76364ac7's sibling half, wave 22, and the same shape as `make_plate --visible-rows`:
    `[int(v) for v in a.sample.split(",")]` puts the cast above every check, so a
    non-integer component dies with an untyped `ValueError` naming neither the flag nor the
    value.
    """
    parts = [t.strip() for t in str(text).split(",") if t.strip() != ""]
    bad = [t for t in parts if not t.lstrip("+-").isdigit()]
    if bad:
        raise E13SheetError(
            f"--sample takes frame indices; got {text!r}",
            {"gate": None, "andon": "E13SheetError",
             "clause": "sample_component_not_an_integer",
             "flag": "--sample", "supplied": text, "unreadable": bad})
    idx = [int(t) for t in parts]
    if not idx:
        raise E13SheetError(
            f"--sample={text!r} names no frames; the OUTPUT band would be empty on the "
            f"sheet the Director rules the arm from",
            {"gate": None, "andon": "E13SheetError",
             "clause": "sample_names_no_frames", "flag": "--sample", "supplied": text})
    negative = [i for i in idx if i < 0]
    if negative:
        raise E13SheetError(
            f"--sample carries negative indices {negative}; frame files are numbered from "
            f"zero and a negative index is not a frame",
            {"gate": None, "andon": "E13SheetError",
             "clause": "sample_index_is_negative", "flag": "--sample",
             "supplied": text, "negative": negative})
    return idx


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="E13's panel for the composed route: references | output | provenance")
    ap.add_argument("--arm", required=True,
                    help="which arm this sheet shows (A1 = reference record, A2 = "
                         "reference clip); it selects the left column's source")
    ap.add_argument("--seed", required=True,
                    help="the seed this run was submitted with, drawn onto the provenance "
                         "column")
    ap.add_argument("--frames", required=True, help="the extracted output frames dir")
    ap.add_argument("--payload", required=True,
                    help="the run's payload record; the provenance column is read off it")
    ap.add_argument("--out", required=True, help="the sheet image to write")
    ap.add_argument("--refs", default=None, help="A1: the reference record JSON")
    ap.add_argument("--ref-frames", default=None,
                    help="A2: the reference CLIP's frames dir (sampled)")
    ap.add_argument("--prompt-id", default=None,
                    help="the run this sheet shows, when the payload record does not "
                         "carry it; a sheet naming another run's id is a placeholder "
                         "shaped like evidence")
    ap.add_argument("--sample", default="0,37,75,112,149",
                    help="output frame indices (argparse eats leading minus signs)")
    a = ap.parse_args(argv)

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
        # ---- ANDON, before the listing is indexed and before anything is written.
        if not paths:
            raise E13SheetError(
                f"--ref-frames {os.path.abspath(a.ref_frames)} holds no PNG frames; the "
                f"REFERENCES band is what was SENT to the tier, and a sheet whose "
                f"reference band is empty claims a conditioning input that cannot be shown",
                {"gate": None, "andon": "E13SheetError",
                 "clause": "reference_clip_has_no_frames",
                 "ref_frames": os.path.abspath(a.ref_frames),
                 "png_files": sorted(os.path.basename(p) for p in
                                     glob.glob(os.path.join(a.ref_frames, "*.png")))})
        picks = reference_picks(len(paths))
        for i in picks:
            ref_images.append(paths[i])
            ref_labels.append(f"video1  constructed clip f{i}")
        ref_rows.append({"slot": "video1", "label": f"constructed clip ({len(paths)}f)",
                         "sha": "see cascade_decode_compare.json"})

    # ---- ANDON, above `build` and above `os.makedirs`: `--sample` names frames the
    #      extraction actually holds. F-76364ac7, wave 22.
    #
    #      Wave 16 guarded the REFERENCES listing above (`--ref-frames` empty ->
    #      `E13SheetError`) and moved `os.makedirs` below the andons, and left the OUTPUT
    #      band — the panels the Director actually judges — indexing an unchecked listing
    #      one screen down. `--sample` defaults to `0,37,75,112,149`. Measured on `e8263a3`
    #      on a 3-frame extraction whose `frames.json` records `n_frames: 3`, run with the
    #      default `--sample`: `FileNotFoundError: [Errno 2] No such file or directory:
    #      '...\\frames\\00037.png'` — untyped, no clause, and naming neither the band nor
    #      the denominator, even though `fr["n_frames"]` was read four lines above and is
    #      quoted in the provenance panel eleven lines below. The write ordering was
    #      already correct (no sheet directory was created), so the residue half of the
    #      wave-16 fix held; the missing half was the refusal. The sibling sheet in this
    #      domain already has it: `make_e08_sheet` reads each frame through
    #      `_imread(..., f"previz frame {i}")` and names the input that was missing.
    idx = _sample_indices(a.sample)
    missing = [i for i in idx if not os.path.isfile(
        os.path.join(a.frames, f"{i:05d}.png"))]
    if missing:
        raise E13SheetError(
            f"--sample asks for frame(s) {missing} and the extraction at "
            f"{os.path.abspath(a.frames)} holds {fr['n_frames']} "
            f"(0..{fr['n_frames'] - 1}); the OUTPUT band is the panel the Director rules "
            f"the arm from, and it cannot show a frame that was never extracted",
            {"gate": None, "andon": "E13SheetError",
             "clause": "sample_frame_not_in_the_extraction",
             "flag": "--sample", "sample": idx, "n_frames": fr["n_frames"],
             "missing": missing, "frames": os.path.abspath(a.frames)})
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
    # ---- the output directory is created only once every in-tool andon above has fired.
    #      It used to sit at the top of `main`, above the `--ref-frames` listing that could
    #      die with a bare IndexError, so a refused run left an empty sheet directory
    #      behind — which a later reader, or a re-run into the same `--out`, reads as an
    #      attempt that produced nothing rather than one that was refused.
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    # Its OWN token -- see make_cast_sheet for the four-way collision this retires.
    print(f"E13_SHEET_OK {a.out}  {sheet.size[0]}x{sheet.size[1]}")
    return a.out


def _cli(argv=None):
    """The process entry point: an exit code, beside the sheet path `main` returns.

    WAVE 25, F-68f3fb4b — the shape `composite_reference._cli` took in wave 22, for the
    same reason.

    `main` returns the sheet's path, not an exit code, and this module ended in a bare
    `main()`. The wrapper keeps the return value a value and gives the process the code.

    `main` keeps returning the sheet path; this wrapper is what `run_tool_main` runs, so the
    process gets 0 on success, 2 on a typed refusal and 1 on a crash.
    """
    main(argv)
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(_cli, "MAKE_E13_SHEET")
