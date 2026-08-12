#!/usr/bin/env python
"""project_pose_keypoints — the rig's AAPose-20 keypoints, per frame, in pixels.

    python tools\\project_pose_keypoints.py --motion=<lifted_ema.motion.json>
           --manifest=<rig_manifest.json> --out=<dir> [--width=832 --height=480]
           [--camera-json=<a prior camera record>]

Stage 1 of the pose-stick commission (E08). It decides WHERE the joints are;
`tools/render_pose_sticks.py` decides how they are drawn. Split where their secrets are
(DECOMPOSE_BY_SECRETS): what changes here is kinematics and framing, what changes there is a
drawing convention pinned to somebody else's source file.

**No Blender, and that is a correction rather than a convenience.** The first version of
this tool imported the exported GLB and read bone heads and tails. Eighteen keypoints landed
correctly; the two that did not were the toes, because glTF stores joints as nodes and has
no notion of a bone tail, so Blender's importer synthesises one for every leaf bone — and
the ankles are leaves. Every gate in that version passed on the wrong output. It is kept
runnable with its numbers at `tools/superseded/project_pose_keypoints_from_glb.py`.

What replaced it places landmarks with `armature_core.lift_solve.fk_sites`: the rig
manifest's MEASURED rest landmarks, moved by the motion record's per-bone rotations, through
the same kinematics the solver inverts and `tests/test_lift_solve.py` already exercises.
`toe_L` and `toe_R` are measured landmarks there — "furthest foot vertex in the measured
facing direction, at ground" — so nothing about a foot is synthesised.

**The camera is the E09 previz camera.** Azimuth 225 / elevation 6 / lens 50 / height-frac
0.70 are `render_performer`'s banked constants, reused verbatim so the stick frames and the
previz frames are the same composition at two resolutions and the Gate 0 sheet compares
panels rather than compositions. Figure size is E10's variable (E09 closing ruling, open
items); holding it fixed here is the one-variable discipline, not a preference. Pass
`--camera-json` to pin an exact prior camera instead of solving one — that is what makes the
overlay check possible, and its loader refuses a record that disagrees about any angle.

Prints `PROJECT_POSE_OK`.

--------------------------------------------------------------------------------
The gates — all raise, in-process, before the JSON exists

* **Gate MAP** — `aapose.require_rig_map`. A keypoint whose landmark is missing would be
  written as a zero and drawn as a limb running to the corner of the frame, erroring nowhere.
* **Gate FRONT** — every keypoint of every frame projects in FRONT of the camera. A point
  behind the camera has no screen position at all; a caller that merely skipped it would
  emit a frame with a limb silently absent.
* **Gate FRAMING** — the solved composition keeps the whole performance inside the frame. A
  clipped driving signal drives the part it can see and reports nothing. Skipped, and
  recorded as skipped, when the camera is pinned instead of solved.
* **Gate MOTION** — the PROJECTED keypoints are not identical at every frame. A pose video
  that does not move would drive a still, and the frame count, the file count and every
  legality check pass on 65 copies of one pose.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing a JSON under
`outputs/`. Compensator: delete the directory; owner: the executor session. The motion
record and the manifest are opened read-only.
"""

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from armature_core import aapose, framing, lift_solve, sitelist  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E08.2"

#: `render_performer`'s banked composition, verbatim. See the module docstring.
AZIMUTH_DEG = 225.0
ELEVATION_DEG = 6.0
LENS_MM = 50.0
SENSOR_MM = 36.0
HEIGHT_FRAC = 0.70
END_X_FRAC = 0.62
TARGET_Y_FRAC = 0.52

#: The angles a pinned camera record must agree with before it may be used here.
PINNED_CAMERA_EXPECT = {
    "azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG,
    "lens_mm": LENS_MM, "sensor_mm": SENSOR_MM,
}

#: Rendered ground truth carries no uncertainty: we know where every joint is, including the
#: ones the body occludes. Emitted at 1.0 so the convention's `threshold` never drops one.
#: The consequence is recorded rather than tuned: a real detector would report low confidence
#: on an occluded joint and Wan would see it dropped, where it sees ours drawn.
GROUND_TRUTH_CONFIDENCE = 1.0


class ProjectGate(GateFailure):
    gate = "PROJECT"


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--motion", required=True,
                    help="a motion record: {frames: [{local: {bone: 3x3}, root: [x,y,z]}]}")
    ap.add_argument("--manifest", required=True, help="the rig manifest (rest landmarks)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--camera-json", default=None,
                    help="reuse a PINNED camera instead of solving one (argparse eats "
                         "leading minus signs, so pass flags as --flag=value)")
    return ap.parse_args(argv)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rest_landmarks(manifest):
    """The rig's measured rest landmarks, as plain 3-tuples."""
    out = {}
    for name, rec in manifest["landmarks"].items():
        p = rec["p"] if isinstance(rec, dict) and "p" in rec else rec
        if isinstance(p, (list, tuple)) and len(p) == 3:
            out[name] = tuple(float(v) for v in p)
    return out


def placed_frames(rest, motion):
    """Every landmark's world position at every frame, through `lift_solve.fk_sites`."""
    out = []
    for fr in motion["frames"]:
        solved = {
            "local": {k: tuple(tuple(float(x) for x in row) for row in v)
                      for k, v in fr["local"].items()},
            "root": {"hips_delta_translation": tuple(float(v) for v in fr["root"])},
        }
        out.append(lift_solve.fk_sites(rest, solved))
    return out


def body_cloud(placed, lo, hi):
    """Points that must stay in frame for one frame — `render_performer.body_cloud`'s shape.

    Lifted in form rather than re-derived so the two tools frame the same performance the
    same way. Landmarks under-report the SILHOUETTE (this character's torso is wider than
    his shoulder joints), so the rest bbox's own half-extents are hung on the hips as a
    bound. `render_performer` aliases the `crotch` landmark to the name `hips`; the same
    point is used here under its own name.
    """
    pts = [tuple(v) for v in placed.values() if isinstance(v, (list, tuple)) and len(v) == 3]
    hx, hy = 0.5 * (hi[0] - lo[0]), 0.5 * (hi[1] - lo[1])
    hips = tuple(placed["crotch"])
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            pts.append((hips[0] + sx * hx, hips[1] + sy * hy, hips[2]))
    return pts


def hand_points(placed, side):
    """The 21 synthesised mitten-hand world points for one frame and one side."""
    wrist, hand_end, elbow = aapose.HAND_SITES[side]
    d, s, length = aapose.hand_frame(placed[wrist], placed[hand_end], placed[elbow])
    return aapose.mitten_hand(placed[wrist], d, s, length)


def to_pixels(points, target, radius, width, height, label, frame_index):
    """Project world points to pixel coordinates. Gate FRONT raises here.

    The gate is inside the projection because this is the last moment the mistake is cheap:
    downstream every point is already a number, and a dropped joint looks exactly like a
    joint the convention's threshold declined to draw.
    """
    out = []
    for j, p in enumerate(points):
        fx, fy, ok = framing.project(p, target, radius, AZIMUTH_DEG, ELEVATION_DEG,
                                     LENS_MM, SENSOR_MM, width, height)
        if not ok:
            raise ProjectGate(
                f"frame {frame_index}, {label} point {j} is BEHIND the camera and has no "
                f"screen position. Skipping it would emit a pose frame with a limb silently "
                f"absent and nothing would error",
                {"frame": frame_index, "channel": label, "index": j,
                 "world": [float(v) for v in p]})
        out.append([fx * width, fy * height, GROUND_TRUTH_CONFIDENCE])
    return out


def gate_motion(body_px, n_frames):
    """Gate MOTION · ANDON — the pose sequence is a performance, not N copies of a pose.

    The quantity is the rounded PROJECTED body keypoints, because that is what actually
    reaches the model: a rig that moved only along the camera axis would move in world space
    and not on screen, and the model would be driven by a still either way. Raising on ALL
    frames identical rather than on any adjacent pair identical is deliberate — a slow
    passage can legitimately hold, and a gate that fired on that would fail on correct work.
    """
    sigs = {json.dumps([[round(v, 3) for v in kp] for kp in f]) for f in body_px}
    ev = {"gate": "MOTION", "n_frames": n_frames, "distinct_projected_poses": len(sigs)}
    if n_frames < 2:
        raise ProjectGate(
            f"a pose video of {n_frames} frame(s) carries no motion to drive with", ev)
    if len(sigs) == 1:
        raise ProjectGate(
            f"all {n_frames} projected poses are IDENTICAL — the driving signal is a still. "
            f"The frame count, the file count and every legality check pass on this",
            ev)
    ev["verdict"] = f"{len(sigs)} distinct projected poses over {n_frames} frames"
    return ev


def span_stats(seq):
    """Per-frame max extent of a keypoint set, in pixels. A diagnostic; gates nothing."""
    per = []
    for f in seq:
        xs = [kp[0] for kp in f]
        ys = [kp[1] for kp in f]
        per.append(max(max(xs) - min(xs), max(ys) - min(ys)))
    return {"min": min(per), "median": sorted(per)[len(per) // 2], "max": max(per)}


def main(argv=None):
    started = time.time()
    a = parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    sitelist.validate()
    with open(a.manifest, encoding="utf-8") as fh:
        rig = json.load(fh)
    with open(a.motion, encoding="utf-8") as fh:
        motion = json.load(fh)

    rest = rest_landmarks(rig)
    aapose.require_rig_map(rest)                    # Gate MAP, before anything is placed
    lo, hi = rig["bbox"]["lo"], rig["bbox"]["hi"]

    n_frames = len(motion["frames"])
    placed = placed_frames(rest, motion)

    # ---- the camera: solved over the whole performance, or pinned to a prior record
    clouds = [body_cloud(p, lo, hi) for p in placed]
    if a.camera_json:
        target, radius = framing.load_pinned_camera(a.camera_json, PINNED_CAMERA_EXPECT)
        sol = {"target": list(target), "radius": radius,
               "pinned_from": os.path.abspath(a.camera_json)}
        framing_gate = {"verdict": "SKIPPED — camera pinned, not solved",
                        "pinned_from": os.path.abspath(a.camera_json)}
    else:
        sol = framing.solve_camera([p for c in clouds for p in c], clouds[-1],
                                   AZIMUTH_DEG, ELEVATION_DEG, LENS_MM, SENSOR_MM,
                                   a.width, a.height, height_frac=HEIGHT_FRAC,
                                   end_x_frac=END_X_FRAC, target_y_frac=TARGET_Y_FRAC)
        if not sol["in_frame"]:
            raise ProjectGate(
                f"the solved composition puts part of the performance outside the frame: "
                f"x {sol['achieved']['union_x']} y {sol['achieved']['union_y']}. A clipped "
                f"driving signal drives the part it can see and reports nothing",
                {"solution": sol})
        framing_gate = {"verdict": "PASS", "achieved": sol["achieved"]}
        target, radius = tuple(sol["target"]), float(sol["radius"])

    body_px, lhand_px, rhand_px = [], [], []
    for i, p in enumerate(placed):
        body_px.append(to_pixels([p[s] for s in aapose.LANDMARK_SITES],
                                 target, radius, a.width, a.height, "body", i))
        lhand_px.append(to_pixels(hand_points(p, "left"), target, radius,
                                  a.width, a.height, "left_hand", i))
        rhand_px.append(to_pixels(hand_points(p, "right"), target, radius,
                                  a.width, a.height, "right_hand", i))

    gate_mot = gate_motion(body_px, n_frames)

    # Diagnostics. They gate nothing. The ankle->toe ratio is here because it is the
    # quantity that caught the superseded route: a foot is a small fraction of a leg, and
    # a number two to three times too large is what a synthesised bone tail looks like.
    ratios = []
    for f in body_px:
        leg = float(np.hypot(f[8][0] - f[10][0], f[8][1] - f[10][1]))
        foot = float(np.hypot(f[10][0] - f[19][0], f[10][1] - f[19][1]))
        if leg > 0:
            ratios.append(foot / leg)

    payload = {
        "tool": "project_pose_keypoints",
        "tool_version": TOOL_VERSION,
        "convention": dict(aapose.SOURCE),
        "source": {"motion": os.path.abspath(a.motion), "motion_sha256": _sha256(a.motion),
                   "manifest": os.path.abspath(a.manifest),
                   "manifest_sha256": _sha256(a.manifest),
                   "kinematics": "armature_core.lift_solve.fk_sites"},
        "resolution": [a.width, a.height],
        "frames": n_frames,
        "fps": a.fps,
        "confidence": {"value": GROUND_TRUTH_CONFIDENCE,
                       "note": ("rendered ground truth carries no uncertainty; occluded "
                                "joints are emitted, where a detector would drop them")},
        "camera": {
            "azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG,
            "lens_mm": LENS_MM, "sensor_mm": SENSOR_MM,
            "target": list(target), "radius": radius,
            "height_frac": HEIGHT_FRAC, "end_x_frac": END_X_FRAC,
            "target_y_frac": TARGET_Y_FRAC,
            "solver_achieved": sol.get("achieved"), "in_frame": sol.get("in_frame"),
            "pinned_from": sol.get("pinned_from"),
            "inherited_from": "tools/render_performer.py (E09 previz), verbatim",
        },
        "keypoint_names": list(aapose.KEYPOINT_NAMES),
        "landmark_sites": list(aapose.LANDMARK_SITES),
        "hand_sites": {k: list(v) for k, v in aapose.HAND_SITES.items()},
        "body": body_px,
        "left_hand": lhand_px,
        "right_hand": rhand_px,
        "diagnostics": {
            "body_span_px_per_frame": span_stats(body_px),
            "left_hand_span_px_per_frame": span_stats(lhand_px),
            "right_hand_span_px_per_frame": span_stats(rhand_px),
            "ankle_to_toe_over_hip_to_ankle": {
                "min": min(ratios), "median": sorted(ratios)[len(ratios) // 2],
                "max": max(ratios),
                "note": ("the quantity that caught the superseded GLB-tail route, where it "
                         "read 0.33-0.55; a foot is a small fraction of a leg"),
            },
        },
        "gates": {
            "MAP": {"verdict": "PASS", "detail": "aapose.require_rig_map"},
            "FRONT": {"verdict": "PASS",
                      "detail": f"{n_frames * 62} points, all in front of the camera"},
            "FRAMING": framing_gate,
            "MOTION": gate_mot,
        },
        "elapsed_s": time.time() - started,
    }

    path = os.path.join(out, "keypoints.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print("PROJECT_POSE_OK " + json.dumps({
        "out": path, "frames": n_frames, "resolution": [a.width, a.height],
        "radius": round(radius, 5),
        "body_span_px": payload["diagnostics"]["body_span_px_per_frame"],
        "hand_span_px": payload["diagnostics"]["left_hand_span_px_per_frame"],
        "foot_leg_ratio": payload["diagnostics"]["ankle_to_toe_over_hip_to_ankle"],
        "motion": gate_mot["verdict"]}))
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
        print("PROJECT_POSE_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
