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
    # THE WRITER VERIFIES ITS OWN OUTPUT (F-51c5e0ef). `bpy.ops.render.render` returns
    # an operator status set and can return `{'CANCELLED'}` WITHOUT raising; this
    # function discarded it, and no code path in this tool ever opened a rendered file
    # again -- so `panels.json` was a manifest of paths that may not exist, printed
    # under a success sentinel, and a stale file left at the path by an earlier run put
    # the previous run's panel into the sheet the Director is asked to approve. The
    # shape is `preview_walk.py:196-206`'s, carried here rather than reinvented.
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise PartsSheetGate(
            f"the render operator returned without writing "
            f"{os.path.basename(path)}; the panel does not exist or is zero bytes, and "
            f"the sheet would name a file that is not there",
            {"path": os.path.abspath(path),
             "exists": os.path.isfile(path),
             "bytes": os.path.getsize(path) if os.path.isfile(path) else None})
    return path


def corner_bounds(objs):
    """(lo, hi) corners over the objects' UNEVALUATED mesh vertices, in world space.

    Renamed from `world_bounds` 2026-09-04 (F-328aaea2): it shadowed
    `blender_scene.world_bounds`, which returns a (center, half_extent, radius) triple
    over EVALUATED geometry and filters by render visibility when it is given the scene.
    Two different measurements under one name is how a visibility obligation gets lost.
    """
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
    lo, hi = corner_bounds(visible)
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

    # F-244b2ad5: five refusals sit above this line — three inline `raise`s plus
    # `light_the_scene` and `articulated_side`, which raise through helpers — and none of
    # them needs a directory. It is created HERE so a halt leaves nothing behind. Corrected
    # shape carried from `render_performer.py:319`; the wave-10 census could not see any of
    # the five because it recognised a refusal by the callee's NAME.
    os.makedirs(frames_dir, exist_ok=True)

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
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback

        from armature_core.errors import ArmatureError, GateFailure
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
            "tool": "make_parts_sheet", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "make_parts_sheet", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("MAKE_PARTS_SHEET_HALT " + _line)
            sys.exit(_code)
