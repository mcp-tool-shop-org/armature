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

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is writing the rendered panels under `--out/frames` and
one `panels.json` under `--out` -- the sheet the Director approves the skeleton at.
Compensator: delete `--out`; owner: the executor session. Every path it writes is
composed from `--out` and a fixed literal, so no operator-supplied name component can
carry a panel outside the directory the compensator names. The GLB is opened
read-only.

Named because CLAUDE.md's workflow standard 3 (NAMED_COMPENSATORS -- Sagas,
Garcia-Molina & Salem, SIGMOD 1987) takes NO skip, and because the ordering makes the
question ordinary rather than exotic: `_census_nodes.refusal_and_write_lines`, run over
the 21 Blender-side tools, finds 15 modules with at least one refusal BELOW the first
write, so a halt after the first write is the common case (F-6e1a9d54, wave 25).
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
from render_performer import maybe_compose_panels  # noqa: E402
from make_parts_sheet import CLAY_STUDIO_LINEAR  # noqa: E402

FULL_W, FULL_H = 900, 1360
INSET = 620

#: Half the inset's world width, as a fraction of the figure's own height. Sized so the
#: LARGEST before-offset still lands inside the frame: the elbow pivot sat 0.074 from its
#: ball, and at the first zoom tried (0.115) it fell outside the panel entirely — the before
#: row showed a bone tube and no pivot at all, which reads as a missing render rather than
#: as the error it is. The comparison is only worth looking at if the miss is in shot.
INSET_HEIGHT_FRACTION = 0.20

#: Cool magenta — separates from terracotta (F-02ab94ad). Warm orange was same-hue as the body.
BEFORE_RGB = (0.95, 0.20, 0.90)
AFTER_RGB = (0.10, 0.85, 1.00)    # the placement measured off the sculpted balls
#: On-sheet unmatched caption stays short (F-3aec0c43); long reason rides panels.json.
UNMATCHED_LABEL_SUFFIX = "— NO MATCH"
UNMATCHED_DETAIL = "NO BALL MATCHED, heuristic placement"

#: The six joints the insets show, in body order. One side only — the panels are already
#: six wide, and the offset table in the report carries both sides.
INSET_JOINTS = ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")


#: The engine identifiers this tool will accept, in the order it tries them. One order
#: across `make_skeleton_sheet`, `make_binding_sheet`, `make_parts_sheet` and
#: `preview_glb` -- `preview_glb` used to try them the other way round.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")


def _render_status(result):
    """The render operator's status set as a sorted list of strings, `[]` if unreadable.

    WAVE 14, F-6a9a0f72. `bpy.ops.render.render(write_still=True)` returns an operator
    STATUS SET and can return `{'CANCELLED'}` without raising -- the premise this repo
    recorded in wave 12 and then read at none of its 14 render call sites. Every check
    those call sites have downstream (`os.path.isfile`, `getsize`, a re-read of the pixels)
    is a property a PREVIOUS run's file at the same path satisfies, so the operator's own
    verdict is the only clause that distinguishes "this call drew nothing" from "an older
    file is sitting where this call's output was supposed to land". An unreadable return is
    `[]`, which FAILS the `'FINISHED' in ...` clause rather than passing it.

    It is spelled once per tool rather than imported, because these modules share no
    parent inside `tools/` -- `armature_core` is where one implementation belongs and it is
    outside this domain's globs (FILED, see the wave-14 report). The census in
    `tests/test_instruments_amend_w14.py` asserts every copy is byte-identical, so the
    duplication cannot drift.
    """
    try:
        return sorted(str(s) for s in result)
    except TypeError:
        return []


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
    """The panel's on-sheet caption — short when unmatched (F-3aec0c43)."""
    if table.get(site, {}).get("matched"):
        return joint
    return f"{joint} {UNMATCHED_LABEL_SUFFIX}"


def inset_record(joint, site, table, *, body, before, after):
    """One inset's entry, carrying `matched` and the unmatched reason into panels.json.

    The sheet used to read only `after` and the offset fraction, so `matched` and `reason`
    never reached the emitted spec and an unmatched joint was indistinguishable from a
    joint that had needed no correction. The long unmatched spelling lives here as
    `unmatched_detail`, not in the on-sheet caption (F-3aec0c43).
    """
    rec = table.get(site, {})
    out = {"body": body, "before": before, "after": after,
           "site": site,
           "matched": bool(rec.get("matched")),
           "label": inset_panel_label(joint, site, table),
           "offset_frac": rec.get("offset_as_fraction_of_segment")}
    if not out["matched"]:
        out["unmatched_detail"] = UNMATCHED_DETAIL
        if rec.get("reason"):
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


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/make_skeleton_sheet.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--glb", required=True,
                   help="the skeleton GLB the Director is approving -- the insets are "
                        "framed on its BALL CENTRES, before and after, same camera. "
                        "Read only")
    p.add_argument("--out", required=True,
                   help="the directory panels.json and its panels are written into; "
                        "`sheet_compose.py <out>/panels.json` composes the sheet. "
                        "Compensator: delete it; owner: the executor session")
    p.add_argument("--bands", type=int, default=200,
                   help="horizontal bands the silhouette is read in to place the pivots "
                        "(default 200); the same number make_skeleton_sheet's own "
                        "landmark derivation is bounded by")
    p.add_argument("--compose", dest="compose", action="store_true", default=True,
                   help="after panels.json is valid, spawn sheet_compose (default; F-938485d6)")
    p.add_argument("--no-compose", dest="compose", action="store_false",
                   help="stop after panels.json; operator runs sheet_compose by hand")
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
            {"clause": "no_valid_render_engine",
             "candidates": list(ENGINE_CANDIDATES),
             "blender": bpy.app.version_string})
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*CLAY_STUDIO_LINEAR, 1.0)
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
    # WAVE 25, F-c05e8b32 (ground F-4925f60f, moved) -- THE PRE-RENDER SNAPSHOT, at the
    # sheet tools the wave-22 enumeration dropped. Wave 22 added
    # `rig_character.render_target_snapshot` / `require_render_target_moved` and adopted
    # them at the FIVE renderers; the wave-21 re-sighting's list of render write sites
    # stopped before the three sheets. Re-counted in this worktree:
    # `scene.render.filepath` assignments / snapshots / moved-checks per owned module --
    # preview_glb 2/3/1, preview_walk 1/2/2, render_performer 2/3/3,
    # render_start_frame 6/7/7, render_turnaround 2/2/2, and make_binding_sheet 1/0/0,
    # make_parts_sheet 1/0/0, make_skeleton_sheet 1/0/0.
    #
    # The comment below states the premise itself -- the existence and size clauses are
    # properties a PREVIOUS run's file at the same path satisfies -- and no clause
    # measured the target before the write, on the artefact the Director approves the
    # skeleton at. Consequence stays bounded as the ground row framed it: no realistic
    # FINISHED-without-write was constructed on this rig. The home is ADOPTED, not
    # respelled.
    _before = rig_character.render_target_snapshot(path)
    scene.render.filepath = path
    render_result = bpy.ops.render.render(write_still=True)
    # WAVE 14, F-6a9a0f72: the render operator's STATUS SET, read. The existence and
    # size checks below are properties a PREVIOUS run's file at the same path satisfies;
    # only the operator's own verdict says whether THIS call drew anything. Shape carried
    # from `rig_bake.py`'s `if 'FINISHED' not in result`.
    _status = _render_status(render_result)
    if "FINISHED" not in _status:
        raise SkeletonSheetGate(
            f"the render operator did not report FINISHED for "
            f"{os.path.basename(path)}; it returned {_status!r}, and any file at "
            f"that path is then the previous run's",
            {"clause": "operator_status", "status": _status,
             "path": os.path.abspath(path),
             # F-d6042cf6: where the partial run is, and its named undo.
             "out": os.path.dirname(os.path.abspath(path)),
             "compensator": "delete --out; owner: the executor session"})
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
            {"clause": "render_wrote_nothing", "path": os.path.abspath(path),
             "exists": os.path.isfile(path),
             "bytes": os.path.getsize(path) if os.path.isfile(path) else None})
    rig_character.require_render_target_moved(
        path, _before, SkeletonSheetGate,
        {"gate": SkeletonSheetGate.gate, "sub_gate": "RENDER_TARGET",
         "who": "make_skeleton_sheet"},
        what="the sheet panel")
    return path


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    frames = os.path.join(out, "frames")

    scene = rig_character.fresh_scene(rig_character.PROBE_FPS)
    _import = bpy.ops.import_scene.gltf(filepath=args.glb)
    rig_character.require_import_status(_import, args.glb, SkeletonSheetGate,
                                       {"who": "make_skeleton_sheet"})
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
            {"clause": "subject_is_not_one_render_visible_mesh",
             "gate": "SKELETON_SHEET", "glb": args.glb,
             "render_visible": [o.name for o in visible],
             "all_meshes": [o.name for o in meshes]})
    mesh_obj = visible[0]

    source = rig_character.world_verts(mesh_obj)
    # SIBLING CARRIED under F-6a9a0f72 (wave 14). Gate SCALE: `measure_joint_balls` DIVIDES
    # by this diagonal, and this is the sheet the Director approves the skeleton on.
    diagonal, lo, hi = rig_character.subject_scale(source, "make_skeleton_sheet")
    height = float(hi[2] - lo[2])
    centre = Vector(((lo + hi) / 2.0).tolist())

    lm = landmarks.derive(source, n_bands=args.bands)
    before_marks = dict(lm["landmarks"])
    balls, _ = rig_character.measure_joint_balls(mesh_obj, diagonal)
    after_marks, table = joints.snap_sites_to_balls(lm, balls)
    # THE ANDON, MOVED (F-a74b69c9, wave 14). It used to sit 36 lines below, after
    # `os.makedirs(frames)` and after four body/bones panels had been shot into it -- and
    # nothing in it reads anything those four renders wrote. Its only input is `table`,
    # produced on the line above. What a refused run left behind was `frames/` holding four
    # panels and no sheet, which reads as an interrupted render rather than as a refusal
    # and is MORE misreadable than the empty directory the comment below was written
    # against. The whole purpose of this andon is that a subject where no ball matched any
    # pivot must not produce something that looks like an approval artifact.
    gate_snap = gate_any_pivot_matched(table)

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
    # WAVE 25, F-f204a6d1 -- THE SUCCESS SENTINEL SAYS WHAT THE RUN MEASURED.
    # This line was `print("MAKE_SKELETON_SHEET_OK " + path)`: the only `_OK` line in
    # the 21 owned tools whose payload a JSON reader cannot parse (an AST walk finds 22
    # `_OK` prints in 20 modules building their payload with `json.dumps`, and exactly
    # this one that did not), so a wrapper reading BOTH halves of the halt contract
    # needed two parsers -- the HALT line is strict JSON everywhere.
    #
    # It was also earned by reaching the end of `main` rather than by a measurable
    # effect (the wave-12 rule, and the shape F-7e7703cb already closed for
    # `diagnose_bone_heat`): `gate_snap` and the whole `joint_snap_table` are computed
    # above and none of it reached the line, so a run in which every joint snapped and a
    # run assembled from a degenerate table read identically to a wrapper. The counts
    # are the sheet's own summary, from the same objects the record carries.
    compose_rec = maybe_compose_panels(path, compose=bool(getattr(args, "compose", True)))
    print("MAKE_SKELETON_SHEET_OK " + json.dumps({
        "tool": "make_skeleton_sheet",
        "json": path,
        "sheet": compose_rec.get("sheet"),
        "compose": compose_rec,
        "gate_SKELETON_SHEET": {"n_matched": gate_snap["n_matched"],
                                "n_snappable": gate_snap["n_snappable"],
                                "unmatched": gate_snap["unmatched"]},
        "n_inset_joints": len(INSET_JOINTS),
        # The quantity `gate_any_pivot_matched(table)` above actually rules on, so the
        # count this line reports and the count the gate refused over are the same
        # object (`test_instruments_amend_w10`'s counting-success census asks exactly
        # that: a refusal above the success line on the emptiness of what is counted).
        "n_snap_sites": len(table),
        "panels": sum(len(r["panels"]) for r in spec["rows"]),
        "side": side,
    }))


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
    # WAVE 22, F-897a3329: the VALUE clause, beside the key clause this walk was written
    # for. `json.dumps`'s `default=` applies to values Python cannot encode, never to a
    # float it CAN, and `allow_nan` defaults True -- so a non-finite operand that
    # `armature_core.parts.require_finite` wrote into the evidence (`ev[name] = v`)
    # reached the halt line as the bare token `NaN`. MEASURED end-to-end on `e8263a3`:
    # a sentinel of that shape serialises to `{"evidence": {"max_displacement": NaN}}`;
    # `json.loads(payload)` ACCEPTS it -- which is why every reader in this suite was
    # green -- and `json.loads(payload, parse_constant=<raise>)` REJECTS it naming the
    # constant, as would JS `JSON.parse`, Go `encoding/json` and serde. The halt contract
    # promises "stdout EXACTLY ONE line `<STEM>_HALT <json object>`", and for exactly the
    # refusal family wave 16 added -- the NaN andons -- the object was not JSON.
    #
    # The operand stays READABLE: `repr` gives "nan" / "inf" / "-inf", which is the same
    # text `require_finite`'s own message carries, rather than a null that erases which
    # non-finite value it was. `json.dumps(..., allow_nan=False)` below then cannot raise,
    # so the guard around the sentinel keeps its meaning.
    if isinstance(value, float) and (value != value
                                     or value in (float("inf"), float("-inf"))):
        return repr(value)
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
            "tool": "make_skeleton_sheet", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "make_skeleton_sheet", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            # `allow_nan=False` (F-897a3329): strict JSON, and it cannot raise here because
            # `_halt_keysafe` above has already replaced every non-finite float with its repr.
            _line = json.dumps(_sentinel, default=str, allow_nan=False)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("MAKE_SKELETON_SHEET_HALT " + _line)
            sys.exit(_code)
