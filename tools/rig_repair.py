"""Arm (d), the route that actually works — **repair the shell, do not resample it**.

The voxel+QuadriFlow route (``rig_retopo.py``) produces a clean manifold and **destroys the
character's face doing it**. Measured: at the coarse voxel the mouth comes back as a ragged
trench and the eyelids as steps; at 0.0012 — the finest voxel QuadriFlow will accept on this
figure — the mouth is still serrated. The deviation metric read **0.144 %** of the diagonal
while the face was ruined, because a two-millimetre mouth crease averages to nothing against a
whole body of smooth limb. That is the standing law in one number: metrics are diagnostics,
and the eye is the judge.

The insight that makes resampling unnecessary: after the interior wall is deleted and the glTF
seam splits are welded, the outer shell has **125 non-manifold vertices, 98 non-manifold edges
and 34 boundary edges out of ~221,000 edges**. It is not a broken mesh; it is an intact mesh
with a few bad stitches. One pass of *select non-manifold → grow → delete faces → fill holes*
takes it to **0 / 0 / 0**, costing **593 faces of 147,450 (0.40 %)**, and bone heat then binds
**17 of 17 bones with no unweighted vertices**.

Because nothing is resampled, this route also **keeps the original UVs and the original
atlas**: there is no unwrap and no bake, so texture fidelity is exact everywhere except the
few filled holes. Those are counted and located rather than assumed harmless.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The world-touching acts are EXPORTING the repaired GLB and writing
`repair_manifest.json` under `--out`, plus `halt.json` on the refusal path.
Compensator: delete `--out`; owner: the executor session. Every path it writes is
composed from `--out` and a fixed literal, so no operator-supplied name component can
carry the exported GLB outside the directory the compensator names. The source GLB is
opened read-only.

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
import time

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_character as rc                                            # noqa: E402
from armature_core import blender_scene                               # noqa: E402
import rig_parts as rp                                                # noqa: E402
# `ArmatureError` as well as `GateFailure`: line 159's ambiguous-subject refusal raised
# a name this module never bound, so the branch the comment there describes produced
# `NameError: name 'ArmatureError' is not defined` -- a crash (exit 1) where the tool
# meant to decline (exit 2), with the halt record naming Python instead of naming the
# ambiguous subject. Measured 2026-09-04 (F-3bf15648); pinned by
# `tests/test_instruments_amend_w10.py::test_every_raise_names_something_the_module_actually_binds`.
from armature_core.errors import ArmatureError, GateFailure           # noqa: E402

#: How many repair passes before giving up. One is enough on this figure; the loop exists so
#: a mesh needing two does not silently ship at 1.
MAX_REPAIR_PASSES = 8


class RigRepairSubjectError(ArmatureError):
    """The asset this repair was pointed at is not one identifiable subject.

    Wave 25, F-3b71c0aa. The render-visible ambiguity refused through the family BASE
    with no evidence; `SourceHasNoFaces` above is the gate for an asset with no polygons
    at all, and this is the one for an asset with more than one candidate."""


class NotManifoldAfterRepair(GateFailure):
    """The shell could not be repaired to a closed manifold."""

    gate = "REPAIR"


class SourceHasNoFaces(GateFailure):
    """The asset this repair was pointed at has no polygons to repair.

    F-4354f34d, wave 22. Its own class rather than a clause on `NotManifoldAfterRepair`,
    because a reader of the halt line has to be able to tell WHICH andon pulled: "the
    shell is still not a closed manifold after repair" describes a repair that ran and
    fell short, and this describes a run that had nothing to repair. Two different
    defects in the asset, two different next actions.
    """

    gate = "REPAIR_SOURCE"


class TooMuchRemoved(GateFailure):
    """Repair ate more of the character than a stitch-fixing pass should."""

    gate = "REPAIR_BUDGET"


#: Repair may remove a little geometry around bad stitches. It may not remove a hand. The
#: budget is a fraction of the shell's own face count, not an absolute number.
REPAIR_FACE_BUDGET = 0.02


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/rig_repair.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--glb", required=True,
                   help="the double-walled character shell to REPAIR in place of "
                        "resampling it; read only")
    p.add_argument("--out", required=True,
                   help="the directory the repaired GLB and its manifold record are "
                        "written into. Compensator: delete it; owner: the executor session")
    return vars(p.parse_args(argv))


def manifold_stats(ob):
    """The shell's manifold counts, and whether it IS one.

    **`closed_manifold` needs a face to be a claim about (F-4354f34d, wave 22).** It was
    derived as three counts all being zero — which is True for an EMPTY mesh, MEASURED by
    evaluating the expression on the zero-count dict: `closed_manifold = True`. So Gate
    REPAIR's `if not final["closed_manifold"]` clause passed a mesh that had been deleted
    entirely, and total deletion was caught one clause LOWER, by the face BUDGET — and
    only while `shell_faces > 0`. CLAUDE.md rules on that direction: a gate whose andon is
    load-bearing only in another gate's presence is not an andon. A vacuous PASS is not a
    PASS; nothing is not a closed manifold.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    s = {"non_manifold_verts": sum(1 for v in bm.verts if not v.is_manifold),
         "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold),
         "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
         "faces": len(bm.faces), "verts": len(bm.verts)}
    s["closed_manifold"] = (s["faces"] > 0
                            and s["non_manifold_verts"] == 0
                            and s["non_manifold_edges"] == 0
                            and s["boundary_edges"] == 0)
    bm.free()
    return s


def extract_and_weld(ob, diagonal):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    before = {"faces": len(bm.faces), "verts": len(bm.verts)}
    # F-4354f34d, wave 22 — THE DENOMINATOR, guarded where it is READ. This tool's
    # EXPECTED input is a broken mesh, and `interior_fraction = interior_deleted /
    # before["faces"]` divided by a measured count with no guard: a source contributing
    # vertices and no polygons reached a bare `ZeroDivisionError` inside a helper, which
    # this tool's halt contract records as "FAILED — an unhandled error" at exit 1 rather
    # than as a refusal naming the asset. The asset is what a reader needs.
    if before["faces"] == 0:
        bm.free()
        raise SourceHasNoFaces(
            f"the source mesh {ob.name!r} contributes {before['verts']} vertices and "
            f"ZERO polygons, so there is no face count to divide the interior deletion "
            f"by and nothing for a shell classification to be about. A repair pass over "
            f"no surface is not a repair",
            {"gate": SourceHasNoFaces.gate, "sub_gate": "EXTRACT",
             "andon": SourceHasNoFaces.__name__, "who": "rig_repair",
             "clause": "source_has_no_faces", "object": ob.name,
             "faces": 0, "verts": int(before["verts"])})
    face_comp, exterior, n_shells = rp.classify_shells(bm, diagonal)
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in np.flatnonzero(face_comp != exterior)],
                     context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    interior_deleted = before["faces"] - len(bm.faces)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6 * diagonal)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return {"shells_welded": n_shells, "faces_before": before["faces"],
            "verts_before": before["verts"], "interior_faces_deleted": interior_deleted,
            "interior_fraction": interior_deleted / before["faces"],
            **manifold_stats(ob)}


def repair(ob, diagonal):
    """Bad stitches out, holes closed, until the shell is a closed manifold.

    Grow-by-one before deleting matters: a non-manifold vertex is usually the corner of a
    small malformed fan, and removing only the faces that touch it leaves the same defect one
    ring out. Each pass is recorded so "how much surgery did this take" is answerable.
    """
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
    bpy.ops.mesh.dissolve_degenerate(threshold=1e-6 * diagonal)
    bpy.ops.object.mode_set(mode="OBJECT")

    passes = []
    for _ in range(MAX_REPAIR_PASSES):
        s = manifold_stats(ob)
        if s["closed_manifold"]:
            break
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_non_manifold(extend=False)
        bpy.ops.mesh.select_more()
        bpy.ops.mesh.delete(type="FACE")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.fill_holes(sides=0)
        bpy.ops.object.mode_set(mode="OBJECT")
        passes.append(manifold_stats(ob))

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return passes


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    started = time.strftime("%Y-%m-%dT%H:%M:%S")

    scene = rc.fresh_scene(16)
    _import = bpy.ops.import_scene.gltf(filepath=args["glb"])
    rc.require_import_status(_import, args["glb"], RigRepairSubjectError,
                             {"who": "rig_repair"})
    # FAMILY of F-cb986eb3 / F-e911313d: `[...][0]` over the object table. Which
    # object index 0 is depends on file order, and the glTF importer routinely adds a
    # second mesh -- the `glTF_not_exported` Icosphere, which make_rig_sheet's own
    # comment records picking once. Selection is render visibility and an ambiguous
    # result RAISES, the shape rig_character.build_pass and rig_bake._import use.
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1:
        raise RigRepairSubjectError(
            f"{args['glb']} presents {len(visible)} render-visible mesh object(s) "
            f"{[o.name for o in visible]} (all meshes {[o.name for o in meshes]}); "
            f"the repair would run on whichever one file order put first",
            {"clause": "subject_is_not_one_render_visible_mesh", "andon": "ArmatureError",
             "glb": args["glb"], "render_visible": [o.name for o in visible],
             "all_meshes": [o.name for o in meshes]})
    ob = visible[0]
    ob.name = ob.data.name = "performer_repaired"
    src = rc.world_verts(ob)
    # SIBLING CARRIED under F-6a9a0f72 (wave 14). Gate SCALE, on the tool whose EXPECTED
    # input is a broken mesh -- the weld distance below is a fraction of this number, and a
    # NaN weld distance welds nothing while every manifold statistic beside it reads normal.
    diagonal, _lo, _hi = rc.subject_scale(src, "rig_repair")

    extraction = extract_and_weld(ob, diagonal)
    shell_faces = extraction["faces"]
    # F-4354f34d's second denominator: `"faces_removed_fraction": removed / shell_faces`
    # in the manifest below has the same exposure as `interior_fraction` above, one step
    # later — every shell classified interior leaves a zero here even when the source had
    # faces. It is also the number the face-BUDGET clause divides by, so a zero makes that
    # clause (`removed > REPAIR_FACE_BUDGET * shell_faces`) unable to fire on any removal.
    if shell_faces == 0:
        raise SourceHasNoFaces(
            f"shell extraction left ZERO faces on {ob.name!r}: every shell in the source "
            f"was classified interior and deleted. There is no surface for the repair "
            f"passes to fix, no denominator for the removal fraction, and the face-budget "
            f"clause below cannot fire against a budget of zero",
            {"gate": SourceHasNoFaces.gate, "sub_gate": "EXTRACT",
             "andon": SourceHasNoFaces.__name__, "who": "rig_repair",
             "clause": "extraction_left_no_faces", "object": ob.name,
             "faces_before": int(extraction["faces_before"]),
             "interior_faces_deleted": int(extraction["interior_faces_deleted"]),
             "shell_faces": 0})
    t = time.time()
    passes = repair(ob, diagonal)
    final = manifold_stats(ob)
    secs = time.time() - t

    if not final["closed_manifold"]:
        raise NotManifoldAfterRepair(
            "the shell is still not a closed manifold after repair",
            {"clause": "still_not_manifold_after_repair", "final": final, "passes": passes})
    removed = shell_faces - final["faces"]
    if removed > REPAIR_FACE_BUDGET * shell_faces:
        raise TooMuchRemoved(
            "repair removed more of the character than a stitch-fixing pass should",
            {"clause": "repair_removed_too_much", "faces_removed": removed, "of": shell_faces,
             "budget_fraction": REPAIR_FACE_BUDGET})

    if not ob.data.validate(verbose=False):
        validated = "mesh reported valid"
    else:
        validated = "mesh.validate() CORRECTED problems — recorded, not hidden"
    ob.data.update()

    # F-244b2ad5: three inline `raise`s sit above this line — an ambiguous subject, a
    # shell still not manifold after repair, and a repair that removed more of the
    # character than the budget allows — and none of them needs a directory. It is created
    # HERE. The wave-10 census reported this file clean because all three are inline
    # `raise`s and its predicate keyed on the callee's NAME.
    os.makedirs(out_dir, exist_ok=True)

    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    out_glb = os.path.join(out_dir, "performer_repaired.glb")
    # WAVE 14, F-6a9a0f72: snapshot before, status set captured, both handed to the gate.
    before_glb = rc.export_target_snapshot(out_glb)
    export_result = bpy.ops.export_scene.gltf(
        filepath=out_glb, export_format="GLB", use_selection=True,
        export_apply=False, export_yup=True,
        export_image_format="AUTO")
    # F-9b2d4106, family carry: one implementation, `rig_character.gate_glb_written`.
    gate_glb = rc.gate_glb_written(out_glb, result=export_result, before=before_glb,
                                   what="the repaired GLB")

    manifest = {
        "tool": "rig_repair", "started": started,
        # WAVE 14, F-252f399d: `blender_provenance()` and not `bpy.app.version_string`.
        # A version string is not enough to reproduce a build -- the record needs the build
        # hash, the build date and the numpy version, and numpy in particular is
        # load-bearing wherever a verdict is a numerical comparison between two builds.
        "blender": blender_scene.blender_provenance(),
        "gate_GLB_written": gate_glb,
        "thesis": ("repair the shell rather than resample it -- the voxel route reaches a "
                   "clean manifold by destroying the face, and this reaches the same "
                   "manifold while touching 0.40% of the faces"),
        "source": {"path": args["glb"], "sha256": rc.sha256_file(args["glb"])},
        "extraction": extraction,
        "repair": {"passes": passes, "passes_needed": len(passes), "seconds": round(secs, 1),
                   "faces_removed": removed,
                   "faces_removed_fraction": removed / shell_faces,
                   "budget_fraction": REPAIR_FACE_BUDGET,
                   "operators": "delete_loose -> dissolve_degenerate -> (select_non_manifold "
                                "-> select_more -> delete FACE -> fill_holes)* -> "
                                "normals_make_consistent"},
        "final": final, "validate": validated,
        "uvs": {"layers": [l.name for l in ob.data.uv_layers],
                "note": "the ORIGINAL uv layout and atlas survive -- nothing is resampled, "
                        "so there is no unwrap and no bake in this route"},
        "materials": [m.name for m in ob.data.materials if m],
        "output": {"path": out_glb, "sha256": rc.sha256_file(out_glb),
                   "bytes": os.path.getsize(out_glb)},
    }
    with open(os.path.join(out_dir, "repair_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    print("RIG_REPAIR_OK " + json.dumps({"glb": out_glb, "faces": final["faces"],
                                     "closed_manifold": final["closed_manifold"],
                                     "faces_removed": removed,
                                     "passes": len(passes)}))


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
    #
    # The record on disk carries the same three-state vocabulary. The exit code is computed
    # BEFORE anything that can fail and delivered from a `finally`: re-parsing argv or
    # re-hashing the GLB inside this block can raise a SECOND exception, which used to leave
    # the whole `try` statement with `sys.exit` never reached (measured 2026-09-04).
    try:
        main()
    # WAVE 28, F-814335e4. A DELIBERATE REFUSAL IS NOT A CRASH, and this handler used
    # to record it as one. `argparse` refuses a missing or mistyped required flag by
    # raising `SystemExit(2)`; with no re-raise above the `except BaseException`, the
    # branch below caught it, wrote `"error": "SystemExit", "message": "2"` under
    # `FAILED - an unhandled error`, and exited **1** -- the code this repo reserves for
    # a crash. MEASURED on `3380ae2` with `blender_stub.exit_code_of_main_block` and a
    # `main` replaced by a `SystemExit(2)` raiser: rig_bake, rig_character, rig_parts,
    # rig_repair and rig_retopo returned 1 with a halt line whose entire message was the
    # character `2`, while the sixteen siblings (preview_glb.py and kin) returned 2 and
    # printed nothing. Worse, the halt-record branch re-parses argv to find `--out`, and
    # on this path argparse raised a SECOND time, so no `halt.json` was written either.
    # `armature_core.parts.run_tool_main`, the ONE CPython handler, has carried this
    # same two lines since wave 22; this is the Blender-side local handler adopting the
    # shape, not a second spelling of it. The three-outcome rule the comment above
    # states -- "a deliberate refusal exits 2; a crash exits 1" -- is what these two
    # lines make true for an argument the operator got wrong.
    except SystemExit:
        raise
    except BaseException as exc:                                      # noqa: BLE001
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
            "tool": "rig_repair", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "rig_repair", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            # `allow_nan=False` (F-897a3329): strict JSON, and it cannot raise here because
            # `_halt_keysafe` above has already replaced every non-finite float with its repr.
            _line = json.dumps(_sentinel, default=str, allow_nan=False)
        except BaseException:                                         # noqa: BLE001
            pass
        try:
            _a = parse_args()
            _d = os.path.abspath(_a["out"])
            os.makedirs(_d, exist_ok=True)
            with open(os.path.join(_d, "halt.json"), "w", encoding="utf-8") as fh:
                json.dump(dict(_sentinel, traceback=traceback.format_exc()), fh,
                          indent=2, default=str)
        except BaseException:                                         # noqa: BLE001
            # The halt record is a courtesy; the sentinel and the exit code are
            # the contract. Even this diagnostic is guarded (F-586822bf):
            # nothing in this handler may reach the `finally` before `sys.exit`.
            try:
                traceback.print_exc()
            except BaseException:                                     # noqa: BLE001
                pass
        finally:
            print("RIG_REPAIR_HALT " + _line)
            sys.exit(_code)
