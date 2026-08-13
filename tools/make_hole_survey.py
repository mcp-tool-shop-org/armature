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
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

TOOL_VERSION = "S03.1"

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
        old_path = os.path.join(panels_dir, f"old_{i}.png")
        Image.fromarray(old_rgba[..., :3]).save(old_path)

        records.append({
            "view": i,
            "new": dict(survey_view(new_rgb, figure_mask_new(new_rgba)), source=np_path),
            "old": dict(survey_view(old_rgba[..., :3],
                                    figure_mask_old(old_rgba[..., :3])), source=op_path),
        })
        new_panels.append(comp_path)
        old_panels.append(old_path)

        spec = {
            "title": f"S03 Task B — the hole survey, view {i}",
            "subtitle": ("OLD turn_final (flat alpha 255,255, baked grey void) beside NEW "
                         "turn_rgba (authored RGBA, composited here over the old set's own "
                         f"{OLD_VOID_RGB} for comparison only). Full size, no resampling."),
            "out": out, "filename": f"view_{i}.png",
            "rows": [{"title": f"view {i}", "panels": [
                {"body": old_path, "label": f"OLD armfinal_{i}.png"},
                {"body": comp_path, "label": f"NEW turn_{i}.png"}]}],
        }
        with open(os.path.join(out, f"_panels_view_{i}.json"), "w", encoding="utf-8") as fh:
            json.dump(spec, fh, indent=1)

    contact = {
        "title": "S03 Task B — the hole survey, contact sheet",
        "subtitle": ("Row 1 OLD turn_final; row 2 NEW turn_rgba. Sheets locate; full size "
                     "decides — the per-view sheets are the ones to read."),
        "out": out, "filename": "contact.png",
        "rows": [
            {"title": "OLD — facet_E33/turn_final (alpha extrema 255,255 on all eight)",
             "panels": [{"body": p, "label": f"armfinal_{i}"}
                        for i, p in enumerate(old_panels)]},
            {"title": "NEW — S03/turn_rgba (alpha extrema 0,255 on all eight)",
             "panels": [{"body": p, "label": f"turn_{i}"}
                        for i, p in enumerate(new_panels)]},
        ],
    }
    with open(os.path.join(out, "_panels_contact.json"), "w", encoding="utf-8") as fh:
        json.dump(contact, fh, indent=1)

    with open(os.path.join(out, "survey.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "tool": "make_hole_survey", "tool_version": TOOL_VERSION,
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
