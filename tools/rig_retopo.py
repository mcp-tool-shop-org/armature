"""Arm (d) stage 1 — strip the interior wall, then retopologise with **stock Blender only**.

Arms (a) through (c) all broke on the same rock: the performer is a **double-walled,
non-manifold shell**. Bone heat refuses it (E03), envelope tears it, and rigid parts carry
inner wall out into the open air (arm (c), twice). This stage attacks the geometry instead of
the partition.

**Licence, ruled by the Director 2026-08-11:** he ruled it not fit for the pipeline on
commercial-safety grounds. QuadRemesher (Exoside) is **struck** — not enabled, not measured, no
licence row. The gate protects the **pipeline's** cleanliness and reproducibility, not one
rig's right to run a tool. Everything here is Blender's own: ``voxel_remesh`` and
``quadriflow_remesh``, licence-clean by construction under Blender's GPL.

Two variants, measured side by side:

* **A — QuadriFlow direct** on the welded outer shell.
* **B — voxel remesh first** (at a size derived from the *smallest* structure on the figure,
  never a global guess) **then QuadriFlow** to the same target.

Both are graded on whether the sculpted joint balls, the mitten hands and the toes survive —
those are the character, and a retopology that smooths them away has failed no matter what its
face count says.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The world-touching acts are EXPORTING the retopologised GLB and the outer shell,
rendering the comparison panels under `--out/panels`, and writing
`retopo_manifest.json` and `panels.json` under `--out`, plus `halt.json` on the
refusal path. Compensator: delete `--out`; owner: the executor session. Every path it
writes is composed from `--out` and a fixed literal (the panel stems are built from
the tool's own labels, never from an operator-supplied name), so no name component
can carry an export outside the directory the compensator names. The source GLB is
opened read-only.

Named because CLAUDE.md's workflow standard 3 (NAMED_COMPENSATORS -- Sagas,
Garcia-Molina & Salem, SIGMOD 1987) takes NO skip, and because the ordering makes the
question ordinary rather than exotic: `_census_nodes.refusal_and_write_lines`, run over
the 21 Blender-side tools, finds 15 modules with at least one refusal BELOW the first
write, so a halt after the first write is the common case (F-6e1a9d54, wave 25).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_character as rc                                            # noqa: E402
import rig_parts as rp                                                # noqa: E402
from armature_core import blender_scene, landmarks, parts, sitelist   # noqa: E402
from armature_core.errors import GateFailure                          # noqa: E402


class QuadriflowDeclined(GateFailure):
    """QuadriFlow returned CANCELLED and changed nothing."""

    gate = "QUADRIFLOW"


class VoxelOverrideRefused(GateFailure):
    """An explicit `--voxel` that is not a size a remesh can be run at.

    F-e472aa37, wave 22. `--voxel` is declared `type=float, default=None` and was read
    with a TRUTHINESS test, so an explicit `--voxel=0.0` (or `-0.0`) fell through to the
    derived value with nothing saying the given number had been discarded — the wave-16
    rule that a clause keys on the VALUE, never on presence or truthiness. Its own class
    because the two refusals in this file are about the RESULT of a remesh (QuadriFlow
    declined; nothing was produced) and this one is about the argument, before any of it
    runs.
    """

    gate = "RETOPO_ARGS"


class ComparisonNotIsolated(GateFailure):
    """A comparison panel could not be reduced to the one variant it claims to show."""

    gate = "ISOLATE"


class NoRetopoProduced(GateFailure):
    """Neither stock-Blender route produced a mesh."""

    gate = "RETOPO"
from make_parts_sheet import light_the_scene, ortho_camera, shoot     # noqa: E402

#: Object types that put marks on the film, so an object of one of them left render-visible
#: beside a comparison panel's subject IS in the panel. Cameras, lights, empties and
#: armatures are excluded because they draw nothing; `rig_character.gate_objects_registered`
#: keeps ARMATURE in its own stray set because that gate is about what rides into an EXPORT,
#: which is a different question from what reaches a picture. MEASURED as the reason the
#: wave-14 population is not `o.type == "MESH"`: the old clause read only the list it was
#: handed, so a render-visible object of ANY other type was outside the question entirely.
DRAWN_TYPES = frozenset({"MESH", "CURVE", "SURFACE", "META", "FONT", "VOLUME",
                         "GPENCIL", "GREASEPENCIL"})

#: QuadriFlow target, in faces. Chosen for the features that ARE the character: the mitten
#: hands, the toes, and the curvature of the sculpted balls. Recorded with its result rather
#: than defended in the abstract -- the sheet decides whether it was enough.
TARGET_FACES = 40000
#: Voxel size as a fraction of the SMALLEST measured limb radius on this figure. A global
#: constant here would erase the toes to hold the torso; the ratio is what travels.
VOXEL_PER_SMALLEST_RADIUS = 1.0 / 6.0
#: **QuadriFlow is scale-sensitive, and it does not say so.** MEASURED 2026-08-11: on the
#: performer's voxel mesh the operator returns ``{'CANCELLED'}`` in 0.0 s at scale x1 and x10,
#: and ``{'FINISHED'}`` in 2.2 s at x100 (27,066 -> 7,646 quads). The warning it prints --
#: "the mesh needs to be manifold and have face normals that point in a consistent direction"
#: -- is misleading: the mesh passes all three of Blender's own manifold clauses (0 edges not
#: shared by exactly 2 faces, 0 directed edges used more than once, 0 vertices with more than
#: one fan), identically to a control mesh the operator accepts. The figure is simply too
#: small in absolute units for QuadriFlow's internal tolerance. A uniform scale is exactly
#: invertible, so scaling up, remeshing, and scaling back is geometrically free.
QUADRIFLOW_SCALE = 100.0


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/rig_retopo.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--glb", required=True,
                   help="the character shell to voxel-remesh and retopologise; read only")
    p.add_argument("--out", required=True,
                   help="the directory the retopologised GLB, the stripped shell and the "
                        "deviation record are written into. Compensator: delete it; "
                        "owner: the executor session")
    p.add_argument("--target-faces", type=int, default=TARGET_FACES,
                   help=f"faces QuadriFlow is asked for (default {TARGET_FACES}); a "
                        f"budget, not a guarantee -- the measured count rides the record")
    p.add_argument("--voxel", type=float, default=None,
                   help="override the voxel size. The default derives it from the smallest "
                        "LIMB radius, which is far too coarse for the face: at 0.002169 the "
                        "mouth crease is about one voxel wide and comes back as a ragged "
                        "trench. Features, not limbs, set this number.")
    return vars(p.parse_args(argv))


def import_subject(glb):
    scene = rc.fresh_scene(16)
    _import = bpy.ops.import_scene.gltf(filepath=glb)
    rc.require_import_status(_import, glb, NoRetopoProduced, {"who": "rig_retopo"})
    # FAMILY of F-cb986eb3 / F-e911313d: `[...][0]` over the object table. Which
    # object index 0 is depends on file order, and the glTF importer routinely adds a
    # second mesh -- the `glTF_not_exported` Icosphere, which make_rig_sheet's own
    # comment records picking once. Selection is render visibility and an ambiguous
    # result RAISES, the shape rig_character.build_pass and rig_bake._import use.
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    visible = blender_scene.render_visible_meshes(scene, meshes)
    if len(visible) != 1:
        raise NoRetopoProduced(
            f"{glb} presents {len(visible)} render-visible mesh object(s); exactly one "
            f"is the subject to retopologise",
            {"clause": "subject_is_not_one_render_visible_mesh", "gate": "RETOPO", "glb": glb,
             "render_visible": [o.name for o in visible],
             "all_meshes": [o.name for o in meshes]})
    return scene, visible[0]


def extract_outer_shell(ob, diagonal):
    """Delete the interior wall, then repair the glTF seam splits.

    **The rule, recorded:** connected components are computed on *welded* positions (glTF
    splits a vertex at every UV and normal seam, presenting 21,514 shells where the asset has
    67); the component carrying the **most faces** is the exterior; every face outside it is
    deleted. The survivors are then welded by distance at 1e-6 x the bbox diagonal, because
    QuadriFlow needs real edge connectivity and the seam splits leave a boundary edge at every
    UV island.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    before_faces, before_verts = len(bm.faces), len(bm.verts)

    face_comp, exterior, n_shells = rp.classify_shells(bm, diagonal)
    doomed = [bm.faces[int(i)] for i in np.flatnonzero(face_comp != exterior)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    after_delete = len(bm.faces)

    # bmesh.ops.remove_doubles returns None in Blender 5.2 -- count the vertices instead
    # of trusting a return value the API does not give.
    verts_pre_weld = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6 * diagonal)
    welded_away = verts_pre_weld - len(bm.verts)
    bm.faces.ensure_lookup_table()

    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    report = {
        "rule": ("welded-position connected components; keep the component with the most "
                 "faces; delete the rest; then weld by distance at 1e-6 x diagonal to repair "
                 "the glTF UV/normal seam splits"),
        "shells_welded": n_shells,
        "faces_before": before_faces, "verts_before": before_verts,
        "faces_interior_deleted": before_faces - after_delete,
        "interior_fraction": (before_faces - after_delete) / before_faces,
        "faces_after": len(bm.faces), "verts_after": len(bm.verts),
        "verts_welded_away": welded_away,
        "non_manifold_edges": non_manifold, "boundary_edges": boundary,
        "is_closed_manifold": non_manifold == 0 and boundary == 0,
    }
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return report


def _select_only(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def _duplicate(ob, name):
    new = ob.copy()
    new.data = ob.data.copy()
    new.name = new.data.name = name
    bpy.context.scene.collection.objects.link(new)
    return new


def mesh_stats(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    stats = {
        "faces": len(bm.faces), "verts": len(bm.verts), "edges": len(bm.edges),
        "quads": quads, "tris": tris, "ngons": ngons,
        "quad_fraction": quads / max(len(bm.faces), 1),
        "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold),
        "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
    }
    stats["is_closed_manifold"] = (stats["non_manifold_edges"] == 0
                                   and stats["boundary_edges"] == 0)
    bm.free()
    return stats


def deviation_from(reference_ob, ob, diagonal):
    """How far the retopologised surface sits from the surface it replaced.

    Every vertex of the new mesh is measured to the nearest point on the ORIGINAL outer shell.
    This is the number that says whether the sculpted balls kept their curvature or were
    smoothed into the limb -- but it is a **diagnostic**. It gates nothing. The Director's eye
    on the closeups decides whether the character survived.
    """
    from mathutils.bvhtree import BVHTree
    bm_ref = bmesh.new()
    bm_ref.from_mesh(reference_ob.data)
    bm_ref.faces.ensure_lookup_table()
    bvh = BVHTree.FromPolygons([v.co.copy() for v in bm_ref.verts],
                               [[v.index for v in f.verts] for f in bm_ref.faces],
                               all_triangles=False)
    d = []
    for v in ob.data.vertices:
        loc, nrm, idx, dist = bvh.find_nearest(v.co)
        if idx is not None:
            d.append(float(dist))
    bm_ref.free()
    a = np.array(d) if d else np.zeros(1)
    return {"measured_verts": int(len(d)),
            "mean": float(a.mean()), "p99": float(np.percentile(a, 99)),
            "max": float(a.max()),
            "max_as_fraction_of_diagonal": float(a.max() / diagonal),
            "note": "diagnostic only -- gates nothing; the eye judges the closeups"}


def quadriflow(ob, target_faces, scale=QUADRIFLOW_SCALE):
    """Scale up, remesh, scale back — see QUADRIFLOW_SCALE for the measurement behind it.

    The operator's return value is checked. ``{'CANCELLED'}`` is a silent no-op that leaves
    the mesh untouched, and arm (d)'s first run recorded it as a successful retopology of
    147,450 faces into 147,450 faces. A gate that reads the return value costs one line.
    """
    _select_only(ob)
    ob.data.transform(Matrix.Scale(scale, 4))
    ob.data.update()
    t = time.time()
    result = bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=False,
                                              use_preserve_sharp=False,
                                              use_preserve_boundary=False,
                                              preserve_attributes=False, smooth_normals=False,
                                              mode="FACES", target_faces=int(target_faces),
                                              seed=0)
    secs = time.time() - t
    ob.data.transform(Matrix.Scale(1.0 / scale, 4))
    ob.data.update()
    if "FINISHED" not in str(result):
        raise QuadriflowDeclined("the operator declined the mesh and changed nothing",
                                 {"clause": "quadriflow_declined",
                                  "returned": str(result), "scale": scale,
                                  "target_faces": int(target_faces),
                                  "faces_unchanged": len(ob.data.polygons)})
    return secs, str(result)


def voxel_remesh(ob, voxel_size):
    _select_only(ob)
    ob.data.remesh_voxel_size = float(voxel_size)
    ob.data.remesh_voxel_adaptivity = 0.0
    t = time.time()
    bpy.ops.object.voxel_remesh()
    return time.time() - t


def smallest_limb_radius(ob):
    src = rc.world_verts(ob)
    lm = landmarks.derive(src, n_bands=200)
    radii = landmarks.bone_radii(lm, sitelist.BONES)
    named = {k: v for k, v in radii.items() if v and v > 0}
    smallest = min(named.items(), key=lambda kv: kv[1])
    return smallest[0], float(smallest[1]), {k: float(v) for k, v in named.items()}


def isolate_subject(scene, objects, subject):
    """Hide every object but `subject` from the render, and refuse if that did not hold.

    MEASURED 2026-09-04: `render_comparison` hid objects by iterating the `variants` list
    it was handed -- `for _, other in variants: other.hide_render = other is not ob` -- so
    an object ABSENT from that list was never touched. The two variants were then disposed
    of asymmetrically: a dead `variant_a` was removed, a dead `variant_b` was neither
    removed nor hidden. Both arms are wrapped in `except Exception` that records a FAILED
    result and continues, so a failed B -- a duplicate of the outer shell at the identical
    transform -- stayed render-visible and was drawn into every panel of every region, on
    top of the variant each panel claims to show. The tool then wrote `panels.json`,
    printed `RIG_RETOPO_OK` and exited 0.

    The andon is on the direction the invariant does not bound: not "the listed objects are
    hidden" but "nothing else is visible". Same shape as
    `rig_character.gate_objects_registered`.

    WAVE 14, F-4392a2c1 — THE OPERAND. The clause written above for that direction read
    `[o for o in OBJECTS if o is not subject and o.hide_render is not True]`: the same list
    the loop on the line above had just assigned `hide_render` on, so its population was
    the population the loop bounds and it could only fire on an object whose setter refuses
    (measured under the stub: three plain objects, three trials, `still` empty every time,
    the raise never reached). The population that answers "nothing else is visible" is the
    SCENE's, and visibility is `hide_render` OR any of the object's collections'
    (`rig_character.gate_objects_registered:600`, the sibling this docstring already names,
    and the level this one never consulted). `scene` is passed for that reason and for no
    other.
    """
    for ob in objects:
        ob.hide_render = ob is not subject
    # WAVE 16, F-94a7d14d. The expression this replaces was `o.hide_render or
    # any(c.hide_render for c in o.users_collection)` -- a ONE-LEVEL predicate, carried
    # from `rig_character.gate_objects_registered`, where the canonical walk lives in
    # `blender_scene.collection_render_flags` and picks up `exclude` and an ancestor's
    # `hide_render` too. Measured under the stub: an object in a collection nested inside a
    # `hide_render=True` parent, and one in an excluded collection, both read as VISIBLE to
    # the old expression and as invisible to `render_visible_meshes` -- so this andon
    # halted a comparison between panels on a scene the renderer would draw correctly. The
    # gate and the renderer answer one question with one implementation now.
    reachable, hidden_collections = blender_scene.collection_render_flags(scene)
    drawable = reachable - hidden_collections

    def _drawn(o):
        return not o.hide_render and any(c.name in drawable for c in o.users_collection)

    still = sorted(
        o.name for o in scene.objects
        if o is not subject and o.type in DRAWN_TYPES and _drawn(o))
    if still:
        raise ComparisonNotIsolated(
            f"{len(still)} object(s) are still in the render beside the panel's subject "
            f"{getattr(subject, 'name', subject)!r}: {still}. Every panel would be a "
            f"composite of the variant it names and something else",
            {"clause": "comparison_is_not_isolated",
             "gate": "ISOLATE", "subject": getattr(subject, "name", None),
             "still_visible": still,
             "population": f"scene.objects of type {sorted(DRAWN_TYPES)}",
             "n_examined": len([o for o in scene.objects if o.type in DRAWN_TYPES]),
             "n_hidden_by_the_loop": len([o for o in objects if o is not subject]),
             "visibility": ("blender_scene.collection_render_flags: hide_render OR "
                            "no users_collection reachable in the view layer and not "
                            "hidden from render (ancestor hide_render and exclude "
                            "included)"),
             "collections_reachable": sorted(reachable),
             "collections_hidden": sorted(hidden_collections)})
    if subject is None or subject.hide_render:
        raise ComparisonNotIsolated(
            f"the panel's own subject {getattr(subject, 'name', subject)!r} is hidden from "
            f"render; the panel would be empty",
            {"clause": "panel_subject_is_hidden_from_render",
             "gate": "ISOLATE", "subject": getattr(subject, "name", None),
             "still_visible": []})
    return [o.name for o in objects if o is not subject]


def render_comparison(scene, variants, out_dir, diagonal, centre):
    """Full figure plus the three regions that decide it: a sculpted ball, a hand, a foot."""
    light_the_scene(scene)
    os.makedirs(out_dir, exist_ok=True)
    lo, hi = centre
    height = hi[2] - lo[2]
    mid_x = 0.5 * (lo[0] + hi[0])
    regions = [
        ("figure", (mid_x, 0.0, lo[2] + 0.5 * height), height * 1.12, 0.0),
        ("shoulder ball", (mid_x + 0.085, 0.0, lo[2] + 0.79 * height), height * 0.17, 0.0),
        ("mitten hand", (mid_x + 0.115, 0.0, lo[2] + 0.50 * height), height * 0.15, 0.0),
        ("foot and toes", (mid_x + 0.055, 0.0, lo[2] + 0.035 * height), height * 0.15, 18.0),
    ]
    rows = []
    for region, target, oscale, azim in regions:
        panels = []
        for label, ob in variants:
            # Everything render-visible in the SCENE, not only the objects in `variants`:
            # a failed variant never reaches this list and used to be drawn into every
            # panel, on top of the one being shown.
            isolate_subject(scene, [o for o in bpy.data.objects if o.type == "MESH"], ob)
            ortho_camera(scene, f"cam_{label}_{region}", Vector(target), oscale,
                         (700, 1150) if region == "figure" else (700, 700), azim)
            path = os.path.join(out_dir, f"{label}_{region}.png".replace(" ", "_"))
            shoot(scene, path)
            panels.append({"body": path, "label": label})
        rows.append({"title": region, "panels": panels})
    for _, other in variants:
        other.hide_render = False
    return rows


def main():
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    started = time.strftime("%Y-%m-%dT%H:%M:%S")

    scene, ob = import_subject(args["glb"])
    src = rc.world_verts(ob)
    # SIBLING CARRIED under F-6a9a0f72 (wave 14). Gate SCALE: the voxel size and every
    # deviation figure in the comparison manifest are fractions of this number.
    diagonal, lo, hi = rc.subject_scale(src, "rig_retopo")

    smallest_name, smallest_r, all_radii = smallest_limb_radius(ob)
    # F-e472aa37, wave 22 — the branch keys on the VALUE, never on truthiness, and the
    # override is BOUNDED. `args["voxel"] if args["voxel"] else ...` is a truthiness test
    # on a float declared `type=float, default=None`, so an explicit `--voxel=0.0` or
    # `-0.0` silently fell through to the derived value — MEASURED with
    # `VOXEL_PER_SMALLEST_RADIUS = 1/6` and a smallest limb radius of 0.01301: both
    # produced voxel 0.00217 with `voxel_derivation` reading "smallest measured limb
    # radius", the override erased without a word. A non-finite or non-positive explicit
    # size is refused by name instead.
    voxel_given = args["voxel"] is not None
    if voxel_given:
        voxel = parts.require_finite(
            "--voxel", args["voxel"], VoxelOverrideRefused,
            {"gate": VoxelOverrideRefused.gate, "sub_gate": "VOXEL",
             "andon": VoxelOverrideRefused.__name__, "who": "rig_retopo",
             "flag": "--voxel", "clause": "voxel_not_finite_and_positive",
             "smallest_limb": smallest_name, "smallest_limb_radius": smallest_r,
             "would_have_derived": smallest_r * VOXEL_PER_SMALLEST_RADIUS},
            positive=True)
        voxel_derivation = ("explicit override -- limb radii do not bound facial "
                            "features")
        voxel_route = f"voxel remesh at {voxel:.5f} (explicit --voxel override)"
    else:
        voxel = smallest_r * VOXEL_PER_SMALLEST_RADIUS
        voxel_derivation = (f"smallest measured limb radius ({smallest_name} = "
                            f"{smallest_r:.5f}) / 6")
        voxel_route = (f"voxel remesh at {voxel:.5f} (= {smallest_name} radius "
                       f"{smallest_r:.5f} / 6)")

    extraction = extract_outer_shell(ob, diagonal)
    ob.name = ob.data.name = "outer_shell"
    shell_stats = mesh_stats(ob)

    variant_a = _duplicate(ob, "A_quadriflow_direct")
    variant_b = _duplicate(ob, "B_voxel_then_quadriflow")

    results = {}
    try:
        secs, returned = quadriflow(variant_a, args["target_faces"])
        results["A_quadriflow_direct"] = {
            "route": "QuadriFlow directly on the welded outer shell, at x100 scale",
            "seconds": round(secs, 1), "returned": returned, **mesh_stats(variant_a),
            "deviation": deviation_from(ob, variant_a, diagonal)}
    except Exception as exc:                                          # noqa: BLE001
        results["A_quadriflow_direct"] = {"route": "QuadriFlow direct", "FAILED": str(exc),
                                          "exception": type(exc).__name__}

    try:
        vsecs = voxel_remesh(variant_b, voxel)
        after_voxel = mesh_stats(variant_b)
        qsecs, returned = quadriflow(variant_b, args["target_faces"])
        results["B_voxel_then_quadriflow"] = {
            # F-e472aa37: `route` used to be built UNCONDITIONALLY as "voxel remesh at
            # {voxel} (= {limb} radius {r} / 6)" while `voxel_derivation` beside it was
            # built under the branch — so one record stated two contradictory accounts
            # of where its voxel size came from, and the arithmetic in the first was
            # FALSE on an override. MEASURED: `--voxel=0.005` wrote `route: "voxel
            # remesh at 0.00500 (= forearm radius 0.01301 / 6)"` — 0.01301/6 is 0.00217
            # — directly above `voxel_derivation: "explicit override..."`. A reader
            # deciding which arm won read the false one first. Both strings are built in
            # the ONE branch above now, so they cannot disagree.
            "route": voxel_route + " then QuadriFlow at x100 scale",
            "voxel_size": voxel,
            "voxel_derivation": voxel_derivation,
            "seconds_voxel": round(vsecs, 1), "seconds_quadriflow": round(qsecs, 1),
            "returned": returned,
            "after_voxel_before_quadriflow": after_voxel,
            **mesh_stats(variant_b), "deviation": deviation_from(ob, variant_b, diagonal)}
    except Exception as exc:                                          # noqa: BLE001
        results["B_voxel_then_quadriflow"] = {"route": "voxel then QuadriFlow",
                                              "FAILED": str(exc),
                                              "exception": type(exc).__name__}

    live = [k for k, v in results.items() if "FAILED" not in v and v.get("faces", 0) > 0]
    if not live:
        raise NoRetopoProduced("both stock-Blender routes failed to produce a mesh",
                               {"clause": "no_retopo_route_produced_a_mesh", "results": results})

    # F-244b2ad5: `import_subject` refuses an ambiguous import, `quadriflow` refuses a
    # declined operator (twice), and the `NoRetopoProduced` inline `raise` above says both
    # routes produced nothing — four refusals, none of which needs a directory. It is
    # created HERE, below the last of them. Corrected shape carried from
    # `render_performer.py:319`.
    os.makedirs(out_dir, exist_ok=True)

    for name, obj in (("A_quadriflow_direct", variant_a),
                      ("B_voxel_then_quadriflow", variant_b)):
        if name not in live:
            continue
        path = os.path.join(out_dir, f"{name}.glb")
        _select_only(obj)
        # WAVE 14, F-6a9a0f72: snapshot before, status set captured.
        before_glb = rc.export_target_snapshot(path)
        export_result = bpy.ops.export_scene.gltf(
            filepath=path, export_format="GLB", use_selection=True,
            export_apply=False, export_yup=True)
        # F-9b2d4106: the variants recorded a sha, which raises on an absent file, but
        # nothing refused a ZERO-BYTE export. One implementation for all three exports in
        # this file, `rig_character.gate_glb_written`.
        written = rc.gate_glb_written(path, result=export_result, before=before_glb,
                                      what=f"the {name} retopo GLB")
        results[name]["glb"] = written["path"]
        results[name]["sha256"] = written["sha256"]
        results[name]["bytes"] = written["bytes"]

    shell_path = os.path.join(out_dir, "outer_shell.glb")
    _select_only(ob)
    # WAVE 14, F-6a9a0f72: snapshot before, status set captured.
    before_shell = rc.export_target_snapshot(shell_path)
    shell_result = bpy.ops.export_scene.gltf(
        filepath=shell_path, export_format="GLB", use_selection=True,
        export_apply=False, export_yup=True)
    # F-21d6e3ac. This manifest published `outer_shell_glb` as a BARE STRING while the two
    # variant exports twelve lines above each recorded a sha and the input recorded
    # `source_sha256` - the asymmetry was inside one manifest. The outer shell is not
    # incidental: it is the INPUT both retopo arms are compared against and the object every
    # comparison panel is shot from, so a later session re-reading the manifest to reproduce
    # the comparison could not tell whether the shell on disk is the shell the run used.
    shell_written = rc.gate_glb_written(shell_path, result=shell_result,
                                        before=before_shell,
                                        what="the outer-shell GLB")

    # SYMMETRIC. MEASURED 2026-09-04: the superseded shape removed a dead A and did
    # nothing at all about a dead B, and B is a duplicate of the outer shell at the
    # identical transform -- so it stayed render-visible and was composited into every
    # panel. Both arms go through one loop, before any panel is shot.
    labels = {
        "A_quadriflow_direct":
            lambda: f"A — QuadriFlow direct, "
                    f"{results['A_quadriflow_direct']['faces']:,} faces",
        "B_voxel_then_quadriflow":
            lambda: f"B — voxel then QuadriFlow, "
                    f"{results['B_voxel_then_quadriflow']['quads']:,} quads"}
    columns = [(f"input — outer shell, {shell_stats['faces']:,} tris", ob)]
    removed = []
    for name, obj in (("A_quadriflow_direct", variant_a),
                      ("B_voxel_then_quadriflow", variant_b)):
        if name in live:
            columns.append((labels[name](), obj))
        else:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    rows = render_comparison(scene, columns, os.path.join(out_dir, "panels"), diagonal,
                             (lo, hi))

    manifest = {
        "tool": "rig_retopo", "started": started, "source_glb": args["glb"],
        "blender": blender_scene.blender_provenance(),
        "variants_removed_before_the_sheet": removed,
        "source_sha256": rc.sha256_file(args["glb"]), "diagonal": diagonal,
        # The ruling, restated in neutral prose. MEASURED 2026-09-04: this field carried
        # the Director's conversational sentence verbatim, copied into every
        # retopo_manifest.json the tool writes -- against the standing rule that public
        # surfaces carry decisions and facts in neutral prose and never quotations from
        # chat. The date, the subject and the verdict are what a record needs.
        "licence": {
            "ruling": ("Director ruling 2026-08-11: QuadRemesher (Exoside) is struck from "
                       "the pipeline on commercial-safety grounds"),
            "struck": "QuadRemesher (Exoside) — not enabled, not measured, no licence row",
            "used": ("Blender built-ins only (mesh.voxel_remesh, mesh.quadriflow_remesh) "
                     "— GPL, COMMERCIAL: YES, and no per-rig entitlement is involved. "
                     "Which build ran is recorded under `blender`, not asserted here"),
        },
        "target_faces": args["target_faces"],
        "quadriflow_scale": {
            "factor": QUADRIFLOW_SCALE,
            "why": "MEASURED: quadriflow_remesh returns CANCELLED in 0.0s at x1 and x10 and "
                   "FINISHED in 2.2s at x100 on this figure. Its warning names manifoldness, "
                   "but the mesh passes all three of Blender's manifold clauses identically "
                   "to a control the operator accepts -- the figure is too small in absolute "
                   "units for QuadriFlow's tolerance. A uniform scale is exactly invertible.",
        },
        "smallest_limb_radius": {"bone": smallest_name, "radius": smallest_r},
        "limb_radii": all_radii,
        "outer_shell_extraction": extraction, "outer_shell_stats": shell_stats,
        "variants": results,
        "outer_shell_glb": shell_written["path"],
        "outer_shell_sha256": shell_written["sha256"],
        "outer_shell_bytes": shell_written["bytes"],
        "gate_GLB_written": {"outer_shell": shell_written},
        "sheet_rows": rows,
    }
    with open(os.path.join(out_dir, "retopo_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    with open(os.path.join(out_dir, "panels.json"), "w", encoding="utf-8") as fh:
        json.dump({"title": "E07 arm (d) — outer-shell extraction and stock-Blender retopo",
                   "subtitle": "the interior wall deleted, then retopologised · the sculpted "
                               "balls, the mitten hands and the toes are what decide it",
                   "out": out_dir, "filename": "E07-retopo.png",
                   "rows": rows}, fh, indent=2)
    print("RIG_RETOPO_OK " + json.dumps({k: {"faces": v.get("faces"), "quads": v.get("quads"),
                                         "manifold": v.get("is_closed_manifold"),
                                         "max_dev": v.get("deviation", {}).get("max")}
                                     for k, v in results.items()}))


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
    #
    # The record on disk carries the same three-state vocabulary. The exit code is computed
    # BEFORE anything that can fail and delivered from a `finally`: re-parsing argv or
    # re-hashing the GLB inside this block can raise a SECOND exception, which used to leave
    # the whole `try` statement with `sys.exit` never reached (measured 2026-09-04).
    try:
        main()
    # WAVE 28, F-814335e4. A DELIBERATE REFUSAL IS NOT A CRASH, and this handler used
    # to record it as one. `argparse` refuses a missing or mistyped required flag by
    # raising `SystemExit(2)`; with no re-raise above the `except BaseException`, the
    # branch below caught it, wrote `"error": "SystemExit", "message": "2"` under
    # `FAILED - an unhandled error`, and exited **1** -- the code this repo reserves for
    # a crash. MEASURED on `3380ae2` with `blender_stub.exit_code_of_main_block` and a
    # `main` replaced by a `SystemExit(2)` raiser: rig_bake, rig_character, rig_parts,
    # rig_repair and rig_retopo returned 1 with a halt line whose entire message was the
    # character `2`, while the sixteen siblings (preview_glb.py and kin) returned 2 and
    # printed nothing. Worse, the halt-record branch re-parses argv to find `--out`, and
    # on this path argparse raised a SECOND time, so no `halt.json` was written either.
    # `armature_core.parts.run_tool_main`, the ONE CPython handler, has carried this
    # same two lines since wave 22; this is the Blender-side local handler adopting the
    # shape, not a second spelling of it. The three-outcome rule the comment above
    # states -- "a deliberate refusal exits 2; a crash exits 1" -- is what these two
    # lines make true for an argument the operator got wrong.
    except SystemExit:
        raise
    except BaseException as exc:                                      # noqa: BLE001
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
            "tool": "rig_retopo", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "rig_retopo", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            # `allow_nan=False` (F-897a3329): strict JSON, and it cannot raise here because
            # `_halt_keysafe` above has already replaced every non-finite float with its repr.
            _line = json.dumps(_sentinel, default=str, allow_nan=False)
        except BaseException:                                         # noqa: BLE001
            pass
        try:
            _a = parse_args()
            _d = os.path.abspath(_a["out"])
            os.makedirs(_d, exist_ok=True)
            with open(os.path.join(_d, "halt.json"), "w", encoding="utf-8") as fh:
                json.dump(dict(_sentinel, traceback=traceback.format_exc()), fh,
                          indent=2, default=str)
        except BaseException:                                         # noqa: BLE001
            # The halt record is a courtesy; the sentinel and the exit code are
            # the contract. Even this diagnostic is guarded (F-586822bf):
            # nothing in this handler may reach the `finally` before `sys.exit`.
            try:
                traceback.print_exc()
            except BaseException:                                     # noqa: BLE001
                pass
        finally:
            print("RIG_RETOPO_HALT " + _line)
            sys.exit(_code)
