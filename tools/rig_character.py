"""rig_character — give a canonical character mesh a rig whose bones carry anatomical names.

    blender -b --factory-startup -P tools\\rig_character.py -- --glb=<in.glb> --out=<dir>
    blender -b --factory-startup -P tools\\rig_character.py -- --glb=<in.glb> --out=<dir> --measure-only

E01 measured the whole reason this exists: four rigged GLBs on this machine, every one of
them naming its bones `bone_0 … bone_N`, **zero of 18 anatomical sites findable by name in
any of them**. Nothing about those files reports a problem — they import, they carry a skin,
they pose. They simply cannot be posed *on purpose*, because nothing in them says which bone
is the shoulder. E03 was designed to route around that gap and E06 measured that it cannot be
routed around. So this tool closes it: it places bones from landmarks measured on the mesh,
names them from a list committed before the first bone, skins with `ARMATURE_AUTO`, authors
E03's arm arc as a probe, and exports.

**The gates raise from inside this file**, before the manifest that would make a run look
finished — never behind a shell `&&`, never through an `assert`, with no skip flag anywhere:

* **Gate N** — every registered site names exactly one bone, and the rig carries nothing
  unregistered. Run twice: on the built armature, and again on the **re-imported export**,
  because the names that matter are the ones a consumer reads out of the GLB and
  `export_def_bones` alone would silently drop every non-deforming marker.
* **Gate P** — binding the mesh did not move it, within 1e-4 of the mesh's own bbox diagonal.
* **Gate D** — a second build from the same inputs produced the same rig, compared as parsed
  objects and never as bytes.

**Deformation under pose is NOT a gate.** Per-structure displacement statistics are written
to the manifest as diagnostics. Whether the deform is acceptable — whether he still looks
like *him* when his arm comes up — is the Director's judgement on the sheet, at his zoom, and
no number here approximates it.
"""

import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from armature_core import (  # noqa: E402
    binding, blender_scene, joints, landmarks, posearc, rig_gates, sitelist)
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "1.1.0"

#: Weld distance for the throwaway copy the joint-ball search runs on, as a fraction of the
#: subject's own bbox diagonal. glTF splits a vertex at every UV and normal seam, so the
#: duplicates sit at *identical* positions and any tiny epsilon recovers the asset's real
#: shells. Expressed per-structure so it is not a length in metres.
BALL_WELD_FRACTION = 1e-6

#: E03's authored arc, reused verbatim so E08 compares character-control against
#: wire-control on the same authored transform: rotate about +Y by -theta, 0 -> 90 degrees,
#: 33 keys, 16 fps. `arm_r_raise`'s own docstring defines the moving limb as "the arm named
#: _r in the generator (the +X side)" -- a label on a planar wire figure, not anatomy. Which
#: of this character's arms lies on +X is measured (`landmarks.facing`) and reported.
PROBE_ARC = "arm_r_raise"
PROBE_FRAMES = 33
PROBE_FPS = 16
PROBE_START_DEG = 0.0
PROBE_END_DEG = 90.0


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {"glb": None, "out": None, "measure_only": False, "bands": 200,
            "name": "performer", "mode": "skeleton", "binding": "rigid",
            "envelope_radii": "measured"}
    for token in argv:
        if token == "--measure-only":
            args["measure_only"] = True
            continue
        key, _, value = token[2:].partition("=")
        key = key.replace("-", "_")
        if key not in args:
            raise ArmatureError(f"unknown argument {token!r}; known: {sorted(args)}")
        args[key] = int(value) if key == "bands" else value
    if not args["glb"] or not args["out"]:
        raise ArmatureError("usage: -- --glb=<path> --out=<dir> [--measure-only] [--bands=N]")
    return args


# --------------------------------------------------------------------------- scene


def fresh_scene(fps):
    """Empty the scene and set the frame rate BEFORE anything else happens.

    **The fps-ordering law, E03 closing Ruling 9.** `prepare()` imported a GLB before the
    frame rate was set, so a 33-key action authored at 16 fps landed on frames 1-49 at
    Blender's default 24 and the render captured two thirds of the arc. glTF stores key
    times in *seconds*; every conversion between seconds and frames in this process reads
    `scene.render.fps`, so it is set first, on an empty scene, and nothing that follows can
    be authored against the wrong one.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = PROBE_FRAMES
    scene.frame_set(1)
    return scene


def world_verts(ob, mesh=None):
    me = mesh if mesh is not None else ob.data
    n = len(me.vertices)
    flat = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", flat)
    co = flat.reshape(n, 3)
    m = np.array(ob.matrix_world, dtype=np.float64)
    return co @ m[:3, :3].T + m[:3, 3]


def evaluated_world_verts(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        return world_verts(ev, me)
    finally:
        ev.to_mesh_clear()


def measure_subject(ob):
    """Premises 2 and 6, measured on import rather than inherited from the dispatch."""
    me = ob.data
    me.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.edges.ensure_lookup_table()
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    edges = np.array([[e.verts[0].index, e.verts[1].index] for e in bm.edges], dtype=np.int64)
    bm.free()

    # Union-find over the edge graph: how many disconnected shells the skinning solve
    # actually has to spread heat across. This is the premise the dispatch handed over as
    # "67 interior shells", and it is measured here rather than carried.
    n = len(me.vertices)
    parent = np.arange(n, dtype=np.int64)

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for a, b in edges:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra
    roots = np.array([find(i) for i in range(n)], dtype=np.int64)
    uniq, shell_id, sizes = np.unique(roots, return_inverse=True, return_counts=True)

    return {
        "object_name": ob.name,
        "vertices": n,
        "triangles": len(me.loop_triangles),
        "polygons": len(me.polygons),
        "edges": len(me.edges),
        "shells": int(len(uniq)),
        "non_manifold_edges": int(non_manifold),
        "boundary_edges": int(boundary),
        "watertight": bool(non_manifold == 0 and boundary == 0),
        "largest_shell_vertices": int(sizes.max()),
        "largest_shell_fraction": float(sizes.max() / n),
        "shells_over_1pct": int((sizes > 0.01 * n).sum()),
        "pre_existing_vertex_groups": len(ob.vertex_groups),
        "pre_existing_modifiers": [m.type for m in ob.modifiers],
        "matrix_world_is_identity": bool(ob.matrix_world == Matrix.Identity(4)),
    }, shell_id, sizes


def measure_joint_balls(ob, diagonal):
    """The subject's own sculpted ball-joints, found on a THROWAWAY welded copy.

    The mesh handed to the rig is never touched: `bmesh.from_mesh` reads into a private
    bmesh, the weld happens there, and it is freed without `to_mesh`. The balls come back as
    world-space points, which is all the skeleton needs — nothing downstream depends on the
    welded topology existing.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=BALL_WELD_FRACTION * diagonal)
    bm.verts.ensure_lookup_table()
    n = len(bm.verts)
    parent = np.arange(n, dtype=np.int64)

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for e in bm.edges:
        a, b = find(e.verts[0].index), find(e.verts[1].index)
        if a != b:
            parent[b] = a
    labels = np.array([find(i) for i in range(n)], dtype=np.int64)
    co = np.empty((n, 3), dtype=np.float64)
    for i, v in enumerate(bm.verts):
        co[i] = v.co
    bm.free()

    m = np.array(ob.matrix_world, dtype=np.float64)
    world = co @ m[:3, :3].T + m[:3, 3]
    shells = joints.describe_shells(world, labels)
    return joints.candidate_balls(shells), shells


def build_armature(scene, marks, name):
    arm_data = bpy.data.armatures.new(f"{name}_armature")
    arm_obj = bpy.data.objects.new(f"{name}_rig", arm_data)
    scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    try:
        for b in sitelist.BONES:
            head, tail = marks[b.head], marks[b.tail]
            eb = arm_data.edit_bones.new(b.name)
            eb.head = Vector(head)
            eb.tail = Vector(tail)
            eb.roll = 0.0
            eb.use_deform = b.deform
            if b.parent is not None:
                eb.parent = made[b.parent]
                eb.use_connect = False
            made[b.name] = eb
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")

    # Blender deletes zero-length bones on leaving edit mode without raising. Gate N would
    # catch the result as a missing site; naming it here makes the evidence legible.
    lengths = {b.name: float(b.length) for b in arm_data.bones}
    return arm_obj, lengths


#: Weight quantisation for the procedural arm. Only the blend band carries fractional
#: weights — rigid vertices are exactly 1.0 — and Blender's armature modifier normalises by
#: the accumulated weight, so this cannot move the bind pose. Recorded because it is a
#: property of the arm, not an implementation detail.
RIGID_WEIGHT_QUANTISATION = 1e-3


def _parent_to(mesh_obj, arm_obj, kind):
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.parent_set(type=kind)


def _set_envelopes(arm_obj, radii, distance_multiple):
    """Envelope radii from the MEASURED cross-section of the structure each bone runs through.

    Blender's defaults are absolute lengths — 0.1 head/tail radius, 0.25 envelope distance —
    on a figure 1.0 units tall. That is a global constant governing a local feature, and it
    is why the mechanism sweep measured a mean of 7.4 bone influences per vertex on this
    subject. Sized from the mesh instead; the multiple applied to the falloff is declared
    here rather than tuned against a coverage number.
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    applied = {}
    try:
        for eb in arm_obj.data.edit_bones:
            r = radii.get(eb.name)
            if r is None:                       # the non-deforming facial markers
                eb.head_radius = eb.tail_radius = 0.0
                eb.envelope_distance = 0.0
                applied[eb.name] = {"deform": False, "head_radius": 0.0,
                                    "tail_radius": 0.0, "envelope_distance": 0.0}
                continue
            eb.head_radius = eb.tail_radius = float(r)
            eb.envelope_distance = float(r) * distance_multiple
            applied[eb.name] = {"deform": True, "head_radius": float(r),
                                "tail_radius": float(r),
                                "envelope_distance": float(r) * distance_multiple}
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    return applied


def _write_weights(mesh_obj, weights, quantisation):
    """Push computed weights into vertex groups.

    Rigid vertices (weight exactly 1.0) go in one call per bone; only the blend band is
    quantised, and it is the small minority. A per-vertex loop over 400k vertices would move
    the same numbers far more slowly.
    """
    groups = {g.name: g for g in mesh_obj.vertex_groups}
    written = 0
    for name, w in weights.items():
        group = groups.get(name)
        if group is None:
            raise ArmatureError(
                f"no vertex group named {name!r} on the mesh; the armature was parented "
                f"without empty groups and there is nowhere to write weights"
            )
        full = np.flatnonzero(w >= 1.0)
        if len(full):
            group.add(full.tolist(), 1.0, "REPLACE")
            written += len(full)
        partial = np.flatnonzero((w > 0.0) & (w < 1.0))
        if len(partial):
            q = np.round(w[partial] / quantisation) * quantisation
            for value in np.unique(q):
                sel = partial[q == value]
                group.add(sel.tolist(), float(value), "REPLACE")
                written += len(sel)
    return written


def apply_binding(mesh_obj, arm_obj, mode, source, radii, envelope_distance_multiple=1.0,
                  envelope_radii="measured"):
    """Bind the mesh by one named route. Returns (seconds, a record of what was applied)."""
    t0 = time.time()
    if mode == "auto":
        # FALSIFIED on this subject in round 1. Kept runnable, with the reason attached.
        _parent_to(mesh_obj, arm_obj, "ARMATURE_AUTO")
        rec = {"binding": "auto", "operator": "parent_set(ARMATURE_AUTO)",
               "note": ("Blender bone-heat weighting. Measured on this subject to produce "
                        "ZERO weights across all 17 deform groups — see E07 round 1.")}
    elif mode == "envelope":
        # TWO configurations, both runnable, because they are genuinely different arms and
        # the difference was measured rather than argued:
        #
        #   measured — head/tail radius from the structure's own cross-section, falloff a
        #     declared multiple of it. 1.88 bone influences per vertex, and **1,162 of
        #     399,140 vertices (0.29 %) left unweighted**, all in the fingers and toes that
        #     stick out past every envelope. glTF then adds a `neutral_bone` to hold them
        #     and **Gate N fires** on the unregistered name.
        #   default — Blender's own absolute radii, untouched. 100 % coverage, and 9.86
        #     influences per vertex against a weight sum of 7.7.
        #
        # The advisor's ruling named "ARMATURE_ENVELOPE (measured 100% coverage)", which is
        # the DEFAULT configuration as the mechanism sweep ran it. This seat substituted
        # measured radii on the global-constant law without flagging it first; both are run
        # and reported rather than one being quietly chosen.
        if envelope_radii == "measured":
            applied = _set_envelopes(arm_obj, radii, envelope_distance_multiple)
            source_note = ("measured cross-section of the structure each bone runs through "
                           "(landmarks.bone_radii); falloff a declared multiple of it")
        elif envelope_radii == "default":
            applied = {b.name: {"deform": bool(b.use_deform),
                                "head_radius": float(b.head_radius),
                                "tail_radius": float(b.tail_radius),
                                "envelope_distance": float(b.envelope_distance)}
                       for b in arm_obj.data.bones}
            source_note = ("Blender's own defaults, untouched — absolute lengths on a figure "
                           "1.0 units tall, which is a global constant governing a local "
                           "feature and is recorded as such")
        else:
            raise ArmatureError(
                f"unknown --envelope-radii={envelope_radii!r}; known: measured, default")
        _parent_to(mesh_obj, arm_obj, "ARMATURE_ENVELOPE")
        rec = {
            "binding": "envelope", "operator": "parent_set(ARMATURE_ENVELOPE)",
            "envelope_radii": envelope_radii,
            "radii_source": source_note,
            "envelope_distance_multiple_of_bone_radius":
                envelope_distance_multiple if envelope_radii == "measured" else None,
            "envelopes_applied": applied,
            "smoothing_applied": False,
            "smoothing_note": ("No vertex-group smoothing was run. Envelope weights are "
                               "already a distance falloff, and whether an additional blur "
                               "improves the read is a judgement this seat does not make."),
        }
    elif mode == "rigid":
        _parent_to(mesh_obj, arm_obj, "ARMATURE_NAME")
        bones = [{"name": b.name, "head": tuple(b.head_local), "tail": tuple(b.tail_local),
                  "parent": b.parent.name if b.parent else None}
                 for b in arm_obj.data.bones if b.use_deform]
        weights, diag = binding.rigid_segment_weights(source, bones, radii)
        written = _write_weights(mesh_obj, weights, RIGID_WEIGHT_QUANTISATION)
        rec = {"binding": "rigid",
               "operator": "parent_set(ARMATURE_NAME) + computed weights",
               "assignment": diag, "weight_entries_written": written,
               "weight_quantisation": RIGID_WEIGHT_QUANTISATION,
               "radii_source": "measured cross-section (landmarks.bone_radii)"}
    else:
        raise ArmatureError(f"unknown binding {mode!r}; known: auto, envelope, rigid")
    return time.time() - t0, rec


def read_weights(ob, n_verts):
    """Per-vertex-group weight arrays, plus the sums that a failed heat solve shows up in."""
    idx_to_name = {g.index: g.name for g in ob.vertex_groups}
    w = {name: np.zeros(n_verts, dtype=np.float64) for name in idx_to_name.values()}
    for i, v in enumerate(ob.data.vertices):
        for ge in v.groups:
            name = idx_to_name.get(ge.group)
            if name is not None:
                w[name][i] = ge.weight
    return w


def bone_table(arm_obj):
    return {b.name: {"head": tuple(b.head_local), "tail": tuple(b.tail_local),
                     "roll": 0.0, "parent": b.parent.name if b.parent else None,
                     "use_deform": bool(b.use_deform)}
            for b in arm_obj.data.bones}


def build_pass(glb_path, name, bands, label, bind=True, envelope_radii="measured"):
    """One complete build, from a fresh scene to a rig.

    With `bind=False` the mesh is never parented to the armature: the skeleton is placed and
    exported, and nothing is attached to it. That is the **skeleton-approval** mode the
    Director gated the experiment at — *"Nothing moves forward until I approve the
    skeleton."* Gate P's liveness clause deliberately does not run there, because there is no
    binding for it to be about; a liveness reading on an unbound mesh would be a check
    reporting on a thing that does not exist yet.
    """
    scene = fresh_scene(PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=glb_path)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(meshes) != 1:
        raise ArmatureError(
            f"expected exactly one mesh object in the subject, found {len(meshes)}: "
            f"{[o.name for o in meshes]}. Which one carries the character is a question "
            f"this tool will not answer by picking the biggest"
        )
    mesh_obj = meshes[0]
    premise2 = {
        "pre_existing_armatures": [o.name for o in armatures],
        "pre_existing_empties": [o.name for o in bpy.data.objects if o.type == "EMPTY"],
        "pre_existing_actions": [a.name for a in bpy.data.actions],
        "carries_a_rig": bool(armatures) or any(o.type == "EMPTY" for o in bpy.data.objects),
    }
    premise6, shell_id, shell_sizes = measure_subject(mesh_obj)

    source = world_verts(mesh_obj)
    lo, hi = source.min(axis=0), source.max(axis=0)
    diagonal = float(np.linalg.norm(hi - lo))

    t0 = time.time()
    lm = landmarks.derive(source, n_bands=bands)
    t_landmarks = time.time() - t0

    # The subject's own sculpted ball-joints, and the pivots moved onto them. Placement by
    # proportion is the fallback for sites that carry no marker, never the default: this
    # mannequin sculpts a ball at every limb joint and those balls are the ground truth.
    t0 = time.time()
    balls, shells = measure_joint_balls(mesh_obj, diagonal)
    heuristic_marks = dict(lm["landmarks"])
    snapped, offsets = joints.snap_sites_to_balls(lm, balls)
    lm["landmarks"] = snapped
    t_balls = time.time() - t0
    ruling = joints.verdict(offsets)

    arm_obj, bone_lengths = build_armature(scene, snapped, name)
    radii = landmarks.bone_radii(lm, sitelist.BONES)

    gate_p, weights, t_skin, bind_record = None, {}, None, None
    if bind:
        t_skin, bind_record = apply_binding(mesh_obj, arm_obj, bind, source, radii,
                                            envelope_radii=envelope_radii)
        # Liveness BEFORE Gate P, so Gate P's reading is known to be about a bound mesh and
        # not about an evaluation that never carried the modifier. Restored immediately; no
        # keyframe exists yet, so nothing survives the restore.
        bpy.context.view_layer.update()
        rest_before = evaluated_world_verts(mesh_obj)
        pb = arm_obj.pose.bones["shoulder.L"]
        saved = pb.matrix_basis.copy()
        pb.matrix_basis = Matrix.Rotation(math.radians(30.0), 4, "Y")
        bpy.context.view_layer.update()
        probed = evaluated_world_verts(mesh_obj)
        pb.matrix_basis = saved
        bpy.context.view_layer.update()

        liveness = rig_gates.gate_p_evaluation_is_live(rest_before, probed, diagonal)
        bound = evaluated_world_verts(mesh_obj)
        gate_p = rig_gates.gate_p_rest_pose(source, bound, diagonal)
        gate_p["evaluation_liveness"] = liveness
        weights = read_weights(mesh_obj, len(source))

    fingerprint = rig_gates.rig_fingerprint(bone_table(arm_obj), weights, len(source))

    return {
        "label": label, "scene": scene, "mesh": mesh_obj, "armature": arm_obj,
        "source": source, "diagonal": diagonal, "landmarks": lm, "weights": weights,
        "fingerprint": fingerprint, "gate_p": gate_p, "premise2": premise2,
        "premise6": premise6, "shell_id": shell_id, "shell_sizes": shell_sizes,
        "bone_lengths": bone_lengths, "bbox_lo": lo.tolist(), "bbox_hi": hi.tolist(),
        "heuristic_landmarks": heuristic_marks, "joint_balls": balls, "shells": shells,
        "offset_table": offsets, "placement_ruling": ruling, "bound": bind or False,
        "bone_radii": radii, "binding_record": bind_record,
        "timings": {"landmarks_s": t_landmarks, "joint_balls_s": t_balls,
                    "bind_s": t_skin},
    }


# ----------------------------------------------------------------------- the probe


def author_probe(ctx):
    """E03's arc on a bone: rotate the +X-side arm about +Y, 0 -> 90 deg, 33 keys @ 16 fps.

    The rotation is E03's, applied to a pose bone instead of a joined cylinder group, so
    E08 compares character-control against wire-control on the same authored transform.
    What differs is the rest pose it acts on: E03's wire figure was T-posed, so the arc
    read as horizontal -> overhead; this character stands with his arms down, so the same
    rotation reads as arm-at-side -> arm-horizontal. Reported, not silently rescaled.

    `matrix_basis` is computed in closed form rather than assigned through `pose_bone.matrix`,
    which would need a depsgraph settle per frame — 33 evaluations of a 400k-vertex armature
    deform, and a value that depends on when the settle happened is not a recipe.
    """
    arm_obj, scene = ctx["armature"], ctx["scene"]
    arc = posearc.resolve_arc(PROBE_ARC)
    readout = posearc.arc_readout(arc, PROBE_FRAMES, PROBE_START_DEG, PROBE_END_DEG)

    left_sign = ctx["landmarks"]["facing"]["left_x_sign"]
    side = "L" if left_sign * sitelist.PROBE_ARC_SIDE_X_SIGN > 0 else "R"
    bone_name = f"shoulder.{side}"

    bpy.context.view_layer.objects.active = arm_obj
    pb = arm_obj.pose.bones[bone_name]
    pb.rotation_mode = "QUATERNION"
    rest = arm_obj.data.bones[bone_name].matrix_local.copy()
    pivot = rest.to_translation()
    to_pivot = Matrix.Translation(pivot)
    from_pivot = Matrix.Translation(-pivot)
    rest_inv = rest.inverted()

    keyed = []
    for i in range(PROBE_FRAMES):
        theta = posearc.angle_at_frame(i, PROBE_FRAMES, PROBE_START_DEG, PROBE_END_DEG)
        applied = arc["sign"] * theta
        rot = Matrix.Rotation(math.radians(applied), 4, arc["axis"])
        target = to_pivot @ rot @ from_pivot @ rest
        pb.matrix_basis = rest_inv @ target
        pb.keyframe_insert(data_path="rotation_quaternion", frame=1 + i)
        pb.keyframe_insert(data_path="location", frame=1 + i)
        keyed.append({"frame": 1 + i, "index": i, "angle_deg": round(theta, 9),
                      "applied_deg": round(applied, 9)})

    action = arm_obj.animation_data.action if arm_obj.animation_data else None
    n_fcurves = 0
    for fc in _action_fcurves(action) if action else []:
        n_fcurves += 1
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

    scene.frame_set(1)
    bpy.context.view_layer.update()
    return {
        "arc": PROBE_ARC, "bone": bone_name,
        "which_arm_is_on_plus_x": ("the character's LEFT" if left_sign > 0
                                   else "the character's RIGHT"),
        "axis": arc["axis"], "sign": arc["sign"],
        "start_deg": PROBE_START_DEG, "end_deg": PROBE_END_DEG,
        "frames": PROBE_FRAMES, "fps": PROBE_FPS,
        "scene_fps_at_authoring": scene.render.fps,
        "action": action.name if action else None,
        "n_fcurves": n_fcurves, "readout": readout, "keys": keyed,
        "note": ("The authored transform is E03's exactly. The rest pose it acts on is not: "
                 "E03's wire subject was T-posed so the arc read horizontal -> overhead; "
                 "this character stands with his arms down so the same rotation reads "
                 "arm-at-side -> arm-horizontal."),
    }


def _action_fcurves(action):
    """Both Action APIs. Blender 5.2's slotted actions replaced the flat `fcurves` list
    with layers -> strips -> channelbags; the attribute's absence is the discriminator,
    measured on this rig 2026-08-10 in `make_test_armature.py` and reused rather than
    re-derived."""
    flat = getattr(action, "fcurves", None)
    if flat is not None:
        return list(flat)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cbag in getattr(strip, "channelbags", []):
                out.extend(cbag.fcurves)
    return out


# ------------------------------------------------------------------- diagnostics


def deformation_diagnostics(ctx, probe):
    """Per-structure displacement under the probe arc. DIAGNOSTIC — gates nothing.

    Reported per bone rather than as one number for the figure, because a global statistic
    over a character is exactly the quantity that hides a shredded shoulder inside an
    otherwise still body: 400k vertices barely move, so any mesh-wide mean is dominated by
    the parts that were never asked to.
    """
    scene, mesh_obj = ctx["scene"], ctx["mesh"]
    weights = ctx["weights"]
    n = len(ctx["source"])
    diagonal = ctx["diagonal"]

    scene.frame_set(1)
    bpy.context.view_layer.update()
    rest = evaluated_world_verts(mesh_obj)
    scene.frame_set(PROBE_FRAMES)
    bpy.context.view_layer.update()
    end = evaluated_world_verts(mesh_obj)
    d = np.linalg.norm(end - rest, axis=1)

    stack = np.zeros((len(weights), n), dtype=np.float64)
    names = sorted(weights)
    for i, name in enumerate(names):
        stack[i] = weights[name]
    total = stack.sum(axis=0)
    dominant = np.argmax(stack, axis=0)
    dominant[total <= 0] = -1

    per_bone = {}
    for i, name in enumerate(names):
        sel = dominant == i
        cnt = int(sel.sum())
        rec = {"vertices_dominated": cnt,
               "vertices_with_any_weight": int((stack[i] > 0).sum()),
               "mean_weight_where_present": float(stack[i][stack[i] > 0].mean())
               if (stack[i] > 0).any() else 0.0}
        if cnt:
            dd = d[sel]
            rec.update({
                "displacement_max": float(dd.max()),
                "displacement_mean": float(dd.mean()),
                "displacement_p95": float(np.percentile(dd, 95)),
                "displacement_max_frac_of_diagonal": float(dd.max() / diagonal),
            })
        per_bone[name] = rec

    unweighted = int((total <= 1e-9).sum())
    short = int((total < 0.999).sum())
    over = int((total > 1.001).sum())

    shell_id, shell_sizes = ctx["shell_id"], ctx["shell_sizes"]
    n_shells = len(shell_sizes)
    split = 0
    for s in range(n_shells):
        sel = shell_id == s
        if sel.sum() < 2:
            continue
        if len(np.unique(dominant[sel])) > 1:
            split += 1

    return {
        "unit": "world units (the subject stands 1.0 tall)",
        "bbox_diagonal": diagonal,
        "frames_compared": [1, PROBE_FRAMES],
        "probe_bone": probe["bone"],
        "per_bone": per_bone,
        "weight_sums": {
            "vertices_total": n,
            "vertices_with_no_weight_at_all": unweighted,
            "vertices_with_weight_sum_below_0.999": short,
            "vertices_with_weight_sum_above_1.001": over,
            "min_weight_sum": float(total.min()),
            "mean_weight_sum": float(total.mean()),
            "note": ("A partially failed bone-heat solve shows up here and nowhere else. "
                     "Rest-pose identity is Gate P's business; these are the sums that "
                     "would break it."),
        },
        "shells": {
            "n_shells": n_shells,
            "shells_spanning_more_than_one_dominant_bone": split,
            "note": ("A shell weighted to a different bone than the skin around it is what "
                     "pushes an interior shard through the surface when the pose changes. "
                     "Counted, not judged."),
        },
        "whole_mesh": {
            "displacement_max": float(d.max()),
            "displacement_mean": float(d.mean()),
            "vertices_moving_more_than_1pct_of_diagonal":
                int((d > 0.01 * diagonal).sum()),
            "note": ("Present for completeness and deliberately not headline: a mesh-wide "
                     "mean over a figure where only one arm was asked to move is dominated "
                     "by the parts that were not."),
        },
    }


# ----------------------------------------------------------------------- export


def export_rigged(ctx, probe, out_path, animated=True):
    """Export, then Gate N on the RE-IMPORTED result. Raises before any manifest exists.

    The re-import also re-reads the mesh, so Gate P's fidelity clause runs on the round trip
    itself: whatever else the exporter did, the vertices a consumer loads must be the
    vertices that went in. In skeleton mode that is the *whole* of the rest-pose path,
    because nothing is bound — see `build_pass`.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wanted = {
        "filepath": out_path, "export_format": "GLB", "use_selection": False,
        "export_yup": True, "export_animations": animated,
        "export_frame_range": animated,
        "export_animation_mode": "ACTIONS", "export_skins": True,
        # export_def_bones=True would drop every non-deforming marker and fire Gate N.
        "export_def_bones": False, "export_apply": False, "export_materials": "EXPORT",
    }
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    kwargs = {k: v for k, v in wanted.items() if k in props}
    dropped = sorted(set(wanted) - set(kwargs))
    bpy.ops.export_scene.gltf(**kwargs)

    # Re-import into a throwaway scene and read the names a consumer would actually get.
    fresh_scene(PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=out_path)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    reimported = sorted(b.name for a in arms for b in a.data.bones)
    gate_n_post = rig_gates.gate_n_names(reimported, sitelist.ALL_NAMES,
                                         "the re-imported exported GLB")

    # MEASURED 2026-08-11, and it was a gate silently not running. Selecting the re-imported
    # subject by `type == "MESH"` returns TWO objects: `geometry_0` and an `Icosphere` — the
    # decoy Blender's glTF importer drops into its hidden `glTF_not_exported` collection,
    # the same decoy E01's G4 fired on. The first version of this code skipped Gate P when
    # the count was not 1, so the round-trip clause reported `null` and the manifest carried
    # a gate that had quietly declined to run. Selection is now render-visibility, and an
    # ambiguous subject **raises** rather than returning None: a gate that opts out is worse
    # than one that fails, because nothing downstream can tell the difference.
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(bpy.context.scene, meshes)
    if len(visible) != 1:
        raise ArmatureError(
            f"the re-imported export presents {len(visible)} render-visible mesh object(s) "
            f"({[o.name for o in visible]}, from {[o.name for o in meshes]}); Gate P's "
            f"round-trip clause cannot say which one is the subject, and guessing would "
            f"make it report on geometry nobody asked about"
        )
    gate_p_round_trip = rig_gates.gate_p_round_trip_positions(
        ctx["source"], world_verts(visible[0]), ctx["diagonal"])
    actions = [a.name for a in bpy.data.actions]
    return {
        "export_kwargs": {k: v for k, v in kwargs.items() if k != "filepath"},
        "requested_but_not_supported_by_this_blender": dropped,
        "reimported_armatures": [a.name for a in arms],
        "reimported_bone_names": reimported,
        "reimported_mesh_objects": [o.name for o in meshes],
        "reimported_actions": actions,
        "gate_n_post": gate_n_post,
        "gate_p_round_trip": gate_p_round_trip,
    }


def run_skeleton(args, out_dir, source_sha, started):
    """Skeleton-approval mode. Places the pivots, gates the names, exports, and stops.

    **Nothing is bound.** The Director gated the experiment here — *"Nothing moves forward
    until I approve the skeleton"* — so the binding arms do not run and Gate P's liveness
    clause is NOT YET RUN by design, not by omission.
    """
    first = build_pass(args["glb"], args["name"], args["bands"], "determinism-probe",
                       bind=False)
    fp_first, offsets_first = first["fingerprint"], first["offset_table"]
    del first

    ctx = build_pass(args["glb"], args["name"], args["bands"], "kept", bind=False)
    gate_d = rig_gates.gate_d_determinism(fp_first, ctx["fingerprint"], ctx["diagonal"])
    gate_n_pre = rig_gates.gate_n_names(
        [b.name for b in ctx["armature"].data.bones], sitelist.ALL_NAMES,
        "the built armature, before export")

    out_glb = os.path.join(out_dir, f"{args['name']}_skeleton.glb")
    export = export_rigged(ctx, None, out_glb, animated=False)

    manifest = {
        "tool": "rig_character", "tool_version": TOOL_VERSION, "mode": "skeleton",
        "tool_sha256": _tool_hashes(),
        "blender": bpy.app.version_string,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "elapsed_s": round(time.time() - started, 2),
        "source": {"path": args["glb"], "sha256": source_sha,
                   "bytes": os.path.getsize(args["glb"])},
        "output": {"path": out_glb, "sha256": sha256_file(out_glb),
                   "bytes": os.path.getsize(out_glb)},
        "site_to_bone_map": {b.name: b.as_dict() for b in sitelist.BONES},
        "registered_site_count": len(sitelist.ALL_NAMES),
        "premise_2_pre_existing_rig": ctx["premise2"],
        "premise_6_skinnability": ctx["premise6"],
        "bbox": {"lo": ctx["bbox_lo"], "hi": ctx["bbox_hi"], "diagonal": ctx["diagonal"]},
        "facing": ctx["landmarks"]["facing"],
        "regions": ctx["landmarks"]["regions"],
        "landmarks_after_snap": ctx["landmarks"]["landmarks"],
        "landmarks_before_snap": ctx["heuristic_landmarks"],
        "landmark_provenance": ctx["landmarks"]["provenance"],
        "joint_ball_offset_table": ctx["offset_table"],
        "placement_ruling": ctx["placement_ruling"],
        "joint_balls_detected": ctx["joint_balls"],
        "offset_table_reproduced_by_second_build":
            offsets_first == ctx["offset_table"],
        "bone_lengths": ctx["bone_lengths"],
        "gates": {
            "N_pre_export": gate_n_pre,
            "N_post_export": export["gate_n_post"],
            "P_rest_pose_round_trip": export["gate_p_round_trip"],
            "P_evaluation_liveness": {
                "verdict": "NOT YET RUN",
                "reason": ("nothing is bound in skeleton mode, so there is no deform for a "
                           "liveness clause to be about. It runs when a binding arm runs."),
            },
            "D_determinism": gate_d,
        },
        "export": {k: v for k, v in export.items()
                   if k not in ("gate_n_post", "gate_p_round_trip")},
        "probe_action": {"verdict": "NOT AUTHORED",
                         "reason": "an arc on an unbound skeleton moves no geometry"},
        "deformation_diagnostics": {
            "verdict": "NOT YET RUN",
            "reason": "no binding exists; deformation statistics require weights",
        },
        "timings": ctx["timings"],
        "note": ("Skeleton-approval mode. The Director approves the skeleton before any "
                 "binding arm runs; no metric here approximates that judgement."),
    }
    path = os.path.join(out_dir, "skeleton_manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("SKELETON_OK " + json.dumps(
        {"glb": out_glb, "sha256": manifest["output"]["sha256"], "manifest": path}))


def _tool_hashes():
    here = os.path.dirname(os.path.abspath(__file__))
    return {os.path.basename(p): sha256_file(p) for p in [
        os.path.abspath(__file__),
        os.path.join(here, "armature_core", "sitelist.py"),
        os.path.join(here, "armature_core", "landmarks.py"),
        os.path.join(here, "armature_core", "joints.py"),
        os.path.join(here, "armature_core", "rig_gates.py"),
    ]}


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    os.makedirs(out_dir, exist_ok=True)
    sitelist.validate()

    started = time.time()
    source_sha = sha256_file(args["glb"])

    if args["measure_only"]:
        ctx = build_pass(args["glb"], args["name"], args["bands"], "measure")
        rec = {
            "tool": "rig_character", "tool_version": TOOL_VERSION, "mode": "measure-only",
            "blender": bpy.app.version_string, "source": args["glb"],
            "source_sha256": source_sha,
            "premise_2_pre_existing_rig": ctx["premise2"],
            "premise_6_skinnability": ctx["premise6"],
            "landmarks": ctx["landmarks"]["landmarks"],
            "landmark_provenance": ctx["landmarks"]["provenance"],
            "facing": ctx["landmarks"]["facing"],
            "regions": ctx["landmarks"]["regions"],
            "bone_lengths": ctx["bone_lengths"],
            "gate_p": ctx["gate_p"],
            "timings": ctx["timings"],
        }
        path = os.path.join(out_dir, "measure.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2)
        print("MEASURE_OK " + path)
        return

    if args["mode"] == "skeleton":
        run_skeleton(args, out_dir, source_sha, started)
        return
    if args["mode"] != "full":
        raise ArmatureError(f"unknown --mode={args['mode']!r}; known: skeleton, full")

    # Two full builds from the same input. The second is the one kept; Gate D compares.
    mode = args["binding"]
    first = build_pass(args["glb"], args["name"], args["bands"], "determinism-probe",
                       bind=mode, envelope_radii=args["envelope_radii"])
    fp_first = first["fingerprint"]
    gate_p_first = first["gate_p"]
    del first

    ctx = build_pass(args["glb"], args["name"], args["bands"], "kept", bind=mode,
                     envelope_radii=args["envelope_radii"])
    gate_d = rig_gates.gate_d_determinism(fp_first, ctx["fingerprint"], ctx["diagonal"])

    gate_n_pre = rig_gates.gate_n_names(
        [b.name for b in ctx["armature"].data.bones], sitelist.ALL_NAMES,
        "the built armature, before export")

    probe = author_probe(ctx)
    diagnostics = deformation_diagnostics(ctx, probe)

    tag = mode if mode != "envelope" else f"envelope_{args['envelope_radii']}"
    out_glb = os.path.join(out_dir, f"{args['name']}_{tag}.glb")
    export = export_rigged(ctx, probe, out_glb)
    out_sha = sha256_file(out_glb)

    manifest = {
        "tool": "rig_character",
        "tool_version": TOOL_VERSION,
        "mode": "full",
        "binding": mode,
        "binding_record": ctx["binding_record"],
        "bone_radii_measured": ctx["bone_radii"],
        "joint_ball_offset_table": ctx["offset_table"],
        "placement_ruling": ctx["placement_ruling"],
        "tool_sha256": _tool_hashes(),
        "blender": bpy.app.version_string,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "elapsed_s": round(time.time() - started, 2),
        "source": {"path": args["glb"], "sha256": source_sha,
                   "bytes": os.path.getsize(args["glb"])},
        "output": {"path": out_glb, "sha256": out_sha, "bytes": os.path.getsize(out_glb)},
        "site_to_bone_map": {b.name: b.as_dict() for b in sitelist.BONES},
        "registered_site_count": len(sitelist.ALL_NAMES),
        "e01_site_count": len(sitelist.E01_SITES),
        "premise_2_pre_existing_rig": ctx["premise2"],
        "premise_6_skinnability": ctx["premise6"],
        "bbox": {"lo": ctx["bbox_lo"], "hi": ctx["bbox_hi"], "diagonal": ctx["diagonal"]},
        "facing": ctx["landmarks"]["facing"],
        "regions": ctx["landmarks"]["regions"],
        "landmarks": ctx["landmarks"]["landmarks"],
        "landmark_provenance": ctx["landmarks"]["provenance"],
        "bone_lengths": ctx["bone_lengths"],
        "probe_action": probe,
        "gates": {
            "N_pre_export": gate_n_pre,
            "N_post_export": export["gate_n_post"],
            "P_rest_pose_kept_build": ctx["gate_p"],
            "P_rest_pose_first_build": gate_p_first,
            "D_determinism": gate_d,
        },
        "export": {k: v for k, v in export.items() if k != "gate_n_post"},
        "deformation_diagnostics": diagnostics,
        "timings": ctx["timings"],
        "note": ("Deformation statistics are DIAGNOSTICS and gate nothing. Whether the "
                 "deform is acceptable, and whether the figure is still the same "
                 "character, are the Director's on the sheet at his zoom. No number here "
                 "approximates either."),
    }
    path = os.path.join(out_dir, f"rig_manifest_{tag}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("RIG_OK " + json.dumps({"binding": tag, "glb": out_glb, "sha256": out_sha,
                                  "manifest": path}))


def _write_halt(out_dir, exc, source_sha, glb):
    """Record a fired andon where the run can be read back, then re-raise.

    A gate that halts and leaves nothing behind makes the executor the only witness. The
    evidence dict each gate carries is the measurement that stopped the run, so it is
    written beside the outputs the run did not produce — and the process still exits
    non-zero, because a halt that returns success is not a halt.
    """
    rec = {
        "tool": "rig_character", "tool_version": TOOL_VERSION,
        "outcome": "HALTED — a gate fired",
        "gate": getattr(exc, "gate", "?"),
        "exception": type(exc).__name__,
        "message": str(exc),
        "evidence": getattr(exc, "evidence", {}),
        "blender": bpy.app.version_string,
        "source": {"path": glb, "sha256": source_sha},
        "outputs_not_produced": ["<name>_rigged.glb", "rig_manifest.json"],
        "note": ("Nothing downstream of the gate ran. No rigged GLB exists, no manifest "
                 "was written, and no export was attempted. Gates after the one that "
                 "fired are NOT YET RUN, not passed."),
    }
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "halt.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, default=str)
    print("HALT " + json.dumps({"gate": rec["gate"], "record": path}))
    return path


if __name__ == "__main__":
    try:
        main()
    except GateFailure as exc:
        import traceback
        traceback.print_exc()
        _args = parse_args()
        _write_halt(os.path.abspath(_args["out"]), exc,
                    sha256_file(_args["glb"]), _args["glb"])
        # MEASURED 2026-08-11: letting the exception propagate out of a `-b -P` script
        # prints the traceback and Blender still exits **0**. A caller reading the exit
        # code — a shell chain, a CI step, a later session's `if ($LASTEXITCODE -eq 0)` —
        # would see the halt as a success. A halt that returns success is not a halt.
        sys.exit(2)
