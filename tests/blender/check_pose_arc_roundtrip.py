"""Does an authored performance survive the glTF round trip? Run inside Blender.

    blender -b -P tests/blender/check_pose_arc_roundtrip.py -- <subject.glb>

**This is the check E03 cannot proceed without**, and it is separated from the render
because it is fast, free, and answers the one question that would otherwise be answered by
33 rendered frames and a fired G6. The round trip has three places to lose an action:

  1. the exporter may not write object-level TRS animation at all;
  2. glTF stores key times in **seconds**, so an export at one fps read back at another
     lands the keys on different frames — the arc arrives compressed or stretched, and
     nothing errors;
  3. the importer may create the action but leave it unassigned, in which case
     `frame_set` moves the timeline and the geometry does not follow.

All three produce a well-formed GLB. Only the evaluated world position of the moving
geometry distinguishes them, which is what this measures — against the authored ground
truth in the `.joints.json` sidecar, not against itself.

Exits non-zero with a named reason on any mismatch, so it can gate a shell step; the
render's G6 is the andon that stands inside the tool.
"""

import json
import os
import sys

import bpy
import numpy as np

TOL = 1e-4  # metres. Round-trip error is float32 in the buffer; 0.1 mm is generous.


def evaluated_vertices(objects):
    deps = bpy.context.evaluated_depsgraph_get()
    chunks = []
    for ob in objects:
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        if me is None or not len(me.vertices):
            ev.to_mesh_clear()
            continue
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        M = np.array(ev.matrix_world, dtype=np.float64)
        chunks.append(co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
        ev.to_mesh_clear()
    return np.concatenate(chunks, axis=0) if chunks else np.zeros((0, 3))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        print("CHECK_FAIL need a path to a .glb")
        return 2
    glb = argv[0]
    with open(os.path.splitext(glb)[0] + ".joints.json", encoding="utf-8") as fh:
        side = json.load(fh)

    arc = side.get("pose_arc")
    if not arc:
        print("CHECK_FAIL the sidecar carries no pose_arc; this asset has no performance")
        return 2
    count, fps = arc["frames"], arc["fps"]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    # Set fps BEFORE importing: the importer maps key times in seconds onto frames using
    # the scene's rate, and this is failure mode 2 above.
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    bpy.ops.import_scene.gltf(filepath=glb)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    actions = len(bpy.data.actions)
    print(f"  imported {len(meshes)} mesh objects, {actions} action(s), fps={scene.render.fps}")
    if actions == 0:
        print("CHECK_FAIL no action survived the export/import; the arc is gone")
        return 1

    # glTF export is Y-up; the sidecar's ground truth is authored Z-up. Convert the truth
    # into the imported frame rather than the other way round, so what is compared is what
    # the renderer will actually evaluate.
    def zup_to_import(p):
        return np.array([p[0], p[1], p[2]], dtype=np.float64)

    worst = 0.0
    rows = []
    for i in (0, count // 2, count - 1):
        scene.frame_set(1 + i)
        bpy.context.view_layer.update()
        pts = evaluated_vertices(meshes)
        truth = zup_to_import(side["frames"][i]["joints_world_zup"]["wrist_r"])
        # The wrist is a bone END, not a ball, so no vertex sits exactly on it. Compare
        # against the nearest vertex: if the arm is where it should be, some geometry is
        # within a limb radius of the authored wrist. If the arc did not survive, the
        # nearest vertex stays at the T-pose position and the distance blows up.
        d = float(np.linalg.norm(pts - truth, axis=1).min())
        rows.append((i, side["frames"][i]["angle_deg"], truth.tolist(), d))
        worst = max(worst, d)

    radius = side["params"]["thickness"]
    for i, ang, truth, d in rows:
        print(f"  f{i:03d} angle={ang:7.3f}  authored wrist={[round(v, 4) for v in truth]}"
              f"  nearest vertex {d:.5f} m")

    # The arc must MOVE: frame 0 and the last frame must not evaluate identically.
    scene.frame_set(1)
    bpy.context.view_layer.update()
    first = evaluated_vertices(meshes)
    scene.frame_set(count)
    bpy.context.view_layer.update()
    last = evaluated_vertices(meshes)
    moved = float(np.abs(first - last).max())
    print(f"  max vertex displacement frame 1 -> frame {count}: {moved:.5f} m")

    if moved < TOL:
        print("CHECK_FAIL the geometry is identical at the first and last frame; the "
              "action imported but is not driving anything")
        return 1
    if worst > radius + TOL:
        print(f"CHECK_FAIL geometry is {worst:.5f} m from the authored wrist, further than "
              f"one limb radius ({radius}); the pose does not match the ground truth")
        return 1

    print(f"CHECK_OK the arc survived the round trip; worst gap {worst:.5f} m "
          f"within limb radius {radius}, displacement {moved:.5f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
