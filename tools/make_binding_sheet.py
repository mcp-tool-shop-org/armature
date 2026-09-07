"""make_binding_sheet — arm (a) beside arm (b), for the Director's eye to pick the binding.

    blender -b --factory-startup -P tools\\make_binding_sheet.py -- --a=<glb> --a-label=... --b=<glb> --b-label=... --out=<dir>
    <venv-python> tools\\sheet_compose.py <dir>\\panels.json

`rest | arc frames | 1:1 joint insets`, the two bindings on adjacent rows at identical
cameras. Rendered from the terracotta body with material and light; **no skeleton overlay**,
because the judgement here is what the deform does to him, and a bone drawn over the surface
hides exactly the region being judged. No gate states are printed and no debug text.

**The insets are framed on the POSED BONE position at the last frame, read from the armature
rather than from either mesh.** Both arms carry the same authored action on the same skeleton,
so that point is identical in both — which makes the camera identical and lets a difference in
where the *body* actually ends up read as the difference it is. Framing on each arm's own mesh
would move the camera with the defect and hide it.

**The arc is checked, not assumed.** If a re-imported GLB comes back with the mesh identical at
frame 1 and frame 33, the sheet would show two matching panels and read as "this binding does
not move" when the truth is that the action did not survive the round trip. That is E03's
Ruling 9 failure with the axes swapped, so it raises here instead.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is writing the rendered panels under `--out/frames` and
one `panels.json` under `--out`. Compensator: delete `--out`; owner: the executor
session. Every path it writes is composed from `--out` and a fixed literal, so no
operator-supplied name component can carry a panel outside the directory the
compensator names. Both GLBs are opened read-only.

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
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import rig_character  # noqa: E402
from armature_core import blender_scene  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
from render_performer import maybe_compose_panels  # noqa: E402
from make_parts_sheet import (ArcDidNotSurvive, arc_liveness,        # noqa: E402,F401
                              articulated_side, CLAY_STUDIO_LINEAR, side_word)

FULL_W, FULL_H = 780, 1180
INSET = 560
INSET_HEIGHT_FRACTION = 0.24
ARC_FRAMES = (17, rig_character.PROBE_FRAMES)
#: `(panel label, joint)` -- the SIDE is appended at run time from `articulated_side`,
#: never pinned here.
INSET_JOINTS = (("shoulder", "shoulder"), ("elbow", "elbow"),
                ("hand", "wrist"), ("hip", "hip"))


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


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/make_binding_sheet.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--a", required=True,
                   help="arm (a): the first bound GLB, drawn on the TOP row; read only")
    p.add_argument("--a-label", default="(a)",
                   help="the caption under the top row (default \"(a)\") -- it is what the "
                        "Director reads to know which binding he is looking at")
    p.add_argument("--b", required=True,
                   help="arm (b): the second bound GLB, drawn on the BOTTOM row at the "
                        "SAME cameras as (a); read only")
    p.add_argument("--b-label", default="(b)", help="the caption under the bottom row "
                                                    "(default \"(b)\")")
    p.add_argument("--out", required=True,
                   help="the directory panels.json and its frames are written into; "
                        "`sheet_compose.py <out>/panels.json` composes the sheet. "
                        "Compensator: delete it; owner: the executor session")
    p.add_argument("--compose", dest="compose", action="store_true", default=True,
                   help="after panels.json is valid, spawn sheet_compose (default; F-938485d6)")
    p.add_argument("--no-compose", dest="compose", action="store_false",
                   help="stop after panels.json; operator runs sheet_compose by hand")
    return p.parse_args(argv)


#: The engine identifiers this tool will accept, in the order it tries them. One order
#: across `make_skeleton_sheet`, `make_binding_sheet`, `make_parts_sheet` and
#: `preview_glb` -- `preview_glb` used to try them the other way round.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")


class BindingSheetGate(GateFailure):
    """The sheet cannot be composed reproducibly."""

    gate = "BINDING_SHEET"


def light_the_scene(scene):
    """Light the sheet, and RETURN the render engine actually set.

    MEASURED 2026-09-04 (F-bba38f1c): this loop had no `else`, so if a future Blender
    renamed both identifiers the `for` would complete normally, nothing would be set, and
    the sheet would render on whatever the factory settings left in place -- with no field
    in `panels.json` able to reveal it. Four copies of the loop existed and `preview_glb`
    tried the two names in the OPPOSITE order, so on a Blender where both are valid the
    preview and the sheets did not agree on which engine drew them. One order now, and the
    engine that was set is written into the record.
    """
    engine = None
    for eng in ENGINE_CANDIDATES:
        try:
            scene.render.engine = eng
        except TypeError:
            continue
        engine = eng
        break
    if engine is None:
        raise BindingSheetGate(
            "none of the candidate render engines is valid on this Blender, so the sheet "
            "would be drawn by whatever the factory settings left in place",
            {"clause": "no_valid_render_engine",
             "candidates": list(ENGINE_CANDIDATES),
             "blender": bpy.app.version_string})
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*CLAY_STUDIO_LINEAR, 1.0)
    bg.inputs[1].default_value = 1.0
    for name, energy, rot in (("key", 3.4, (52, 0, 26)), ("fill", 1.3, (62, 0, -134)),
                              ("rim", 2.1, (74, 0, 178))):
        data = bpy.data.lights.new(name, type="SUN")
        data.energy = energy
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.rotation_euler = tuple(math.radians(a) for a in rot)
    return engine


def ortho_camera(scene, name, target, ortho_scale, res, azim_deg=0.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    a = math.radians(azim_deg)
    cam.location = Vector(target) + Vector((6.0 * math.sin(a), -6.0 * math.cos(a), 0.0))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100


def shoot(scene, path):
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    # WAVE 25, F-c05e8b32 (ground F-4925f60f, moved) -- THE PRE-RENDER SNAPSHOT, at the
    # sheet tools the wave-22 enumeration dropped. Wave 22 added
    # `rig_character.render_target_snapshot` / `require_render_target_moved` and adopted
    # them at the FIVE renderers; the wave-21 re-sighting's list of render write sites
    # stopped before the three sheets. Re-counted in this worktree:
    # `scene.render.filepath` assignments / snapshots / moved-checks per owned module --
    # preview_glb 2/3/1, preview_walk 1/2/2, render_performer 2/3/3,
    # render_start_frame 6/7/7, render_turnaround 2/2/2, and make_binding_sheet 1/0/0,
    # make_parts_sheet 1/0/0, make_skeleton_sheet 1/0/0.
    #
    # The comment below states the premise itself -- the existence and size clauses are
    # properties a PREVIOUS run's file at the same path satisfies -- and no clause
    # measured the target before the write, on the artefact the Director approves the
    # skeleton at. Consequence stays bounded as the ground row framed it: no realistic
    # FINISHED-without-write was constructed on this rig. The home is ADOPTED, not
    # respelled.
    _before = rig_character.render_target_snapshot(path)
    scene.render.filepath = path
    render_result = bpy.ops.render.render(write_still=True)
    # WAVE 14, F-6a9a0f72: the render operator's STATUS SET, read. The existence and
    # size checks below are properties a PREVIOUS run's file at the same path satisfies;
    # only the operator's own verdict says whether THIS call drew anything. Shape carried
    # from `rig_bake.py`'s `if 'FINISHED' not in result`.
    _status = _render_status(render_result)
    if "FINISHED" not in _status:
        raise BindingSheetGate(
            f"the render operator did not report FINISHED for "
            f"{os.path.basename(path)}; it returned {_status!r}, and any file at "
            f"that path is then the previous run's",
            {"clause": "operator_status", "status": _status,
             "path": os.path.abspath(path),
             # F-d6042cf6: where the partial run is, and its named undo.
             "out": os.path.dirname(os.path.abspath(path)),
             "compensator": "delete --out; owner: the executor session"})
    # THE WRITER VERIFIES ITS OWN OUTPUT (F-51c5e0ef). `bpy.ops.render.render` returns
    # an operator status set and can return `{'CANCELLED'}` WITHOUT raising; this
    # function discarded it, and no code path in this tool ever opened a rendered file
    # again -- so `panels.json` was a manifest of paths that may not exist, printed
    # under a success sentinel, and a stale file left at the path by an earlier run put
    # the previous run's panel into the sheet the Director is asked to approve. The
    # shape is `preview_walk.py:196-206`'s, carried here rather than reinvented.
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise BindingSheetGate(
            f"the render operator returned without writing "
            f"{os.path.basename(path)}; the panel does not exist or is zero bytes, and "
            f"the sheet would name a file that is not there",
            {"clause": "render_wrote_nothing", "path": os.path.abspath(path),
             "exists": os.path.isfile(path),
             "bytes": os.path.getsize(path) if os.path.isfile(path) else None})
    rig_character.require_render_target_moved(
        path, _before, BindingSheetGate,
        {"gate": BindingSheetGate.gate, "sub_gate": "RENDER_TARGET",
         "who": "make_binding_sheet"},
        what="the sheet panel")
    return path


def load(glb):
    scene = rig_character.fresh_scene(rig_character.PROBE_FPS)
    _import = bpy.ops.import_scene.gltf(filepath=glb)
    rig_character.require_import_status(_import, glb, BindingSheetGate,
                                       {"who": "make_binding_sheet"})
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1:
        raise BindingSheetGate(
            f"{glb}: {len(visible)} render-visible mesh objects {[o.name for o in visible]}; "
            f"the sheet cannot decide which one is the character",
            {"clause": "subject_is_not_one_render_visible_mesh", "andon": "ArmatureError",
             "glb": glb, "render_visible": [o.name for o in visible],
             "all_meshes": [o.name for o in meshes]})
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise BindingSheetGate(f"{glb}: expected one armature, found {len(arms)}",
            {"clause": "subject_is_not_one_armature", "andon": "ArmatureError",
             "glb": glb, "armatures": [o.name for o in arms]})
    return scene, visible[0], arms[0]


def evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        return rig_character.world_verts(ev, me)
    finally:
        ev.to_mesh_clear()


def render_arm(glb, tag, out_dir, targets=None):
    scene, mesh_obj, arm_obj = load(glb)
    engine = light_the_scene(scene)

    source = rig_character.world_verts(mesh_obj)
    lo, hi = source.min(axis=0), source.max(axis=0)
    height = float(hi[2] - lo[2])
    centre = Vector(((lo + hi) / 2.0).tolist())

    scene.frame_set(1)
    bpy.context.view_layer.update()
    at_rest = evaluated(mesh_obj)
    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()
    at_end = evaluated(mesh_obj)
    # ONE implementation of the MEASUREMENT and the BOUND (`make_parts_sheet.arc_liveness`,
    # wave 16, F-4dc96644 + F-8958f574), beside the staging triple and `articulated_side`
    # this module already imports from there; the refusal stays here, in this sheet's own
    # words. It refuses a non-finite displacement -- a NaN in the POSED array made `moved`
    # NaN, every clause False, and `max_vertex_motion: NaN` was published -- and it derives
    # the floor as a fraction of the subject's OWN bbox diagonal instead of the 1e-6 metres
    # that used to stand here, whose only justification was that it is small.
    arc, _diagonal, _slo, _shi = arc_liveness(
        float(np.linalg.norm(at_end - at_rest, axis=1).max()),
        "max_vertex_motion", at_rest, "make_binding_sheet")
    if arc["max_vertex_motion"] <= arc["floor"]:
        raise ArcDidNotSurvive(
            f"{glb}: the mesh is identical at frame 1 and frame "
            f"{rig_character.PROBE_FRAMES} (max {arc['max_vertex_motion']:.3e}, "
            f"{arc['displacement_over_diagonal']:.3e} of this subject's own bbox diagonal "
            f"{arc['bbox_diagonal']:.6f}). The authored arc did not survive the round "
            f"trip, and a sheet built from this would show two matching panels and read "
            f"as 'this binding does not move'",
            dict(arc, glb=glb, tag=tag))

    # The posed bone positions at the last frame — identical across arms, so both rows share
    # one camera per joint. Computed from the FIRST arm and passed to the second.
    # Which arm the arc moves is MEASURED, not pinned: `rig_character.author_probe` binds
    # the probe to the +X side, and which of this character's arms that is comes out of
    # `landmarks.facing`. ONE implementation, imported from `make_parts_sheet` beside the
    # staging triple.
    side_rec = articulated_side(arm_obj, scene, 1, rig_character.PROBE_FRAMES)
    if targets is None:
        targets = {}
        for label, joint in INSET_JOINTS:
            bone = f"{joint}.{side_rec['side']}"
            targets[label] = tuple(arm_obj.matrix_world @ arm_obj.pose.bones[bone].head)

    full_scale = height * 1.10
    inset_scale = height * INSET_HEIGHT_FRACTION
    out = {"targets": targets, "max_displacement": arc["max_vertex_motion"],
           "arc": arc,
           "articulated_side": side_rec, "panels": {}}

    for frame in (1,) + tuple(ARC_FRAMES):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        ortho_camera(scene, f"cam_{tag}_f{frame}", centre, full_scale, (FULL_W, FULL_H))
        out["panels"][f"f{frame}"] = shoot(
            scene, os.path.join(out_dir, f"{tag}_f{frame:02d}.png"))

    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()
    for label, _ in INSET_JOINTS:
        ortho_camera(scene, f"cam_{tag}_{label}", Vector(targets[label]), inset_scale,
                     (INSET, INSET))
        out["panels"][f"inset_{label}"] = shoot(
            scene, os.path.join(out_dir, f"{tag}_inset_{label}.png"))
    return out


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    frames = os.path.join(out, "frames")
    os.makedirs(frames, exist_ok=True)

    a = render_arm(args.a, "a", frames)
    b = render_arm(args.b, "b", frames, targets=a["targets"])

    last = rig_character.PROBE_FRAMES
    spec = {
        "tool": "make_binding_sheet",
        "blender": blender_scene.blender_provenance(),
        "engine": engine,
        "out": out,
        "filename": "E07-binding-comparison.png",
        "title": "E07 — the two bindings, for the Director's eye",
        "subtitle": (f"(a) {args.a_label}   ·   (b) {args.b_label}   ·   the arc is E03's: "
                     f"the character's {a['articulated_side']['side_word']} arm, "
                     f"0°→90° about +Y, {last} keys at 16 fps   ·   "
                     f"insets are 1:1 at frame {last}, identical camera in both rows"),
        "articulated_side": {"a": a["articulated_side"], "b": b["articulated_side"]},
        "rows": [
            {"title": "Rest pose — frame 1",
             "panels": [{"body": a["panels"]["f1"], "label": f"(a) {args.a_label}"},
                        {"body": b["panels"]["f1"], "label": f"(b) {args.b_label}"}]},
            {"title": f"The arc — frames {ARC_FRAMES[0]} and {ARC_FRAMES[1]}",
             "panels": [{"body": a["panels"][f"f{ARC_FRAMES[0]}"],
                         "label": f"(a) frame {ARC_FRAMES[0]}"},
                        {"body": a["panels"][f"f{ARC_FRAMES[1]}"],
                         "label": f"(a) frame {ARC_FRAMES[1]}"},
                        {"body": b["panels"][f"f{ARC_FRAMES[0]}"],
                         "label": f"(b) frame {ARC_FRAMES[0]}"},
                        {"body": b["panels"][f"f{ARC_FRAMES[1]}"],
                         "label": f"(b) frame {ARC_FRAMES[1]}"}]},
            {"title": f"(a) {args.a_label} — at 1:1, frame {last}",
             "panels": [{"body": a["panels"][f"inset_{n}"], "label": n}
                        for n, _ in INSET_JOINTS]},
            {"title": f"(b) {args.b_label} — at 1:1, frame {last}",
             "panels": [{"body": b["panels"][f"inset_{n}"], "label": n}
                        for n, _ in INSET_JOINTS]},
        ],
    }
    path = os.path.join(out, "panels.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    compose_rec = maybe_compose_panels(path, compose=bool(getattr(args, "compose", True)))
    print("MAKE_BINDING_SHEET_OK " + json.dumps(
        {"panels": path, "sheet": compose_rec.get("sheet"),
         "compose": compose_rec,
         "a_max_displacement": a["max_displacement"],
         "b_max_displacement": b["max_displacement"]}))


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

        from armature_core.errors import ArmatureError, GateFailure
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
            "tool": "make_binding_sheet", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "make_binding_sheet", "outcome": _outcome,
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
            print("MAKE_BINDING_SHEET_HALT " + _line)
            sys.exit(_code)
