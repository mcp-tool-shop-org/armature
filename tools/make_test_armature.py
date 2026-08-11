"""Generate the wire-armature test subject — the instrument, not a character.

    blender -b -P tools/make_test_armature.py -- --thickness 0.030 --out <path.glb>

WHY THIS EXISTS. Every subject this route has measured so far is a sculpted asset whose
joint positions we can only infer from its silhouette. That limits a control experiment to
"does it look held". This subject is built from parameters, so **the true 3D position of
every joint is known before a single frame is rendered** — which means a control experiment
can ask *how far did the elbow move*, in pixels, against ground truth. That is a different
class of question and it is why this file is a tool rather than a downloaded mesh.

Three properties it has that an authored character cannot:

  1. **License-clean by construction.** We authored the geometry; no model card, no grant, no
     row in the licence map. Nothing to verify because nothing was obtained.
  2. **A recipe that reproduces its output.** Same args in, byte-identical mesh out — no
     randomness anywhere, vertices emitted in a deterministic order. The GLB IS the recipe's
     output rather than an artifact whose provenance we assert.
  3. **Thickness is a parameter, and that is the point.** Thin members are the hardest case
     for a video model, and this repo has already recorded that a proxy fails precisely where
     the subject is thin. A single wire figure would confound "the thesis failed" with "these
     limbs are three pixels wide". Generating a thickness bracket separates them: if control
     holds at 0.045 and fails at 0.015, the finding is about width, not about control.

⚠ WHAT THIS SUBJECT IS NOT. It carries no identity. There is no face, no costume, nothing a
reference image could preserve or lose. It can measure whether **structure** is obeyed and it
can say nothing whatever about whether a character survived — that question needs the
blackguard, and the Director has ruled on that subject separately. Do not read an identity
result off this mesh.

Scale matches the blackguard (~1.0 unit tall) so framing and camera fit are comparable
between subjects without re-deriving anything.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import posearc  # noqa: E402
from armature_core.errors import SpecError  # noqa: E402

# Joint layout in metres, origin at the feet, +Z up, facing -Y. A T-pose: the bind pose,
# and the reason a rig reads as a rig at a glance.
JOINTS = {
    "head_top":    (0.000, 0.0, 1.000),
    "head_base":   (0.000, 0.0, 0.880),
    "neck":        (0.000, 0.0, 0.840),
    "shoulder_l":  (-0.090, 0.0, 0.820),
    "shoulder_r":  (0.090, 0.0, 0.820),
    "elbow_l":     (-0.250, 0.0, 0.820),
    "elbow_r":     (0.250, 0.0, 0.820),
    "wrist_l":     (-0.400, 0.0, 0.820),
    "wrist_r":     (0.400, 0.0, 0.820),
    "chest":       (0.000, 0.0, 0.760),
    "pelvis":      (0.000, 0.0, 0.560),
    "hip_l":       (-0.075, 0.0, 0.545),
    "hip_r":       (0.075, 0.0, 0.545),
    "knee_l":      (-0.080, 0.0, 0.300),
    "knee_r":      (0.080, 0.0, 0.300),
    "ankle_l":     (-0.085, 0.0, 0.045),
    "ankle_r":     (0.085, 0.0, 0.045),
}

# Ordered so the mesh is emitted deterministically.
BONES = [
    ("neck", "head_base"), ("head_base", "head_top"),
    ("neck", "chest"), ("chest", "pelvis"),
    ("neck", "shoulder_l"), ("neck", "shoulder_r"),
    ("shoulder_l", "elbow_l"), ("elbow_l", "wrist_l"),
    ("shoulder_r", "elbow_r"), ("elbow_r", "wrist_r"),
    ("pelvis", "hip_l"), ("pelvis", "hip_r"),
    ("hip_l", "knee_l"), ("knee_l", "ankle_l"),
    ("hip_r", "knee_r"), ("knee_r", "ankle_r"),
]

# Joints that get a ball. Wrists and head_top are ends, not articulations.
BALLS = ["neck", "chest", "pelvis", "shoulder_l", "shoulder_r", "elbow_l", "elbow_r",
         "hip_l", "hip_r", "knee_l", "knee_r", "ankle_l", "ankle_r", "head_base"]


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_limb(name, a, b, radius, segments):
    """A capsule-less cylinder between two points. Deterministic: no ops that sample state."""
    va, vb = Vector(a), Vector(b)
    d = vb - va
    length = d.length
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius, depth=length,
                                        location=(va + d / 2.0))
    ob = bpy.context.active_object
    ob.name = name
    # Align +Z to the bone direction. quaternion path avoids euler-order ambiguity.
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    return ob


def add_ball(name, p, radius, segments):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(segments // 2, 4),
                                         radius=radius, location=p)
    ob = bpy.context.active_object
    ob.name = name
    return ob


def _action_fcurves(action):
    """Every F-curve in an action, across both Action APIs.

    Blender 5.2 API note, measured on this rig 2026-08-10 rather than inherited: slotted
    actions replaced the flat `Action.fcurves` list with `layers -> strips -> channelbags
    -> fcurves`, and reading the old attribute raises `AttributeError`. Both shapes are
    walked because the attribute's absence is the only reliable discriminator — the version
    number is not, since the slotted system landed across a range of point releases.
    """
    flat = getattr(action, "fcurves", None)
    if flat is not None:
        return list(flat)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cbag in getattr(strip, "channelbags", []):
                out.extend(cbag.fcurves)
    return out


def _join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in parts:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob


def build(thickness, joint_scale, segments, arc=None, frames=33, start_deg=0.0, end_deg=90.0):
    """Build the figure. With `arc`, the moving group becomes its own keyframed object.

    Without an arc this is E01's subject exactly: every part joined into one mesh. With one,
    the parts the arc moves are joined separately, their origin is put **at the pivot joint**
    (so a rotation about the object's own origin is a rotation about the shoulder), and the
    rotation is keyed once per frame.

    Keying every frame rather than just the endpoints is deliberate. glTF stores keyframe
    times in seconds and Blender resamples on import; two keys plus an interpolation curve
    would round-trip as a curve we would then have to trust. 33 explicit keys make the
    authored angle and the imported angle the same number at every frame, and
    `posearc.joints_at_frame` can be compared against the render directly.
    """
    clear_scene()
    limbs, balls = {}, {}
    for a, b in BONES:
        n = f"bone_{a}__{b}"
        limbs[n] = add_limb(n, JOINTS[a], JOINTS[b], thickness, segments)
    for j in BALLS:
        n = f"joint_{j}"
        balls[n] = add_ball(n, JOINTS[j], thickness * joint_scale, segments)
    all_parts = {**limbs, **balls}

    if arc is None:
        fig = _join(list(all_parts.values()), "armature_test_figure")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.shade_flat()
        return fig, None

    missing = [n for n in arc["moving_parts"] if n not in all_parts]
    if missing:
        raise SpecError(f"pose arc names parts that this figure has none of: {missing}")

    moving = [all_parts[n] for n in arc["moving_parts"]]
    static = [ob for n, ob in all_parts.items() if n not in set(arc["moving_parts"])]

    fig = _join(static, "armature_test_figure")
    arm = _join(moving, f"armature_moving_{arc['pivot']}")

    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm

    # Bake the joined group's REST rotation into its mesh, leaving the object rotation
    # identity and the world geometry untouched.
    #
    # MEASURED 2026-08-10, and this is the subtlest failure in the build. `add_limb` aims
    # each cylinder by setting the OBJECT's `rotation_quaternion` to a track-quat, and
    # `join` hands the active object's transform to the joined result — so the moving group
    # arrives carrying a non-identity rotation that is load-bearing geometry, not a pose.
    # Assigning `rotation_euler` for the arc then discards it, and the arm stands bolt
    # upright before the performance starts: measured, the arc ran from vertical to
    # horizontal-pointing-backwards while every angle in the F-curve read exactly 0°, -45°,
    # -90° as authored. The keys were right and the pose they were applied to was not.
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Put the moving group's origin ON the pivot joint. Without this the object rotates
    # about wherever `join` left its origin — plausible-looking motion about the wrong
    # point, with the shoulder swinging and the whole arm sliding off the body.
    pivot = JOINTS[arc["pivot"]]
    bpy.context.scene.cursor.location = Vector(pivot)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")

    arm.rotation_mode = "XYZ"
    for i in range(frames):
        theta = posearc.angle_at_frame(i, frames, start_deg, end_deg)
        arm.rotation_euler = (0.0, math.radians(arc["sign"] * theta), 0.0)
        arm.keyframe_insert(data_path="rotation_euler", frame=1 + i)

    # Linear interpolation between keys. With a key on every frame the interpolation is
    # never consulted at an integer frame, but a constant/bezier default would still change
    # what a glTF consumer sampling between frames would see, and the recipe should not
    # depend on a default we did not choose.
    if arm.animation_data and arm.animation_data.action:
        for fc in _action_fcurves(arm.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

    # Put the object back on the bind pose. MEASURED 2026-08-10, and it is not cosmetic:
    # the loop above leaves `rotation_euler` holding the LAST keyed value (-90°), and the
    # glTF exporter composes that residual node transform WITH the animation track. The
    # exported arc then ran 90°->180° instead of 0°->90° — an arm that starts overhead and
    # ends pointing sideways. Every frame is well-formed, the action is present with 33
    # keys over frames 1-33 at the right fps, and nothing anywhere reports it; only
    # comparing the geometry against the authored ground truth shows it
    # (tests/blender/check_pose_arc_roundtrip.py, which is what caught it).
    arm.rotation_euler = (0.0, 0.0, 0.0)

    # Shade flat: this subject exists to be read as geometry, and smooth shading would
    # invent gradients in the normal channel that the geometry does not have.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.shade_flat()
    return fig, arm


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--thickness", type=float, default=0.030,
                    help="limb radius in metres; the bracket variable")
    ap.add_argument("--joint-scale", type=float, default=1.55,
                    help="ball radius as a multiple of limb radius")
    ap.add_argument("--segments", type=int, default=16)
    # NOTE the `--key=value` form for these: argparse eats leading minus signs, so a
    # negative arc angle must be written --arc-start-deg=-30, never --arc-start-deg -30.
    ap.add_argument("--pose-arc", default=None,
                    help=f"authored performance; one of {sorted(posearc.POSE_ARCS)}. "
                         f"Omit for the static bind pose (E01/E02's subject).")
    ap.add_argument("--frames", type=int, default=33,
                    help="frames the arc spans; must match the shot spec's frame count")
    ap.add_argument("--fps", type=int, default=16,
                    help="MUST match the shot spec's fps: glTF stores key times in seconds")
    ap.add_argument("--arc-start-deg", type=float, default=0.0)
    ap.add_argument("--arc-end-deg", type=float, default=90.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    arc = posearc.resolve_arc(args.pose_arc) if args.pose_arc else None
    readout = None
    if arc is not None:
        # Raises on a zero-span arc or an uncrossable readout BEFORE any geometry is built.
        readout = posearc.arc_readout(arc, args.frames, args.arc_start_deg, args.arc_end_deg)

    fig, arm = build(args.thickness, args.joint_scale, args.segments, arc=arc,
                     frames=args.frames, start_deg=args.arc_start_deg,
                     end_deg=args.arc_end_deg)

    # The frame rate and range are properties of the EXPORT, not of the scene we happened
    # to build in: glTF writes key times in seconds, so an action authored at 33 keys and
    # exported at the wrong fps arrives at the renderer spanning the wrong number of frames.
    scene = bpy.context.scene
    scene.render.fps = args.fps
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = args.frames if arc is not None else 1
    scene.frame_set(1)
    # Settle the depsgraph before anything reads a matrix: `frame_set` schedules the
    # evaluation, and `matrix_world`/`bound_box` read before it settles return the previous
    # frame's values — which is how `dimensions_xyz` came to describe a raised arm.
    bpy.context.view_layer.update()

    objs = [o for o in (fig, arm) if o is not None]
    # Over BOTH groups, not just the static one. With an arc, `fig.dimensions` describes a
    # figure missing an arm — a number whose name says "the subject" while measuring a
    # part of it, which is the kind of quantity this repo has been burned by.
    corners = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    dims = tuple(
        round(max(c[i] for c in corners) - min(c[i] for c in corners), 6) for i in range(3)
    )
    verts = sum(len(o.data.vertices) for o in objs)
    tris = sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)

    bpy.ops.export_scene.gltf(filepath=args.out, export_format="GLB",
                              use_selection=False, export_yup=True,
                              export_animations=arc is not None,
                              export_frame_range=arc is not None)

    # Ground truth beside the mesh. This is the whole reason the subject is procedural:
    # a later experiment can project these and measure displacement rather than eyeball it.
    side = {
        "generator": os.path.basename(__file__),
        "params": {"thickness": args.thickness, "joint_scale": args.joint_scale,
                   "segments": args.segments, "fps": args.fps},
        "blender": bpy.app.version_string,
        "dimensions_xyz": dims,
        "vertices": verts,
        "triangles": tris,
        "aspect_longest_over_shortest": round(max(dims) / min(dims), 4),
        "joints_world_zup": {k: list(v) for k, v in JOINTS.items()},
        "bones": [list(b) for b in BONES],
        "note": ("Joint coordinates are Z-up world metres as authored. glTF export is Y-up; "
                 "a consumer must convert. NO IDENTITY: this subject cannot answer whether a "
                 "character survived, only whether structure was obeyed."),
    }

    if arc is not None:
        # THE GROUND TRUTH. Every joint's true world position at every frame, computed from
        # the authored angle rather than read back from the mesh — so a later measurement
        # can ask "where was the wrist supposed to be on frame 20" and compare, instead of
        # inferring it from the silhouette it is trying to grade.
        frames = []
        for i in range(args.frames):
            theta, joints = posearc.joints_at_frame(
                JOINTS, arc, i, args.frames, args.arc_start_deg, args.arc_end_deg
            )
            frames.append({
                "frame": i,
                "scene_frame": 1 + i,
                "angle_deg": round(theta, 9),
                "joints_world_zup": {k: [round(v, 9) for v in p] for k, p in joints.items()},
            })
        side["pose_arc"] = {
            "name": args.pose_arc,
            "pivot": arc["pivot"],
            "axis": arc["axis"],
            "sign": arc["sign"],
            "moving_joints": list(arc["moving_joints"]),
            "moving_parts": list(arc["moving_parts"]),
            "description": arc["description"],
            "start_deg": args.arc_start_deg,
            "end_deg": args.arc_end_deg,
            "frames": args.frames,
            "fps": args.fps,
            "moving_object": arm.name if arm is not None else None,
            "readout": readout,
        }
        side["frames"] = frames
    with open(os.path.splitext(args.out)[0] + ".joints.json", "w", encoding="utf-8") as fh:
        json.dump(side, fh, indent=2)

    print(f"[make_test_armature] {args.out}")
    print(f"  thickness={args.thickness}  dims={dims}  verts={verts}  tris={tris}")
    print(f"  aspect(longest/shortest)={side['aspect_longest_over_shortest']}")
    if arc is not None:
        r = readout
        wrist0 = side["frames"][0]["joints_world_zup"]["wrist_r"]
        wristN = side["frames"][-1]["joints_world_zup"]["wrist_r"]
        print(f"  pose_arc={args.pose_arc}  {args.arc_start_deg}deg -> {args.arc_end_deg}deg "
              f"over {args.frames} frames @ {args.fps}fps")
        print(f"  moving object={arm.name}  pivot={arc['pivot']}")
        print(f"  readout {r['readout_deg']}deg crosses at frame "
              f"{r['crossing_frame_exact']} (integer={r['lands_on_an_integer_frame']})")
        print(f"  wrist_r f000={[round(v, 4) for v in wrist0]} -> "
              f"f{args.frames - 1:03d}={[round(v, 4) for v in wristN]}")


if __name__ == "__main__":
    main()
