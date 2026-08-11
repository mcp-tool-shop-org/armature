"""Arm (d) stage 1 — strip the interior wall, then retopologise with **stock Blender only**.

Arms (a) through (c) all broke on the same rock: the performer is a **double-walled,
non-manifold shell**. Bone heat refuses it (E03), envelope tears it, and rigid parts carry
inner wall out into the open air (arm (c), twice). This stage attacks the geometry instead of
the partition.

**Licence, ruled by the Director 2026-08-11:** *"it's not fit for the pipeline, as it isn't
non-commercial safe."* QuadRemesher (Exoside) is **struck** — not enabled, not measured, no
licence row. The gate protects the **pipeline's** cleanliness and reproducibility, not one
rig's right to run a tool. Everything here is Blender's own: ``voxel_remesh`` and
``quadriflow_remesh``, licence-clean by construction under Blender's GPL.

Two variants, measured side by side:

* **A — QuadriFlow direct** on the welded outer shell.
* **B — voxel remesh first** (at a size derived from the *smallest* structure on the figure,
  never a global guess) **then QuadriFlow** to the same target.

Both are graded on whether the sculpted joint balls, the mitten hands and the toes survive —
those are the character, and a retopology that smooths them away has failed no matter what its
face count says.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_character as rc                                            # noqa: E402
import rig_parts as rp                                                # noqa: E402
from armature_core import landmarks, sitelist                         # noqa: E402
from armature_core.errors import GateFailure                          # noqa: E402


class QuadriflowDeclined(GateFailure):
    """QuadriFlow returned CANCELLED and changed nothing."""

    gate = "QUADRIFLOW"


class NoRetopoProduced(GateFailure):
    """Neither stock-Blender route produced a mesh."""

    gate = "RETOPO"
from make_parts_sheet import light_the_scene, ortho_camera, shoot     # noqa: E402

#: QuadriFlow target, in faces. Chosen for the features that ARE the character: the mitten
#: hands, the toes, and the curvature of the sculpted balls. Recorded with its result rather
#: than defended in the abstract -- the sheet decides whether it was enough.
TARGET_FACES = 40000
#: Voxel size as a fraction of the SMALLEST measured limb radius on this figure. A global
#: constant here would erase the toes to hold the torso; the ratio is what travels.
VOXEL_PER_SMALLEST_RADIUS = 1.0 / 6.0
#: **QuadriFlow is scale-sensitive, and it does not say so.** MEASURED 2026-08-11: on the
#: performer's voxel mesh the operator returns ``{'CANCELLED'}`` in 0.0 s at scale x1 and x10,
#: and ``{'FINISHED'}`` in 2.2 s at x100 (27,066 -> 7,646 quads). The warning it prints --
#: "the mesh needs to be manifold and have face normals that point in a consistent direction"
#: -- is misleading: the mesh passes all three of Blender's own manifold clauses (0 edges not
#: shared by exactly 2 faces, 0 directed edges used more than once, 0 vertices with more than
#: one fan), identically to a control mesh the operator accepts. The figure is simply too
#: small in absolute units for QuadriFlow's internal tolerance. A uniform scale is exactly
#: invertible, so scaling up, remeshing, and scaling back is geometrically free.
QUADRIFLOW_SCALE = 100.0


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--target-faces", type=int, default=TARGET_FACES)
    p.add_argument("--voxel", type=float, default=None,
                   help="override the voxel size. The default derives it from the smallest "
                        "LIMB radius, which is far too coarse for the face: at 0.002169 the "
                        "mouth crease is about one voxel wide and comes back as a ragged "
                        "trench. Features, not limbs, set this number.")
    return vars(p.parse_args(argv))


def import_subject(glb):
    scene = rc.fresh_scene(16)
    bpy.ops.import_scene.gltf(filepath=glb)
    ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
    return scene, ob


def extract_outer_shell(ob, diagonal):
    """Delete the interior wall, then repair the glTF seam splits.

    **The rule, recorded:** connected components are computed on *welded* positions (glTF
    splits a vertex at every UV and normal seam, presenting 21,514 shells where the asset has
    67); the component carrying the **most faces** is the exterior; every face outside it is
    deleted. The survivors are then welded by distance at 1e-6 x the bbox diagonal, because
    QuadriFlow needs real edge connectivity and the seam splits leave a boundary edge at every
    UV island.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    before_faces, before_verts = len(bm.faces), len(bm.verts)

    face_comp, exterior, n_shells = rp.classify_shells(bm, diagonal)
    doomed = [bm.faces[int(i)] for i in np.flatnonzero(face_comp != exterior)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    after_delete = len(bm.faces)

    # bmesh.ops.remove_doubles returns None in Blender 5.2 -- count the vertices instead
    # of trusting a return value the API does not give.
    verts_pre_weld = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6 * diagonal)
    welded_away = verts_pre_weld - len(bm.verts)
    bm.faces.ensure_lookup_table()

    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    report = {
        "rule": ("welded-position connected components; keep the component with the most "
                 "faces; delete the rest; then weld by distance at 1e-6 x diagonal to repair "
                 "the glTF UV/normal seam splits"),
        "shells_welded": n_shells,
        "faces_before": before_faces, "verts_before": before_verts,
        "faces_interior_deleted": before_faces - after_delete,
        "interior_fraction": (before_faces - after_delete) / before_faces,
        "faces_after": len(bm.faces), "verts_after": len(bm.verts),
        "verts_welded_away": welded_away,
        "non_manifold_edges": non_manifold, "boundary_edges": boundary,
        "is_closed_manifold": non_manifold == 0 and boundary == 0,
    }
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return report


def _select_only(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def _duplicate(ob, name):
    new = ob.copy()
    new.data = ob.data.copy()
    new.name = new.data.name = name
    bpy.context.scene.collection.objects.link(new)
    return new


def mesh_stats(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    stats = {
        "faces": len(bm.faces), "verts": len(bm.verts), "edges": len(bm.edges),
        "quads": quads, "tris": tris, "ngons": ngons,
        "quad_fraction": quads / max(len(bm.faces), 1),
        "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold),
        "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
    }
    stats["is_closed_manifold"] = (stats["non_manifold_edges"] == 0
                                   and stats["boundary_edges"] == 0)
    bm.free()
    return stats


def deviation_from(reference_ob, ob, diagonal):
    """How far the retopologised surface sits from the surface it replaced.

    Every vertex of the new mesh is measured to the nearest point on the ORIGINAL outer shell.
    This is the number that says whether the sculpted balls kept their curvature or were
    smoothed into the limb -- but it is a **diagnostic**. It gates nothing. The Director's eye
    on the closeups decides whether the character survived.
    """
    from mathutils.bvhtree import BVHTree
    bm_ref = bmesh.new()
    bm_ref.from_mesh(reference_ob.data)
    bm_ref.faces.ensure_lookup_table()
    bvh = BVHTree.FromPolygons([v.co.copy() for v in bm_ref.verts],
                               [[v.index for v in f.verts] for f in bm_ref.faces],
                               all_triangles=False)
    d = []
    for v in ob.data.vertices:
        loc, nrm, idx, dist = bvh.find_nearest(v.co)
        if idx is not None:
            d.append(float(dist))
    bm_ref.free()
    a = np.array(d) if d else np.zeros(1)
    return {"measured_verts": int(len(d)),
            "mean": float(a.mean()), "p99": float(np.percentile(a, 99)),
            "max": float(a.max()),
            "max_as_fraction_of_diagonal": float(a.max() / diagonal),
            "note": "diagnostic only -- gates nothing; the eye judges the closeups"}


def quadriflow(ob, target_faces, scale=QUADRIFLOW_SCALE):
    """Scale up, remesh, scale back — see QUADRIFLOW_SCALE for the measurement behind it.

    The operator's return value is checked. ``{'CANCELLED'}`` is a silent no-op that leaves
    the mesh untouched, and arm (d)'s first run recorded it as a successful retopology of
    147,450 faces into 147,450 faces. A gate that reads the return value costs one line.
    """
    _select_only(ob)
    ob.data.transform(Matrix.Scale(scale, 4))
    ob.data.update()
    t = time.time()
    result = bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=False,
                                              use_preserve_sharp=False,
                                              use_preserve_boundary=False,
                                              preserve_attributes=False, smooth_normals=False,
                                              mode="FACES", target_faces=int(target_faces),
                                              seed=0)
    secs = time.time() - t
    ob.data.transform(Matrix.Scale(1.0 / scale, 4))
    ob.data.update()
    if "FINISHED" not in str(result):
        raise QuadriflowDeclined("the operator declined the mesh and changed nothing",
                                 {"returned": str(result), "scale": scale,
                                  "target_faces": int(target_faces),
                                  "faces_unchanged": len(ob.data.polygons)})
    return secs, str(result)


def voxel_remesh(ob, voxel_size):
    _select_only(ob)
    ob.data.remesh_voxel_size = float(voxel_size)
    ob.data.remesh_voxel_adaptivity = 0.0
    t = time.time()
    bpy.ops.object.voxel_remesh()
    return time.time() - t


def smallest_limb_radius(ob):
    src = rc.world_verts(ob)
    lm = landmarks.derive(src, n_bands=200)
    radii = landmarks.bone_radii(lm, sitelist.BONES)
    named = {k: v for k, v in radii.items() if v and v > 0}
    smallest = min(named.items(), key=lambda kv: kv[1])
    return smallest[0], float(smallest[1]), {k: float(v) for k, v in named.items()}


def render_comparison(scene, variants, out_dir, diagonal, centre):
    """Full figure plus the three regions that decide it: a sculpted ball, a hand, a foot."""
    light_the_scene(scene)
    os.makedirs(out_dir, exist_ok=True)
    lo, hi = centre
    height = hi[2] - lo[2]
    mid_x = 0.5 * (lo[0] + hi[0])
    regions = [
        ("figure", (mid_x, 0.0, lo[2] + 0.5 * height), height * 1.12, 0.0),
        ("shoulder ball", (mid_x + 0.085, 0.0, lo[2] + 0.79 * height), height * 0.17, 0.0),
        ("mitten hand", (mid_x + 0.115, 0.0, lo[2] + 0.50 * height), height * 0.15, 0.0),
        ("foot and toes", (mid_x + 0.055, 0.0, lo[2] + 0.035 * height), height * 0.15, 18.0),
    ]
    rows = []
    for region, target, oscale, azim in regions:
        panels = []
        for label, ob in variants:
            for _, other in variants:
                other.hide_render = other is not ob
            ortho_camera(scene, f"cam_{label}_{region}", Vector(target), oscale,
                         (700, 1150) if region == "figure" else (700, 700), azim)
            path = os.path.join(out_dir, f"{label}_{region}.png".replace(" ", "_"))
            shoot(scene, path)
            panels.append({"body": path, "label": label})
        rows.append({"title": region, "panels": panels})
    for _, other in variants:
        other.hide_render = False
    return rows


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    os.makedirs(out_dir, exist_ok=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%S")

    scene, ob = import_subject(args["glb"])
    src = rc.world_verts(ob)
    lo, hi = src.min(0), src.max(0)
    diagonal = float(np.linalg.norm(hi - lo))

    smallest_name, smallest_r, all_radii = smallest_limb_radius(ob)
    voxel = args["voxel"] if args["voxel"] else smallest_r * VOXEL_PER_SMALLEST_RADIUS

    extraction = extract_outer_shell(ob, diagonal)
    ob.name = ob.data.name = "outer_shell"
    shell_stats = mesh_stats(ob)

    variant_a = _duplicate(ob, "A_quadriflow_direct")
    variant_b = _duplicate(ob, "B_voxel_then_quadriflow")

    results = {}
    try:
        secs, returned = quadriflow(variant_a, args["target_faces"])
        results["A_quadriflow_direct"] = {
            "route": "QuadriFlow directly on the welded outer shell, at x100 scale",
            "seconds": round(secs, 1), "returned": returned, **mesh_stats(variant_a),
            "deviation": deviation_from(ob, variant_a, diagonal)}
    except Exception as exc:                                          # noqa: BLE001
        results["A_quadriflow_direct"] = {"route": "QuadriFlow direct", "FAILED": str(exc),
                                          "exception": type(exc).__name__}

    try:
        vsecs = voxel_remesh(variant_b, voxel)
        after_voxel = mesh_stats(variant_b)
        qsecs, returned = quadriflow(variant_b, args["target_faces"])
        results["B_voxel_then_quadriflow"] = {
            "route": f"voxel remesh at {voxel:.5f} (= {smallest_name} radius "
                     f"{smallest_r:.5f} / 6) then QuadriFlow at x100 scale",
            "voxel_size": voxel,
            "voxel_derivation": ("explicit override -- limb radii do not bound facial "
                                 "features" if args["voxel"] else
                                 f"smallest measured limb radius ({smallest_name} = "
                                 f"{smallest_r:.5f}) / 6"),
            "seconds_voxel": round(vsecs, 1), "seconds_quadriflow": round(qsecs, 1),
            "returned": returned,
            "after_voxel_before_quadriflow": after_voxel,
            **mesh_stats(variant_b), "deviation": deviation_from(ob, variant_b, diagonal)}
    except Exception as exc:                                          # noqa: BLE001
        results["B_voxel_then_quadriflow"] = {"route": "voxel then QuadriFlow",
                                              "FAILED": str(exc),
                                              "exception": type(exc).__name__}

    live = [k for k, v in results.items() if "FAILED" not in v and v.get("faces", 0) > 0]
    if not live:
        raise NoRetopoProduced("both stock-Blender routes failed to produce a mesh",
                               {"results": results})

    for name, obj in (("A_quadriflow_direct", variant_a),
                      ("B_voxel_then_quadriflow", variant_b)):
        if name not in live:
            continue
        path = os.path.join(out_dir, f"{name}.glb")
        _select_only(obj)
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                                  export_apply=False, export_yup=True)
        results[name]["glb"] = path
        results[name]["sha256"] = rc.sha256_file(path)

    shell_path = os.path.join(out_dir, "outer_shell.glb")
    _select_only(ob)
    bpy.ops.export_scene.gltf(filepath=shell_path, export_format="GLB", use_selection=True,
                              export_apply=False, export_yup=True)

    columns = [(f"input — outer shell, {shell_stats['faces']:,} tris", ob)]
    if "A_quadriflow_direct" in live:
        columns.append((f"A — QuadriFlow direct, "
                        f"{results['A_quadriflow_direct']['faces']:,} faces", variant_a))
    else:
        bpy.data.objects.remove(variant_a, do_unlink=True)
    if "B_voxel_then_quadriflow" in live:
        columns.append((f"B — voxel then QuadriFlow, "
                        f"{results['B_voxel_then_quadriflow']['quads']:,} quads", variant_b))
    rows = render_comparison(scene, columns, os.path.join(out_dir, "panels"), diagonal,
                             (lo, hi))

    manifest = {
        "tool": "rig_retopo", "started": started, "source_glb": args["glb"],
        "source_sha256": rc.sha256_file(args["glb"]), "diagonal": diagonal,
        "licence": {
            "ruling": "Director 2026-08-11: 'it's not fit for the pipeline, as it isn't "
                      "non-commercial safe.'",
            "struck": "QuadRemesher (Exoside) — not enabled, not measured, no licence row",
            "used": "Blender 5.2 built-ins only (voxel_remesh, quadriflow_remesh) — GPL, "
                    "COMMERCIAL: YES, and no per-rig entitlement is involved",
        },
        "target_faces": args["target_faces"],
        "quadriflow_scale": {
            "factor": QUADRIFLOW_SCALE,
            "why": "MEASURED: quadriflow_remesh returns CANCELLED in 0.0s at x1 and x10 and "
                   "FINISHED in 2.2s at x100 on this figure. Its warning names manifoldness, "
                   "but the mesh passes all three of Blender's manifold clauses identically "
                   "to a control the operator accepts -- the figure is too small in absolute "
                   "units for QuadriFlow's tolerance. A uniform scale is exactly invertible.",
        },
        "smallest_limb_radius": {"bone": smallest_name, "radius": smallest_r},
        "limb_radii": all_radii,
        "outer_shell_extraction": extraction, "outer_shell_stats": shell_stats,
        "variants": results, "outer_shell_glb": shell_path,
        "sheet_rows": rows,
    }
    with open(os.path.join(out_dir, "retopo_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    with open(os.path.join(out_dir, "panels.json"), "w", encoding="utf-8") as fh:
        json.dump({"title": "E07 arm (d) — outer-shell extraction and stock-Blender retopo",
                   "subtitle": "the interior wall deleted, then retopologised · the sculpted "
                               "balls, the mitten hands and the toes are what decide it",
                   "out": out_dir, "filename": "E07-retopo.png",
                   "rows": rows}, fh, indent=2)
    print("RETOPO_OK " + json.dumps({k: {"faces": v.get("faces"), "quads": v.get("quads"),
                                         "manifold": v.get("is_closed_manifold"),
                                         "max_dev": v.get("deviation", {}).get("max")}
                                     for k, v in results.items()}))


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:                                      # noqa: BLE001
        import traceback
        traceback.print_exc()
        gate = getattr(exc, "gate", None)
        try:
            a = parse_args()
            d = os.path.abspath(a["out"])
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "halt.json"), "w", encoding="utf-8") as fh:
                json.dump({"tool": "rig_retopo",
                           "outcome": ("HALTED — a gate fired" if gate
                                       else "FAILED — an unhandled error"),
                           "gate": gate or "n/a", "exception": type(exc).__name__,
                           "message": str(exc), "evidence": getattr(exc, "evidence", {}),
                           "traceback": traceback.format_exc()}, fh, indent=2, default=str)
            print(("HALT " if gate else "ERROR ") + json.dumps({"gate": gate or "n/a"}))
        finally:
            sys.exit(2 if gate else 1)
