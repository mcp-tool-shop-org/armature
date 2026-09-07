"""Headless GLB preview: import, measure, render 2 full views + 2 head crops.

blender -b --factory-startup -P preview_glb.py -- --glb <path> --out <dir> --name <name>
Read-only on the GLB; writes renders + stats.json into --out.

`make_cast_sheet.py` consumes the `<name>_stats.json` this writes.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is writing four PNGs and `<name>_stats.json` under `--out`.
Compensator: delete `--out`; owner: the executor session. That statement is only true
while every written path resolves UNDER `--out`, which is why `--name` is refused unless
it is a single path component (F-7cd1b3b7, wave 22): `--name` is pasted as the NAME
COMPONENT of every written path, and MEASURED on the repo venv,
`os.path.join("C:/tmp/out", "../v3_full_a.png")` and
`os.path.join("C:/tmp/out", "C:/elsewhere/v3_full_a.png")` both resolve outside `--out`
— while `gate_previews_written` PASSES (it re-reads the same escaped paths) and
`PREVIEW_GLB_OK` prints. A compensator that names a directory the artifacts are not in
undoes nothing. The GLB is opened read-only and is never written.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

# `single_path_segment` is ADOPTED BY IMPORT from SEAM 1's ONE home, never copied:
# instruments-measure held two byte-identical spellings (`pack_pose_pack.py:82`,
# `resample_motion.py:76`) and deletes both; builders adopts the same object for
# `fetch_run --run`. Nobody spells a third (wave 22, SEAM 1).
from armature_core import blender_scene, parts  # noqa: E402
# F-a2630f86: `render_target_snapshot` is `export_target_snapshot`'s twin and lives
# beside it. The idiom is `rig_bake`'s and `make_parts_sheet`'s -- one implementation,
# imported.
import rig_character as rc  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

#: The engine identifiers this tool will accept, in the order it tries them. The loop
#: exists because Blender renamed EEVEE between versions; the ORDER is now the same one
#: `make_skeleton_sheet`, `make_binding_sheet` and `make_parts_sheet` use, because this
#: file used to try them the other way round and a sheet rendered beside a preview could
#: be drawn by a different engine with nothing in either record able to say so.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")

#: Director-facing clay/character stills share ONE linear plate with the sheet tools
#: (F-cade389c). Home is `make_parts_sheet.CLAY_STUDIO_LINEAR`; imported, never copied.
from make_parts_sheet import CLAY_STUDIO_LINEAR  # noqa: E402

#: Head elev is level so a look-down does not pack torso into the square crop.
HEAD_ELEV_DEG = 0.0
#: Head radius as a fraction of bbox height — height alone, never width (F-34e036b0).
HEAD_RADIUS_FRAC = 0.13
#: Head centre sits this fraction of H below the bbox top (middle of the top ~14% band).
HEAD_CENTRE_FROM_TOP_FRAC = 0.07


def head_framing(center, dims, hi):
    """Square head crop from HEIGHT alone — centre in the top band, radius ~0.13*H.

    WAVE 32, F-34e036b0. The prior formula took `max(0.14*H, 0.5*max(W,D)*0.6)`, so
    character WIDTH drove the crop on 6 of 8 cast-survey subjects and the square frame
    packed chest under a look-down elev. Width is deliberately absent here.
    """
    h = float(dims.z)
    head_r = HEAD_RADIUS_FRAC * h
    head_c = Vector((center.x, center.y, hi.z - HEAD_CENTRE_FROM_TOP_FRAC * h))
    return head_c, head_r


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


class PreviewGlbGate(GateFailure):
    """The preview could not be composed, or could not be composed reproducibly."""

    gate = "PREVIEW_GLB"


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/preview_glb.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def gate_output_overwrite(out, planned, overwrite, gate_cls):
    """`(pre_existed, already_present, strays)` for `--out`, refusing a silent overwrite.

    WAVE 28, F-8b7f48a8 (panel CRITICAL). MEASURED on `3380ae2` over the 21 Blender-side
    instruments: **36 `os.makedirs` call sites, every one `exist_ok=True`, no refusal, no
    numbering, and no line in any record saying the directory already existed.** The three
    renderers that author the images a generation is conditioned on -- `render_turnaround`,
    `render_start_frame` and `preview_glb` -- also had no `unexpected_files_in_out_dir`
    sweep, where `render_performer.py:511` and `preview_walk.py:365` both derive one and
    say in their own comments why. All three write FIXED names, so a re-run always lands on
    the previous run's: a re-run with fewer views or a different name left the earlier run's
    masters beside this run's, the manifest named only its own, and every consumer that
    reads the directory as a set (`encode_control.py:138`, `build_payload.py:363`, both a
    bare listdir) picked up both.

    THE POLICY, stated rather than defaulted: a run that would land on its own earlier
    output REFUSES, by name, ABOVE `os.makedirs` -- so a declined run leaves nothing behind
    -- unless `--overwrite` says to replace it. When it does replace, the success record
    and the success line both carry `out_dir_pre_existed` and `overwrote`, which is what
    makes two runs into one `--out` distinguishable in a scrollback.

    SEAM 1 (`wave-28/seams-inbox.md`): builders' `F-5fd16451` is the same mechanism at
    `build_assembly_payload.py:831`. The flag name, the clause word, the sentence and the
    two record keys are agreed across both domains. `armature_core.parts` is where a shared
    helper would live and is another domain's owned file this wave, so these three
    Blender-side copies are held to ONE text by `tests/test_instruments_amend_w28.py`
    instead -- the arrangement `_render_status`'s nine copies already have.

    `strays` is a DIAGNOSTIC: it gates nothing here either.
    """
    pre_existed = os.path.isdir(out)
    already_present = sorted(f for f in planned
                             if os.path.isfile(os.path.join(out, f))
                             ) if pre_existed else []
    strays = sorted(f for f in os.listdir(out)
                    if f.lower().endswith(".png") and f not in set(planned)
                    ) if pre_existed else []
    if already_present and not overwrite:
        raise gate_cls(
            f"{len(already_present)} of the {len(planned)} files this run writes: already "
            f"on disk from an earlier run; this run would replace what is there. Pass "
            f"--overwrite to replace it, or point --out at a directory of its own",
            {"clause": "output_already_exists", "out": os.path.abspath(out),
             "already_present": already_present, "planned": len(planned),
             "unexpected_files_in_out_dir": strays,
             "compensator": "delete --out; owner: the executor session"})
    return pre_existed, already_present, strays


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--glb", action="append", required=True,
                   help="the GLB to look at. READ ONLY -- nothing here writes to it")
    p.add_argument("--out", required=True,
                   help="the directory the four renders and <name>_stats.json are written "
                        "into; make_cast_sheet.py consumes that stats file. Compensator: "
                        "delete it; owner: the executor session")
    p.add_argument("--overwrite", action="store_true",
                   help="replace this run's own files where --out already holds them "
                        "from an earlier run. WITHOUT it the run REFUSES rather than "
                        "overwriting, by name, before the output directory is touched")
    p.add_argument("--camera-path", default=None,
                   help="optional keyframed orbit JSON (framing.normalize_camera_keys); "
                        "reuses render_performer.load_camera_path / sample_camera_at "
                        "(F-813d7a7f). Default: this tool's hard-coded preview orbits")
    p.add_argument("--name", required=True,
                   help="ONE path component — it is pasted into every written "
                        "filename, so a separator, an absolute path or a dot name "
                        "writes the preview outside --out")
    a = p.parse_args(argv)
    # F-7cd1b3b7, wave 22 — REFUSED AT THE PARSER, above `os.makedirs`, which is where
    # the mistake is still free. `--name` was free text with no `type=`, no `choices=`
    # and no validation, pasted as the NAME COMPONENT of `os.path.join(out_dir,
    # f"{args.name}_{suffix}.png")` (:141), assigned to `scn.render.filepath` (:142),
    # and again into `os.path.join(args.out, f"{args.name}_stats.json")` (:290).
    # MEASURED on the repo venv: of `perf/v3`, `../v3` and `C:/elsewhere/v3`, the last
    # two resolve OUTSIDE `--out`. This is the family wave 18 closed one domain over
    # (`pack_pose_pack --name`, `resample_motion --name`); that census was scoped to
    # instruments-measure's 42 tools and never ranged over these 21. An equivalent AST
    # walk over the 21 finds this flag and `render_turnaround --prefix` and nothing else.
    parts.single_path_segment(a.name, "--name", PreviewGlbGate,
                              {"who": "preview_glb", "out": a.out})
    return a


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

    WAVE 16, F-39381793 -- THE COPY THE FAMILY WAS CARRIED FROM IS THE COPY THAT DRIFTED.
    `_render_status` is held identical across its nine copies by a census
    (`test_instruments_amend_w14.py:468`); `select_engine` had none, and one of its seven
    definitions had drifted in the field the halt line reads. Measured by AST over
    `tools/*.py` and `tools/superseded/`: seven definitions, and THIS one raised with no
    `"clause": "engine"` key, where `preview_walk`, `render_performer`,
    `render_start_frame`, `render_turnaround`, `rig_bake` and `superseded/render_reference`
    all carried it. `preview_glb` has four `PreviewGlbGate` raise sites and only one of
    them named a clause at all, so a `PREVIEW_GLB_HALT` line could not be told from its
    siblings by the field every other refusal in this family uses for exactly that. All
    four name a clause now, and `test_instruments_amend_w16.py` carries the census that
    holds every copy of this function to one shape -- its MESSAGE stays each tool's own
    (a bake is not a render, and this file is a preview), its structure and its evidence
    KEYS do not.
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
        {"clause": "engine", "candidates": list(candidates),
         "blender": bpy.app.version_string})


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
    path = os.path.join(out_dir, f"{args.name}_{name_suffix}.png")
    # F-a2630f86: the target as it stood BEFORE this render, returned beside the path
    # and the status so `gate_previews_written` can rule on all three at once. It is not
    # refused here for the same reason the status is not (see below).
    before = rc.render_target_snapshot(path)
    scn.render.filepath = path
    render_result = bpy.ops.render.render(write_still=True)
    # WAVE 14, F-6a9a0f72: the render operator's STATUS SET, RETURNED beside the path so
    # `gate_previews_written` refuses on it. It is not refused here, deliberately: this
    # tool's post-write verification is one gate over the whole PLAN, and a second raise
    # inside the shooter would strand a refusal below the first write that the
    # write-ordering ratchet would then have to carry under a name of its own.
    return path, _render_status(render_result), before



def gate_previews_written(written):
    """Every planned view was drawn, exists on disk and is not zero bytes, or halt.

    `written` is the list of `(path, status, before)` triples `add_camera_render`
    returns -- `before` being `rig_character.render_target_snapshot(path)`, taken above
    the render (F-a2630f86, wave 22: it was a PAIR, and the fourth clause below could
    not exist without the third element).

    F-13bd448d. `bpy.ops.render.render(write_still=True)` returns an operator status set and
    can return `{'CANCELLED'}` WITHOUT raising; `add_camera_render` discarded it, and nothing
    afterwards read the four paths back -- `<name>_stats.json` is written from measurements
    taken off the SCENE, and the success sentinel was printed over a directory that may hold
    nothing. This tool is also the one whose output nothing downstream reads
    (`make_cast_sheet.py` consumes the stats JSON, not the PNGs), so a run that wrote zero
    images left no failing consumer anywhere and the operator discovered the four missing
    previews by opening the directory.

    The shape is `preview_walk.py:196-206`'s -- missing AND zero-byte, over the PLAN --
    carried rather than reinvented.

    WAVE 14, F-6a9a0f72: the docstring above says the operator can return CANCELLED without
    raising and this gate read no status set -- it read the FILES, which is a property a
    PREVIOUS run's four PNGs at the same paths satisfy. The status clause runs FIRST, and
    it is the only one of the three that can tell an empty directory from a stale one.
    """
    paths = [p for p, _st, _b in written]
    declined = [(os.path.basename(p), st)
                for p, st, _b in written if "FINISHED" not in st]
    if declined:
        raise PreviewGlbGate(
            f"the render operator declined {len(declined)} of {len(written)} views: "
            f"{declined}. It returns a status set and can return CANCELLED without "
            f"raising, so any file at those paths is a previous run's",
            {"clause": "operator_status", "declined": declined,
             "planned": len(written),
             "paths": [os.path.abspath(p) for p in paths]})
    missing = [p for p in paths if not os.path.isfile(p)]
    empty = [p for p in paths
             if p not in missing and os.path.getsize(p) == 0]
    if missing or empty:
        raise PreviewGlbGate(
            f"the preview is not complete: {len(missing)} of {len(paths)} views were never "
            f"written {[os.path.basename(p) for p in missing[:8]]} and {len(empty)} are "
            f"zero bytes {[os.path.basename(p) for p in empty[:8]]}",
            {"clause": "missing_or_empty", "planned": len(paths),
             "paths": [os.path.abspath(p) for p in paths],
             "missing": [os.path.abspath(p) for p in missing],
             "empty": [os.path.abspath(p) for p in empty]})
    # CLAUSE 4, F-a2630f86 -- the direction the three above cannot see. `FINISHED` in
    # the status set, `os.path.isfile` and `getsize != 0` are exactly the three
    # properties `rig_character.gate_glb_written`'s docstring names as insufficient: a
    # PREVIOUS run's four PNGs at these paths satisfy all three. Wave 16 made the
    # pre-export snapshot REQUIRED on that ground and the render half of the same
    # premise had no such clause at any of the five renderers. One implementation,
    # beside its export twin.
    for path, _st, before in written:
        rc.require_render_target_moved(
            path, before, PreviewGlbGate,
            {"gate": PreviewGlbGate.gate, "sub_gate": "RENDER_TARGET",
             "who": "preview_glb", "planned": len(paths)},
            what="the preview view")
    return {"planned": len(paths), "missing": [], "empty": [],
            "verdict": f"all {len(paths)} planned views exist and are non-empty"}


def main():
    args = parse_args()
    glbs = list(args.glb)
    primary_glb = glbs[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _import = bpy.ops.import_scene.gltf(filepath=primary_glb)
    rc.require_import_status(_import, primary_glb, PreviewGlbGate,
                             {"who": "preview_glb"})
    for extra in glbs[1:]:
        _extra = bpy.ops.import_scene.gltf(filepath=extra)
        rc.require_import_status(_extra, extra, PreviewGlbGate,
                                 {"who": "preview_glb", "role": "roster_extra"})

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
            f"{primary_glb} imported {len(all_meshes)} mesh object(s) and none of them is "
            f"render-visible; there is nothing to preview",
            {"clause": "no_render_visible_mesh", "glb": primary_glb,
             "mesh_objects_all": [o.name for o in all_meshes]})

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
        "glb": primary_glb,
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

    # Head crop from HEIGHT alone (F-34e036b0): width used to inflate head_r into a
    # torso frame on wide characters. Centre sits in the top ~14% of H; elev is level.
    head_c, head_r = head_framing(center, dims, hi)

    stats["engine"] = select_engine(scn)
    scn.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scn.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    # ONE clay plate with the sheets (F-cade389c); not the old 0.72 light grey.
    bg.inputs[0].default_value = (*CLAY_STUDIO_LINEAR, 1.0)
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
    # ---- WAVE 28, F-8b7f48a8 (panel CRITICAL). THE SILENT OVERWRITE. Every written
    # name here is `<--name>_<suffix>`, so a second run under the same --name lands on the
    # first one's four renders and its stats file -- and `make_cast_sheet.py` consumes that
    # stats file. MEASURED on `3380ae2` over the 21 owned tools: 36 `os.makedirs` sites,
    # every one `exist_ok=True`, none saying the directory already existed. SEAM 1
    # (wave-28 inbox): one flag, one clause word, one sentence, two record keys, shared
    # with builders' `F-5fd16451`.
    #
    # The refusal fires ABOVE `os.makedirs`, so a declined run leaves nothing behind.
    planned = [f"{args.name}_{s}.png"
               for s in ("full_a", "full_b", "head_a", "head_b")]
    planned.append(f"{args.name}_stats.json")
    # Here the stray sweep is also how an operator sees that a PREVIOUS --name's four
    # views are still sitting in this directory.
    out_dir_pre_existed, already_present, strays = gate_output_overwrite(
        args.out, planned, args.overwrite, PreviewGlbGate)
    if already_present:
        print("[overwrite] " + json.dumps(
            {"out": os.path.abspath(args.out), "overwrote": already_present}))

    os.makedirs(args.out, exist_ok=True)
    # F-813d7a7f: optional authored camera path drives full_a / full_b orbits.
    cam_keys = None
    if getattr(args, "camera_path", None):
        from render_performer import load_camera_path
        from armature_core import framing as _framing
        cam_keys = load_camera_path(args.camera_path)
        sample_a = _framing.sample_camera_at(cam_keys, 0)
        sample_b = _framing.sample_camera_at(cam_keys, cam_keys[-1]["frame"])
        full_a_az, full_a_el = sample_a["azimuth_deg"], sample_a["elevation_deg"]
        full_b_az, full_b_el = sample_b["azimuth_deg"], sample_b["elevation_deg"]
        # Path radius is absolute world distance; fall back to bbox radius when unset.
        path_radius = float(sample_a["radius"]) if sample_a["radius"] else radius
    else:
        full_a_az, full_a_el, full_b_az, full_b_el = 30, 10, -30, 10
        path_radius = radius
    stats["camera_path"] = getattr(args, "camera_path", None)
    written = [
        add_camera_render("full_a", center, path_radius, full_a_az, full_a_el,
                          (640, 960), args.out, args),
        add_camera_render("full_b", center, path_radius, full_b_az, full_b_el,
                          (640, 960), args.out, args),
        add_camera_render("head_a", head_c, head_r, full_a_az, HEAD_ELEV_DEG,
                          (512, 512), args.out, args),
        add_camera_render("head_b", head_c, head_r, full_b_az, HEAD_ELEV_DEG,
                          (512, 512), args.out, args),
    ]
    stats["gate_PREVIEW_GLB"] = gate_previews_written(written)
    stats["views"] = [os.path.abspath(p) for p, _st, _b in written]
    stats["render_status"] = {os.path.basename(p): st for p, st, _b in written}
    # F-8b7f48a8: what --out held BEFORE this run, in the record make_cast_sheet reads.
    stats["out_dir_pre_existed"] = out_dir_pre_existed
    stats["overwrote"] = already_present
    stats["unexpected_files_in_out_dir"] = strays
    stats["unexpected_files_rule"] = ("every file in --out whose name ends in .png, compared case-INSENSITIVELY, that this run did not plan to write. A DIAGNOSTIC: it gates nothing. The sibling renderers render_performer.py and preview_walk.py derive the same population")

    with open(os.path.join(args.out, f"{args.name}_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print("PREVIEW_GLB_OK " + json.dumps({"name": args.name, "engine": stats["engine"],
                                      "triangles": tris,
                                      # F-8b7f48a8: two runs into one --out are
                                      # distinguishable in a scrollback.
                                      "out_dir_pre_existed": out_dir_pre_existed,
                                      "overwrote": already_present,
                                      "unexpected_files_in_out_dir": strays}))
    return 0


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
            "tool": "preview_glb", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "preview_glb", "outcome": _outcome,
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
            print("PREVIEW_GLB_HALT " + _line)
            sys.exit(_code)
