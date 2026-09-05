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


def compose_over_named_plate(arr, plate, *, label, exc, extra_evidence=None,
                             channel_order="RGB"):
    """The Director's authored-RGBA law (2026-08-12), in ONE place, for every producer.

    `arr` is a decoded image array of 3 or 4 channels in whatever order the caller's
    decoder produced — `channel_order` names it for the RECORD only, because
    `composite_over`'s arithmetic is order-agnostic as long as `plate` is in the same
    order (pass BGR to a cv2 caller, RGB to a PIL one).

    Returns `(rgb, record)`. A 4th channel with **no plate named** raises `exc`: the RGB
    composite a route submits is a deliberate, recorded choice, and dropping the channel
    makes it an accidental one. That is not a style preference — a grey previz void bled
    through E11's frame 0, and `fit_reference` was measured on 2026-09-03 deriving a
    letterbox pad from the RGB sitting *under* alpha=0, on the reference image two paid
    runs submitted.

    This function exists because the law was implemented twice and missing three times.
    `encode_control.read_frames`, `fit_reference`, `make_plate` and `pack_pose_pack` all
    call it; there is one refusal, one composite and one record shape.
    """
    a = np.asarray(arr)
    if a.ndim == 3 and a.shape[2] == 4:
        lo, hi = int(a[..., 3].min()), int(a[..., 3].max())
        ev = dict(extra_evidence or {}, alpha_present=True, alpha_min=lo, alpha_max=hi,
                  channel_order=channel_order, source_channels=4)
        if plate is None:
            raise exc(
                f"{label} carries an alpha channel (extrema {lo}, {hi}) and no plate was "
                f"named. The RGB composite a route submits is a deliberate, recorded "
                f"choice (the Director, 2026-08-12) — pass --alpha-over=R,G,B to make it "
                f"one. Dropping the channel would submit whatever RGB the author made "
                f"invisible", ev)
        rgb = composite_over(a.astype(np.uint8), plate)
        record = {
            "source_channels": 4, "channel_order": channel_order,
            "alpha_present": True, "alpha_min": lo, "alpha_max": hi,
            "alpha_disposition": (
                f"composited straight-alpha over the named plate "
                f"{tuple(int(v) for v in plate)} ({channel_order})"),
        }
        return rgb, record
    if a.ndim == 3 and a.shape[2] == 3:
        return a, {"source_channels": 3, "channel_order": channel_order,
                   "alpha_present": False, "alpha_min": None, "alpha_max": None,
                   "alpha_disposition": "no alpha channel in the source"}
    raise exc(f"{label}: array shape {list(a.shape)} is neither a 3- nor a 4-channel "
              f"frame, so there is no alpha disposition to record",
              dict(extra_evidence or {}, shape=list(a.shape), alpha_present=None))


def parse_plate(text, exc, flag="--alpha-over"):
    """`R,G,B` of a named plate, or None. Raises `exc` on anything else.

    **The ONE three-integer parser in this domain.** `fit_reference`, `make_plate`,
    `pack_pose_pack` and `encode_control` all call it rather than splitting the flag
    themselves — the census that pins that is
    `tests/test_alpha_law.py::test_the_flag_parser_is_one_implementation_read_off_the_ast`.
    Wave 22 (F-3092e646) added `fit_reference --pad`, which had its own inline
    `[int(v) for v in a.pad.split(",")]` with the cast ABOVE the length check and no
    0-255 range check, eleven lines below this function's own `--alpha-over` call.

    The evidence dict names the andon and the clause as well as the value, because the
    caller's `flag` is the thing a reader has to retype and `supplied` alone said only that
    something was wrong. `supplied` is kept — `tests/test_alpha_law.py` reads it across all
    four producers.
    """
    if text is None or text == "":
        return None
    parts = [t.strip() for t in str(text).split(",")]
    if len(parts) != 3:
        raise exc(f"{flag} takes three 0-255 integers, e.g. {flag}=0,0,0; got {text!r}",
                  {"gate": "ARGS", "andon": exc.__name__,
                   "clause": "plate_not_three_components", "flag": flag,
                   "supplied": text, "n_components": len(parts)})
    # ---- WAVE 25 (F-e7565198). The integer clause asks the question `int()` ANSWERS.
    #      `str.isdigit()` is True for characters `int()` refuses: it is a Unicode property,
    #      and superscripts, circled digits and other numeric forms satisfy it. Wave 22 split
    #      one boolean (`t.isdigit() and 0 <= int(t) <= 255`) into two clauses, which moved
    #      the untyped raise rather than removing it: a component passed the `isdigit` clause
    #      and then `int(t)` in the RANGE clause raised `ValueError` before a typed refusal
    #      could be produced. Re-measured on `580af47` in this worktree with the repo venv:
    #      `parse_plate('0,0,0')` -> `(0, 0, 0)`; `parse_plate('a,b,c')` and
    #      `parse_plate('999,-5,0')` -> typed, with their clauses; `parse_plate('\u00b2,0,0')`
    #      (superscript two) and `parse_plate('\u2461,0,0')` (circled two) -> untyped
    #      `ValueError: invalid literal for int() with base 10`. This is the ONE plate parser
    #      the authored-RGBA law is administered through - `encode_control`, `pack_pose_pack`,
    #      `fit_reference` and `make_plate` all call it - so a value pasted from a document
    #      carrying a non-ASCII numeric character exited untyped on whichever caller ran,
    #      while this module's own `_cli` docstring cites exactly that input as the crash the
    #      wave-22 wrapper was written for.
    #
    #      `t.isascii() and t.isdigit()` is true only of a run of the ASCII digits `0`-`9`,
    #      which `int()` reads by definition - so the cast below this clause CANNOT raise,
    #      and nothing this parser accepted before is refused now (a superscript was never
    #      accepted; it crashed).
    unreadable = [t for t in parts if not (t.isascii() and t.isdigit())]
    if unreadable:
        raise exc(f"{flag} takes three 0-255 integers, e.g. {flag}=0,0,0; got {text!r}",
                  {"gate": "ARGS", "andon": exc.__name__,
                   "clause": "plate_component_not_an_integer", "flag": flag,
                   "supplied": text,
                   "unreadable": unreadable})
    values = [int(t) for t in parts]
    out_of_range = [v for v in values if not 0 <= v <= 255]
    if out_of_range:
        raise exc(f"{flag} takes three 0-255 integers, e.g. {flag}=0,0,0; got {text!r}",
                  {"gate": "ARGS", "andon": exc.__name__,
                   "clause": "plate_component_out_of_range", "flag": flag,
                   "supplied": text,
                   "out_of_range": out_of_range})
    return tuple(values)


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

    # ---- ONE parser, the module's own, rather than a third variant of it. `main`'s
    #      inline `tuple(int(v) for v in a.plate.split(","))` checked only the LENGTH:
    #      measured 2026-09-04, `--plate=999,-5,0` passed it, `composite_over` clipped the
    #      channels to [255, 0, 0], and the record below wrote `"plate_rgb_srgb": [999,
    #      -5, 0]` -- naming a colour that is not the colour composited, in the artefact
    #      that says what the model was actually shown. `--plate=a,b,c` raised a bare
    #      `ValueError` rather than this tool's own error with its evidence dict.
    plate = parse_plate(a.plate, ReferenceGate, flag="--plate")
    if plate is None:
        raise ReferenceGate(
            "--plate is empty; the plate is a deliberate, recorded choice under the "
            "authored-RGBA law and an unnamed one cannot be recorded",
            {"supplied": a.plate})

    with open(os.path.join(a.kit, "turnaround_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    by_stem = {}
    for i, v in enumerate(manifest["views"]):
        stem = os.path.splitext(os.path.basename(v.get("file", f"turn_{i}.png")))[0]
        by_stem[stem] = dict(v, index=i)

    stems = [s.strip() for s in a.views.split(",") if s.strip()]

    # ---- PASS ONE: every andon, for every view, before a byte is written. The module
    #      docstring above says "all before a byte is written" and that was true only of
    #      the FIRST view: the gates ran inside the write loop, so a kit whose third view
    #      failed Gate ALPHA left two composited plates and an output directory behind,
    #      and `os.makedirs` sat above all three andons besides.
    gated = []
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
        gated.append((slot, stem, entry, src, rgba, rgb, pin, alpha, flat))

    # ---- PASS TWO: the writes. The output directory is created only now, so a refused
    #      kit leaves nothing behind rather than an empty directory that reads as a run.
    os.makedirs(out, exist_ok=True)
    entries = []
    for slot, stem, entry, src, rgba, rgb, pin, alpha, flat in gated:
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


def _cli(argv=None):
    """The process entry point: an exit code, beside the record `main` returns.

    F-41a09432, wave 22. This module ended in a bare `main()` — the weakest form in the
    42-tool population, in which the function's return value can never become an exit code
    at all. It holds the authored-RGBA law's ONE plate parser, called by `encode_control`,
    `pack_pose_pack`, `fit_reference` and `make_plate`. Measured on `e8263a3` through its
    real CLI on a one-view kit: a deliberate typed refusal (`--plate=a,b,c` ->
    `ReferenceGate: [REFERENCE] --plate takes three 0-255 integers ...`) and an untyped
    crash (`--plate=\u00b2,0,0` -> `ValueError: invalid literal for int()`) BOTH exited 1
    with stdout empty and no halt line, so the two outcomes the three-outcome contract
    exists to separate were indistinguishable here.

    `main` keeps returning the record — `tests/test_composite_reference.py` reads it — and
    this wrapper is what `run_tool_main` runs, so the process gets 0 on success, 2 on a
    typed refusal and 1 on a crash.
    """
    main(argv)
    return 0


if __name__ == "__main__":
    # WAVE 22, SEAM 1: the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (core-solvers' file, posted to the wave-22 seams inbox). Never
    # copied — the whole point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(_cli, "COMPOSITE_REFERENCE")
