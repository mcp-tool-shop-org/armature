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


def _render_status(result):
    """The render operator's status set as a sorted list of strings, `[]` if unreadable.

    WAVE 14, F-6a9a0f72. `bpy.ops.render.render(write_still=True)` returns an operator
    STATUS SET and can return `{'CANCELLED'}` without raising -- the premise this repo
    recorded in wave 12 and then read at none of its 14 render call sites. Every check
    those call sites have downstream (`os.path.isfile`, `getsize`, a re-read of the pixels)
    is a property a PREVIOUS run's file at the same path satisfies, so the operator's own
    verdict is the only clause that distinguishes "this call drew nothing" from "an older
    file is sitting where this call's output was supposed to land". An unreadable return is
    `[]`, which FAILS the `'FINISHED' in ...` clause rather than passing it.

    It is spelled once per tool rather than imported, because these modules share no
    parent inside `tools/` -- `armature_core` is where one implementation belongs and it is
    outside this domain's globs (FILED, see the wave-14 report). The census in
    `tests/test_instruments_amend_w14.py` asserts every copy is byte-identical, so the
    duplication cannot drift.
    """
    try:
        return sorted(str(s) for s in result)
    except TypeError:
        return []


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

    **The gate owns its threshold; a caller may only tighten it.** ROUTED 2026-09-04 from
    core-gates' threshold-argument family (the same shape they applied to four rig gates):
    a tolerance the caller can LOOSEN is a gate the caller can switch off, one keyword at a
    time, with the record still reporting that the gate ran and passed. `MIN_SUBJECT_FRAC`
    is a decision about what a picture of the performer IS, and it belongs to the gate.
    Passing a smaller `min_frac` (a stricter bar) is allowed and recorded; passing a larger
    one raises here, before a single pixel is read.
    """
    if min_frac > MIN_SUBJECT_FRAC:
        raise RenderGate(
            f"gate_coverage was asked to accept {min_frac} where its own floor is "
            f"{MIN_SUBJECT_FRAC}. A caller may TIGHTEN this gate and may not loosen it: "
            f"what counts as a picture of the performer is the gate's decision, not the "
            f"caller's, and a loosened threshold leaves a record saying the gate passed",
            {"gate": "COVERAGE", "requested_min_fraction": min_frac,
             "gate_floor": MIN_SUBJECT_FRAC})
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
        # Same filter as render_start_frame.py:435 and render_turnaround: the ground
        # plane's height is a MEASUREMENT of the subject, and the glTF importer's hidden
        # radius-1.0 Icosphere sits at the origin, so an unfiltered `min(zs)` puts the
        # floor a metre under a character standing on it and nothing reports the gap.
        zs = [(o.matrix_world @ Vector(c)).z
              for o in blender_scene.render_visible_meshes(scene, meshes)
              for c in o.bound_box]
        if not zs:
            raise RenderGate(
                "the GLB imported no render-visible mesh, so the floor has no height to "
                "sit at", {"glb": a.glb, "mesh_objects": [o.name for o in meshes]})
        gob.location = (0.0, 0.0, min(zs))

    # Every refusal above this line can fire before a single pixel exists; the output
    # directory is created HERE so a halt does not leave an empty one behind for a
    # later run to read as a used one (F-8d2b9d7d). Nothing between the old site and
    # this one writes.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

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
        render_result = bpy.ops.render.render(write_still=True)
        # WAVE 14, F-6a9a0f72: the render operator's STATUS SET, read. The existence and
        # size checks below are properties a PREVIOUS run's file at the same path satisfies;
        # only the operator's own verdict says whether THIS call drew anything. Shape carried
        # from `rig_bake.py`'s `if 'FINISHED' not in result`.
        _status = _render_status(render_result)
        if "FINISHED" not in _status:
            raise RenderGate(
                f"the render operator did not report FINISHED for "
                f"{os.path.basename(p)}; it returned {_status!r}, and any file at "
                f"that path is then the previous run's",
                {"clause": "operator_status", "status": _status,
                 "path": os.path.abspath(p)})
        paths.append(p)

    # The population is the PLAN, not whatever is in the directory — the shape
    # `preview_walk.py:167` carries, under a comment naming this exact failure. MEASURED
    # 2026-09-04 (F-ed1dfdb5) on the superseded two lines
    #
    #     written = sorted(f for f in os.listdir(out) if f.startswith("0") ...)
    #     if len(written) != count: raise RenderGate(f"wrote {len(written)} frames ...")
    #
    # a 16-frame run into an `--out` already holding a stale `00099.png`, with `00007.png`
    # never written, gives `len(written) == 16 == count` and the gate does NOT fire; and a
    # 16-frame run into a directory holding 33 stale frames prints "wrote 33 frames" about
    # a run that wrote 16. A zero-byte frame passed either way, because nothing read
    # `getsize`. `paths` is built two lines above and is the list the render wrote against.
    missing = [p for p in paths if not os.path.isfile(p)]
    empty = [p for p in paths
             if p not in missing and os.path.getsize(p) == 0]
    planned_names = {os.path.basename(p) for p in paths}
    # `.lower().endswith` and not `.endswith` (F-ffdb6d4d). MEASURED 2026-09-04: this
    # test was case-SENSITIVE while the consumers that list frames downstream
    # (`encode_control.py:126`, `invert_frames.py:70`) match case-INSENSITIVELY, so a
    # frame arriving as `.PNG` -- an operator copy, a tool from another pipeline -- was
    # absent from this record (which then said nothing unexpected was in the directory)
    # while a consumer picked it up and encoded it into the clip. The sibling renderer
    # `preview_walk` now derives the same population.
    strays = sorted(f for f in os.listdir(out)
                    if f.lower().endswith(".png") and f not in planned_names
                    and f != "empty_plate.png")
    if missing or empty:
        raise RenderGate(
            f"the performance is not complete: {len(missing)} of {count} frames were "
            f"never written {[os.path.basename(p) for p in missing[:8]]} and "
            f"{len(empty)} are zero bytes {[os.path.basename(p) for p in empty[:8]]}",
            {"out": out, "planned": count,
             "missing": [os.path.basename(p) for p in missing],
             "empty": [os.path.basename(p) for p in empty],
             "unexpected_files_in_out_dir": strays})

    # ---- the empty plate the coverage andon measures against: same camera, same lights,
    # same floor, character hidden. One frame, because none of those move.
    for o in meshes + arms:
        o.hide_render = True
    empty_plate = os.path.join(out, "empty_plate.png")
    scene.render.filepath = empty_plate
    render_result = bpy.ops.render.render(write_still=True)
    # WAVE 14, F-6a9a0f72: the render operator's STATUS SET, read. The existence and
    # size checks below are properties a PREVIOUS run's file at the same path satisfies;
    # only the operator's own verdict says whether THIS call drew anything. Shape carried
    # from `rig_bake.py`'s `if 'FINISHED' not in result`.
    _status = _render_status(render_result)
    if "FINISHED" not in _status:
        raise RenderGate(
            f"the render operator did not report FINISHED for "
            f"{os.path.basename(empty_plate)}; it returned {_status!r}, and any file at "
            f"that path is then the previous run's",
            {"clause": "operator_status", "status": _status,
             "path": os.path.abspath(empty_plate)})

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
            "unexpected_files_in_out_dir": strays,
            "unexpected_files_rule": (
                "every file in --out whose name ends in .png, compared "
                "case-INSENSITIVELY, that the plan did not name, minus empty_plate.png. "
                "A DIAGNOSTIC: it gates nothing, and a stray cannot make the "
                "frame-completeness check pass or fail. The sibling renderer "
                "preview_walk.py derives the same population"),
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


def _halt_keysafe(value, _seen=None):
    """`value` with every mapping key stringified, at every depth.

    `json.dumps(..., default=str)` applies `default` to VALUES ONLY: a tuple key or a
    `numpy.int64` key raises `TypeError` from inside the halt handler below, the new
    exception leaves the whole `try` statement, `sys.exit` never runs -- and `blender -b -P`
    then exits **0** on a fired andon, with no sentinel line at all. MEASURED 2026-09-04
    against all 21 handlers: 21 of 21 escaped that way. Pinned by
    `tests/test_instruments_amend_w10.py`.

    STAGE B: this belongs in `armature_core.errors` beside the halt vocabulary, as one
    implementation with 21 call sites (together with `halt_outcome`, which lives in
    `rig_character.py` today and is inlined as a ternary in the other twenty).
    `armature_core` is outside the instruments domain's globs, so the lift is FILED, not
    done -- see the wave-10 `skipped[]` entry for F-ce3a471d.
    """
    # WAVE-10 MERGE (coordinator, 2026-09-04): a SELF-REFERENCING evidence dict recursed here until
    # `RecursionError` escaped the handler — measured on the merged tree by
    # `tests/test_instrument_exits.py` (the "circular" direction), 21 of 21. Containers already
    # on the path are written as the literal "<circular>" instead of re-entered.
    if _seen is None:
        _seen = set()
    if isinstance(value, (dict, list, tuple)):
        if id(value) in _seen:
            return "<circular>"
        _seen = _seen | {id(value)}
    if isinstance(value, dict):
        return {str(k): _halt_keysafe(v, _seen) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_halt_keysafe(v, _seen) for v in value]
    return value


if __name__ == "__main__":
    # THE HALT CONTRACT — one shape across all 21 Blender-side tools (wave 8; pinned by
    # `tests/test_instruments_amend_w8.py`). `blender -b -P` exits **0** when the script's
    # exception propagates (E07, measured three times: rig_character.py, rig_parts.py,
    # author_walk.py), so a halt that does not exit deliberately is reported as a success.
    #
    # THREE outcomes, not two. A typed `GateFailure` is an andon that fired and names
    # itself; a bare `ArmatureError` is a deliberate refusal with no gate behind it (an
    # unknown flag, an unknown `--mode=`); anything else is a crash. Recording a crash as
    # "a gate fired" is a false record — F-c3f86abc measured `rig_character` writing one.
    # A deliberate refusal exits 2; a crash exits 1.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        # THE HALT CONTRACT'S OWN GUARD (F-586822bf, wave 12). Wave 10 moved `json.dumps`
        # inside a try/except/finally so a sentinel that cannot serialise could no longer
        # delete `sys.exit` — but the sentinel's CONSTRUCTION stayed ABOVE that guard, and
        # so did `traceback.print_exc()`. MEASURED 2026-09-04 by driving
        # `blender_stub.exit_code_of_main_block` over all 21 WITH_MAIN tools with a
        # `GateFailure` whose evidence carried (a) a key whose `__str__` raises and (b) 6000
        # levels of non-cyclic nesting: 21 of 21 returned code None, with `RuntimeError` /
        # `RecursionError` escaping the handler and ZERO sentinel lines printed — which is
        # `blender -b -P` reporting exit 0 on a fired andon, the E07 failure this contract
        # exists to end.
        #
        # Stated plainly: neither trigger is reachable from today's raise sites (an AST scan
        # of all 21 finds no non-string-literal evidence key, and every `raise` passes an
        # already-materialised f-string, so `str(exc)` cannot fail). The measured defect was
        # in the CLAIM `tests/test_instrument_exits.py` makes about this block — that any
        # secondary failure in a handler still yields a sentinel and an exit code — and the
        # claim is made TRUE here rather than weakened there.
        #
        # Everything below that can fail is inside the guard. What is above it cannot:
        # `isinstance` on an exception, `type(exc).__name__`, and a `json.dumps` of six
        # values that are already strings or None.
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _outcome = ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                    else "REFUSED — the tool declined to proceed"
                    if isinstance(exc, ArmatureError)
                    else "FAILED — an unhandled error")
        _sentinel = {
            "tool": "render_performer", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "render_performer", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("RENDER_PERFORMER_HALT " + _line)
            sys.exit(_code)
