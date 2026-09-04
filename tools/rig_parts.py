"""rig_parts — E07 arm (c): a real stop-motion armature in software.

    blender -b --factory-startup -P tools\\rig_parts.py -- --glb=<in.glb> --out=<dir>

Separate **rigid parts** articulating at the sculpted ball joints, each parented to its bone.
**No armature modifier, no vertex weights, no deformation anywhere.** Commissioned after both
deforming arms failed at the Director's eye — ruled a hard fail — on the ranked
recommendation of Comfy Agent consult #5 (`docs/comfy-consult-5.md`), whose atlas-survives
promise the advisor calibrated on this exact performer before any of this was scripted:
298,366 of 298,366 far-from-cut faces came through a full-mesh bisect with **byte-identical
UVs**, 0 changed and 0 missing.

The consult's two shell-class prescriptions are binding and live in `armature_core/parts.py`:
faces are assigned by **spatial region, never by loose parts** (67 interior shells would
explode a connectivity split into anatomy-free fragments), and every joint carries a **collar
overlap** so adjacent parts interpenetrate and no gap opens under articulation.

Gates, all raising inside this file, before the manifest that would make a run look finished:

* **PARTS** — every face assigned exactly once, the part list is the registered segment list,
  nothing unassigned. The direction nothing else bounds.
* **N-analog** — every part carries its registered bone's name, checked on the built scene
  and again on the **re-imported export**.
* **P** — parenting did not move anything at the bind pose.
* **RIGID** — the authored arc arrives whole: each part lands exactly on its own bone's
  rest-to-pose transform, and every part's internal distances are invariant.
* **D** — a second build produces the same parts, compared as parsed geometry, never bytes.
* **ATLAS** — the embedded texture is byte-identical in the export. For this asset the image
  bytes ARE the contract, because "no re-bake" is the promise the route was chosen for.
"""

import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import rig_character  # noqa: E402
from armature_core import glb, joints, landmarks, parts, rig_gates, sitelist  # noqa: E402
from armature_core.errors import (ArmatureError, GateFailure,          # noqa: E402
                                  GateNNames, GatePRestPose)

TOOL_VERSION = "1.0.0"

#: How far either side of a joint plane the bisect is allowed to look, as a multiple of that
#: joint's own radius. Bisecting the whole mesh on every plane would also cut the other leg.
BISECT_NEIGHBOURHOOD = 3.0
#: Vertices sampled per part for the rigidity check. Deterministic stride, never random.
RIGIDITY_SAMPLE = 400


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {"glb": None, "out": None, "bands": 200, "name": "performer",
            "collar_fraction": parts.COLLAR_BALL_FRACTION, "assignment": "nearest"}
    for token in argv:
        key, _, value = token[2:].partition("=")
        key = key.replace("-", "_")
        if key not in args:
            raise ArmatureError(f"unknown argument {token!r}; known: {sorted(args)}")
        args[key] = (int(value) if key == "bands"
                     else float(value) if key == "collar_fraction" else value)
    if not args["glb"] or not args["out"]:
        raise ArmatureError("usage: -- --glb=<path> --out=<dir> [--bands=N] "
                            "[--collar-fraction=F]")
    return args


# --------------------------------------------------------------------------- geometry


def source_bmesh(mesh_obj):
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm


def bisect_at_joints(bm, planes, diagonal):
    """Realise each joint boundary as a planar cut, restricted to that joint's neighbourhood.

    `bmesh.ops.bisect_plane` rather than the `mesh.bisect` operator: it takes the geometry to
    consider as an argument, so the cut can be confined to faces near this joint. An
    unrestricted bisect would also slice the opposite leg, the far arm and the head wherever
    the same infinite plane happens to pass through them.
    """
    record = []
    for plane in planes:
        co = Vector(plane["point"])
        no = Vector(plane["normal"])
        reach = plane["radius"] * BISECT_NEIGHBOURHOOD
        bm.faces.ensure_lookup_table()
        near = [f for f in bm.faces if (f.calc_center_median() - co).length <= reach]
        if not near:
            record.append({"joint": f"{plane['parent']}->{plane['child']}",
                           "faces_before": 0, "faces_after": 0, "reach": reach,
                           "note": "no geometry within reach of this joint"})
            continue
        geom = set(near)
        for f in near:
            geom.update(f.verts)
            geom.update(f.edges)
        before = len(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=list(geom), dist=1e-6 * diagonal,
                               plane_co=co, plane_no=no,
                               clear_inner=False, clear_outer=False)
        bm.faces.ensure_lookup_table()
        record.append({"joint": f"{plane['parent']}->{plane['child']}",
                       "reach": reach, "faces_before": before,
                       "faces_after": len(bm.faces),
                       "faces_created": len(bm.faces) - before})
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return record


def classify_shells(bm, diagonal):
    """Which faces are the outer surface and which are the wall lining it.

    Connectivity on **welded** positions, without touching the mesh: glTF splits a vertex at
    every UV and normal seam, so the file presents 21,514 shells where the asset has 67.
    Vertices are grouped by rounded position, groups are unioned across edges, and the
    component carrying the most faces is the exterior.
    """
    coords = np.array([list(v.co) for v in bm.verts], dtype=np.float64)
    key = np.round(coords / (1e-6 * diagonal)).astype(np.int64)
    _, rep = np.unique(key, axis=0, return_inverse=True)
    groups = int(rep.max()) + 1
    parent = np.arange(groups, dtype=np.int64)

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for e in bm.edges:
        a, b = find(rep[e.verts[0].index]), find(rep[e.verts[1].index])
        if a != b:
            parent[b] = a
    root = np.array([find(i) for i in range(groups)], dtype=np.int64)
    comp_of_vert = root[rep]
    face_comp = np.array([comp_of_vert[f.verts[0].index] for f in bm.faces], dtype=np.int64)
    uniq, counts = np.unique(face_comp, return_counts=True)
    exterior = int(uniq[int(np.argmax(counts))])
    return face_comp, exterior, int(len(uniq))


def pair_interior_faces(bm, face_comp, exterior, labels, ray_reject_multiple=3.0):
    """An interior face inherits the part of the exterior face it backs.

    **The armpit shard, and the rule that kills it by construction.** Nearest-bone assignment
    is blind to wall-ness: the torso's inner wall near the armpit is simply nearer the
    shoulder bone than the chest bone, so 21,664 interior faces went to `shoulder.L` and swung
    out of the body when the arm rotated. An inner wall has no business belonging to a bone
    the surface it lines does not belong to.

    Each interior face casts along **both** directions of its own normal and takes the nearer
    exterior hit. A ray landing more than `ray_reject_multiple` times further than the nearest
    exterior face is rejected in favour of that nearest face -- a grazing normal can otherwise
    pair a hip to a shoulder. No hit at all falls back to nearest. Every branch is counted:
    which rule fired how often is what makes this auditable rather than magic.
    """
    from mathutils.bvhtree import BVHTree

    ext_idx = np.flatnonzero(face_comp == exterior)
    int_idx = np.flatnonzero(face_comp != exterior)
    if not len(ext_idx) or not len(int_idx):
        return np.asarray(labels).copy(), {"interior_faces": int(len(int_idx)),
                                           "note": "nothing to pair"}

    bm.faces.ensure_lookup_table()
    bm.normal_update()
    verts = [v.co.copy() for v in bm.verts]
    polys = [[v.index for v in bm.faces[int(i)].verts] for i in ext_idx]
    # all_triangles=False: the joint bisects leave n-gons at every cut, and asserting
    # triangles raises on the first one. FromPolygons triangulates internally and still
    # reports the POLYGON index, which is what the pairing needs.
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False)

    out = np.asarray(labels).copy()
    stats = {"by_ray": 0, "by_nearest_no_hit": 0, "by_nearest_ray_rejected": 0,
             "unpaired": 0}
    distances = []
    for fi in int_idx:
        f = bm.faces[int(fi)]
        origin = f.calc_center_median()
        n = f.normal
        best = None
        for direction in (n, -n):
            loc, nrm, idx, dist = bvh.ray_cast(origin, direction)
            if idx is not None and (best is None or dist < best[0]):
                best = (dist, idx)
        near_loc, near_nrm, near_idx, near_dist = bvh.find_nearest(origin)

        if best is not None and near_idx is not None and                 best[0] > ray_reject_multiple * max(near_dist, 1e-12):
            chosen = near_idx
            stats["by_nearest_ray_rejected"] += 1
            distances.append(float(near_dist))
        elif best is not None:
            chosen = best[1]
            stats["by_ray"] += 1
            distances.append(float(best[0]))
        elif near_idx is not None:
            chosen = near_idx
            stats["by_nearest_no_hit"] += 1
            distances.append(float(near_dist))
        else:
            stats["unpaired"] += 1
            continue
        out[fi] = out[int(ext_idx[int(chosen)])]

    d = np.array(distances) if distances else np.zeros(1)
    stats.update({
        "interior_faces": int(len(int_idx)), "exterior_faces": int(len(ext_idx)),
        "interior_fraction": float(len(int_idx)) / (len(int_idx) + len(ext_idx)),
        "ray_reject_multiple": ray_reject_multiple,
        "pairing_distance_mean": float(d.mean()), "pairing_distance_max": float(d.max()),
        "rule": ("normal ray both directions, nearer hit wins; nearest exterior face where "
                 "the ray misses or lands >3x further than the nearest face"),
    })
    return out, stats


def face_centroids(bm):
    bm.faces.ensure_lookup_table()
    return np.array([list(f.calc_center_median()) for f in bm.faces], dtype=np.float64)


def extract_part(bm_src, face_indices, name, material, uv_name):
    """A new mesh holding exactly these faces, with their UVs copied value for value."""
    bm = bmesh.new()
    uv_src = bm_src.loops.layers.uv.active
    uv_dst = bm.loops.layers.uv.new(uv_name) if uv_src else None
    vmap = {}
    made = 0
    for fi in face_indices:
        f = bm_src.faces[int(fi)]
        verts = []
        for v in f.verts:
            got = vmap.get(v.index)
            if got is None:
                got = bm.verts.new(v.co)
                vmap[v.index] = got
            verts.append(got)
        try:
            nf = bm.faces.new(verts)
        except ValueError:
            continue          # this face already exists in this part
        made += 1
        if uv_dst is not None:
            for l_new, l_src in zip(nf.loops, f.loops):
                l_new[uv_dst].uv = l_src[uv_src].uv
    bm.verts.ensure_lookup_table()
    me = bpy.data.meshes.new(f"{name}_mesh")
    bm.to_mesh(me)
    bm.free()
    if material is not None:
        me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, made


def parent_to_bone(part, arm_obj, bone_name):
    """Bone parenting, with the parent inverse that keeps the part where it already is.

    Blender's bone parent space has its origin at the bone **tail** with +Y along the bone,
    so the inverse composes `matrix_local` with a translation of the bone's own length. Get
    this wrong and every part jumps to the tail of its bone — which Gate P catches, and
    which nothing else would.
    """
    bone = arm_obj.data.bones[bone_name]
    part.parent = arm_obj
    part.parent_type = "BONE"
    part.parent_bone = bone_name
    part.matrix_parent_inverse = (
        arm_obj.matrix_world @ bone.matrix_local
        @ Matrix.Translation((0.0, bone.length, 0.0))
    ).inverted()


def part_world_verts(ob):
    me = ob.data
    n = len(me.vertices)
    flat = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", flat)
    m = np.array(ob.matrix_world, dtype=np.float64)
    return flat.reshape(n, 3) @ m[:3, :3].T + m[:3, 3]


def fingerprint(part_objs):
    out = {}
    for name, ob in part_objs.items():
        v = part_world_verts(ob)
        order = np.lexsort((v[:, 2], v[:, 1], v[:, 0]))
        out[name] = {"n_verts": int(len(v)), "n_faces": int(len(ob.data.polygons)),
                     "positions": v[order]}
    return out


# ------------------------------------------------------------------------- the build


def build_pass(args, label):
    scene = rig_character.fresh_scene(rig_character.PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=args["glb"])

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if len(meshes) != 1:
        raise ArmatureError(f"expected one mesh object, found {[o.name for o in meshes]}")
    mesh_obj = meshes[0]
    material = mesh_obj.data.materials[0] if mesh_obj.data.materials else None
    uv_name = (mesh_obj.data.uv_layers.active.name if mesh_obj.data.uv_layers.active
               else "UVMap")

    source = rig_character.world_verts(mesh_obj)
    # F-940b0800, family carry: the second site in this domain that derives the tolerance
    # scale for a whole build from a raw imported mesh, and it divides by it eleven lines
    # down (`measure_joint_balls`). One implementation, in the file that owns the andon —
    # never a second finiteness clause here.
    diagonal, lo, hi = rig_character.subject_scale(source, "parts")

    lm = landmarks.derive(source, n_bands=args["bands"])
    balls, _ = rig_character.measure_joint_balls(mesh_obj, diagonal)
    snapped, offsets = joints.snap_sites_to_balls(lm, balls)
    lm["landmarks"] = snapped
    arm_obj, bone_lengths = rig_character.build_armature(scene, snapped, args["name"])
    limb_radii = landmarks.bone_radii(lm, sitelist.BONES)

    deform = [{"name": b.name, "head": tuple(b.head_local), "tail": tuple(b.tail_local),
               "parent": b.parent.name if b.parent else None}
              for b in arm_obj.data.bones if b.use_deform]
    names = [b["name"] for b in deform]
    ball_radii = {site.replace("_", "."): rec["ball_radius"]
                  for site, rec in offsets.items() if rec.get("matched")}

    planes = parts.joint_planes(deform, snapped, ball_radii, limb_radii,
                                collar_fraction=args["collar_fraction"])

    bm = source_bmesh(mesh_obj)
    faces_before_cut = len(bm.faces)
    cuts = bisect_at_joints(bm, planes, diagonal)
    centroids = face_centroids(bm)
    labels = parts.assign_faces(centroids, deform, limb_radii,
                                normalise=args["assignment"] == "normalised")
    # Round 2 of arm (c). Order matters: clamp the exterior to its own joint planes FIRST,
    # then let every interior face inherit the already-clamped part of the surface it lines.
    labels, clamp_detail = parts.clamp_to_joint_planes(centroids, labels, names, planes)
    face_comp, exterior_shell, n_shells = classify_shells(bm, diagonal)
    labels, pairing = pair_interior_faces(bm, face_comp, exterior_shell, labels)
    accounting = parts.gate_parts_accounting(labels, len(bm.faces), names)
    borrowed, collar_detail = parts.collar_faces(centroids, labels, names, planes)

    mesh_obj.hide_render = True
    mesh_obj.hide_viewport = True
    part_objs, part_stats = {}, {}
    for i, name in enumerate(names):
        primary = np.flatnonzero(labels == i)
        face_ids = np.unique(np.concatenate([primary, borrowed[name]])).astype(np.int64)
        ob, made = extract_part(bm, face_ids, f"{args['name']}_{name}", material, uv_name)
        parent_to_bone(ob, arm_obj, name)
        part_objs[name] = ob
        part_stats[name] = {"faces_primary": int(len(primary)),
                            "faces_from_collar": int(len(borrowed[name])),
                            "faces_built": int(made),
                            "vertices": int(len(ob.data.vertices))}
    bm.free()
    bpy.data.objects.remove(mesh_obj, do_unlink=True)

    return {"label": label, "scene": scene, "armature": arm_obj, "parts": part_objs,
            "source": source, "diagonal": diagonal, "landmarks": lm, "offsets": offsets,
            "planes": planes, "collar_detail": collar_detail, "accounting": accounting,
            "part_stats": part_stats, "bone_lengths": bone_lengths, "cuts": cuts,
            "clamp_detail": clamp_detail, "pairing": pairing,
            "shells_welded": n_shells,
            "deform": deform, "names": names, "limb_radii": limb_radii,
            "faces_before_cut": faces_before_cut, "faces_after_cut": len(centroids),
            "bbox_lo": lo.tolist(), "bbox_hi": hi.tolist()}


def gate_p_bind_pose(part_objs, at_bind, diagonal):
    """Gate P - ANDON: bone parenting left every part where it was built.

    MEASURED 2026-09-04: this clause raised `GateNNames`, whose `gate` attribute is "N",
    for a failure that is Gate P. The message says bone parenting moved the parts at the
    bind pose, the evidence dict is `gate_p`, the threshold is
    `rig_gates.REST_POSE_EPSILON_FRAC`, and the manifest records the result under
    `gates.P_bind_pose`. The consequence is not cosmetic: the `__main__` handler reads
    `getattr(exc, "gate", None)` and writes it into `halt.json` and the printed HALT line,
    so the only machine-readable record of a wrong bone-parent inverse said "N" -- sending
    the next session to `sitelist` and the registered-name list instead of to the
    parent-inverse arithmetic at rig_parts.py:284-297, which is where the defect is.

    `at_bind` maps part name -> world positions at frame 1; the comparison is against each
    part's own LOCAL coordinates, which are what it was built with. Bounded as a fraction
    of the subject's own bbox diagonal, not in metres.

    Wave 12, F-524f0a25: `worst = max(worst, d)` returns `worst` when `d` is NaN — the
    same sentinel-plus-comparison shape that let `lift_solve.gate_arrived` publish "max
    0.000e+00" over a performance made entirely of NaN. A part whose bind-pose positions
    are not numbers (a degenerate parent inverse, a division by a zero-length segment)
    therefore passed Gate P with a verdict saying bone parenting left every part where it
    was built. Each per-part displacement goes through `armature_core.parts.require_finite`
    — the one implementation of wave 10's rule 4 — which raises THIS gate's andon with the
    offending part named in THIS gate's evidence.
    """
    ev = {"gate": "P", "andon": "GatePRestPose", "per_part": {}, "verdict": None}
    parts.require_finite("bbox_diagonal", diagonal, GatePRestPose, ev)
    worst = 0.0
    for name, ob in part_objs.items():
        local = np.array([list(v.co) for v in ob.data.vertices], dtype=np.float64)
        d = parts.require_finite(
            f"displacement[{name}]",
            float(np.linalg.norm(at_bind[name] - local, axis=1).max()),
            GatePRestPose, ev, positive=False)
        ev["per_part"][name] = d
        worst = max(worst, d)
    threshold = rig_gates.REST_POSE_EPSILON_FRAC * diagonal
    ev.update({"max_displacement": worst, "threshold": threshold,
               "threshold_frac_of_diagonal": rig_gates.REST_POSE_EPSILON_FRAC,
               "bbox_diagonal": float(diagonal)})
    if worst > threshold:
        raise GatePRestPose(
            f"bone parenting moved the parts at the bind pose: max {worst:.9f} > "
            f"{threshold:.9f}. The parent inverse is wrong and every part has jumped",
            ev)
    ev["verdict"] = "bone parenting left every part where it was built"
    return ev


def gate_part_names(part_objs, where):
    """N-analog: every registered deforming segment is a part, and nothing else is."""
    registered = [b.name for b in sitelist.BONES if b.deform]
    observed = sorted(part_objs)
    return rig_gates.gate_n_names(observed, registered, where)


def observe_under_pose(ctx):
    """Per part: how far it moved, how far from its bone's own transform, and how rigid."""
    scene, arm_obj = ctx["scene"], ctx["armature"]
    scene.frame_set(1)
    bpy.context.view_layer.update()
    rest = {n: part_world_verts(ob) for n, ob in ctx["parts"].items()}
    rest_bone = {n: arm_obj.data.bones[n].matrix_local.copy() for n in ctx["parts"]}

    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()

    out = []
    for name, ob in ctx["parts"].items():
        posed = part_world_verts(ob)
        transform = np.array(arm_obj.pose.bones[name].matrix @ rest_bone[name].inverted(),
                             dtype=np.float64)
        expected = rest[name] @ transform[:3, :3].T + transform[:3, 3]
        step = max(1, len(rest[name]) // RIGIDITY_SAMPLE)
        sample = slice(None, None, step)
        a, b = rest[name][sample], posed[sample]
        da = np.linalg.norm(a[:, None, :] - a[None, :, :], axis=2)
        db = np.linalg.norm(b[:, None, :] - b[None, :, :], axis=2)
        out.append({
            "name": name,
            "vertices": int(len(posed)),
            "max_displacement": float(np.linalg.norm(posed - rest[name], axis=1).max()),
            "max_transform_error": float(np.linalg.norm(posed - expected, axis=1).max()),
            "max_pair_distance_change": float(np.abs(da - db).max()),
            "rigidity_sample": int(len(a)),
        })
    scene.frame_set(1)
    bpy.context.view_layer.update()
    return out


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    # F-61671cb3: through `rig_character`'s wrapper, so a refusal from the registration
    # validator answers the halt contract's 2 ("REFUSED") instead of 1 ("FAILED - an
    # unhandled error"). One implementation, imported, not a second copy of the wrapper.
    rig_character.validate_sitelist()
    started = time.time()
    source_sha = sha256_file(args["glb"])

    first = build_pass(args, "determinism-probe")
    fp_first = fingerprint(first["parts"])
    del first

    ctx = build_pass(args, "kept")
    gate_d = parts.gate_parts_determinism(fp_first, fingerprint(ctx["parts"]),
                                          ctx["diagonal"])
    gate_names_pre = gate_part_names(ctx["parts"], "the built parts, before export")

    # Gate P: parenting moved nothing. Captured against the parts as built, so a wrong
    # bone-parent inverse — which puts every part at its bone's tail — cannot slip through.
    ctx["scene"].frame_set(1)
    bpy.context.view_layer.update()
    at_bind = {n: part_world_verts(ob) for n, ob in ctx["parts"].items()}
    gate_p = gate_p_bind_pose(ctx["parts"], at_bind, ctx["diagonal"])

    probe = rig_character.author_probe(ctx)
    observations = observe_under_pose(ctx)
    gate_rigid = parts.gate_rigid_arrival(observations, ctx["diagonal"])

    out_glb = os.path.join(out_dir, f"{args['name']}_parts.glb")
    wanted = {"filepath": out_glb, "export_format": "GLB", "use_selection": False,
              "export_yup": True, "export_animations": True, "export_frame_range": True,
              "export_animation_mode": "ACTIONS", "export_def_bones": False,
              "export_apply": False, "export_materials": "EXPORT"}
    # THE DIRECTORY IS CREATED HERE, immediately above the first byte (F-d47095fa).
    # It used to sit at line 480 of `main()`, with 4 named refusal(s) stranded between
    # the two (490, 492, 499, 503) -- none of which needs the directory. A run refused by any of
    # them left an empty output directory behind, which a reader scanning `outputs/` or
    # a re-run into the same `--out` reads as an attempt that produced nothing rather
    # than one that was refused. Pinned by `tests/test_instruments_amend_w10.py::
    # test_no_refusal_sits_between_the_output_directory_and_the_first_byte`.
    os.makedirs(out_dir, exist_ok=True)
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    kwargs = {k: v for k, v in wanted.items() if k in props}
    bpy.ops.export_scene.gltf(**kwargs)
    # F-9b2d4106, family carry: refused before Gate ATLAS reads the file back.
    gate_glb = rig_character.gate_glb_written(out_glb, what="the parts GLB")

    gate_atlas = glb.gate_atlas_untouched(args["glb"], out_glb)

    rig_character.fresh_scene(rig_character.PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=out_glb)
    reimported = {o.name.rsplit("_", 1)[-1]: o for o in bpy.data.objects
                  if o.type == "MESH" and o.name.startswith(args["name"])}
    gate_names_post = gate_part_names(reimported, "the re-imported exported GLB")

    manifest = {
        "tool": "rig_parts", "tool_version": TOOL_VERSION, "arm": "c — rigid parts",
        "commissioned_by": "Comfy Agent consult #5 (docs/comfy-consult-5.md), ranked first",
        "calibration_cited": ("full-mesh bisect on this performer: 298,366 of 298,366 "
                              "far-from-cut faces byte-identical UVs, 0 changed, 0 missing; "
                              "1,590 cut-band faces split to 1,980 with interpolated UVs"),
        "blender": bpy.app.version_string,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "elapsed_s": round(time.time() - started, 2),
        "source": {"path": args["glb"], "sha256": source_sha,
                   "bytes": os.path.getsize(args["glb"])},
        "output": {"path": out_glb, "sha256": sha256_file(out_glb),
                   "bytes": os.path.getsize(out_glb)},
        "no_deformation": ("no armature modifier and no vertex group exists on any part; "
                           "each part is bone-parented and moves rigidly"),
        "faces": {"before_cuts": ctx["faces_before_cut"],
                  "after_cuts": ctx["faces_after_cut"],
                  "created_by_cuts": ctx["faces_after_cut"] - ctx["faces_before_cut"]},
        "cuts": ctx["cuts"],
        "collar_fraction_of_ball_radius": args["collar_fraction"],
        "face_assignment": {
            "rule": args["assignment"],
            "note": ("`nearest` is the consult's prescription: plain nearest bone segment to "
                     "the face centroid. `normalised` divides by each bone's own radius and "
                     "is measured to leave the neck with zero faces on this performer."),
        },
        "collar_per_joint": ctx["collar_detail"],
        "joint_plane_clamp": ctx["clamp_detail"],
        "interior_wall_pairing": ctx["pairing"],
        "shells_after_weld": ctx["shells_welded"],
        "joint_planes": ctx["planes"],
        "parts": ctx["part_stats"],
        "part_count": len(ctx["parts"]),
        "joint_ball_offset_table": ctx["offsets"],
        "bone_radii_measured": ctx["limb_radii"],
        "bone_lengths": ctx["bone_lengths"],
        "probe_action": probe,
        "gates": {"PARTS_accounting": ctx["accounting"],
                  "GLB_written": gate_glb,
                  "N_parts_pre_export": gate_names_pre,
                  "N_parts_post_export": gate_names_post,
                  "P_bind_pose": gate_p,
                  "RIGID_arrival": gate_rigid,
                  "D_determinism": gate_d,
                  "ATLAS_untouched": gate_atlas},
        "note": ("Rigidity and displacement statistics are DIAGNOSTICS. Whether the joint "
                 "seam reads is the Director's, on the sheet, at his zoom."),
    }
    path = os.path.join(out_dir, "parts_manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    print("RIG_PARTS_OK " + json.dumps({"glb": out_glb, "sha256": manifest["output"]["sha256"],
                                    "manifest": path, "parts": len(ctx["parts"])}))


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
    #
    # The record on disk carries the same three-state vocabulary. The exit code is computed
    # BEFORE anything that can fail and delivered from a `finally`: re-parsing argv or
    # re-hashing the GLB inside this block can raise a SECOND exception, which used to leave
    # the whole `try` statement with `sys.exit` never reached (measured 2026-09-04).
    try:
        main()
    except BaseException as exc:                                      # noqa: BLE001
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
            "tool": "rig_parts", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "rig_parts", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            _line = json.dumps(_sentinel, default=str)
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
            print("RIG_PARTS_HALT " + _line)
            sys.exit(_code)
