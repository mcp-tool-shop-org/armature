#!/usr/bin/env python
"""make_thesis_sheet — control vs controlled-output vs no-control-output, one panel.

    python tools/make_thesis_sheet.py --control=<dir> --arms=A1a:<dir>,A2:<dir>
                                      --reference=<plate.png> --out=<sheet.png>

The panel E02 exists to produce. The A1a sheet on its own shows a turning armored figure
that follows the control — and that is **unfalsifiable without A2**, because the model may
produce a turning armored figure from the prompt and the reference alone. A2 is the same
prompt, the same reference, and no `control_video`. Putting the two output rows under the
same control row is what turns a demonstration into evidence.

**The rows are PAIRED and the request is BOUNDED (measured 2026-09-03).** Every row was a
listing indexed by the same `fi`, with nothing checking that the control and the arms name
the same frames, and `if fi >= len(names): continue` dropped a requested index in silence —
the same two defects `make_gate0_sheet` and `make_lift_sheet` carried. And `sheet.save`
had no `os.makedirs` anywhere in the file, the only writer among this domain's sheets
without one: `--out=outputs/E02/sheets/thesis.png` against a tree where that directory did
not yet exist died with `FileNotFoundError` out of PIL, on the panel assembled after the
arms had been generated and paid for.

Computes nothing, decides nothing, quotes no metric. Whether the figure is in the same
place at the same time is P3, and P3 is judged by eye on this panel at full size.
"""

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from composite_reference import parse_plate  # noqa: E402
# The sibling panel's provenance block, CALLED rather than copied: `make_gate0_sheet`
# derives every line from the run's own record and prints `NOT RECORDED` where the record
# does not carry it (the `make_startframe_sheet` convention). One implementation, so the
# thesis panel says the same things about a run that the Gate 0 panel does.
from make_gate0_sheet import provenance_lines  # noqa: E402
from measure_lift import gate_listing_pairing  # noqa: E402
from sheet_compose import (SHEET_PLATE, SheetPopulationError,  # noqa: E402
                           frames_by_number, load_rgb_over_plate, require_frames)

MARGIN = 10
#: Width reserved for the provenance column when `--meta` is given. The Gate 0 panel's own
#: reservation is 430; this matches it, because the lines are the same lines.
PROV_W = 430
LABEL_H = 17
HDR = 24
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (145, 145, 155)


def _rgb(p, plate=SHEET_PLATE):
    """One tile, composited over the NAMED plate. See `sheet_compose.SHEET_PLATE`."""
    return load_rgb_over_plate(p, plate)[0]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="control vs controlled-output vs no-control-output in one panel — the "
                    "sheet the whole thesis is read off")
    ap.add_argument("--control", required=True,
                    help="the control channel directory this run was driven by")
    ap.add_argument("--arms", required=True, help="LABEL:dir,LABEL:dir")
    ap.add_argument("--reference", required=True,
                    help="path to the reference plate, or the literal 'none'")
    ap.add_argument("--out", required=True, help="the sheet image to write")
    ap.add_argument("--frames", default="0,8,16,24,32",
                    help="the frame indices every row is sampled at (argparse eats leading "
                         "minus signs: pass as --frames=0,8,16)")
    ap.add_argument("--tile-height", type=int, default=300,
                    help="height each tile is drawn at, in pixels")
    # DECLARED **and READ**. Measured 2026-09-04: `--meta` was parsed here and grep for
    # `meta` across the whole module returned this one line -- the value reached nothing,
    # and a path that does not exist was accepted in silence
    # (`--meta=E:/no/such/meta.json` returned 0, printed THESIS_SHEET and left the sheet on
    # disk). Its two siblings read the same flag and draw the run's provenance from it
    # (`make_gate0_sheet.py:251`, `make_startframe_sheet.py:206`). A flag DECLARED and not
    # READ is the mirror of the `--sheet-plate` regression `tests/test_sheet_argv_smoke.py`
    # exists for, and that census walks only the other direction.
    ap.add_argument("--meta", default=None,
                    help="a payload/run record; its provenance is drawn as a fourth "
                         "column, every line from the record and NOT RECORDED where the "
                         "record does not carry it")
    ap.add_argument("--title", default=None,
                    help="the sheet's heading; default: derived from the arms")
    ap.add_argument("--control-label", default="CONTROL   depth, per-shot, near-bright",
                    help="the heading over the control row. Change it when the control is "
                         "not depth/per-shot/near-bright — a label asserting a channel the "
                         "run did not use is a caption a reader has no reason to doubt")
    ap.add_argument("--captions", default=None,
                    help="'idx=text,idx=text' per-frame labels, replacing the frame index")
    # Azimuth is opt-in as of E14. It used to be the DEFAULT caption, computed as
    # 360*i/len(frames) — true for a turnaround, and a fabricated number on every video
    # route, where the frames are time and not a camera orbit. E10's closing lesson names
    # this class: a tool that bakes one experiment's meaning into a literal will lie the
    # first time it is reused, and it lies in a caption a reader has no reason to doubt.
    ap.add_argument("--azimuth-captions", action="store_true",
                    help="label frames as turnaround azimuth (only true for a turnaround)")
    ap.add_argument("--no-reference-note", default=None,
                    help="pipe-separated lines drawn when --reference=none")
    ap.add_argument("--sheet-plate", default=",".join(str(v) for v in SHEET_PLATE),
                    help="R,G,B of the plate an RGBA tile is composited over before it is "
                         "drawn. Named and recorded, never assumed: the reference column "
                         "of a panel must not show the character against a plate the "
                         "route did not submit")
    a = ap.parse_args(argv)
    plate = parse_plate(a.sheet_plate, SheetPopulationError, flag="--sheet-plate")

    captions = None
    if a.captions:
        captions = {}
        for part in a.captions.split(","):
            k, _, v = part.partition("=")
            captions[int(k)] = v

    idx = [int(v) for v in a.frames.split(",") if v.strip()]
    th = a.tile_height
    arms = []
    for tok in a.arms.split(","):
        lab, _, d = tok.partition(":")
        arms.append((lab, d))
    # ---- ANDON, before the pairing gate is armed: the labels are DISTINCT. The gate below
    #      is armed with a dict comprehension keyed by the row TITLE, so two arms sharing a
    #      label collapsed to one key and the earlier one's listing was discarded before the
    #      gate saw it. Measured 2026-09-04: a control numbered 00000..00002 with
    #      `--arms=A1:<dir numbered 00007..00009>,A1:<dir numbered 00000..00002>` built the
    #      sheet, printed THESIS_SHEET and exited 0, with the mis-numbered arm drawn under
    #      captions f000/f001; the same two arms with distinct labels raised PairingGate.
    #      The one input shape that disarmed the andon on the panel this repo says turns a
    #      demonstration into evidence.
    repeated = sorted({lab for lab in [x[0] for x in arms]
                       if [x[0] for x in arms].count(lab) > 1})
    if repeated:
        raise SheetPopulationError(
            f"--arms repeats the label(s) {', '.join(repr(r) for r in repeated)}; the "
            f"pairing gate is keyed by label, so a repeat discards the earlier arm's "
            f"listing before the gate sees it and puts two different moments of the "
            f"performance side by side with exit 0",
            {"arms": [lab for lab, _d in arms], "repeated": repeated})

    def listing(d):
        return sorted(n for n in os.listdir(d) if n.lower().endswith(".png"))

    cn = listing(a.control)

    def fit(im):
        s = th / im.height
        return im.resize((max(1, round(im.width * s)), th), Image.LANCZOS)

    rows = [(a.control_label, a.control, cn)]
    for lab, d in arms:
        rows.append((f"OUTPUT  {lab}", d, listing(d)))

    # ---- ANDON, and the ORDER of the two is the fix (F-2f2c19a9, wave 25). The POPULATION
    #      is settled first: `sheet_compose.frames_by_number` is the ONE home for "the
    #      numbered frame population, with a stray refusal", and it ran BELOW the pairing
    #      gate — so a `strip_every8.png` present in one row and not another was refused by
    #      `gate_listing_pairing` under `listings_disagree`, naming the wrong andon for the
    #      condition, and a stray present in EVERY row reached the pairing gate as a frame.
    #      `render_pose_sticks` writes `strip_every{N}.png` into the same directory as its
    #      `NNNNN.png` control frames, so this is the pipeline's own ordinary output.
    by_number = {}
    for title, ddir, names in rows:
        by_number[title] = frames_by_number(names, where=ddir,
                                            what=f"frame(s) of {title}")
    # ---- THEN the pairing: every row names the same frames as the control.
    gate_listing_pairing({title: names for title, _d, names in rows})
    # ---- and the bound is the frames' own NUMBERS, not their POSITION in the listing
    #      (wave 12): a run numbered 00001..00003 accepted `--frames=0,1,2` and captioned
    #      its three files f000/f001/f002 — frame numbers the run does not hold — while
    #      refusing the numbers it does.
    for title, ddir, names in rows:
        require_frames(idx, names, what=f"frame(s) of {title}", where=ddir,
                       numbers=sorted(by_number[title]))

    # ---- the provenance column. Read BEFORE any tile is cut, so a --meta that is not
    #      there refuses rather than being discovered after the panel is composed.
    meta = None
    if a.meta:
        with open(a.meta, encoding="utf-8") as fh:
            meta = json.load(fh)
    prov = provenance_lines(meta) if meta is not None else []

    ctl_by_number = by_number[rows[0][0]]
    tw = fit(_rgb(os.path.join(a.control, ctl_by_number[min(ctl_by_number)]),
                  plate)).width
    # `none` is a real value: E03's arms deliberately carry no reference image.
    ref = None if a.reference.lower() == "none" else fit(_rgb(a.reference, plate))
    ref_w = ref.width if ref is not None else 260
    # The provenance column is only as wide as it is present: a run given no `--meta`
    # composes the sheet it always composed, at the same size.
    prov_w = (PROV_W + MARGIN) if prov else 0
    width = MARGIN + len(idx) * (tw + MARGIN) + ref_w + MARGIN * 2 + prov_w
    height = HDR + len(rows) * (LABEL_H + th + LABEL_H + MARGIN) + MARGIN

    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 6), a.title or ("E02 THESIS PANEL   -   same control, same prompt, "
                                    "same reference.   A1a HAS control_video.  A2 HAS NONE."),
           fill=FG)

    y = HDR
    for row_i, (title, ddir, names) in enumerate(rows):
        d.text((MARGIN, y), title, fill=FG)
        x = MARGIN
        for fi in idx:
            # Indexed by NUMBER, not by position in the listing.
            t = fit(_rgb(os.path.join(ddir, by_number[title][fi]), plate))
            sheet.paste(t, (x, y + LABEL_H))
            if captions is not None:
                cap = f"f{fi:03d}  {captions.get(fi, '')}"
            elif a.azimuth_captions:
                cap = f"f{fi:03d}  az {360.0 * fi / len(cn):.0f}d"
            else:
                cap = f"f{fi:03d}"
            d.text((x, y + LABEL_H + th + 2), cap, fill=DIM)
            x += tw + MARGIN
        # The reference rides the FIRST row, whatever that row is called. This was
        # `title.startswith("CONTROL")` until E14, where the first row is a BASELINE rather
        # than a control — and the reference plate was silently not drawn at all. A sheet
        # that omits the reference on a label mismatch is the panel this repo requires,
        # missing the third of its four columns, with nothing saying so.
        if row_i == 0:
            if ref is not None:
                sheet.paste(ref, (x, y + LABEL_H))
                d.text((x, y + LABEL_H + th + 2), "REFERENCE (all arms)", fill=DIM)
            else:
                for i, ln in enumerate(
                        (a.no_reference_note or "REFERENCE: NONE.").split("|")):
                    d.text((x, y + LABEL_H + 4 + i * 15), ln, fill=DIM)
            if prov:
                px = x + ref_w + MARGIN
                d.text((px, y), "PROVENANCE", fill=DIM)
                yy = y + LABEL_H
                for ln in prov:
                    d.text((px, yy), ln,
                           fill=FG if ln.startswith("Gate") else DIM)
                    yy += 15
        y += LABEL_H + th + LABEL_H + MARGIN

    # scripts create their own output directories — matching make_lift_sheet.py
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    # The flag's effect is on the OK line, not only in the pixels: a reader keying on this
    # line can tell whether the panel carries provenance or does not.
    print(f"THESIS_SHEET {a.out} {sheet.width}x{sheet.height} "
          f"plate={tuple(int(v) for v in plate)} "
          f"provenance={os.path.abspath(a.meta) if a.meta else 'NONE (--meta not given)'}")
    # The SUCCESS direction of the exit convention, stated: 0, beside the sentinel. It
    # returned None, which `SystemExit(None)` happens to render as 0 — a convention no
    # census could read off the function.
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MAKE_THESIS_SHEET")
