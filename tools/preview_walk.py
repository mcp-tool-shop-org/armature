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
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402


class PreviewWalkGate(GateFailure):
    """The preview could not be composed, or did not complete.

    MEASURED 2026-09-04 (F-1aee25e2): this file's three refusals raised the bare
    `RuntimeError`, which carries no `gate` and no evidence dict, so the measurement that
    stopped the run was discarded at the raise. The handler then printed
    `PREVIEW_WALK_HALT {"error": ..., "message": ...}` — no gate, no evidence — and called
    `sys.exit(1)` unconditionally, where the twenty siblings discriminate. Of the 21
    Blender-side tools this was the only one whose exit code could not tell a fired andon
    from a crash, in the tool whose whole purpose is to be looked at before a credit is
    spent.
    """

    gate = "PREVIEW"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=0.5, help="fraction of shot resolution")
    return ap.parse_args(argv)


def resolve_camera(spec, bounds, width, height):
    """`camera.target` and `camera.radius`, resolved the way `stage_render` resolves them.

    MEASURED 2026-09-04: this file used to re-derive both fields two lines apart --
    `Vector((0, 0, 0))` for the `bbox_center` sentinel and a bare `float(c["radius"])` --
    while `stage_render.BlenderBackend.prepare` resolves the sentinel to the MEASURED bbox
    centre and handles `"auto"` through `blender_scene.auto_radius`. Both are the shotspec
    DEFAULTS (`shotspec.DEFAULTS["camera"]`), so this was the default path, not an edge
    case: `specs/E01-anchor.json` and `specs/E02-control-blackguard.json` aimed the preview
    at the world origin and then raised `ValueError: could not convert string to float:
    'auto'`. The module docstring's claim -- "one implementation, so the preview cannot
    drift from the render" -- is now true of the arithmetic rather than of the intent.

    `bounds` is `blender_scene.world_bounds`'s triple; `width`/`height` are the SHOT
    resolution, not the scaled preview, because that is what the render solves against.
    """
    c = spec["camera"]
    center, _half, sphere_r = bounds
    if c["target"] == "bbox_center":
        target = tuple(float(v) for v in center)
        target_source = "measured bbox centre"
    else:
        target = tuple(float(v) for v in c["target"])
        target_source = "spec.camera.target (pinned)"

    radius = c["radius"]
    if radius == "auto":
        radius = blender_scene.auto_radius(sphere_r, c["lens_mm"], c["sensor_mm"],
                                           width, height, c["fit_margin"])
        radius_source = "auto (fitted to the subject's bounding sphere)"
    else:
        radius_source = "spec.camera.radius (pinned)"
    return {"target": target, "target_source": target_source,
            "radius": float(radius), "radius_source": radius_source}


def main():
    a = parse_args()
    spec = shotspec.load_spec(a.spec)

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
    # Same filter as `stage_render.py:138` and `render_start_frame.py:435`: the floor's
    # height is a MEASUREMENT of the subject, and the glTF importer's hidden radius-1.0
    # Icosphere sits at the origin, so an unfiltered `min(zs)` drops the floor a metre
    # below a character standing on it -- in the one preview whose purpose is showing a
    # foot sinking through the ground.
    subject = blender_scene.render_visible_meshes(scene, meshes)
    if not subject:
        raise PreviewWalkGate(
            f"{asset} imported {len(meshes)} mesh object(s) and none is render-visible "
            f"({[o.name for o in meshes]}); there is nothing to preview",
            {"asset": asset, "mesh_objects_all": [o.name for o in meshes],
             "mesh_objects_render_visible": []})
    zs = [(o.matrix_world @ Vector(c)).z for o in subject for c in o.bound_box]
    gob.location = (0.0, 0.0, min(zs))

    c = spec["camera"]
    bounds = (blender_scene.world_bounds_over_frames(scene, subject, count)
              if spec["subject"]["animation"] == "per_frame"
              else blender_scene.world_bounds(subject, scene=scene))
    if bounds is None:
        raise PreviewWalkGate(
            f"{asset} has no evaluated geometry to frame",
            {"asset": asset, "subject": [o.name for o in subject],
             "animation": spec["subject"]["animation"], "frames": count})

    # Every refusal above this line can fire before a single pixel exists; the output
    # directory is created HERE so a halt does not leave an empty one behind for a later
    # run to read as a used one (F-8d2b9d7d). Nothing between the old site and this one
    # writes.
    os.makedirs(a.out, exist_ok=True)          # scripts create their own output directories
    cam_solution = resolve_camera(spec, bounds, int(spec["resolution"]["width"]),
                                  int(spec["resolution"]["height"]))
    target = Vector(cam_solution["target"])
    radius = cam_solution["radius"]
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

    # The population is the PLAN, not whatever is in the directory. A bare
    # `listdir(...*.png)` counts strays as successes and cannot say WHICH frame is missing;
    # `shotspec.frame_names` is the same list the render writes against.
    planned = shotspec.frame_names(count, "png")
    missing = [f for f in planned if not os.path.isfile(os.path.join(a.out, f))]
    empty = [f for f in planned
             if f not in missing and os.path.getsize(os.path.join(a.out, f)) == 0]
    # The SAME population as `render_performer.py`'s (F-ffdb6d4d): `.png`
    # case-insensitively, minus the plan. This took the whole listing with no suffix
    # filter at all, so the two renderers reported different things about the same kind
    # of directory. A diagnostic in both: `strays` gates nothing.
    strays = sorted(f for f in os.listdir(a.out)
                    if f.lower().endswith(".png") and f not in set(planned))
    if missing or empty:
        raise PreviewWalkGate(
            f"the preview is not complete: {len(missing)} of {count} frames were never "
            f"written {missing[:8]} and {len(empty)} are zero bytes {empty[:8]}",
            {"out": os.path.abspath(a.out), "planned": count,
             "missing": missing, "empty": empty, "unexpected_files_in_out_dir": strays})
    print("PREVIEW_WALK_OK " + json.dumps({
        "tool": "preview_walk", "blender": blender_scene.blender_provenance(),
        "out": os.path.abspath(a.out), "frames": len(planned), "resolution": [w, h],
        "unexpected_files_in_out_dir": strays,
        "unexpected_files_rule": (
            "every file in --out whose name ends in .png, compared case-INSENSITIVELY, "
            "that the plan did not name. A DIAGNOSTIC: it gates nothing, and a stray "
            "cannot make the frame-completeness check pass or fail. The sibling renderer "
            "render_performer.py derives the same population"),
        "asset": asset, "asset_sha256": sha, "camera_position": [round(v, 6) for v in pos],
        "camera_target": [round(v, 6) for v in cam_solution["target"]],
        "camera_target_source": cam_solution["target_source"],
        "camera_radius": round(cam_solution["radius"], 6),
        "camera_radius_source": cam_solution["radius_source"],
        "subject_render_visible": [o.name for o in subject],
        "subject_excluded_not_render_visible": [o.name for o in meshes
                                                if o not in subject],
        "import": info}))
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
            "tool": "preview_walk", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "preview_walk", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("PREVIEW_WALK_HALT " + _line)
            sys.exit(_code)
