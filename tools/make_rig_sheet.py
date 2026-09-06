"""The arm (d) comparison sheet — a SKINNED figure, judged beside the mesh it replaced.

``make_parts_sheet`` cannot serve here and its refusal was correct rather than a nuisance: it
compares **part object transforms**, which is how a rigid-parts rig moves. A skinned figure
has one object that never moves; the motion lives in evaluated vertex positions. Pointed at a
skinned GLB it reports "the parts are identical at frame 1 and frame 33" and declines to draw.
Rather than loosen that check, this tool makes the same assertion against the thing that
actually moves here.

Inset cameras are aimed from the **posed bone positions read out of the armature**, not from
guessed fractions of the figure's height. Arm (d)'s first comparison sheet framed the "mitten
hand" panel on a forearm and a shin, which is a sheet that cannot answer the question it was
built to ask.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is writing the rendered panels under `--out/panels` and
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
from __future__ import annotations

import argparse
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_character as rc                                            # noqa: E402
from armature_core import blender_scene                               # noqa: E402
from armature_core.errors import ArmatureError                        # noqa: E402
from make_parts_sheet import (ArcDidNotSurvive, arc_liveness,         # noqa: E402
                              articulated_side, light_the_scene,
                              ortho_camera, shoot)


class RigSheetSubjectError(ArmatureError):
    """A panel's subject cannot be identified without guessing which mesh it is.

    Wave 25, F-3b71c0aa. The reference import, the skinned mesh and the armature each
    refused through the family BASE with no evidence; each names this class and its own
    `clause` now. `ReferenceFileError` above stays what it is -- `--reference` naming an
    unreadable file -- so the two refusals a reader has to tell apart are two classes."""


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/make_rig_sheet.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--glb", required=True, help="the skinned, animated GLB")
    p.add_argument("--reference", required=True, help="the ORIGINAL textured GLB")
    p.add_argument("--out", required=True,
                   help="the directory panels.json and its panels are written into; "
                        "`sheet_compose.py <out>/panels.json` composes the sheet. "
                        "Compensator: delete it; owner: the executor session")
    p.add_argument("--title", default="E07 arm (d) — retopologised, baked, bone-heat bound",
                   help="the sheet's heading, as the Director reads it (default names "
                        "E07 arm (d))")
    p.add_argument("--after-label", default=None,
                   help="what the AFTER column actually is. Derived from the mesh when "
                        "omitted -- a hard-coded label outlived its route once already and "
                        "described a 4096 bake on a mesh that was never baked.")
    return vars(p.parse_args(argv))


def evaluated(ob, depsgraph):
    ev = ob.evaluated_get(depsgraph)
    me = ev.to_mesh()
    v = np.array([list(ob.matrix_world @ x.co) for x in me.vertices])
    ev.to_mesh_clear()
    return v


class ReferenceFileError(ArmatureError):
    """`--reference` does not name a readable file. A plain refusal (gate None + andon + clause): the
    path is known at parse time and nothing has been written. WAVE-14 MERGE (coordinator, 2026-09-04, after #159/#160 and receipt #287): named because
    instruments-measure's census over tools/** refuses a BASE `ArmatureError` raised with an evidence
    argument (the wave-14 rule is a named subclass with a clause) — the coordinator's previous cut had
    added the evidence to the base."""


def require_reference_file(path):
    """`--reference` names a readable file, refused BEFORE anything is written.

    F-4db23b72, wave 14. `import_reference` was the one refusal this module stranded below
    its first write (`os.makedirs(out_dir)`), and its argument is a path known at PARSE
    time -- it does not read, and cannot read, anything the seven panels between the two
    wrote. What a run naming a missing or unreadable `--reference` actually left behind was
    `<out>/panels/` holding three figure frames and four joint insets, no `panels.json` and
    no sheet: a half-built approval artifact rather than a refusal. The Blender import
    stays where it is; only the clause that never needed a scene moves up.
    """
    if not os.path.isfile(path):
        # WAVE-14 MERGE (coordinator, 2026-09-04, after #159): the refusal carries the plain-refusal receipt
        # (gate None + andon + clause) like every other wave-14 refusal; it was a bare base raise.
        raise ReferenceFileError(
            f"--reference={path!r} is not a file. It is the ORIGINAL textured GLB the "
            f"texture-fidelity row is built from, and it is named on the command line, so "
            f"this is refused before the output directory exists rather than after seven "
            f"panels have been rendered into it",
            {"gate": None, "andon": "ReferenceFileError", "clause": "reference_not_a_file",
             "path": path})
    try:
        with open(path, "rb") as fh:
            fh.read(1)
    except OSError as exc:
        raise ReferenceFileError(
            f"--reference={path!r} cannot be read: {exc}",
            {"gate": None, "andon": "ReferenceFileError", "clause": "reference_unreadable",
             "path": path, "error": type(exc).__name__}) from exc
    return os.path.abspath(path)


def import_reference(path, scene, skinned):
    """The ONE render-visible mesh the reference import adds.

    MEASURED 2026-09-04. The superseded line was

        ref = [o for o in bpy.data.objects if o.type == "MESH" and o is not mesh][0]

    -- the first mesh in the file that is not the skinned one, taken AFTER a second glTF
    import. This file's own comment at lines 63-67 records catching that exact selection
    once: the exported GLB carries a stray `Icosphere` and index 0 picked it. The stray
    removal above runs BEFORE this import, so it does not cover what this import adds, and
    the discriminator it uses (vertex groups plus an ARMATURE modifier) does not apply to
    an unrigged reference mesh.

    `ref.data.polygons` then supplies the triangle count in the "before -- original mesh,
    N tris, source atlas" label, and `ref` is rendered as that panel: the Director's
    texture-fidelity row could show an Icosphere beside the retopologised character under a
    count read off the Icosphere, and the sheet would read as catastrophic texture loss
    where the route is fine.

    The population is now the DIFFERENCE the import made, filtered by render visibility,
    and an ambiguous result raises -- the shape `rig_bake._import` and
    `rig_character.build_pass` already use.
    """
    before = {o.name for o in bpy.data.objects}
    _import = bpy.ops.import_scene.gltf(filepath=path)
    rc.require_import_status(_import, path, RigSheetSubjectError,
                             {"who": "make_rig_sheet", "role": "reference"},
                             what="the reference GLB")
    added = [o for o in bpy.data.objects if o.name not in before]
    meshes = [o for o in added if o.type == "MESH" and o is not skinned]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1:
        raise RigSheetSubjectError(
            f"the reference import of {path} contributed {len(visible)} render-visible "
            f"mesh object(s) {[o.name for o in visible]} (from added "
            f"{[o.name for o in added]}); exactly one is needed, and taking index 0 is how "
            f"a decoy once became the 'before' panel and its triangle count",
            {"clause": "reference_import_is_not_one_render_visible_mesh",
             "andon": "ArmatureError", "path": path,
             "render_visible": [o.name for o in visible],
             "added": [o.name for o in added]})
    return visible[0]


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    panel_dir = os.path.join(out_dir, "panels")

    scene = rc.fresh_scene(16)
    _import = bpy.ops.import_scene.gltf(filepath=args["glb"])
    rc.require_import_status(_import, args["glb"], RigSheetSubjectError,
                             {"who": "make_rig_sheet"})
    # Pick the mesh that is actually SKINNED, not the first mesh in the file. The exported
    # GLB also contains a stray `Icosphere` with no vertex groups and no modifier; taking
    # index 0 picked that, and it of course never moves -- this tool's own liveness check
    # then reported "the arc did not survive the round trip" about an object that was never
    # in the arc. Identify by the property that matters.
    skinned = [o for o in bpy.data.objects
               if o.type == "MESH" and o.vertex_groups
               and any(m.type == "ARMATURE" for m in o.modifiers)]
    if len(skinned) != 1:
        raise RigSheetSubjectError(
            f"expected exactly one skinned mesh in {args['glb']}, found {len(skinned)}: "
            f"{[o.name for o in skinned]} (all meshes: "
            f"{[o.name for o in bpy.data.objects if o.type == 'MESH']})",
            {"clause": "subject_is_not_one_skinned_mesh", "andon": "ArmatureError",
             "glb": args["glb"], "skinned": [o.name for o in skinned]})
    mesh = skinned[0]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise RigSheetSubjectError(
            f"expected exactly one armature in {args['glb']}, found "
            f"{[o.name for o in arms]}; index 0 is whichever the file happened to "
            f"list first",
            {"clause": "subject_is_not_one_armature", "andon": "ArmatureError",
             "glb": args["glb"], "armatures": [o.name for o in arms]})
    arm = arms[0]
    stray = [o.name for o in bpy.data.objects if o.type == "MESH" and o is not mesh]
    for name in stray:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    dg = bpy.context.evaluated_depsgraph_get()
    scene.frame_set(1)
    dg.update()
    at_rest = evaluated(mesh, dg)
    scene.frame_set(rc.PROBE_FRAMES)
    dg.update()
    at_end = evaluated(mesh, dg)
    # SIBLING CARRIED under F-6a9a0f72 (wave 14). Gate SCALE: the arc-survived refusal
    # compares `moved` against a fraction of the subject's bbox diagonal, and a NaN
    # diagonal makes that comparison False -- so a subject carrying a NaN read as a
    # subject whose arc survived. `subject_scale` closed that half.
    #
    # WAVE 16, F-4dc96644 -- the half the comment above did NOT cover, and said so: it
    # names a NaN DIAGONAL only, and `subject_scale` is taken on `at_rest`. The POSED
    # frame was examined by no clause, so one NaN vertex arriving at frame PROBE_FRAMES
    # made `moved` NaN, the comparison False, and the sheet was built and captioned over
    # an arc nobody measured. Both halves now live in ONE implementation of the measurement
    # and the bound -- `make_parts_sheet.arc_liveness`, beside the staging triple and
    # `articulated_side` this module already imports from there, with the refusal staying
    # here in this sheet's own words -- and this file's `1e-4 * diagonal` is the form the
    # other two were corrected TO (F-8958f574).
    arc, diagonal, lo, hi = arc_liveness(
        float(np.abs(at_end - at_rest).max()),
        "max_vertex_motion", at_rest, "make_rig_sheet")
    if arc["max_vertex_motion"] <= arc["floor"]:
        raise ArcDidNotSurvive(
            f"{args['glb']}: the evaluated mesh is identical at frame 1 and frame "
            f"{rc.PROBE_FRAMES} (max {arc['max_vertex_motion']:.3e}, "
            f"{arc['displacement_over_diagonal']:.3e} of this subject's own bbox diagonal "
            f"{arc['bbox_diagonal']:.6f}). The authored arc did not survive the round "
            f"trip, and a sheet built from this would read as 'this route does not move'",
            dict(arc, glb=args["glb"]))

    # Every refusal above this line can fire before a single pixel exists — three of them
    # are inline `raise`s, which is precisely why the wave-10 census could not see that
    # they were stranded below the directory (F-244b2ad5; the corrected shape is carried
    # from `render_performer.py` and `preview_glb.py`). The directory is created HERE so a
    # halt does not leave an empty one behind for a later run, or a reader scanning
    # `outputs/`, to read as an attempt that produced nothing. Nothing between the old site
    # and this one writes.
    # F-4db23b72: BOTH of `import_reference`'s clauses now fire above the first byte -- the
    # argv clause here, and the ambiguous-import `raise` inside the import itself, which is
    # performed HERE rather than 55 lines below among the panels. Nothing about the
    # reference ever needed a rendered panel: it needs the scene and the skinned mesh, and
    # both exist above this line. The reference is hidden from the render immediately, so
    # the figure and inset panels are unchanged; the fidelity row un-hides it at its own
    # site. What this stops leaving behind is `<out>/panels/` holding seven panels, no
    # `panels.json` and no sheet, which reads as an interrupted render rather than as a
    # refusal.
    reference_path = require_reference_file(args["reference"])
    ref = import_reference(reference_path, scene, mesh)
    ref.hide_render = True

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(panel_dir, exist_ok=True)

    # Inset targets read from the POSED armature, so each crop lands on its own joint.
    scene.frame_set(rc.PROBE_FRAMES)
    dg.update()
    bones = {b.name: (arm.matrix_world @ b.head) for b in arm.pose.bones}
    height = hi[2] - lo[2]
    # Which arm the arc moves is MEASURED here too -- ONE implementation, imported from
    # `make_parts_sheet` beside the staging triple this file already takes from there.
    side_rec = articulated_side(arm, scene, 1, rc.PROBE_FRAMES)
    side = side_rec["side"]
    # The arc's own numbers, from the constants the probe is AUTHORED with -- carried from
    # `rig_sheet_compose`, which reads `spec["probe"]` rather than baking the frame count
    # and the rate into its subtitle (instruments-measure, F-f3fe8179). One implementation:
    # if `rig_character.PROBE_FRAMES` or `PROBE_FPS` moves, every caption moves with it.
    probe = {"frames": rc.PROBE_FRAMES, "fps": rc.PROBE_FPS,
             "start_deg": rc.PROBE_START_DEG, "end_deg": rc.PROBE_END_DEG,
             "arc": rc.PROBE_ARC,
             "which_arm_is_on_plus_x": side_rec["side_word"],
             "bone": f"shoulder.{side}"}
    scene.frame_set(rc.PROBE_FRAMES)
    dg.update()
    insets = [("shoulder", bones[f"shoulder.{side}"], height * 0.20, 0.0),
              ("elbow", bones[f"elbow.{side}"], height * 0.16, 0.0),
              ("wrist", bones[f"wrist.{side}"], height * 0.16, 0.0),
              ("hip", bones[f"hip.{side}"], height * 0.20, 0.0)]

    light_the_scene(scene)
    centre = Vector((0.5 * (lo[0] + hi[0]), 0.0, lo[2] + 0.5 * height))
    rows = []

    figure = []
    for frame in (1, 1 + rc.PROBE_FRAMES // 2, rc.PROBE_FRAMES):
        scene.frame_set(frame)
        ortho_camera(scene, f"cam_f{frame}", centre, height * 1.10, (700, 1120))
        figure.append({"body": shoot(scene, os.path.join(panel_dir, f"figure_{frame}.png")),
                       "label": "frame 1 — rest" if frame == 1 else f"frame {frame}"})
    rows.append({"title": "The figure through the arc", "panels": figure})

    scene.frame_set(rc.PROBE_FRAMES)
    close = []
    for label, target, oscale, azim in insets:
        ortho_camera(scene, f"cam_{label}", Vector(target), oscale, (700, 700), azim)
        close.append({"body": shoot(scene, os.path.join(panel_dir, f"{label}.png")),
                      "label": label})
    rows.append({"title": f"At 1:1, frame {rc.PROBE_FRAMES} — the joints under "
                          f"articulation", "panels": close})

    # ---- texture fidelity: the mesh that was replaced, and the one that replaced it -------
    scene.frame_set(1)
    # The loop that used to sit here iterated every object and did nothing -- its whole
    # body was `if ob.type == "ARMATURE": continue`. An abandoned cleanup; removed rather
    # than completed, because the two objects this row compares are exactly the skinned
    # mesh and the reference, and a cleanup here would have had to spare both.
    # `ref` was imported and hidden above the first write (F-4db23b72).
    fidelity = []
    after_label = args["after_label"] or (
        f"after — {len(mesh.data.polygons):,} faces, {len(mesh.data.vertices):,} verts")
    before_label = (f"before — original mesh, {len(ref.data.polygons):,} tris, "
                    f"source atlas")
    for label, shown in ((before_label, ref), (after_label, mesh)):
        ref.hide_render = shown is not ref
        mesh.hide_render = shown is not mesh
        ortho_camera(scene, f"cam_fid_{shown.name}", centre, height * 1.10, (700, 1120))
        fidelity.append({"body": shoot(scene, os.path.join(
            panel_dir, f"fidelity_{'before' if shown is ref else 'after'}.png")),
            "label": label})
        for label2, target, oscale, _ in insets[:1]:
            ortho_camera(scene, f"cam_fid_{shown.name}_{label2}", Vector(target),
                         height * 0.22, (700, 700))
            fidelity.append({"body": shoot(scene, os.path.join(
                panel_dir,
                f"fidelity_{'before' if shown is ref else 'after'}_{label2}.png")),
                "label": f"{label2}, same camera"})
    ref.hide_render = False
    mesh.hide_render = False
    rows.append({"title": "Texture fidelity — at rest, same camera, nothing else changed",
                 "panels": fidelity})

    spec = {"tool": "make_rig_sheet",
            "blender": blender_scene.blender_provenance(),
            "title": args["title"],
            "subtitle": (f"one skinned mesh, {len(mesh.data.vertices):,} verts, "
                         f"{len(mesh.data.polygons):,} faces, bone-heat weights normalised "
                         f"to 1.0 · the arc is E03's: the character's "
                         f"{probe['which_arm_is_on_plus_x']} arm, "
                         f"{probe['start_deg']:g}°→{probe['end_deg']:g}° "
                         f"about +Y, {probe['frames']} keys at {probe['fps']} fps"),
            "articulated_side": side_rec,
            "probe": probe,
            "out": out_dir, "filename": "E07-rig-armature.png", "rows": rows}
    with open(os.path.join(out_dir, "panels.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print("MAKE_RIG_SHEET_OK " + json.dumps({"max_vertex_motion":
                                             arc["max_vertex_motion"],
                                             "rows": len(rows),
                                     "stray_meshes_removed": stray}))


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
            "tool": "make_rig_sheet", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "make_rig_sheet", "outcome": _outcome,
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
            print("MAKE_RIG_SHEET_HALT " + _line)
            sys.exit(_code)
