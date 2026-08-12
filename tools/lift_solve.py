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
from armature_core import blender_scene, rig_gates, sitelist  # noqa: E402
from armature_core import lift_solve as LS  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E09.1"

#: A fraction of the CHARACTER'S OWN bbox diagonal, never metres. The value is the repo's
#: existing round-trip unit (`rig_gates`, `author_walk`'s Gate A): measured there to sit
#: about 17x above the float32 arithmetic of a glTF round trip and four orders of magnitude
#: below any real compositional defect.
GATE_ARRIVED_TOL_FRAC = 1e-4


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


def gate_space_is_identity(arm_obj, tol=1e-9):
    """ANDON — armature space and world space coincide.

    Every rotation in the motion record is expressed in world axes; `matrix_basis` lives
    in armature space. A rotated armature would put the whole performance in the wrong
    plane with every other gate still green. Measured identity on the E07 GLB — but
    measured once is not measured always.
    """
    M = arm_obj.matrix_world
    ident = Matrix.Identity(4)
    worst = max(abs(M[i][j] - ident[i][j]) for i in range(4) for j in range(4))
    ev = {"gate": "SPACE", "max_abs_delta": worst, "tolerance": tol,
          "matrix_world": [list(r) for r in M]}
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


def gate_arrived(keyed, reimported, diagonal, tol_frac=GATE_ARRIVED_TOL_FRAC):
    """Gate ARRIVED · ANDON — the performance that ships is the one that was keyed."""
    tol = tol_frac * diagonal
    ev = {"gate": "ARRIVED", "tolerance": tol, "tolerance_frac_of_diagonal": tol_frac,
          "bbox_diagonal": diagonal, "n_frames": len(keyed)}
    if len(keyed) != len(reimported):
        raise LiftGate(
            f"the export carries {len(reimported)} frames and {len(keyed)} were keyed; a "
            f"frame-count change through glTF is the fps defect's signature", ev)
    worst = {"bone": None, "frame": None, "d": 0.0}
    for i, (a, b) in enumerate(zip(keyed, reimported)):
        for name in sitelist.ALL_NAMES:
            d = math.dist(a[name], b[name])
            if d > worst["d"]:
                worst = {"bone": name, "frame": i, "d": d}
    ev["worst"] = worst
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
    os.makedirs(os.path.dirname(out_path), exist_ok=True)  # scripts make their own dirs

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
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    bpy.ops.export_scene.gltf(**{k: v for k, v in wanted.items() if k in props})

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
                      "SPACE": gate_space, "ARRIVED": gate_a},
            "elapsed_s": time.time() - started,
        }, fh, indent=2)

    print("LIFT_SOLVE_OK " + json.dumps({
        "glb": out_path, "sha256": out_sha, "frames": len(frames), "fps": a.fps,
        "fcurves": n_curves, "gate_ARRIVED": gate_a["verdict"], "sidecar": side}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        # A crashed `blender -b -P` exits 0 (E07, measured three times). The sentinel is
        # the contract; this prints the negative one so a reader sees a halt rather than an
        # absence, and still exits non-zero for anything that does check.
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("LIFT_SOLVE_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
