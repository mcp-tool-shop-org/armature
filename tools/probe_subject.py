#!/usr/bin/env python
"""probe_subject — open a GLB and report what it is. Reads only; writes only JSON.

    blender -b -P tools\\probe_subject.py -- --out=<dir> --glb=<path> [--glb=<path> ...]

E02's premise 6 ("the subject is a character") is marked MEASURED on the condition
that the executor opens the asset rather than reading its filename. This is that
measurement, and it is separate from `probe_glb.py` on purpose: that tool answers
"does this asset carry a usable armature", this one answers "what shape is it".

Subject selection is `blender_scene.render_visible_meshes`, not `type == "MESH"`.
That distinction is not cosmetic — it is the defect G4 fired on in E01. Blender's
glTF importer creates a hidden `glTF_not_exported` collection holding a radius-1.0
Icosphere, and selecting by type sweeps it in. On a ~0.5-radius character that decoy
*doubles* the measured bounding sphere, so a probe written the naive way would report
proportions for a figure-plus-phantom-ball and read as authoritative while doing it.

No verdict is emitted. There is no `is_character` field and no threshold, because
whether the figure is the right character is canon and the Director's to judge.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from armature_core import blender_scene  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402
from armature_core.subject import extent_summary  # noqa: E402


def require_openable(paths):
    """`paths` if every one is a file, else raise - BEFORE the population is built.

    F-5b3ead49, wave 12. `probe_one` returned `{"exists": False, "error": "file not
    found"}` for a path that is not a file, `main` never inspected it, and the sentinel's
    `n` was `len(records)` - the count of ARGUMENTS. MEASURED:
    `probe_subject.py -- --out=<tmp> --glb=nope.glb --glb=also_missing.glb` printed
    `PROBE_SUBJECT_OK {"json": ".../subject_extents.json", "n": 2}`, `main()` returned
    None, `raise SystemExit(main())` exited 0, and the written record carried two
    `"error": "file not found"` rows the sentinel did not mention.

    That is the rule E07 earned - "verify a success sentinel in the output, never the exit
    code alone" - answered with a sentinel saying two subjects were probed when zero were
    opened. `check_relift.py:185-187` already refuses outright on `not os.path.isfile(p)`;
    this is the same refusal, in the tool whose record marks premise 6 ("the subject is a
    character") MEASURED.

    Distinct from the closed F-f3cd559e, which stopped EMPTY `--glb` values from joining
    the population: a named-but-absent path still did.
    """
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        raise ArmatureError(
            f"{len(missing)} of {len(paths)} named GLB(s) are not files: {missing}. Each "
            f"would have joined the probed population as an error row while the success "
            f"sentinel counted it as a subject probed, and a record whose rows are all "
            f"errors is not a measurement of anything")
    return paths


def probe_summary(records):
    """`n_probed` / `n_measured` / `n_errors`, derived from the records themselves.

    Carried from `probe_glb.py:305-311`, which already builds its whole summary out of the
    records and prints it in its own OK line - the honest shape existed one file over.
    """
    return {"n_probed": len(records),
            "n_measured": sum(1 for r in records if "error" not in r),
            "n_errors": sum(1 for r in records if "error" in r)}


def require_something_measured(records):
    """Refuse a run whose every row is an error, before the success sentinel is printed.

    The SUCCESS rule: `<PREFIX>_OK` is earned by a measurable effect, not by reaching the
    end of `main`. An import that contributes no render-visible mesh produces
    `{"error": "no render-visible geometry to measure"}`, which `require_openable` above
    cannot see - the file exists, it simply carries nothing this tool can measure.
    """
    summary = probe_summary(records)
    if summary["n_probed"] and not summary["n_measured"]:
        raise ArmatureError(
            f"this run measured 0 of {summary['n_probed']} subject(s); every row is an "
            f"error: {[r.get('error') for r in records]}. A PROBE_SUBJECT_OK line here "
            f"would report subjects probed that were never opened")
    return None


def probe_one(path):
    rec = {"path": path, "exists": os.path.isfile(path)}
    if not rec["exists"]:
        rec["error"] = "file not found"
        return rec

    rec["bytes"] = os.path.getsize(path)
    scene = blender_scene.reset_scene()
    # SEAM, wave 6 (core-solvers F-abcb06a8): `import_glb` takes `expected_fps` as a
    # REQUIRED keyword-only argument, because glTF key times are in SECONDS and the
    # importer resolves them against whatever rate the scene carries at that moment. This
    # tool measures a subject's EXTENT, not its timing, so it has no rate of its own to
    # assert; the scene's own rate is passed so the omission is a recorded choice rather
    # than a silent one, and the record says which rate was in force.
    expected_fps = int(blender_scene.scene_fps())
    meshes, armatures, info = blender_scene.import_glb(path, expected_fps=expected_fps)
    rec["import"] = info
    rec["expected_fps"] = expected_fps
    rec["expected_fps_source"] = (
        "the scene's own rate: this probe measures extent, not timing, so it asserts no "
        "rate of its own")

    visible = blender_scene.render_visible_meshes(scene, meshes)
    rec["mesh_objects_all"] = [o.name for o in meshes]
    rec["mesh_objects_render_visible"] = [o.name for o in visible]
    rec["mesh_objects_excluded"] = [o.name for o in meshes if o not in visible]
    rec["armature_names"] = [o.name for o in armatures]

    # `scene=` is passed even though `visible` is already a `render_visible_meshes`
    # result: the filter is idempotent, and the call then states which of the two
    # measurements this is instead of leaving that to the reader of the argument
    # (F-328aaea2). `world_bounds` with `scene` omitted IS the naive measurement.
    bounds = blender_scene.world_bounds(visible, scene=scene)
    if bounds is None:
        rec["error"] = "no render-visible geometry to measure"
        return rec
    center, half, radius = bounds
    rec["bbox_center"] = [float(v) for v in center]
    rec["bbox_half_extent"] = [float(v) for v in half]
    rec["bounding_sphere_radius"] = float(radius)
    rec["summary"] = extent_summary(half)

    # Reported because it is the E01 defect made visible rather than merely avoided:
    # what the naive `type == "MESH"` selection would have concluded on this asset.
    # `unfiltered_world_bounds` BY NAME, not `world_bounds` on an unfiltered list.
    # MEASURED 2026-09-04 (F-328aaea2): the naive row and the filtered row were the same
    # call with a different argument, so a later sweep giving `world_bounds` its scene at
    # every call site (or a default scene) would silently turn this line into a second
    # copy of the filtered one -- and the record would keep publishing a field labelled
    # `naive_type_mesh_selection` whose numbers are the filtered ones, with no test able
    # to see it. `blender_scene.unfiltered_world_bounds` exists for exactly this row and
    # names this file in its own docstring; its only caller was a rig-only script.
    naive = blender_scene.unfiltered_world_bounds(meshes)
    if naive is not None:
        rec["naive_type_mesh_selection"] = {
            "bbox_half_extent": [float(v) for v in naive[1]],
            "bounding_sphere_radius": float(naive[2]),
            "summary": extent_summary(naive[1]),
        }
    return rec


def parse_argv(argv, *, known=("out", "glb")):
    """`--out=<dir>` once and `--glb=<path>` one or more times. Anything else RAISES.

    MEASURED 2026-09-04 (F-f3cd559e). The loop this replaces was

        key, _, value = token[2:].partition("=")
        if key == "out": out_dir = value
        elif key == "glb": globs.append(value)

    which silently ignores what it does not recognise and silently ADMITS empty paths into
    the probed population. Measured on those lines verbatim: `--out=d --glb=a.glb --glb
    b.glb` (the space form) yields `['a.glb', '', '']` -- `--glb` alone gives key "glb"
    with value "", and `'b.glb'[2:]` is ALSO "glb", so the bare path contributes a second
    "" -- and the summary then reports `n_files` 3 for two files named. `--gbl=b.glb` (a
    typo) is dropped without a word; a bare positional adds another ""; `--help` is
    swallowed and the tool probes anyway. Each "" reaches `probe_one`, which records
    `{{"path": "", "exists": false, "clause_A_loads": false}}` -- a phantom member of a
    denominator that every number this tool exists to produce is computed over.

    `rig_character.parse_args` and `rig_parts.parse_args` already refuse an unknown token
    by name; this is that shape, carried.
    """
    out_dir, paths = None, []
    for token in argv:
        if not token.startswith("--"):
            raise ArmatureError(
                f"unexpected argument {token!r}: every value is attached to its flag with "
                f"'=' ({' '.join('--' + k + '=<value>' for k in known)}). The space form "
                f"is not accepted, because `token[2:]` on a bare path silently produced a "
                f"second empty member of the probed population")
        key, sep, value = token[2:].partition("=")
        key = key.replace("-", "_")
        if key not in known:
            raise ArmatureError(
                f"unknown argument {token!r}; known: {sorted(known)}")
        if not sep or not value:
            raise ArmatureError(
                f"{token!r} carries no value; an empty --{key} would join the population "
                f"as a file that does not exist and be counted in every denominator")
        if key == "out":
            if out_dir is not None:
                raise ArmatureError(
                    f"--out given twice ({out_dir!r} then {value!r}); one run writes one "
                    f"record")
            out_dir = value
        else:
            paths.append(value)
    if not out_dir or not paths:
        raise ArmatureError("usage: -- --out=<dir> --glb=<path> [--glb=<path> ...]")
    return out_dir, paths


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir, paths = parse_argv(argv)
    # F-5b3ead49: refused before the population is built, and before the directory exists.
    require_openable(paths)

    records = [probe_one(p) for p in paths]
    require_something_measured(records)
    summary = probe_summary(records)
    payload = {
        "tool": "probe_subject",
        "blender": bpy.app.version_string,
        "n_files": len(records),
        "summary": summary,
        "files": records,
    }
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "subject_extents.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    # The OK line reports what was OPENED, not what was named: `n_probed`, `n_measured`
    # and `n_errors` come from the records, the way `probe_glb.py:317` already does.
    print("PROBE_SUBJECT_OK " + json.dumps(dict(summary, json=out_path)))


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
            "tool": "probe_subject", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "probe_subject", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("PROBE_SUBJECT_HALT " + _line)
            sys.exit(_code)
