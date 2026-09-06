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
from armature_core.framing import half_fovs  # noqa: E402
from armature_core.parts import require_finite  # noqa: E402
from measure_lift import as_pairing_rows, gate_pairing  # noqa: E402


class MeasureError(ArmatureError):
    """The measurement could not be made as specified.

    Carries an evidence dict, like every other refusal in this repo: the measurement that
    fired it is the useful half.
    """


# ------------------------------------------------------------------------ projection

#: Half field-of-view per axis, matching Blender's AUTO sensor fit — **imported, not
#: copied**. This file used to carry a third implementation beside
#: `armature_core.blender_scene.half_fovs` and `armature_core.framing.half_fovs`, and
#: justified it by naming a test that pinned the copies together. That test did not
#: exist; `tests/test_framing.py::test_half_fovs_matches_blenders` pins framing's copy
#: against blender_scene's, and this one was pinned by nothing. `framing` imports no bpy,
#: so there was never a reason to copy it — the reason given was blender_scene's import,
#: and framing is the copy that already solved that. `tests/test_measure_arm.py` now
#: exists and asserts the two are one function object.


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


def gate_segmentation(mask, seg, frame, filename):
    """The clause this module's docstring promised and no code implemented.

    The docstring states "an angle whose segmentation is implausible is reported as failed,
    not as a number", records the E02 confound it is written against (a lit studio gradient
    counted as subject at 78-89% coverage), and `subject_mask` says "the caller is expected
    to refuse an implausible one". The caller stored the fraction and refused nothing.

    **The clause, and why it carries no constant.** A shot is framed AROUND the figure —
    `armature_core.framing` solves the camera to bound the subject's own cloud — so the
    four image corners are background by construction. A mask that classifies a corner as
    subject has not found a subject; it has found a gradient. Measured 2026-09-04 on frames
    carrying a left-to-right luminance ramp: `subject_fraction 0.875`, all four corners
    inside the mask, and a confident `angle_deg_measured 0.0` on every frame. A
    subject-fraction band would have needed a number nobody has calibrated (advisor rule 3:
    suspend rather than invent one); the corners are a property of the frame itself.

    Returns `(ok, evidence)`. The row-level caller marks the row failed; the run-level
    caller refuses to publish a crossing frame computed across one.
    """
    h, w = mask.shape
    corners = {"top_left": (0, 0), "top_right": (0, w - 1),
               "bottom_left": (h - 1, 0), "bottom_right": (h - 1, w - 1)}
    hit = sorted(name for name, (y, x) in corners.items() if bool(mask[y, x]))
    # ---- WAVE 25 (F-eb2456cc): `clause` is a WORD, and the sentence moves to `note`.
    #      `clause` is the machine-readable key a halt reader keys on - this repo's own
    #      stated contract, quoted by `tests/_census_nodes.py:797` from
    #      `tests/test_instruments_amend_w14.py:461`: "a halt reader keys on that string,
    #      never on the sentence around it". Derived with the census's own home on
    #      `580af47` (`_census_nodes.clause_literals()`, 385 literals): exactly 4 of the 385
    #      contained a space and the two LONGEST were both this module's - this one at 28
    #      words and `segmentation_summary`'s at 19. A reader or runner keying on the clause
    #      vocabulary to tell one refusal from another met two members no predicate could
    #      match and no fixture could name without quoting a paragraph, and the value that
    #      WOULD be the key - the condition's name - was nowhere on the record, so the same
    #      segmentation failure could not be counted across runs. The sentences are not
    #      wrong; they were the wrong FIELD. `composite_reference.parse_plate` is the shape
    #      followed here: a vocabulary word in `clause`, the full sentence beside it.
    ev = {"gate": "SEGMENTATION", "frame": frame, "file": filename,
          "corners_classified_as_subject": hit,
          "subject_fraction": seg.get("subject_fraction"),
          "background_rgb": seg.get("background_rgb"),
          "tolerance": seg.get("tolerance"),
          "clause": "corner_classified_as_subject",
          "note": ("the four image corners are background on a shot framed around the "
                   "figure; a mask that calls one of them subject has segmented a "
                   "gradient, not a body")}
    if hit:
        ev["verdict"] = "FAILED"
        return False, ev
    ev["verdict"] = "no image corner is inside the subject mask"
    return True, ev


def arm_angle(mask, shoulder_px, r_in, r_out, hemisphere=1):
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
        return None, {"n_px": 0, "hemisphere": int(hemisphere)}
    dx = xs - shoulder_px[0]
    dy = shoulder_px[1] - ys  # image y grows downward; flip so +y is up
    r = np.hypot(dx, dy)
    annulus = (r >= r_in) & (r <= r_out)
    # The SIDE is a measured property of the subject, handed in by the caller from the
    # authored truth — not the `dx > 0` this line used to carry. On a figure whose arm
    # projects to image-LEFT, that constant returned a full series of confident angles off
    # the opposite side of the body, and no key in the record named a hemisphere.
    keep = annulus & ((dx * hemisphere) > 0)
    other = annulus & ((dx * hemisphere) < 0)
    if keep.sum() == 0:
        ev = {"n_px": 0, "hemisphere": int(hemisphere),
              "n_px_other_side": int(other.sum()),
              "note": "annulus empty on the arm's side"}
        if other.sum():
            raise MeasureError(
                f"the annulus holds no subject pixels on the hemisphere the authored "
                f"truth names (sign {int(hemisphere):+d}) while {int(other.sum())} sit on "
                f"the other side; measuring there would report the wrong side of the body "
                f"and reporting no angle would hide that the pixels exist",
                dict(ev, gate="HEMISPHERE"))
        return None, ev
    # Measured in the arm's own frame first, so the median does not wrap at +-180 for a
    # left-side arm, then mapped back to the image convention the authored angle uses.
    rot = np.degrees(np.arctan2(dy[keep], dx[keep] * hemisphere))
    ang = rot if hemisphere > 0 else 180.0 - rot
    return float(np.median(ang)), {
        "n_px": int(keep.sum()),
        "hemisphere": int(hemisphere),
        "n_px_other_side": int(other.sum()),
        "angle_p25": round(float(np.percentile(ang, 25)), 3),
        "angle_p75": round(float(np.percentile(ang, 75)), 3),
    }


def crossing_frame(angles, threshold, failed=None, reasons=None):
    """First frame index at which the angle series reaches `threshold`, interpolated.

    Returns None if it never does. Linear interpolation between the bracketing frames, so a
    crossing that happens between two frames is not silently rounded to one of them.

    `failed` marks rows whose segmentation was refused. A missing angle used to be skipped
    with `continue`, so the number the arm is graded on could be interpolated straight
    across a frame that had no measurement at all — a placeholder shaped like evidence in
    the one scalar this record quotes.
    """
    failed = list(failed) if failed is not None else [False] * len(angles)
    reasons = list(reasons) if reasons is not None else [None] * len(angles)
    prev = None
    for i, a in enumerate(angles):
        if failed[i]:
            raise MeasureError(
                f"frame {i} is a failed row (its segmentation was refused) and lies "
                f"before the crossing ({reasons[i]}); interpolating the crossing frame "
                f"across it would publish a number derived from a frame nothing was "
                f"measured on",
                {"gate": "CROSSING", "failed_row": i, "threshold": threshold,
                 "failed": [j for j, f in enumerate(failed) if f],
                 "failed_reason": reasons[i],
                 "failed_reasons": {j: reasons[j] for j, f in enumerate(failed) if f}})
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
    """The NUMBERED frames of `d`, in index order, and a refusal for anything else.

    The filter its four siblings already have (`encode_control.frame_population`,
    `invert_frames.frame_population`, `measure_clip.frame_paths`,
    `gate_b_frames.frame_paths`), for the reason their docstrings name:
    `render_pose_sticks` writes a `strip_every{N}.png` contact sheet into the very
    directory it just filled with `NNNNN.png` frames. Under the bare `os.listdir` this
    function used, that stray sorted LAST and became the final measured frame of the arm
    arc. Measured 2026-09-04: a 5-frame authored arc against a directory of 10 numbered
    frames plus one `strip_every8.png` produced 11 measured rows, the last naming
    `file: strip_every8.png` as `frame: 10`.

    It raises rather than filtering, because the row it would produce is published as a
    measured angle beside an authored one.
    """
    if not os.path.isdir(d):
        raise MeasureError(f"{d} is not a directory of frames", {"frames_dir": d})
    pngs = sorted(n for n in os.listdir(d) if n.lower().endswith(".png"))
    numbered = [n for n in pngs if os.path.splitext(n)[0].isdigit()]
    unexpected = [n for n in pngs if n not in set(numbered)]
    names = sorted(numbered, key=lambda n: int(os.path.splitext(n)[0]))
    if unexpected:
        raise MeasureError(
            f"{d} holds {len(unexpected)} PNG(s) that are not numbered frames "
            f"({', '.join(unexpected[:8])}); a stray sorts into the population and is "
            f"published as a measured angle beside an authored one",
            {"frames_dir": d, "unexpected": unexpected, "frames": names},
        )
    if not names:
        raise MeasureError(f"no NNNNN.png frames in {d}",
                           {"frames_dir": d, "png_files": pngs})
    return names, [np.array(Image.open(os.path.join(d, n)).convert("RGB")) for n in names]


def arm_hemisphere(truth):
    """`(+1 | -1, why)` — which side of the shoulder the arm projects to, from the truth.

    Derived from the authored frame whose wrist is furthest from the shoulder in x, so a
    pose that happens to start vertical does not decide the side on a rounding error. This
    is the posture `rig_character.which_arm_is_on_plus_x` already takes: the side is a
    measured property of the subject, not a constant in an instrument.
    """
    best, best_dx = None, 0.0
    for row in truth:
        dx = float(row["wrist_px"][0]) - float(row["shoulder_px"][0])
        if abs(dx) > abs(best_dx):
            best, best_dx = row, dx
    if best is None or best_dx == 0.0:
        raise MeasureError(
            "the authored truth places the wrist at the shoulder's own x in every frame, "
            "so the arm projects to neither side and no hemisphere can be derived",
            {"gate": "HEMISPHERE", "frames": len(truth)})
    sign = 1 if best_dx > 0 else -1
    return sign, ("derived from truth frame %s: wrist_px[0] - shoulder_px[0] = %+.2f px"
                  % (best["frame"], best_dx))


def _rows(names, frames, shoulder, r_in, r_out, hemisphere, tol):
    """One row per measured frame, with the segmentation clause applied to each.

    A row whose segmentation is refused carries `angle_deg_measured: None`, `failed: True`
    and a `failed_reason` — "reported as failed, not as a number", which is what this
    module docstring has said since it was written and no code did.
    """
    rows = []
    for n, f in zip(names, frames):
        number = int(os.path.splitext(n)[0])
        mask, seg = subject_mask(f, tol=tol)
        ok, gate = gate_segmentation(mask, seg, number, n)
        if not ok:
            rows.append({"frame": number, "file": n, "angle_deg_measured": None,
                         "segmentation": seg, "gate_SEGMENTATION": gate,
                         "failed": True, "n_px": 0,
                         "failed_reason": (
                             "segmentation refused: image corner(s) %s are inside the "
                             "subject mask at subject_fraction %s"
                             % (", ".join(gate["corners_classified_as_subject"]),
                                seg["subject_fraction"]))})
            continue
        ang, adiag = arm_angle(mask, shoulder, r_in, r_out, hemisphere=hemisphere)
        rows.append({"frame": number, "file": n, "angle_deg_measured": (
            round(ang, 3) if ang is not None else None), "segmentation": seg,
            "gate_SEGMENTATION": gate, "failed": False, "failed_reason": None, **adiag})
    return rows


def rows_for_frames(frames_dir, shoulder, r_in, r_out, hemisphere=1, tol=12):
    """The measured rows for one frames directory, without the authored half.

    Exposed so the segmentation clause can be exercised on its own — the run-level driver
    refuses at the crossing frame, which would otherwise be the only way to see it.
    """
    names, frames = _load_frames(frames_dir)
    return _rows(names, frames, np.array(shoulder), r_in, r_out, hemisphere, tol)


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
    # ---- ANDON on the direction the arithmetic does NOT bound. A NaN span (a projection
    #      that divided by a zero depth) makes `r >= r_in` and `r <= r_out` False in BOTH
    #      directions, so every frame silently reports "no angle" instead of "the
    #      projection failed". `require_finite` is the one helper (armature_core.parts),
    #      raising THIS module's own error so the gate id and evidence stay ours.
    span = require_finite("span_px", span, MeasureError,
                          {"gate": "SPAN", "shoulder_px": truth[0]["shoulder_px"],
                           "wrist_px": truth[0]["wrist_px"],
                           "note": ("nan >= nan is False in both directions, so a "
                                    "non-finite span empties the annulus in silence")})
    r_in, r_out = 0.35 * span, 1.10 * span
    hemisphere, hemi_source = arm_hemisphere(truth)

    out = {
        "label": label or os.path.basename(run_dir),
        "run_dir": os.path.abspath(run_dir),
        "frames_dir": os.path.abspath(frames_dir) if frames_dir else None,
        "resolution": [w, h],
        "arc": {k: arc[k] for k in ("name", "start_deg", "end_deg", "frames")},
        "readout_deg": arc["readout"]["readout_deg"],
        "authored_crossing_frame": arc["readout"]["crossing_frame_exact"],
        "annulus_px": [round(r_in, 2), round(r_out, 2)],
        # The SIDE, beside the radii it is measured with — both derived from the subject's
        # own projected geometry. `arm_angle` used to carry `dx > 0` as a constant.
        "hemisphere": hemisphere,
        "hemisphere_source": hemi_source,
        "shoulder_px": truth[0]["shoulder_px"],
        "truth": truth,
    }

    if frames_dir:
        names, frames = _load_frames(frames_dir)
        # ---- ANDON, before a single angle is computed: the MEASURED population IS the
        #      AUTHORED population, frame for frame, by frame NUMBER. `measure_lift`'s
        #      gate is one import away in the same domain and was not called: measured
        #      2026-09-04, a 5-frame authored arc against a directory of 10 numbered
        #      frames produced `len(truth) == 5` and `len(out["measured"]) == 11` with
        #      no refusal and nothing in the record stating the populations differ —
        #      and `measured_crossing_frame`, the number the arm is graded on, was then
        #      an index into a population nobody described. The rows carry `"frame": i`,
        #      the enumeration index, which is precisely the number `gate_pairing`'s own
        #      docstring says does NOT carry the information.
        out["gate_PAIRING"] = gate_pairing(as_pairing_rows(names), truth)
        shoulder = np.array(truth[0]["shoulder_px"])
        rows = _rows(names, frames, shoulder, r_in, r_out, hemisphere, tol)
        angles = [r["angle_deg_measured"] for r in rows]
        failed = [r["failed"] for r in rows]
        out["measured"] = rows
        out["measured_angles"] = [None if a is None else round(a, 3) for a in angles]
        # Image-space readout: the authored 45 deg arc angle lands at this image angle.
        img_readout = truth[arc["readout"]["crossing_frame_nearest"]]["angle_deg_image"]
        out["readout_deg_image"] = img_readout
        fracs = [r["segmentation"]["subject_fraction"] for r in rows]
        out["segmentation_summary"] = {
            "subject_fraction_min": round(min(fracs), 6),
            "subject_fraction_max": round(max(fracs), 6),
            "frames_without_an_angle": sum(1 for a in angles if a is None),
            "frames_failed": sum(1 for f in failed if f),
            # WAVE 25 (F-eb2456cc): the word is the key; the sentence is the note.
            "clause": "no_corner_is_inside_the_subject_mask",
            "note": ("SEGMENTATION: no image corner is inside the subject mask; a row "
                     "that fails carries angle_deg_measured null and a failed_reason"),
        }
        # ---- ANDON on the one scalar this record quotes. It used to skip a missing angle
        #      with `continue` and interpolate straight across it.
        out["measured_crossing_frame"] = crossing_frame(
            angles, img_readout, failed=failed,
            reasons=[r["failed_reason"] for r in rows])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="where the arm is, frame by frame, in image space — a diagnostic that "
                    "gates nothing")
    ap.add_argument("--run", required=True, help="control run dir (for camera + manifest)")
    ap.add_argument("--joints", required=True, help="the subject's .joints.json sidecar")
    ap.add_argument("--frames", default=None, help="image dir to MEASURE (control or output)")
    ap.add_argument("--label", default=None,
                    help="what this measurement is OF, into the record; default: derived "
                         "from --frames")
    ap.add_argument("--tol", type=int, default=12,
                    help="pixel tolerance the projected joint is matched to the mask "
                         "within (default 12)")
    ap.add_argument("--out", default=None,
                    help="where to write the JSON report; omitted, none is written and the "
                         "numbers only reach stdout")
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
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MEASURE_ARM")
