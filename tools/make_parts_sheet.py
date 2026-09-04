"""make_parts_sheet — the dailies sheet for E07 arm (c), the rigid-parts armature.

    blender -b --factory-startup -P tools\\make_parts_sheet.py -- --glb=<parts.glb> --out=<dir>
    <venv-python> tools\\sheet_compose.py <dir>\\panels.json

`rest | frame 17 | frame 33 | 1:1 insets on the joints UNDER ARTICULATION`. The joint seam
read is what the Director rules on, so the insets are framed on the **posed bone position at
the last frame** — where the collar overlap is doing its work — rather than on the rest pose
where every seam is closed by definition.

Rendered from the terracotta body with material and light. No overlay: a bone drawn over the
surface would hide the exact thing being judged. No gate states, no debug text.

**The arc is checked, not assumed.** A re-imported GLB whose parts sit still at frame 33 would
produce a sheet of matching panels reading as "this route does not move", when the truth would
be that the animation did not survive the round trip. It raises instead.
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

FULL_W, FULL_H = 820, 1240
INSET = 620
INSET_HEIGHT_FRACTION = 0.20
ARC_FRAMES = (17, rig_character.PROBE_FRAMES)
#: The joints the Director rules on, in the order he reads them. `(panel label, joint)` --
#: the SIDE is appended at run time from `articulated_side`, never pinned here.
INSET_JOINTS = (("shoulder", "shoulder"), ("elbow", "elbow"),
                ("wrist", "wrist"), ("hip", "hip"))

#: The joints whose displacement decides which arm the arc moved. The hip is excluded: the
#: probe arc rotates a shoulder, so a hip on either side stays put and would only dilute
#: the measurement.
SIDE_PROBE_JOINTS = ("shoulder", "elbow", "wrist")


def side_word(side):
    """"L" -> "LEFT". The word a caption prints, from the side the run measured."""
    return {"L": "LEFT", "R": "RIGHT"}[side]


def articulated_side(arm_obj, scene, rest_frame, posed_frame,
                     joints=SIDE_PROBE_JOINTS):
    """Which arm the authored arc actually moves, MEASURED on this rig.

    THE ONE IMPLEMENTATION. `make_binding_sheet` and `make_rig_sheet` import it from here,
    the way they already import `light_the_scene` / `ortho_camera` / `shoot`;
    `make_skeleton_sheet` derives its own side from the landmark dict it already holds.

    MEASURED 2026-09-04: these three sheets pinned `shoulder.L / elbow.L / wrist.L / hip.L`
    and captioned "the character's LEFT arm", while `rig_character.author_probe` chooses
    `shoulder.{side}` from `landmarks.facing.left_x_sign` against
    `sitelist.PROBE_ARC_SIDE_X_SIGN` -- which arm lies on +X is a property of the mesh, not
    of the letter in the generator's bone name. Nothing raised when the two disagreed,
    because each sheet's liveness andon is satisfied by the OTHER arm moving. On a subject
    whose +X arm is the right one, four 1:1 insets showed the joints that did not move.

    Returns the side and both displacements, so the record can say what it measured.
    """
    names = {side: [f"{j}.{side}" for j in joints
                    if f"{j}.{side}" in arm_obj.pose.bones]
             for side in ("L", "R")}
    if not names["L"] or not names["R"]:
        raise ArmatureError(
            f"the armature does not name both sides of {list(joints)}: "
            f"L={names['L']} R={names['R']}. Which arm the arc moves cannot be measured, "
            f"and a sheet that guessed would caption the wrong limb")

    def heads(frame):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        return {n: (arm_obj.matrix_world @ arm_obj.pose.bones[n].head).copy()
                for side in ("L", "R") for n in names[side]}

    rest, posed = heads(rest_frame), heads(posed_frame)
    disp = {side: max((posed[n] - rest[n]).length for n in names[side])
            for side in ("L", "R")}
    hi = "L" if disp["L"] >= disp["R"] else "R"
    lo = "R" if hi == "L" else "L"
    ev = {"rest_frame": rest_frame, "posed_frame": posed_frame,
          "joints": list(joints), "displacement": disp,
          "bones": {side: names[side] for side in ("L", "R")}}

    if disp[hi] <= 0.0:
        raise ArmatureError(
            f"neither arm moved between frames {rest_frame} and {posed_frame} "
            f"(L={disp['L']:.3e} R={disp['R']:.3e}); there is no articulated side for the "
            f"insets to be about. {ev}")
    # Bounded as a fraction of the WINNER'S OWN displacement, not by a metric constant: a
    # global constant must not govern a local feature.
    if disp[lo] > 0.5 * disp[hi]:
        raise ArmatureError(
            f"both arms move across the arc (L={disp['L']:.3e} R={disp['R']:.3e}); there "
            f"is no single articulated side, and picking one silently is how a caption "
            f"stops describing the picture. {ev}")
    ev["side"] = hi
    ev["side_word"] = side_word(hi)
    return ev


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title", default="E07 arm (c) — the rigid-parts armature")
    return p.parse_args(argv)


#: The engine identifiers this tool will accept, in the order it tries them. One order
#: across `make_skeleton_sheet`, `make_binding_sheet`, `make_parts_sheet` and
#: `preview_glb` -- `preview_glb` used to try them the other way round.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")


class PartsSheetGate(GateFailure):
    """The sheet cannot be composed reproducibly."""

    gate = "PARTS_SHEET"


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
        raise PartsSheetGate(
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


def world_bounds(objs):
    lo = np.array([1e18, 1e18, 1e18])
    hi = -lo.copy()
    for ob in objs:
        m = np.array(ob.matrix_world, dtype=np.float64)
        n = len(ob.data.vertices)
        flat = np.empty(n * 3, dtype=np.float64)
        ob.data.vertices.foreach_get("co", flat)
        w = flat.reshape(n, 3) @ m[:3, :3].T + m[:3, 3]
        lo = np.minimum(lo, w.min(axis=0))
        hi = np.maximum(hi, w.max(axis=0))
    return lo, hi


def all_world_verts(objs):
    return np.concatenate([
        (np.frombuffer(bytearray(len(ob.data.vertices) * 24), dtype=np.float64)
         if False else _wv(ob)) for ob in objs], axis=0)


def _wv(ob):
    n = len(ob.data.vertices)
    flat = np.empty(n * 3, dtype=np.float64)
    ob.data.vertices.foreach_get("co", flat)
    m = np.array(ob.matrix_world, dtype=np.float64)
    return flat.reshape(n, 3) @ m[:3, :3].T + m[:3, 3]


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    frames_dir = os.path.join(out, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    scene = rig_character.fresh_scene(rig_character.PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=args.glb)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if not visible:
        raise ArmatureError(f"{args.glb}: no render-visible mesh objects")
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise ArmatureError(f"{args.glb}: expected one armature, found {len(arms)}")
    arm_obj = arms[0]
    engine = light_the_scene(scene)

    scene.frame_set(1)
    bpy.context.view_layer.update()
    lo, hi = world_bounds(visible)
    height = float(hi[2] - lo[2])
    centre = Vector(((lo + hi) / 2.0).tolist())
    at_rest = all_world_verts(visible)

    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()
    moved = float(np.linalg.norm(all_world_verts(visible) - at_rest, axis=1).max())
    if moved <= 1e-6:
        raise ArmatureError(
            f"{args.glb}: the parts are identical at frame 1 and frame "
            f"{rig_character.PROBE_FRAMES}. The authored arc did not survive the round trip, "
            f"and a sheet built from this would read as 'this route does not move'")

    side_rec = articulated_side(arm_obj, scene, 1, rig_character.PROBE_FRAMES)
    side = side_rec["side"]
    targets = {label: tuple(arm_obj.matrix_world
                            @ arm_obj.pose.bones[f"{joint}.{side}"].head)
               for label, joint in INSET_JOINTS}

    full_scale = height * 1.10
    panels = {}
    for frame in (1,) + tuple(ARC_FRAMES):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        ortho_camera(scene, f"cam_f{frame}", centre, full_scale, (FULL_W, FULL_H))
        panels[f"f{frame}"] = shoot(scene, os.path.join(frames_dir, f"f{frame:02d}.png"))

    scene.frame_set(rig_character.PROBE_FRAMES)
    bpy.context.view_layer.update()
    inset_scale = height * INSET_HEIGHT_FRACTION
    for label, _ in INSET_JOINTS:
        ortho_camera(scene, f"cam_{label}", Vector(targets[label]), inset_scale,
                     (INSET, INSET))
        panels[f"inset_{label}"] = shoot(
            scene, os.path.join(frames_dir, f"inset_{label}.png"))

    last = rig_character.PROBE_FRAMES
    spec = {
        "tool": "make_parts_sheet",
        "blender": blender_scene.blender_provenance(),
        "engine": engine,
        "out": out,
        "filename": "E07-parts-armature.png",
        "title": args.title,
        "subtitle": ("17 rigid parts, bone-parented, no deformation anywhere   ·   the arc is "
                     f"E03's: the character's {side_rec['side_word']} arm, 0°→90° about "
                     f"+Y, {last} keys at 16 fps   ·   insets are 1:1 at frame {last}, on "
                     "the joints under articulation"),
        "articulated_side": side_rec,
        "rows": [
            {"title": "The figure through the arc",
             "panels": [{"body": panels["f1"], "label": "frame 1 — rest"},
                        {"body": panels[f"f{ARC_FRAMES[0]}"],
                         "label": f"frame {ARC_FRAMES[0]}"},
                        {"body": panels[f"f{ARC_FRAMES[1]}"],
                         "label": f"frame {ARC_FRAMES[1]}"}]},
            {"title": f"At 1:1, frame {last} — the joint seams under articulation",
             "panels": [{"body": panels[f"inset_{n}"], "label": n}
                        for n, _ in INSET_JOINTS]},
        ],
    }
    path = os.path.join(out, "panels.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print("MAKE_PARTS_SHEET_OK " + json.dumps({"panels": path, "max_displacement": moved,
                                     "parts_rendered": len(visible)}))


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
            "tool": "make_parts_sheet",
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
            print("MAKE_PARTS_SHEET_HALT " + _line)
            sys.exit(_code)
