#!/usr/bin/env python
"""lift_clip — a generated clip through the detector and the solver. No ground truth.

    python tools/lift_clip.py --frames=<dir> --manifest=<rig_manifest.json>
                              --model=<pose.task> --out=<dir>

E09 Stage B2's measurement. B1 had an authored performance to measure against; a generated
dance has none, so every quantity here is either **self-referential** (does the solve
reproduce the positions it was solved from) or **pose-invariant** (bone lengths, jitter).
Nothing here is compared to a truth that does not exist, and nothing here judges quality.

--------------------------------------------------------------------------------
The detection gate runs FIRST, and it raises

Same clause as B1: a pose on EVERY frame, or the run halts with the whole per-frame record
as evidence. A mean over a partly-detected population is a mean over a population no report
described.

--------------------------------------------------------------------------------
Two things B1 measured that this stage cannot, and says so instead of pretending

* **The axis convention.** B1 fitted the detector's frame against known ground truth and
  found the camera-derived basis sitting 16.26 degrees off. Here there is no ground truth
  and no camera record, so the basis is ASSUMED — the frontal-camera convention below — and
  the offset it carries is unquantified. B1 measured where that cost lands: almost entirely
  on the root (`hips` 27.98 deg vs 19.14 deg with an oracle fit) and nowhere else, because
  parent-relative rotations absorb a global mis-rotation at the root. Root motion is out of
  scope for this stage anyway (premise 7), so the limbs — which is what a dance is — are
  read at the same cost B1 measured for them, which was none.
* **The scale.** B1 fitted it against ground truth. Here it comes from a pose-invariant
  quantity instead: the ratio of summed rest segment lengths to summed observed segment
  lengths. Bone lengths do not change with pose, so this is a size correction that does not
  need to know what the dancer was doing.
"""

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from armature_core import lift_solve as LS
from armature_core import sitelist, walk
from armature_core.errors import ArmatureError, GateFailure

TOOL_VERSION = "E09.2"
EMA_ALPHA = 0.5
DETECTION_CONF = 0.5
PRESENCE_CONF = 0.5
TRACKING_CONF = 0.5

FACE_INDICES = (0, 1, 2, 3, 4, 5, 6, 9, 10)
TORSO_INDICES = (11, 12, 23, 24)
#: The landmarks that fall outside a frame cropped above the ankle. Named so a report can
#: say which numbers are extrapolations rather than observations.
LOWER_LEG_INDICES = (27, 28, 29, 30, 31, 32)

#: MediaPipe world landmarks are image-aligned: +x runs right across the image, +y runs
#: DOWN it, +z grows with distance from the camera. For a camera in front of a character
#: who faces -Y in a Z-up rig, that maps to world +X, -Z, +Y as columns. ASSUMED — there is
#: no camera record for a generated clip, and B1 measured what the assumption costs.
FRONTAL_BASIS = ((1.0, 0.0, 0.0),
                 (0.0, 0.0, 1.0),
                 (0.0, -1.0, 0.0))


class DetectionGate(GateFailure):
    """The detector did not return a pose on every frame."""

    gate = "DETECT"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=16)
    return ap.parse_args()


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_rest(manifest_path):
    with open(manifest_path, encoding="utf-8") as fh:
        man = json.load(fh)
    rest = {}
    for name, rec in man["landmarks"].items():
        p = rec["p"] if isinstance(rec, dict) and "p" in rec else rec
        if isinstance(p, (list, tuple)) and len(p) == 3:
            rest[name] = tuple(float(v) for v in p)
    return rest, man


def detect(frames_dir, model_path, fps):
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    names = sorted(f for f in os.listdir(frames_dir)
                   if f.endswith(".png") and f[0].isdigit())
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.VIDEO, num_poses=1,
        min_pose_detection_confidence=DETECTION_CONF,
        min_pose_presence_confidence=PRESENCE_CONF,
        min_tracking_confidence=TRACKING_CONF,
        output_segmentation_masks=False)
    rows = []
    with vision.PoseLandmarker.create_from_options(options) as lm:
        for i, name in enumerate(names):
            image = mp.Image.create_from_file(os.path.join(frames_dir, name))
            res = lm.detect_for_video(image, int(round(i * 1000.0 / fps)))
            fired = bool(res.pose_world_landmarks)
            row = {"frame": i, "file": name, "fired": fired}
            if fired:
                row["world"] = [(p.x, p.y, p.z) for p in res.pose_world_landmarks[0]]
                row["image"] = [(p.x, p.y) for p in res.pose_landmarks[0]]
                row["visibility"] = [float(getattr(p, "visibility", 0.0) or 0.0)
                                     for p in res.pose_landmarks[0]]
            rows.append(row)
    return names, rows


def gate_detection(rows):
    """ANDON — a pose on every frame, before any error number exists."""
    fired = [r for r in rows if r["fired"]]
    missed = [r["frame"] for r in rows if not r["fired"]]
    vis = np.array([r["visibility"] for r in fired], dtype=np.float64) if fired else None
    # How far outside the frame the detector placed each landmark, which is the honest way
    # to report a body the shot cropped: an image landmark below y=1 is extrapolated, not
    # seen, and its world position is a guess wearing the same units as a measurement.
    out_of_frame = None
    if fired:
        img = np.array([r["image"] for r in fired], dtype=np.float64)
        outside = (img[:, :, 1] > 1.0) | (img[:, :, 1] < 0.0) | \
                  (img[:, :, 0] > 1.0) | (img[:, :, 0] < 0.0)
        out_of_frame = {LS.POSE_LANDMARKS[i]: float(outside[:, i].mean())
                        for i in range(33)}
    ev = {
        "gate": "DETECT", "n_frames": len(rows), "n_fired": len(fired),
        "fire_rate": (len(fired) / len(rows)) if rows else 0.0,
        "frames_without_a_pose": missed,
        "mean_visibility_all_landmarks": float(vis.mean()) if vis is not None else None,
        "mean_visibility_face_landmarks":
            float(vis[:, list(FACE_INDICES)].mean()) if vis is not None else None,
        "mean_visibility_torso_landmarks":
            float(vis[:, list(TORSO_INDICES)].mean()) if vis is not None else None,
        "mean_visibility_lower_leg_landmarks":
            float(vis[:, list(LOWER_LEG_INDICES)].mean()) if vis is not None else None,
        "per_landmark_mean_visibility":
            {LS.POSE_LANDMARKS[i]: float(vis[:, i].mean()) for i in range(33)}
            if vis is not None else None,
        "fraction_of_frames_landmark_lies_outside_the_image": out_of_frame,
        "detector_confidences": {"detection": DETECTION_CONF, "presence": PRESENCE_CONF,
                                 "tracking": TRACKING_CONF},
    }
    if missed:
        raise DetectionGate(
            f"the Pose Landmarker returned no pose on {len(missed)} of {len(rows)} frames "
            f"({missed[:12]}). Every metric below it would be a mean over a population "
            f"this report never described, so none is computed. This record is the result",
            ev)
    ev["verdict"] = (f"a pose on all {len(rows)} frames; mean visibility "
                     f"{ev['mean_visibility_all_landmarks']:.4f}")
    return ev


def pose_invariant_scale(rest, obs_frames):
    """Detector units -> rig units, from bone lengths rather than from a truth we lack.

    Summed segment length is pose-invariant: a limb does not get longer when it bends. So
    the ratio of the rig's own summed rest segments to the detector's summed observed
    segments is a size correction that needs to know nothing about what the dancer did.
    """
    pairs = []
    for bone in sitelist.BONES:
        rule = LS.MODEL.get(bone.name)
        if rule and rule[0] == "direction":
            pairs.append((bone.head, rule[1]))
    rest_total = sum(LS._norm(LS._sub(rest[b], rest[a])) for a, b in pairs)
    per_frame = []
    for f in obs_frames:
        got = sum(LS._norm(LS._sub(f[b], f[a])) for a, b in pairs)
        per_frame.append(rest_total / got if got > 0 else None)
    good = [s for s in per_frame if s]
    return float(np.median(good)), per_frame, rest_total


def orthonormalise(m):
    u, _, vt = np.linalg.svd(m)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1.0
        r = u @ vt
    return r


def ema_rotations(series, alpha=EMA_ALPHA):
    out, state = [], {}
    for rec in series:
        row = {}
        for bone, m in rec.items():
            m = np.array(m, dtype=np.float64)
            state[bone] = m if bone not in state else alpha * m + (1 - alpha) * state[bone]
            row[bone] = orthonormalise(state[bone]).tolist()
        out.append(row)
    return out


def jitter(series, bones):
    out = {}
    for bone in bones:
        d = [LS.geodesic_deg(tuple(map(tuple, series[i][bone])),
                             tuple(map(tuple, series[i + 1][bone])))
             for i in range(len(series) - 1)]
        out[bone] = {"median_deg": float(np.median(d)), "p90_deg": float(np.percentile(d, 90)),
                     "max_deg": float(np.max(d))}
    return out


def summarise(v):
    if not v:
        return None
    a = np.array(v, dtype=np.float64)
    return {"n": int(a.size), "median": float(np.median(a)), "mean": float(a.mean()),
            "p90": float(np.percentile(a, 90)), "max": float(a.max()), "min": float(a.min())}


def main():
    started = time.time()
    a = parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    rest, man = read_rest(a.manifest)
    diagonal = float(man["bbox"]["diagonal"])

    names, rows = detect(a.frames, a.model, a.fps)
    gate = gate_detection(rows)                        # raises; the halt is the result

    sites = sorted(LS.SITE_FROM_LANDMARK)
    obs = [LS.convert_axes(LS.sites_from_landmarks(r["world"]), FRONTAL_BASIS) for r in rows]
    scale, per_frame_scale, rest_total = pose_invariant_scale(rest, obs)
    obs_scaled = [{k: LS._scale(v, scale) for k, v in f.items()} for f in obs]

    locals_, roots, rt, lengths, under, cond = [], [], [], [], [], []
    for f in obs_scaled:
        s = LS.solve_frame(rest, f)
        locals_.append({k: [list(r) for r in v] for k, v in s["local"].items()})
        roots.append(list(s["root"]["hips_delta_translation"]))
        rt.append(LS.round_trip_report(rest, f, s, diagonal, raise_on_fail=False))
        lengths.append(LS.bone_length_residuals(rest, f))
        under.append(sorted(s["underdetermined"]))
        cond.append(s["twist_conditioning"])

    gait_bones = list(walk.GAIT_BONES)
    smoothed = ema_rotations(locals_)

    def fk_rows(series):
        o = []
        for i, loc in enumerate(series):
            p = LS.fk_sites(rest, {"local": {k: tuple(map(tuple, v)) for k, v in loc.items()},
                                   "root": {"hips_delta_translation": tuple(roots[i])}})
            o.append({"frame": i, "hips": list(p["crotch"]),
                      "toe_L": list(p["toe_L"]), "toe_R": list(p["toe_R"])})
        return o

    feet = {"detected": walk.foot_slip(fk_rows(locals_)),
            "detected_after_one_ema_pass": walk.foot_slip(fk_rows(smoothed))}

    record = {
        "tool": "lift_clip", "tool_version": TOOL_VERSION,
        "solver_version": LS.TOOL_VERSION,
        "inputs": {"frames": os.path.abspath(a.frames), "n_frames": len(rows),
                   "manifest": os.path.abspath(a.manifest),
                   "model": os.path.abspath(a.model), "model_sha256": _sha256(a.model),
                   "fps": a.fps},
        "gates": {"DETECT": gate},
        "axis_convention": {
            "basis": [list(r) for r in FRONTAL_BASIS], "status": "ASSUMED",
            "why": ("a generated clip carries no camera record, so the basis cannot be "
                    "measured the way B1 measured it against known ground truth"),
            "what_b1_measured_about_this": (
                "the camera-derived basis sat 16.26 deg (median) from the best fit, and the "
                "cost landed almost entirely on the root — hips 27.98 vs 19.14 deg with an "
                "oracle fit, every limb bone identical to two decimal places"),
        },
        "scale_detector_to_rig": {
            "value": scale, "method": "pose-invariant summed bone length ratio",
            "rest_summed_segment_length": rest_total,
            "per_frame": summarise([s for s in per_frame_scale if s]),
        },
        "jitter_deg": {"detected": jitter(locals_, gait_bones),
                       "detected_after_one_ema_pass": jitter(smoothed, gait_bones),
                       "ema_alpha": EMA_ALPHA},
        "bone_length_residual_fraction": {
            bone: summarise([f[bone]["residual_fraction"] for f in lengths])
            for bone in lengths[0]},
        "round_trip_residual": {
            "detected": summarise([r["worst"]["d"] for r in rt]),
            "bbox_diagonal": diagonal,
            "note": ("no gate: the observation comes from another body entirely, so a "
                     "residual is the measurement rather than a defect"),
        },
        "twist_underdetermined_frames_per_bone": {
            b: sum(1 for u in under if b in u) for b in gait_bones},
        "twist_conditioning_sine": {
            b: summarise([c[b] for c in cond if b in c]) for b in gait_bones
            if any(b in c for c in cond)},
        "foot_slip": {
            k: {"slide_fraction_total": v["slide"]["slide_fraction_total"],
                "slower_foot_path": v["slide"]["slower_foot_path"],
                "hips_path": v["slide"]["hips_path"],
                "max_slip_either_foot": v["max_slip_either_foot"]}
            for k, v in feet.items()},
        "foot_slip_caveat": (
            "the headline ratio's denominator is the hips' path, which the hip-origin "
            "landmark convention pins near zero — E09 R3 ruled this metric valid on "
            "world-rooted motion and INVALID on hip-origin lifted motion. Numerator and "
            "denominator are carried separately and the ratio is not quoted as a reading."),
        "elapsed_s": time.time() - started,
    }
    with open(os.path.join(out, "measurement.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    with open(os.path.join(out, "detection_raw.json"), "w", encoding="utf-8") as fh:
        json.dump({"frames": names, "rows": rows}, fh)
    for name, series in (("lifted", locals_), ("lifted_ema", smoothed)):
        with open(os.path.join(out, f"{name}.motion.json"), "w", encoding="utf-8") as fh:
            json.dump({"tool": "lift_clip", "tool_version": TOOL_VERSION,
                       "source": os.path.abspath(a.frames),
                       "ema_alpha": EMA_ALPHA if name.endswith("ema") else None,
                       "frames": [{"frame": i, "local": series[i], "root": roots[i]}
                                  for i in range(len(series))]}, fh)

    print("LIFT_CLIP_OK " + json.dumps({
        "out": out, "frames": len(rows), "fire_rate": gate["fire_rate"],
        "mean_visibility": gate["mean_visibility_all_landmarks"],
        "scale": round(scale, 5),
        "median_jitter_deg": float(np.median(
            [v["median_deg"] for v in record["jitter_deg"]["detected"].values()]))}))
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
        print("LIFT_CLIP_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
