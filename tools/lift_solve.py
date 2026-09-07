#!/usr/bin/env python
"""lift_solve — key a solved lift onto the performer's rig and write a GLB.

    blender -b -P tools\\lift_solve.py -- --glb=<rigged.glb> --manifest=<rig_manifest.json>
                                          --motion=<solved.json> --out=<lifted.glb>
    blender -b -P tools\\lift_solve.py -- --glb=<rigged.glb> --manifest=<rig_manifest.json>
                                          --retarget=<clip.bvh> --bone-map=<map.json>
                                          --licence-row=<license-map-id> --out=<lifted.glb>

The Blender half of E09's Stage A. `armature_core.lift_solve` turns landmarks into
rotations with no bpy anywhere near it; this file only drives Blender with the answer,
gates the result, and exports. Same split, and the same reason, as `author_walk` and its
gait module: the arithmetic that every later measurement is quoted against must be
testable without a render.

`--motion` is the solver's own output, written by `tools/measure_lift.py`: a JSON record
carrying one entry per frame with `local` (bone -> 3x3) and `root` (the hips' translation
channel). Consuming the solver's numbers verbatim rather than re-deriving them here is
deliberate — a second implementation of the solve would be a second thing to be wrong.

Wave 34 (F-97da5a40): `--retarget` imports a BVH/FBX/GLB mocap clip, maps its armature
onto sitelist bone names through `--bone-map`, emits the same per-frame local-3x3 + root
record, and records root-translation representation + `--licence-row` in provenance
before any bake. Blender's importers are loaders, not retargeters
(`docs/research-grounding-movement-library.md` §4); this mode is that missing step.

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

TOOL_VERSION = "E09.2"

#: Root-translation representations a retarget run must name (movement-library §4).
#: BVH gives translation only on the root; whether that channel survives the map is a
#: retargeter setting, never a clip property — provenance must say which was chosen.
ROOT_TRANSLATION_REPS = ("hips_delta_world", "stripped")

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


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/lift_solve.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glb", required=True,
                    help="the RIGGED performer GLB the solved lift is keyed onto; read only")
    ap.add_argument("--manifest", required=True,
                    help="that rig's own rig_manifest.json -- the rest landmark table the "
                         "solve is expressed against, never typed in")
    ap.add_argument("--motion", default=None,
                    help="the SOLVED motion record (armature_core.lift_solve's output): "
                         "landmarks already turned into rotations, with no bpy involved. "
                         "Required unless --retarget is set")
    ap.add_argument("--retarget", default=None,
                    help="BVH / FBX / GLB mocap clip to retarget onto the performer "
                         "(F-97da5a40). Mutually exclusive with --motion; requires "
                         "--bone-map and --licence-row")
    ap.add_argument("--bone-map", default=None,
                    help="JSON object mapping sitelist bone name -> source armature bone "
                         "name. Required with --retarget. Unmapped sitelist bones hold "
                         "IDENTITY")
    ap.add_argument("--licence-row", default=None,
                    help="license-map.md row id for the clip (required with --retarget); "
                         "recorded in provenance before any bake")
    ap.add_argument("--root-translation", default="hips_delta_world",
                    choices=ROOT_TRANSLATION_REPS,
                    help="whether hips translation from the source root survives the "
                         "retarget (default hips_delta_world) or is stripped. Movement-"
                         "library §4: this is a retargeter setting, not a clip property")
    ap.add_argument("--motion-out", default=None,
                    help="optional path to write the emitted motion-record JSON (retarget "
                         "mode). Default: <out> with .motion.json suffix")
    ap.add_argument("--out", required=True,
                    help="the GLB to write, carrying the lifted action. Compensator: "
                         "delete it; owner: the executor session")
    # argparse eats leading minus signs: pass any negative value as --key=value.
    ap.add_argument("--fps", type=int, default=16,
                    help="frame rate the action is keyed at (default 16); glTF key times "
                         "are SECONDS, so this must match the record's own rate")
    return ap.parse_args(argv)


def require_retarget_flags(args):
    """Refuse overlapping or incomplete retarget / motion admissions (pure)."""
    if args.motion and args.retarget:
        raise ArmatureError(
            "--motion and --retarget both name a performance source; pass one",
            {"clause": "motion_and_retarget_both_set",
             "motion": args.motion, "retarget": args.retarget})
    if not args.motion and not args.retarget:
        raise ArmatureError(
            "one of --motion or --retarget is required",
            {"clause": "motion_or_retarget_required"})
    if args.retarget:
        missing = [f for f, v in (("--bone-map", args.bone_map),
                                  ("--licence-row", args.licence_row)) if not v]
        if missing:
            raise ArmatureError(
                f"--retarget requires {', '.join(missing)} so the map and the licence "
                f"row are on the record before any bake",
                {"clause": "retarget_missing_admission", "missing": missing,
                 "retarget": args.retarget})
    return args


def load_bone_map(path):
    """Sitelist -> source bone names. Refuses unknown sitelist keys and empty maps."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict) or not raw:
        raise ArmatureError(
            f"--bone-map={path!r} must be a non-empty JSON object "
            f"{{sitelist_name: source_bone_name}}",
            {"clause": "bone_map_not_an_object", "path": os.path.abspath(path)})
    known = set(sitelist.ALL_NAMES)
    unknown = sorted(k for k in raw if k not in known)
    if unknown:
        raise ArmatureError(
            f"--bone-map names sitelist bones this rig does not carry: {unknown}",
            {"clause": "bone_map_unknown_sitelist_bones", "unknown": unknown,
             "known": list(sitelist.ALL_NAMES)})
    out = {str(k): str(v) for k, v in raw.items()}
    return out


def retarget_provenance(*, source_path, source_sha, bone_map, licence_row,
                        root_translation, source_format):
    """The provenance block every retarget bake must carry (pure; movement-library §4)."""
    return {
        "mode": "retarget",
        "source_clip": {"path": os.path.abspath(source_path), "sha256": source_sha,
                        "format": source_format},
        "bone_map": dict(bone_map),
        "licence_row_id": licence_row,
        "root_translation_representation": root_translation,
        "root_translation_note": (
            "docs/research-grounding-movement-library.md §4 — root/hip translation is a "
            "retargeter setting, not a clip property; this run records which setting was "
            "chosen rather than assuming the clip arrived with traversal intact"),
    }


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


def _clip_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".bvh":
        return "bvh"
    if ext == ".fbx":
        return "fbx"
    if ext in (".glb", ".gltf"):
        return "gltf"
    raise ArmatureError(
        f"--retarget={path!r} must be a .bvh, .fbx, .glb or .gltf clip",
        {"clause": "retarget_unsupported_format", "path": os.path.abspath(path),
         "extension": ext})


def import_retarget_source(path, *, expected_fps):
    """Load a mocap clip into the current scene; return (armature_object, format, info)."""
    fmt = _clip_format(path)
    before_arms = {o.name for o in bpy.data.objects if o.type == "ARMATURE"}
    abspath = os.path.abspath(path)
    if fmt == "bvh":
        # Blender 5.x: bpy.ops.import_anim.bvh
        op = getattr(bpy.ops.import_anim, "bvh", None)
        if op is None:
            raise LiftGate(
                "this Blender build has no import_anim.bvh operator; cannot retarget BVH",
                {"clause": "bvh_importer_missing"})
        result = op(filepath=abspath)
        if "FINISHED" not in set(result):
            raise LiftGate(
                f"BVH import of {abspath} did not finish: {set(result)!r}",
                {"clause": "bvh_import_failed", "path": abspath, "status": list(result)})
        info = {"importer": "import_anim.bvh", "path": abspath}
    elif fmt == "fbx":
        op = getattr(bpy.ops.import_scene, "fbx", None)
        if op is None:
            raise LiftGate(
                "this Blender build has no import_scene.fbx operator; cannot retarget FBX",
                {"clause": "fbx_importer_missing"})
        result = op(filepath=abspath)
        if "FINISHED" not in set(result):
            raise LiftGate(
                f"FBX import of {abspath} did not finish: {set(result)!r}",
                {"clause": "fbx_import_failed", "path": abspath, "status": list(result)})
        info = {"importer": "import_scene.fbx", "path": abspath}
    else:
        _, arms, info = blender_scene.import_glb(abspath, expected_fps=expected_fps)
        if len(arms) != 1:
            raise LiftGate(
                f"retarget GLB imported {len(arms)} armature(s); need exactly one",
                {"clause": "retarget_glb_armature_count", "n": len(arms),
                 "names": [a.name for a in arms]})
        return arms[0], fmt, info

    after = [o for o in bpy.data.objects
             if o.type == "ARMATURE" and o.name not in before_arms]
    if len(after) != 1:
        # Some importers rename onto an existing datablock; fall back to any new-or-only.
        arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
        if len(arms) == 1:
            after = arms
        else:
            raise LiftGate(
                f"retarget import left {len(after)} new armature(s) "
                f"(scene total {len(arms)}); need exactly one source armature",
                {"clause": "retarget_source_armature_count",
                 "new": [a.name for a in after],
                 "all": [a.name for a in arms]})
    return after[0], fmt, info


def _mat3_from_matrix(M):
    """Upper-left 3x3 of a mathutils Matrix as nested tuples."""
    return ((float(M[0][0]), float(M[0][1]), float(M[0][2])),
            (float(M[1][0]), float(M[1][1]), float(M[1][2])),
            (float(M[2][0]), float(M[2][1]), float(M[2][2])))


def _source_action_range(arm_obj):
    """Inclusive (first, last) scene frames of the source armature's action, or None."""
    ad = arm_obj.animation_data
    if ad is None or ad.action is None:
        return None
    action = ad.action
    frames = []
    for fc in _action_fcurves(action):
        for kp in fc.keyframe_points:
            frames.append(kp.co[0])
    if not frames:
        return None
    return (int(math.floor(min(frames))), int(math.ceil(max(frames))))


def sample_retarget_frames(source_arm, bone_map, *, root_translation, scene):
    """Read source pose into lift_solve channel frames.

    For each mapped sitelist bone, the source pose-bone's `matrix_basis` rotation becomes
    the local 3x3 (rest-relative delta on the source skeleton). Unmapped bones stay
    IDENTITY. Hips translation is taken from the mapped hips source bone's basis location
    when `root_translation == 'hips_delta_world'`, else stripped to (0,0,0).
    """
    span = _source_action_range(source_arm)
    if span is None:
        raise LiftGate(
            f"retarget source armature {source_arm.name!r} carries no keyed action",
            {"clause": "retarget_source_has_no_action",
             "armature": source_arm.name})
    first, last = span
    missing_src = sorted({src for src in bone_map.values()
                          if src not in source_arm.pose.bones})
    if missing_src:
        raise LiftGate(
            f"--bone-map names source bones not on {source_arm.name!r}: {missing_src}",
            {"clause": "bone_map_source_bone_missing", "missing": missing_src,
             "source_bones": sorted(b.name for b in source_arm.pose.bones)})

    # Rest basis locations for hips delta.
    hips_src = bone_map.get("hips")
    rest_hips_loc = None
    if hips_src and root_translation == "hips_delta_world":
        scene.frame_set(first)
        bpy.context.view_layer.update()
        # Capture rest as frame-first basis location (BVH rest is typically frame 1 / T).
        pb = source_arm.pose.bones[hips_src]
        rest_hips_loc = pb.matrix_basis.to_translation().copy()

    frames = []
    for scene_f in range(first, last + 1):
        scene.frame_set(scene_f)
        bpy.context.view_layer.update()
        local = {name: [list(row) for row in LS.IDENTITY] for name in sitelist.ALL_NAMES}
        for site, src_name in bone_map.items():
            pb = source_arm.pose.bones[src_name]
            local[site] = [list(row) for row in _mat3_from_matrix(pb.matrix_basis)]
        root = [0.0, 0.0, 0.0]
        if (hips_src and root_translation == "hips_delta_world"
                and rest_hips_loc is not None):
            cur = source_arm.pose.bones[hips_src].matrix_basis.to_translation()
            root = [float(cur[i] - rest_hips_loc[i]) for i in range(3)]
        frames.append({"frame": scene_f - first, "local": local, "root": root})
    gate = LS.validate_motion_record(frames)
    return frames, gate, {"first_scene_frame": first, "last_scene_frame": last,
                          "n_frames": len(frames)}


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
            {"clause": "subject_is_not_one_mesh_and_one_armature",
             "meshes": [o.name for o in meshes], "armatures": [o.name for o in arms]})
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
    ev = {"gate": LiftGate.gate, "sub_gate": "SPACE",       # F-6381b9ff
          "andon": "LiftGate", "module_tol": GATE_SPACE_TOL,
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
        n_bones = len(sitelist.ALL_NAMES)
        n_frames = len(frames)
        raise LiftGate(
            f"keying produced no action at all after posing {n_bones} sites "
            f"across {n_frames} frames",
            {"clause": "keying_produced_no_action",
             "n_bones": n_bones, "n_frames": n_frames})
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
    ev = {"gate": LiftGate.gate, "sub_gate": "ARRIVED",     # F-6381b9ff
          "andon": "LiftGate",
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
    a = require_retarget_flags(parse_args())
    out_path = os.path.abspath(a.out)

    source_sha = _sha256(a.glb)
    rest, man = read_rest(a.manifest)
    diagonal = float(man["bbox"]["diagonal"])

    retarget_meta = None
    motion_sha = None
    motion_path_abs = None
    if a.retarget:
        # F-97da5a40: retarget mode — map source clip onto sitelist, emit motion record,
        # THEN key. Licence row and root-translation representation ride provenance
        # before the bake.
        bone_map = load_bone_map(a.bone_map)
        clip_sha = _sha256(a.retarget)
        scene = rig_character.fresh_scene(a.fps)
        # Performer first so fps andon is armed before either import settles.
        _, _, info = blender_scene.import_glb(a.glb, expected_fps=a.fps)
        mesh_obj, arm_obj = pick_subject(scene)
        src_arm, src_fmt, src_info = import_retarget_source(
            a.retarget, expected_fps=a.fps)
        frames, gate_record, span_info = sample_retarget_frames(
            src_arm, bone_map, root_translation=a.root_translation, scene=scene)
        retarget_meta = retarget_provenance(
            source_path=a.retarget, source_sha=clip_sha, bone_map=bone_map,
            licence_row=a.licence_row, root_translation=a.root_translation,
            source_format=src_fmt)
        retarget_meta["source_import"] = src_info
        retarget_meta["source_span"] = span_info
        record = {"tool": "lift_solve", "mode": "retarget",
                  "retarget": retarget_meta, "frames": frames}
        # Hide every MESH/ARMATURE that is not the performer so Gate OBJ and the export
        # see only the registered subject (clip companions must not ride the bake).
        for o in list(scene.objects):
            if o in (mesh_obj, arm_obj):
                continue
            if o.type in ("MESH", "ARMATURE"):
                o.hide_render = True
        motion_out = (os.path.abspath(a.motion_out) if a.motion_out
                      else os.path.splitext(out_path)[0] + ".motion.json")
        os.makedirs(os.path.dirname(motion_out) or ".", exist_ok=True)
        with open(motion_out, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        motion_path_abs = motion_out
        motion_sha = _sha256(motion_out)
    else:
        motion_sha = _sha256(a.motion)
        motion_path_abs = os.path.abspath(a.motion)
        record, frames, gate_record = read_motion(a.motion)
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
    os.makedirs(os.path.dirname(out_path), exist_ok=True)  # scripts make their own dirs
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    before_glb = rig_character.export_target_snapshot(out_path)
    export_result = bpy.ops.export_scene.gltf(
        **{k: v for k, v in wanted.items() if k in props})
    gate_glb = rig_character.gate_glb_written(
        out_path, result=export_result, before=before_glb, what="the lifted GLB")

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
    side_body = {
        "tool": "lift_solve", "tool_version": TOOL_VERSION,
        "solver_version": LS.TOOL_VERSION,
        "mode": "retarget" if a.retarget else "motion",
        "blender": blender_scene.blender_provenance(),
        "source": {"glb": os.path.abspath(a.glb), "sha256": source_sha,
                   "manifest": os.path.abspath(a.manifest),
                   "motion": motion_path_abs, "motion_sha256": motion_sha},
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
    }
    if retarget_meta is not None:
        side_body["retarget"] = retarget_meta
        side_body["source"]["retarget_clip"] = retarget_meta["source_clip"]
        side_body["source"]["licence_row_id"] = retarget_meta["licence_row_id"]
        side_body["source"]["root_translation_representation"] = (
            retarget_meta["root_translation_representation"])
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(side_body, fh, indent=2)

    ok = {
        "glb": out_path, "sha256": out_sha, "frames": len(frames), "fps": a.fps,
        "fcurves": n_curves, "gate_ARRIVED": gate_a["verdict"], "sidecar": side,
        "mode": side_body["mode"],
    }
    if motion_path_abs:
        ok["motion"] = motion_path_abs
    print("LIFT_SOLVE_OK " + json.dumps(ok))
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
            # `allow_nan=False` (F-897a3329): strict JSON, and it cannot raise here because
            # `_halt_keysafe` above has already replaced every non-finite float with its repr.
            _line = json.dumps(_sentinel, default=str, allow_nan=False)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("LIFT_SOLVE_HALT " + _line)
            sys.exit(_code)
