"""The arm (d) comparison sheet — a SKINNED figure, judged beside the mesh it replaced.

``make_parts_sheet`` cannot serve here and its refusal was correct rather than a nuisance: it
compares **part object transforms**, which is how a rigid-parts rig moves. A skinned figure
has one object that never moves; the motion lives in evaluated vertex positions. Pointed at a
skinned GLB it reports "the parts are identical at frame 1 and frame 33" and declines to draw.
Rather than loosen that check, this tool makes the same assertion against the thing that
actually moves here.

Inset cameras are aimed from the **posed bone positions read out of the armature**, not from
guessed fractions of the figure's height. Arm (d)'s first comparison sheet framed the "mitten
hand" panel on a forearm and a shin, which is a sheet that cannot answer the question it was
built to ask.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_character as rc                                            # noqa: E402
from armature_core.errors import ArmatureError                        # noqa: E402
from make_parts_sheet import light_the_scene, ortho_camera, shoot     # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True, help="the skinned, animated GLB")
    p.add_argument("--reference", required=True, help="the ORIGINAL textured GLB")
    p.add_argument("--out", required=True)
    p.add_argument("--title", default="E07 arm (d) — retopologised, baked, bone-heat bound")
    return vars(p.parse_args(argv))


def evaluated(ob, depsgraph):
    ev = ob.evaluated_get(depsgraph)
    me = ev.to_mesh()
    v = np.array([list(ob.matrix_world @ x.co) for x in me.vertices])
    ev.to_mesh_clear()
    return v


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    os.makedirs(out_dir, exist_ok=True)
    panel_dir = os.path.join(out_dir, "panels")
    os.makedirs(panel_dir, exist_ok=True)

    scene = rc.fresh_scene(16)
    bpy.ops.import_scene.gltf(filepath=args["glb"])
    # Pick the mesh that is actually SKINNED, not the first mesh in the file. The exported
    # GLB also contains a stray `Icosphere` with no vertex groups and no modifier; taking
    # index 0 picked that, and it of course never moves -- this tool's own liveness check
    # then reported "the arc did not survive the round trip" about an object that was never
    # in the arc. Identify by the property that matters.
    skinned = [o for o in bpy.data.objects
               if o.type == "MESH" and o.vertex_groups
               and any(m.type == "ARMATURE" for m in o.modifiers)]
    if len(skinned) != 1:
        raise ArmatureError(
            f"expected exactly one skinned mesh in {args['glb']}, found {len(skinned)}: "
            f"{[o.name for o in skinned]} (all meshes: "
            f"{[o.name for o in bpy.data.objects if o.type == 'MESH']})")
    mesh = skinned[0]
    arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
    stray = [o.name for o in bpy.data.objects if o.type == "MESH" and o is not mesh]
    for name in stray:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    dg = bpy.context.evaluated_depsgraph_get()
    scene.frame_set(1)
    dg.update()
    at_rest = evaluated(mesh, dg)
    scene.frame_set(33)
    dg.update()
    at_end = evaluated(mesh, dg)
    moved = float(np.abs(at_end - at_rest).max())
    lo, hi = at_rest.min(0), at_rest.max(0)
    diagonal = float(np.linalg.norm(hi - lo))
    if moved <= 1e-4 * diagonal:
        raise ArmatureError(
            f"{args['glb']}: the evaluated mesh is identical at frame 1 and frame 33 "
            f"(max {moved:.3e}). The authored arc did not survive the round trip, and a "
            f"sheet built from this would read as 'this route does not move'")

    # Inset targets read from the POSED armature, so each crop lands on its own joint.
    scene.frame_set(33)
    dg.update()
    bones = {b.name: (arm.matrix_world @ b.head) for b in arm.pose.bones}
    height = hi[2] - lo[2]
    insets = [("shoulder", bones["shoulder.L"], height * 0.20, 0.0),
              ("elbow", bones["elbow.L"], height * 0.16, 0.0),
              ("wrist", bones["wrist.L"], height * 0.16, 0.0),
              ("hip", bones["hip.L"], height * 0.20, 0.0)]

    light_the_scene(scene)
    centre = Vector((0.5 * (lo[0] + hi[0]), 0.0, lo[2] + 0.5 * height))
    rows = []

    figure = []
    for frame in (1, 17, 33):
        scene.frame_set(frame)
        ortho_camera(scene, f"cam_f{frame}", centre, height * 1.10, (700, 1120))
        figure.append({"body": shoot(scene, os.path.join(panel_dir, f"figure_{frame}.png")),
                       "label": "frame 1 — rest" if frame == 1 else f"frame {frame}"})
    rows.append({"title": "The figure through the arc", "panels": figure})

    scene.frame_set(33)
    close = []
    for label, target, oscale, azim in insets:
        ortho_camera(scene, f"cam_{label}", Vector(target), oscale, (700, 700), azim)
        close.append({"body": shoot(scene, os.path.join(panel_dir, f"{label}.png")),
                      "label": label})
    rows.append({"title": "At 1:1, frame 33 — the joints under articulation", "panels": close})

    # ---- texture fidelity: the mesh that was replaced, and the one that replaced it -------
    scene.frame_set(1)
    for ob in list(bpy.data.objects):
        if ob.type == "ARMATURE":
            continue
    bpy.ops.import_scene.gltf(filepath=args["reference"])
    ref = [o for o in bpy.data.objects if o.type == "MESH" and o is not mesh][0]
    ref.hide_render = True
    fidelity = []
    for label, shown in (("before — original mesh, 299,956 tris, source atlas", ref),
                         ("after — retopologised, 4096 atlas baked old to new", mesh)):
        ref.hide_render = shown is not ref
        mesh.hide_render = shown is not mesh
        ortho_camera(scene, f"cam_fid_{shown.name}", centre, height * 1.10, (700, 1120))
        fidelity.append({"body": shoot(scene, os.path.join(
            panel_dir, f"fidelity_{'before' if shown is ref else 'after'}.png")),
            "label": label})
        for label2, target, oscale, _ in insets[:1]:
            ortho_camera(scene, f"cam_fid_{shown.name}_{label2}", Vector(target),
                         height * 0.22, (700, 700))
            fidelity.append({"body": shoot(scene, os.path.join(
                panel_dir,
                f"fidelity_{'before' if shown is ref else 'after'}_{label2}.png")),
                "label": f"{label2}, same camera"})
    ref.hide_render = False
    mesh.hide_render = False
    rows.append({"title": "Texture fidelity — at rest, same camera, nothing else changed",
                 "panels": fidelity})

    spec = {"title": args["title"],
            "subtitle": "one skinned mesh, 39,707 verts, bone-heat weights · the arc is "
                        "E03's: the character's LEFT arm, 0°→90° about +Y, 33 keys at 16 fps",
            "out": out_dir, "filename": "E07-rig-armature.png", "rows": rows}
    with open(os.path.join(out_dir, "panels.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print("PANELS_OK " + json.dumps({"max_vertex_motion": moved, "rows": len(rows),
                                     "stray_meshes_removed": stray}))


if __name__ == "__main__":
    main()
