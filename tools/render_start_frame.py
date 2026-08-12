#!/usr/bin/env python
r"""render_start_frame — the one frame E11 hands an image-to-video model.

    blender -b -P tools\render_start_frame.py -- --glb=<performer.glb>
            --out=<dir> [--frame=0] [--width=832] [--height=480] [--height-frac=0.90]

E11's commission. armature is image-to-video with a GLB instead of an image; this tool is
where the GLB becomes the image. It stages one frame of a performance, lights it, and
writes it at the **generation's own resolution**, so nothing scales, letterboxes or
centre-crops it on the way to the model.

**Why native size, stated as a decision.** E08 handed `WanAnimateToVideo` a 352x1024
portrait reference and measured what the node did to it: `common_upscale(..., "area",
"center")` kept 204 of its 1024 rows — hips and thighs, no head. The Director ruled
letterbox, and E08's own report named the fix this tool implements: a native 832x480 frame
with the figure filling it. Authoring the frame at the model's size removes the whole class
of failure rather than compensating for it.

**The staging is E09/E10's, reused verbatim rather than re-invented** — the same two suns,
the same 0.16/0.16/0.18 world, the same EEVEE + Standard view transform, the same ground
plane, the same 225 deg / 6 deg / 50 mm / 36 mm camera convention. One consequence is worth
naming before anybody reads a result off it: this staging is a grey studio, not a bar. On
the no-control route the start frame is the model's only picture of the world, so a scene
prompt is asking it to *replace* what the image shows rather than to fill a silence. That
is a property of the experiment, recorded here so the report does not have to discover it.

--------------------------------------------------------------------------------
The gates

* **the fps andon** — the scene rate is pinned on an empty scene before the import, or
  `blender_scene.import_glb` raises. glTF key times are SECONDS.
* **Gate WHOLE** (`armature_core.startframe`) — the entire silhouette is inside the frame
  with margin, measured UNCLIPPED on every evaluated vertex. This is the gate the tool
  exists for; the module docstring carries why `solve_camera`'s own `in_frame` cannot do
  it (it is solved over landmarks, which under-report the silhouette).
* **the coverage andon** — the rendered frame differs from an empty plate of the same
  camera, lights and floor with the character hidden. Bounds the other direction: WHOLE
  says nothing left the frame, COVERAGE says somebody is in it. A render of a floor passes
  every count-, size- and legality-based check ever written.
* **the pose andon** — the requested frame index exists inside the action's own range. A
  frame past the end holds the last pose and looks like a perfectly good render.

Prints `RENDER_START_FRAME_OK`. A crashed `blender -b -P` exits 0, so that line is the
contract and `$LASTEXITCODE` proves nothing.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing PNGs and a
sidecar under `outputs/`. Compensator: delete the directory; owner: the executor session.
Inputs are opened read-only.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from armature_core import blender_scene, framing, startframe as SF  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E11.1"

#: The camera convention, carried verbatim from `render_performer` (E09/E10) so this frame
#: shows the performer from the angle the rest of the arc has been looking at him from.
#: 225 deg is a true three-quarter front on a performer who faces -Y; a profile would
#: occlude one arm and one leg outright.
AZIMUTH_DEG = 225.0
ELEVATION_DEG = 6.0
LENS_MM = 50.0
SENSOR_MM = 36.0

#: The generation's own frame. Both dimensions are divisible by 16 and this is the model
#: family's documented 480p bucket; Gate L checks it again downstream against the graph.
WIDTH, HEIGHT = 832, 480

#: Of the frame, over the performer's own silhouette at this pose — not over a landmark
#: cloud, and not over a whole performance. A composition decision, and it is E08's named
#: lever: its identity result was explicitly a FLOOR because the letterboxed reference put
#: the figure at ~165x480 with a face too small to hold. 0.90 leaves ~24 px of margin top
#: and bottom, which is headroom for Gate WHOLE and room for the model to put a room in.
HEIGHT_FRAC = 0.90
CENTRE_X_FRAC = 0.50
CENTRE_Y_FRAC = 0.50

#: Gate WHOLE's clearance. Small enough that it is not a second composition knob, large
#: enough that a body actually touching the border cannot creep under it.
MARGIN_PX = 8

#: A frame whose subject covers less of it than this is not a picture of the performer.
MIN_SUBJECT_FRAC = 0.01

#: Points handed to the framing solve. The solve is approximate by construction (see
#: `startframe.framing_cloud`); Gate WHOLE then runs on every vertex, so an under-report
#: here costs margin, never correctness.
FRAMING_CLOUD_CAP = 1500


class RenderGate(GateFailure):
    """A gate specific to rendering the start frame."""

    gate = "STARTFRAME"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frame", type=int, default=0,
                    help="which frame of the action to stage, 0-based (argparse eats "
                         "leading minus signs: pass flags as --flag=value)")
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--height", type=int, default=HEIGHT)
    ap.add_argument("--height-frac", type=float, default=HEIGHT_FRAC)
    ap.add_argument("--floor", type=int, default=1,
                    help="1 draws a ground plane; recorded either way")
    return ap.parse_args(argv)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _pixels(path, width, height):
    """A rendered PNG as a top-down (H, W, 3) float array.

    `image.pixels` is bottom-up; the flip is what makes the reported bbox agree with the
    coordinates every other tool in this repo — and with the file a human opens — uses.
    """
    img = bpy.data.images.load(path)
    try:
        buf = np.empty(width * height * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(height, width, 4)[::-1, :, :3])
    finally:
        bpy.data.images.remove(img)


def action_frame_range():
    """(first, last) scene frames the imported actions actually key, or None.

    The pose andon's quantity. `frame_set` past the end of an action holds the last pose
    and renders it without complaint, so a frame index that misses the performance
    produces a well-formed picture of the wrong moment.
    """
    lo = hi = None
    for act in bpy.data.actions:
        try:
            a, b = act.frame_range
        except (AttributeError, TypeError):
            continue
        lo = a if lo is None else min(lo, a)
        hi = b if hi is None else max(hi, b)
    if lo is None:
        return None
    return float(lo), float(hi)


def main():
    started = time.time()
    a = parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories
    width, height = int(a.width), int(a.height)

    # ---- fps FIRST, on an empty scene, before the import. glTF key times are seconds.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, a.fps)
    meshes, arms, info = blender_scene.import_glb(a.glb, expected_fps=a.fps)

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"

    # `render_visible_meshes` and not `type == 'MESH'`: the glTF importer drops a
    # 42-vertex Icosphere into a hidden `glTF_not_exported` collection, and framing against
    # it once pulled a whole shot's camera back (blender_scene, G4, 2026-08-10). Framing
    # here is *tighter* than that shot's, so the decoy would cost more, not less.
    subject = blender_scene.render_visible_meshes(scene, meshes)
    if not subject:
        raise RenderGate("the GLB imported no render-visible mesh", {"glb": a.glb})

    span = action_frame_range()
    scene.frame_start, scene.frame_end = 1, max(1, int(span[1]) if span else 1)
    blender_scene.set_scene_frame(scene, a.frame)
    if span is not None and not (span[0] <= scene.frame_current <= span[1]):
        raise RenderGate(
            f"frame {a.frame} maps to scene frame {scene.frame_current}, outside the "
            f"action's own keyed range {span}. Blender holds the nearest pose and renders "
            f"it with no error, so the start frame would be a well-formed picture of a "
            f"moment the performance never had",
            {"requested_frame": a.frame, "scene_frame": scene.frame_current,
             "action_range": list(span)})

    # ---- the silhouette: every evaluated world vertex the renderer is about to draw.
    verts = blender_scene._evaluated_world_vertices(subject)
    if verts.shape[0] == 0:
        raise RenderGate("the subject evaluates to no vertices at this frame", {})
    cloud = [tuple(map(float, p)) for p in verts]
    solve_cloud = SF.framing_cloud(cloud, cap=FRAMING_CLOUD_CAP)

    sol = framing.solve_camera(solve_cloud, solve_cloud, AZIMUTH_DEG, ELEVATION_DEG,
                               LENS_MM, SENSOR_MM, width, height,
                               height_frac=float(a.height_frac),
                               end_x_frac=CENTRE_X_FRAC, target_y_frac=CENTRE_Y_FRAC)
    target, radius = tuple(sol["target"]), float(sol["radius"])

    # ---- Gate WHOLE, on EVERY vertex and unclipped. The solve above is approximate.
    extent = SF.silhouette_extent(cloud, target, radius, AZIMUTH_DEG, ELEVATION_DEG,
                                  LENS_MM, SENSOR_MM, width, height)
    gate_whole = SF.gate_whole(extent, width, height, MARGIN_PX)

    world = bpy.data.worlds.new("performer")
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

    if a.floor:
        ground = bpy.data.meshes.new("ground")
        ground.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [],
                           [(0, 1, 2, 3)])
        gob = bpy.data.objects.new("ground", ground)
        scene.collection.objects.link(gob)
        zs = [(o.matrix_world @ Vector(c)).z for o in subject for c in o.bound_box]
        gob.location = (0.0, 0.0, min(zs))

    cam_data = bpy.data.cameras.new("start_cam")
    cam_data.lens, cam_data.sensor_fit, cam_data.sensor_width = LENS_MM, "AUTO", SENSOR_MM
    cam_data.clip_start, cam_data.clip_end = 0.01, 100.0
    cam = bpy.data.objects.new("start_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.matrix_world = blender_scene.orbit_matrix(Vector(target), radius,
                                                  ELEVATION_DEG, AZIMUTH_DEG)

    frame_path = os.path.join(out, "start_frame.png")
    scene.render.filepath = frame_path
    bpy.ops.render.render(write_still=True)

    # ---- the empty plate: same camera, same lights, same floor, character hidden.
    for o in subject + arms:
        o.hide_render = True
    plate_path = os.path.join(out, "empty_plate.png")
    scene.render.filepath = plate_path
    bpy.ops.render.render(write_still=True)
    for o in subject + arms:
        o.hide_render = False

    frame_px = _pixels(frame_path, width, height)
    plate_px = _pixels(plate_path, width, height)
    diff = np.abs(frame_px - plate_px).max(axis=2) > (1.0 / 255.0)
    frac = float(diff.mean())
    ev_cov = {
        "gate": "COVERAGE", "min_fraction": MIN_SUBJECT_FRAC, "subject_fraction": frac,
        "empty_plate": plate_path,
        "note": ("fraction of pixels differing from an empty-plate render of the same "
                 "camera, lights and floor with the character hidden. It INCLUDES the "
                 "figure's shadow on the ground plane, so its bbox bounds subject+shadow "
                 "and is a diagnostic; Gate WHOLE is what bounds the body")}
    if frac < MIN_SUBJECT_FRAC:
        raise RenderGate(
            f"the render differs from the empty plate over only {frac:.5f} of the image "
            f"(floor {MIN_SUBJECT_FRAC}); the performer is not in it, and a frame of an "
            f"empty floor would condition the whole generation", ev_cov)
    ev_cov["verdict"] = f"subject covers {frac:.4f} of the frame"

    ys, xs = np.nonzero(diff)
    rendered_bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]

    provenance = {
        "tool": "render_start_frame", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "source": {"glb": os.path.abspath(a.glb), "sha256": _sha256(a.glb),
                   "frame_index": a.frame, "scene_frame": scene.frame_current,
                   "action_frame_range": list(span) if span else None,
                   "pose_signature":
                       blender_scene.evaluated_geometry_signature(subject)},
        "resolution": [width, height], "fps": a.fps, "floor_drawn": bool(a.floor),
        "staging": {
            "inherited_from": "render_performer (E09/E10), verbatim",
            "world_background": [0.16, 0.16, 0.18, 1.0],
            "key_sun_energy": 3.2, "fill_sun_energy": 1.1,
            "engine": "BLENDER_EEVEE", "view_transform": "Standard",
            "consequence": ("the start frame shows a grey studio, not a bar. On the "
                            "no-control route this frame is the model's only picture of "
                            "the world, so the scene clause of the prompt is asking the "
                            "model to REPLACE what it shows, not to fill a silence")},
        "camera": {
            "azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG,
            "lens_mm": LENS_MM, "sensor_mm": SENSOR_MM,
            "target": list(target), "radius": radius,
            "position": list(framing.camera_position(target, radius,
                                                     ELEVATION_DEG, AZIMUTH_DEG)),
            "height_frac_requested": float(a.height_frac),
            "centre_x_frac": CENTRE_X_FRAC, "centre_y_frac": CENTRE_Y_FRAC,
            "solver_achieved": sol["achieved"], "solver_in_frame": sol["in_frame"],
            "framing_cloud": {"n_vertices": len(cloud), "n_solved_against": len(solve_cloud),
                              "cap": FRAMING_CLOUD_CAP}},
        "import_info": info,
        "outputs": {
            "start_frame": {"path": frame_path, "sha256": _sha256(frame_path)},
            "empty_plate": {"path": plate_path, "sha256": _sha256(plate_path)}},
        "measured": {
            "silhouette_extent_px": extent,
            "rendered_subject_bbox_px": rendered_bbox,
            "rendered_bbox_includes_shadow": True,
            "subject_fraction": frac},
        "gates": {
            "fps_ordering": {"verdict": "PASS", "detail": "import_glb(expected_fps)"},
            "POSE": {"verdict": "PASS", "scene_frame": scene.frame_current,
                     "action_frame_range": list(span) if span else None},
            "WHOLE": gate_whole,
            "COVERAGE": ev_cov},
        "elapsed_s": time.time() - started,
    }
    side = os.path.join(out, "start_frame_provenance.json")
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(provenance, fh, indent=2)

    print("RENDER_START_FRAME_OK " + json.dumps({
        "frame": frame_path, "sha256": provenance["outputs"]["start_frame"]["sha256"][:32],
        "resolution": [width, height], "scene_frame": scene.frame_current,
        "figure_height_frac": round(gate_whole["height_frac"], 4),
        "smallest_margin_px": round(min(gate_whole["margins_px"].values()), 1),
        "subject_fraction": round(frac, 4),
        "gate_WHOLE": gate_whole["verdict"], "gate_COVERAGE": ev_cov["verdict"],
        "provenance": side}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("RENDER_START_FRAME_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
