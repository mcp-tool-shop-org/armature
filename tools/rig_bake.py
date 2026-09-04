"""Arm (d) stage 2 — new UVs on the retopologised mesh, and the terracotta atlas baked
old to new.

The retopology throws the original UV layout away: QuadriFlow builds new vertices with no
correspondence to the old ones, so the atlas cannot simply be carried across. The surface has
to be re-parameterised and the colour transferred by **baking** — casting rays from the new
surface to the old one and recording what the old one looked like.

Everything is stock Blender: ``uv.smart_project`` for the unwrap and Cycles' *Selected to
Active* bake for the transfer. No external tool, no addon, no licence question.

**The cage is derived, not guessed.** The retopologised surface sits at most `max_deviation`
from the surface it replaces (measured in stage 1, 0.00358 on this figure). The cage
extrusion is a multiple of that measured number, so the rays always start outside the old
surface and always land on it. A global constant here would either miss the old surface
entirely on the thin limbs or punch through the figure at the torso.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_character as rc                                            # noqa: E402
from armature_core import blender_scene                               # noqa: E402
from armature_core.errors import GateFailure                          # noqa: E402

#: Bake resolution. The Director's deliverable atlas.
ATLAS = 4096
#: Cage extrusion as a multiple of the MEASURED stage-1 deviation between the two surfaces.
CAGE_PER_DEVIATION = 3.0
#: UV margin in pixels at 4096. Bleed has to exceed the mip footprint or seams show as dark
#: hairlines the moment the atlas is sampled below full resolution. This is the BAKE margin,
#: which is measured in pixels and is the correct knob for bleed.
BAKE_MARGIN = 16
#: **Smart UV Project's island_margin must stay at its default 0.0**, and the number below is
#: not a preference. MEASURED 2026-08-11 on this mesh: island_margin=0.0 packs to a UV area of
#: **0.627**; island_margin=0.002 collapses it to **0.0028**; island_margin=0.0039 (16 px at
#: 4096, which is what a pixel-margin intuition suggests) collapses it to **0.00077**. The
#: unwrap has thousands of islands, each demanding that margin, and the packer shrinks every
#: island to make them all fit. The UNWRAP gate caught this before a single ray was cast.
ISLAND_MARGIN = 0.0


class BakeEmpty(GateFailure):
    """The bake produced a blank or near-blank atlas."""

    gate = "BAKE"


class UnwrapFailed(GateFailure):
    """The unwrap produced no UV area to bake into."""

    gate = "UNWRAP"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--retopo", required=True, help="the retopologised GLB from stage 1")
    p.add_argument("--source", required=True, help="the ORIGINAL textured GLB")
    p.add_argument("--out", required=True)
    p.add_argument("--max-deviation", type=float, required=True,
                   help="stage 1's measured max deviation — the cage is derived from it")
    p.add_argument("--atlas", type=int, default=ATLAS)
    return vars(p.parse_args(argv))


class ImportEmpty(GateFailure):
    """An import brought in no usable mesh, or more than one and no way to choose."""

    gate = "IMPORT"


def _import(path, name):
    """The one render-visible mesh `path` brings in, renamed.

    MEASURED 2026-09-04, two defects in four lines. (a) The refusal was the BASE
    `GateFailure` with no evidence dict, so `gate` fell through to the class default and
    `halt.json` recorded `"gate": "G?"` with `"evidence": {}` -- a halt whose record cannot
    say which andon pulled, in a file that already defined two properly-tagged subclasses.
    (b) The population was a SET (`set(bpy.data.objects) - before`) and the choice was
    `new[0]`: iteration order over a set follows the objects' identity hashes and is not
    stable across processes. More than one mesh is the NORM here, because Blender's glTF
    importer adds the `glTF_not_exported` Icosphere, so WHICH mesh got baked was not
    reproducible from the recorded inputs -- and neither the manifest nor the BAKE andon
    named it. `_import` is called twice per run, for the source and the retopo target.

    Selection is now render visibility and an ambiguous result RAISES, the way
    `rig_character.build_pass` and `lift_solve.pick_subject` already refuse it. Order is
    the scene's own object order, not a set's.
    """
    before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=path)
    added = [o for o in bpy.data.objects if o.name not in before]
    meshes = [o for o in added if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(bpy.context.scene, meshes)
    if len(visible) != 1:
        raise ImportEmpty(
            f"{path} contributed {len(visible)} render-visible mesh object(s); exactly one "
            f"is needed and guessing would bake an object nobody asked about",
            {"path": path,
             "objects_added": [o.name for o in added],
             "mesh_objects": [o.name for o in meshes],
             "render_visible": [o.name for o in visible]})
    ob = visible[0]
    ob.name = ob.data.name = name
    return ob


def unwrap(ob, margin_px, atlas):
    """Smart UV Project, then measure that it actually produced area to bake into."""
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    while ob.data.uv_layers:
        ob.data.uv_layers.remove(ob.data.uv_layers[0])
    ob.data.uv_layers.new(name="retopo")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    t = time.time()
    result = bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=ISLAND_MARGIN,
                                      area_weight=0.0, correct_aspect=True,
                                      scale_to_bounds=False)
    secs = time.time() - t
    bpy.ops.object.mode_set(mode="OBJECT")

    uv = ob.data.uv_layers.active.data
    coords = np.array([list(d.uv) for d in uv])
    area = 0.0
    for poly in ob.data.polygons:
        pts = coords[list(poly.loop_indices)]
        x, y = pts[:, 0], pts[:, 1]
        area += abs(0.5 * float(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))
    rec = {"operator": "bpy.ops.uv.smart_project", "seconds": round(secs, 1),
           "returned": str(result), "angle_limit_rad": 1.15192,
           "island_margin": ISLAND_MARGIN,
           "island_margin_measured": {"0.0": 0.627, "0.002": 0.0028, "0.0039": 0.00077,
                                      "units": "packed UV area fraction"},
           "uv_area_fraction": area,
           "uv_in_unit_square": bool(coords.min() >= -1e-6 and coords.max() <= 1 + 1e-6)}
    if area < 0.05:
        raise UnwrapFailed("the unwrap produced almost no UV area", rec)
    return rec


def bake_material(ob, atlas, name="terracotta_retopo"):
    """A material whose ACTIVE node is the image the bake writes into."""
    for slot in list(ob.material_slots):
        ob.data.materials.clear()
        break
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    img = bpy.data.images.new(f"{name}_atlas", width=atlas, height=atlas, alpha=False)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.location = (-420, 240)
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    ob.data.materials.append(mat)
    arm_bake_target(ob)
    return mat, img, tex


def arm_bake_target(ob):
    """Select and activate the image texture node Cycles will write into.

    Cycles finds its bake destination by looking for the material's **active and selected**
    image texture node, and it refuses with *"No active and selected image texture node
    found"* otherwise. Setting this once at material-construction time is not enough — later
    edits to the node tree drop it — so it is re-asserted immediately before the bake call,
    and the number of materials armed is returned so a silent miss cannot pass for a success.
    """
    armed = 0
    for mat in ob.data.materials:
        if mat is None or mat.node_tree is None:
            continue
        nt = mat.node_tree
        tex = next((n for n in nt.nodes
                    if n.type == "TEX_IMAGE" and n.image is not None), None)
        if tex is None:
            continue
        for n in nt.nodes:
            n.select = False
        tex.select = True
        nt.nodes.active = tex
        armed += 1
    return armed


def bake(source, target, cage, margin, atlas):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type != "CPU"
    except Exception:                                                 # noqa: BLE001
        scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = cage
    scene.render.bake.max_ray_distance = cage * 2.0
    scene.render.bake.margin = margin
    scene.render.bake.use_clear = True
    scene.render.bake.target = "IMAGE_TEXTURES"

    bpy.ops.object.select_all(action="DESELECT")
    source.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    if arm_bake_target(target) == 0:
        raise BakeEmpty("no image texture node could be armed on the target material", {})
    t = time.time()
    result = bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"},
                                 use_selected_to_active=True, cage_extrusion=cage,
                                 max_ray_distance=cage * 2.0, margin=margin,
                                 use_clear=True)
    return time.time() - t, str(result)


def atlas_health(img):
    """Is there actually a texture in there? A blank bake is the failure this catches."""
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
    rgb = px[:, :3]
    lit = rgb.max(axis=1) > 0.02
    return {"pixels": int(len(rgb)), "non_black_fraction": float(lit.mean()),
            "mean_rgb": [float(v) for v in rgb[lit].mean(axis=0)] if lit.any() else [0, 0, 0],
            "std_rgb": [float(v) for v in rgb[lit].std(axis=0)] if lit.any() else [0, 0, 0]}


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    os.makedirs(out_dir, exist_ok=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%S")

    rc.fresh_scene(16)
    source = _import(args["source"], "source_original")
    target = _import(args["retopo"], "retopo_clean")
    subject_selection = {
        "how": ("the one RENDER-VISIBLE mesh each import contributed; an ambiguous import "
                "raises rather than indexing into an unordered set"),
        "source_original": source.name, "retopo_clean": target.name}

    cage = args["max_deviation"] * CAGE_PER_DEVIATION
    uv_rec = unwrap(target, BAKE_MARGIN, args["atlas"])
    mat, img, tex = bake_material(target, args["atlas"])
    secs, result = bake(source, target, cage, BAKE_MARGIN, args["atlas"])
    if "FINISHED" not in result:
        raise BakeEmpty("the bake operator declined", {"returned": result, "cage": cage})

    health = atlas_health(img)
    if health["non_black_fraction"] < 0.20:
        raise BakeEmpty("the baked atlas is mostly empty", {"health": health, "cage": cage,
                                                            "returned": result})

    atlas_path = os.path.join(out_dir, "terracotta_retopo_4096.png")
    img.filepath_raw = atlas_path
    img.file_format = "PNG"
    img.save()
    img.pack()

    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    out_glb = os.path.join(out_dir, "performer_retopo_textured.glb")
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", use_selection=True,
                              export_apply=False, export_yup=True, export_image_format="AUTO")

    manifest = {
        "tool": "rig_bake", "started": started,
        "blender": blender_scene.blender_provenance(),
        "subject_selection": subject_selection,
        "inputs": {"retopo": args["retopo"], "source": args["source"],
                   "source_sha256": rc.sha256_file(args["source"]),
                   "retopo_sha256": rc.sha256_file(args["retopo"])},
        "unwrap": uv_rec,
        "bake": {"engine": "CYCLES", "device": bpy.context.scene.cycles.device,
                 "samples": bpy.context.scene.cycles.samples,
                 "type": "DIFFUSE", "pass_filter": ["COLOR"],
                 "use_selected_to_active": True,
                 "cage_extrusion": cage,
                 "cage_derivation": f"{CAGE_PER_DEVIATION} x the stage-1 measured max "
                                    f"deviation {args['max_deviation']:.5f}",
                 "max_ray_distance": cage * 2.0, "margin_px": BAKE_MARGIN,
                 "atlas": args["atlas"], "seconds": round(secs, 1), "returned": result},
        "atlas_health": health,
        "outputs": {"atlas": atlas_path, "atlas_sha256": rc.sha256_file(atlas_path),
                    "glb": out_glb, "glb_sha256": rc.sha256_file(out_glb),
                    "glb_bytes": os.path.getsize(out_glb)},
    }
    with open(os.path.join(out_dir, "bake_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    print("RIG_BAKE_OK " + json.dumps({"glb": out_glb, "atlas": atlas_path,
                                   "non_black": round(health["non_black_fraction"], 4),
                                   "seconds": round(secs, 1)}))


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

        from armature_core.errors import ArmatureError, GateFailure
        traceback.print_exc()
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _detail = getattr(exc, "evidence", None)
        _sentinel = {
            "tool": "rig_bake",
            "outcome": ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                        else "REFUSED — the tool declined to proceed"
                        if isinstance(exc, ArmatureError)
                        else "FAILED — an unhandled error"),
            "gate": getattr(exc, "gate", None),
            "error": type(exc).__name__, "message": str(exc),
            "evidence": _halt_keysafe(_detail) if isinstance(_detail, dict) else None}
        try:
            _a = parse_args()
            _d = os.path.abspath(_a["out"])
            os.makedirs(_d, exist_ok=True)
            with open(os.path.join(_d, "halt.json"), "w", encoding="utf-8") as fh:
                json.dump(dict(_sentinel, traceback=traceback.format_exc()), fh,
                          indent=2, default=str)
        except BaseException:                                         # noqa: BLE001
            # The halt record is a courtesy; the sentinel and the exit code are the contract.
            traceback.print_exc()
        finally:
            # The sentinel line may not be deleted by a failure to serialise the sentinel:
            # a `TypeError` raised HERE would leave the `finally` before `sys.exit`. The
            # fallback carries only values that are already strings.
            try:
                _line = json.dumps(_sentinel, default=str)
            except BaseException:                                     # noqa: BLE001
                _line = json.dumps({
                    "tool": _sentinel["tool"], "outcome": _sentinel["outcome"],
                    "gate": None, "error": _sentinel["error"],
                    "message": _sentinel["message"], "evidence": None})
            print("RIG_BAKE_HALT " + _line)
            sys.exit(_code)
