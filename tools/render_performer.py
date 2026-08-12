#!/usr/bin/env python
"""render_performer — a shaded 1080p pass of the performer performing, for the detector.

    blender -b -P tools\\render_performer.py -- --glb=<walk.glb> --motion=<walk.motion.json>
                                                --manifest=<rig_manifest.json> --out=<dir>

E09 Stage B1's instrument. The control channels a video model consumes are not what a
landmark detector consumes: MediaPipe wants a photograph of a person, so this renders the
same performance shaded and textured at full size, composed so the whole walk stays inside
the frame with the figure as large as it can be.

**The camera is solved, not typed in.** `armature_core.framing` fits the radius to the
union of every authored frame and pins the target, so the composition is derivable and can
be checked afterwards against the render's own measured extent. The banked E08 shot solved
the same way at 832x480; this is the same machinery at the detector's resolution.

**The camera basis is recorded, and that is the point of the sidecar.** MediaPipe's world
landmarks arrive in an image-aligned frame, so turning them into rig-space directions needs
to know where the camera was. Writing the basis here means the conversion downstream is
derived from the render that produced the landmarks rather than assumed — and it can be
checked against a best-fit rotation to the known ground truth, which is what E09 does.

Prints `RENDER_PERFORMER_OK`. A crashed `blender -b -P` exits 0, so that line is the
contract and `$LASTEXITCODE` proves nothing.

--------------------------------------------------------------------------------
The gates

* **the fps andon** — the scene rate is pinned on an empty scene before the import, or
  `blender_scene.import_glb` raises. glTF key times are SECONDS; importing at Blender's
  default 24 lands a 16 fps action on the wrong frames while everything else passes.
* **the framing gate** — `solve_camera` reports whether the union stays inside the frame,
  and a composition that clips the performer is refused rather than rendered. A detector
  fed a cropped figure returns landmarks for the part it can see and no error at all.
* **the coverage andon** — every written frame must actually contain the subject. A render
  of an empty backdrop is well-formed, non-empty, correctly sized and counts correctly;
  the only thing wrong with it is that nobody is in it, and a detector would then be
  measured on the background. The bound is a fraction of the FRAME, and the check runs on
  every frame rather than a sample, because the figure walks out of frame gradually.
* **the frame-count check** — as many PNGs as there are authored frames.

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

from armature_core import blender_scene, framing  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E09.1"

#: The composition. Every one of these is a decision and belongs in the report.
#: The azimuth is the banked E08 value and the reason carries: the camera sits at `az`
#: around a performer who faces -Y, and 225 deg is a true three-quarter front. A profile
#: would occlude one arm and one leg outright, and a detector cannot regress what the
#: silhouette does not show.
AZIMUTH_DEG = 225.0
ELEVATION_DEG = 6.0
LENS_MM = 50.0
SENSOR_MM = 36.0
#: 1080p, the reading of the spec's "1080p" that a detector benefits from: the vertical
#: resolution is what sets how many pixels the figure is drawn with.
WIDTH, HEIGHT = 1920, 1080
#: Of the frame, over the union of every authored frame INCLUDING the raised hand. Chosen
#: before any measurement: large enough that the figure is drawn with as many pixels as the
#: frame allows, small enough that 1.27 body-heights of travel still fit across 16:9.
HEIGHT_FRAC = 0.70
END_X_FRAC = 0.62
TARGET_Y_FRAC = 0.52

#: A frame whose subject covers less of it than this is not a picture of the performer.
#: Measured against the FRAME, which is the thing the detector is handed.
MIN_SUBJECT_FRAC = 0.01


class RenderGate(GateFailure):
    """A gate specific to rendering the performer for a detector."""

    gate = "RENDER"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--motion", default=None,
                    help="an AUTHORED motion record (walk.motion.json) to frame against")
    ap.add_argument("--lift", default=None,
                    help="a SOLVED motion record (lift_clip/measure_lift output) to frame "
                         "against; used when there is no authored ground truth, as in B2")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--floor", type=int, default=1,
                    help="1 draws a ground plane; recorded either way")
    return ap.parse_args(argv)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def body_cloud(world, lo, hi):
    """Points that must stay in frame for one authored frame.

    The ground truth carries landmarks, and landmarks under-report the SILHOUETTE: this
    character's torso is wider than his shoulder landmarks, so the rest bbox's own
    half-extents are hung on the hips as a bound. Under-reporting here would frame him
    correctly on paper and clip his shoulder in the render. Lifted in form from E08's
    banked `make_shot_spec.body_cloud` rather than re-derived.
    """
    pts = [tuple(v) for v in world.values() if isinstance(v, list) and len(v) == 3]
    hx, hy = 0.5 * (hi[0] - lo[0]), 0.5 * (hi[1] - lo[1])
    hips = tuple(world["hips"])
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            pts.append((hips[0] + sx * hx, hips[1] + sy * hy, hips[2]))
    return pts


def _pixels(path):
    img = bpy.data.images.load(path)
    try:
        return np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3].copy()
    finally:
        bpy.data.images.remove(img)


def gate_coverage(paths, empty_plate, min_frac=MIN_SUBJECT_FRAC):
    """ANDON — the performer is actually in every frame that was written.

    **The invariant nothing else here bounds.** The frame count is right, the files are
    non-empty, the resolution is right and the camera solves perfectly on a render with
    nobody in it; the only thing wrong with such a render is that it is a picture of a
    floor, and a detector measured on it would be measured on a floor.

    **Measured against an empty plate, and the first version was not.** That one counted
    pixels differing from the frame's own modal colour, which on a scene with a ground
    plane reads about 0.63 whether the character is there or not — the floor supplies the
    non-modal pixels by itself. A check that returns a healthy number on the failure it
    exists to catch is not a check. The plate is the same camera, the same lights and the
    same floor with the character hidden, rendered once because none of those move, so the
    difference is the subject and nothing else.
    """
    base = _pixels(empty_plate)
    per_frame, worst = [], {"frame": None, "frac": 1.0}
    for i, p in enumerate(paths):
        px = _pixels(p)
        # 1/255 per channel: below one 8-bit step is not a subject, it is quantisation.
        diff = np.abs(px - base).max(axis=1) > (1.0 / 255.0)
        frac = float(diff.mean())
        per_frame.append(frac)
        if frac < worst["frac"]:
            worst = {"frame": i, "frac": frac}
    ev = {"gate": "COVERAGE", "min_fraction": min_frac, "worst": worst,
          "empty_plate": empty_plate, "per_frame_subject_fraction": per_frame,
          "note": ("fraction of pixels differing from an empty-plate render of the same "
                   "camera, lights and floor with the character hidden; a frame with "
                   "nobody in it reads 0 while passing every count-based check")}
    if worst["frac"] < min_frac:
        raise RenderGate(
            f"frame {worst['frame']} differs from the empty plate over only "
            f"{worst['frac']:.5f} of the image (floor {min_frac}); the performer is not "
            f"in it and a detector run on this would be measured on the backdrop", ev)
    ev["verdict"] = (f"min {worst['frac']:.4f} at frame {worst['frame']} over "
                     f"{len(paths)} frames")
    return ev


def main():
    started = time.time()
    a = parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    if not (a.motion or a.lift):
        raise RenderGate(
            "give either --motion (authored ground truth) or --lift (a solved record); the "
            "camera is SOLVED against where the body actually goes, and framing a "
            "performance against nothing would fit the rest pose and clip the performance",
            {})
    with open(a.manifest, encoding="utf-8") as fh:
        rig = json.load(fh)
    lo, hi = rig["bbox"]["lo"], rig["bbox"]["hi"]

    if a.motion:
        with open(a.motion, encoding="utf-8") as fh:
            gt = json.load(fh)["ground_truth"]
        clouds = [body_cloud(rec["world"], lo, hi) for rec in gt]
        frame_source = {"kind": "authored", "path": os.path.abspath(a.motion)}
    else:
        # No ground truth exists for a generated clip, so the framing cloud is computed
        # from the SOLVED rotations through the same kinematics the solver inverts —
        # `lift_solve.fk_sites` — rather than from the rest pose, which would frame a
        # standing figure and clip whatever the performance actually did.
        from armature_core import lift_solve as LS  # noqa: E402  (only this branch needs it)
        rest = {}
        for name, rec in rig["landmarks"].items():
            p = rec["p"] if isinstance(rec, dict) and "p" in rec else rec
            if isinstance(p, (list, tuple)) and len(p) == 3:
                rest[name] = tuple(float(v) for v in p)
        with open(a.lift, encoding="utf-8") as fh:
            frames = json.load(fh)["frames"]
        clouds = []
        for fr in frames:
            placed = LS.fk_sites(rest, {
                "local": {k: tuple(map(tuple, v)) for k, v in fr["local"].items()},
                "root": {"hips_delta_translation": tuple(fr["root"])}})
            world = {k: list(v) for k, v in placed.items()}
            # `body_cloud` hangs the torso's own half-extents on "hips"; the solver's site
            # list calls that landmark "crotch". Aliased rather than renamed, so the two
            # vocabularies stay each correct in their own module.
            world["hips"] = world["crotch"]
            clouds.append(body_cloud(world, lo, hi))
        frame_source = {"kind": "solved_lift", "path": os.path.abspath(a.lift)}

    count = len(clouds)
    all_points = [p for c in clouds for p in c]
    end_points = clouds[-1]

    sol = framing.solve_camera(all_points, end_points, AZIMUTH_DEG, ELEVATION_DEG,
                               LENS_MM, SENSOR_MM, WIDTH, HEIGHT,
                               height_frac=HEIGHT_FRAC, end_x_frac=END_X_FRAC,
                               target_y_frac=TARGET_Y_FRAC)
    if not sol["in_frame"]:
        raise RenderGate(
            f"the solved composition puts part of the performance outside the frame: "
            f"x {sol['achieved']['union_x']} y {sol['achieved']['union_y']}. A detector "
            f"fed a clipped figure returns landmarks for the part it can see and no "
            f"error at all", {"solution": sol})

    target, radius = tuple(sol["target"]), float(sol["radius"])

    # ---- fps FIRST, on an empty scene, before the import. glTF key times are seconds.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, a.fps)
    meshes, arms, info = blender_scene.import_glb(a.glb, expected_fps=a.fps)

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    scene.frame_start, scene.frame_end = 1, count

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
        zs = [(o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box]
        gob.location = (0.0, 0.0, min(zs))

    cam_data = bpy.data.cameras.new("performer_cam")
    cam_data.lens, cam_data.sensor_fit, cam_data.sensor_width = LENS_MM, "AUTO", SENSOR_MM
    cam_data.clip_start, cam_data.clip_end = 0.01, 100.0
    cam = bpy.data.objects.new("performer_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.matrix_world = blender_scene.orbit_matrix(Vector(target), radius,
                                                  ELEVATION_DEG, AZIMUTH_DEG)

    position = framing.camera_position(target, radius, ELEVATION_DEG, AZIMUTH_DEG)
    right, up, back = framing.camera_basis(target, position)

    paths = []
    for i in range(count):
        blender_scene.set_scene_frame(scene, i)
        p = os.path.join(out, f"{i:05d}.png")
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)

    written = sorted(f for f in os.listdir(out) if f.startswith("0") and f.endswith(".png"))
    if len(written) != count:
        raise RenderGate(
            f"wrote {len(written)} frames and the performance is {count}", {"out": out})

    # ---- the empty plate the coverage andon measures against: same camera, same lights,
    # same floor, character hidden. One frame, because none of those move.
    for o in meshes + arms:
        o.hide_render = True
    empty_plate = os.path.join(out, "empty_plate.png")
    scene.render.filepath = empty_plate
    bpy.ops.render.render(write_still=True)
    for o in meshes + arms:
        o.hide_render = False

    gate_cov = gate_coverage(paths, empty_plate)

    side = os.path.join(out, "render_provenance.json")
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({
            "tool": "render_performer", "tool_version": TOOL_VERSION,
            "blender": blender_scene.blender_provenance(),
            "source": {"glb": os.path.abspath(a.glb), "sha256": _sha256(a.glb),
                       "framed_against": frame_source,
                       "manifest": os.path.abspath(a.manifest)},
            "resolution": [WIDTH, HEIGHT], "frames": count, "fps": a.fps,
            "floor_drawn": bool(a.floor),
            "camera": {
                "azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG,
                "lens_mm": LENS_MM, "sensor_mm": SENSOR_MM,
                "target": list(target), "radius": radius,
                "position": list(position),
                # The three axes the MediaPipe conversion is built from. Recorded rather
                # than reconstructed downstream: a conversion derived from the render that
                # produced the landmarks can be checked; one assumed cannot.
                "basis_right": list(right), "basis_up": list(up), "basis_back": list(back),
                "height_frac": HEIGHT_FRAC, "end_x_frac": END_X_FRAC,
                "target_y_frac": TARGET_Y_FRAC,
                "solver_achieved": sol["achieved"], "in_frame": sol["in_frame"],
            },
            "import_info": info,
            "frame_sha256": {os.path.basename(p): _sha256(p) for p in paths},
            "gates": {"fps_ordering": {"verdict": "PASS",
                                       "detail": "import_glb(expected_fps)"},
                      "FRAMING": {"verdict": "PASS", "achieved": sol["achieved"]},
                      "COUNT": {"verdict": "PASS", "frames": count},
                      "COVERAGE": gate_cov},
            "elapsed_s": time.time() - started,
        }, fh, indent=2)

    print("RENDER_PERFORMER_OK " + json.dumps({
        "out": out, "frames": count, "resolution": [WIDTH, HEIGHT],
        "radius": round(radius, 5), "target": [round(v, 5) for v in target],
        "coverage": gate_cov["verdict"], "provenance": side}))
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
        print("RENDER_PERFORMER_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
