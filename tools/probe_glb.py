#!/usr/bin/env python
"""probe_glb — measure what a GLB actually contains. Reads only; writes only JSON.

    blender -b -P tools\\probe_glb.py -- --out=<dir> --glb=<a.glb> --glb=<b.glb> ...

E01's premise 3 ("some of those GLBs carry a usable armature") is marked ASSUMED, and
P2 is the measurement that settles it. The conjunction it counts is *loads* AND *has
bones* AND *bones are usable*, so each clause is measured and reported separately —
a joined number with no clauses is a number that cannot be wrong in a useful way.

"Usable" here is the spec's word: **posable and named**. That is a mechanical property
and it is deliberately not the same question as whether the rig is any good. The
studio's June 2026 verdict (rigging abandoned — UniRig shreds faced characters) is
about rig *quality*; conflating the two would make this measurement answer a question
nobody asked.

P2b is the stricter, downstream-relevant count: whether bone names identify the
anatomical sites a body skeleton needs. `docs/research-grounding.md` F20 records
OpenPose-18's limbSeq and keypoint count but **not** the keypoint order or names, so
no complete COCO-18 map can be built from the retrieved record regardless of what the
names say; this reports which sites are findable, not that a map exists.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Euler  # noqa: E402

# Token sets for the anatomical sites an 18-keypoint body skeleton needs. Matching is
# substring-on-lowercased-name, side-aware. These are naming conventions (Mixamo,
# Rigify, glTF/VRM humanoid), not a retrieved COCO-18 ordering.
SITES = {
    "nose": (("nose",), None),
    "neck": (("neck",), None),
    "shoulder.L": (("shoulder", "upperarm", "upper_arm", "arm"), "L"),
    "shoulder.R": (("shoulder", "upperarm", "upper_arm", "arm"), "R"),
    "elbow.L": (("elbow", "forearm", "lowerarm", "lower_arm"), "L"),
    "elbow.R": (("elbow", "forearm", "lowerarm", "lower_arm"), "R"),
    "wrist.L": (("wrist", "hand"), "L"),
    "wrist.R": (("wrist", "hand"), "R"),
    "hip.L": (("hip", "upleg", "upperleg", "upper_leg", "thigh"), "L"),
    "hip.R": (("hip", "upleg", "upperleg", "upper_leg", "thigh"), "R"),
    "knee.L": (("knee", "leg", "shin", "calf"), "L"),
    "knee.R": (("knee", "leg", "shin", "calf"), "R"),
    "ankle.L": (("ankle", "foot"), "L"),
    "ankle.R": (("ankle", "foot"), "R"),
    "eye.L": (("eye",), "L"),
    "eye.R": (("eye",), "R"),
    "ear.L": (("ear",), "L"),
    "ear.R": (("ear",), "R"),
}

LEFT_TOKENS = ("left", "_l", ".l", "l_", "lft", "lf_")
RIGHT_TOKENS = ("right", "_r", ".r", "r_", "rgt", "rt_")


def _side_of(name):
    low = name.lower()
    left = any(t in low for t in LEFT_TOKENS) or low.endswith("l")
    right = any(t in low for t in RIGHT_TOKENS) or low.endswith("r")
    if left and not right:
        return "L"
    if right and not left:
        return "R"
    return None


def match_sites(bone_names):
    found = {}
    for site, (tokens, side) in SITES.items():
        hits = []
        for name in bone_names:
            low = name.lower()
            if not any(t in low for t in tokens):
                continue
            if side is not None and _side_of(name) != side:
                continue
            hits.append(name)
        if hits:
            found[site] = sorted(hits)[:3]
    return found


def probe_one(path):
    rec = {"path": path, "exists": os.path.isfile(path)}
    if not rec["exists"]:
        rec["clause_A_loads"] = False
        rec["error"] = "file not found"
        return rec
    rec["bytes"] = os.path.getsize(path)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
        rec["clause_A_loads"] = True
    except Exception as exc:  # a failed import is a measurement, not a crash
        rec["clause_A_loads"] = False
        rec["error"] = f"{type(exc).__name__}: {exc}"
        return rec

    objs = list(bpy.data.objects)
    armatures = [o for o in objs if o.type == "ARMATURE"]
    meshes = [o for o in objs if o.type == "MESH"]

    rec["objects"] = len(objs)
    # A file whose name says `_rigged` but that carries no ARMATURE has to have put
    # its skeleton somewhere; the type histogram is what says where.
    types = {}
    for o in objs:
        types[o.type] = types.get(o.type, 0) + 1
    rec["object_types"] = types
    rec["empty_names_sample"] = sorted(o.name for o in objs if o.type == "EMPTY")[:12]
    rec["mesh_objects"] = len(meshes)
    rec["vertices"] = int(sum(len(o.data.vertices) for o in meshes))
    rec["materials"] = len(bpy.data.materials)
    rec["images"] = len(bpy.data.images)
    rec["actions"] = len(bpy.data.actions)
    rec["armature_objects"] = len(armatures)

    total_bones = sum(len(a.data.bones) for a in armatures)
    rec["bone_count"] = total_bones
    rec["clause_B_has_bones"] = len(armatures) > 0 and total_bones > 0

    bone_names = []
    for a in armatures:
        bone_names.extend(b.name for b in a.data.bones)
    rec["bone_names"] = bone_names
    rec["bone_names_nonempty"] = all(n.strip() for n in bone_names) if bone_names else False

    # clause C — posable: can a pose bone actually take a rotation?
    posable = False
    pose_error = None
    if rec["clause_B_has_bones"]:
        try:
            arm = armatures[0]
            pb = arm.pose.bones[0]
            before = pb.rotation_mode
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = Euler((0.1, 0.0, 0.0), "XYZ")
            bpy.context.view_layer.update()
            posable = abs(pb.rotation_euler.x - 0.1) < 1e-6
            pb.rotation_euler = Euler((0.0, 0.0, 0.0), "XYZ")
            pb.rotation_mode = before
        except Exception as exc:
            pose_error = f"{type(exc).__name__}: {exc}"
    rec["clause_C_posable_and_named"] = bool(posable and rec["bone_names_nonempty"])
    if pose_error:
        rec["pose_error"] = pose_error

    rec["P2_joined"] = bool(
        rec["clause_A_loads"] and rec["clause_B_has_bones"] and rec["clause_C_posable_and_named"]
    )

    # skinning: bones that actually deform something
    vgroups = set()
    for m in meshes:
        vgroups.update(g.name for g in m.vertex_groups)
    rec["vertex_groups"] = len(vgroups)
    rec["bones_with_matching_vertex_group"] = len(set(bone_names) & vgroups)

    sites = match_sites(bone_names)
    rec["anatomical_sites_found"] = sorted(sites)
    rec["anatomical_sites_count"] = len(sites)
    rec["anatomical_sites_detail"] = sites
    rec["P2b_all_18_sites_named"] = len(sites) == len(SITES)
    return rec


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_dir, globs = None, []
    for token in argv:
        key, _, value = token[2:].partition("=")
        if key == "out":
            out_dir = value
        elif key == "glb":
            globs.append(value)
    if not out_dir or not globs:
        raise SystemExit("usage: -- --out=<dir> --glb=<path> [--glb=<path> ...]")
    os.makedirs(out_dir, exist_ok=True)

    records = [probe_one(p) for p in globs]
    summary = {
        "n_files": len(records),
        "clause_A_loads": sum(1 for r in records if r.get("clause_A_loads")),
        "clause_B_has_bones": sum(1 for r in records if r.get("clause_B_has_bones")),
        "clause_C_posable_and_named": sum(1 for r in records if r.get("clause_C_posable_and_named")),
        "P2_joined": sum(1 for r in records if r.get("P2_joined")),
        "P2b_all_18_sites_named": sum(1 for r in records if r.get("P2b_all_18_sites_named")),
        "blender": bpy.app.version_string,
    }
    payload = {"summary": summary, "files": records}
    path = os.path.join(out_dir, "p2_armatures.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print("PROBE_GLB " + json.dumps({"summary": summary, "json": path}))


if __name__ == "__main__":
    main()
