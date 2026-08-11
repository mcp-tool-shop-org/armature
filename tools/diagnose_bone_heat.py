"""diagnose_bone_heat — why `ARMATURE_AUTO` produced no weights on the E07 subject.

    blender -b --factory-startup -P tools\\diagnose_bone_heat.py -- --glb=<in.glb> --out=<dir>

E07's Gate P liveness clause fired: the mesh did not move when a bone was posed. The cause
measured immediately behind it was that Blender's bone-heat weighting created all 17 deform
vertex groups and left **every one of them empty** — 399,140 of 399,140 vertices with a
total weight of zero. `parent_set` reports this as an INFO-level warning and returns
success.

This file is the sweep that narrows the mechanism, kept in the repo because a finding whose
recipe does not reproduce is not a finding. **It is a diagnostic and it is not a pipeline
stage.** Nothing here produces a rigged asset, and no arm of it is a route past the gate —
which of these routes, if any, E07 should have taken is the advisor's ruling and the
Director's call, not this tool's.

Each arm removes one candidate mechanism:

* **bones** — two bones instead of 22, to separate "the solve fails" from "this armature".
* **weld** — merge by distance, to test whether the 21,514 shells the glTF importer
  produces (vertices split at every UV seam) are what defeats the solve.
* **outer** — keep only the largest shell, to test whether the interior shells block it.
* **scale** — 0.1× to 100×, because bone heat is known to carry hard-coded epsilons and a
  figure 1.0 units tall is small for them.
* **envelope** — `ARMATURE_ENVELOPE` on the same mesh and the same armature, as the contrast
  that says whether the mesh can be weighted at all by anything.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

from armature_core import landmarks, sitelist  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bands", type=int, default=200)
    return p.parse_args(argv)


def load(glb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = 16, 1.0
    bpy.ops.import_scene.gltf(filepath=glb)
    return scene, [o for o in bpy.data.objects if o.type == "MESH"][0]


def world_verts(ob):
    n = len(ob.data.vertices)
    flat = np.empty(n * 3, dtype=np.float64)
    ob.data.vertices.foreach_get("co", flat)
    m = np.array(ob.matrix_world, dtype=np.float64)
    return flat.reshape(n, 3) @ m[:3, :3].T + m[:3, 3]


def shell_components(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    seen, comps = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            x = stack.pop()
            comp.append(x.index)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        comps.append(comp)
    bm.free()
    return comps, boundary, non_manifold


def weld(ob, dist):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def keep_only(ob, indices):
    keep = set(indices)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def build_and_bind(scene, ob, bands, mode="ARMATURE_AUTO", only=None):
    marks = landmarks.derive(world_verts(ob), n_bands=bands)["landmarks"]
    data = bpy.data.armatures.new("diag_armature")
    arm = bpy.data.objects.new("diag_rig", data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    for b in sitelist.BONES:
        if only and b.name not in only:
            continue
        eb = data.edit_bones.new(b.name)
        eb.head, eb.tail = marks[b.head], marks[b.tail]
        eb.use_deform = b.deform
        if b.parent and b.parent in made:
            eb.parent = made[b.parent]
            eb.use_connect = False
        made[b.name] = eb
    bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type=mode)

    idx = {g.index: g.name for g in ob.vertex_groups}
    n = len(ob.data.vertices)
    total = np.zeros(n)
    per = {name: 0 for name in idx.values()}
    for i, v in enumerate(ob.data.vertices):
        for ge in v.groups:
            if ge.group in idx:
                total[i] += ge.weight
                if ge.weight > 1e-9:
                    per[idx[ge.group]] += 1
    weighted = int((total > 1e-9).sum())
    return {
        "mode": mode,
        "groups_created": len(idx),
        "vertices": n,
        "weighted_vertices": weighted,
        "weighted_fraction": float(weighted) / n if n else 0.0,
        "empty_groups": sorted(k for k, c in per.items() if c == 0),
        "n_empty_groups": sum(1 for c in per.values() if c == 0),
        "weight_sum_min": float(total.min()) if n else None,
        "weight_sum_mean": float(total.mean()) if n else None,
    }


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    arms = {}

    scene, ob = load(args.glb)
    comps, boundary, non_manifold = shell_components(ob)
    arms["A_as_imported_full_rig"] = dict(
        build_and_bind(scene, ob, args.bands),
        topology={"shells": len(comps), "boundary_edges": boundary,
                  "non_manifold_edges": non_manifold})

    scene, ob = load(args.glb)
    arms["B_two_bones_only"] = build_and_bind(scene, ob, args.bands,
                                              only={"hips", "spine"})

    scene, ob = load(args.glb)
    arms["C_envelope_contrast"] = build_and_bind(scene, ob, args.bands,
                                                 mode="ARMATURE_ENVELOPE")

    for dist in (1e-6, 1e-4):
        scene, ob = load(args.glb)
        weld(ob, dist)
        comps, boundary, non_manifold = shell_components(ob)
        arms[f"D_welded_{dist:g}"] = dict(
            build_and_bind(scene, ob, args.bands),
            topology={"shells": len(comps), "boundary_edges": boundary,
                      "non_manifold_edges": non_manifold})

    scene, ob = load(args.glb)
    weld(ob, 1e-6)
    comps, _, _ = shell_components(ob)
    comps.sort(key=len, reverse=True)
    sizes = [len(c) for c in comps]
    keep_only(ob, comps[0])
    _, boundary, non_manifold = shell_components(ob)
    arms["E_outer_shell_only"] = dict(
        build_and_bind(scene, ob, args.bands),
        topology={"shells_before": len(sizes), "shell_sizes_top8": sizes[:8],
                  "boundary_edges": boundary, "non_manifold_edges": non_manifold})

    for s in (0.1, 2.0, 10.0, 100.0):
        scene, ob = load(args.glb)
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        ob.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        arms[f"F_scale_{s:g}x"] = build_and_bind(scene, ob, args.bands)

    payload = {
        "tool": "diagnose_bone_heat",
        "blender": bpy.app.version_string,
        "glb": args.glb,
        "arms": arms,
        "note": ("A DIAGNOSTIC. No arm here is a pipeline stage and none produces a rigged "
                 "asset. Which route E07 should take, if any, is the advisor's ruling."),
    }
    path = os.path.join(out, "bone_heat_diagnosis.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print("DIAGNOSIS_OK " + path)
    for name, rec in arms.items():
        print(f"  {name:<26} weighted {rec['weighted_vertices']:>7}/{rec['vertices']:<7} "
              f"({100 * rec['weighted_fraction']:6.2f}%)  empty_groups="
              f"{rec['n_empty_groups']}/{rec['groups_created']}")


if __name__ == "__main__":
    main()
