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


def build(thickness, joint_scale, segments):
    clear_scene()
    parts = []
    for a, b in BONES:
        parts.append(add_limb(f"bone_{a}__{b}", JOINTS[a], JOINTS[b], thickness, segments))
    for j in BALLS:
        parts.append(add_ball(f"joint_{j}", JOINTS[j], thickness * joint_scale, segments))

    for ob in parts:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    fig = bpy.context.active_object
    fig.name = "armature_test_figure"

    # Shade flat: this subject exists to be read as geometry, and smooth shading would
    # invent gradients in the normal channel that the geometry does not have.
    bpy.ops.object.shade_flat()
    return fig


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--thickness", type=float, default=0.030,
                    help="limb radius in metres; the bracket variable")
    ap.add_argument("--joint-scale", type=float, default=1.55,
                    help="ball radius as a multiple of limb radius")
    ap.add_argument("--segments", type=int, default=16)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    fig = build(args.thickness, args.joint_scale, args.segments)
    dims = tuple(round(v, 6) for v in fig.dimensions)
    verts = len(fig.data.vertices)
    tris = sum(len(p.vertices) - 2 for p in fig.data.polygons)

    bpy.ops.export_scene.gltf(filepath=args.out, export_format="GLB",
                              use_selection=False, export_yup=True)

    # Ground truth beside the mesh. This is the whole reason the subject is procedural:
    # a later experiment can project these and measure displacement rather than eyeball it.
    side = {
        "generator": os.path.basename(__file__),
        "params": {"thickness": args.thickness, "joint_scale": args.joint_scale,
                   "segments": args.segments},
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
    with open(os.path.splitext(args.out)[0] + ".joints.json", "w", encoding="utf-8") as fh:
        json.dump(side, fh, indent=2)

    print(f"[make_test_armature] {args.out}")
    print(f"  thickness={args.thickness}  dims={dims}  verts={verts}  tris={tris}")
    print(f"  aspect(longest/shortest)={side['aspect_longest_over_shortest']}")


if __name__ == "__main__":
    main()
