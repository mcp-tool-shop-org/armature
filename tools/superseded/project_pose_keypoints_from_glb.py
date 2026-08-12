#!/usr/bin/env python
"""SUPERSEDED 2026-08-12 — reading keypoints off the exported GLB's BONES loses the toes.

Kept runnable, with the measurement, because "import the GLB and read the bone heads and
tails" is the obvious approach and a session that did not know this would re-derive it.

**What was measured.** Eighteen of the twenty AAPose keypoints land correctly this way; the
two that do not are `LToe` and `RToe`, which come off the ankle bones' TAILS. glTF has no
concept of a bone tail — it stores joints as nodes with transforms — so Blender's importer
*synthesises* a tail for every leaf bone. The ankle bones are leaves. The synthesised tails
are neither the right length nor the right direction:

    rig manifest, measured   ankle.L -> toe_L  0.10476     ankle.R -> toe_R  0.09208
    (knee -> ankle, for scale)                 0.31379                       0.30812

so a toe sits about a sixth of the leg beyond the ankle. Projected from this tool's bone
tails at 1920x1080 the ankle-to-toe span came out 114-190 px against a hip-to-ankle span of
328-348 px — roughly a third of the leg, two to three times too far — and the overlay sheet
`outputs/E08/sheets/E08-overlay-feet.png` shows both toe markers hanging in empty air on the
floor, clear of the rendered feet, at frames 0, 32 and 64.

**Every gate in this tool passed on that output.** MAP resolved, FRONT resolved, FRAMING
solved, MOTION counted 65 distinct poses, and downstream CANVAS, INK and COUNT passed too.
The only instrument that saw it was the body itself — the pose sticks composited onto the
previz render of the same performance, which is why that overlay is now built before any
credit is spent rather than after.

**The replacement:** `tools/project_pose_keypoints.py` places landmarks with
`armature_core.lift_solve.fk_sites` from the rig manifest's MEASURED rest landmarks and the
motion record — the same kinematics the solver inverts, already under test. `toe_L` and
`toe_R` are measured landmarks there ("furthest foot vertex in the measured facing
direction, at ground"), so nothing is synthesised. It needs no Blender at all.

--------------------------------------------------------------------------------
Original docstring follows.

project_pose_keypoints — the rig's AAPose-20 keypoints, per frame, in pixels.

    blender -b -P tools\\project_pose_keypoints.py -- --glb=<performer_dance.glb>
            --manifest=<rig_manifest.json> --out=<dir> [--width=832 --height=480 --fps=16]

Stage 1 of the pose-stick commission (E08). This is the ONLY half that needs Blender: it
imports the performance, reads where every registered bone actually is at every frame, and
pushes those points through the shot camera. It draws nothing. `tools/render_pose_sticks.py`
takes the JSON this writes and draws the convention.

**Why the two halves are separate tools** (DECOMPOSE_BY_SECRETS). What changes here is scene
assembly and the camera; what changes there is a drawing convention pinned to somebody else's
source file. They also have incompatible dependencies — the convention is defined in `cv2`
calls and Blender's bundled Python has no cv2 — so joining them would mean reimplementing
`cv2.ellipse2Poly` by hand, which is precisely the "we re-implemented it ourselves" move the
licence map's procedure note 7 warns about. Split, each half is testable in its own runtime.

**The camera is the E09 previz camera, unchanged.** Azimuth 225 / elevation 6 / lens 50 /
height-frac 0.70 are `render_performer`'s banked constants, reused verbatim so the stick
frames and the E09 previz frames are the same composition at two resolutions and the Gate 0
sheet compares panels rather than compositions. Figure size is E10's variable (E09 closing
ruling, open items); holding it fixed here is the one-variable discipline, not a preference.

Prints `PROJECT_POSE_OK`. A crashed `blender -b -P` exits 0, so that line is the contract.

--------------------------------------------------------------------------------
The gates — all raise, in-process, before the JSON exists

* **the fps andon** — `blender_scene.import_glb(expected_fps=)`. glTF key times are SECONDS;
  importing at Blender's default 24 lands a 16 fps action on the wrong frames and every other
  check still passes.
* **Gate MAP** — `aapose.require_rig_map`. A keypoint whose bone is missing would be written
  as a zero and drawn as a limb running to the corner of the frame, erroring nowhere.
* **Gate FRONT** — every keypoint of every frame projects in FRONT of the camera. A point
  behind the camera has no screen position at all; `framing.project` returns `ok=False` and a
  caller that merely skipped it would emit a frame with a limb silently absent.
* **Gate FRAMING** — the solved composition keeps the whole performance inside the frame. A
  clipped driving signal drives the part it can see and reports nothing.
* **Gate MOTION** — the projected keypoints are not identical at every frame. A pose video
  that does not move would drive a still, and the frame count, the file count and every
  legality check pass on 65 copies of one pose.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing a JSON under
`outputs/`. Compensator: delete the directory; owner: the executor session. The GLB and the
manifest are opened read-only.
"""

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from armature_core import aapose, blender_scene, framing, sitelist  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E08.1"

#: `render_performer`'s banked composition, verbatim. See the module docstring.
AZIMUTH_DEG = 225.0
ELEVATION_DEG = 6.0
LENS_MM = 50.0
SENSOR_MM = 36.0
HEIGHT_FRAC = 0.70
END_X_FRAC = 0.62
TARGET_Y_FRAC = 0.52

#: Rendered ground truth carries no uncertainty: we know where every joint is, including the
#: ones the body occludes. Emitted at 1.0 so the convention's `threshold` never drops one.
#: The consequence is recorded rather than tuned: a real detector would report low confidence
#: on an occluded joint and Wan would see it dropped, where it sees ours drawn.
GROUND_TRUTH_CONFIDENCE = 1.0


class ProjectGate(GateFailure):
    gate = "PROJECT"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--frames", type=int, default=0,
                    help="0 = every frame the action carries")
    ap.add_argument("--camera-json", default=None,
                    help="reuse a PINNED camera instead of solving one: any JSON carrying "
                         "camera.target and camera.radius (a render_provenance.json or a "
                         "prior keypoints.json). Two uses: overlaying these keypoints on a "
                         "render made with that camera, and locking one composition across "
                         "a series of shots")
    return ap.parse_args(argv)


#: The angles a pinned camera record must agree with before it may be used here.
PINNED_CAMERA_EXPECT = {
    "azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG,
    "lens_mm": LENS_MM, "sensor_mm": SENSOR_MM,
}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def bone_frames(arm_obj, scene, n_frames):
    """Per frame: world head, world tail and world axes of every registered bone.

    World space, not armature space — the glTF round trip may put the armature object's
    Y-up conversion anywhere, and what has to survive is where the body is when the camera
    looks at it. Same reasoning as `lift_solve.posed_heads`, extended to tails and axes
    because toes come off tails and the mitten hands need the wrist's own frame.
    """
    out = []
    for i in range(n_frames):
        blender_scene.set_scene_frame(scene, i)
        M = arm_obj.matrix_world
        rec = {}
        for name in sitelist.ALL_NAMES:
            pb = arm_obj.pose.bones[name]
            W = M @ pb.matrix
            head = W.to_translation()
            R = W.to_3x3()
            length = pb.length
            rec[name] = {
                "head": [float(v) for v in head],
                "tail": [float(v) for v in (head + R @ Vector((0.0, length, 0.0)))],
                "axis_y": [float(v) for v in (R @ Vector((0.0, 1.0, 0.0))).normalized()],
                "axis_x": [float(v) for v in (R @ Vector((1.0, 0.0, 0.0))).normalized()],
                "length": float(length),
            }
        out.append(rec)
    return out


def body_cloud(rec, lo, hi):
    """Points that must stay in frame for one frame — `render_performer.body_cloud`'s shape.

    Lifted in form rather than re-derived so the two tools frame the same performance the
    same way. Landmarks under-report the SILHOUETTE (this character's torso is wider than
    his shoulder joints), so the rest bbox's own half-extents are hung on the hips as a
    bound. `hips` head sits on the `crotch` landmark, which is the point the other tool
    aliases to the same name.
    """
    pts = []
    for b in rec.values():
        pts.append(tuple(b["head"]))
        pts.append(tuple(b["tail"]))
    hx, hy = 0.5 * (hi[0] - lo[0]), 0.5 * (hi[1] - lo[1])
    hips = tuple(rec["hips"]["head"])
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            pts.append((hips[0] + sx * hx, hips[1] + sy * hy, hips[2]))
    return pts


def aapose_points(rec):
    """The 20 AAPose world points for one frame, in convention order."""
    return [tuple(rec[bone][end]) for bone, end in aapose.RIG_SITES]


def hand_points(rec, side):
    """The 21 synthesised mitten-hand world points for one frame and one side."""
    import numpy as np

    bone = aapose.HAND_BONES[side]
    b = rec[bone]
    return aapose.mitten_hand(
        wrist=np.asarray(b["head"], dtype=np.float64),
        palm_dir=np.asarray(b["axis_y"], dtype=np.float64),
        palm_side=np.asarray(b["axis_x"], dtype=np.float64),
        hand_length=b["length"],
    )


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
    """Gate MOTION · ANDON — the pose sequence is a performance, not 65 copies of a pose.

    The quantity is the rounded projected body keypoints, because that is what actually
    reaches the model: a rig that moves entirely along the camera axis would move in world
    space and not on screen, and the model would be driven by a still either way. Raising on
    ALL frames identical rather than on any adjacent pair identical is deliberate — a slow
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
            f"The frame count, the file count and every legality check pass on this. Check "
            f"that the GLB carries an action and that the scene rate matches the export",
            ev)
    ev["verdict"] = f"{len(sigs)} distinct projected poses over {n_frames} frames"
    return ev


def main():
    started = time.time()
    a = parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    aapose.require_rig_map(sitelist.ALL_NAMES)      # Gate MAP, before anything is loaded
    sitelist.validate()

    with open(a.manifest, encoding="utf-8") as fh:
        rig = json.load(fh)
    lo, hi = rig["bbox"]["lo"], rig["bbox"]["hi"]

    # ---- fps FIRST, on an empty scene, before the import. glTF key times are seconds.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, a.fps)
    meshes, arms, info = blender_scene.import_glb(a.glb, expected_fps=a.fps)
    if len(arms) != 1:
        raise ProjectGate(
            f"expected exactly one armature in {a.glb}, found {len(arms)}; a pose read off "
            f"the wrong skeleton is a pose that looks perfectly well-formed",
            {"armatures": [o.name for o in arms]})
    arm_obj = arms[0]

    missing = [n for n in sitelist.ALL_NAMES if n not in arm_obj.pose.bones]
    if missing:
        raise ProjectGate(
            f"the imported armature is missing registered bone(s) {missing}", {})

    n_frames = a.frames or int(round(scene.frame_end - scene.frame_start + 1))
    if a.frames:
        n_frames = a.frames
    else:
        # The action's own extent, in scene frames, at the rate pinned above.
        spans = [act.frame_range for act in bpy.data.actions]
        if not spans:
            raise ProjectGate("the GLB carries no action; there is no performance to project",
                              {"asset": a.glb})
        last = max(int(round(s[1])) for s in spans)
        n_frames = last                      # scene frames are 1-based; frame N is index N-1
    scene.frame_start, scene.frame_end = 1, n_frames

    frames = bone_frames(arm_obj, scene, n_frames)

    # ---- the camera: solved over the whole performance, or pinned to a prior record
    clouds = [body_cloud(rec, lo, hi) for rec in frames]
    if a.camera_json:
        target, radius = framing.load_pinned_camera(a.camera_json, PINNED_CAMERA_EXPECT)
        sol = {"target": list(target), "radius": radius, "in_frame": None,
               "achieved": None, "pinned_from": os.path.abspath(a.camera_json)}
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
    for i, rec in enumerate(frames):
        body_px.append(to_pixels(aapose_points(rec), target, radius, a.width, a.height,
                                 "body", i))
        lhand_px.append(to_pixels(hand_points(rec, "left"), target, radius, a.width,
                                  a.height, "left_hand", i))
        rhand_px.append(to_pixels(hand_points(rec, "right"), target, radius, a.width,
                                  a.height, "right_hand", i))

    gate_mot = gate_motion(body_px, n_frames)

    # ---- diagnostics (they gate nothing): how big the figure and the hands actually are
    def span(seq):
        xs = [kp[0] for f in seq for kp in f]
        ys = [kp[1] for f in seq for kp in f]
        return {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)],
                "w": max(xs) - min(xs), "h": max(ys) - min(ys)}

    def per_frame_span(seq):
        out_ = []
        for f in seq:
            xs = [kp[0] for kp in f]
            ys = [kp[1] for kp in f]
            out_.append(max(max(xs) - min(xs), max(ys) - min(ys)))
        return {"min": min(out_), "median": sorted(out_)[len(out_) // 2], "max": max(out_)}

    payload = {
        "tool": "project_pose_keypoints",
        "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "convention": dict(aapose.SOURCE),
        "source": {"glb": os.path.abspath(a.glb), "sha256": _sha256(a.glb),
                   "manifest": os.path.abspath(a.manifest),
                   "manifest_sha256": _sha256(a.manifest)},
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
        "import_info": info,
        "keypoint_names": list(aapose.KEYPOINT_NAMES),
        "rig_sites": [list(s) for s in aapose.RIG_SITES],
        "body": body_px,
        "left_hand": lhand_px,
        "right_hand": rhand_px,
        "diagnostics": {
            "body_span_px_over_all_frames": span(body_px),
            "body_span_px_per_frame": per_frame_span(body_px),
            "left_hand_span_px_per_frame": per_frame_span(lhand_px),
            "right_hand_span_px_per_frame": per_frame_span(rhand_px),
        },
        "gates": {
            "fps_ordering": {"verdict": "PASS", "detail": "import_glb(expected_fps)"},
            "MAP": {"verdict": "PASS", "detail": "aapose.require_rig_map"},
            "FRONT": {"verdict": "PASS",
                      "detail": f"{n_frames * (20 + 42)} points, all in front"},
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
