"""diagnose_bone_heat — why `ARMATURE_AUTO` produced no weights on the E07 subject.

    blender -b --factory-startup -P tools\\diagnose_bone_heat.py -- --glb=<in.glb> --out=<dir>

E07's Gate P liveness clause fired: the mesh did not move when a bone was posed. The cause
measured immediately behind it was that Blender's bone-heat weighting created all 17 deform
vertex groups and left **every one of them empty** — 399,140 of 399,140 vertices with a
total weight of zero. `parent_set` reports this as an INFO-level warning and returns
success.

This file is the sweep that narrows the mechanism, kept in the repo because a finding whose
recipe does not reproduce is not a finding. **It is a diagnostic and it is not a pipeline
stage.** Nothing here produces a rigged asset, and no arm of it is a route past the gate —
which of these routes, if any, E07 should have taken is the advisor's ruling and the
Director's call, not this tool's.

Each arm removes one candidate mechanism:

* **bones** — two bones instead of 22, to separate "the solve fails" from "this armature".
* **weld** — merge by distance, to test whether the 21,514 shells the glTF importer
  produces (vertices split at every UV seam) are what defeats the solve.
* **outer** — keep only the largest shell, to test whether the interior shells block it.
* **scale** — 0.1× to 100×, because bone heat is known to carry hard-coded epsilons and a
  figure 1.0 units tall is small for them.
* **envelope** — `ARMATURE_ENVELOPE` on the same mesh and the same armature, as the contrast
  that says whether the mesh can be weighted at all by anything.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is writing `bone_heat_diagnosis.json` under `--out`.
Compensator: delete `--out`; owner: the executor session. Every path it writes is
composed from `--out` and a fixed literal, so no operator-supplied name component can
carry the artifact outside the directory the compensator names. The GLB is opened
read-only and is never written.

Named because CLAUDE.md's workflow standard 3 (NAMED_COMPENSATORS -- Sagas,
Garcia-Molina & Salem, SIGMOD 1987) takes NO skip, and because the ordering makes the
question ordinary rather than exotic: `_census_nodes.refusal_and_write_lines`, run over
the 21 Blender-side tools, finds 15 modules with at least one refusal BELOW the first
write, so a halt after the first write is the common case (F-6e1a9d54, wave 25).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

from armature_core import landmarks, sitelist  # noqa: E402
from armature_core import blender_scene  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402
# F-19d4e0f7: `require_import_status` is `require_render_target_moved`'s sibling and
# lives beside it -- one implementation of the importer's status clause, fourteen
# callers, with the operator call itself kept here where this module's `bpy` is.
import rig_character as rc  # noqa: E402


class BoneHeatSubjectError(ArmatureError):
    """The mesh this diagnosis was pointed at is not one identifiable subject.

    Wave 25, F-3b71c0aa. Named rather than the family BASE, for the reason
    `errors.ArmatureError`'s docstring gives; `BandCountError` above is its sibling for
    the FLAG, and keeping the two apart is the whole point -- this tool exists to
    investigate why a mesh binds badly, so a refusal about the MESH and a refusal about
    an argument must not arrive under one name."""


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/diagnose_bone_heat.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--glb", required=True,
                   help="the character GLB whose bone-heat binding is being diagnosed; "
                        "read only")
    p.add_argument("--out", required=True,
                   help="the directory the diagnosis is written into. Compensator: delete "
                        "it; owner: the executor session")
    p.add_argument("--bands", type=int, default=200,
                   help="horizontal bands the silhouette is read in (default 200). Bounds "
                        "the landmark derivation: below MIN_BANDS the figure cannot be "
                        "resolved and the run is refused on THIS flag, by name")
    return p.parse_args(argv)


#: The fewest bands `landmarks.derive` can resolve a standing figure out of.
#:
#: DERIVED, not chosen. `landmarks._region_runs` reads the band profile bottom-up and
#: requires FOUR runs -- legs alone, legs+arms, trunk+arms, trunk -- each surviving the
#: `end - start >= MIN_RUN_BANDS` filter. `_median3` holds its edges and preserves
#: length, so the floor is exactly four times that constant. It is spelled as an
#: expression over `landmarks.MIN_RUN_BANDS` rather than as the literal 12 so the number
#: this clause tests and the number the derivation enforces are the same object: a global
#: constant must not govern a local feature, and this one is the feature's own.
MIN_BANDS = 4 * landmarks.MIN_RUN_BANDS


class BandCountError(ArmatureError):
    """`--bands` cannot produce a band profile any landmark could be read off."""


def require_band_count(args):
    """`args` if `--bands` can resolve a figure, else raise naming THE FLAG. · ANDON

    WAVE 25, F-a4f7b3c9. `--bands` was `type=int, default=200` and reached by nothing:
    an AST sweep of every `type=int` / `type=float` `add_argument` across the 21 owned
    tools finds every other numeric flag routed through `parts.require_finite`,
    `require_subject_args`, `require_frame_size`, `require_shot_fraction` or
    `parts.tightened`, and this one through nothing. It is read at the single call
    `landmarks.derive(world_verts(ob), n_bands=bands)` and reaches all twelve arms.

    MEASURED in this worktree on the repo venv: `landmarks.band_profile(v, n_bands=0)`
    and `n_bands=-5` each RETURN with zero bands and no refusal of any kind, and
    `landmarks.derive` then raises `LandmarkError` under the clause
    `silhouette_is_not_a_standing_figure` -- a clause about the ASSET, on a run whose
    only defect is the flag. That is the 'refused, but incidentally' shape the ground row
    F-114e1c6c described and wave 22 closed at `make_test_armature`; here the incidental
    refusal is worse than fragile, because this tool's whole purpose is investigating WHY
    a mesh binds badly, so a message blaming the silhouette is the message the operator is
    primed to believe. A value of 1 or 2 also passes `band_profile` with no complaint at
    all while deciding the RESOLUTION of every landmark the twelve arms are built from.

    The shape is `make_test_armature.require_subject_args`'s: ONE clause, listing every
    offending flag by name, with the value in the evidence, above `load()` and above any
    write. The complementary half -- `landmarks.band_profile` refusing a band count that
    produces zero bands, rather than returning an empty profile for `derive` to
    misattribute -- is `armature_core`'s and is posted to the wave-25 inbox.
    """
    ev = {"gate": None, "andon": "BandCountError",
          "clause": "bands_not_a_usable_band_count",
          "flag": "--bands", "bands": args.bands, "minimum": MIN_BANDS,
          "min_run_bands": landmarks.MIN_RUN_BANDS}
    if not isinstance(args.bands, int) or isinstance(args.bands, bool):
        raise BandCountError(
            f"--bands={args.bands!r} is not an integer; it is the number of horizontal "
            f"sections the silhouette is sliced into", ev)
    if args.bands < MIN_BANDS:
        raise BandCountError(
            f"--bands={args.bands} cannot resolve a standing figure: "
            f"`landmarks._region_runs` needs four cluster-count runs of at least "
            f"{landmarks.MIN_RUN_BANDS} bands each (legs, legs+arms, trunk+arms, trunk), "
            f"so the floor is {MIN_BANDS}. Below it the derivation refuses under "
            f"`silhouette_is_not_a_standing_figure` -- a clause about the MESH -- on a "
            f"run whose only defect is this flag, and this tool exists to investigate "
            f"why a mesh binds badly", ev)
    return args


def load(glb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = 16, 1.0
    _import = bpy.ops.import_scene.gltf(filepath=glb)
    rc.require_import_status(_import, glb, BoneHeatSubjectError,
                             {"who": "diagnose_bone_heat"})
    # FAMILY of F-cb986eb3 / F-e911313d: `[...][0]` over the object table. Which
    # object index 0 is depends on file order, and the glTF importer routinely adds a
    # second mesh -- the `glTF_not_exported` Icosphere, which make_rig_sheet's own
    # comment records picking once. Selection is render visibility and an ambiguous
    # result RAISES, the shape rig_character.build_pass and rig_bake._import use.
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1:
        raise BoneHeatSubjectError(
            f"{glb} presents {len(visible)} render-visible mesh object(s) "
            f"{[o.name for o in visible]} (all meshes {[o.name for o in meshes]}); "
            f"which one carries the character is not a question this tool answers by "
            f"taking index 0",
            {"clause": "subject_is_not_one_render_visible_mesh", "andon": "ArmatureError",
             "glb": glb, "render_visible": [o.name for o in visible],
             "all_meshes": [o.name for o in meshes]})
    return scene, visible[0]


def world_verts(ob):
    n = len(ob.data.vertices)
    flat = np.empty(n * 3, dtype=np.float64)
    ob.data.vertices.foreach_get("co", flat)
    m = np.array(ob.matrix_world, dtype=np.float64)
    return flat.reshape(n, 3) @ m[:3, :3].T + m[:3, 3]


def shell_components(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    seen, comps = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            x = stack.pop()
            comp.append(x.index)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        comps.append(comp)
    bm.free()
    return comps, boundary, non_manifold


def weld(ob, dist):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def keep_only(ob, indices):
    keep = set(indices)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def build_and_bind(scene, ob, bands, mode="ARMATURE_AUTO", only=None):
    marks = landmarks.derive(world_verts(ob), n_bands=bands)["landmarks"]
    data = bpy.data.armatures.new("diag_armature")
    arm = bpy.data.objects.new("diag_rig", data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    for b in sitelist.BONES:
        if only and b.name not in only:
            continue
        eb = data.edit_bones.new(b.name)
        eb.head, eb.tail = marks[b.head], marks[b.tail]
        eb.use_deform = b.deform
        if b.parent and b.parent in made:
            eb.parent = made[b.parent]
            eb.use_connect = False
        made[b.name] = eb
    bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type=mode)

    idx = {g.index: g.name for g in ob.vertex_groups}
    n = len(ob.data.vertices)
    total = np.zeros(n)
    per = {name: 0 for name in idx.values()}
    for i, v in enumerate(ob.data.vertices):
        for ge in v.groups:
            if ge.group in idx:
                total[i] += ge.weight
                if ge.weight > 1e-9:
                    per[idx[ge.group]] += 1
    weighted = int((total > 1e-9).sum())
    return {
        "mode": mode,
        "groups_created": len(idx),
        "vertices": n,
        "weighted_vertices": weighted,
        "weighted_fraction": float(weighted) / n if n else 0.0,
        "empty_groups": sorted(k for k, c in per.items() if c == 0),
        "n_empty_groups": sum(1 for c in per.values() if c == 0),
        "weight_sum_min": float(total.min()) if n else None,
        "weight_sum_mean": float(total.mean()) if n else None,
    }


def main():
    args = parse_args()
    # FIRST, above `load` and above `os.makedirs`: nothing exists yet when this
    # fires, so a refusal leaves nothing behind (the `require_subject_args`
    # placement, carried).
    require_band_count(args)
    out = os.path.abspath(args.out)
    arms = {}

    scene, ob = load(args.glb)
    comps, boundary, non_manifold = shell_components(ob)
    arms["A_as_imported_full_rig"] = dict(
        build_and_bind(scene, ob, args.bands),
        topology={"shells": len(comps), "boundary_edges": boundary,
                  "non_manifold_edges": non_manifold})

    scene, ob = load(args.glb)
    arms["B_two_bones_only"] = build_and_bind(scene, ob, args.bands,
                                              only={"hips", "spine"})

    scene, ob = load(args.glb)
    arms["C_envelope_contrast"] = build_and_bind(scene, ob, args.bands,
                                                 mode="ARMATURE_ENVELOPE")

    for dist in (1e-6, 1e-4):
        scene, ob = load(args.glb)
        weld(ob, dist)
        comps, boundary, non_manifold = shell_components(ob)
        arms[f"D_welded_{dist:g}"] = dict(
            build_and_bind(scene, ob, args.bands),
            topology={"shells": len(comps), "boundary_edges": boundary,
                      "non_manifold_edges": non_manifold})

    scene, ob = load(args.glb)
    weld(ob, 1e-6)
    comps, _, _ = shell_components(ob)
    comps.sort(key=len, reverse=True)
    sizes = [len(c) for c in comps]
    keep_only(ob, comps[0])
    _, boundary, non_manifold = shell_components(ob)
    arms["E_outer_shell_only"] = dict(
        build_and_bind(scene, ob, args.bands),
        topology={"shells_before": len(sizes), "shell_sizes_top8": sizes[:8],
                  "boundary_edges": boundary, "non_manifold_edges": non_manifold})

    for s in (0.1, 2.0, 10.0, 100.0):
        scene, ob = load(args.glb)
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        ob.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        arms[f"F_scale_{s:g}x"] = build_and_bind(scene, ob, args.bands)

    # F-244b2ad5: `load` raises when the GLB contributes no single render-visible mesh,
    # and it is called SIX times above this line. Every one of those refusals can fire
    # before a byte exists, so the output directory is created HERE rather than at the top
    # of `main` — a halt must not leave an empty `outputs/<run>/` for a reader, or a re-run
    # into the same `--out`, to read as an attempt that produced nothing. Corrected shape
    # carried from `render_performer.py:319` and `preview_glb.py:218`. The wave-10 census
    # could not see these six because it recognised a refusal by the callee's NAME.
    os.makedirs(out, exist_ok=True)

    payload = {
        "tool": "diagnose_bone_heat",
        # WAVE 14, F-252f399d: `blender_provenance()` and not `bpy.app.version_string`.
        # A version string is not enough to reproduce a build -- the record needs the build
        # hash, the build date and the numpy version, and numpy in particular is
        # load-bearing wherever a verdict is a numerical comparison between two builds.
        "blender": blender_scene.blender_provenance(),
        "glb": args.glb,
        "arms": arms,
        "note": ("A DIAGNOSTIC. No arm here is a pipeline stage and none produces a rigged "
                 "asset. Which route E07 should take, if any, is the advisor's ruling."),
    }
    path = os.path.join(out, "bone_heat_diagnosis.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    # WAVE 14, F-7e7703cb: THE SENTINEL CARRIES THE SWEEP'S OWN SUMMARY. It used to be
    # `print('DIAGNOSE_BONE_HEAT_OK ' + path)` -- the only thing after the token was the
    # JSON's location, so the token was earned by reaching the end of `main` rather than by
    # a measurable effect (the wave-12 rule). Every sibling's OK line carries counts:
    # `probe_subject` reports n_probed/n_measured/n_errors, `probe_glb`, `rig_bake`,
    # `preview_walk` and `check_relift` each print a JSON object with counts or verdicts.
    # The twelve arms' numbers existed one line below the sentinel and none was in it, so a
    # sweep in which all twelve arms weighted zero vertices -- the exact condition this
    # diagnostic exists to investigate, and therefore a condition under which the tool is
    # working correctly -- read identically to a run in which the harness itself failed.
    #
    # There is deliberately NO refusal on an all-zero sweep: an all-zero result is a
    # legitimate finding for a diagnostic, and a gate here would delete it. The counts make
    # the two cases read differently, which is what was missing.
    weighted_arms = {k: v for k, v in arms.items() if v["weighted_fraction"] > 0}
    best = max(arms.items(), key=lambda kv: kv[1]["weighted_fraction"], default=None)
    print("DIAGNOSE_BONE_HEAT_OK " + json.dumps({
        "tool": "diagnose_bone_heat",
        "json": path,
        "n_arms": len(arms),
        "n_arms_with_weight": len(weighted_arms),
        "best_arm": best[0] if best else None,
        "best_weighted_fraction": (round(best[1]["weighted_fraction"], 6)
                                   if best else None),
        "all_arms_weighted_nothing": len(weighted_arms) == 0,
    }))
    for name, rec in arms.items():
        print(f"  {name:<26} weighted {rec['weighted_vertices']:>7}/{rec['vertices']:<7} "
              f"({100 * rec['weighted_fraction']:6.2f}%)  empty_groups="
              f"{rec['n_empty_groups']}/{rec['groups_created']}")


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
            "tool": "diagnose_bone_heat", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "diagnose_bone_heat", "outcome": _outcome,
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
            print("DIAGNOSE_BONE_HEAT_HALT " + _line)
            sys.exit(_code)
