"""Build a synthetic subject inside Blender, export it as GLB, and export a run.

Run by `tests/test_blender_conventions.py` via `blender -b -P`. It renders and writes;
it asserts nothing. The pytest wrapper reads the PNGs back with Pillow — a different
implementation — and makes the assertions there.

The subject is built so that every convention under test has a *known* right answer
and a *distinguishable* wrong one:

    plane NEAR  at x = +0.5, occupying z in [-0.4, 0]   -> nearer, LOWER in frame
    plane FAR   at x = -0.5, occupying z in [ 0, +0.4]  -> farther, UPPER in frame

with the camera parked at azimuth 0, elevation 0 (on the +X axis, looking toward -X)
and screen-up along world +Z.

  * depth direction  — if the ramp were inverted, the upper half would be brighter.
  * vertical orientation — if the image were flipped, near would land at the top.
    A flip is invisible on a symmetric subject, so the subject is not symmetric.
  * camera-space normals — both planes face +X in world space. Under the correct
    transform they encode (128,128,255); if the transform were skipped and world
    normals emitted unchanged, they would encode (255,128,128). The camera is deliberately not
    axis-aligned with world, so the two answers differ.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))

import bpy  # noqa: E402

import stage_render  # noqa: E402
from armature_core import shotspec  # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)


def quad_facing_plus_x(name, x, y_half, z_lo, z_hi):
    """Winding chosen so the face normal is +X (cross of the first two edges)."""
    verts = [(x, -y_half, z_lo), (x, y_half, z_lo), (x, y_half, z_hi), (x, -y_half, z_hi)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


bpy.ops.wm.read_factory_settings(use_empty=True)
quad_facing_plus_x("NEAR_LOWER", 0.5, 0.4, -0.4, 0.0)
quad_facing_plus_x("FAR_UPPER", -0.5, 0.4, 0.0, 0.4)

glb = os.path.join(OUT, "synthetic.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=False)

spec = shotspec.normalise_spec({
    "spec_version": 1,
    "name": "E01-conventions",
    "generator": "wan-vace",
    "asset": {"path": glb},
    "resolution": {"width": 64, "height": 96},
    "frames": {"count": 5, "fps": 16},
    "channels": ["depth", "normal", "mask", "edge"],
    "camera": {
        "elevation_deg": 0.0,
        "azimuth_start_deg": 0.0,
        "azimuth_sweep_deg": 0.0,   # parked: every frame is the same view
        "fit_margin": 1.3,
    },
})

run_dir = os.path.join(OUT, "run")
manifest = stage_render.run_export(spec, run_dir)
print("SYNTHETIC_RUN " + json.dumps({
    "run_dir": run_dir,
    "glb": glb,
    "frames": manifest["frame_count"],
    "camera_radius": manifest["scene"]["camera_radius_resolved"],
    "z_min": manifest["frames"][0]["z_min"],
    "z_max": manifest["frames"][0]["z_max"],
    "g4_max_delta": manifest["gates"]["G4"]["max_delta_px"],
    "alpha_soft_fraction": manifest["frames"][0]["alpha_soft_fraction"],
}))
