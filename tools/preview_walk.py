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

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is writing one PNG per planned frame under `--out`.
Compensator: delete `--out`; owner: the executor session. Every frame path is
composed from `--out` and `shotspec.frame_names`' fixed `%05d.png` stem, so no
operator-supplied name component can carry a frame outside the directory the
compensator names. The GLB and the shot spec are opened read-only.

Named because CLAUDE.md's workflow standard 3 (NAMED_COMPENSATORS -- Sagas,
Garcia-Molina & Salem, SIGMOD 1987) takes NO skip, and because the ordering makes the
question ordinary rather than exotic: `_census_nodes.refusal_and_write_lines`, run over
the 21 Blender-side tools, finds 15 modules with at least one refusal BELOW the first
write, so a halt after the first write is the common case (F-6e1a9d54, wave 25).
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from armature_core import blender_scene, framing, parts, shotspec  # noqa: E402
# F-a2630f86: `render_target_snapshot` / `require_render_target_moved` are
# `export_target_snapshot`'s twins and live beside it. The idiom is
# `rig_bake`'s and `make_parts_sheet`'s -- one implementation, imported.
import rig_character as rc  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
# CARRIED, not copied (the `render_turnaround` idiom, F-267361f5): the repo has ONE bound on
# a frame that reaches `scene.render.resolution_x` and ONE bound on a fraction of a shot,
# both in the sibling renderer. This is their third caller. Stage B: they belong in
# `armature_core.startframe`.
from render_start_frame import require_frame_size, require_shot_fraction  # noqa: E402
# Control/performer plate — ONE name with render_turnaround (F-cade389c).
from render_turnaround import WORLD_LINEAR  # noqa: E402
from render_performer import (  # noqa: E402
    maybe_run_review_clip, review_clip_next, load_camera_path)


#: The engine identifiers this tool will accept, in the order it tries them.
#:
#: WAVE 14, F-0bf74152. This module pinned the single literal `'BLENDER_EEVEE'`. The
#: candidate list exists in the four SHEET tools precisely because that identifier is not
#: stable across Blender versions, and their `except TypeError: continue` is this repo's own
#: recorded evidence that an invalid enum name RAISES rather than being ignored -- so on a
#: Blender where the other spelling is the live one, the diagnostic sheets kept working and
#: the four tools whose pixels become control sequences and reference stacks died with an
#: untyped `TypeError`, recorded by the halt contract as "FAILED - an unhandled error" at
#: exit 1 naming a bpy property assignment. The order is the sheets' order, so a sheet and
#: a render made beside each other cannot be drawn by different engines.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")


def select_engine(scene, candidates=ENGINE_CANDIDATES):
    """Set the render engine and RETURN the one actually set, else raise.

    Carried from `preview_glb.select_engine` (F-bba38f1c) rather than reinvented: the loop
    has an `else` branch, because a loop that completes without setting anything leaves the
    render on whatever the factory settings put there with no field in any record able to
    say so. `armature_core.blender_scene` is where the one implementation belongs and is
    outside this domain's globs, so the lift is FILED, not done.
    """
    for eng in candidates:
        try:
            scene.render.engine = eng
        except TypeError:
            continue
        return eng
    raise PreviewWalkGate(
        "none of the candidate render engines is valid on this Blender, so the render "
        "would be drawn by whatever the factory settings left in place",
        {"clause": "engine", "candidates": list(candidates),
         "blender": bpy.app.version_string})


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


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/preview_walk.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True,
                    help="the SHOT SPEC json -- the same camera, frames and fps the paid "
                         "control sequence is rendered at; read only")
    ap.add_argument("--out", required=True,
                    help="the directory the shaded preview frames are written into. "
                         "Compensator: delete it; owner: the executor session")
    ap.add_argument("--scale", type=float, default=0.5, help="fraction of shot resolution")
    ap.add_argument("--review-clip", action="store_true",
                    help="after frames gate green, shell make_review_clip on --out "
                         "(F-cee7b569). Absent: PREVIEW_WALK_OK still carries next:")
    ap.add_argument("--camera-path", default=None,
                    help="optional keyframed orbit JSON (F-82f88f23); default shot-spec camera")
    return ap.parse_args(argv)


def preview_frame(shot_width, shot_height, scale):
    """`(w, h)` for the preview, refused by name before any of it reaches the scene.

    F-3990e197, wave 22. `--scale` was a bare `type=float, default=0.5` with no bound
    anywhere; it was read into the frame at `w = int(round(spec["resolution"]["width"] *
    a.scale))` and assigned straight to `scene.render.resolution_x`. MEASURED on the repo
    venv over an 832x480 shot: `--scale=nan` raises a bare `ValueError: cannot convert
    float NaN to integer`; `--scale=inf` a bare `OverflowError`; both are recorded by this
    tool's halt contract as "FAILED — an unhandled error" at exit 1, on the tool whose
    stated purpose (module docstring, line 9) is to be looked at BEFORE a credit is spent.
    `--scale=0` yields `(0, 0)`, `--scale=-0.5` yields `(-416, -240)` and `--scale=1e6`
    yields `(832000000, 480000000)` — all three silent, all three assigned.

    THREE bounds, on three different quantities, and each is asked by the one implementation
    that already owns it rather than by a fourth copy of `math.isfinite`:

    * **The flag is a FRACTION of the shot** — its own `help` string says so — so it goes
      through `require_shot_fraction`, the repo's bound on exactly that (`0 < f <= 1`,
      finiteness through `parts.require_finite`). That refuses nan, inf, 0, -0.5 and 1e6 by
      name, at the flag, with the operand in the evidence.
    * **The SHOT's own resolution** goes through `require_frame_size`, the same bound the
      two sibling renderers put on the frame that conditions a generation — this is the
      same quantity, read out of the spec instead of off a flag, and this is that bound's
      third caller.
    * **The derived preview frame** can still collapse to zero from a legal fraction
      (`--scale=1e-9` on a 480-wide shot rounds to 0), and neither bound above can see
      that: it is a property of the PRODUCT. So it gets its own named clause here, above
      the assignment. The generator-bucket clause deliberately does NOT ride this one — the
      preview is never submitted and never conditions a generation, and 480x832 admits only
      `--scale` of 0.5 and 1.0 under a divisor of 16, so imposing it would refuse correct
      work, which is the failure `parts.tightened`'s docstring records.
    """
    who = "preview_walk"
    shot_w, shot_h = require_frame_size(
        int(shot_width), int(shot_height), who=who,
        module_frame=(int(shot_width), int(shot_height)),
        gate=PreviewWalkGate, gate_id="PREVIEW_SHOT_FRAME")
    s = require_shot_fraction("--scale", scale, who=who, gate=PreviewWalkGate,
                              gate_id="PREVIEW_SCALE")
    w, h = int(round(shot_w * s)), int(round(shot_h * s))
    collapsed = [n for n, v in (("width", w), ("height", h)) if v <= 0]
    if collapsed:
        raise PreviewWalkGate(
            f"--scale={s!r} of the {shot_w}x{shot_h} shot rounds to {w}x{h}: "
            f"{' and '.join(collapsed)} is not a positive number of pixels. A zero "
            f"dimension is assigned to scene.render.resolution_x and the preview this "
            f"tool exists to have LOOKED at cannot be drawn at all",
            {"gate": PreviewWalkGate.gate, "sub_gate": "PREVIEW_SCALE",
             "andon": PreviewWalkGate.__name__, "who": who, "flag": "--scale",
             "clause": "preview_frame_collapsed", "scale": s,
             "shot": [shot_w, shot_h], "preview": [w, h], "collapsed": collapsed})
    return w, h


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
    # BOUNDED where it is READ, and above every assignment — F-3990e197. See
    # `preview_frame` for the three quantities and why the generator-bucket clause is on
    # the shot's resolution and not on the preview's.
    w, h = preview_frame(spec["resolution"]["width"], spec["resolution"]["height"],
                         a.scale)

    # fps FIRST, on an empty scene, before the import. glTF key times are seconds.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, fps)
    asset, sha = shotspec.resolve_asset(spec)
    meshes, arms, info = blender_scene.import_glb(asset, expected_fps=fps)

    engine = select_engine(scene)
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    scene.frame_start, scene.frame_end = 1, count

    world = bpy.data.worlds.new("preview")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (*WORLD_LINEAR, 1.0)

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
            {"clause": "asset_has_no_render_visible_mesh",
             "asset": asset, "mesh_objects_all": [o.name for o in meshes],
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
            {"clause": "asset_has_no_evaluated_geometry",
             "asset": asset, "subject": [o.name for o in subject],
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
        frame_path = os.path.join(a.out, f"{i:05d}.png")
        _before = rc.render_target_snapshot(frame_path)
        scene.render.filepath = frame_path
        render_result = bpy.ops.render.render(write_still=True)
        # WAVE 14, F-6a9a0f72: the render operator's STATUS SET, read. The existence and
        # size checks below are properties a PREVIOUS run's file at the same path satisfies;
        # only the operator's own verdict says whether THIS call drew anything. Shape carried
        # from `rig_bake.py`'s `if 'FINISHED' not in result`.
        _status = _render_status(render_result)
        if "FINISHED" not in _status:
            raise PreviewWalkGate(
                f"the render operator did not report FINISHED for "
                f"{os.path.basename(frame_path)}; it returned {_status!r}, and any file at "
                f"that path is then the previous run's",
                {"clause": "operator_status", "status": _status,
                 "path": os.path.abspath(frame_path),
                 # F-d6042cf6: where the partial run is, and its named undo.
                 "out": os.path.dirname(os.path.abspath(frame_path)),
                 "compensator": "delete --out; owner: the executor session"})
        rc.require_render_target_moved(
            frame_path, _before, PreviewWalkGate,
            {"gate": PreviewWalkGate.gate, "sub_gate": "RENDER_TARGET",
             "who": "preview_walk"})


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
            {"clause": "preview_is_incomplete", "out": os.path.abspath(a.out), "planned": count,
             "missing": missing, "empty": empty, "unexpected_files_in_out_dir": strays,
             "compensator": "delete --out; owner: the executor session"})
    review = maybe_run_review_clip(
        a.out, enabled=bool(getattr(a, "review_clip", False)))
    if not review.get("ran"):
        review = dict(review_clip_next(a.out), ran=False,
                      reason=review.get("reason", "--review-clip not set"))
    print("PREVIEW_WALK_OK " + json.dumps({
        "tool": "preview_walk", "blender": blender_scene.blender_provenance(),
        "out": os.path.abspath(a.out), "frames": len(planned), "resolution": [w, h],
        "next": review.get("next"),
        "review_clip": review,
        # the engine ACTUALLY set, from `select_engine`'s return (F-0bf74152) -- never a
        # literal, because the identifier this tool used to pin is not stable across
        # Blender versions and no field in this record could have revealed a substitution.
        "engine": engine,
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
    # WAVE 22, F-897a3329: the VALUE clause, beside the key clause this walk was written
    # for. `json.dumps`'s `default=` applies to values Python cannot encode, never to a
    # float it CAN, and `allow_nan` defaults True -- so a non-finite operand that
    # `armature_core.parts.require_finite` wrote into the evidence (`ev[name] = v`)
    # reached the halt line as the bare token `NaN`. MEASURED end-to-end on `e8263a3`:
    # a sentinel of that shape serialises to `{"evidence": {"max_displacement": NaN}}`;
    # `json.loads(payload)` ACCEPTS it -- which is why every reader in this suite was
    # green -- and `json.loads(payload, parse_constant=<raise>)` REJECTS it naming the
    # constant, as would JS `JSON.parse`, Go `encoding/json` and serde. The halt contract
    # promises "stdout EXACTLY ONE line `<STEM>_HALT <json object>`", and for exactly the
    # refusal family wave 16 added -- the NaN andons -- the object was not JSON.
    #
    # The operand stays READABLE: `repr` gives "nan" / "inf" / "-inf", which is the same
    # text `require_finite`'s own message carries, rather than a null that erases which
    # non-finite value it was. `json.dumps(..., allow_nan=False)` below then cannot raise,
    # so the guard around the sentinel keeps its meaning.
    if isinstance(value, float) and (value != value
                                     or value in (float("inf"), float("-inf"))):
        return repr(value)
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
            # `allow_nan=False` (F-897a3329): strict JSON, and it cannot raise here because
            # `_halt_keysafe` above has already replaced every non-finite float with its repr.
            _line = json.dumps(_sentinel, default=str, allow_nan=False)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("PREVIEW_WALK_HALT " + _line)
            sys.exit(_code)
