#!/usr/bin/env python
"""make_hole_survey — the old turnaround beside the new one, per view, at full size.

    <venv-python> tools\\make_hole_survey.py --new=<dir> --old=<dir> --out=<dir>

S03 Task B. The survey **documents**; it fixes nothing. The white unpainted patches on
these views live in the texture atlas, and texture repair is facet's projection-coverage
arc — `E:\\AI\\training` and `E:\\AI\\facet` are read-only law here. What this produces is
evidence: eight full-size old-beside-new panels, one contact sheet, and per-view numbers.
Which views are usable is the Director's ruling, not this tool's and not this session's.

Runs outside Blender (Pillow + numpy), like every other sheet tool here.

--------------------------------------------------------------------------------
The composite is a choice, and it is recorded

The new masters are RGBA with a real alpha channel — that is the entire point of them — and
a sheet cannot show transparency. So the panels composite the masters over **the old set's
own measured background colour**, sRGB (154, 154, 157), read off `turn_final`'s corner
pixel. That choice is what makes the comparison a comparison: put the new figure on any
other ground and every difference between the two panels includes a difference of backdrop.

The composite exists ONLY in this survey. The deliverable masters in `turn_rgba/` stay
RGBA and are never overwritten — per the Director's ruling of 2026-08-12, the RGB each
consuming route submits is that route's own recorded choice, not this one.

Alpha is **straight**, not premultiplied — measured on the render rather than assumed:
edge pixels at alpha < 60 carry mean RGB (110, 86, 76) against a full-alpha mean of
(136, 98, 79). Premultiplied edges at that alpha would read near (16, 12, 9). So the
composite is the ordinary `rgb*a + bg*(1-a)`.

--------------------------------------------------------------------------------
Why the unpainted-patch number is measured on an ERODED interior

The obvious instrument — count low-saturation pixels inside the figure — is not comparable
between these two sets as written, and the reason is the thing S03 exists to fix. The old
views have no alpha, so the figure has to be masked by colour difference from the baked grey
void, which necessarily includes the antialiased rim where figure blends into grey. Grey rim
pixels are low-saturation. The new views are masked by their real alpha instead. The two
masks therefore disagree about the edge, and an un-eroded count would report the *masking
method* as if it were a texture defect.

Both masks are eroded by the same amount before anything is counted, so what is compared is
interior texel against interior texel. The number is a **locator, not a verdict**: it says
where to look at full size. No threshold here gates anything, and the whole percentile curve
is reported beside the count so no single cut carries the claim.

--------------------------------------------------------------------------------
`--old-rgba`: both sides are authored masters (S06)

Absent the flag nothing below applies and the flat-alpha old side described above is what
runs; the branch is `old_side_plan` and nothing else, so "the default path is untouched when
the flag is absent" is a property of one testable object rather than of a careful reading of
this loop.

The flag exists because the survey's *second* use is not its first. S03 compared a flat-alpha
`turn_final` against a new RGBA master. S06 compares **two RGBA masters** — S03's own E33
renders against the repaired performer's — and the old-side machinery above is wrong for that
input in two independent ways, both measured before the flag was written:

* `figure_mask_old` asks how far a pixel sits from the baked void `(154, 154, 157)`. An RGBA
  master's background is transparent black, which is *maximally* far from that grey, so the
  mask marks **100% of the frame** as figure against a true opaque fraction of 0.2255. Every
  interior number would then be computed over the background as well as the figure.
* the old side is written to its panel uncomposited, so it would sit on near-black while the
  new side sits on grey — putting a difference of backdrop into every panel, which is the one
  thing the composite above exists to prevent.

With the flag, the old side is treated exactly as the new one: composited over the same
`OLD_VOID_RGB` and masked by its own alpha. Same instrument, both sides.
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

TOOL_VERSION = "S06.1"

#: `turn_final`'s baked void, measured off its corner pixel. sRGB.
OLD_VOID_RGB = (154, 154, 157)

#: Erosion radius in pixels, applied to BOTH masks. 3 px comfortably clears the
#: antialiased rim at this resolution without eating the thin structures (fingers, the
#: ankle joints) where the patches actually are.
ERODE_PX = 3

#: Reported cuts. Several, deliberately: a locator that quoted one number would invite it
#: to be read as a verdict.
SAT_CUTS = (0.10, 0.15, 0.20, 0.25)


def composite_over(rgba, bg_rgb):
    """Straight-alpha composite of an RGBA uint8 array over a solid colour.

    Returns uint8 RGB. Kept a module-level function with no I/O so the arithmetic is
    testable against the two cases that matter — alpha 0 must give exactly the background,
    alpha 255 exactly the source — which is where an off-by-one or a premultiply
    assumption shows up and nowhere else.
    """
    rgb = rgba[..., :3].astype(np.float64)
    a = (rgba[..., 3].astype(np.float64) / 255.0)[..., None]
    bg = np.asarray(bg_rgb, dtype=np.float64)
    return np.rint(rgb * a + bg * (1.0 - a)).clip(0, 255).astype(np.uint8)


def saturation(rgb):
    """HSV saturation of a uint8 RGB array, as 0..1 floats."""
    mx = rgb.max(axis=-1).astype(np.float64)
    mn = rgb.min(axis=-1).astype(np.float64)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-9), 0.0)


def erode(mask, px=ERODE_PX):
    """Shrink a boolean mask by `px` pixels (a min filter of width 2*px+1)."""
    if px <= 0:
        return mask
    im = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    im = im.filter(ImageFilter.MinFilter(size=2 * int(px) + 1))
    return np.array(im) > 127


def figure_mask_new(rgba):
    """The new set's figure: its own alpha, which is what having alpha is for."""
    return rgba[..., 3] >= 255


def figure_mask_old(rgb, void_rgb=OLD_VOID_RGB, tol=18):
    """The old set's figure: colour difference from the baked void, because there is no
    alpha to ask. This is the mask whose rim the erosion exists to remove."""
    return np.abs(rgb.astype(np.int32) - np.asarray(void_rgb, np.int32)).sum(-1) > tol


def old_side_plan(old_rgba, old_is_rgba):
    """How the OLD side is read: the whole `--old-rgba` branch, as one testable object.

    Returns `(panel_rgb, figure_mask, described)` — the RGB written to the panel, the mask
    the interior is counted over, and the sentence the manifest records about which of the
    two readings ran. Kept separate from `main` so "the default path is untouched when the
    flag is absent" is an assertion about a function rather than about a loop body.
    """
    if old_is_rgba:
        rgb = composite_over(old_rgba, OLD_VOID_RGB)
        return rgb, figure_mask_new(old_rgba), (
            "authored RGBA master: composited over the same background as the new side and "
            "masked by its own alpha, so the two sides differ in the figure and not in the "
            "instrument")
    rgb = old_rgba[..., :3]
    return rgb, figure_mask_old(rgb), (
        "flat-alpha set with a baked void: masked by colour difference from "
        f"{OLD_VOID_RGB} and written to the panel uncomposited")


def survey_view(rgb, mask):
    """Locator numbers for one view: how much of the interior reads as unpainted."""
    interior = erode(mask)
    s = saturation(rgb)[interior]
    if s.size == 0:
        return {"interior_px": 0, "note": "nothing survived erosion"}
    return {
        "interior_px": int(s.size),
        "saturation_percentiles": {
            str(p): round(float(np.percentile(s, p)), 4)
            for p in (1, 5, 10, 25, 50, 75, 95)},
        "low_saturation_fraction": {
            f"{c:.2f}": round(float((s < c).mean()), 5) for c in SAT_CUTS},
        "mean_value": round(float(rgb[interior].mean()), 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--new-prefix", default="turn")
    ap.add_argument("--old-prefix", default="armfinal")
    ap.add_argument("--views", type=int, default=8)
    ap.add_argument("--old-rgba", action="store_true",
                    help="the OLD side is an authored RGBA master too — composite and mask "
                         "it exactly as the new side. Absent, the flat-alpha reading runs "
                         "unchanged (S06)")
    ap.add_argument("--tag", default="S03 Task B",
                    help="the run this survey belongs to, used in the sheet titles")
    ap.add_argument("--old-label", default=None,
                    help="panel label for the old side; defaults to the S03 wording")
    ap.add_argument("--new-label", default=None,
                    help="panel label for the new side; defaults to the S03 wording")
    a = ap.parse_args()

    out = os.path.abspath(a.out)
    panels_dir = os.path.join(out, "panels")
    os.makedirs(panels_dir, exist_ok=True)     # scripts create their own output directories

    records, new_panels, old_panels = [], [], []
    for i in range(a.views):
        np_path = os.path.join(a.new, f"{a.new_prefix}_{i}.png")
        op_path = os.path.join(a.old, f"{a.old_prefix}_{i}.png")
        new_rgba = np.array(Image.open(np_path).convert("RGBA"))
        old_rgba = np.array(Image.open(op_path).convert("RGBA"))

        new_rgb = composite_over(new_rgba, OLD_VOID_RGB)
        comp_path = os.path.join(panels_dir, f"new_{i}.png")
        Image.fromarray(new_rgb).save(comp_path)
        old_rgb, old_mask, old_reading = old_side_plan(old_rgba, a.old_rgba)
        old_path = os.path.join(panels_dir, f"old_{i}.png")
        Image.fromarray(old_rgb).save(old_path)

        records.append({
            "view": i,
            "new": dict(survey_view(new_rgb, figure_mask_new(new_rgba)), source=np_path),
            "old": dict(survey_view(old_rgb, old_mask), source=op_path,
                        reading=old_reading),
        })
        new_panels.append(comp_path)
        old_panels.append(old_path)

        old_lab = a.old_label or f"OLD armfinal_{i}.png"
        new_lab = a.new_label or f"NEW turn_{i}.png"
        spec = {
            "title": f"{a.tag} — the hole survey, view {i}",
            "subtitle": (
                ("BEFORE beside AFTER — both authored RGBA masters, both composited here "
                 f"over {OLD_VOID_RGB} and both masked by their own alpha, so the panels "
                 "differ in the paint and not in the instrument. Full size, no resampling.")
                if a.old_rgba else
                ("OLD turn_final (flat alpha 255,255, baked grey void) beside NEW "
                 "turn_rgba (authored RGBA, composited here over the old set's own "
                 f"{OLD_VOID_RGB} for comparison only). Full size, no resampling.")),
            "out": out, "filename": f"view_{i}.png",
            "rows": [{"title": f"view {i}", "panels": [
                {"body": old_path, "label": old_lab.replace("{i}", str(i))},
                {"body": comp_path, "label": new_lab.replace("{i}", str(i))}]}],
        }
        with open(os.path.join(out, f"_panels_view_{i}.json"), "w", encoding="utf-8") as fh:
            json.dump(spec, fh, indent=1)

    contact = {
        "title": f"{a.tag} — the hole survey, contact sheet",
        "subtitle": (("Row 1 BEFORE; row 2 AFTER. Sheets locate; full size decides — the "
                      "per-view sheets are the ones to read.") if a.old_rgba else
                     ("Row 1 OLD turn_final; row 2 NEW turn_rgba. Sheets locate; full size "
                      "decides — the per-view sheets are the ones to read.")),
        "out": out, "filename": "contact.png",
        "rows": [
            {"title": (a.old_label.replace("{i}", "0-7") if a.old_label else
                       "OLD — facet_E33/turn_final (alpha extrema 255,255 on all eight)"),
             "panels": [{"body": p, "label": f"{a.old_prefix}_{i}"}
                        for i, p in enumerate(old_panels)]},
            {"title": (a.new_label.replace("{i}", "0-7") if a.new_label else
                       "NEW — S03/turn_rgba (alpha extrema 0,255 on all eight)"),
             "panels": [{"body": p, "label": f"{a.new_prefix}_{i}"}
                        for i, p in enumerate(new_panels)]},
        ],
    }
    with open(os.path.join(out, "_panels_contact.json"), "w", encoding="utf-8") as fh:
        json.dump(contact, fh, indent=1)

    with open(os.path.join(out, "survey.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "tool": "make_hole_survey", "tool_version": TOOL_VERSION,
            "tag": a.tag,
            "old_side_is_rgba": bool(a.old_rgba),
            "old_side_reading": old_side_plan(
                np.zeros((1, 1, 4), np.uint8), a.old_rgba)[2],
            "composite_rgb_srgb": list(OLD_VOID_RGB),
            "composite_why": ("the old set's own measured background, so the two panels "
                              "differ in the figure and not in the ground. The delivered "
                              "masters stay RGBA and are not overwritten"),
            "erode_px": ERODE_PX,
            "instrument_note": ("low-saturation fraction over an ERODED interior. The old "
                                "views must be masked by colour difference from their baked "
                                "void and the new ones by their real alpha; the two masks "
                                "disagree at the antialiased rim, so both are eroded by the "
                                "same amount and only interior texels are counted. A "
                                "locator for the eye, gating nothing"),
            "out_of_scope": ("texture repair. The patches live in the atlas; no re-render "
                             "moves them. facet's projection-coverage arc owns them"),
            "views": records,
        }, fh, indent=1)

    print(f"SURVEY_OK {out}")
    for r in records:
        n, o = r["new"], r["old"]
        print(f"  view {r['view']}: new sat<0.20 {n['low_saturation_fraction']['0.20']:.5f}"
              f"  old {o['low_saturation_fraction']['0.20']:.5f}"
              f"   | new mean value {n['mean_value']:.1f}  old {o['mean_value']:.1f}")


if __name__ == "__main__":
    main()
