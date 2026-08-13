#!/usr/bin/env python
"""make_shotset_sheet — the ortho shot-set as a sheet, and beside its perspective sibling.

    <venv-python> tools\\make_shotset_sheet.py --ortho=outputs/S04/ortho \\
        --out=outputs/S04/sheets --mode=shotset
    <venv-python> tools\\make_shotset_sheet.py --ortho=outputs/S04/ortho \\
        --persp=outputs/S04/persp --out=outputs/S04/sheets --mode=compare

Layout is `sheet_compose`'s — enumerated before this was written, and it already sizes a
sheet to its text as well as its panels and pastes panels at their rendered size without
resampling, which is the property a constant-scale claim needs. What this tool adds is the
part that is specific to a shot-set of RGBA cutouts.

**The cells are composited, and the choice is recorded rather than defaulted.** The
turnaround's deliverable is an RGBA master whose RGB is black wherever alpha is zero, so
handing those files straight to a sheet paints black cells on a near-black sheet and the
cell boundaries — the very thing a constant-scale claim is read against — disappear. Each
cell is composited over one recorded flat field and given a one-pixel border, so a figure
that touched its cell edge is visible AS touching it. This is a judging surface and not a
submission; the alpha law's "the RGB composite is the consuming route's own recorded
choice" is discharged here by recording it.

**The two rules are a ruler, not an argument.** Every cell on a sheet carries horizontal
lines at the SAME two frame rows — the highest silhouette top and the lowest silhouette
bottom over every cell on that sheet — so the eye can read how each figure sits against a
fixed reference instead of against its neighbour's edge. They assert nothing about which
projection is better; the rows are stated in the subtitle and in the manifest.

Metrics on the labels are diagnostics. The Director's eye judges the cells.

Compensator (NAMED_COMPENSATORS): writes composited cells and one PNG under the `--out`
directory. Compensator: delete that directory; owner: the executor session. The rendered
masters and both manifests are opened read-only.
"""

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sheet_compose  # noqa: E402

TOOL_VERSION = "S04.1"

#: The field each RGBA cutout is composited over, and the cell border drawn on top of it.
#: Recorded here rather than chosen at the call site so two sheets cannot disagree.
CELL_FIELD = (38, 38, 42)
CELL_BORDER = (96, 96, 104)
RULE = (150, 110, 60)


def load_set(directory):
    """A turnaround manifest plus the fields this sheet reads, or raise naming what is
    missing. A sheet built from a directory listing would happily compose a partial set."""
    path = os.path.join(directory, "turnaround_manifest.json")
    if not os.path.isfile(path):
        raise SystemExit(f"no turnaround_manifest.json in {directory}")
    with open(path, encoding="utf-8") as fh:
        man = json.load(fh)
    cam = man["camera"]
    return {
        "dir": directory, "manifest": man, "camera": cam,
        "projection": cam.get("projection", "NOT RECORDED"),
        "ortho_scale": cam.get("ortho_scale"),
        "radius": cam.get("radius"),
        "elevation_deg": cam.get("elevation_deg"),
        "resolution": man["resolution"],
        "views": man["views"],
    }


def rule_rows(sets):
    """The two frame rows every cell on this sheet is ruled at.

    Derived from the cells themselves — the highest silhouette top and the lowest
    silhouette bottom over every view on the sheet — so the ruler brackets everything
    drawn and no figure is ruled off its own cell.
    """
    tops, bottoms = [], []
    for s in sets:
        for v in s["views"]:
            box = v.get("subject_bbox_px")
            if box:
                tops.append(int(box[1]))
                bottoms.append(int(box[3]))
    if not tops:
        return None
    return min(tops), max(bottoms)


def composite_cell(src, dst, rules):
    """One RGBA master over the recorded field, bordered, ruled. Never resampled."""
    im = Image.open(src).convert("RGBA")
    out = Image.new("RGB", im.size, CELL_FIELD)
    out.paste(im, (0, 0), im)
    d = ImageDraw.Draw(out)
    if rules:
        for y in rules:
            if 0 <= y < im.size[1]:
                d.line([(0, y), (im.size[0] - 1, y)], fill=RULE, width=1)
    d.rectangle([(0, 0), (im.size[0] - 1, im.size[1] - 1)], outline=CELL_BORDER, width=1)
    out.save(dst)
    return dst


def view_clearances(v):
    """The per-border clearances, wherever this view's record happens to keep them.

    Armed (ORTHO) Gate CROP reports them at the top level of its evidence; unarmed (PERSP)
    the same numbers ride the reported measurement one level down. One reader, both shapes.
    """
    crop = v.get("gate_CROP") or {}
    clear = crop.get("clearance_px")
    if not isinstance(clear, dict):
        clear = (crop.get("border_contact") or {}).get("clearance_px")
    return clear if isinstance(clear, dict) else None


def view_label(v):
    """Numbers on the cell, and nothing that is a judgement — SHORT ENOUGH TO FIT IT.

    `sheet_compose` sizes the SHEET to its longest label, which is E12's fix and is the
    right one for a label that would otherwise be cropped off the edge. It does not stop a
    label from running under the NEXT panel's label, because each is drawn at its own
    panel's x. Measured on this sheet's first build: 1153 px of label in a 1024 px cell,
    so every cell's numbers overprinted its neighbour's and the row read as one smear.

    So the full record — bbox, width fraction, per-border clearances, the
    predicted-vs-measured delta — stays in the manifest, and the cell carries the five
    quantities the eye is being asked to compare. Sheets locate; full size decides.
    `tests/test_make_shotset_sheet.py` pins the fit against the real font.
    """
    box = v.get("subject_bbox_px")
    clear = view_clearances(v)
    bits = [f"az {v['azimuth_deg']:.0f}",
            f"alpha {tuple(v['gate_ALPHA']['alpha_extrema'])}",
            f"h {v['gate_WHOLE']['height_frac']:.4f}"]
    if box:
        bits.append(f"px h {box[3] - box[1]}")
    if clear:
        bits.append(f"min clear {min(clear.values())} px")
    return "   ".join(bits)


def row_title(s, tag):
    cam = s["camera"]
    if s["projection"] == "ORTHO":
        shared = f"ortho_scale {s['ortho_scale']:.6f} SHARED across all cells"
    else:
        shared = f"radius {s['radius']:.6f} shared; scale varies per view"
    return (f"{tag}  —  {s['projection']}   elevation {cam['elevation_deg']:.0f}deg   "
            f"{s['resolution'][0]}x{s['resolution'][1]}   {shared}")


def build(sets, tags, out_dir, filename, title, subtitle):
    cells_dir = os.path.join(out_dir, "cells")
    os.makedirs(cells_dir, exist_ok=True)
    rules = rule_rows(sets)

    rows = []
    for s, tag in zip(sets, tags):
        panels = []
        for v in s["views"]:
            dst = os.path.join(cells_dir, f"{tag}_{v['view']}.png")
            composite_cell(v["path"], dst, rules)
            panels.append({"body": dst, "label": view_label(v)})
        rows.append({"title": row_title(s, tag), "panels": panels})

    spec = {"title": title, "subtitle": subtitle, "out": out_dir,
            "filename": filename, "rows": rows}
    spec_path = os.path.join(out_dir, filename.replace(".png", "-panels.json"))
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=1)

    argv = sys.argv
    sys.argv = ["sheet_compose", spec_path]
    try:
        sheet_compose.main()
    finally:
        sys.argv = argv
    return os.path.join(out_dir, filename), rules


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ortho", required=True)
    ap.add_argument("--persp", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=("shotset", "compare"), default="shotset")
    a = ap.parse_args(argv)

    out_dir = os.path.abspath(a.out)
    os.makedirs(out_dir, exist_ok=True)          # scripts create their own directories
    ortho = load_set(a.ortho)

    if a.mode == "compare":
        if not a.persp:
            raise SystemExit("--mode=compare needs --persp")
        persp = load_set(a.persp)
        if persp["camera"]["elevation_deg"] != ortho["camera"]["elevation_deg"]:
            raise SystemExit(
                f"the two sets are at different elevations "
                f"({ortho['camera']['elevation_deg']} vs "
                f"{persp['camera']['elevation_deg']}); a comparison across elevation is "
                f"not a comparison of projection")
        sets, tags = [ortho, persp], ["ORTHO", "PERSP"]
        title = ("S04 — the same GLB at the same elevation, parallel above perspective   "
                 "(diagnostics only; the Director's eye is the verdict)")
        filename = "S04-ortho-vs-perspective.png"
    else:
        sets, tags = [ortho], ["ORTHO"]
        title = ("S04 — the orthographic sprite shot-set   "
                 "(diagnostics only; the Director's eye is the verdict)")
        filename = "S04-shotset.png"

    rules = rule_rows(sets)
    subtitle = (
        f"GLB {os.path.basename(ortho['manifest']['source']['glb'])} "
        f"sha256 {ortho['manifest']['source']['sha256'][:16]}   "
        f"Blender {ortho['manifest']['blender']['version']}   "
        f"tool {ortho['manifest']['tool_version']}   "
        f"cells composited over RGB{CELL_FIELD} with a 1px border, pasted 1:1, never "
        f"resampled   "
        + (f"horizontal rules are a fixed ruler at frame rows {rules[0]} and {rules[1]}"
           if rules else "no silhouette measured; no rules drawn")
        + "   texture holes on the subject are pre-known (facet's arc) and are not "
          "findings here")

    path, rules = build(sets, tags, out_dir, filename, title, subtitle)
    im = Image.open(path)
    print(f"SHOTSET_SHEET_OK {path}  {im.size[0]}x{im.size[1]}  rules={rules}")
    return path


if __name__ == "__main__":
    main()
