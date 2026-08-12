#!/usr/bin/env python
"""render_reference — the identity input: one beauty render of the performer.

    blender -b -P tools\\render_reference.py -- --glb=<rigged.glb> --out=<dir>

THE ROUTE THIS SERVES. armature is image-to-video with a GLB instead of an image: the GLB
supplies **who he is**, the model generates **the performance**. So this render is not a
control channel and not previz — it is the single reference plate the sampler sees, and
the only thing in the whole payload that carries the character.

Framed like the E33 twins on purpose (`twin_r3_v0.png`, 352x1024, measured): full body,
portrait, centred, plain pale backdrop, soft studio light, the unglazed-terracotta register
the Director ruled canon. Rendering at 2x the twins' pixel size and nothing else different,
so "same register" is a property of the recipe rather than a claim in a report.

⚠ **RECORDED RISK, not a defect this tool introduces.** E07's quality ledger carries *the
atlas holes* — the E33 brush pass never ran, so the hand-interior texels are dilation fill
and the Director's "tiny triangle artifacts" are in every render since the twins. This
render is taken from that atlas and therefore carries them. The alternate reference, if the
probe shows them poisoning identity or surface, is `twin_r3_v0.png` itself — and switching
is the **advisor's call after the probe**, never this tool's and never silent.

Rest pose, explicitly: E07's GLB ships a 33-frame probe action on one shoulder. It is
removed rather than trusted to sit at zero on frame 1.

Prints `RENDER_REFERENCE_OK`. A crashed `blender -b -P` exits 0 (E07, three instances), so
that line is the contract and the exit code is not.
"""

import argparse
import hashlib
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import rig_character  # noqa: E402  (the OBJ gate; enumerated, not rebuilt)
from armature_core import blender_scene, framing  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E08.1"

#: The E33 twins, measured: 352 x 1024. Rendered at 2x — same framing, more pixels.
TWIN_SIZE = (352, 1024)
SCALE = 2

AZIMUTH_DEG = 225.0     # three-quarter front from his right: 45 deg off his facing axis
ELEVATION_DEG = 4.0     # just above his mid-height, the twins' near-level eye
LENS_MM, SENSOR_MM = 50.0, 36.0
HEIGHT_FRAC = 0.86      # of frame height, matching the twins' margins
CENTRE_X, CENTRE_Y = 0.50, 0.50

#: A render whose subject covers less than this fraction of the frame is not a full-body
#: plate — it is a miss. Derived from the framing this tool asks for: at HEIGHT_FRAC of a
#: 0.34-aspect frame a standing figure of this build covers well over 8%.
MIN_SUBJECT_FRACTION = 0.08


class ReferenceGate(GateFailure):
    gate = "REF"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="performer_reference")
    ap.add_argument("--scale", type=int, default=SCALE)
    return ap.parse_args(argv)


def studio(scene, lo, hi):
    """A plain pale backdrop and soft studio light — the twins' staging, in Blender.

    A floor plane plus a back plane rather than a world colour alone: the twins carry a
    soft contact shadow under the feet and a faint vertical falloff behind, and a bare
    world background has neither. The figure would float.
    """
    world = bpy.data.worlds.new("studio")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.80, 0.80, 0.81, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.85

    span = float(max(hi[i] - lo[i] for i in range(3)))
    mat = bpy.data.materials.new("backdrop")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.815, 0.815, 0.822, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.92
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.1

    r = span * 14.0
    cx = 0.5 * (lo[0] + hi[0])
    cy = 0.5 * (lo[1] + hi[1])
    floor_mesh = bpy.data.meshes.new("backdrop_floor")
    floor_mesh.from_pydata([(cx - r, cy - r, lo[2]), (cx + r, cy - r, lo[2]),
                            (cx + r, cy + r, lo[2]), (cx - r, cy + r, lo[2])], [],
                           [(0, 1, 2, 3)])
    floor = bpy.data.objects.new("backdrop_floor", floor_mesh)
    floor.data.materials.append(mat)
    scene.collection.objects.link(floor)

    # the back wall sits behind him along +Y, which is behind a character facing -Y
    back_y = cy + span * 3.0
    back_mesh = bpy.data.meshes.new("backdrop_wall")
    back_mesh.from_pydata([(cx - r, back_y, lo[2]), (cx + r, back_y, lo[2]),
                           (cx + r, back_y, lo[2] + r), (cx - r, back_y, lo[2] + r)], [],
                          [(0, 1, 2, 3)])
    back = bpy.data.objects.new("backdrop_wall", back_mesh)
    back.data.materials.append(mat)
    scene.collection.objects.link(back)

    def area(name, energy, size, loc, rot):
        d = bpy.data.lights.new(name, type="AREA")
        d.energy = energy
        d.size = size
        o = bpy.data.objects.new(name, d)
        o.location = loc
        o.rotation_euler = rot
        scene.collection.objects.link(o)
        return o

    h = 0.5 * (lo[2] + hi[2])
    s = span * 2.0
    # key from camera-left-ish and above, big and soft; fill opposite; a gentle rim
    area("key", 260.0 * span * span, s, (cx - s, cy - s, h + span * 0.9),
         (math.radians(58), 0.0, math.radians(-42)))
    area("fill", 90.0 * span * span, s * 1.4, (cx + s, cy - s * 0.8, h + span * 0.3),
         (math.radians(76), 0.0, math.radians(48)))
    area("rim", 70.0 * span * span, s * 0.7, (cx, cy + s * 0.9, h + span * 1.1),
         (math.radians(120), 0.0, math.radians(0)))
    return floor, back


def main():
    a = parse_args()
    out_dir = os.path.abspath(a.out)
    os.makedirs(out_dir, exist_ok=True)     # scripts create their own output directories
    w, h = TWIN_SIZE[0] * a.scale, TWIN_SIZE[1] * a.scale
    source_sha = _sha256(a.glb)

    scene = rig_character.fresh_scene(16)
    meshes, arms, info = blender_scene.import_glb(a.glb, expected_fps=16)

    # Rest pose, and not by trusting frame 1: E07's GLB carries a probe action.
    for ob in list(bpy.data.objects):
        if ob.animation_data is not None:
            ob.animation_data_clear()
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    for arm_obj in arms:
        for pb in arm_obj.pose.bones:
            pb.matrix_basis.identity()
    bpy.context.view_layer.update()

    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1 or len(arms) != 1:
        raise ReferenceGate(
            f"expected one render-visible mesh and one armature, found {len(visible)} and "
            f"{len(arms)}; guessing which is the character would put an unknown body on "
            f"the only plate that carries identity",
            {"meshes": [o.name for o in meshes], "armatures": [o.name for o in arms]})
    mesh_obj, arm_obj = visible[0], arms[0]
    gate_obj = rig_character.gate_objects_registered(scene, mesh_obj, arm_obj)

    bounds = blender_scene.world_bounds(visible)
    if bounds is None:
        raise ReferenceGate("the imported mesh has no evaluated geometry", {})
    centre, half, sphere_r = bounds
    lo = [centre[i] - half[i] for i in range(3)]
    hi = [centre[i] + half[i] for i in range(3)]

    studio(scene, lo, hi)

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.eevee.taa_render_samples = 128
    # Standard, not Filmic/AgX: the atlas IS the identity and a tone curve would restate
    # the Director's terracotta ruling in a register he did not approve.
    scene.view_settings.view_transform = "Standard"

    corners = [(lo[0], lo[1], lo[2]), (hi[0], lo[1], lo[2]), (lo[0], hi[1], lo[2]),
               (hi[0], hi[1], lo[2]), (lo[0], lo[1], hi[2]), (hi[0], lo[1], hi[2]),
               (lo[0], hi[1], hi[2]), (hi[0], hi[1], hi[2])]
    sol = framing.solve_camera(corners, corners, AZIMUTH_DEG, ELEVATION_DEG,
                               LENS_MM, SENSOR_MM, w, h,
                               height_frac=HEIGHT_FRAC, end_x_frac=CENTRE_X,
                               target_y_frac=CENTRE_Y)
    if not sol["in_frame"]:
        raise ReferenceGate(
            f"the solved framing clips the performer: x {sol['achieved']['union_x']} "
            f"y {sol['achieved']['union_y']}", sol)

    cam_data = bpy.data.cameras.new("reference_cam")
    cam_data.lens = LENS_MM
    cam_data.sensor_fit = "AUTO"
    cam_data.sensor_width = SENSOR_MM
    cam_data.clip_start, cam_data.clip_end = 0.05, 1000.0
    cam = bpy.data.objects.new("reference_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.matrix_world = blender_scene.orbit_matrix(
        Vector(sol["target"]), sol["radius"], ELEVATION_DEG, AZIMUTH_DEG)

    path = os.path.join(out_dir, f"{a.name}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if not os.path.isfile(path):
        raise ReferenceGate(f"the render wrote no file at {path}", {})

    # ---- ANDON: the plate actually carries a figure. A reference that renders an empty
    # backdrop passes every other check here and would spend a credit on nothing — and the
    # failure is silent, because a pale-grey frame is a perfectly well-formed PNG.
    img = bpy.data.images.load(path)
    try:
        buf = np.empty(img.size[0] * img.size[1] * img.channels, dtype=np.float32)
        img.pixels.foreach_get(buf)
        px = buf.reshape(img.size[1], img.size[0], img.channels)[..., :3]
    finally:
        bpy.data.images.remove(img)
    # the backdrop is a flat pale grey; the figure is terracotta, so it separates on the
    # red-minus-blue axis rather than on brightness, which the backdrop shares.
    warmth = px[..., 0] - px[..., 2]
    subject = warmth > 0.02
    frac = float(subject.mean())
    ys, xs = np.nonzero(subject)
    coverage = {
        "subject_fraction": frac,
        "threshold": MIN_SUBJECT_FRACTION,
        "bbox_px": ([int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
                    if xs.size else None),
        "criterion": "red - blue > 0.02 (terracotta against a neutral backdrop)",
    }
    if frac < MIN_SUBJECT_FRACTION:
        raise ReferenceGate(
            f"the reference plate is {frac:.4f} subject against a floor of "
            f"{MIN_SUBJECT_FRACTION}; this is a backdrop with no character on it",
            dict(coverage, framing=sol))

    sha = _sha256(path)
    record = {
        "tool": "render_reference", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "source": {"glb": os.path.abspath(a.glb), "sha256": source_sha},
        "output": {"png": path, "sha256": sha, "bytes": os.path.getsize(path),
                   "resolution": [w, h]},
        "framed_like": {"plate": "E:/AI/training/facet_E33/twins/twin_r3_v0.png",
                        "plate_size": list(TWIN_SIZE), "scale": a.scale},
        "camera": {"azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG,
                   "lens_mm": LENS_MM, "sensor_mm": SENSOR_MM,
                   "target": sol["target"], "radius": sol["radius"],
                   "achieved": sol["achieved"]},
        "pose": "rest — animation data and all action datablocks removed before render",
        "view_transform": "Standard",
        "import": info,
        "gates": {"OBJ": gate_obj, "coverage": dict(coverage, verdict="PASS")},
        "recorded_risk": ("the source atlas carries the unfilled texels of E07's quality "
                          "ledger (the E33 brush pass never ran), so this plate carries "
                          "them; the alternate reference is twin_r3_v0.png and switching "
                          "is the advisor's call after the probe"),
    }
    with open(os.path.join(out_dir, f"{a.name}.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)

    print("RENDER_REFERENCE_OK " + json.dumps({
        "png": path, "sha256": sha, "resolution": [w, h],
        "subject_fraction": round(frac, 5), "subject_bbox_px": coverage["bbox_px"],
        "camera_radius": round(sol["radius"], 4),
        "height_frac_achieved": round(sol["achieved"]["union_height_frac"], 4)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("RENDER_REFERENCE_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
