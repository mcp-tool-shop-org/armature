#!/usr/bin/env python
"""measure_arm — where is the arm, frame by frame, in image space.

    python tools/measure_arm.py --run=<control run dir> --joints=<subject.joints.json>
                                [--frames=<image dir>] [--label=B1] [--out=<json>]

Two independent things, deliberately kept apart:

**1. The authored truth, projected.** The subject is procedural, so every joint's true 3-D
position is known at every frame. Pushing those through the run's own recorded camera gives
the pixel position the shoulder, elbow and wrist *should* occupy — and the arm's angle in
image space. Nothing is estimated; this is the control's ground truth, and it is what the
Gate 0 sheet marks up.

**2. A measured angle, from pixels alone.** The same estimator-free measure is applied to
the control frames and to a generated output: classify subject vs background, take the
pixels in an annulus about the shoulder, and report the angular lobe they fall in. Applied
to the control it can be checked against the truth in (1); that check is the only reason to
trust anything it says about an output.

⚠ **This is a DIAGNOSTIC and it gates nothing.** The E03 spec chose an arm raise precisely
so the answer is readable by eye off a sheet with no pose estimator involved, and this repo
has twice recorded a metric that returned confident numbers about a thing it could not see
(high-pass statistics for material identity, silhouette IoU for character identity). E02
dropped a modal-background coverage measure for exactly the confound this one could hit: a
non-flat background is counted as subject. So `segmentation` is reported beside every angle,
and **an angle whose segmentation is implausible is reported as failed, not as a number.**

The Director's eye on the sheet is the judge. This exists so the report can put a number
beside the eye, not instead of it.
"""

import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402


class MeasureError(ArmatureError):
    """The measurement could not be made as specified."""


# ------------------------------------------------------------------------ projection


def half_fovs(lens_mm, sensor_mm, width, height):
    """Half field-of-view per axis, matching Blender's AUTO sensor fit.

    Duplicated from blender_scene rather than imported because that module imports bpy at
    module scope and this tool runs outside Blender. `test_measure_arm.py` pins the two
    against each other numerically so the copy cannot drift silently.
    """
    if width >= height:
        sx, sy = sensor_mm, sensor_mm * height / width
    else:
        sy, sx = sensor_mm, sensor_mm * width / height
    return math.atan(sx * 0.5 / lens_mm), math.atan(sy * 0.5 / lens_mm)


def project(points_zup, camera_matrix, lens_mm, sensor_mm, width, height):
    """World Z-up points -> pixel coordinates, using the run's own recorded camera."""
    M = np.asarray(camera_matrix, dtype=np.float64)
    view = np.linalg.inv(M)
    hx, hy = half_fovs(lens_mm, sensor_mm, width, height)

    pts = np.asarray(points_zup, dtype=np.float64)
    homo = np.concatenate([pts, np.ones((pts.shape[0], 1))], axis=1)
    cam = homo @ view.T
    # Blender cameras look down local -Z, so a point in front has negative z_cam.
    depth = -cam[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        xn = (cam[:, 0] / depth) / math.tan(hx)
        yn = (cam[:, 1] / depth) / math.tan(hy)
    px = (xn * 0.5 + 0.5) * width
    py = (1.0 - (yn * 0.5 + 0.5)) * height
    return np.stack([px, py], axis=1), depth


# --------------------------------------------------------------------- segmentation


def subject_mask(arr, tol=12):
    """Subject vs background, and the evidence that the split is believable.

    Background is the frame's modal colour. That is exactly the instrument E02 caught out —
    a lit studio gradient got counted as subject and returned 78-89% coverage — so the
    fraction is returned with the mask and the caller is expected to refuse an implausible
    one rather than quote the angle it produces.
    """
    a = arr.astype(np.int16)
    if a.ndim == 2:
        a = a[..., None]
    flat = a.reshape(-1, a.shape[2])
    # Modal colour over a coarse quantisation, so near-identical background pixels agree.
    keys = (flat // 8).astype(np.int64)
    packed = keys[:, 0] * 65536 + (keys[:, 1] * 256 if a.shape[2] > 1 else 0) + (
        keys[:, 2] if a.shape[2] > 2 else 0
    )
    vals, counts = np.unique(packed, return_counts=True)
    bg_key = vals[counts.argmax()]
    bg = flat[packed == bg_key].mean(axis=0)

    dist = np.abs(a - bg[None, None, :]).max(axis=2)
    mask = dist > tol
    return mask, {
        "background_rgb": [round(float(v), 2) for v in bg],
        "subject_fraction": round(float(mask.mean()), 6),
        "tolerance": tol,
    }


def arm_angle(mask, shoulder_px, r_in, r_out):
    """The angular lobe of subject pixels in an annulus about the shoulder, in degrees.

    0 deg is image-right (the T-pose), +90 deg is image-up (overhead) — so the number is
    directly comparable to the authored arc angle. Returns None when the annulus is empty.

    The annulus is the whole trick: it excludes the torso and head (inside `r_in`) and the
    background beyond the hand (outside `r_out`), leaving the limb as the dominant lobe. The
    reported angle is the median of the pixel angles rather than the mean, so a stray blob
    on the far side of the body shifts it less than it would a centroid.
    """
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None, {"n_px": 0}
    dx = xs - shoulder_px[0]
    dy = shoulder_px[1] - ys  # image y grows downward; flip so +y is up
    r = np.hypot(dx, dy)
    keep = (r >= r_in) & (r <= r_out) & (dx > 0)  # right hemisphere: the arm's side
    if keep.sum() == 0:
        return None, {"n_px": 0, "note": "annulus empty on the arm's side"}
    ang = np.degrees(np.arctan2(dy[keep], dx[keep]))
    return float(np.median(ang)), {
        "n_px": int(keep.sum()),
        "angle_p25": round(float(np.percentile(ang, 25)), 3),
        "angle_p75": round(float(np.percentile(ang, 75)), 3),
    }


def crossing_frame(angles, threshold):
    """First frame index at which the angle series reaches `threshold`, interpolated.

    Returns None if it never does. Linear interpolation between the bracketing frames, so a
    crossing that happens between two frames is not silently rounded to one of them.
    """
    prev = None
    for i, a in enumerate(angles):
        if a is None:
            continue
        if a >= threshold:
            if prev is None:
                return float(i)
            j, b = prev
            if a == b:
                return float(i)
            return j + (threshold - b) / (a - b) * (i - j)
        prev = (i, a)
    return None


# --------------------------------------------------------------------------- driver


def _load_frames(d):
    names = sorted(n for n in os.listdir(d) if n.lower().endswith(".png"))
    if not names:
        raise MeasureError(f"no PNG frames in {d}")
    return names, [np.array(Image.open(os.path.join(d, n)).convert("RGB")) for n in names]


def run(run_dir, joints_path, frames_dir=None, label=None, tol=12):
    with open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    with open(joints_path, encoding="utf-8") as fh:
        side = json.load(fh)
    if "pose_arc" not in side:
        raise MeasureError(f"{joints_path} carries no pose_arc; there is no truth to project")

    w, h = man["resolution"]
    cam = man["spec"]["camera"]
    arc = side["pose_arc"]
    names_of = ("shoulder_r", "elbow_r", "wrist_r")

    truth = []
    for i, fr in enumerate(side["frames"]):
        cm = man["frames"][i]["camera_matrix"]
        pts = np.array([fr["joints_world_zup"][n] for n in names_of])
        px, _ = project(pts, cm, cam["lens_mm"], cam["sensor_mm"], w, h)
        sh, _el, wr = px
        truth.append({
            "frame": i,
            "angle_deg_authored": fr["angle_deg"],
            "shoulder_px": [round(float(v), 2) for v in sh],
            "wrist_px": [round(float(v), 2) for v in wr],
            # The authored angle measured in IMAGE space, which is what a pixel measure can
            # be compared against. It differs slightly from the 3-D arc angle because the
            # camera sits 8 deg above the horizon.
            "angle_deg_image": round(
                float(math.degrees(math.atan2(sh[1] - wr[1], wr[0] - sh[0]))), 3
            ),
        })

    # The annulus is derived from the subject's own projected geometry — never a global
    # constant. r_out is the shoulder-to-wrist distance in pixels; r_in clears the torso.
    span = float(np.hypot(*(np.array(truth[0]["wrist_px"]) - np.array(truth[0]["shoulder_px"]))))
    r_in, r_out = 0.35 * span, 1.10 * span

    out = {
        "label": label or os.path.basename(run_dir),
        "run_dir": os.path.abspath(run_dir),
        "frames_dir": os.path.abspath(frames_dir) if frames_dir else None,
        "resolution": [w, h],
        "arc": {k: arc[k] for k in ("name", "start_deg", "end_deg", "frames")},
        "readout_deg": arc["readout"]["readout_deg"],
        "authored_crossing_frame": arc["readout"]["crossing_frame_exact"],
        "annulus_px": [round(r_in, 2), round(r_out, 2)],
        "shoulder_px": truth[0]["shoulder_px"],
        "truth": truth,
    }

    if frames_dir:
        names, frames = _load_frames(frames_dir)
        shoulder = np.array(truth[0]["shoulder_px"])
        angles, rows = [], []
        for i, (n, f) in enumerate(zip(names, frames)):
            mask, seg = subject_mask(f, tol=tol)
            ang, adiag = arm_angle(mask, shoulder, r_in, r_out)
            angles.append(ang)
            rows.append({"frame": i, "file": n, "angle_deg_measured": (
                round(ang, 3) if ang is not None else None), "segmentation": seg, **adiag})
        out["measured"] = rows
        out["measured_angles"] = [None if a is None else round(a, 3) for a in angles]
        # Image-space readout: the authored 45 deg arc angle lands at this image angle.
        img_readout = truth[arc["readout"]["crossing_frame_nearest"]]["angle_deg_image"]
        out["readout_deg_image"] = img_readout
        out["measured_crossing_frame"] = crossing_frame(angles, img_readout)
        fracs = [r["segmentation"]["subject_fraction"] for r in rows]
        out["segmentation_summary"] = {
            "subject_fraction_min": round(min(fracs), 6),
            "subject_fraction_max": round(max(fracs), 6),
            "frames_without_an_angle": sum(1 for a in angles if a is None),
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="control run dir (for camera + manifest)")
    ap.add_argument("--joints", required=True, help="the subject's .joints.json sidecar")
    ap.add_argument("--frames", default=None, help="image dir to MEASURE (control or output)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--tol", type=int, default=12)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    res = run(a.run, a.joints, frames_dir=a.frames, label=a.label, tol=a.tol)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2)

    print("MEASURE_ARM " + json.dumps({
        "label": res["label"],
        "authored_crossing_frame": res["authored_crossing_frame"],
        "readout_deg_image": res.get("readout_deg_image"),
        "measured_crossing_frame": res.get("measured_crossing_frame"),
        "annulus_px": res["annulus_px"],
        "segmentation": res.get("segmentation_summary"),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
