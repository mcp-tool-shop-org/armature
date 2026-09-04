"""The arm (d) comparison sheet — a SKINNED figure, judged beside the mesh it replaced.

``make_parts_sheet`` cannot serve here and its refusal was correct rather than a nuisance: it
compares **part object transforms**, which is how a rigid-parts rig moves. A skinned figure
has one object that never moves; the motion lives in evaluated vertex positions. Pointed at a
skinned GLB it reports "the parts are identical at frame 1 and frame 33" and declines to draw.
Rather than loosen that check, this tool makes the same assertion against the thing that
actually moves here.

Inset cameras are aimed from the **posed bone positions read out of the armature**, not from
guessed fractions of the figure's height. Arm (d)'s first comparison sheet framed the "mitten
hand" panel on a forearm and a shin, which is a sheet that cannot answer the question it was
built to ask.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_character as rc                                            # noqa: E402
from armature_core import blender_scene                               # noqa: E402
from armature_core.errors import ArmatureError                        # noqa: E402
from make_parts_sheet import (articulated_side, light_the_scene,      # noqa: E402
                              ortho_camera, shoot)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True, help="the skinned, animated GLB")
    p.add_argument("--reference", required=True, help="the ORIGINAL textured GLB")
    p.add_argument("--out", required=True)
    p.add_argument("--title", default="E07 arm (d) — retopologised, baked, bone-heat bound")
    p.add_argument("--after-label", default=None,
                   help="what the AFTER column actually is. Derived from the mesh when "
                        "omitted -- a hard-coded label outlived its route once already and "
                        "described a 4096 bake on a mesh that was never baked.")
    return vars(p.parse_args(argv))


def evaluated(ob, depsgraph):
    ev = ob.evaluated_get(depsgraph)
    me = ev.to_mesh()
    v = np.array([list(ob.matrix_world @ x.co) for x in me.vertices])
    ev.to_mesh_clear()
    return v


def import_reference(path, scene, skinned):
    """The ONE render-visible mesh the reference import adds.

    MEASURED 2026-09-04. The superseded line was

        ref = [o for o in bpy.data.objects if o.type == "MESH" and o is not mesh][0]

    -- the first mesh in the file that is not the skinned one, taken AFTER a second glTF
    import. This file's own comment at lines 63-67 records catching that exact selection
    once: the exported GLB carries a stray `Icosphere` and index 0 picked it. The stray
    removal above runs BEFORE this import, so it does not cover what this import adds, and
    the discriminator it uses (vertex groups plus an ARMATURE modifier) does not apply to
    an unrigged reference mesh.

    `ref.data.polygons` then supplies the triangle count in the "before -- original mesh,
    N tris, source atlas" label, and `ref` is rendered as that panel: the Director's
    texture-fidelity row could show an Icosphere beside the retopologised character under a
    count read off the Icosphere, and the sheet would read as catastrophic texture loss
    where the route is fine.

    The population is now the DIFFERENCE the import made, filtered by render visibility,
    and an ambiguous result raises -- the shape `rig_bake._import` and
    `rig_character.build_pass` already use.
    """
    before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=path)
    added = [o for o in bpy.data.objects if o.name not in before]
    meshes = [o for o in added if o.type == "MESH" and o is not skinned]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1:
        raise ArmatureError(
            f"the reference import of {path} contributed {len(visible)} render-visible "
            f"mesh object(s) {[o.name for o in visible]} (from added "
            f"{[o.name for o in added]}); exactly one is needed, and taking index 0 is how "
            f"a decoy once became the 'before' panel and its triangle count")
    return visible[0]


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    os.makedirs(out_dir, exist_ok=True)
    panel_dir = os.path.join(out_dir, "panels")
    os.makedirs(panel_dir, exist_ok=True)

    scene = rc.fresh_scene(16)
    bpy.ops.import_scene.gltf(filepath=args["glb"])
    # Pick the mesh that is actually SKINNED, not the first mesh in the file. The exported
    # GLB also contains a stray `Icosphere` with no vertex groups and no modifier; taking
    # index 0 picked that, and it of course never moves -- this tool's own liveness check
    # then reported "the arc did not survive the round trip" about an object that was never
    # in the arc. Identify by the property that matters.
    skinned = [o for o in bpy.data.objects
               if o.type == "MESH" and o.vertex_groups
               and any(m.type == "ARMATURE" for m in o.modifiers)]
    if len(skinned) != 1:
        raise ArmatureError(
            f"expected exactly one skinned mesh in {args['glb']}, found {len(skinned)}: "
            f"{[o.name for o in skinned]} (all meshes: "
            f"{[o.name for o in bpy.data.objects if o.type == 'MESH']})")
    mesh = skinned[0]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise ArmatureError(
            f"expected exactly one armature in {args['glb']}, found "
            f"{[o.name for o in arms]}; index 0 is whichever the file happened to "
            f"list first")
    arm = arms[0]
    stray = [o.name for o in bpy.data.objects if o.type == "MESH" and o is not mesh]
    for name in stray:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    dg = bpy.context.evaluated_depsgraph_get()
    scene.frame_set(1)
    dg.update()
    at_rest = evaluated(mesh, dg)
    scene.frame_set(rc.PROBE_FRAMES)
    dg.update()
    at_end = evaluated(mesh, dg)
    moved = float(np.abs(at_end - at_rest).max())
    lo, hi = at_rest.min(0), at_rest.max(0)
    diagonal = float(np.linalg.norm(hi - lo))
    if moved <= 1e-4 * diagonal:
        raise ArmatureError(
            f"{args['glb']}: the evaluated mesh is identical at frame 1 and frame "
            f"{rc.PROBE_FRAMES} "
            f"(max {moved:.3e}). The authored arc did not survive the round trip, and a "
            f"sheet built from this would read as 'this route does not move'")

    # Inset targets read from the POSED armature, so each crop lands on its own joint.
    scene.frame_set(rc.PROBE_FRAMES)
    dg.update()
    bones = {b.name: (arm.matrix_world @ b.head) for b in arm.pose.bones}
    height = hi[2] - lo[2]
    # Which arm the arc moves is MEASURED here too -- ONE implementation, imported from
    # `make_parts_sheet` beside the staging triple this file already takes from there.
    side_rec = articulated_side(arm, scene, 1, rc.PROBE_FRAMES)
    side = side_rec["side"]
    # The arc's own numbers, from the constants the probe is AUTHORED with -- carried from
    # `rig_sheet_compose`, which reads `spec["probe"]` rather than baking the frame count
    # and the rate into its subtitle (instruments-measure, F-f3fe8179). One implementation:
    # if `rig_character.PROBE_FRAMES` or `PROBE_FPS` moves, every caption moves with it.
    probe = {"frames": rc.PROBE_FRAMES, "fps": rc.PROBE_FPS,
             "start_deg": rc.PROBE_START_DEG, "end_deg": rc.PROBE_END_DEG,
             "arc": rc.PROBE_ARC,
             "which_arm_is_on_plus_x": side_rec["side_word"],
             "bone": f"shoulder.{side}"}
    scene.frame_set(rc.PROBE_FRAMES)
    dg.update()
    insets = [("shoulder", bones[f"shoulder.{side}"], height * 0.20, 0.0),
              ("elbow", bones[f"elbow.{side}"], height * 0.16, 0.0),
              ("wrist", bones[f"wrist.{side}"], height * 0.16, 0.0),
              ("hip", bones[f"hip.{side}"], height * 0.20, 0.0)]

    light_the_scene(scene)
    centre = Vector((0.5 * (lo[0] + hi[0]), 0.0, lo[2] + 0.5 * height))
    rows = []

    figure = []
    for frame in (1, 1 + rc.PROBE_FRAMES // 2, rc.PROBE_FRAMES):
        scene.frame_set(frame)
        ortho_camera(scene, f"cam_f{frame}", centre, height * 1.10, (700, 1120))
        figure.append({"body": shoot(scene, os.path.join(panel_dir, f"figure_{frame}.png")),
                       "label": "frame 1 — rest" if frame == 1 else f"frame {frame}"})
    rows.append({"title": "The figure through the arc", "panels": figure})

    scene.frame_set(rc.PROBE_FRAMES)
    close = []
    for label, target, oscale, azim in insets:
        ortho_camera(scene, f"cam_{label}", Vector(target), oscale, (700, 700), azim)
        close.append({"body": shoot(scene, os.path.join(panel_dir, f"{label}.png")),
                      "label": label})
    rows.append({"title": f"At 1:1, frame {rc.PROBE_FRAMES} — the joints under "
                          f"articulation", "panels": close})

    # ---- texture fidelity: the mesh that was replaced, and the one that replaced it -------
    scene.frame_set(1)
    # The loop that used to sit here iterated every object and did nothing -- its whole
    # body was `if ob.type == "ARMATURE": continue`. An abandoned cleanup; removed rather
    # than completed, because the two objects this row compares are exactly the skinned
    # mesh and the reference, and a cleanup here would have had to spare both.
    ref = import_reference(args["reference"], scene, mesh)
    ref.hide_render = True
    fidelity = []
    after_label = args["after_label"] or (
        f"after — {len(mesh.data.polygons):,} faces, {len(mesh.data.vertices):,} verts")
    before_label = (f"before — original mesh, {len(ref.data.polygons):,} tris, "
                    f"source atlas")
    for label, shown in ((before_label, ref), (after_label, mesh)):
        ref.hide_render = shown is not ref
        mesh.hide_render = shown is not mesh
        ortho_camera(scene, f"cam_fid_{shown.name}", centre, height * 1.10, (700, 1120))
        fidelity.append({"body": shoot(scene, os.path.join(
            panel_dir, f"fidelity_{'before' if shown is ref else 'after'}.png")),
            "label": label})
        for label2, target, oscale, _ in insets[:1]:
            ortho_camera(scene, f"cam_fid_{shown.name}_{label2}", Vector(target),
                         height * 0.22, (700, 700))
            fidelity.append({"body": shoot(scene, os.path.join(
                panel_dir,
                f"fidelity_{'before' if shown is ref else 'after'}_{label2}.png")),
                "label": f"{label2}, same camera"})
    ref.hide_render = False
    mesh.hide_render = False
    rows.append({"title": "Texture fidelity — at rest, same camera, nothing else changed",
                 "panels": fidelity})

    spec = {"tool": "make_rig_sheet",
            "blender": blender_scene.blender_provenance(),
            "title": args["title"],
            "subtitle": (f"one skinned mesh, {len(mesh.data.vertices):,} verts, "
                         f"{len(mesh.data.polygons):,} faces, bone-heat weights normalised "
                         f"to 1.0 · the arc is E03's: the character's "
                         f"{probe['which_arm_is_on_plus_x']} arm, "
                         f"{probe['start_deg']:g}°→{probe['end_deg']:g}° "
                         f"about +Y, {probe['frames']} keys at {probe['fps']} fps"),
            "articulated_side": side_rec,
            "probe": probe,
            "out": out_dir, "filename": "E07-rig-armature.png", "rows": rows}
    with open(os.path.join(out_dir, "panels.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print("MAKE_RIG_SHEET_OK " + json.dumps({"max_vertex_motion": moved, "rows": len(rows),
                                     "stray_meshes_removed": stray}))


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
        print("MAKE_RIG_SHEET_HALT " + json.dumps({
            "tool": "make_rig_sheet",
            "outcome": ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                        else "REFUSED — the tool declined to proceed"
                        if isinstance(exc, ArmatureError)
                        else "FAILED — an unhandled error"),
            "gate": getattr(exc, "gate", None),
            "error": type(exc).__name__, "message": str(exc),
            "evidence": _detail if isinstance(_detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
