"""make_parts_sheet — the dailies sheet for E07 arm (c), the rigid-parts armature.

    blender -b --factory-startup -P tools\\make_parts_sheet.py -- --glb=<parts.glb> --out=<dir>
    <venv-python> tools\\sheet_compose.py <dir>\\panels.json

`rest | frame 17 | frame 33 | 1:1 insets on the joints UNDER ARTICULATION`. The joint seam
read is what the Director rules on, so the insets are framed on the **posed bone position at
the last frame** — where the collar overlap is doing its work — rather than on the rest pose
where every seam is closed by definition.

Rendered from the terracotta body with material and light. No overlay: a bone drawn over the
surface would hide the exact thing being judged. No gate states, no debug text.

**The arc is checked, not assumed.** A re-imported GLB whose parts sit still at frame 33 would
produce a sheet of matching panels reading as "this route does not move", when the truth would
be that the animation did not survive the round trip. It raises instead.
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import rig_character  # noqa: E402
from armature_core import blender_scene  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

FULL_W, FULL_H = 820, 1240
INSET = 620
INSET_HEIGHT_FRACTION = 0.20
ARC_FRAMES = (17, rig_character.PROBE_FRAMES)
#: The joints the Director rules on, in the order he reads them.
INSET_JOINTS = (("shoulder", "shoulder.L"), ("elbow", "elbow.L"),
                ("wrist", "wrist.L"), ("hip", "hip.L"))


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title", default="E07 arm (c) — the rigid-parts armature")
    return p.parse_args(argv)


def light_the_scene(scene):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.30, 0.30, 0.32, 1.0)
    bg.inputs[1].default_value = 1.0
    for name, energy, rot in (("key", 3.4, (52, 0, 26)), ("fill", 1.3, (62, 0, -134)),
                              ("rim", 2.1, (74, 0, 178))):
        data = bpy.data.lights.new(name, type="SUN")
        data.energy = energy
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.rotation_euler = tuple(math.radians(a) for a in rot)


def ortho_camera(scene, name, target, ortho_scale, res, azim_deg=0.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    a = math.radians(azim_deg)
    cam.location = Vector(target) + Vector((6.0 * math.sin(a), -6.0 * math.cos(a), 0.0))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100


def shoot(scene, path):
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def world_bounds(objs):
    lo = np.array([1e18, 1e18, 1e18])
    hi = -lo.copy()
    for ob in objs:
        m = np.array(ob.matrix_world, dtype=np.float64)
        n = len(ob.data.vertices)
        flat = np.empty(n * 3, dtype=np.float64)
        ob.data.vertices.foreach_get("co", flat)
        w = flat.reshape(n, 3) @ m[:3, :3].T + m[:3, 3]
        lo = np.minimum(lo, w.min(axis=0))
        hi = np.maximum(hi, w.max(axis=0))
    return lo, hi


def all_world_verts(objs):
    return np.concatenate([
        (np.frombuffer(bytearray(len(ob.data.vertices) * 24), dtype=np.float64)
         if False else _wv(ob)) for ob in objs], axis=0)


def _wv(ob):
    n = len(ob.data.vertices)
    flat = np.empty(n * 3, dtype=np.float64)
    ob.data.vertices.foreach_get("co", flat)
    m = np.array(ob.matrix_world, dtype=np.float64)
    return flat.reshape(n, 3) @ m[:3, :3].T + m[:3, 3]


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    frames_dir = os.path.join(out, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    scene = rig_character.fresh_scene(rig_character.PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=args.glb)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if not visible:
        raise ArmatureError(f"{args.glb}: no render-visible mesh objects")
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise ArmatureError(f"{args.glb}: expected one armature, found {len(arms)}")
    arm_obj = arms[0]
    light_the_scene(scene)

    scene.frame_set(1)
    bpy.context.view_layer.update()
    lo, hi = world_bounds(visible)
    height = float(hi[2] - lo[2])
    centre = Vector(((lo + hi) / 2.0).tolist())
    at_rest = all_world_verts(visible)

    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()
    moved = float(np.linalg.norm(all_world_verts(visible) - at_rest, axis=1).max())
    if moved <= 1e-6:
        raise ArmatureError(
            f"{args.glb}: the parts are identical at frame 1 and frame "
            f"{rig_character.PROBE_FRAMES}. The authored arc did not survive the round trip, "
            f"and a sheet built from this would read as 'this route does not move'")

    targets = {label: tuple(arm_obj.matrix_world @ arm_obj.pose.bones[bone].head)
               for label, bone in INSET_JOINTS}

    full_scale = height * 1.10
    panels = {}
    for frame in (1,) + tuple(ARC_FRAMES):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        ortho_camera(scene, f"cam_f{frame}", centre, full_scale, (FULL_W, FULL_H))
        panels[f"f{frame}"] = shoot(scene, os.path.join(frames_dir, f"f{frame:02d}.png"))

    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()
    inset_scale = height * INSET_HEIGHT_FRACTION
    for label, _ in INSET_JOINTS:
        ortho_camera(scene, f"cam_{label}", Vector(targets[label]), inset_scale,
                     (INSET, INSET))
        panels[f"inset_{label}"] = shoot(
            scene, os.path.join(frames_dir, f"inset_{label}.png"))

    last = rig_character.PROBE_FRAMES
    spec = {
        "out": out,
        "filename": "E07-parts-armature.png",
        "title": args.title,
        "subtitle": ("17 rigid parts, bone-parented, no deformation anywhere   ·   the arc is "
                     f"E03's: the character's LEFT arm, 0°→90° about +Y, {last} keys at 16 "
                     f"fps   ·   insets are 1:1 at frame {last}, on the joints under "
                     "articulation"),
        "rows": [
            {"title": "The figure through the arc",
             "panels": [{"body": panels["f1"], "label": "frame 1 — rest"},
                        {"body": panels[f"f{ARC_FRAMES[0]}"],
                         "label": f"frame {ARC_FRAMES[0]}"},
                        {"body": panels[f"f{ARC_FRAMES[1]}"],
                         "label": f"frame {ARC_FRAMES[1]}"}]},
            {"title": f"At 1:1, frame {last} — the joint seams under articulation",
             "panels": [{"body": panels[f"inset_{n}"], "label": n}
                        for n, _ in INSET_JOINTS]},
        ],
    }
    path = os.path.join(out, "panels.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print("PANELS_OK " + json.dumps({"panels": path, "max_displacement": moved,
                                     "parts_rendered": len(visible)}))


if __name__ == "__main__":
    main()
