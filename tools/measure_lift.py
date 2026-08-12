#!/usr/bin/env python
"""measure_lift — the detector, then the solve, then the numbers. In that order.

    python tools/measure_lift.py --render=<dir> --motion=<walk.motion.json>
                                 --manifest=<rig_manifest.json> --model=<pose.task>
                                 --out=<dir>

E09 Stage B1's measurement. No bpy: this reads PNGs, runs MediaPipe, calls the pure
solver, and writes numbers plus a motion record `tools/lift_solve.py` can key.

--------------------------------------------------------------------------------
The detection gate runs FIRST, and it raises

*A number from a detector that did not fire is noise wearing a unit.* So detection is
measured over every frame and gated before a single error is computed. The gate's clause is
not "most frames" — it is **every** frame, because the alternative is a mean over a
population the report never described. If it does not hold, the run halts with the whole
per-frame detection record as its evidence, and that record IS the result: a full negative
for this fixture class is a full success, not a failure to be worked around.

**Where the andon points.** Nothing else in this chain looks at whether the detector saw a
person. The solve happily inverts whatever positions it is handed; the round trip closes on
noise as readily as on a pose; the bone-length residual returns a number for a landmark set
regressed off a shadow. Detection is the one thing the rest of the pipeline cannot see, so
it is the one thing gated here.

--------------------------------------------------------------------------------
The axis convention is MEASURED, not assumed

MediaPipe's world landmarks arrive hip-origin in an image-aligned frame, so turning them
into rig-space directions needs the camera. Two answers are computed and both are reported:

* the **assumed** basis, derived from the render's own recorded camera axes;
* the **best-fit** rotation to the known ground truth, by SVD.

If those disagree, the assumption is wrong — and a wrong basis produces a solve that
round-trips perfectly and is wrong in a consistent direction, which no gate in this repo
could catch. The **handedness** is measured the same way, by fitting the mirrored landmark
assignment as well and reporting which lands closer.

--------------------------------------------------------------------------------
Two gaps, told apart, because otherwise one number carries both

The same solve is run twice: once on the detector's landmarks and once on the **authored
ground-truth positions with no detector in the loop at all**. The first carries the model
gap and the detector gap together; the second carries only the model gap. Quoting one
number for both would make a detector look bad for a torso the model cannot represent, or
a model look bad for a detector's noise.

Nothing here judges whether any of it is good. That is the Director's, at the sheet.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from armature_core import lift_solve as LS
from armature_core import sitelist, walk
from armature_core.errors import ArmatureError, GateFailure

TOOL_VERSION = "E09.1"

#: The one recorded smoothing lever. Applied to the solved rotations, reported before and
#: after, and it gates nothing.
EMA_ALPHA = 0.5

#: The detector's own confidence settings, pinned rather than defaulted silently.
DETECTION_CONF = 0.5
PRESENCE_CONF = 0.5
TRACKING_CONF = 0.5

#: The eight face landmarks and the four torso landmarks H2c is predicted on.
FACE_INDICES = (0, 1, 2, 3, 4, 5, 6, 9, 10)
TORSO_INDICES = (11, 12, 23, 24)


class DetectionGate(GateFailure):
    """The detector did not return a pose on every frame."""

    gate = "DETECT"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--motion", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=16)
    return ap.parse_args()


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------- the ground truth

def read_rest(manifest_path):
    with open(manifest_path, encoding="utf-8") as fh:
        man = json.load(fh)
    rest = {}
    for name, rec in man["landmarks"].items():
        p = rec["p"] if isinstance(rec, dict) and "p" in rec else rec
        if isinstance(p, (list, tuple)) and len(p) == 3:
            rest[name] = tuple(float(v) for v in p)
    return rest, man


def authored_frames(motion, rest):
    """Per frame: the authored local rotations, and every rig site they place.

    The motion sidecar carries only the handful of landmarks `walk.forward_kinematics`
    emits, and the solve needs shoulders, elbows, knees, hips and the head markers too. So
    the full set is rebuilt here from the authored ANGLES through the same kinematics the
    solver inverts — and then cross-checked against the sidecar's own landmarks, so a
    reconstruction that quietly disagreed with the fixture would be caught rather than
    become the ground truth everything else is measured against.
    """
    out = []
    worst = {"frame": None, "site": None, "d": 0.0}
    for rec in motion["ground_truth"]:
        local = {b.name: LS.IDENTITY for b in sitelist.BONES}
        for bone, ch in rec["pose_deg"].items():
            local[bone] = tuple(tuple(float(v) for v in row) for row in
                                walk.rotation_matrix(ch["rx"], ch["ry"], ch["rz"]))
        solved = {"local": local,
                  "root": {"hips_delta_translation": tuple(rec["hips_translation"])}}
        sites = LS.fk_sites(rest, solved)
        for name, want in rec["world"].items():
            got = sites.get({"hips": "crotch"}.get(name, name))
            if got is None:
                continue
            d = LS._norm(LS._sub(tuple(want), got))
            if d > worst["d"]:
                worst = {"frame": rec["frame"], "site": name, "d": d}
        out.append({"frame": rec["frame"], "local": local, "sites": sites,
                    "root": tuple(rec["hips_translation"])})
    return out, worst


# ------------------------------------------------------------------- the detector

def detect(render_dir, model_path, fps):
    """Every frame through the Pose Landmarker. Returns the raw record; gates nothing yet."""
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    frames = sorted(f for f in os.listdir(render_dir)
                    if f.endswith(".png") and f[0].isdigit())
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=DETECTION_CONF,
        min_pose_presence_confidence=PRESENCE_CONF,
        min_tracking_confidence=TRACKING_CONF,
        output_segmentation_masks=False)

    rows = []
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        for i, name in enumerate(frames):
            image = mp.Image.create_from_file(os.path.join(render_dir, name))
            res = landmarker.detect_for_video(image, int(round(i * 1000.0 / fps)))
            fired = bool(res.pose_world_landmarks)
            row = {"frame": i, "file": name, "fired": fired}
            if fired:
                wl = res.pose_world_landmarks[0]
                il = res.pose_landmarks[0]
                row["world"] = [(p.x, p.y, p.z) for p in wl]
                row["image"] = [(p.x, p.y) for p in il]
                row["visibility"] = [float(getattr(p, "visibility", 0.0) or 0.0) for p in il]
                row["presence"] = [float(getattr(p, "presence", 0.0) or 0.0) for p in il]
            rows.append(row)
    return frames, rows


def gate_detection(rows):
    """ANDON — a pose on every frame, before any error number exists.

    Raises on the first shortfall and carries the whole per-frame record, because that
    record is the negative result rather than a diagnostic attached to one.
    """
    fired = [r for r in rows if r["fired"]]
    missed = [r["frame"] for r in rows if not r["fired"]]
    vis = np.array([r["visibility"] for r in fired], dtype=np.float64) if fired else None
    ev = {
        "gate": "DETECT", "n_frames": len(rows), "n_fired": len(fired),
        "fire_rate": (len(fired) / len(rows)) if rows else 0.0,
        "frames_without_a_pose": missed,
        "mean_visibility_all_landmarks": float(vis.mean()) if vis is not None else None,
        "mean_visibility_face_landmarks":
            float(vis[:, list(FACE_INDICES)].mean()) if vis is not None else None,
        "mean_visibility_torso_landmarks":
            float(vis[:, list(TORSO_INDICES)].mean()) if vis is not None else None,
        "per_landmark_mean_visibility":
            {LS.POSE_LANDMARKS[i]: float(vis[:, i].mean()) for i in range(33)}
            if vis is not None else None,
        "per_frame_mean_visibility":
            [float(np.mean(r["visibility"])) for r in fired] if fired else [],
        "detector_confidences": {"detection": DETECTION_CONF, "presence": PRESENCE_CONF,
                                 "tracking": TRACKING_CONF},
    }
    if missed:
        raise DetectionGate(
            f"the Pose Landmarker returned no pose on {len(missed)} of {len(rows)} "
            f"frames ({missed[:12]}{'...' if len(missed) > 12 else ''}). Every metric "
            f"below it would be a mean over a population this report never described, so "
            f"none is computed. This record is the result", ev)
    ev["verdict"] = (f"a pose on all {len(rows)} frames; mean visibility "
                     f"{ev['mean_visibility_all_landmarks']:.4f}")
    return ev


# ----------------------------------------------------------------- the axis convention

def kabsch(a, b):
    """The rotation carrying point cloud `a` onto `b`, both already centred. SVD, with the
    reflection case handled — an unhandled reflection returns an improper 'rotation' that
    fits beautifully and is not a rotation."""
    h = a.T @ b
    u, _, vt = np.linalg.svd(h)
    d = np.sign(np.linalg.det(vt.T @ u.T))
    return vt.T @ np.diag([1.0, 1.0, d]) @ u.T


def fit_convention(detected_sites, truth_sites, sites):
    """Best-fit rotation + uniform scale from the detector's frame to the rig's.

    Reported beside the assumed camera basis. Scale is fitted because MediaPipe regresses
    metres and the rig is in its own units; separating it means the per-bone residuals
    afterwards are about PROPORTION rather than about units.
    """
    a = np.array([detected_sites[s] for s in sites], dtype=np.float64)
    b = np.array([truth_sites[s] for s in sites], dtype=np.float64)
    a -= a.mean(axis=0)
    b -= b.mean(axis=0)
    r = kabsch(a, b)
    ra = a @ r.T
    scale = float((ra * b).sum() / (ra * ra).sum())
    resid = np.linalg.norm(scale * ra - b, axis=1)
    return {"rotation": r.tolist(), "scale": scale,
            "rms_residual": float(np.sqrt((resid ** 2).mean())),
            "max_residual": float(resid.max())}


def basis_from_camera(cam):
    """The assumed detector->rig rotation, from the render's own recorded camera axes.

    MediaPipe's world landmarks are image-aligned: +x runs right across the image, +y runs
    DOWN it, and z grows with distance from the camera. So the columns are the camera's
    right, its negated up, and its negated back.
    """
    right = np.array(cam["basis_right"], dtype=np.float64)
    up = np.array(cam["basis_up"], dtype=np.float64)
    back = np.array(cam["basis_back"], dtype=np.float64)
    return np.column_stack([right, -up, -back])


# ------------------------------------------------------------------------ diagnostics

def orthonormalise(m):
    u, _, vt = np.linalg.svd(m)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1.0
        r = u @ vt
    return r


def ema_rotations(per_frame_local, alpha=EMA_ALPHA):
    """One exponential-moving-average pass over the solved rotations, re-orthonormalised.

    The single smoothing lever this experiment records. It gates nothing and is reported
    beside the unsmoothed numbers, never instead of them.
    """
    out = []
    state = {}
    for rec in per_frame_local:
        row = {}
        for bone, m in rec.items():
            m = np.array(m, dtype=np.float64)
            state[bone] = m if bone not in state else alpha * m + (1 - alpha) * state[bone]
            row[bone] = orthonormalise(state[bone]).tolist()
        out.append(row)
    return out


def jitter(per_frame_local, bones):
    """Median frame-to-frame change per bone, in degrees. The unit is a rotation angle, so
    it needs no scale and cannot be moved by how big the character is."""
    out = {}
    for bone in bones:
        deltas = [LS.geodesic_deg(tuple(map(tuple, per_frame_local[i][bone])),
                                  tuple(map(tuple, per_frame_local[i + 1][bone])))
                  for i in range(len(per_frame_local) - 1)]
        out[bone] = {"median_deg": float(np.median(deltas)),
                     "p90_deg": float(np.percentile(deltas, 90)),
                     "max_deg": float(np.max(deltas))}
    return out


def summarise(values):
    if not values:
        return None
    v = np.array(values, dtype=np.float64)
    return {"n": int(v.size), "median": float(np.median(v)), "mean": float(v.mean()),
            "p90": float(np.percentile(v, 90)), "max": float(v.max()),
            "min": float(v.min())}


def solve_series(rest, obs_frames, diagonal):
    """Solve every frame and collect the per-frame diagnostics. No gate here — the
    observation comes from another body, so a residual is the measurement."""
    locals_, roots, rt, lengths, under, cond = [], [], [], [], [], []
    for obs in obs_frames:
        s = LS.solve_frame(rest, obs)
        locals_.append({k: [list(r) for r in v] for k, v in s["local"].items()})
        roots.append(list(s["root"]["hips_delta_translation"]))
        rt.append(LS.round_trip_report(rest, obs, s, diagonal, raise_on_fail=False))
        lengths.append(LS.bone_length_residuals(rest, obs))
        under.append(sorted(s["underdetermined"]))
        cond.append(s["twist_conditioning"])
    return {"local": locals_, "root": roots, "round_trip": rt, "lengths": lengths,
            "underdetermined": under, "conditioning": cond}


def rotation_errors(solved_local, authored, bones):
    """Per-bone geodesic error, frame by frame, and pooled per bone and per group."""
    per_bone = {b: [] for b in bones}
    for got, want in zip(solved_local, authored):
        for b in bones:
            per_bone[b].append(LS.geodesic_deg(
                want["local"][b], tuple(map(tuple, got[b]))))
    arms = [b for b in bones if b.startswith(("shoulder", "elbow", "wrist"))]
    legs = [b for b in bones if b.startswith(("hip.", "knee", "ankle"))]
    torso = [b for b in bones if b in ("hips", "spine", "chest", "neck", "head")]
    pool = lambda names: summarise([v for b in names for v in per_bone[b]])  # noqa: E731
    return {"per_bone": {b: summarise(v) for b, v in per_bone.items()},
            "all": pool(bones), "arms": pool(arms), "legs": pool(legs),
            "torso": pool(torso)}


def main():
    started = time.time()
    a = parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    with open(os.path.join(a.render, "render_provenance.json"), encoding="utf-8") as fh:
        prov = json.load(fh)
    with open(a.motion, encoding="utf-8") as fh:
        motion = json.load(fh)
    rest, man = read_rest(a.manifest)
    diagonal = float(man["bbox"]["diagonal"])

    truth, truth_check = authored_frames(motion, rest)

    # ---- the detector, then the gate, and nothing numeric before it.
    frame_files, rows = detect(a.render, a.model, a.fps)
    gate = gate_detection(rows)                       # raises; the halt is the result

    sites = sorted(LS.SITE_FROM_LANDMARK)
    cam = prov["camera"]
    assumed = basis_from_camera(cam)

    # ---- the convention, measured three ways on frame 0 and pooled over all frames.
    conv = {"assumed_basis": assumed.tolist(), "per_frame": [], "mirrored_per_frame": []}
    mirror = dict(LS.SITE_FROM_LANDMARK)
    for x, y in (("shoulder_L", "shoulder_R"), ("elbow_L", "elbow_R"),
                 ("wrist_L", "wrist_R"), ("hand_end_L", "hand_end_R"),
                 ("hip_L", "hip_R"), ("knee_L", "knee_R"),
                 ("ankle_L", "ankle_R"), ("toe_L", "toe_R"), ("ear_L", "ear_R")):
        mirror[x], mirror[y] = LS.SITE_FROM_LANDMARK[y], LS.SITE_FROM_LANDMARK[x]

    obs_frames, obs_frames_mirrored = [], []
    for row, tru in zip(rows, truth):
        raw = LS.sites_from_landmarks(row["world"])
        turned = LS.convert_axes(raw, tuple(map(tuple, assumed)))
        obs_frames.append(turned)
        conv["per_frame"].append(fit_convention(turned, tru["sites"], sites))

        raw_m = {s: row["world"][mirror[s]] for s in mirror}
        raw_m = {k: (float(v[0]), float(v[1]), float(v[2])) for k, v in raw_m.items()}
        turned_m = LS.convert_axes(raw_m, tuple(map(tuple, assumed)))
        obs_frames_mirrored.append(turned_m)
        conv["mirrored_per_frame"].append(fit_convention(turned_m, tru["sites"], sites))

    conv["as_read_rms"] = summarise([c["rms_residual"] for c in conv["per_frame"]])
    conv["mirrored_rms"] = summarise([c["rms_residual"] for c in conv["mirrored_per_frame"]])
    conv["scale_detector_to_rig"] = summarise([c["scale"] for c in conv["per_frame"]])
    # The angle between the assumed basis and the measured best fit. If this is not near
    # zero the assumption is wrong, and a wrong basis solves perfectly into the wrong pose.
    conv["assumed_vs_bestfit_deg"] = summarise([
        LS.geodesic_deg(LS.IDENTITY, tuple(map(tuple, np.array(c["rotation"]))))
        for c in conv["per_frame"]])

    # ---- scale the detector's landmarks into the rig's units before any length is read.
    scale = conv["scale_detector_to_rig"]["median"]
    obs_scaled = [{k: LS._scale(v, scale) for k, v in f.items()} for f in obs_frames]

    # ---- the ORACLE arm. Instead of the camera-derived basis, each frame's landmarks are
    # turned by the rotation and scale that best fit that frame's known ground truth. It is
    # an oracle and could never run on a real shot — its only job is to separate the three
    # gaps that would otherwise arrive as one number: what the MODEL cannot represent, what
    # the CONVENTION costs, and what the DETECTOR contributes. Without it, a chain held
    # back by a 16-degree axis assumption would be reported as a noisy detector.
    obs_oracle = []
    for f, c in zip(obs_frames, conv["per_frame"]):
        r = tuple(map(tuple, np.array(c["rotation"])))
        obs_oracle.append({k: LS._scale(LS.mat_vec(r, v), c["scale"])
                           for k, v in f.items()})

    gait_bones = list(walk.GAIT_BONES)
    detected = solve_series(rest, obs_scaled, diagonal)
    oracle = solve_series(rest, obs_oracle, diagonal)
    model_only = solve_series(rest, [{s: t["sites"][s] for s in sites} for t in truth],
                              diagonal)

    err_detected = rotation_errors(detected["local"], truth, gait_bones)
    err_oracle = rotation_errors(oracle["local"], truth, gait_bones)
    err_model = rotation_errors(model_only["local"], truth, gait_bones)

    smoothed = ema_rotations(detected["local"])
    err_smoothed = rotation_errors(smoothed, truth, gait_bones)

    # ---- foot behaviour, through E08's banked diagnostic rather than a new one.
    # `walk.foot_slip` wants hips and both toes per frame in world space; those come from
    # the solved rotations pushed back through the same kinematics.
    def fk_rows(series, roots):
        rows_out = []
        for i, loc in enumerate(series):
            p = LS.fk_sites(rest, {
                "local": {k: tuple(map(tuple, v)) for k, v in loc.items()},
                "root": {"hips_delta_translation": tuple(roots[i])}})
            rows_out.append({"frame": i, "hips": list(p["crotch"]),
                             "toe_L": list(p["toe_L"]), "toe_R": list(p["toe_R"])})
        return rows_out

    feet = {
        "detected": walk.foot_slip(fk_rows(detected["local"], detected["root"])),
        "detected_after_one_ema_pass": walk.foot_slip(
            fk_rows(smoothed, detected["root"])),
        "model_gap_only_no_detector": walk.foot_slip(
            fk_rows(model_only["local"], model_only["root"])),
        "authored_ground_truth": walk.foot_slip(
            fk_rows([t["local"] for t in truth], [t["root"] for t in truth])),
    }

    record = {
        "tool": "measure_lift", "tool_version": TOOL_VERSION,
        "solver_version": LS.TOOL_VERSION,
        "inputs": {
            "render": os.path.abspath(a.render),
            "render_provenance": prov["tool_version"],
            "motion": os.path.abspath(a.motion),
            "manifest": os.path.abspath(a.manifest),
            "model": os.path.abspath(a.model), "model_sha256": _sha256(a.model),
            "frames": len(rows), "fps": a.fps,
        },
        "ground_truth_reconstruction_check": {
            "worst": truth_check,
            "note": ("max distance between the sidecar's own landmark positions and the "
                     "ones rebuilt here from the authored angles; the ground truth every "
                     "error below is quoted against"),
        },
        "gates": {"DETECT": gate},
        "convention": dict(
            {k: v for k, v in conv.items()
             if k not in ("per_frame", "mirrored_per_frame")},
            assumed_vs_bestfit_per_frame_deg=[
                LS.geodesic_deg(LS.IDENTITY, tuple(map(tuple, np.array(c["rotation"]))))
                for c in conv["per_frame"]],
            per_frame_rms_residual=[c["rms_residual"] for c in conv["per_frame"]],
            per_frame_scale=[c["scale"] for c in conv["per_frame"]]),
        "rotation_error_deg": {
            "detected": err_detected,
            "detected_with_oracle_axis_fit": err_oracle,
            "model_gap_only_no_detector": err_model,
            "detected_after_one_ema_pass": err_smoothed,
            "ema_alpha": EMA_ALPHA,
            "how_to_read": (
                "model_gap_only carries no detector at all — it is what this solver's "
                "parameterisation costs on a motion it cannot fully represent. "
                "detected_with_oracle_axis_fit adds the detector but removes the axis "
                "convention by fitting each frame to ground truth, which no real shot "
                "could do. detected is the deployable chain. The differences between the "
                "three are the model gap, the detector gap and the convention gap"),
        },
        "jitter_deg": {
            "detected": jitter(detected["local"], gait_bones),
            "detected_after_one_ema_pass": jitter(smoothed, gait_bones),
            "authored_ground_truth": jitter([t["local"] for t in truth], gait_bones),
        },
        "bone_length_residual_fraction": {
            bone: summarise([f[bone]["residual_fraction"] for f in detected["lengths"]])
            for bone in detected["lengths"][0]
        },
        "round_trip_residual": {
            "detected": summarise([r["worst"]["d"] for r in detected["round_trip"]]),
            "model_gap_only": summarise([r["worst"]["d"] for r in model_only["round_trip"]]),
            "tolerance_used_by_the_stage_a_gate": LS.ROUND_TRIP_TOL_FRAC * diagonal,
            "note": ("no gate here: the observation comes from another body, so a "
                     "residual is the measurement rather than a defect"),
        },
        "foot_slip": {
            k: {"slide_fraction_total": v["slide"]["slide_fraction_total"],
                "slower_foot_path": v["slide"]["slower_foot_path"],
                "hips_path": v["slide"]["hips_path"],
                "max_slip_either_foot": v["max_slip_either_foot"],
                "n_contacts_L": v["L"]["n_contacts"], "n_contacts_R": v["R"]["n_contacts"]}
            for k, v in feet.items()
        },
        "twist_underdetermined_frames_per_bone": {
            bone: sum(1 for u in detected["underdetermined"] if bone in u)
            for bone in gait_bones
        },
        "twist_conditioning_sine": {
            bone: summarise([c[bone] for c in detected["conditioning"] if bone in c])
            for bone in gait_bones
            if any(bone in c for c in detected["conditioning"])
        },
        "elapsed_s": time.time() - started,
    }

    with open(os.path.join(out, "measurement.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    with open(os.path.join(out, "detection_raw.json"), "w", encoding="utf-8") as fh:
        json.dump({"frames": frame_files, "rows": rows}, fh)
    for name, series, roots in (("lifted", detected["local"], detected["root"]),
                                ("lifted_ema", smoothed, detected["root"])):
        with open(os.path.join(out, f"{name}.motion.json"), "w", encoding="utf-8") as fh:
            json.dump({"tool": "measure_lift", "tool_version": TOOL_VERSION,
                       "source": os.path.abspath(a.render),
                       "ema_alpha": EMA_ALPHA if name.endswith("ema") else None,
                       "frames": [{"frame": i, "local": series[i], "root": roots[i]}
                                  for i in range(len(series))]}, fh)

    print("MEASURE_LIFT_OK " + json.dumps({
        "out": out, "frames": len(rows), "fire_rate": gate["fire_rate"],
        "mean_visibility": gate["mean_visibility_all_landmarks"],
        "median_rotation_error_deg_detected": err_detected["all"]["median"],
        "median_rotation_error_deg_model_only": err_model["all"]["median"],
    }))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("MEASURE_LIFT_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
