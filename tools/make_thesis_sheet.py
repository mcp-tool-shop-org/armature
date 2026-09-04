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
from measure_lift import gate_listing_pairing  # noqa: E402
from sheet_compose import (SHEET_PLATE, SheetPopulationError,  # noqa: E402
                           frames_by_number, load_rgb_over_plate, require_frames)

MARGIN = 10
LABEL_H = 17
HDR = 24
BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (145, 145, 155)


def _rgb(p, plate=SHEET_PLATE):
    """One tile, composited over the NAMED plate. See `sheet_compose.SHEET_PLATE`."""
    return load_rgb_over_plate(p, plate)[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--arms", required=True, help="LABEL:dir,LABEL:dir")
    ap.add_argument("--reference", required=True,
                    help="path to the reference plate, or the literal 'none'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,8,16,24,32")
    ap.add_argument("--tile-height", type=int, default=300)
    ap.add_argument("--meta", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--control-label", default="CONTROL   depth, per-shot, near-bright")
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

    # ---- ANDON, before a tile is cut: every row names the same frames as the control,
    #      and every requested index exists in every row.
    gate_listing_pairing({title: names for title, _d, names in rows})
    # ---- and the bound is the frames' own NUMBERS, not their POSITION in the listing
    #      (wave 12): a run numbered 00001..00003 accepted `--frames=0,1,2` and captioned
    #      its three files f000/f001/f002 — frame numbers the run does not hold — while
    #      refusing the numbers it does.
    by_number = {}
    for title, ddir, names in rows:
        by_number[title] = frames_by_number(names, where=ddir,
                                            what=f"frame(s) of {title}")
        require_frames(idx, names, what=f"frame(s) of {title}", where=ddir,
                       numbers=sorted(by_number[title]))

    ctl_by_number = by_number[rows[0][0]]
    tw = fit(_rgb(os.path.join(a.control, ctl_by_number[min(ctl_by_number)]),
                  plate)).width
    # `none` is a real value: E03's arms deliberately carry no reference image.
    ref = None if a.reference.lower() == "none" else fit(_rgb(a.reference, plate))
    ref_w = ref.width if ref is not None else 260
    width = MARGIN + len(idx) * (tw + MARGIN) + ref_w + MARGIN * 2
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
        y += LABEL_H + th + LABEL_H + MARGIN

    # scripts create their own output directories — matching make_lift_sheet.py
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    print(f"THESIS_SHEET {a.out} {sheet.width}x{sheet.height} "
          f"plate={tuple(int(v) for v in plate)}")
    # The SUCCESS direction of the exit convention, stated: 0, beside the sentinel. It
    # returned None, which `SystemExit(None)` happens to render as 0 — a convention no
    # census could read off the function.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
