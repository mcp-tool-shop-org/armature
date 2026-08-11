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

from armature_core import landmarks, posearc, rig_gates, sitelist  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "1.0.0"

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
    args = {"glb": None, "out": None, "measure_only": False, "bands": 200, "name": "performer"}
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


def skin(mesh_obj, arm_obj):
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    t0 = time.time()
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    return time.time() - t0


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


def build_pass(glb_path, name, bands, label):
    """One complete build, from a fresh scene to a skinned mesh. Gate P raises inside it."""
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

    arm_obj, bone_lengths = build_armature(scene, lm["landmarks"], name)
    t_skin = skin(mesh_obj, arm_obj)

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
        "timings": {"landmarks_s": t_landmarks, "skin_s": t_skin},
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


def export_rigged(ctx, probe, out_path):
    """Export, then Gate N on the RE-IMPORTED result. Raises before any manifest exists."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wanted = {
        "filepath": out_path, "export_format": "GLB", "use_selection": False,
        "export_yup": True, "export_animations": True, "export_frame_range": True,
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
    actions = [a.name for a in bpy.data.actions]
    return {
        "export_kwargs": {k: v for k, v in kwargs.items() if k != "filepath"},
        "requested_but_not_supported_by_this_blender": dropped,
        "reimported_armatures": [a.name for a in arms],
        "reimported_bone_names": reimported,
        "reimported_actions": actions,
        "gate_n_post": gate_n_post,
    }


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

    # Two full builds from the same input. The second is the one kept; Gate D compares.
    first = build_pass(args["glb"], args["name"], args["bands"], "determinism-probe")
    fp_first = first["fingerprint"]
    gate_p_first = first["gate_p"]
    del first

    ctx = build_pass(args["glb"], args["name"], args["bands"], "kept")
    gate_d = rig_gates.gate_d_determinism(fp_first, ctx["fingerprint"], ctx["diagonal"])

    gate_n_pre = rig_gates.gate_n_names(
        [b.name for b in ctx["armature"].data.bones], sitelist.ALL_NAMES,
        "the built armature, before export")

    probe = author_probe(ctx)
    diagnostics = deformation_diagnostics(ctx, probe)

    out_glb = os.path.join(out_dir, f"{args['name']}_rigged.glb")
    export = export_rigged(ctx, probe, out_glb)
    out_sha = sha256_file(out_glb)

    manifest = {
        "tool": "rig_character",
        "tool_version": TOOL_VERSION,
        "tool_sha256": {os.path.basename(p): sha256_file(p) for p in [
            os.path.abspath(__file__),
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "armature_core", "sitelist.py"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "armature_core", "landmarks.py"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "armature_core", "rig_gates.py"),
        ]},
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
    path = os.path.join(out_dir, "rig_manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("RIG_OK " + json.dumps({"glb": out_glb, "sha256": out_sha, "manifest": path}))


if __name__ == "__main__":
    main()
