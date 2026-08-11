"""Headless GLB preview: import, measure, render 2 full views + 2 head crops.

blender -b --factory-startup -P preview_glb.py -- --glb <path> --out <dir> --name <name>
Read-only on the GLB; writes renders + stats.json into --out.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--name", required=True)
    return p.parse_args(argv)


def scene_bbox(objs):
    lo = Vector((1e18, 1e18, 1e18))
    hi = Vector((-1e18, -1e18, -1e18))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def look_at(cam, target):
    d = target - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_camera_render(name_suffix, center, radius, azim_deg, elev_deg, res, out_dir, args):
    scn = bpy.context.scene
    cam_data = bpy.data.cameras.new("cam_" + name_suffix)
    cam_data.lens = 50.0
    cam_data.sensor_width = 36.0
    cam = bpy.data.objects.new("cam_" + name_suffix, cam_data)
    scn.collection.objects.link(cam)
    fov = 2.0 * math.atan(cam_data.sensor_width / (2.0 * cam_data.lens))
    dist = (radius / math.tan(fov / 2.0)) * 1.18
    a = math.radians(azim_deg)
    e = math.radians(elev_deg)
    cam.location = center + Vector((
        dist * math.cos(e) * math.sin(a),
        -dist * math.cos(e) * math.cos(a),
        dist * math.sin(e),
    ))
    look_at(cam, center)
    scn.camera = cam
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.filepath = os.path.join(out_dir, f"{args.name}_{name_suffix}.png")
    bpy.ops.render.render(write_still=True)


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=args.glb)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    empties = [o for o in bpy.data.objects if o.type == "EMPTY"]
    tris = 0
    for ob in meshes:
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
    images = [(im.name, list(im.size)) for im in bpy.data.images if im.name != "Render Result"]
    stats = {
        "glb": args.glb,
        "mesh_objects": len(meshes),
        "armatures": [(a.name, len(a.data.bones), [b.name for b in a.data.bones[:6]]) for a in arms],
        "empties": len(empties),
        "triangles": tris,
        "materials": len(bpy.data.materials),
        "images": images,
    }

    lo, hi = scene_bbox(meshes)
    center = (lo + hi) / 2.0
    dims = hi - lo
    stats["bbox_dims"] = list(dims)
    radius = max(dims) / 2.0

    # head region: top 22% of the bbox, framed square
    head_c = Vector((center.x, center.y, hi.z - 0.11 * dims.z))
    head_r = max(0.14 * dims.z, 0.5 * max(dims.x, dims.y) * 0.6)

    scn = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scn.render.engine = eng
            break
        except TypeError:
            continue
    scn.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scn.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.72, 0.72, 0.73, 1.0)
    bg.inputs[1].default_value = 1.0

    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("sun", sun_data)
    scn.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(35))
    fill_data = bpy.data.lights.new("fill", type="SUN")
    fill_data.energy = 1.2
    fill = bpy.data.objects.new("fill", fill_data)
    scn.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(60), 0.0, math.radians(-140))

    add_camera_render("full_a", center, radius, 30, 10, (640, 960), args.out, args)
    add_camera_render("full_b", center, radius, 210, 10, (640, 960), args.out, args)
    add_camera_render("head_a", head_c, head_r, 30, 6, (512, 512), args.out, args)
    add_camera_render("head_b", head_c, head_r, 210, 6, (512, 512), args.out, args)

    with open(os.path.join(args.out, f"{args.name}_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print("PREVIEW_OK", args.name)


main()
