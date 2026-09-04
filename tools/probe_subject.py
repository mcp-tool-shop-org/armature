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

    bounds = blender_scene.world_bounds(visible)
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
    naive = blender_scene.world_bounds(meshes)
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
    os.makedirs(out_dir, exist_ok=True)

    records = [probe_one(p) for p in paths]
    payload = {
        "tool": "probe_subject",
        "blender": bpy.app.version_string,
        "n_files": len(records),
        "files": records,
    }
    out_path = os.path.join(out_dir, "subject_extents.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print("PROBE_SUBJECT_OK " + json.dumps({"json": out_path, "n": len(records)}))


def _halt_keysafe(value):
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
    if isinstance(value, dict):
        return {str(k): _halt_keysafe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_halt_keysafe(v) for v in value]
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
        traceback.print_exc()
        _detail = getattr(exc, "evidence", None)
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _sentinel = {
            "tool": "probe_subject",
            "outcome": ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                        else "REFUSED — the tool declined to proceed"
                        if isinstance(exc, ArmatureError)
                        else "FAILED — an unhandled error"),
            "gate": getattr(exc, "gate", None),
            "error": type(exc).__name__, "message": str(exc),
            "evidence": _halt_keysafe(_detail) if isinstance(_detail, dict) else None}
        # The sentinel and the exit code are the contract, and NEITHER may be deleted by a
        # failure to serialise the sentinel itself. `_code` is computed before anything that
        # can raise and delivered from a `finally`; the fallback line carries only values
        # that are already strings, so it cannot fail in turn.
        try:
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            _line = json.dumps({
                "tool": _sentinel["tool"], "outcome": _sentinel["outcome"], "gate": None,
                "error": _sentinel["error"], "message": _sentinel["message"],
                "evidence": None})
        finally:
            print("PROBE_SUBJECT_HALT " + _line)
            sys.exit(_code)
