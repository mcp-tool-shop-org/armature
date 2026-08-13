"""Is the procedural floor actually procedural, and does it actually change the floor?

    blender -b -P tests/blender/check_floor_material.py

Two claims ride the record when E12's A1w arm runs, and both are the kind that read as true
in a provenance file while being false in the render:

* **no image file** — the licence claim. A material that quietly reads a downloaded wood
  texture puts an unlicensed third-party asset into a pipeline that bans non-commercial and
  research-only work outright, and nothing downstream would ever notice: the render is the
  right size, the gates pass, the frame looks better than before.
* **it is a wood floor, not a flat fill** — a material whose nodes are wired wrongly resolves
  to a single colour, which renders cleanly, passes every check, and is just the pale studio
  slab in a different shade.

So this drives the REAL builder, `render_start_frame.build_wood_material`, and reports the
node inventory, every image datablock the file holds, and the rendered floor's own variance
against a materialless control.

**At the production camera, which is the whole point of the second claim.** The first
version of this fixture looked down at the floor from about 80 degrees, measured the wood at
a mean of 0.0999, and passed — while the real render came back at 0.3729 with a pale sheen,
because `render_start_frame` shoots from **6 degrees of elevation** and at that grazing angle
Fresnel drives the specular lobe toward 1.0 and a dark base colour is washed out by the
reflected world. A fixture that measures a material at a geometry the pipeline never uses is
measuring a different material. The camera convention, the two suns and their angles below
are `render_start_frame`'s own, imported from it rather than retyped.

Prints `FLOOR_MATERIAL <json>`.
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
from armature_core import blender_scene  # noqa: E402

W, H = 320, 180
#: The shot's own geometry, imported rather than retyped. 6 degrees of elevation is a
#: grazing view of the floor, and that is exactly the condition the second claim has to
#: survive.
TARGET, RADIUS = (0.0, 0.0, 0.9), 4.0


def scene_with_floor(material):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"

    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.035, 0.022, 0.014, 1.0)

    # Both suns, at the tool's own energies and angles.
    key = bpy.data.lights.new("key", type="SUN")
    key.energy = 3.2
    ko = bpy.data.objects.new("key", key)
    sc.collection.objects.link(ko)
    ko.rotation_euler = (math.radians(58), 0.0, math.radians(-25))
    fill = bpy.data.lights.new("fill", type="SUN")
    fill.energy = 1.1
    fo = bpy.data.objects.new("fill", fill)
    sc.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(65), 0.0, math.radians(150))

    mesh = bpy.data.meshes.new("ground")
    mesh.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [],
                     [(0, 1, 2, 3)])
    gob = bpy.data.objects.new("ground", mesh)
    sc.collection.objects.link(gob)

    info = None
    if material in ("wood", "flat"):
        mat, info = RSF.build_wood_material()
        if material == "flat":
            # THE control the grain claim needs: the same material, mis-wired the way a
            # broken graph mis-wires — the ramp no longer reaches the shader, so the floor
            # resolves to ONE colour at the same darkness. Comparing wood against the pale
            # default instead would compare brightness, not texture, and a dark floor has
            # less absolute variation than a bright one however much grain it has.
            nt = mat.node_tree
            bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
            for link in list(bsdf.inputs["Base Color"].links):
                nt.links.remove(link)
            mid = tuple((d + l) / 2 for d, l in
                        zip(RSF.WOOD["dark_linear"], RSF.WOOD["light_linear"]))
            bsdf.inputs["Base Color"].default_value = (*mid, 1.0)
        mesh.materials.append(mat)

    cam_data = bpy.data.cameras.new("c")
    cam_data.lens, cam_data.sensor_width = RSF.LENS_MM, RSF.SENSOR_MM
    cam_data.clip_start, cam_data.clip_end = 0.01, 100.0
    cam = bpy.data.objects.new("c", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.matrix_world = blender_scene.orbit_matrix(
        Vector(TARGET), RADIUS, RSF.ELEVATION_DEG, RSF.AZIMUTH_DEG)
    return sc, info


def render(sc, tag):
    out = os.path.join(REPO, "outputs", "_test_floor_material")
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, f"{tag}.png")
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(p)
    try:
        buf = np.empty(W * H * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(H, W, 4)[::-1, :, :3])
    finally:
        bpy.data.images.remove(img)


sc, info = scene_with_floor("wood")
wood_px = render(sc, "wood")
# Every image datablock in the file after building the material. Not the node inventory —
# the FILE. A texture pulled in by any route at all shows up here.
images_after = [i.name for i in bpy.data.images if i.name not in ("Render Result",)]

sc2, _ = scene_with_floor("default")
plain_px = render(sc2, "default")

sc3, _ = scene_with_floor("flat")
flat_px = render(sc3, "flat")

# The floor occupies the frame below the horizon; at 6 degrees of elevation that seam sits
# near the middle, so the lower third is floor and only floor in both renders.
band = slice(int(H * 0.66), H)


def high_freq_std(px):
    """Variation that is NOT the lighting gradient.

    Plain `std` over the floor cannot answer "is there grain": at 6 degrees of elevation the
    floor carries a strong brightness gradient from the near edge to the horizon, and that
    gradient dominates the number. Measured, it does so almost completely — the mis-wired
    single-colour control comes back at 0.0291 against the real material's 0.0324, a ratio of
    1.11 that would make any threshold either vacuous or arbitrary.

    A discrete Laplacian is zero on a linear gradient and non-zero on texture, so this
    separates the two things the plain std adds together.
    """
    a = px.mean(axis=2).astype(np.float64)
    lap = (-4.0 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:])
    return float(lap.std())
result = {
    "camera": {"azimuth_deg": RSF.AZIMUTH_DEG, "elevation_deg": RSF.ELEVATION_DEG,
               "lens_mm": RSF.LENS_MM, "sensor_mm": RSF.SENSOR_MM,
               "target": list(TARGET), "radius": RADIUS,
               "note": "render_start_frame's own convention — a grazing view of the floor"},
    "material_info": info,
    "image_datablocks_in_file": images_after,
    "node_types": info["node_types"],
    "reads_image_file": info["reads_image_file"],
    "wood_floor_std": float(wood_px[band].std()),
    "plain_floor_std": float(plain_px[band].std()),
    "flat_floor_std": float(flat_px[band].std()),
    "wood_floor_mean": float(wood_px[band].mean()),
    "plain_floor_mean": float(plain_px[band].mean()),
    "flat_floor_mean": float(flat_px[band].mean()),
    "wood_floor_hf": high_freq_std(wood_px[band]),
    "flat_floor_hf": high_freq_std(flat_px[band]),
    "plain_floor_hf": high_freq_std(plain_px[band]),
}
print("FLOOR_MATERIAL " + json.dumps(result))
