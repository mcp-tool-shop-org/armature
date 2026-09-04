"""make_binding_sheet — arm (a) beside arm (b), for the Director's eye to pick the binding.

    blender -b --factory-startup -P tools\\make_binding_sheet.py -- --a=<glb> --a-label=... --b=<glb> --b-label=... --out=<dir>
    <venv-python> tools\\sheet_compose.py <dir>\\panels.json

`rest | arc frames | 1:1 joint insets`, the two bindings on adjacent rows at identical
cameras. Rendered from the terracotta body with material and light; **no skeleton overlay**,
because the judgement here is what the deform does to him, and a bone drawn over the surface
hides exactly the region being judged. No gate states are printed and no debug text.

**The insets are framed on the POSED BONE position at the last frame, read from the armature
rather than from either mesh.** Both arms carry the same authored action on the same skeleton,
so that point is identical in both — which makes the camera identical and lets a difference in
where the *body* actually ends up read as the difference it is. Framing on each arm's own mesh
would move the camera with the defect and hide it.

**The arc is checked, not assumed.** If a re-imported GLB comes back with the mesh identical at
frame 1 and frame 33, the sheet would show two matching panels and read as "this binding does
not move" when the truth is that the action did not survive the round trip. That is E03's
Ruling 9 failure with the axes swapped, so it raises here instead.
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import rig_character  # noqa: E402
from armature_core import blender_scene  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
from make_parts_sheet import articulated_side, side_word  # noqa: E402,F401

FULL_W, FULL_H = 780, 1180
INSET = 560
INSET_HEIGHT_FRACTION = 0.24
ARC_FRAMES = (17, rig_character.PROBE_FRAMES)
#: `(panel label, joint)` -- the SIDE is appended at run time from `articulated_side`,
#: never pinned here.
INSET_JOINTS = (("shoulder", "shoulder"), ("elbow", "elbow"),
                ("hand", "wrist"), ("hip", "hip"))


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--a", required=True)
    p.add_argument("--a-label", default="(a)")
    p.add_argument("--b", required=True)
    p.add_argument("--b-label", default="(b)")
    p.add_argument("--out", required=True)
    return p.parse_args(argv)


#: The engine identifiers this tool will accept, in the order it tries them. One order
#: across `make_skeleton_sheet`, `make_binding_sheet`, `make_parts_sheet` and
#: `preview_glb` -- `preview_glb` used to try them the other way round.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")


class BindingSheetGate(GateFailure):
    """The sheet cannot be composed reproducibly."""

    gate = "BINDING_SHEET"


def light_the_scene(scene):
    """Light the sheet, and RETURN the render engine actually set.

    MEASURED 2026-09-04 (F-bba38f1c): this loop had no `else`, so if a future Blender
    renamed both identifiers the `for` would complete normally, nothing would be set, and
    the sheet would render on whatever the factory settings left in place -- with no field
    in `panels.json` able to reveal it. Four copies of the loop existed and `preview_glb`
    tried the two names in the OPPOSITE order, so on a Blender where both are valid the
    preview and the sheets did not agree on which engine drew them. One order now, and the
    engine that was set is written into the record.
    """
    engine = None
    for eng in ENGINE_CANDIDATES:
        try:
            scene.render.engine = eng
        except TypeError:
            continue
        engine = eng
        break
    if engine is None:
        raise BindingSheetGate(
            "none of the candidate render engines is valid on this Blender, so the sheet "
            "would be drawn by whatever the factory settings left in place",
            {"candidates": list(ENGINE_CANDIDATES), "blender": bpy.app.version_string})
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.30, 0.30, 0.32, 1.0)
    bg.inputs[1].default_value = 1.0
    for name, energy, rot in (("key", 3.4, (52, 0, 26)), ("fill", 1.3, (62, 0, -134)),
                              ("rim", 2.1, (74, 0, 178))):
        data = bpy.data.lights.new(name, type="SUN")
        data.energy = energy
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.rotation_euler = tuple(math.radians(a) for a in rot)
    return engine


def ortho_camera(scene, name, target, ortho_scale, res, azim_deg=0.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    a = math.radians(azim_deg)
    cam.location = Vector(target) + Vector((6.0 * math.sin(a), -6.0 * math.cos(a), 0.0))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100


def shoot(scene, path):
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def load(glb):
    scene = rig_character.fresh_scene(rig_character.PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=glb)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1:
        raise ArmatureError(
            f"{glb}: {len(visible)} render-visible mesh objects {[o.name for o in visible]}; "
            f"the sheet cannot decide which one is the character")
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise ArmatureError(f"{glb}: expected one armature, found {len(arms)}")
    return scene, visible[0], arms[0]


def evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        return rig_character.world_verts(ev, me)
    finally:
        ev.to_mesh_clear()


def render_arm(glb, tag, out_dir, targets=None):
    scene, mesh_obj, arm_obj = load(glb)
    engine = light_the_scene(scene)

    source = rig_character.world_verts(mesh_obj)
    lo, hi = source.min(axis=0), source.max(axis=0)
    height = float(hi[2] - lo[2])
    centre = Vector(((lo + hi) / 2.0).tolist())

    scene.frame_set(1)
    bpy.context.view_layer.update()
    at_rest = evaluated(mesh_obj)
    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()
    at_end = evaluated(mesh_obj)
    moved = float(np.linalg.norm(at_end - at_rest, axis=1).max())
    if moved <= 1e-6:
        raise ArmatureError(
            f"{glb}: the mesh is identical at frame 1 and frame "
            f"{rig_character.PROBE_FRAMES}. The authored arc did not survive the round trip, "
            f"and a sheet built from this would show two matching panels and read as 'this "
            f"binding does not move'")

    # The posed bone positions at the last frame — identical across arms, so both rows share
    # one camera per joint. Computed from the FIRST arm and passed to the second.
    # Which arm the arc moves is MEASURED, not pinned: `rig_character.author_probe` binds
    # the probe to the +X side, and which of this character's arms that is comes out of
    # `landmarks.facing`. ONE implementation, imported from `make_parts_sheet` beside the
    # staging triple.
    side_rec = articulated_side(arm_obj, scene, 1, rig_character.PROBE_FRAMES)
    if targets is None:
        targets = {}
        for label, joint in INSET_JOINTS:
            bone = f"{joint}.{side_rec['side']}"
            targets[label] = tuple(arm_obj.matrix_world @ arm_obj.pose.bones[bone].head)

    full_scale = height * 1.10
    inset_scale = height * INSET_HEIGHT_FRACTION
    out = {"targets": targets, "max_displacement": moved,
           "articulated_side": side_rec, "panels": {}}

    for frame in (1,) + tuple(ARC_FRAMES):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        ortho_camera(scene, f"cam_{tag}_f{frame}", centre, full_scale, (FULL_W, FULL_H))
        out["panels"][f"f{frame}"] = shoot(
            scene, os.path.join(out_dir, f"{tag}_f{frame:02d}.png"))

    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()
    for label, _ in INSET_JOINTS:
        ortho_camera(scene, f"cam_{tag}_{label}", Vector(targets[label]), inset_scale,
                     (INSET, INSET))
        out["panels"][f"inset_{label}"] = shoot(
            scene, os.path.join(out_dir, f"{tag}_inset_{label}.png"))
    return out


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    frames = os.path.join(out, "frames")
    os.makedirs(frames, exist_ok=True)

    a = render_arm(args.a, "a", frames)
    b = render_arm(args.b, "b", frames, targets=a["targets"])

    last = rig_character.PROBE_FRAMES
    spec = {
        "tool": "make_binding_sheet",
        "blender": blender_scene.blender_provenance(),
        "engine": engine,
        "out": out,
        "filename": "E07-binding-comparison.png",
        "title": "E07 — the two bindings, for the Director's eye",
        "subtitle": (f"(a) {args.a_label}   ·   (b) {args.b_label}   ·   the arc is E03's: "
                     f"the character's {a['articulated_side']['side_word']} arm, "
                     f"0°→90° about +Y, {last} keys at 16 fps   ·   "
                     f"insets are 1:1 at frame {last}, identical camera in both rows"),
        "articulated_side": {"a": a["articulated_side"], "b": b["articulated_side"]},
        "rows": [
            {"title": "Rest pose — frame 1",
             "panels": [{"body": a["panels"]["f1"], "label": f"(a) {args.a_label}"},
                        {"body": b["panels"]["f1"], "label": f"(b) {args.b_label}"}]},
            {"title": f"The arc — frames {ARC_FRAMES[0]} and {ARC_FRAMES[1]}",
             "panels": [{"body": a["panels"][f"f{ARC_FRAMES[0]}"],
                         "label": f"(a) frame {ARC_FRAMES[0]}"},
                        {"body": a["panels"][f"f{ARC_FRAMES[1]}"],
                         "label": f"(a) frame {ARC_FRAMES[1]}"},
                        {"body": b["panels"][f"f{ARC_FRAMES[0]}"],
                         "label": f"(b) frame {ARC_FRAMES[0]}"},
                        {"body": b["panels"][f"f{ARC_FRAMES[1]}"],
                         "label": f"(b) frame {ARC_FRAMES[1]}"}]},
            {"title": f"(a) {args.a_label} — at 1:1, frame {last}",
             "panels": [{"body": a["panels"][f"inset_{n}"], "label": n}
                        for n, _ in INSET_JOINTS]},
            {"title": f"(b) {args.b_label} — at 1:1, frame {last}",
             "panels": [{"body": b["panels"][f"inset_{n}"], "label": n}
                        for n, _ in INSET_JOINTS]},
        ],
    }
    path = os.path.join(out, "panels.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print("MAKE_BINDING_SHEET_OK " + json.dumps(
        {"panels": path, "a_max_displacement": a["max_displacement"],
         "b_max_displacement": b["max_displacement"]}))


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

        from armature_core.errors import ArmatureError, GateFailure
        traceback.print_exc()
        _detail = getattr(exc, "evidence", None)
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _sentinel = {
            "tool": "make_binding_sheet",
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
            print("MAKE_BINDING_SHEET_HALT " + _line)
            sys.exit(_code)
