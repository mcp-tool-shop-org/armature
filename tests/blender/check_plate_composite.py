"""Measure what the plate composite actually does to a plate's pixels.

    blender -b -P tests/blender/check_plate_composite.py

Gate BACKDROP compares the submitted composite against the plate over the master's
transparent region and passes when they agree to within a tolerance. That tolerance is a
number about **Blender's colour pipeline** — the plate is linearised on load and re-encoded
by the Standard view transform on the way out — and a tolerance guessed from theory is a
gate that either fires on a good run or sleeps through a bad one. So it is measured here,
on a synthetic scene, before any plate exists and before any credit is spent.

This drives the REAL write path: `render_start_frame.wire_plate_composite` and
`render_start_frame._pixels`, not a copy of them. It also carries its own falsifier — the
same numbers computed against the FLAT composite, which is what the un-wired compositor
would have written. If those two disagree by less than the separation the gate demands,
this fixture is no longer able to tell a working compositor from a broken one and says so.

Prints `PLATE_COMPOSITE <json>`.
"""

import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))

import render_start_frame as RSF  # noqa: E402
from armature_core import pngio  # noqa: E402

W, H = 256, 144
WORLD = (0.035, 0.022, 0.014)


def plate_pixels():
    """A plate no flat colour could be mistaken for: a bright two-axis gradient."""
    ys, xs = np.mgrid[0:H, 0:W]
    return np.stack([(40 + xs * 200 // (W - 1)),
                     (30 + ys * 210 // (H - 1)),
                     (200 - xs * 150 // (W - 1))], axis=-1).astype(np.uint8)


def main():
    out = os.path.join(REPO, "outputs", "_test_plate_composite")
    os.makedirs(out, exist_ok=True)

    plate_path = os.path.join(out, "plate.png")
    pngio.write_png(plate_path, plate_pixels())

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = W, H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"

    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (*WORLD, 1.0)

    light = bpy.data.lights.new("key", type="SUN")
    light.energy = 3.2
    lo = bpy.data.objects.new("key", light)
    scene.collection.objects.link(lo)
    lo.rotation_euler = (math.radians(58), 0.0, math.radians(-25))

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    cube = bpy.context.object

    cam_data = bpy.data.cameras.new("c")
    cam_data.lens, cam_data.sensor_width = 50.0, 36.0
    cam = bpy.data.objects.new("c", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = Vector((0.0, -5.0, 0.0))
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)

    # (1) the authored master, RGBA
    master = os.path.join(out, "master.png")
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = master
    bpy.ops.render.render(write_still=True)

    # (2) the flat composite — what the route submits with no plate
    flat = os.path.join(out, "flat.png")
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = flat
    bpy.ops.render.render(write_still=True)

    # (3) the submitted composite: the same master, alpha-over the plate
    RSF.wire_plate_composite(scene, plate_path)
    comp = os.path.join(out, "composite.png")
    scene.render.filepath = comp
    bpy.ops.render.render(write_still=True)

    alpha = RSF._alpha_channel(master, W, H)
    void = alpha < 0.5
    solid = ~void

    plate_px = RSF._pixels(plate_path, W, H)
    comp_px = RSF._pixels(comp, W, H)
    flat_px = RSF._pixels(flat, W, H)

    def mad(a, b, mask):
        return float(np.abs(a[mask] - b[mask]).mean() * 255.0)

    result = {
        "resolution": [W, H],
        "transparent_fraction": float(void.mean()),
        "subject_fraction": float(solid.mean()),
        # what the gate measures on a WORKING compositor
        "void_vs_plate_255": mad(comp_px, plate_px, void),
        "plate_vs_flat_255": mad(plate_px, flat_px, void),
        # the falsifier: the same first number computed on the flat render, which is what an
        # un-wired compositor writes. The gate can only discriminate if this is large.
        "unwired_void_vs_plate_255": mad(flat_px, plate_px, void),
        # the performer must not have moved: alpha-over changes the void, nothing else
        "subject_comp_vs_flat_255": mad(comp_px, flat_px, solid),
        "gate_constants": {"tol_255": RSF.PLATE_TOL_255,
                           "min_separation_255": RSF.PLATE_MIN_SEPARATION_255},
        "cube_present": cube.name in bpy.data.objects,
    }
    print("PLATE_COMPOSITE " + json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
