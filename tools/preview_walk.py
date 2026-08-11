#!/usr/bin/env python
"""preview_walk — a shaded pass at the shot camera, so the walk can be LOOKED at.

    blender -b -P tools\\preview_walk.py -- --spec=<shot spec.json> --out=<dir>

The control channels are what the model sees; they are not what a person judges a walk
from. A depth map hides an arm passing through a torso, and a silhouette hides a foot
sinking through the floor. This renders the same camera, the same frames, shaded and
textured, small and fast, so the performance can be inspected before a credit is spent.

It reads the SAME spec `stage_render` runs, so the preview is the shot rather than a
similar one. Camera construction is `armature_core.framing`, which the spec was solved
with — one implementation, so the preview cannot drift from the render.

Prints `PREVIEW_WALK_OK`; a crashed `blender -b -P` exits 0, so that line is the contract.
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from armature_core import blender_scene, framing, shotspec  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=0.5, help="fraction of shot resolution")
    return ap.parse_args(argv)


def main():
    a = parse_args()
    spec = shotspec.load_spec(a.spec)
    os.makedirs(a.out, exist_ok=True)          # scripts create their own output directories

    fps = spec["frames"]["fps"]
    count = spec["frames"]["count"]
    w = int(round(spec["resolution"]["width"] * a.scale))
    h = int(round(spec["resolution"]["height"] * a.scale))

    # fps FIRST, on an empty scene, before the import. glTF key times are seconds.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, fps)
    asset, sha = shotspec.resolve_asset(spec)
    meshes, arms, info = blender_scene.import_glb(asset, expected_fps=fps)

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    scene.frame_start, scene.frame_end = 1, count

    world = bpy.data.worlds.new("preview")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.16, 0.18, 1.0)

    key = bpy.data.lights.new("key", type="SUN")
    key.energy = 3.2
    ko = bpy.data.objects.new("key", key)
    scene.collection.objects.link(ko)
    ko.rotation_euler = (math.radians(58), 0.0, math.radians(-25))
    fill = bpy.data.lights.new("fill", type="SUN")
    fill.energy = 1.1
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(65), 0.0, math.radians(150))

    # A floor, purely so a foot sinking through it is visible. It is NOT in the control
    # render — the control must leave the ground silent for the model to paint a bar floor.
    ground = bpy.data.meshes.new("ground")
    ground.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [],
                       [(0, 1, 2, 3)])
    gob = bpy.data.objects.new("ground", ground)
    scene.collection.objects.link(gob)
    zs = [(o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box]
    gob.location = (0.0, 0.0, min(zs))

    c = spec["camera"]
    target = Vector(c["target"]) if c["target"] != "bbox_center" else Vector((0, 0, 0))
    radius = float(c["radius"])
    cam_data = bpy.data.cameras.new("preview_cam")
    cam_data.lens = float(c["lens_mm"])
    cam_data.sensor_fit = "AUTO"
    cam_data.sensor_width = float(c["sensor_mm"])
    cam_data.clip_start = float(c["clip_start"])
    cam_data.clip_end = float(c["clip_end"])
    cam = bpy.data.objects.new("preview_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    pos = framing.camera_position(tuple(target), radius, c["elevation_deg"],
                                  c["azimuth_start_deg"])
    cam.matrix_world = blender_scene.orbit_matrix(
        target, radius, c["elevation_deg"], c["azimuth_start_deg"])

    for i in range(count):
        blender_scene.set_scene_frame(scene, i)
        scene.render.filepath = os.path.join(a.out, f"{i:05d}.png")
        bpy.ops.render.render(write_still=True)

    n = len([f for f in os.listdir(a.out) if f.endswith(".png")])
    if n != count:
        raise RuntimeError(f"rendered {n} preview frames, expected {count}")
    print("PREVIEW_WALK_OK " + json.dumps({
        "out": os.path.abspath(a.out), "frames": n, "resolution": [w, h],
        "asset": asset, "asset_sha256": sha, "camera_position": [round(v, 6) for v in pos],
        "import": info}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("PREVIEW_WALK_HALT " + json.dumps({"error": type(exc).__name__,
                                                 "message": str(exc)}))
        sys.exit(1)
