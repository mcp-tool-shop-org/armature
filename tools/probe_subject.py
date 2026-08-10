#!/usr/bin/env python
"""probe_subject — open a GLB and report what it is. Reads only; writes only JSON.

    blender -b -P tools\\probe_subject.py -- --out=<dir> --glb=<path> [--glb=<path> ...]

E02's premise 6 ("the subject is a character") is marked MEASURED on the condition
that the executor opens the asset rather than reading its filename. This is that
measurement, and it is separate from `probe_glb.py` on purpose: that tool answers
"does this asset carry a usable armature", this one answers "what shape is it".

Subject selection is `blender_scene.render_visible_meshes`, not `type == "MESH"`.
That distinction is not cosmetic — it is the defect G4 fired on in E01. Blender's
glTF importer creates a hidden `glTF_not_exported` collection holding a radius-1.0
Icosphere, and selecting by type sweeps it in. On a ~0.5-radius character that decoy
*doubles* the measured bounding sphere, so a probe written the naive way would report
proportions for a figure-plus-phantom-ball and read as authoritative while doing it.

No verdict is emitted. There is no `is_character` field and no threshold, because
whether the figure is the right character is canon and the Director's to judge.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from armature_core import blender_scene  # noqa: E402
from armature_core.subject import extent_summary  # noqa: E402


def probe_one(path):
    rec = {"path": path, "exists": os.path.isfile(path)}
    if not rec["exists"]:
        rec["error"] = "file not found"
        return rec

    rec["bytes"] = os.path.getsize(path)
    scene = blender_scene.reset_scene()
    meshes, armatures, info = blender_scene.import_glb(path)
    rec["import"] = info

    visible = blender_scene.render_visible_meshes(scene, meshes)
    rec["mesh_objects_all"] = [o.name for o in meshes]
    rec["mesh_objects_render_visible"] = [o.name for o in visible]
    rec["mesh_objects_excluded"] = [o.name for o in meshes if o not in visible]
    rec["armature_names"] = [o.name for o in armatures]

    bounds = blender_scene.world_bounds(visible)
    if bounds is None:
        rec["error"] = "no render-visible geometry to measure"
        return rec
    center, half, radius = bounds
    rec["bbox_center"] = [float(v) for v in center]
    rec["bbox_half_extent"] = [float(v) for v in half]
    rec["bounding_sphere_radius"] = float(radius)
    rec["summary"] = extent_summary(half)

    # Reported because it is the E01 defect made visible rather than merely avoided:
    # what the naive `type == "MESH"` selection would have concluded on this asset.
    naive = blender_scene.world_bounds(meshes)
    if naive is not None:
        rec["naive_type_mesh_selection"] = {
            "bbox_half_extent": [float(v) for v in naive[1]],
            "bounding_sphere_radius": float(naive[2]),
            "summary": extent_summary(naive[1]),
        }
    return rec


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_dir, paths = None, []
    for token in argv:
        key, _, value = token[2:].partition("=")
        if key == "out":
            out_dir = value
        elif key == "glb":
            paths.append(value)
    if not out_dir or not paths:
        raise SystemExit("usage: -- --out=<dir> --glb=<path> [--glb=<path> ...]")
    os.makedirs(out_dir, exist_ok=True)

    records = [probe_one(p) for p in paths]
    payload = {
        "tool": "probe_subject",
        "blender": bpy.app.version_string,
        "n_files": len(records),
        "files": records,
    }
    out_path = os.path.join(out_dir, "subject_extents.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print("PROBE_SUBJECT " + json.dumps({"json": out_path, "n": len(records)}))


if __name__ == "__main__":
    main()
