"""make_skeleton_sheet — the Director's skeleton-approval sheet.

    blender -b --factory-startup -P tools\\make_skeleton_sheet.py -- --glb=<subject.glb> --out=<dir>
    <venv-python> tools\\sheet_compose.py <dir>\\panels.json

Built for the judgement it exists to serve: **is every pivot on its sculpted ball?** The
Director caught the first skeleton at 1:1 — he saw it was not lined up properly —
so the joint insets are framed on the **ball centre**, identical camera before and after, and
rendered at native size so the two rows are the same zoom he was looking at.

Every camera is orthographic and every panel in a row shares one `ortho_scale`, so panel
scale is uniform by construction rather than by care. Rendered from the terracotta body with
material and light; the skeleton is a second pass composited over it, so a pivot can be seen
*inside* him rather than only where it breaks the silhouette.

No gate state is printed on this sheet, and no debug text.
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import json  # noqa: E402
from mathutils import Vector  # noqa: E402

import rig_character  # noqa: E402
from armature_core import joints, landmarks, sitelist  # noqa: E402
from armature_core import blender_scene  # noqa: E402
from armature_core.errors import GateFailure  # noqa: E402

FULL_W, FULL_H = 900, 1360
INSET = 620

#: Half the inset's world width, as a fraction of the figure's own height. Sized so the
#: LARGEST before-offset still lands inside the frame: the elbow pivot sat 0.074 from its
#: ball, and at the first zoom tried (0.115) it fell outside the panel entirely — the before
#: row showed a bone tube and no pivot at all, which reads as a missing render rather than
#: as the error it is. The comparison is only worth looking at if the miss is in shot.
INSET_HEIGHT_FRACTION = 0.20

BEFORE_RGB = (1.00, 0.42, 0.16)   # the heuristic placement
AFTER_RGB = (0.10, 0.85, 1.00)    # the placement measured off the sculpted balls

#: The six joints the insets show, in body order. One side only — the panels are already
#: six wide, and the offset table in the report carries both sides.
INSET_JOINTS = ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")


#: The engine identifiers this tool will accept, in the order it tries them. One order
#: across `make_skeleton_sheet`, `make_binding_sheet`, `make_parts_sheet` and
#: `preview_glb` -- `preview_glb` used to try them the other way round.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")


class SkeletonSheetGate(GateFailure):
    """The approval sheet cannot be composed as an approval sheet."""

    gate = "SKELETON_SHEET"


def snap_census(table):
    """(n_matched, n_snappable) over `joints.snap_sites_to_balls`' table."""
    return sum(1 for r in table.values() if r.get("matched")), len(table)


def gate_any_pivot_matched(table):
    """ANDON - at least one limb pivot moved onto a sculpted ball.

    When NOTHING matched, every inset's Before and After panel is the same picture and the
    sheet is six identical pairs under a caption about pivots being moved: the most
    reassuring possible appearance for a total failure of the measurement this sheet
    exists to show. That is not an approval artifact, so it is refused rather than
    rendered. Raises; no `assert`, no skip flag.
    """
    n_matched, n_snappable = snap_census(table)
    ev = {"gate": "SKELETON_SHEET", "n_matched": n_matched, "n_snappable": n_snappable,
          "unmatched": sorted(k for k, r in table.items() if not r.get("matched"))}
    if n_snappable and n_matched == 0:
        raise SkeletonSheetGate(
            f"no ball was matched for any of the {n_snappable} snappable sites, so every "
            f"inset's Before and After panel is the SAME picture. A sheet of identical "
            f"pairs reads as 'these pivots were already correct', which is the opposite "
            f"of what happened", ev)
    return ev


def inset_panel_label(joint, site, table):
    """The panel's label, which says when its two rows are the same picture."""
    if table.get(site, {}).get("matched"):
        return joint
    return f"{joint} - NO BALL MATCHED, heuristic placement"


def inset_record(joint, site, table, *, body, before, after):
    """One inset's entry, carrying `matched` and the unmatched reason into panels.json.

    The sheet used to read only `after` and the offset fraction, so `matched` and `reason`
    never reached the emitted spec and an unmatched joint was indistinguishable from a
    joint that had needed no correction.
    """
    rec = table.get(site, {})
    out = {"body": body, "before": before, "after": after,
           "site": site,
           "matched": bool(rec.get("matched")),
           "label": inset_panel_label(joint, site, table),
           "offset_frac": rec.get("offset_as_fraction_of_segment")}
    if not out["matched"] and rec.get("reason"):
        out["reason"] = rec["reason"]
    return out


def sheet_subtitle(table, side):
    """The subtitle, built from the run's own measurements rather than typed out.

    MEASURED 2026-09-04: the superseded literal read "22 named bones - every limb pivot
    moved onto the mannequin's own sculpted ball-joint". The count was correct on this
    sitelist and is latent drift; the second clause was an unconditional assertion about a
    measurement that reports per-site whether it succeeded.
    """
    n_matched, n_snappable = snap_census(table)
    return (f"{len(sitelist.BONES)} named bones · {n_matched} of {n_snappable} limb "
            f"pivots moved onto the mannequin's own sculpted ball-joint · insets are "
            f"1:1, character's {side} side, same camera in both rows")


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bands", type=int, default=200)
    return p.parse_args(argv)


def emission(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*rgb, 1.0)
    em.inputs[1].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])
    return mat


def overlay_from_marks(marks, height, rgb, tag):
    """Bone tubes and pivot balls straight from a landmark dict — no armature needed.

    Built from the landmarks rather than from a Blender armature so the *before* skeleton
    can be drawn without building a second rig, and so the two rows differ in exactly one
    thing: where the pivots are.
    """
    mat = emission(f"ov_{tag}", rgb)
    r_bone, r_pivot = 0.0035 * height, 0.0135 * height
    made = []
    for b in sitelist.BONES:
        head, tail = Vector(marks[b.head]), Vector(marks[b.tail])
        d = tail - head
        if d.length > 0:
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r_bone, depth=d.length,
                                                location=head + d / 2.0)
            ob = bpy.context.active_object
            ob.name = f"ov_{tag}_bone_{b.name}"
            ob.rotation_mode = "QUATERNION"
            ob.rotation_quaternion = d.to_track_quat("Z", "Y")
            ob.data.materials.append(mat)
            made.append(ob)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=18, ring_count=10, radius=r_pivot,
                                             location=head)
        j = bpy.context.active_object
        j.name = f"ov_{tag}_pivot_{b.name}"
        j.data.materials.append(mat)
        made.append(j)
    for ob in made:
        ob.hide_render = True
    return made


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
        raise SkeletonSheetGate(
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


def ortho_camera(scene, name, target, azim_deg, ortho_scale, res):
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


def shoot(scene, path, transparent):
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
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
        raise SkeletonSheetGate(
            f"the render operator returned without writing "
            f"{os.path.basename(path)}; the panel does not exist or is zero bytes, and "
            f"the sheet would name a file that is not there",
            {"path": os.path.abspath(path),
             "exists": os.path.isfile(path),
             "bytes": os.path.getsize(path) if os.path.isfile(path) else None})
    return path


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    frames = os.path.join(out, "frames")

    scene = rig_character.fresh_scene(rig_character.PROBE_FPS)
    bpy.ops.import_scene.gltf(filepath=args.glb)
    # FAMILY of F-cb986eb3 / F-e911313d: `[...][0]` over the object table. Which
    # object index 0 is depends on file order, and the glTF importer routinely adds a
    # second mesh -- the `glTF_not_exported` Icosphere, which make_rig_sheet's own
    # comment records picking once. Selection is render visibility and an ambiguous
    # result RAISES, the shape rig_character.build_pass and rig_bake._import use.
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1:
        raise SkeletonSheetGate(
            f"{args.glb} presents {len(visible)} render-visible mesh object(s); the sheet "
            f"cannot decide which one is the character",
            {"gate": "SKELETON_SHEET", "glb": args.glb,
             "render_visible": [o.name for o in visible],
             "all_meshes": [o.name for o in meshes]})
    mesh_obj = visible[0]

    source = rig_character.world_verts(mesh_obj)
    lo, hi = source.min(axis=0), source.max(axis=0)
    height = float(hi[2] - lo[2])
    diagonal = float(((hi - lo) ** 2).sum() ** 0.5)
    centre = Vector(((lo + hi) / 2.0).tolist())

    lm = landmarks.derive(source, n_bands=args.bands)
    before_marks = dict(lm["landmarks"])
    balls, _ = rig_character.measure_joint_balls(mesh_obj, diagonal)
    after_marks, table = joints.snap_sites_to_balls(lm, balls)

    engine = light_the_scene(scene)
    # F-244b2ad5: the subject-ambiguity `raise` above and `light_the_scene` (which raises
    # through a helper) both fire before any pixel exists. The directory is created HERE so
    # a halt does not leave an empty one behind — this is the sheet the Director approves
    # the skeleton on, and an empty `frames/` beside no sheet is the most misreadable
    # residue of the eleven. Corrected shape carried from `render_performer.py:319`.
    os.makedirs(frames, exist_ok=True)

    ov_before = overlay_from_marks(before_marks, height, BEFORE_RGB, "before")
    ov_after = overlay_from_marks(after_marks, height, AFTER_RGB, "after")

    def render(tag, target, azim, oscale, res, overlay):
        ortho_camera(scene, f"cam_{tag}", target, azim, oscale, res)
        for ob in ov_before + ov_after:
            ob.hide_render = True
        mesh_obj.hide_render = False
        body = shoot(scene, os.path.join(frames, f"{tag}_body.png"), False)
        if overlay is None:
            return body, None
        mesh_obj.hide_render = True
        for ob in overlay:
            ob.hide_render = False
        bones = shoot(scene, os.path.join(frames, f"{tag}_bones.png"), True)
        mesh_obj.hide_render = False
        return body, bones

    full_scale = height * 1.10
    full = {tag: render(tag, centre, azim, full_scale, (FULL_W, FULL_H), ov_after)
            for tag, azim in (("front", 0.0), ("side", 90.0))}

    # Insets framed on the BALL CENTRE, so the camera is identical before and after and the
    # only thing that moves between the two rows is the pivot.
    side = "L" if lm["facing"]["left_x_sign"] > 0 else "R"
    inset_scale = height * INSET_HEIGHT_FRACTION
    gate_snap = gate_any_pivot_matched(table)
    insets = {}
    for joint in INSET_JOINTS:
        site = f"{joint}_{side}"
        target = Vector(table[site]["after"])
        body_b, bones_b = render(f"inset_{joint}_before", target, 0.0, inset_scale,
                                 (INSET, INSET), ov_before)
        _, bones_a = render(f"inset_{joint}_after", target, 0.0, inset_scale,
                            (INSET, INSET), ov_after)
        insets[joint] = inset_record(joint, site, table, body=body_b, before=bones_b,
                                     after=bones_a)

    spec = {
        "tool": "make_skeleton_sheet",
        "blender": blender_scene.blender_provenance(),
        "engine": engine,
        "out": out,
        "filename": "E07-skeleton-approval.png",
        "title": "E07 — the skeleton, for approval",
        "subtitle": sheet_subtitle(table, side),
        "gate_SKELETON_SHEET": gate_snap,
        "joint_snap_table": {f"{j}_{side}": table[f"{j}_{side}"] for j in INSET_JOINTS},
        "rows": [
            {"title": "The figure, with the skeleton in place",
             "panels": [{"body": full["front"][0], "overlay": full["front"][1],
                         "label": "front"},
                        {"body": full["side"][0], "overlay": full["side"][1],
                         "label": "side"}]},
            {"title": "Before — pivots placed by proportion",
             "panels": [{"body": insets[j]["body"], "overlay": insets[j]["before"],
                         "label": insets[j]["label"]} for j in INSET_JOINTS]},
            {"title": "After — pivots placed on the sculpted ball",
             "panels": [{"body": insets[j]["body"], "overlay": insets[j]["after"],
                         "label": insets[j]["label"]} for j in INSET_JOINTS]},
        ],
    }
    path = os.path.join(out, "panels.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print("MAKE_SKELETON_SHEET_OK " + path)


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
        traceback.print_exc()
        _detail = getattr(exc, "evidence", None)
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _sentinel = {
            "tool": "make_skeleton_sheet",
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
            print("MAKE_SKELETON_SHEET_HALT " + _line)
            sys.exit(_code)
