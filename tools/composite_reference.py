#!/usr/bin/env python
"""composite_reference — authored RGBA masters into the RGB plates a hosted tier receives.

    <venv-python> tools\\composite_reference.py --kit=<turn_rgba dir> \\
        --views=turn_0,turn_1,turn_2,turn_4 --out=<dir> [--plate=154,154,157]

E13's re-arm, A1. The authored-RGBA law (the Director's ruling, 2026-08-12) says every
reference render of the character is authored RGBA with a real alpha channel, and that the
**RGB composite each route actually submits is a deliberate, recorded choice** — because
video VAEs are RGB and raw transparency cannot reach the model. This tool is where that
choice is made explicit, recorded, and gated, instead of happening inside an image library
nobody looked at.

The plate is the survey's neutral mid-grey, sRGB (154, 154, 157) — `make_hole_survey`'s
`OLD_VOID_RGB`, read off `turn_final`'s corner pixel, and the presentation the Director's
eye passed on the S03 kit. It is a parameter here because it is a choice, and a choice
that cannot be named in the record is not one.

Three andons, all raising in-tool, all before a byte is written:

* **Gate PIN** — every source view's sha256 equals the manifest's entry for it. The
  manifest is the authority for what the kit IS; compositing an unpinned file would put
  an unrecorded picture in front of the model with a pinned-looking record beside it.
* **Gate ALPHA** — the source has REAL alpha. `alpha_min == 255` is exactly the
  `turn_final` defect the halt ruling refused (a baked grey void wearing an alpha
  channel), and it is re-measured here rather than inherited from S03's manifest: an
  inherited claim is a hypothesis wearing a fact's clothes, and this one is the premise
  the whole arm rests on.
* **Gate FLAT** — the composite is not a single flat colour. The failure it exists for is
  a fully-transparent master compositing to a uniform plate: a legal PNG, a plausible
  hash, and no character in it at all.

Compensator (NAMED_COMPENSATORS): writes PNG + JSON under `outputs/`. Compensator: delete
the directory; owner: the executor session. The kit itself is read-only.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import GateFailure  # noqa: E402

TOOL_VERSION = "E13.1"

#: `make_hole_survey.OLD_VOID_RGB` — the old set's own measured background, and the plate
#: the Director's eye read the kit against.
SURVEY_PLATE = (154, 154, 157)


class ReferenceGate(GateFailure):
    """A reference plate is not the authored master it claims to be."""

    gate = "REFERENCE"


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def composite_over(rgba, plate):
    """Straight-alpha composite of an RGBA uint8 array over a solid colour.

    Straight, not premultiplied: S03 measured the kit's edge pixels at alpha < 60 carrying
    mean RGB (110, 86, 76) against a full-alpha mean of (136, 98, 79), where premultiplied
    edges would read near (16, 12, 9). Compositing premultiplied data with this formula
    would darken every edge in the plate and nothing would raise.
    """
    a = rgba[..., 3:4].astype(np.float64) / 255.0
    rgb = rgba[..., :3].astype(np.float64)
    bg = np.asarray(plate, dtype=np.float64).reshape(1, 1, 3)
    return np.clip(np.rint(rgb * a + bg * (1.0 - a)), 0, 255).astype(np.uint8)


def gate_pin(path, manifest_sha):
    """Gate PIN · ANDON — this file is the manifest's file."""
    got = sha256_file(path)
    ev = {"gate": "PIN", "file": os.path.basename(path), "manifest": manifest_sha,
          "measured": got}
    if got != manifest_sha:
        raise ReferenceGate(
            f"{os.path.basename(path)} hashes {got} where the turnaround manifest records "
            f"{manifest_sha}. The manifest is the authority for what this kit is, and a "
            f"reference that is not the pinned file is an unrecorded picture in front of "
            f"the model", ev)
    return ev


def gate_alpha(rgba, label):
    """Gate ALPHA · ANDON — a real alpha channel, re-measured rather than inherited."""
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ReferenceGate(f"{label} is not RGBA (shape {rgba.shape})",
                            {"gate": "ALPHA", "shape": list(rgba.shape)})
    lo, hi = int(rgba[..., 3].min()), int(rgba[..., 3].max())
    ev = {"gate": "ALPHA", "view": label, "alpha_min": lo, "alpha_max": hi}
    if lo == 255:
        raise ReferenceGate(
            f"{label} has alpha extrema ({lo}, {hi}) — fully opaque everywhere. That is a "
            f"baked void wearing an alpha channel, the exact `turn_final` defect the halt "
            f"ruling refused, and there is no composite choice to record because there is "
            f"no alpha to composite from", ev)
    if hi < 255:
        raise ReferenceGate(
            f"{label} has alpha extrema ({lo}, {hi}) — nothing is fully opaque, so no "
            f"pixel is solidly the character. This is the view nobody rendered into", ev)
    return ev


def gate_flat(rgb, plate, label):
    """Gate FLAT · ANDON — something other than the plate is in the frame."""
    distinct = int(len(np.unique(rgb.reshape(-1, 3), axis=0)))
    off_plate = float((np.abs(rgb.astype(np.int16)
                              - np.asarray(plate, dtype=np.int16)).sum(-1) > 0).mean())
    ev = {"gate": "FLAT", "view": label, "distinct_colours": distinct,
          "frac_off_plate": off_plate}
    if distinct < 2 or off_plate <= 0.0:
        raise ReferenceGate(
            f"{label} composites to a frame that is entirely the plate colour: a legal "
            f"PNG with no character in it, which every hash and every count downstream "
            f"would accept", ev)
    return ev


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", required=True, help="the turn_rgba directory")
    ap.add_argument("--views", required=True,
                    help="comma-separated stems IN SLOT ORDER, e.g. turn_0,turn_1,turn_2,"
                         "turn_4 (argparse eats leading minus signs: use --views=...)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--plate", default=",".join(str(c) for c in SURVEY_PLATE))
    a = ap.parse_args(argv)

    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    plate = tuple(int(v) for v in a.plate.split(","))
    if len(plate) != 3:
        raise ReferenceGate(f"--plate={a.plate!r} is not r,g,b", {"supplied": a.plate})

    with open(os.path.join(a.kit, "turnaround_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    by_stem = {}
    for i, v in enumerate(manifest["views"]):
        stem = os.path.splitext(os.path.basename(v.get("file", f"turn_{i}.png")))[0]
        by_stem[stem] = dict(v, index=i)

    stems = [s.strip() for s in a.views.split(",") if s.strip()]
    entries = []
    for slot, stem in enumerate(stems, start=1):
        entry = by_stem.get(stem)
        if entry is None:
            raise ReferenceGate(
                f"the manifest carries no view named {stem!r}; it names "
                f"{sorted(by_stem)}. Picking a view the authority does not name is how a "
                f"reference set stops being the kit that was judged",
                {"asked": stem, "known": sorted(by_stem)})
        src = os.path.join(a.kit, f"{stem}.png")
        pin = gate_pin(src, entry["sha256"])
        rgba = np.asarray(Image.open(src))
        alpha = gate_alpha(rgba, stem)
        rgb = composite_over(rgba, plate)
        flat = gate_flat(rgb, plate, stem)

        dst = os.path.join(out, f"A1_slot{slot}_{stem}.png")
        Image.fromarray(rgb, mode="RGB").save(dst)
        entries.append({
            "slot": f"image{slot}", "view": stem,
            "azimuth_deg": entry.get("azimuth_deg"),
            "source": os.path.abspath(src), "source_sha256": entry["sha256"],
            "composited": os.path.abspath(dst), "composited_sha256": sha256_file(dst),
            "shape": [int(rgba.shape[0]), int(rgba.shape[1])],
            "gates": {"PIN": pin, "ALPHA": alpha, "FLAT": flat},
        })

    record = {
        "tool": "composite_reference", "tool_version": TOOL_VERSION,
        "kit": os.path.abspath(a.kit),
        "kit_manifest_source_glb": manifest["source"],
        "plate_rgb_srgb": list(plate),
        "plate_why": ("make_hole_survey.OLD_VOID_RGB — the old set's own measured "
                      "background and the presentation the Director's eye passed on the "
                      "S03 kit. The RGB composite a route submits is a deliberate, "
                      "recorded choice under the authored-RGBA law"),
        "composite_formula": "straight alpha: rgb*a + plate*(1-a), rounded, uint8",
        "slot_order": [e["slot"] for e in entries],
        "views": entries,
    }
    with open(os.path.join(out, "A1-reference-record.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    for e in entries:
        print(f"{e['slot']:<7} {e['view']:<8} az {e['azimuth_deg']:>6}  "
              f"alpha {e['gates']['ALPHA']['alpha_min']},{e['gates']['ALPHA']['alpha_max']}  "
              f"off-plate {e['gates']['FLAT']['frac_off_plate']:.4f}  "
              f"sha {e['composited_sha256'][:16]}")
    print(f"plate            {plate}")
    print(f"COMPOSITE_OK     {out}")
    return record


if __name__ == "__main__":
    main()
