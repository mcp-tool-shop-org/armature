#!/usr/bin/env python
r"""measure_shot — camera error and masked identity diagnostics for a generated shot.

    python tools\measure_shot.py --frames=<lossless dir> --out=<shot_diagnostics.json>
           (--render-run=<stage_render dir> | --static)
           [--masks=<mask dir>] [--lens-mm=50] [--sensor-mm=36] [--label=shot]
           [--floor-frames=<render rgb dir>]
           [--reference=<rgba png or dir> --decoy-reference=<rgba png or dir>
            --dinov2-weights=<local model.safetensors> [--decoy-label=decoy]]

Runs `armature_core.shotdiag` over a directory of numerically named lossless `NNNNN.png`
frames (the `VAEDecode` tap — never a re-encoded video) and writes one JSON record with the
`camera` block first and the optional `identity` block after it.

**Rulings implemented (`docs/dispatches/shot-diagnostics-design.md`):**
- **Camera error is REPORT ONLY (D1).** Printed first in every report with no pass/fail and
  no threshold; `followed` reads `"NO THRESHOLD — CALIBRATION NOT YET RUN"` until calibration
  runs on the F0, N and G populations.
- **Tier A only:** OpenCV SIFT on background features outside the dilated Blender character
  mask, fitting both Essential matrix (known `K`) and Homography with Torr GRIC selection,
  reporting translation as unobservable (`t_unobservable`) on rotation-only pairs, and
  aligning by frame-0 anchoring (zero fitted parameters for rotation and direction errors;
  `fitted_scale` and `ate` set to `"NOT COMPUTABLE — pairwise unit directions carry no relative scale"`). Tier B (`facebook/map-anything-apache`) is NOT
  built here and requires a later grant.
- **Masked identity:** DINOv2 ViT-B/14 (`facebook/dinov2-base` @ `f9e44c81`, Apache-2.0)
  behind a `"weights not present"` refusal (`weights_not_present`) and `MeasureWeightGate`
  (`MEASURE_WEIGHT`). Masked identity **gates nothing**: low scores and zero fired counts
  return normally, and non-separable or sub-patch frames report `score: null`.

Compensator (NAMED_COMPENSATORS): writes one JSON under `outputs/`. Compensator: delete the
file; owner: the executor session. Input directories and weights are opened read-only.

Prints `MEASURE_SHOT_OK`.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encode_control import runtime_provenance  # noqa: E402
from measure_clip import round_or_none  # noqa: E402

from armature_core import shotdiag as SD  # noqa: E402
from armature_core.shotdiag import ShotDiagError  # noqa: E402

HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'


def _build_summary(cam_block, id_block):
    summary = {
        "camera_fired_pairs": f"{cam_block['n_fired']}/{cam_block['n_pairs']}",
        "rot_err_median_deg": round_or_none(cam_block["rot_err_deg"]["median"], 3),
        "rot_err_p90_deg": round_or_none(cam_block["rot_err_deg"]["p90"], 3),
        "tdir_err_median_deg": round_or_none(cam_block["tdir_err_deg"]["median"], 3),
        "static_parallax_median_px": round_or_none(
            cam_block["static_parallax_px"]["median"], 3
        ),
        "followed": cam_block["followed"],
    }
    if id_block is not None:
        summary["identity_fired_frames"] = (
            f"{id_block['n_fired']}/{id_block['n_frames']}"
        )
        summary["identity_score_median"] = round_or_none(
            id_block["score"]["median"], 4
        )
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="measure_shot",
        description=(
            "camera error (Tier A) and masked identity diagnostics for a generated "
            "shot — report-only diagnostics; the Director's eye is the judge"
        ),
        epilog=HALT_EPILOG,
    )
    ap.add_argument(
        "--frames",
        required=True,
        help="directory of numerically named lossless NNNNN.png generated frames",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="path to write the shot diagnostics JSON record",
    )
    ap.add_argument(
        "--render-run",
        default=None,
        help="stage_render run directory holding manifest.json, optional spec.json, and mask/",
    )
    ap.add_argument(
        "--static",
        action="store_true",
        help="declare a Static camera request (identity GT pose; reports pixel parallax)",
    )
    ap.add_argument(
        "--masks",
        default=None,
        help="optional directory of numbered NNNNN.png character masks overriding stage_render mask/",
    )
    ap.add_argument(
        "--lens-mm",
        type=float,
        default=None,
        help="camera focal length in mm (defaults to stage_render spec.json or 50.0)",
    )
    ap.add_argument(
        "--sensor-mm",
        type=float,
        default=None,
        help="camera sensor width in mm (defaults to stage_render spec.json or 36.0)",
    )
    ap.add_argument(
        "--label",
        default="shot",
        help="label written into the record and sheet diagnostic lines",
    )
    ap.add_argument(
        "--floor-frames",
        default=None,
        help="optional directory of numbered NNNNN.png Blender render frames to measure the F0 instrument floor",
    )
    ap.add_argument(
        "--reference",
        default=None,
        help="optional authored RGBA reference PNG or directory to include masked identity",
    )
    ap.add_argument(
        "--decoy-reference",
        default=None,
        help="authored RGBA reference PNG or directory of a distinct canonical character for the decoy floor",
    )
    ap.add_argument(
        "--decoy-label",
        default="decoy",
        help="name of the decoy canonical character recorded in the identity block",
    )
    ap.add_argument(
        "--dinov2-weights",
        default=None,
        help="local path to facebook/dinov2-base model.safetensors (checked by Gate MEASURE_WEIGHT; never auto-downloaded)",
    )
    a = ap.parse_args(argv)

    if not a.render_run and not a.static:
        raise ShotDiagError(
            "measure_shot requires --render-run=<stage_render dir> or --static so "
            "ground-truth camera motion is known before any metric is computed",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "no_ground_truth_camera",
            },
        )
    if a.reference and not a.decoy_reference:
        raise ShotDiagError(
            "--reference requires --decoy-reference naming a distinct canonical "
            "character so the decoy floor is computed alongside subject similarity",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "missing_decoy_reference",
            },
        )
    if a.decoy_reference and not a.reference:
        raise ShotDiagError(
            "--decoy-reference was given without --reference",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "missing_subject_reference",
            },
        )

    frames, frame_indices = SD.load_numbered_rgb_frames(a.frames)

    cam_matrices = None
    lens_mm = 50.0
    sensor_mm = 36.0
    spec_width = None
    spec_height = None
    masks = None

    if a.render_run:
        run_info = SD.load_stage_render_run(
            a.render_run, require_camera_matrices=not bool(a.static)
        )
        if not a.static:
            cam_matrices = run_info["camera_matrices"]
        lens_mm = run_info["lens_mm"]
        sensor_mm = run_info["sensor_mm"]
        spec_width = run_info["spec_width"]
        spec_height = run_info["spec_height"]
        masks = run_info["masks"]

    if a.lens_mm is not None:
        lens_mm = a.lens_mm
    if a.sensor_mm is not None:
        sensor_mm = a.sensor_mm

    if a.masks:
        mask_rgb_frames, _ = SD.load_numbered_rgb_frames(a.masks)
        masks = [f[:, :, 0] > 127 for f in mask_rgb_frames]

    if a.reference and masks is None:
        raise ShotDiagError(
            "masked identity requires per-frame character masks (from --render-run "
            "mask/ or --masks=<dir>)",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "missing_subject_mask",
            },
        )

    cam_block = SD.measure_camera_from_frames(
        frames,
        cam_matrices,
        lens_mm=lens_mm,
        sensor_mm=sensor_mm,
        spec_width=spec_width,
        spec_height=spec_height,
        masks=masks,
        is_static=bool(a.static),
    )

    if a.floor_frames:
        floor_rgb, _ = SD.load_numbered_rgb_frames(a.floor_frames)
        floor_cam = SD.measure_camera_from_frames(
            floor_rgb,
            cam_matrices,
            lens_mm=lens_mm,
            sensor_mm=sensor_mm,
            spec_width=spec_width,
            spec_height=spec_height,
            masks=masks,
            is_static=bool(a.static),
        )
        cam_block["instrument_floor"] = {
            "n_pairs": floor_cam["n_pairs"],
            "n_fired": floor_cam["n_fired"],
            "rot_err_deg": floor_cam["rot_err_deg"],
            "tdir_err_deg": floor_cam["tdir_err_deg"],
            "static_parallax_px": floor_cam["static_parallax_px"],
            "note": SD.FLOOR_NOTE,
        }

    id_block = None
    if a.reference:
        subj_refs = SD.load_rgba_references(a.reference)
        decoy_refs = SD.load_rgba_references(a.decoy_reference)
        id_block = SD.measure_masked_identity(
            frames,
            masks,
            subj_refs,
            decoy_refs,
            dinov2_weights_path=a.dinov2_weights,
            decoy_label=a.decoy_label,
        )

    source_meta = {
        "frames": os.path.abspath(a.frames),
        "frame_indices": frame_indices,
    }
    if a.render_run:
        source_meta["render_run"] = os.path.abspath(a.render_run)
    if a.masks:
        source_meta["masks"] = os.path.abspath(a.masks)
    if a.floor_frames:
        source_meta["floor_frames"] = os.path.abspath(a.floor_frames)
    if a.reference:
        source_meta["reference"] = os.path.abspath(a.reference)
        source_meta["decoy_reference"] = os.path.abspath(a.decoy_reference)

    record = SD.build_shot_record(
        cam_block, id_block, label=a.label, source=source_meta
    )
    record.update(runtime_provenance())
    summary = _build_summary(cam_block, id_block)

    payload_text = json.dumps(record, indent=2, allow_nan=False) + "\n"
    ok_obj = {"out": os.path.abspath(a.out), "summary": summary}
    json.dumps(ok_obj, allow_nan=False)

    out_dir = os.path.dirname(os.path.abspath(a.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(payload_text)

    print("MEASURE_SHOT_OK " + json.dumps(ok_obj, allow_nan=False))
    return 0


if __name__ == "__main__":
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MEASURE_SHOT")
