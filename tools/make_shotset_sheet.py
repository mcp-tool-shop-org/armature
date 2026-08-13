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

**`--mode=scale` compares where the shared scale came from (S05).**

    <venv-python> tools\\make_shotset_sheet.py --ortho=outputs/S05/solved \\
        --second=outputs/S05/pinned_roomy --out=outputs/S05/sheets --mode=scale

Two ORTHO sets of one subject at one preset, differing only in whether their shared
`ortho_scale` was solved or pinned. It is a separate mode rather than a second use of
`compare` because `compare` hard-tags its rows ORTHO and PERSP **by position**: pointed at
two ortho sets it prints PERSP over a row whose own manifest says ORTHO, and that sheet
saves, opens, rules and labels itself, and looks entirely finished. This mode reads both
tags off the manifests, and refuses the two cases where it could not — a set that is not
ORTHO at all, and two sets whose tags collide (their cells are named by tag, so they would
overwrite each other and the sheet would show one set twice).

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

TOOL_VERSION = "S05.1"

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
        # S05. A set rendered before the pin existed carries no source key at all, and
        # `None` here reads out as "NOT RECORDED" rather than as "solved" — an older
        # manifest is silent about the question, not an answer to it.
        "ortho_scale_source": cam.get("ortho_scale_source"),
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


#: How a set's row is tagged when the sheet compares SCALE SOURCE rather than projection.
#: Read off each set's own manifest, never assigned by position — a row hard-tagged by
#: where it happens to sit is how a sheet comes to say PERSP over a set whose manifest
#: says ORTHO, and the sheet looks entirely finished either way.
SOURCE_TAGS = {"solved": "SOLVED", "pinned": "PINNED"}


def set_tag(s):
    """This set's row tag, taken from what its manifest recorded."""
    if s["projection"] != "ORTHO":
        return s["projection"]
    return SOURCE_TAGS.get(s.get("ortho_scale_source"), "ORTHO-SOURCE-NOT-RECORDED")


def row_title(s, tag):
    cam = s["camera"]
    if s["projection"] == "ORTHO":
        # Full precision, not `.6f`. On a pinned row this number IS the recipe — the next
        # character in the roster is rendered by retyping it — and 1.123536 is a different
        # world span from 1.1235359256161628.
        src = {"pinned": "PINNED, used verbatim (no solve ran)",
               "solved": "SOLVED from the largest silhouette of this subject"}.get(
                   s.get("ortho_scale_source"), "source NOT RECORDED by this manifest")
        shared = (f"ortho_scale {s['ortho_scale']!r} SHARED across all cells   [{src}]")
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


def _refuse_across_elevations(a, b, what):
    """Two sets at different camera heights are not a comparison of anything else."""
    if a["camera"]["elevation_deg"] != b["camera"]["elevation_deg"]:
        raise SystemExit(
            f"the two sets are at different elevations "
            f"({a['camera']['elevation_deg']} vs {b['camera']['elevation_deg']}); a "
            f"comparison across elevation is not a comparison of {what}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ortho", required=True)
    ap.add_argument("--persp", default=None)
    ap.add_argument("--second", default=None,
                    help="--mode=scale: the other ORTHO set, differing only in where its "
                         "shared scale came from (S05)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=("shotset", "compare", "scale"), default="shotset")
    a = ap.parse_args(argv)

    out_dir = os.path.abspath(a.out)
    os.makedirs(out_dir, exist_ok=True)          # scripts create their own directories
    ortho = load_set(a.ortho)

    if a.mode == "scale":
        # S05. `compare` puts a PERSP row under an ORTHO one and hard-tags it by position,
        # so pointing it at two ortho sets would print PERSP over a set whose own manifest
        # says ORTHO — a mislabelled sheet that saves, opens and looks finished. This mode
        # takes both tags off the manifests instead.
        if not a.second:
            raise SystemExit("--mode=scale needs --second")
        second = load_set(a.second)
        for s, flag in ((ortho, "--ortho"), (second, "--second")):
            if s["projection"] != "ORTHO":
                raise SystemExit(
                    f"{flag} is a {s['projection']} set; --mode=scale compares where an "
                    f"ORTHO run's shared scale came from, and a perspective set has no "
                    f"such scale to compare")
        _refuse_across_elevations(ortho, second, "scale source")
        tags = [set_tag(ortho), set_tag(second)]
        if tags[0] == tags[1]:
            # Not cosmetic: the cell files are named `<tag>_<view>.png`, so two rows
            # sharing a tag overwrite each other's cells and the sheet shows ONE set
            # twice, ruled and labelled and entirely plausible.
            raise SystemExit(
                f"both sets record ortho_scale_source {ortho.get('ortho_scale_source')!r}, "
                f"so both rows would be tagged {tags[0]!r}: the sheet could not name its "
                f"own rows apart and their cells would overwrite each other")
        sets = [ortho, second]
        title = ("S05 — the same GLB at the same preset, one shared ortho_scale SOLVED "
                 "above one PINNED   (diagnostics only; the Director's eye is the verdict)")
        filename = "S05-solved-vs-pinned.png"
    elif a.mode == "compare":
        if not a.persp:
            raise SystemExit("--mode=compare needs --persp")
        persp = load_set(a.persp)
        _refuse_across_elevations(ortho, persp, "projection")
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
