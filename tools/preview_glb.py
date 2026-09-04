"""Headless GLB preview: import, measure, render 2 full views + 2 head crops.

blender -b --factory-startup -P preview_glb.py -- --glb <path> --out <dir> --name <name>
Read-only on the GLB; writes renders + stats.json into --out.

`make_cast_sheet.py` consumes the `<name>_stats.json` this writes.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from armature_core import blender_scene  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

#: The engine identifiers this tool will accept, in the order it tries them. The loop
#: exists because Blender renamed EEVEE between versions; the ORDER is now the same one
#: `make_skeleton_sheet`, `make_binding_sheet` and `make_parts_sheet` use, because this
#: file used to try them the other way round and a sheet rendered beside a preview could
#: be drawn by a different engine with nothing in either record able to say so.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")


class PreviewGlbGate(GateFailure):
    """The preview could not be composed, or could not be composed reproducibly."""

    gate = "PREVIEW_GLB"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--name", required=True)
    return p.parse_args(argv)


def scene_bbox(objs):
    lo = Vector((1e18, 1e18, 1e18))
    hi = Vector((-1e18, -1e18, -1e18))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def look_at(cam, target):
    d = target - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def select_engine(scene, candidates=ENGINE_CANDIDATES):
    """Set the render engine, and RAISE if none of the candidate names is valid.

    MEASURED 2026-09-04 (F-bba38f1c): the loop this replaces had no `else`, so if a future
    Blender renamed both identifiers the `for` would complete normally, nothing would be
    set, and the preview would render on whatever engine the factory settings left in
    place — with no field anywhere in the record able to reveal it. Returns the engine
    actually set, so the record can state it.
    """
    for eng in candidates:
        try:
            scene.render.engine = eng
        except TypeError:
            continue
        return eng
    raise PreviewGlbGate(
        "none of the candidate render engines is valid on this Blender, so the preview "
        "would be drawn by whatever the factory settings left in place",
        {"candidates": list(candidates), "blender": bpy.app.version_string})


def add_camera_render(name_suffix, center, radius, azim_deg, elev_deg, res, out_dir, args):
    scn = bpy.context.scene
    cam_data = bpy.data.cameras.new("cam_" + name_suffix)
    cam_data.lens = 50.0
    cam_data.sensor_width = 36.0
    cam = bpy.data.objects.new("cam_" + name_suffix, cam_data)
    scn.collection.objects.link(cam)
    fov = 2.0 * math.atan(cam_data.sensor_width / (2.0 * cam_data.lens))
    dist = (radius / math.tan(fov / 2.0)) * 1.18
    a = math.radians(azim_deg)
    e = math.radians(elev_deg)
    cam.location = center + Vector((
        dist * math.cos(e) * math.sin(a),
        -dist * math.cos(e) * math.cos(a),
        dist * math.sin(e),
    ))
    look_at(cam, center)
    scn.camera = cam
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.filepath = os.path.join(out_dir, f"{args.name}_{name_suffix}.png")
    bpy.ops.render.render(write_still=True)


def main():
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=args.glb)

    scn = bpy.context.scene
    all_meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    # `render_visible_meshes` and not `type == "MESH"` — CARRIED from
    # `render_start_frame.py:435`, the shape ten sibling tools already use. Blender's glTF
    # importer drops a hidden radius-1.0 Icosphere into `glTF_not_exported`; every number
    # below is measured over this list — the triangle total, and `scene_bbox`, whose radius
    # sets every camera distance and whose dims/hi.z set the head-crop centre and radius.
    # E02-report.md:34 measured that decoy turning a 3.23:1 figure into a 1.05:1 near-cube:
    # here it frames the character too small and crops the head off-centre, and the operator
    # reads that as the mesh being wrong.
    meshes = blender_scene.render_visible_meshes(scn, all_meshes)
    if not meshes:
        raise PreviewGlbGate(
            f"{args.glb} imported {len(all_meshes)} mesh object(s) and none of them is "
            f"render-visible; there is nothing to preview",
            {"glb": args.glb, "mesh_objects_all": [o.name for o in all_meshes]})

    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    empties = [o for o in bpy.data.objects if o.type == "EMPTY"]
    tris = 0
    for ob in meshes:
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
    images = [(im.name, list(im.size)) for im in bpy.data.images if im.name != "Render Result"]
    stats = {
        "tool": "preview_glb",
        "blender": blender_scene.blender_provenance(),
        "glb": args.glb,
        "mesh_objects": len(meshes),
        "mesh_objects_all": [o.name for o in all_meshes],
        "mesh_objects_render_visible": [o.name for o in meshes],
        "mesh_objects_excluded": [o.name for o in all_meshes if o not in meshes],
        "armatures": [(a.name, len(a.data.bones), [b.name for b in a.data.bones[:6]]) for a in arms],
        "empties": len(empties),
        "triangles": tris,
        "materials": len(bpy.data.materials),
        "images": images,
    }

    lo, hi = scene_bbox(meshes)
    center = (lo + hi) / 2.0
    dims = hi - lo
    stats["bbox_dims"] = list(dims)
    radius = max(dims) / 2.0

    # head region: top 22% of the bbox, framed square
    head_c = Vector((center.x, center.y, hi.z - 0.11 * dims.z))
    head_r = max(0.14 * dims.z, 0.5 * max(dims.x, dims.y) * 0.6)

    stats["engine"] = select_engine(scn)
    scn.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scn.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.72, 0.72, 0.73, 1.0)
    bg.inputs[1].default_value = 1.0

    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("sun", sun_data)
    scn.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(35))
    fill_data = bpy.data.lights.new("fill", type="SUN")
    fill_data.energy = 1.2
    fill = bpy.data.objects.new("fill", fill_data)
    scn.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(60), 0.0, math.radians(-140))

    # Every refusal above this line can fire before a single pixel exists; the output
    # directory is created here so a halt does not leave an empty one behind for a later
    # run to read as a used one.
    os.makedirs(args.out, exist_ok=True)
    add_camera_render("full_a", center, radius, 30, 10, (640, 960), args.out, args)
    add_camera_render("full_b", center, radius, 210, 10, (640, 960), args.out, args)
    add_camera_render("head_a", head_c, head_r, 30, 6, (512, 512), args.out, args)
    add_camera_render("head_b", head_c, head_r, 210, 6, (512, 512), args.out, args)

    with open(os.path.join(args.out, f"{args.name}_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print("PREVIEW_GLB_OK " + json.dumps({"name": args.name, "engine": stats["engine"],
                                      "triangles": tris}))
    return 0


def _halt_keysafe(value):
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
    if isinstance(value, dict):
        return {str(k): _halt_keysafe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_halt_keysafe(v) for v in value]
    return value


if __name__ == "__main__":
    # THE HALT CONTRACT — one shape across all 21 Blender-side tools (wave 8; pinned by
    # `tests/test_instruments_amend_w8.py`). `blender -b -P` exits **0** when the script's
    # exception propagates (E07, measured three times: rig_character.py, rig_parts.py,
    # author_walk.py), so a halt that does not exit deliberately is reported as a success.
    #
    # MEASURED 2026-09-04 (F-7e64c103): this file called `main()` bare at module scope —
    # no guard, no handler, no sentinel — and was exempted from the wave-6 exit-handler
    # census by name, on the premise that it is "a library of preview helpers ... not
    # invoked as a script". Its own docstring line 3 is the command line that invokes it.
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
        traceback.print_exc()
        _detail = getattr(exc, "evidence", None)
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _sentinel = {
            "tool": "preview_glb",
            "outcome": ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                        else "REFUSED — the tool declined to proceed"
                        if isinstance(exc, ArmatureError)
                        else "FAILED — an unhandled error"),
            "gate": getattr(exc, "gate", None),
            "error": type(exc).__name__, "message": str(exc),
            "evidence": _halt_keysafe(_detail) if isinstance(_detail, dict) else None}
        # The sentinel and the exit code are the contract, and NEITHER may be deleted by a
        # failure to serialise the sentinel itself. `_code` is computed before anything that
        # can raise and delivered from a `finally`; the fallback line carries only values
        # that are already strings, so it cannot fail in turn.
        try:
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            _line = json.dumps({
                "tool": _sentinel["tool"], "outcome": _sentinel["outcome"], "gate": None,
                "error": _sentinel["error"], "message": _sentinel["message"],
                "evidence": None})
        finally:
            print("PREVIEW_GLB_HALT " + _line)
            sys.exit(_code)
