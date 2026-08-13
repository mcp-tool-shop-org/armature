"""Does Blender's ORTHO camera do what `framing.ortho_half_spans` says it does?

    blender -b -P tests/blender/check_ortho_convention.py

S04's spec marks one premise ASSUMED — "Blender 5.2 headless supports `camera.type='ORTHO'`
+ `ortho_scale`" — and says the first unit render verifies it before any batch. This is that
render, kept as a fixture rather than thrown away, because three separate conventions ride
on it and every one of them is invisible on the shot-set's own square preset.

**1. Which axis `ortho_scale` spans.** `framing.ortho_half_spans` claims Blender's AUTO fit
puts it on the LONGER image axis, mirroring `half_fovs`. On a 1024x1024 frame — the Task-C
preset — the two candidate conventions predict *identical* pixels, so the frame here is
352x1024, where they differ by a factor of (1024/352)². Both predictions are computed and
reported, so the record shows which one the render actually matched rather than only that
one of them fit.

**2. Whether parallel projection is really parallel.** The same subject is rendered at two
standoffs. Under perspective these differ by the ratio of the distances; under parallel they
are the same silhouette. This is what makes the shot-set's shared scale mean anything: if
distance still moved size, one `ortho_scale` across eight views would not produce one scale.

**3. Which end of `Image.pixels` is the top.** The single premise carrying
`_measure_alpha_plane`'s flip, and NOTHING derived from a centred figure's bbox can check
it — the solve centres the subject, so a flipped box maps to itself within a pixel. So the
subject here is deliberately NOT centred: one small cube placed high above the camera
target. Read the array raw, and the rows it lands in answer the question outright.

Prints `ORTHO_CONVENTION <json>`. A crashed `blender -b -P` exits 0, so that line is the
contract.

Compensator (NAMED_COMPENSATORS): writes PNGs under `outputs/_test_ortho_convention/`.
Compensator: delete that directory; owner: the executor session.
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

from armature_core import blender_scene, framing  # noqa: E402
from armature_core import startframe as SF  # noqa: E402

#: NON-square on purpose: the square Task-C preset cannot distinguish the two candidate
#: ortho fits at all.
W, H = 352, 1024

TARGET = (0.0, 0.0, 0.0)
AZ, EL = 270.0, 0.0

#: The cube, and it is placed HIGH rather than at the target. A centred subject cannot
#: answer the row-order question; this one lands in the top of the picture or the bottom,
#: and there is no third possibility.
CUBE_HALF = 0.20
CUBE_CENTRE = (0.0, 0.0, 0.75)


def cube_verts(centre, half):
    cx, cy, cz = centre
    return [(cx + sx * half, cy + sy * half, cz + sz * half)
            for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]


def build(ortho_scale, radius):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True          # alpha marks the subject; lighting is moot
    sc.view_settings.view_transform = "Standard"

    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.16, 0.18, 1.0)

    sun = bpy.data.lights.new("key", type="SUN")
    sun.energy = 3.0
    so = bpy.data.objects.new("key", sun)
    sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(58), 0.0, math.radians(-25))

    verts = cube_verts(CUBE_CENTRE, CUBE_HALF)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new("cube")
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    ob = bpy.data.objects.new("cube", mesh)
    sc.collection.objects.link(ob)

    cam_data = bpy.data.cameras.new("c")
    cam_data.type = "ORTHO"                    # the ASSUMED premise, exercised
    cam_data.ortho_scale = ortho_scale
    cam_data.sensor_fit, cam_data.sensor_width = "AUTO", 36.0
    cam_data.clip_start, cam_data.clip_end = 0.01, 1000.0
    cam = bpy.data.objects.new("c", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.matrix_world = blender_scene.orbit_matrix(Vector(TARGET), radius, EL, AZ)
    # Read BACK off the datablock, here and not later: each `read_factory_settings` frees
    # the previous camera, and a dangling reference raises rather than lying — but the
    # readback is the point (it is what shows ORTHO was accepted, not merely assigned).
    return sc, {"type": cam_data.type, "ortho_scale": float(cam_data.ortho_scale)}


def render_alpha(sc, tag):
    """The alpha plane EXACTLY as Blender hands it back — no flip. That is the question."""
    out = os.path.join(REPO, "outputs", "_test_ortho_convention")
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, f"{tag}.png")
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(p)
    try:
        buf = np.empty(W * H * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return buf.reshape(H, W, 4)[..., 3].copy()
    finally:
        bpy.data.images.remove(img)


def raw_bbox(plane):
    """(x0, y0, x1, y1) of the subject in the RAW array's own row order, or None."""
    mask = plane >= 0.5
    rows, cols = np.any(mask, axis=1), np.any(mask, axis=0)
    if not rows.any():
        return None
    y0, y1 = int(np.argmax(rows)), int(len(rows) - 1 - np.argmax(rows[::-1]))
    x0, x1 = int(np.argmax(cols)), int(len(cols) - 1 - np.argmax(cols[::-1]))
    return (x0, y0, x1, y1)


def predicted(ortho_scale, radius, w, h):
    """The repo's own projection of the cube's corners, in pixels, top-down."""
    ext = SF.silhouette_extent(cube_verts(CUBE_CENTRE, CUBE_HALF), TARGET, radius,
                               AZ, EL, None, None, w, h, ortho_scale=ortho_scale)
    return {k: round(float(ext[k]), 3) for k in ("x0", "x1", "y0", "y1")}


def transposed_prediction(ortho_scale, w, h):
    """What the OTHER candidate convention predicts for the subject's pixel WIDTH.

    Reported so the record shows the two hypotheses being discriminated rather than one
    hypothesis being confirmed. Under the repo's convention the horizontal world span is
    `ortho_scale * w/h` (w < h here); under the transposed one it would be `ortho_scale`.
    """
    world_width = 2.0 * CUBE_HALF
    ours = world_width / (ortho_scale * w / h) * w
    theirs = world_width / ortho_scale * w
    return {"ours_px": round(ours, 3), "transposed_px": round(theirs, 3),
            "ratio": round(theirs / ours, 4)}


SCALE_A, SCALE_B = 2.0, 4.0
RADIUS_NEAR, RADIUS_FAR = 3.0, 30.0

sc, cam_readback = build(SCALE_A, RADIUS_NEAR)
plane_a = render_alpha(sc, "scaleA_near")
bbox_a = raw_bbox(plane_a)

sc2, _ = build(SCALE_A, RADIUS_FAR)
plane_far = render_alpha(sc2, "scaleA_far")
bbox_far = raw_bbox(plane_far)

sc3, _ = build(SCALE_B, RADIUS_NEAR)
plane_b = render_alpha(sc3, "scaleB_near")
bbox_b = raw_bbox(plane_b)

result = {
    "blender": blender_scene.blender_provenance(),
    "camera_type_after_assignment": cam_readback["type"],
    "ortho_scale_after_assignment": cam_readback["ortho_scale"],
    "resolution": [W, H],
    "frame_is_square": W == H,
    "cube": {"centre": list(CUBE_CENTRE), "half": CUBE_HALF, "target": list(TARGET),
             "note": "placed high above the target so the row order has an answer"},
    "scale_a": {
        "ortho_scale": SCALE_A, "radius": RADIUS_NEAR,
        "raw_bbox": list(bbox_a) if bbox_a else None,
        "predicted_top_down": predicted(SCALE_A, RADIUS_NEAR, W, H),
        "width_hypotheses": transposed_prediction(SCALE_A, W, H),
    },
    "scale_a_far": {
        "ortho_scale": SCALE_A, "radius": RADIUS_FAR,
        "raw_bbox": list(bbox_far) if bbox_far else None,
    },
    "scale_b": {
        "ortho_scale": SCALE_B, "radius": RADIUS_NEAR,
        "raw_bbox": list(bbox_b) if bbox_b else None,
        "predicted_top_down": predicted(SCALE_B, RADIUS_NEAR, W, H),
    },
    "half_spans_ours": list(framing.ortho_half_spans(SCALE_A, W, H)),
}
print("ORTHO_CONVENTION " + json.dumps(result))
