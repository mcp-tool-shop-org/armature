#!/usr/bin/env python
"""author_walk — E08's commission: the performance, keyed onto E07's skeleton.

    blender -b -P tools\\author_walk.py -- --glb=<rigged.glb> --manifest=<rig_manifest.json>
                                           --out=<walk.glb>

Takes the rigged performer and writes a new GLB carrying a walk -> stop -> emote action.
The gait itself is `armature_core.walk`, which has no bpy in it and is tested without
Blender; this file is only the driver, the gates, and the export.

--------------------------------------------------------------------------------
Read the exit code and you will be wrong

**A crashed `blender -b -P` exits 0** (E07, three live instances). This script prints
`AUTHOR_WALK_OK <json>` as its final line and nothing else does. A caller checks for that
sentinel in the output; `$LASTEXITCODE` proves nothing here.

--------------------------------------------------------------------------------
The gates, and what each one is the only witness to

* **the fps andon** — `blender_scene.import_glb(expected_fps=...)` raises if the scene
  rate was not pinned before the import. glTF stores key times in seconds, so importing
  at Blender's default 24 puts a 16 fps action on the wrong frames and *every other gate
  still passes* (E03 Ruling 9). It is the first thing that happens here.
* **Gate N** — every registered site is a bone, before and after the round trip.
* **Gate D** — the same inputs produce identical F-curves. Compared as **parsed keyframe
  values**, never as file bytes: a file-hash mismatch is not evidence a thing changed.
* **Gate F** — `walk.forward_kinematics` agrees with Blender's own evaluated pose. This is
  the only check on the ground truth itself, and the ground truth is what every later
  measurement is quoted against; an FK that is quietly wrong would make every one of them
  wrong in the same direction, which is the hardest kind of error to notice.
* **Gate A** — the authored performance ARRIVED: the re-imported GLB's posed skeleton
  matches the authored one at every frame, and its evaluated mesh matches at sampled
  frames. E03's law exactly — *where ground truth is authored, gate on the ground truth,
  not on distinctness*. A distinctness gate (G6) passes on a performance that arrived at
  two thirds of its magnitude, which is the defect that earned the law.
* **the OBJ gate** — nothing unregistered ships. Blender's glTF importer drops a hidden
  `Icosphere` into every import and one already reached a delivered GLB.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing the output GLB
and its sidecars under `outputs/`. Compensator: delete them; owner: the executor session.
The source GLB and the rig manifest are opened read-only and never written.
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
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import rig_character  # noqa: E402  (the OBJ gate lives there; enumerated, not rebuilt)
from armature_core import blender_scene, rig_gates, sitelist, walk  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E08.1"

#: Both tolerances are fractions of the CHARACTER'S OWN bounding diagonal, never absolute
#: metres — a global constant must not govern a local feature.
#:
#: **Gate F's was 1e-6 and that was wrong; MEASURED and corrected 2026-08-11.** 1e-6 of the
#: diagonal is *below the precision of the gate's own inputs*: the FK starts from the rig
#: manifest's float64 landmarks and Blender starts from the GLB's float32 bone matrices,
#: and those two disagree by up to **7.0e-7** (6.6e-7 of the diagonal) before a single
#: rotation is applied. Under the real gait, rotation and a four-deep float32 matrix chain
#: carry that to **6.1e-6** (5.7e-6 of the diagonal), which is what fired. A compositional
#: error — the thing this gate is for — misplaces a limb by a tenth of the character, four
#: orders of magnitude away. So the tolerance is the repo's existing round-trip unit,
#: `rig_gates`' 1e-4 of the diagonal: ~17x above the measured arithmetic and ~1e4 below any
#: real defect. The floor is recorded in the gate's own evidence every run.
GATE_F_TOL_FRAC = 1e-4
GATE_A_TOL_FRAC = 1e-4
#: Frames at which Gate A also compares the evaluated MESH, not just the skeleton. Bone
#: agreement does not prove the skin followed; a broken armature modifier would leave the
#: bones perfect and the body behind.
GATE_A_MESH_FRAMES = (0, 24, 47, 64)


class WalkGate(GateFailure):
    """A gate specific to authoring the walk."""

    gate = "WALK"


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
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=16)
    # argparse eats leading minus signs: pass these as --key=value.
    ap.add_argument("--n-walk", type=int, default=40)
    ap.add_argument("--n-decel", type=int, default=8)
    ap.add_argument("--n-gesture", type=int, default=12)
    ap.add_argument("--n-hold", type=int, default=5)
    ap.add_argument("--steps", type=int, default=5)
    return ap.parse_args(argv)


# ------------------------------------------------------------------------- helpers


def action_fcurves(action):
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


def fcurve_snapshot(action):
    """Every keyed value in an action, as plain sorted data.

    The comparison unit for Gate D. Parsed objects rather than bytes, because a GLB or a
    .blend can differ in a timestamp while the animation is identical, and can be
    identical in size while a channel is missing.
    """
    snap = {}
    for fc in action_fcurves(action):
        key = f"{fc.data_path}[{fc.array_index}]"
        snap[key] = [(round(kp.co[0], 9), round(kp.co[1], 12)) for kp in fc.keyframe_points]
    return {k: snap[k] for k in sorted(snap)}


def pick_subject(scene):
    """The one render-visible mesh and the one armature, or raise.

    An ambiguous subject **raises** rather than guessing: E07 measured a gate that opted
    out when the count was not 1 and reported `null` beside a verdict, which is worse than
    failing because nothing downstream can tell the difference.
    """
    meshes = [o for o in scene.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    arms = [o for o in scene.objects if o.type == "ARMATURE"]
    if len(visible) != 1 or len(arms) != 1:
        raise WalkGate(
            f"expected exactly one render-visible mesh and one armature, found "
            f"{len(visible)} mesh(es) {[o.name for o in visible]} and {len(arms)} "
            f"armature(s) {[o.name for o in arms]}",
            {"meshes": [o.name for o in meshes], "armatures": [o.name for o in arms]},
        )
    return visible[0], arms[0]


def read_performer(manifest_path):
    """The character's measured metrics, out of E07's rig manifest.

    Every length and every sign the gait uses comes from here. Nothing about this body is
    typed into the gait, which is the difference between a walk built for this performer
    and a walk built for an imagined one.
    """
    with open(manifest_path, encoding="utf-8") as fh:
        man = json.load(fh)
    marks = {}
    for name, rec in man["landmarks"].items():
        p = rec["p"] if isinstance(rec, dict) and "p" in rec else rec
        if isinstance(p, (list, tuple)) and len(p) == 3:
            marks[name] = [float(v) for v in p]
    facing = man["facing"]
    performer = walk.Performer(marks, facing["facing_y_sign"], facing["left_x_sign"])
    return performer, man


def apply_pose(arm_obj, pose, keyframe=None):
    """Set every gait bone's `matrix_basis` for one frame, optionally keying it.

    The basis is computed in CLOSED FORM — `rest^-1 @ (translate . rotate-about-head) @
    rest` — rather than assigned through `pose_bone.matrix`, which would need a depsgraph
    settle per bone per frame. 65 frames x 17 bones of settles on a 114k-vertex deform is
    not a recipe; it is a value that depends on when the settle happened.
    """
    for name in walk.GAIT_BONES:
        ch = pose[name]
        pb = arm_obj.pose.bones[name]
        pb.rotation_mode = "QUATERNION"
        rest = arm_obj.data.bones[name].matrix_local.copy()
        pivot = rest.to_translation()
        m = walk.rotation_matrix(ch["rx"], ch["ry"], ch["rz"])
        rot = Matrix(((m[0][0], m[0][1], m[0][2], 0.0),
                      (m[1][0], m[1][1], m[1][2], 0.0),
                      (m[2][0], m[2][1], m[2][2], 0.0),
                      (0.0, 0.0, 0.0, 1.0)))
        t = ch.get("translation") or (0.0, 0.0, 0.0)
        target = (Matrix.Translation(Vector(t)) @ Matrix.Translation(pivot) @ rot
                  @ Matrix.Translation(-pivot) @ rest)
        pb.matrix_basis = rest.inverted() @ target
        if keyframe is not None:
            pb.keyframe_insert(data_path="rotation_quaternion", frame=keyframe)
            pb.keyframe_insert(data_path="location", frame=keyframe)


def author(arm_obj, scene, gait, fps):
    """Key the whole performance. Returns (action, n_fcurves).

    E07's GLB ships with the probe arc keyed on one shoulder — MEASURED on import, one
    action named `performer_rigAction`. Unlinking it is not enough: the exporter's
    `ACTIONS` mode walks `bpy.data.actions`, so a merely-unassigned action can still be
    written into the GLB as a second animation, and a consumer picking the first one would
    play a 33-frame arm raise instead of the walk. The datablock is removed.
    """
    if arm_obj.animation_data is not None:
        arm_obj.animation_data_clear()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for name in walk.GAIT_BONES:
        pb = arm_obj.pose.bones[name]
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = Matrix.Identity(4)

    for rec in gait["frames"]:
        apply_pose(arm_obj, rec["pose"], keyframe=rec["scene_frame"])

    action = arm_obj.animation_data.action if arm_obj.animation_data else None
    if action is None:
        raise WalkGate("keying produced no action at all", {})
    n_curves = 0
    for fc in action_fcurves(action):
        n_curves += 1
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = len(gait["frames"])
    scene.frame_set(1)
    bpy.context.view_layer.update()
    return action, n_curves


def posed_heads(arm_obj, scene, n_frames):
    """World-space head position of every gait bone at every frame.

    World space, not armature space, because the glTF round trip is free to put the
    armature object's Y-up conversion wherever it likes; what has to survive is where the
    body is when the camera looks at it.
    """
    out = []
    for i in range(n_frames):
        scene.frame_set(1 + i)
        bpy.context.view_layer.update()
        M = arm_obj.matrix_world
        out.append({name: list(M @ arm_obj.pose.bones[name].matrix.to_translation())
                    for name in walk.GAIT_BONES})
    return out


def evaluated_verts(mesh_obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh_obj.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(ev.matrix_world, dtype=np.float64)
    out = co @ M[:3, :3].T + M[:3, 3]
    ev.to_mesh_clear()
    return out


def sampled_verts(mesh_obj, scene, frames):
    out = {}
    for i in frames:
        scene.frame_set(1 + i)
        bpy.context.view_layer.update()
        out[i] = evaluated_verts(mesh_obj)
    return out


# --------------------------------------------------------------------------- gates


def gate_d_determinism(snap_a, snap_b):
    """Gate D · ANDON — the same inputs produced identical F-curves."""
    ev = {"gate": "D", "n_channels_a": len(snap_a), "n_channels_b": len(snap_b)}
    if set(snap_a) != set(snap_b):
        only_a = sorted(set(snap_a) - set(snap_b))
        only_b = sorted(set(snap_b) - set(snap_a))
        raise WalkGate(
            f"authoring twice produced different channels: {len(only_a)} only in the "
            f"first pass {only_a[:6]}, {len(only_b)} only in the second {only_b[:6]}",
            dict(ev, only_a=only_a[:20], only_b=only_b[:20]))
    diffs = [k for k in snap_a if snap_a[k] != snap_b[k]]
    if diffs:
        k = diffs[0]
        raise WalkGate(
            f"authoring twice produced {len(diffs)} channel(s) with different keyed "
            f"values, e.g. {k}: {snap_a[k][:3]} vs {snap_b[k][:3]}. A performance that "
            f"is not reproducible is not a recipe",
            dict(ev, differing=diffs[:20]))
    ev["verdict"] = f"{len(snap_a)} channels identical across two independent authorings"
    ev["n_keys"] = sum(len(v) for v in snap_a.values())
    return ev


def gate_space_is_identity(arm_obj, tol=1e-9):
    """ANDON — the armature sits at the world origin, unrotated.

    The gait's every sign is stated in WORLD axes ("positive about +X carries a hanging
    limb toward +Y"), and it is applied through `matrix_basis`, which lives in ARMATURE
    space. Those are the same axes only while this matrix is identity. MEASURED identity
    on the E07 GLB — but measured once is not measured always, and a rotated armature
    would put the whole walk in the wrong plane while every other gate passed.
    """
    M = arm_obj.matrix_world
    ident = Matrix.Identity(4)
    worst = max(abs(M[i][j] - ident[i][j]) for i in range(4) for j in range(4))
    ev = {"gate": "SPACE", "matrix_world": [list(r) for r in M], "max_abs_delta": worst,
          "tolerance": tol}
    if worst > tol:
        raise WalkGate(
            f"the armature object's world matrix is not identity (max |delta| {worst:.3e}); "
            f"the gait authors rotations about WORLD axes through `matrix_basis`, which is "
            f"armature space, so the performance would be rotated out of its own plane", ev)
    ev["verdict"] = "armature space and world space coincide"
    return ev


def gate_f_fk_agreement(fk, heads, performer, arm_obj, diagonal,
                        tol_frac=GATE_F_TOL_FRAC):
    """Gate F · ANDON — the pure-Python ground truth is the pose Blender actually holds.

    The ground truth is what every later number in this experiment is quoted against — the
    foot-slip reading, the motion timing, the hips path. If my composition drifted from
    Blender's pose-bone semantics, every one of those would be wrong *in the same
    direction*, agree with each other perfectly, and look fine.

    **What it does NOT catch, stated because the first version of this docstring implied
    otherwise.** Both sides consume the same `pose` dict, so a wrong AXIS in the gait
    leaves the two in perfect agreement. Measured, not reasoned: swapping one bone's rx
    for ry moved the disagreement DOWN, from 6.10e-6 to 3.60e-6. A check that a defect
    makes *quieter* is not a check for that defect. The gait's own axes are held by
    `tests/test_walk.py` (the gesture must raise the right hand, out and forward; the knee
    must never bend forward; +X must carry a hanging limb toward +Y) and, last, by the
    Director's eye on the preview. Gate F is a check on the *bridge*, not on the gait.

    The gate reports its own noise floor beside its reading — the rest-head disagreement
    between the manifest's float64 landmarks and the GLB's float32 bone matrices, which is
    the precision of its inputs and the number below which it could never be set.
    """
    tol = tol_frac * diagonal
    floor = {"bone": None, "d": 0.0}
    for bone in walk.GAIT_BONES:
        d = math.dist(list(arm_obj.data.bones[bone].matrix_local.to_translation()),
                      performer.landmarks[walk.HEAD_LANDMARK[bone]])
        if d > floor["d"]:
            floor = {"bone": bone, "d": d}

    worst = {"bone": None, "frame": None, "d": 0.0}
    for i, (row, frame_heads) in enumerate(zip(fk, heads)):
        for bone in walk.GAIT_BONES:
            want = row.get("_heads", {}).get(bone)
            if want is None:
                continue
            d = math.dist(want, frame_heads[bone])
            if d > worst["d"]:
                worst = {"bone": bone, "frame": i, "d": d}
    ev = {"gate": "F", "tolerance_frac_of_diagonal": tol_frac, "tolerance": tol,
          "bbox_diagonal": diagonal, "worst": worst, "n_frames": len(heads),
          "input_precision_floor": floor,
          "floor_note": ("max |manifest landmark - GLB bone rest head|; the FK reads the "
                         "first and Blender the second, so no tolerance below this could "
                         "ever pass"),
          "does_not_catch": ("a wrong axis in the gait itself - both sides read the same "
                             "pose dict; held by tests/test_walk.py and the eye")}
    if worst["d"] > tol:
        raise WalkGate(
            f"the authored ground truth and Blender's evaluated pose disagree by "
            f"{worst['d']:.9f} at bone {worst['bone']!r} frame {worst['frame']} "
            f"(tolerance {tol:.9f}, input floor {floor['d']:.3e}); every measurement "
            f"quoted against this ground truth would carry the same error", ev)
    ev["verdict"] = (f"max {worst['d']:.3e} over {len(heads)} frames x "
                     f"{len(walk.GAIT_BONES)} bones, against an input floor of "
                     f"{floor['d']:.3e} and a tolerance of {tol:.3e}")
    return ev


def gate_a_arrival(authored_heads, reimported_heads, authored_verts, reimported_verts,
                   diagonal, tol_frac=GATE_A_TOL_FRAC):
    """Gate A · ANDON — the authored performance survived the glTF round trip.

    E03's law: *where ground truth is authored, gate on the ground truth, not on
    distinctness*. G6 counts distinct frames and passes happily on an action that landed
    on the wrong frames at the wrong magnitude — that is precisely what happened, and only
    the authored truth caught it. This compares pose to pose, frame by frame.
    """
    tol = tol_frac * diagonal
    ev = {"gate": "A", "tolerance_frac_of_diagonal": tol_frac, "tolerance": tol,
          "bbox_diagonal": diagonal, "n_frames": len(authored_heads)}

    if len(authored_heads) != len(reimported_heads):
        raise WalkGate(
            f"the export carries {len(reimported_heads)} frames, {len(authored_heads)} "
            f"were authored; a frame-count change through glTF is the fps defect's "
            f"signature", ev)

    worst = {"bone": None, "frame": None, "d": 0.0}
    for i, (a, b) in enumerate(zip(authored_heads, reimported_heads)):
        for bone in walk.GAIT_BONES:
            d = math.dist(a[bone], b[bone])
            if d > worst["d"]:
                worst = {"bone": bone, "frame": i, "d": d}
    ev["worst_bone"] = worst
    if worst["d"] > tol:
        raise WalkGate(
            f"the re-imported skeleton is {worst['d']:.9f} from the authored one at bone "
            f"{worst['bone']!r} frame {worst['frame']} (tolerance {tol:.9f}); the "
            f"performance that ships is not the performance that was authored", ev)

    # The skin clause is a POINT-SET comparison, not an index-wise one, and that is
    # measured rather than assumed: a glTF export re-splits vertices at attribute
    # discontinuities, and 114,610 authored vertices came back as **114,992**. The first
    # version compared the two arrays index for index and fired saying exactly that.
    #
    # `rig_gates.gate_p_round_trip_positions` was written for this in E07 and was tried
    # first — enumerate before commissioning. It does not fit HERE, and the reason is
    # worth the line: it assumes the two position sets are bit-identical and only falls
    # back to a brute-force O(n*m) nearest-neighbour search for the few that are not. That
    # holds at the REST pose. A POSED mesh is skinned through float32 bone matrices that
    # differ by ~1e-6 across the round trip, so essentially every position lands in the
    # slow path — 20,000 probes against 114,992 references per frame, per direction. It
    # ran past two minutes and was stopped. Blender ships a KD-tree; it is the right
    # instrument for a set comparison whose members do not match exactly.
    from mathutils import kdtree  # local: only this clause needs it

    def hausdorff(src, dst):
        tree = kdtree.KDTree(len(dst))
        for i, p in enumerate(dst):
            tree.insert(Vector((float(p[0]), float(p[1]), float(p[2]))), i)
        tree.balance()
        worst_d, worst_i = 0.0, None
        for i, p in enumerate(src):
            _, _, d = tree.find(Vector((float(p[0]), float(p[1]), float(p[2]))))
            if d > worst_d:
                worst_d, worst_i = d, i
        return worst_d, worst_i

    mesh_clause = {}
    worst_mesh = {"frame": None, "d": 0.0}
    for i in sorted(authored_verts):
        a, b = authored_verts[i], reimported_verts[i]
        d_ab, i_ab = hausdorff(a, b)
        d_ba, i_ba = hausdorff(b, a)
        rec = {"n_authored": int(len(a)), "n_reimported": int(len(b)),
               "authored_to_reimported": d_ab, "reimported_to_authored": d_ba,
               "worst_vertex": {"authored_index": i_ab, "reimported_index": i_ba}}
        mesh_clause[i] = rec
        d = max(d_ab, d_ba)
        if d > worst_mesh["d"]:
            worst_mesh = {"frame": i, "d": d}
    ev["mesh_clause"] = mesh_clause
    ev["worst_mesh"] = worst_mesh
    ev["mesh_frames_checked"] = sorted(authored_verts)
    ev["mesh_clause_note"] = ("symmetric Hausdorff over evaluated world positions; both "
                              "directions, because a one-way check passes on an export "
                              "that dropped half the body")
    if worst_mesh["d"] > tol:
        raise WalkGate(
            f"the re-imported SKIN is {worst_mesh['d']:.9f} from the authored one at "
            f"frame {worst_mesh['frame']} (tolerance {tol:.9f}) while the bones agree "
            f"to {worst['d']:.3e}; the skeleton survived the round trip and the body "
            f"did not", ev)

    ev["verdict"] = (f"bones max {worst['d']:.3e}, skin max {worst_mesh['d']:.3e} over "
                     f"{len(mesh_clause)} sampled frames, across "
                     f"{len(authored_heads)} frames")
    return ev


# ----------------------------------------------------------------------------- main


def main():
    started = time.time()
    args = parse_args()
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)  # scripts make their own dirs

    source_sha = _sha256(args.glb)

    # ---- the fps andon. The rate is pinned on an EMPTY scene, before the import, and
    # `import_glb` raises if it is not. Everything else in this file depends on it.
    scene = rig_character.fresh_scene(args.fps)
    meshes, arms, info = blender_scene.import_glb(args.glb, expected_fps=args.fps)
    mesh_obj, arm_obj = pick_subject(scene)

    gate_n_pre = rig_gates.gate_n_names(
        sorted(b.name for b in arm_obj.data.bones), sitelist.ALL_NAMES,
        "the imported rigged GLB")
    gate_space = gate_space_is_identity(arm_obj)

    performer, rig_manifest = read_performer(args.manifest)
    diagonal = float(rig_manifest["bbox"]["diagonal"])
    params = walk.GaitParams(n_walk=args.n_walk, n_decel=args.n_decel,
                             n_gesture=args.n_gesture, n_hold=args.n_hold,
                             steps=args.steps)
    gait = walk.build_gait(performer, params)
    n_frames = len(gait["frames"])
    fk = walk.forward_kinematics(performer, gait)

    # The FK rows carry landmark positions; Gate F needs bone HEADS, so they are derived
    # from the same deltas rather than re-derived differently inside the gate.
    for row, h in zip(fk, _fk_heads(performer, gait)):
        row["_heads"] = h

    # ---- Gate D. Author, snapshot, wipe, author again, compare parsed keys.
    action, n_curves = author(arm_obj, scene, gait, args.fps)
    snap_a = fcurve_snapshot(action)
    action_b, _ = author(arm_obj, scene, gait, args.fps)
    snap_b = fcurve_snapshot(action_b)
    gate_d = gate_d_determinism(snap_a, snap_b)

    # ---- Gate F, on the pose Blender is actually holding.
    authored_heads = posed_heads(arm_obj, scene, n_frames)
    gate_f = gate_f_fk_agreement(fk, authored_heads, performer, arm_obj, diagonal)
    authored_verts = sampled_verts(mesh_obj, scene,
                                   [f for f in GATE_A_MESH_FRAMES if f < n_frames])

    slip = walk.foot_slip(fk)

    # ---- export. The OBJ gate first: nothing unregistered ships.
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
    kwargs = {k: v for k, v in wanted.items() if k in props}
    bpy.ops.export_scene.gltf(**kwargs)

    # ---- Gate A, on a fresh import of what was just written. Same fps andon again: the
    # re-import is where the seconds-to-frames conversion happens a second time.
    scene2 = rig_character.fresh_scene(args.fps)
    blender_scene.import_glb(out_path, expected_fps=args.fps)
    mesh2, arm2 = pick_subject(scene2)
    gate_n_post = rig_gates.gate_n_names(
        sorted(b.name for b in arm2.data.bones), sitelist.ALL_NAMES,
        "the re-imported exported GLB")
    scene2.frame_start = 1
    scene2.frame_end = n_frames
    reimported_heads = posed_heads(arm2, scene2, n_frames)
    reimported_verts = sampled_verts(mesh2, scene2, sorted(authored_verts))
    gate_a = gate_a_arrival(authored_heads, reimported_heads, authored_verts,
                            reimported_verts, diagonal)

    out_sha = _sha256(out_path)
    record = {
        "tool": "author_walk", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "source": {"glb": os.path.abspath(args.glb), "sha256": source_sha,
                   "manifest": os.path.abspath(args.manifest)},
        "output": {"glb": out_path, "sha256": out_sha,
                   "bytes": os.path.getsize(out_path)},
        "import_info": info,
        "fps": args.fps, "frames": n_frames,
        "duration_s": n_frames / float(args.fps),
        "performer_measured": performer.as_dict(),
        "gait_params": gait["params"],
        "derived": gait["derived"],
        "omega_rad_per_frame": gait["omega_rad_per_frame"],
        "cadence_steps_per_second": args.fps * gait["omega_rad_per_frame"] / math.pi,
        "phase_boundaries": gait["phase_boundaries"],
        "n_fcurves": n_curves,
        "foot_slip": slip,
        "gates": {"fps_ordering": {"verdict": "PASS", "detail": "import_glb(expected_fps)"},
                  "N_pre": gate_n_pre, "N_post": gate_n_post, "OBJ": gate_obj,
                  "SPACE": gate_space, "D": gate_d, "F": gate_f, "A": gate_a},
        "ground_truth": [
            {"frame": r["frame"], "scene_frame": g["scene_frame"],
             "phase_name": g["phase_name"], "gait_speed": g["gait_speed"],
             "phase_rad": g["phase_rad"],
             "hips_translation": g["pose"]["hips"]["translation"],
             "pose_deg": {b: {k: v for k, v in ch.items() if k != "translation"}
                          for b, ch in g["pose"].items()},
             "world": {k: v for k, v in r.items() if k not in ("frame", "_heads")}}
            for r, g in zip(fk, gait["frames"])
        ],
        "elapsed_s": time.time() - started,
    }
    side = os.path.splitext(out_path)[0] + ".motion.json"
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)

    print("AUTHOR_WALK_OK " + json.dumps({
        "glb": out_path, "sha256": out_sha, "frames": n_frames, "fps": args.fps,
        "fcurves": n_curves, "keys": gate_d["n_keys"],
        "travel": round(gait["derived"]["total_forward_travel"], 6),
        "step": round(gait["derived"]["step_distance_derived"], 6),
        "cadence_steps_per_s": round(record["cadence_steps_per_second"], 4),
        "slide_fraction_total": round(slip["slide"]["slide_fraction_total"], 5),
        "gate_D": gate_d["verdict"], "gate_F": gate_f["verdict"],
        "gate_A": gate_a["verdict"], "motion": side,
    }))
    return 0


def _fk_heads(performer, gait):
    """Bone-head world positions per frame, from the same deltas `forward_kinematics`
    uses. Kept beside it rather than inside it because the heads are Gate F's business
    and the landmarks are the report's."""
    lm = performer.landmarks
    out = []
    for rec in gait["frames"]:
        pose = rec["pose"]
        deltas = {}
        row = {}
        for bone in walk.GAIT_BONES:
            ch = pose[bone]
            R = walk.rotation_matrix(ch["rx"], ch["ry"], ch["rz"])
            p0 = lm[walk.HEAD_LANDMARK[bone]]
            t_local = [p0[k] - sum(R[k][j] * p0[j] for j in range(3)) for k in range(3)]
            trans = ch.get("translation")
            if trans:
                t_local = [t_local[k] + trans[k] for k in range(3)]
            parent = walk.PARENT[bone]
            if parent is None:
                deltas[bone] = (R, t_local)
            else:
                Rp, tp = deltas[parent]
                deltas[bone] = (walk._mat_mul(Rp, R),
                                [sum(Rp[k][j] * t_local[j] for j in range(3)) + tp[k]
                                 for k in range(3)])
            Rb, tb = deltas[bone]
            row[bone] = [walk._mat_vec(Rb, p0)[k] + tb[k] for k in range(3)]
        out.append(row)
    return out


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        # A crashed `blender -b -P` exits 0 (E07, measured three times). The sentinel is
        # the contract; this prints the negative one so a reader sees a halt rather than
        # an absence, and still exits non-zero for anything that does check.
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("AUTHOR_WALK_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
