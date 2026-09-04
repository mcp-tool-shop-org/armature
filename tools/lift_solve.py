#!/usr/bin/env python
"""lift_solve — key a solved lift onto the performer's rig and write a GLB.

    blender -b -P tools\\lift_solve.py -- --glb=<rigged.glb> --manifest=<rig_manifest.json>
                                          --motion=<solved.json> --out=<lifted.glb>

The Blender half of E09's Stage A. `armature_core.lift_solve` turns landmarks into
rotations with no bpy anywhere near it; this file only drives Blender with the answer,
gates the result, and exports. Same split, and the same reason, as `author_walk` and its
gait module: the arithmetic that every later measurement is quoted against must be
testable without a render.

`--motion` is the solver's own output, written by `tools/measure_lift.py`: a JSON record
carrying one entry per frame with `local` (bone -> 3x3) and `root` (the hips' translation
channel). Consuming the solver's numbers verbatim rather than re-deriving them here is
deliberate — a second implementation of the solve would be a second thing to be wrong.

--------------------------------------------------------------------------------
Read the exit code and you will be wrong

**A crashed `blender -b -P` exits 0** — E07 measured it three times. This script prints
`LIFT_SOLVE_OK <json>` as its final line and nothing else does. That sentinel is the
contract; `$LASTEXITCODE` proves nothing here.

--------------------------------------------------------------------------------
The gates, and what each one is the only witness to

* **the fps andon** — `blender_scene.import_glb(expected_fps=...)` raises if the scene
  rate was not pinned before the import. glTF stores key times in SECONDS, so importing at
  Blender's default 24 lands a 16 fps action on the wrong frames while every other check
  still passes (E03 Ruling 9).
* **Gate N** — every registered site is a bone, before and after the round trip. A rig
  that skins beautifully and names nothing is E01's result reproduced with more steps.
* **Gate SPACE** — the armature sits at the world origin, unrotated. The solved rotations
  are expressed in WORLD axes and applied through `matrix_basis`, which is ARMATURE space;
  those coincide only while this matrix is identity.
* **Gate ARRIVED** — the re-imported skeleton holds the pose that was keyed, frame by
  frame. E03's law: where the ground truth is authored, gate on the ground truth and not
  on distinctness. A distinctness check passes happily on a performance that arrived at
  two thirds of its magnitude, which is the defect that earned the law.
* **the OBJ gate** — nothing unregistered ships. Blender's glTF importer drops a hidden
  `Icosphere` into every import and one already reached a delivered GLB.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing the output GLB
and its sidecar under `outputs/`. Compensator: delete them; owner: the executor session.
The source GLB, the rig manifest and the motion record are opened read-only.
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
from mathutils import Matrix, Vector  # noqa: E402

import rig_character  # noqa: E402  (the OBJ gate lives there; enumerated, not rebuilt)
from armature_core import blender_scene, parts, rig_gates, sitelist  # noqa: E402
from armature_core import lift_solve as LS  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E09.1"

#: A fraction of the CHARACTER'S OWN bbox diagonal, never metres. The value is the repo's
#: existing round-trip unit (`rig_gates`, `author_walk`'s Gate A): measured there to sit
#: about 17x above the float32 arithmetic of a glTF round trip and four orders of magnitude
#: below any real compositional defect.
GATE_ARRIVED_TOL_FRAC = 1e-4

#: Gate SPACE's bound, as a module constant rather than an inline keyword default. Wave 12
#: (F-196c4257): a tolerance a caller can pass is a tolerance a caller can LOOSEN, and the
#: repo settled that shape in `armature_core.parts` — the module owns the bound and a
#: caller may only tighten it. `parts.tightened` reads `None` as "use the module's own".
GATE_SPACE_TOL = 1e-9


class LiftGate(GateFailure):
    """A gate specific to applying a solved lift."""

    gate = "LIFT"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--motion", required=True)
    ap.add_argument("--out", required=True)
    # argparse eats leading minus signs: pass any negative value as --key=value.
    ap.add_argument("--fps", type=int, default=16)
    return ap.parse_args(argv)


def read_rest(manifest_path):
    """The rig's own landmark table, out of E07's manifest. Never typed in."""
    with open(manifest_path, encoding="utf-8") as fh:
        man = json.load(fh)
    rest = {}
    for name, rec in man["landmarks"].items():
        p = rec["p"] if isinstance(rec, dict) and "p" in rec else rec
        if isinstance(p, (list, tuple)) and len(p) == 3:
            rest[name] = tuple(float(v) for v in p)
    return rest, man


def read_motion(path):
    """The solver's frames, validated by the pure module's own andon.

    The check lives in `armature_core.lift_solve.validate_motion_record` rather than here
    so it can be exercised without a render — enumerate before commissioning, and a gate
    that only runs inside Blender is a gate nobody can test.
    """
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    frames = rec.get("frames") or []
    gate = LS.validate_motion_record(frames)
    return rec, frames, gate


def pick_subject(scene):
    """The one render-visible mesh and the one armature, or raise.

    An ambiguous subject raises rather than guessing: E07 measured a gate that opted out
    when the count was not 1 and reported `null` beside a verdict, which is worse than
    failing because nothing downstream can tell the difference.
    """
    meshes = [o for o in scene.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    arms = [o for o in scene.objects if o.type == "ARMATURE"]
    if len(visible) != 1 or len(arms) != 1:
        raise LiftGate(
            f"expected exactly one render-visible mesh and one armature, found "
            f"{len(visible)} mesh(es) and {len(arms)} armature(s)",
            {"meshes": [o.name for o in meshes], "armatures": [o.name for o in arms]})
    return visible[0], arms[0]


def gate_space_is_identity(arm_obj, tol=None):
    """ANDON — armature space and world space coincide.

    Every rotation in the motion record is expressed in world axes; `matrix_basis` lives
    in armature space. A rotated armature would put the whole performance in the wrong
    plane with every other gate still green. Measured identity on the E07 GLB — but
    measured once is not measured always.

    **Two wave-12 clauses, both from the same family.** (1) `tol` was a keyword defaulting
    to `1e-9` with no tightening guard; it now runs through `parts.tightened` against
    `GATE_SPACE_TOL`, so a caller may only NARROW it — the shape `armature_core.lift_solve.
    gate_round_trip` already carries (F-196c4257). (2) `max(...)` over a matrix carrying a
    NaN element returns whatever the comparison chain happens to hold, and `worst > tol` is
    False for a NaN in BOTH directions, so a rotated-out-of-plane armature with one
    unreadable element read as a PASS. Every element goes through `parts.require_finite`
    before the maximum is taken (F-524f0a25); it is the one implementation of wave 10's
    rule 4 and it raises THIS gate's andon into THIS gate's evidence dict.
    """
    M = arm_obj.matrix_world
    ident = Matrix.Identity(4)
    ev = {"gate": "SPACE", "andon": "LiftGate", "module_tol": GATE_SPACE_TOL,
          "tol_requested": tol, "matrix_world": [list(r) for r in M]}
    tol = parts.tightened("tol", tol, GATE_SPACE_TOL, LiftGate, ev)
    deltas = []
    for i in range(4):
        for j in range(4):
            deltas.append(parts.require_finite(
                f"matrix_world[{i}][{j}]_abs_delta", abs(M[i][j] - ident[i][j]),
                LiftGate, ev, positive=False))
    worst = max(deltas)
    ev.update({"max_abs_delta": worst, "tolerance": tol})
    if worst > tol:
        raise LiftGate(
            f"the armature object's world matrix is not identity (max |delta| {worst:.3e}); "
            f"the solved rotations are world-axis and are applied through `matrix_basis`, "
            f"which is armature space, so the performance would be rotated out of plane",
            ev)
    ev["verdict"] = "armature space and world space coincide"
    return ev


def apply_pose(arm_obj, frame_rec, rest, keyframe=None):
    """Set every registered bone's `matrix_basis` for one frame, optionally keying it.

    Closed form — `rest^-1 @ (translate . rotate-about-head) @ rest` — rather than through
    `pose_bone.matrix`, which would need a depsgraph settle per bone per frame. Frames x
    bones of settles on a 114k-vertex deform is not a recipe; it is a value that depends on
    when the settle happened.
    """
    root = frame_rec.get("root") or (0.0, 0.0, 0.0)
    for name in sitelist.ALL_NAMES:
        m = frame_rec["local"][name]
        pb = arm_obj.pose.bones[name]
        pb.rotation_mode = "QUATERNION"
        bone_rest = arm_obj.data.bones[name].matrix_local.copy()
        pivot = bone_rest.to_translation()
        rot = Matrix(((m[0][0], m[0][1], m[0][2], 0.0),
                      (m[1][0], m[1][1], m[1][2], 0.0),
                      (m[2][0], m[2][1], m[2][2], 0.0),
                      (0.0, 0.0, 0.0, 1.0)))
        t = Vector(root) if name == "hips" else Vector((0.0, 0.0, 0.0))
        target = (Matrix.Translation(t) @ Matrix.Translation(pivot) @ rot
                  @ Matrix.Translation(-pivot) @ bone_rest)
        pb.matrix_basis = bone_rest.inverted() @ target
        if keyframe is not None:
            pb.keyframe_insert(data_path="rotation_quaternion", frame=keyframe)
            pb.keyframe_insert(data_path="location", frame=keyframe)


def author(arm_obj, scene, frames, rest, fps):
    """Key the whole solved performance. Returns (action, n_fcurves).

    E07's GLB ships with the probe arc keyed on one shoulder. Unlinking it is not enough:
    the exporter's `ACTIONS` mode walks `bpy.data.actions`, so a merely-unassigned action
    is still written into the GLB as a second animation and a consumer picking the first
    would play an arm raise instead of the lift. The datablock is removed.
    """
    if arm_obj.animation_data is not None:
        arm_obj.animation_data_clear()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for name in sitelist.ALL_NAMES:
        pb = arm_obj.pose.bones[name]
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = Matrix.Identity(4)

    for i, fr in enumerate(frames):
        apply_pose(arm_obj, fr, rest, keyframe=1 + i)

    action = arm_obj.animation_data.action if arm_obj.animation_data else None
    if action is None:
        raise LiftGate("keying produced no action at all", {})
    n = 0
    for fc in _action_fcurves(action):
        n += 1
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = len(frames)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    return action, n


def _action_fcurves(action):
    """Both Action APIs. Blender 5.2's slotted actions replaced the flat `fcurves` list
    with layers -> strips -> channelbags; the attribute's absence is the discriminator,
    measured on this rig in `make_test_armature.py` and reused rather than re-derived."""
    flat = getattr(action, "fcurves", None)
    if flat is not None:
        return list(flat)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cbag in getattr(strip, "channelbags", []):
                out.extend(cbag.fcurves)
    return out


def posed_heads(arm_obj, scene, n_frames):
    """World-space head position of every registered bone at every frame.

    World space, not armature space: the glTF round trip is free to put the armature
    object's Y-up conversion wherever it likes, and what has to survive is where the body
    is when the camera looks at it.
    """
    out = []
    for i in range(n_frames):
        scene.frame_set(1 + i)
        bpy.context.view_layer.update()
        M = arm_obj.matrix_world
        out.append({n: list(M @ arm_obj.pose.bones[n].matrix.to_translation())
                    for n in sitelist.ALL_NAMES})
    return out


def gate_arrived(keyed, reimported, diagonal, tol_frac=None):
    """Gate ARRIVED · ANDON — the performance that ships is the one that was keyed.

    **Wave 12, F-524f0a25 — measured, not reasoned.** `worst` was seeded `{'d': 0.0}` and
    updated only when `d > worst['d']`. `math.dist` over a NaN coordinate returns NaN and
    `nan > 0.0` is False, so every frame was skipped, `worst['d']` stayed 0.0, and
    `0.0 > tol` was False: a performance in which EVERY site was `(nan, nan, nan)` returned
    the strongest statement this gate can make — `"verdict": "max 0.000e+00 over 1 frames"`
    — about a comparison in which no number was compared. Each distance now goes through
    `armature_core.parts.require_finite`, the repo's one implementation of wave 10's rule 4
    (a verdict on a non-finite number is a refusal, never a PASS); it raises this gate's
    own andon with the NaN in this gate's own evidence.

    The sentinel is unreadable in the other direction too: `worst['d'] == 0.0` means either
    "every site arrived exactly" or "nothing was compared", and those are different claims.
    `n_compared` counts the comparisons the gate actually made and a non-empty population
    that produced none is refused — the honest form of the `worst['bone'] is None` clause,
    which would otherwise fire on a perfect arrival.

    **The tolerance is this module's** (F-196c4257): `tol_frac` was a plain keyword
    defaulting to `GATE_ARRIVED_TOL_FRAC`, so `gate_arrived(..., tol_frac=1e30)` on a
    9e9-unit displacement returned "max 9.000e+09 over 1 frames" and the manifest recorded
    that Gate ARRIVED ran and passed. It runs through `parts.tightened` now — the shape
    `armature_core.lift_solve.gate_round_trip` already carries — so a caller may only
    NARROW it, and the NaN clause comes with it since `tightened` refuses a non-finite
    request.
    """
    ev = {"gate": "ARRIVED", "andon": "LiftGate",
          "module_tol_frac": GATE_ARRIVED_TOL_FRAC, "tol_frac_requested": tol_frac,
          "bbox_diagonal": diagonal, "n_frames": len(keyed)}
    parts.require_finite("bbox_diagonal", diagonal, LiftGate, ev)
    tol_frac = parts.tightened("tol_frac", tol_frac, GATE_ARRIVED_TOL_FRAC, LiftGate, ev)
    tol = tol_frac * diagonal
    ev.update({"tolerance": tol, "tolerance_frac_of_diagonal": tol_frac})
    if len(keyed) != len(reimported):
        raise LiftGate(
            f"the export carries {len(reimported)} frames and {len(keyed)} were keyed; a "
            f"frame-count change through glTF is the fps defect's signature", ev)
    worst = {"bone": None, "frame": None, "d": 0.0}
    n_compared = 0
    for i, (a, b) in enumerate(zip(keyed, reimported)):
        for name in sitelist.ALL_NAMES:
            if name not in a or name not in b:
                continue
            d = parts.require_finite(f"distance[{name}]@frame{i}",
                                     math.dist(a[name], b[name]), LiftGate, ev,
                                     positive=False)
            n_compared += 1
            if d > worst["d"]:
                worst = {"bone": name, "frame": i, "d": d}
    ev["worst"] = worst
    ev["n_compared"] = n_compared
    if keyed and n_compared == 0:
        raise LiftGate(
            f"Gate ARRIVED compared 0 distances over {len(keyed)} keyed frame(s), so a "
            f"PASS would report 'max 0.000e+00' about a comparison that never happened; "
            f"the sentinel 0.0 and a perfect arrival are the same number and this gate may "
            f"not publish one as the other", ev)
    if worst["d"] > tol:
        raise LiftGate(
            f"the re-imported skeleton is {worst['d']:.9f} from the keyed one at bone "
            f"{worst['bone']!r} frame {worst['frame']} (tolerance {tol:.9f}); the "
            f"performance that ships is not the performance that was solved", ev)
    ev["verdict"] = f"max {worst['d']:.3e} over {len(keyed)} frames"
    return ev


def main():
    started = time.time()
    a = parse_args()
    out_path = os.path.abspath(a.out)

    source_sha, motion_sha = _sha256(a.glb), _sha256(a.motion)
    rest, man = read_rest(a.manifest)
    diagonal = float(man["bbox"]["diagonal"])
    record, frames, gate_record = read_motion(a.motion)

    # ---- the fps andon. The rate is pinned on an EMPTY scene, before the import.
    scene = rig_character.fresh_scene(a.fps)
    _, _, info = blender_scene.import_glb(a.glb, expected_fps=a.fps)
    mesh_obj, arm_obj = pick_subject(scene)

    gate_n_pre = rig_gates.gate_n_names(
        sorted(b.name for b in arm_obj.data.bones), sitelist.ALL_NAMES,
        "the imported rigged GLB")
    gate_space = gate_space_is_identity(arm_obj)

    action, n_curves = author(arm_obj, scene, frames, rest, a.fps)
    keyed_heads = posed_heads(arm_obj, scene, len(frames))

    gate_obj = rig_character.gate_objects_registered(scene, mesh_obj, arm_obj)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    wanted = {
        "filepath": out_path, "export_format": "GLB", "use_selection": False,
        "export_yup": True, "export_animations": True, "export_frame_range": True,
        "export_animation_mode": "ACTIONS", "export_skins": True,
        "export_def_bones": False, "export_apply": False, "export_materials": "EXPORT",
    }
    # THE DIRECTORY IS CREATED HERE, immediately above the first byte (F-d47095fa).
    # It used to sit at line 295 of `main()`, with 3 named refusal(s) stranded between
    # the two (307, 310, 315) -- none of which needs the directory. A run refused by any of
    # them left an empty output directory behind, which a reader scanning `outputs/` or
    # a re-run into the same `--out` reads as an attempt that produced nothing rather
    # than one that was refused. Pinned by `tests/test_instruments_amend_w10.py::
    # test_no_refusal_sits_between_the_output_directory_and_the_first_byte`.
    os.makedirs(os.path.dirname(out_path), exist_ok=True)  # scripts make their own dirs
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    bpy.ops.export_scene.gltf(**{k: v for k, v in wanted.items() if k in props})
    # F-9b2d4106, family carry: one implementation, `rig_character.gate_glb_written`.
    gate_glb = rig_character.gate_glb_written(out_path, what="the lifted GLB")

    # ---- the re-import is where the seconds-to-frames conversion happens a second time.
    scene2 = rig_character.fresh_scene(a.fps)
    blender_scene.import_glb(out_path, expected_fps=a.fps)
    _, arm2 = pick_subject(scene2)
    gate_n_post = rig_gates.gate_n_names(
        sorted(b.name for b in arm2.data.bones), sitelist.ALL_NAMES,
        "the re-imported exported GLB")
    scene2.frame_start, scene2.frame_end = 1, len(frames)
    gate_a = gate_arrived(keyed_heads, posed_heads(arm2, scene2, len(frames)), diagonal)

    out_sha = _sha256(out_path)
    side = os.path.splitext(out_path)[0] + ".lift.json"
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({
            "tool": "lift_solve", "tool_version": TOOL_VERSION,
            "solver_version": LS.TOOL_VERSION,
            "blender": blender_scene.blender_provenance(),
            "source": {"glb": os.path.abspath(a.glb), "sha256": source_sha,
                       "manifest": os.path.abspath(a.manifest),
                       "motion": os.path.abspath(a.motion), "motion_sha256": motion_sha},
            "output": {"glb": out_path, "sha256": out_sha,
                       "bytes": os.path.getsize(out_path)},
            "import_info": info, "fps": a.fps, "frames": len(frames),
            "duration_s": len(frames) / float(a.fps), "n_fcurves": n_curves,
            "motion_provenance": {k: v for k, v in record.items() if k != "frames"},
            "gates": {"fps_ordering": {"verdict": "PASS",
                                       "detail": "import_glb(expected_fps)"},
                      "MOTION_RECORD": gate_record,
                      "N_pre": gate_n_pre, "N_post": gate_n_post, "OBJ": gate_obj,
                      "SPACE": gate_space, "ARRIVED": gate_a,
                      "GLB_written": gate_glb},
            "elapsed_s": time.time() - started,
        }, fh, indent=2)

    print("LIFT_SOLVE_OK " + json.dumps({
        "glb": out_path, "sha256": out_sha, "frames": len(frames), "fps": a.fps,
        "fcurves": n_curves, "gate_ARRIVED": gate_a["verdict"], "sidecar": side}))
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
            "tool": "lift_solve", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "lift_solve", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("LIFT_SOLVE_HALT " + _line)
            sys.exit(_code)
