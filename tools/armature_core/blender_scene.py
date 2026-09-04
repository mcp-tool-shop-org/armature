"""The only module that imports bpy.

Scene assembly changes rarely; channel formats change often — so they live apart
(DECOMPOSE_BY_SECRETS). Everything measured here is handed back as plain numpy and
plain dicts, which is what lets the rest of the exporter be tested without Blender.

Blender 5.2 API notes, all measured on this rig 2026-08-10 rather than inherited:
  * `scene.node_tree` does not exist; the compositor is a node group assigned to
    `scene.compositing_node_group`, and `scene.use_nodes` is deprecated.
  * `CompositorNodeOutputFile` uses `directory` / `file_name` / `file_output_items`
    (not `base_path` / `file_slots`), and its `format.media_type` must be set to
    'IMAGE' before `format.file_format` will accept anything but multilayer EXR.
  * `file_output_items.new(socket_type, name)` takes a socket type from
    ('FLOAT', 'VECTOR', 'RGBA', ...) — 'COLOR' is not one.
  * The File Output node does not append a frame number; the caller sets
    `file_name` per frame, which is what this module does.
  * The Z pass is perpendicular camera-space depth (a plane parallel to the image
    plane reads one constant value across the frame), and unhit pixels read 1e10.
  * `image.pixels` is bottom-up; every array leaving this module is flipped so row
    0 is the top row, which is PNG's order.
"""

import hashlib
import math
import os

import bpy
import mathutils
import numpy as np

from .errors import ArmatureError, G6SubjectMotion, GateFailure

SKY_Z = 1e9


class NonReiterableFrames(ArmatureError):
    """`union_sphere` was handed a frame source it could not walk twice.

    F-ae34fe44. The guard that was here checked `callable(frame_points)`, and its own
    message named the failure it exists to stop — "a single-use iterator would silently
    make the second pass read nothing". **Callability is not re-iterability.** Measured
    against the stubbed bpy/mathutils over two frames spanning a 1.118 bounding radius:
    `union_sphere(lambda: iter(frames))` returns 1.118033988749895, while
    `it = iter(frames); union_sphere(lambda: it)` passes the `callable()` guard and
    returns radius 0.0 — as does a generator FUNCTION closing over a spent source, which
    is the exact shape `world_bounds_over_frames.frames()` uses. `centre` and `half` are
    correct in every case, so nothing anywhere disagrees with the zero, and that radius is
    `auto_radius`'s only size input: a 0.0 sphere puts the orbit camera on the target with
    the subject wrapped around the lens.

    The andon is therefore on the direction the invariant does not bound — the frames each
    pass actually yields are counted and compared, which catches a spent source (zero), a
    partly-spent one (fewer) and a source that changes what it yields (different).

    **It carries an `evidence` dict** (F-197cf096 / F-9fab7829, wave 12), so both of this
    function's refusals reach a halt record with the measurement that fired them rather
    than as a sentence — and the second of them, the non-callable guard, stops being a bare
    `TypeError` that the halt contract records as a crash.

    **It defines no `__init__` of its own** (rule 5, wave 16). It carried
    `self.evidence = evidence or {}`, which manufactured an empty dict for a refusal raised
    with a bare message: the halt line then printed `"evidence": {}` for a refusal that
    carried no receipt, so "no receipt" and "a receipt with nothing in it" became the same
    record. `armature_core.errors.ArmatureError` stores what it is passed and normalises
    nothing; the one exemption is `GateFailure`, whose clauses index into `ev` while they
    measure. A bare-message refusal from this class now reads `"evidence": null`, which is
    the honest record; a refusal that passes a dict is unchanged in both directions, and the
    dict the raising line passed is the object the halt handler reads.
    """


class MeasurementWithoutScene(ArmatureError):
    """A measurement that filters by render visibility was asked to run without a scene.

    F-e2be2262 / F-efe65849, wave 12. `world_bounds(objects, scene=None)` routed to the
    unfiltered primitive and returned the naive bounds under the filtered name; the
    docstring on `world_bounds` records the measurement that showed the two spellings are
    behaviourally identical, and the grep that showed no live caller omits the scene any
    more. The refusal names `unfiltered_world_bounds`, which is what a deliberately naive
    reading is called here, so the message says what to do rather than only what not to.

    Carries an `evidence` dict; a plain refusal writes `gate: None` + `andon` + `clause`.

    **It defines no `__init__` of its own** (rule 5, wave 16). It carried
    `self.evidence = evidence or {}`, which manufactured an empty dict for a refusal raised
    with a bare message: the halt line then printed `"evidence": {}` for a refusal that
    carried no receipt, so "no receipt" and "a receipt with nothing in it" became the same
    record. `armature_core.errors.ArmatureError` stores what it is passed and normalises
    nothing; the one exemption is `GateFailure`, whose clauses index into `ev` while they
    measure. A bare-message refusal from this class now reads `"evidence": null`, which is
    the honest record; a refusal that passes a dict is unchanged in both directions, and the
    dict the raising line passed is the object the halt handler reads.
    """


def scene_fps():
    sc = bpy.context.scene
    return sc.render.fps / (sc.render.fps_base or 1.0)


# --------------------------------------------------------------------------- scene


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def set_frame_rate(scene, fps):
    """Pin the scene's frame rate. MUST be called before `import_glb`.

    glTF stores animation key times in **seconds**, and the importer converts them to
    frames using the scene's rate *at import time*. Setting the rate afterwards does not
    move the keys — they are already on the wrong frames.
    """
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0
    return scene


def import_glb(path, *, expected_fps):
    """Import a GLB and return (mesh_objects, armature_objects, info).

    `expected_fps` makes the ordering requirement executable rather than a comment. It is
    **keyword-only and required** (F-abcb06a8): the signature used to be
    `import_glb(path, expected_fps=None)`, so a caller that omitted it skipped the check
    below entirely and the import proceeded at whatever rate the scene carried.
    `probe_subject.py::probe_one` did exactly that, immediately after `reset_scene()` (factory
    settings, 24 fps) - harmless there because it reads geometry, and proof that nothing
    anywhere required a caller to arm the andon. Wave 3 removed the identical shape from
    `assembly.gate_batch_topology` by making `expected_sources` required and keyword-only;
    this is the same removal. An optional keyword IS a skip flag.

    MEASURED 2026-08-10, and it cost a full debugging pass: importing at Blender's default
    24 fps a 33-key action authored and exported at 16 fps lands the keys on frames 1..49.
    The render then samples frames 1..33 and captures the first **two thirds** of the
    performance — a 0..90° arm raise arrives as a 0..60° one. Every frame is well-formed,
    the action is present with the right number of keys, the arc is smooth and monotonic,
    and **G6 passes**, because the subject genuinely does move. Only the authored ground
    truth disagrees: the union bbox topped out at 1.1013 m where the wrist should reach
    1.1314 m, which is sin(60°)/sin(90°) of the authored rise, to five digits.

    The andon is here, inside the function performing the import, because this is the last
    moment the mistake is still cheap.
    """
    if int(scene_fps()) != int(expected_fps):
        raise G6SubjectMotion(
            f"scene frame rate is {scene_fps()} fps but the shot is {expected_fps} fps, and "
            f"the glTF importer maps key times (seconds) to frames using the rate it finds "
            f"NOW. Importing here would silently place the action on the wrong frames and "
            f"the render would sample a fraction of the performance — call "
            f"`set_frame_rate(scene, fps)` before importing",
            {"gate": "G6", "andon": "G6SubjectMotion",
             "scene_fps": scene_fps(), "expected_fps": expected_fps, "asset": path},
        )
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=path)
    added = [bpy.data.objects[k] for k in bpy.data.objects.keys() if k not in before]

    meshes = [o for o in added if o.type == "MESH"]
    armatures = [o for o in added if o.type == "ARMATURE"]
    info = {
        "objects_imported": len(added),
        "mesh_objects": len(meshes),
        "armature_objects": len(armatures),
        "actions_present": len(bpy.data.actions),
        "total_vertices": int(sum(len(o.data.vertices) for o in meshes)),
    }
    return meshes, armatures, info


def collection_render_flags(scene):
    """(reachable, hidden) collection-name sets, walked from the view layer.

    The layer-collection tree is used rather than `view_layer.objects` because the
    latter is empty until a depsgraph update runs — a freshly linked object is invisible
    to it, which made an earlier version of this predicate reject everything. Walking the
    tree also picks up `exclude`, which plain collection flags do not carry.
    """
    reachable, hidden = set(), set()
    layer = scene.view_layers[0].layer_collection

    def walk(lc, parent_hidden):
        name = lc.collection.name
        reachable.add(name)
        here = parent_hidden or bool(lc.exclude) or bool(lc.collection.hide_render)
        if here:
            hidden.add(name)
        for child in lc.children:
            walk(child, here)

    walk(layer, False)
    return reachable, hidden


def render_visible_meshes(scene, objects):
    """The mesh objects the renderer will actually draw.

    Earned by a G4 firing on 2026-08-10. Blender's glTF importer creates a collection
    named `glTF_not_exported` with `hide_render=True` and drops a 42-vertex Icosphere
    of world radius 1.0 into it. Selecting subject geometry by `type == 'MESH'` swept
    that decoy up, which (a) inflated the auto camera radius so the subject was framed
    too small and (b) made G4's expected bbox far larger than the rendered mask. The
    gate fired; this is the defect it found.

    `visible_get()` is deliberately not used: it reports *viewport* visibility, and a
    collection can be hidden in render while visible in the viewport. Render visibility
    is `hide_render` on the object, plus `hide_render` anywhere up its collection
    ancestry, plus presence in the view layer.
    """
    reachable, hidden = collection_render_flags(scene)
    drawable = reachable - hidden
    keep = []
    for ob in objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        # An object renders if it is reachable through at least one collection that is
        # neither excluded from the view layer nor hidden from render.
        if not any(c.name in drawable for c in ob.users_collection):
            continue
        keep.append(ob)
    return keep


def configure_render(scene, spec, width, height):
    r = spec["render"]
    scene.render.engine = r["engine"]
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = bool(r["film_transparent"])
    scene.render.filter_size = float(r["filter_size"])
    scene.render.use_persistent_data = True

    if r["engine"] == "CYCLES":
        scene.cycles.samples = int(r["samples"])
        scene.cycles.use_denoising = False
        scene.cycles.pixel_filter_type = "BOX"
        scene.cycles.filter_width = float(r["filter_size"])
        scene.cycles.seed = 0
    else:
        scene.eevee.taa_render_samples = int(r["samples"])

    # The frame rate is set BEFORE anything else touches the timeline because glTF stores
    # keyframe times in **seconds**. An action exported at 16 fps and evaluated at Blender's
    # 24 fps default lands its keys on different frames, so a 33-frame arc would be sampled
    # over 22 of them and the last third of the shot would hold the final pose. Nothing
    # errors when that happens; the arc is simply the wrong shape.
    scene.render.fps = int(spec["frames"]["fps"])
    scene.render.fps_base = 1.0

    animation = spec["subject"]["animation"]
    if animation == "per_frame":
        # E03 renders a performance: the frame range spans the shot and `set_scene_frame`
        # advances it per control frame. G6 checks the subject actually moved.
        scene.frame_start = 1
        scene.frame_end = int(spec["frames"]["count"])
    else:
        # E01/E02 render an existing pose, not a performance: the scene frame is pinned so
        # any animation the asset carries cannot move the subject while the camera does.
        # P3 measures normalisation on *static* geometry, and this is what makes it static.
        scene.frame_start = 1
        scene.frame_end = 1
    scene.frame_set(1)
    return scene


def set_scene_frame(scene, frame_index):
    """Advance the timeline to control frame `frame_index` (0-based) and settle it.

    Scene frames are 1-based and control frames are 0-based, so the shot's first control
    frame is scene frame 1 — which is also the frame `configure_render` leaves the scene on
    and the frame the bind pose is authored at.

    The depsgraph update is not optional: `frame_set` schedules the evaluation, and reading
    `matrix_world` or evaluated vertices before it settles returns the *previous* frame's
    values. That failure is silent and would show up as a one-frame lag between the control
    and its own manifest.
    """
    scene.frame_set(1 + int(frame_index))
    bpy.context.view_layer.update()
    return scene.frame_current


# ------------------------------------------------------------------------ geometry


def _evaluated_world_vertices(objects):
    """World-space vertex positions of every mesh object, as one (N, 3) array."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    chunks = []
    for ob in objects:
        ev = ob.evaluated_get(depsgraph)
        try:
            me = ev.to_mesh()
        except RuntimeError:
            continue
        if me is None or len(me.vertices) == 0:
            ev.to_mesh_clear()
            continue
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        M = np.array(ev.matrix_world, dtype=np.float64)
        chunks.append(co @ M[:3, :3].T + M[:3, 3])
        ev.to_mesh_clear()
    if not chunks:
        return np.zeros((0, 3), dtype=np.float64)
    return np.concatenate(chunks, axis=0)


def evaluated_world_vertices(scene, objects):
    """World-space vertices of the objects that will actually RENDER, as one (N, 3) array.

    The public entry point. `_evaluated_world_vertices` is the unfiltered primitive, and
    two tools outside this module import it by its underscore name and apply no visibility
    filter at all, so geometry that will never reach a frame can define a measurement -
    the failure `render_visible_meshes` exists for, reintroduced one import at a time. This
    name takes the scene and filters first, and there is no shape of it that skips the
    filter.
    """
    return _evaluated_world_vertices(render_visible_meshes(scene, objects))


def _points_to_measure(objects, scene):
    """The vertices a measurement should read — filtered whenever a scene is available.

    F-0e29613a. `evaluated_world_vertices(scene, objects)` was introduced so that "there
    is no shape of it that skips the filter", but the split guarded ONE entry point of
    five: `world_bounds`, `world_bounds_over_frames`, `evaluated_geometry_signature` and
    `projected_bbox_px` all still called the unfiltered primitive on whatever object list
    they were handed, so the visibility obligation stayed on every caller of those four —
    the state the public name was created to end. Every production caller measured on this
    tree does pass a `render_visible_meshes` result, so this is a shape rather than a live
    defect; it is also the shape the defect came back through once already, one import at
    a time. This funnel is where a scene turns the obligation back into the module's.

    `scene=None` keeps the caller-filtered contract for the sites that have already
    selected (and for `unfiltered_world_bounds`, the one measurement that is DELIBERATELY
    naive: `probe_subject` reports the difference between the two, so filtering that row
    would silently turn its comparison into a no-op).
    """
    if scene is not None:
        return evaluated_world_vertices(scene, objects)
    return _evaluated_world_vertices(objects)


def _sphere(pts):
    """(center, half_extent, bounding_sphere_radius) over a vertex cloud, or None."""
    if pts.shape[0] == 0:
        return None
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    center = (lo + hi) * 0.5
    half = (hi - lo) * 0.5
    radius = float(np.linalg.norm(pts - center, axis=1).max())
    return center, half, radius


def world_bounds(objects, scene):
    """(center, half_extent, bounding_sphere_radius) over the RENDER-VISIBLE geometry.

    `scene` is REQUIRED and may not be None: this function filters by render visibility
    itself, and there is no shape of it that does not. The deliberately naive measurement
    has its own public name, `unfiltered_world_bounds`.

    **Why omitting `scene` was the naive measurement, and why it is gone** (F-08b5c1b8,
    measured 2026-09-04; signature tightened by F-e2be2262 / F-efe65849, wave 12). With
    `scene` omitted this routed through `_points_to_measure`'s
    `return _evaluated_world_vertices(objects)` and was behaviourally IDENTICAL to
    `unfiltered_world_bounds`: under the bpy stub with `_evaluated_world_vertices`
    monkeypatched to record its argument, `world_bounds(["decoy", "real"])` and
    `unfiltered_world_bounds(["decoy", "real"])` returned the same triple and were handed
    the same object list. So a deliberately naive row and a forgotten `scene=` read the
    same way to a reader — and to the census that polices naive measurement, which keys on
    the private name `_evaluated_world_vertices` appearing in a tool's source, a name that
    spelling never mentions.

    **The claim that used to stand here, corrected in place with the measurement that
    overturned it** (F-e2be2262). This docstring read: "The guard on the other spelling is
    a suite-side ban ... not a refusal here: three call sites in other domains still omit
    it and the signature cannot tighten until they move." Re-derived by grep across
    `tools/` and `tests/` on the wave-12 base (`89269f1`), re-derived and re-anchored on the
    SYMBOL 2026-09-04 (F-0f035830 — four of the five line numbers below had already drifted
    onto unrelated code): every live `world_bounds(...)` call passes a scene —
    `preview_walk.py::main`, `probe_subject.py::probe_one`, `stage_render.py::prepare`,
    `tests/blender/check_visibility.py::filtered_bounds` and
    `tests/test_blender_scene_pure.py::test_world_bounds_filters_by_render_visibility_when_it_is_given_the_scene`
    — and the single omission left, `tools/superseded/render_reference.py::main`, is inside
    `UNFILTERED_BAN_EXEMPT_DIRS` by name and date. **Zero live call sites, not three**, so
    the signature could tighten and now has. It is the second time this same docstring asserted a call-site relationship
    the tree did not have (F-08b5c1b8 corrected `unfiltered_world_bounds`'s "probe_subject
    reports the naive bounds" for the same reason), which is why the correction is written
    here beside the claim rather than substituted for it.

    **The two doors that are still open are named, because this one is not the one
    production uses naively** (F-efe65849). `_points_to_measure` has three public entry
    points; `evaluated_geometry_signature` and `projected_bbox_px` keep their `scene=None`
    default, so the naive door is still open on both.

    **Corrected in place 2026-09-04 (F-0f035830): the four call sites this paragraph named
    as omitting the scene now all PASS it.** The paragraph said they "ARE called with the
    scene omitted" and cited four line numbers, every one of which had drifted onto
    unrelated code. Re-derived by grep and re-anchored on the symbol:
    `check_relift.py::signatures`, `render_start_frame.py::main` and
    `stage_render.py::render_frame` (twice — the geometry signature and the projected bbox)
    are the four sites, and each spells `scene=` explicitly today. The naming half of the
    finding is therefore closed by the call sites themselves; what is left open is the
    SIGNATURE, which still defaults `scene=None` on both doors, so a fifth caller can omit
    it silently. Tightening those two defaults is a separate change with its own callers to
    move; the ban's population half (widening `BOUNDS_FAMILY` to all three doors by
    behaviour) is the tests domain's. What is closed here is the one door whose naive
    spelling had no remaining caller.

    A superseded tool calling the old shape (`tools/superseded/render_reference.py::main`)
    will now raise where it calls. That file is a recorded failure kept runnable for its
    reason, not a route; the exempt list names it, and the refusal it now gets says what to
    call instead.
    """
    if scene is None:
        raise MeasurementWithoutScene(
            "world_bounds measures the geometry that will actually RENDER and needs the "
            "scene to filter with; `scene=None` is the naive measurement wearing the "
            "filtered name. Pass the scene, or call "
            "`blender_scene.unfiltered_world_bounds(objects)` if the naive bounds are what "
            "you want — that name is what a deliberately unfiltered reading is called here",
            {"gate": None, "andon": "MeasurementWithoutScene",
             "clause": "world_bounds_without_scene",
             "n_objects": len(objects) if hasattr(objects, "__len__") else None})
    return _sphere(_points_to_measure(objects, scene))


def unfiltered_world_bounds(objects):
    """`world_bounds` over the objects AS GIVEN — the deliberately naive measurement.

    A public name for the one thing that must not be filtered: a session compares the naive
    bounds against the filtered ones to see what the glTF importer's hidden decoy would have
    done to the framing.

    **Its caller, corrected in place 2026-09-04** (F-08b5c1b8). This docstring said
    "`probe_subject` reports the naive bounds beside the filtered ones". Measured by grep
    across `tools/` and `tests/` on the wave-10 base: the ONLY call site of this name in the
    tree was `tests/blender/check_visibility.py::naive_bounds`, and
    `tools/probe_subject.py::probe_one` still read `naive =
    blender_scene.world_bounds(meshes)` — so the named production consumer did not use the
    name, and the docstring asserted a relationship the tree did not have. (Re-anchored on
    the symbol 2026-09-04, F-0f035830: `probe_subject.py:75` had become a blank line, and
    `probe_subject` was routed onto this name in wave 12 — it calls
    `unfiltered_world_bounds` today.)
    `check_visibility.py` pins that the filtered and naive bounds differ; the instruments
    domain is routing `probe_subject` onto this name in the same wave.

    Naming it here keeps that row honest AND keeps tools out of the private primitive, which
    `tests/test_render_visibility.py` bans.
    """
    return _sphere(_evaluated_world_vertices(objects))


def union_sphere(frame_points):
    """(center, half_extent, radius) over a sequence of per-frame (N, 3) arrays.

    Pure — no bpy — so the arithmetic that decides a shot's framing is testable without a
    render. `frame_points` is a CALLABLE returning a fresh iterator, because the union
    centre is not known until every frame has been seen and the radius is measured about
    THAT centre: the function walks the frames twice rather than keeping them, which is the
    whole point (F-39c191a8). Handing it a plain iterator raises, because a single-use
    iterator would leave the radius pass reading nothing and returning 0.0 — a bounding
    sphere of radius zero around a real subject, with every other check green.

    **Callability was never the invariant** (F-ae34fe44). `lambda: it` over a spent
    iterator is callable and returns radius 0.0; so does a generator function closing over
    a spent source, which is the exact shape `world_bounds_over_frames.frames()` uses. The
    frames each pass yields are counted and compared, and a disagreement raises
    `NonReiterableFrames` with both counts. See that class.

    Returns None when no frame carried geometry.
    """
    if not callable(frame_points):
        # F-9fab7829, wave 12: this was a bare `TypeError`, which the 21-tool halt contract
        # records as "FAILED - an unhandled error" at exit 1. It is a refusal, and the class
        # that already exists for this function's refusals is `NonReiterableFrames`.
        raise NonReiterableFrames(
            "union_sphere takes a CALLABLE returning a fresh iterator of per-frame vertex "
            "arrays, not an iterator: it walks the frames twice (the radius is measured "
            "about a centre that is not known until the first pass ends), and a "
            "single-use iterator would silently make the second pass read nothing",
            {"gate": None, "andon": "NonReiterableFrames",
             "clause": "frame_source_not_callable",
             "given_type": type(frame_points).__name__})

    lo = hi = None
    n_first = 0
    for pts in frame_points():
        n_first += 1
        pts = np.asarray(pts, dtype=np.float64)
        if pts.shape[0] == 0:
            continue
        f_lo, f_hi = pts.min(axis=0), pts.max(axis=0)
        lo = f_lo if lo is None else np.minimum(lo, f_lo)
        hi = f_hi if hi is None else np.maximum(hi, f_hi)
    if lo is None:
        return None

    center = (lo + hi) * 0.5
    half = (hi - lo) * 0.5
    # Measured about the UNION centre over every frame's vertices, so it bounds the whole
    # performance rather than the worst single frame about its own centre.
    radius = 0.0
    n_second = 0
    for pts in frame_points():
        n_second += 1
        pts = np.asarray(pts, dtype=np.float64)
        if pts.shape[0] == 0:
            continue
        radius = max(radius, float(np.linalg.norm(pts - center, axis=1).max()))
    # Counted, not assumed. The frames are counted BEFORE the empty-array skip, so this
    # reads re-iterability itself rather than the geometry that survived it.
    if n_second != n_first:
        raise NonReiterableFrames(
            f"the frame source is not re-iterable: the first pass yielded {n_first} "
            f"frame(s) and the second pass {n_second}. The union radius is measured about "
            f"a centre the first pass computes, so the two passes must see the same "
            f"frames; a spent iterator yields zero and returns a bounding sphere of "
            f"radius 0.0 around a real subject, which is auto_radius's only size input",
            {"gate": None, "andon": "NonReiterableFrames",
             "clause": "frame_source_not_reiterable",
             "n_first_pass": n_first, "n_second_pass": n_second})
    return center, half, radius


def world_bounds_over_frames(scene, objects, count):
    """`world_bounds` over the union of every frame in the shot.

    A performance changes the subject's extent, so bounds taken at the bind pose are the
    wrong input to `auto_radius`. E03's arc is the concrete case: the wire figure is 1.000
    tall in T-pose, and raising the right arm overhead puts the wrist above the head — a
    camera fitted to the bind pose frames the shot too tightly and crops the hand out at
    exactly the moment the experiment is asking about.

    Fitting the union instead makes framing constant across the shot, which matters twice
    over here: the camera is static, so any breathing in the framing would be the subject's
    size changing rather than the camera moving, and that is a second variable inside a
    measurement of one.

    **The frames are walked twice and none is retained** (F-39c191a8). This used to do
    `centers.append(pts)` - appending every frame's FULL evaluated vertex array, held until
    a second loop consumed it - so peak resident memory was the whole shot's geometry at
    once: on the performer (306,110 faces, `_evaluated_world_vertices` returns float64)
    roughly 0.3 GB for an 81-frame shot and 1.2 GB for a 320-frame one, on a rig whose GPU
    work runs under a VRAM watchdog and whose Blender process is doing the render. The
    union radius needs the union centre, which is not known until every frame has been
    seen, so the honest shape is two passes over the frames rather than one pass plus a
    list. The trade is stated rather than hidden: depsgraph evaluation happens twice per
    frame, and resident memory falls from O(frames x vertices) to O(vertices).
    """
    def frames():
        for i in range(count):
            set_scene_frame(scene, i)
            # Through the filtering reader (F-0e29613a): this function already holds the
            # scene, so there was never a reason for it to read the unfiltered primitive.
            pts = evaluated_world_vertices(scene, objects)
            if pts.shape[0]:
                yield pts

    result = union_sphere(frames)
    set_scene_frame(scene, 0)
    return result


def evaluated_geometry_signature(objects, scene=None):
    """A hash of the subject's evaluated world-space vertices at the current frame.

    G6's quantity. Taken from *evaluated* geometry so it follows the imported glTF action,
    parenting and modifiers — the authored intent is irrelevant here, only what the
    renderer is about to draw. Rounded to 1e-9 before hashing so float noise in the
    depsgraph cannot manufacture motion that is not there.

    Pass `scene` and this filters by render visibility itself (F-0e29613a); omit it and
    the caller carries that obligation. See `_points_to_measure`.
    """
    pts = _points_to_measure(objects, scene)
    if pts.shape[0] == 0:
        return "empty"
    return hashlib.sha256(np.round(pts, 9).tobytes()).hexdigest()


# -------------------------------------------------------------------------- camera


def half_fovs(lens_mm, sensor_mm, width, height):
    """Half field-of-view in radians per axis, matching Blender's AUTO sensor fit."""
    if width >= height:
        sx = sensor_mm
        sy = sensor_mm * height / width
    else:
        sy = sensor_mm
        sx = sensor_mm * width / height
    return math.atan(sx * 0.5 / lens_mm), math.atan(sy * 0.5 / lens_mm)


def auto_radius(sphere_radius, lens_mm, sensor_mm, width, height, margin):
    """Orbit radius that fits the subject's bounding sphere with a margin.

    Derived from the subject's own size, and rotation-invariant because it fits a
    sphere: framing does not breathe as the camera goes round, which would otherwise
    put a second variable inside P3's measurement.
    """
    hx, hy = half_fovs(lens_mm, sensor_mm, width, height)
    return float(sphere_radius / math.sin(min(hx, hy)) * margin)


def orbit_azimuth(frame_index, count, start_deg, sweep_deg):
    """Azimuth of one frame. `sweep` is the angle of the closed path: frame `count`
    would coincide with frame 0, so a 360 sweep does not render the first pose twice."""
    return start_deg + sweep_deg * (frame_index / float(count))


def orbit_matrix(target, radius, elevation_deg, azimuth_deg):
    el = math.radians(elevation_deg)
    az = math.radians(azimuth_deg)
    offset = mathutils.Vector(
        (
            radius * math.cos(el) * math.cos(az),
            radius * math.cos(el) * math.sin(az),
            radius * math.sin(el),
        )
    )
    pos = mathutils.Vector(tuple(target)) + offset
    direction = mathutils.Vector(tuple(target)) - pos
    rot = direction.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    return mathutils.Matrix.Translation(pos) @ rot


def make_camera(scene, spec):
    cam_data = bpy.data.cameras.new("armature_cam")
    c = spec["camera"]
    cam_data.lens = float(c["lens_mm"])
    cam_data.sensor_fit = "AUTO"
    cam_data.sensor_width = float(c["sensor_mm"])
    cam_data.clip_start = float(c["clip_start"])
    cam_data.clip_end = float(c["clip_end"])
    cam = bpy.data.objects.new("armature_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def projected_bbox_px(cam, objects, width, height, scene=None):
    """Pixel bbox of every mesh vertex pushed through the camera matrix.

    For a polygonal mesh whose silhouette outline runs along edges between vertices,
    this is the *exact* expected mask bbox — which is what lets G4's tolerance be
    tight enough to bind in both directions.

    Pass `scene` and this filters by render visibility itself (F-0e29613a); omit it and
    the caller carries that obligation. See `_points_to_measure`.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = _points_to_measure(objects, scene)
    if pts.shape[0] == 0:
        return None

    proj = np.array(cam.calc_matrix_camera(depsgraph, x=width, y=height), dtype=np.float64)
    view = np.array(cam.matrix_world.inverted(), dtype=np.float64)
    mvp = proj @ view

    homo = np.concatenate([pts, np.ones((pts.shape[0], 1))], axis=1)
    clip = homo @ mvp.T
    w = clip[:, 3]
    in_front = w > 1e-9
    if not in_front.any():
        return None
    ndc = clip[in_front, :3] / w[in_front, None]

    px = (ndc[:, 0] * 0.5 + 0.5) * width
    py = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * height

    inside = (px >= 0) & (px <= width) & (py >= 0) & (py <= height)
    if not inside.any():
        return None
    px, py = px[inside], py[inside]

    x0 = int(np.clip(np.floor(px.min()), 0, width - 1))
    x1 = int(np.clip(np.ceil(px.max()) - 1, 0, width - 1))
    y0 = int(np.clip(np.floor(py.min()), 0, height - 1))
    y1 = int(np.clip(np.ceil(py.max()) - 1, 0, height - 1))
    return (x0, y0, max(x0, x1), max(y0, y1))


# ---------------------------------------------------------------------- compositor


class CompositorWiring(GateFailure):
    """Gate COMPOSITOR — the render passes are not wired to the sockets they claim.

    The three checks this replaces raised a bare `RuntimeError` with no gate id and no
    evidence (F-ac989919), while their own comment named them as the andon: "a dry_run PASS
    does not prove link sanity — check the topology in code". `ArmatureError` subclasses
    `RuntimeError`, so this was not merely untyped: `stage_render.py::__main__` classifies
    on the family and writes the halt contract's `<PREFIX>_HALT` line before exiting (the
    `GATE_FAILURE` / `GATE_EVIDENCE` prints this used to name were deleted in wave 12;
    corrected in passing), so a bare `RuntimeError` was recorded as "FAILED — an unhandled
    error" at exit 1 rather than as the andon it is, with no gate id and no evidence for an
    orchestrator or a later reader to key on. (Re-anchored on the symbol 2026-09-04,
    F-0f035830: the cited `stage_render.py:508` had become a blank line, and the handler
    catches `BaseException` — the "escaped entirely" reading was the wave-12 shape and is
    corrected here rather than deleted, because exit 1 with `"gate": null` is the same
    false record by a different route.) The
    Depth pass wired to the Alpha socket is the case: the run stops, correctly, and leaves
    nothing behind saying which andon stopped it.
    """

    gate = "COMPOSITOR"


def gate_compositor_wiring(tag, expected_socket, render_layers_name, incoming):
    """Gate COMPOSITOR — ANDON — one link, from the Render Layers node, on the right socket.

    `incoming` is `[(from_node_name, from_socket_name), ...]` for the links arriving at
    this output node. Plain tuples, not bpy proxies, so the topology this gate decides on
    is checkable without a render.
    """
    ev = {"gate": "COMPOSITOR", "andon": "CompositorWiring", "tag": tag,
          "expected_socket": expected_socket,
          "render_layers_node": render_layers_name,
          "n_links": len(incoming),
          "incoming": [[str(a), str(b)] for a, b in incoming]}

    if len(incoming) != 1:
        raise CompositorWiring(
            f"compositor wiring for {tag!r}: expected exactly 1 incoming link, got "
            f"{len(incoming)}. A pass with no link writes a blank channel and a pass with "
            f"two writes whichever the compositor evaluated last; both produce a run whose "
            f"files are all present and correctly sized",
            ev)

    from_node, from_socket = incoming[0]
    ev["from_node"] = str(from_node)
    ev["got_socket"] = str(from_socket)

    if str(from_node) != render_layers_name:
        raise CompositorWiring(
            f"compositor wiring for {tag!r}: source is {from_node!r}, not the Render "
            f"Layers node {render_layers_name!r}", ev)

    if str(from_socket) != expected_socket:
        raise CompositorWiring(
            f"compositor wiring for {tag!r}: connected to socket {from_socket!r}, expected "
            f"{expected_socket!r}. The channel would be written from the wrong pass and "
            f"every file would still open, be the right size, and carry plausible numbers",
            ev)

    ev["verdict"] = (f"{tag} takes its one link from {render_layers_name}."
                     f"{expected_socket}")
    return ev


def setup_passes_and_compositor(scene, exr_dir, need_normal=True):
    """Wire Depth / Normal / Alpha to File Output nodes writing single-layer EXR."""
    vl = scene.view_layers[0]
    vl.use_pass_combined = True
    vl.use_pass_z = True
    vl.use_pass_normal = bool(need_normal)

    ng = bpy.data.node_groups.new("armature_comp", "CompositorNodeTree")
    scene.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.scene = scene

    outputs = {}
    wanted = [("depth", "Depth", "BW", "FLOAT"), ("alpha", "Alpha", "BW", "FLOAT")]
    if need_normal:
        wanted.append(("normal", "Normal", "RGB", "VECTOR"))

    for tag, socket, color_mode, socket_type in wanted:
        node = ng.nodes.new("CompositorNodeOutputFile")
        node.directory = os.path.join(exr_dir, tag)
        node.format.media_type = "IMAGE"
        node.format.file_format = "OPEN_EXR"
        node.format.color_depth = "32"
        node.format.color_mode = color_mode
        node.format.exr_codec = "ZIP"
        node.use_file_extension = True
        node.file_output_items.clear()
        node.file_output_items.new(socket_type, tag)
        ng.links.new(rl.outputs[socket], node.inputs[0])
        outputs[tag] = node

    # A dry_run PASS does not prove link sanity — check the topology in code.
    # `is` is wrong here: bpy hands back a fresh Python proxy per attribute access, so
    # identity comparison on a datablock is always False. Compare names.
    wanted_sockets = {tag: socket for tag, socket, _, _ in wanted}
    for tag, node in outputs.items():
        incoming = [(l.from_node.name, l.from_socket.name)
                    for l in ng.links if l.to_node.name == node.name]
        gate_compositor_wiring(tag, wanted_sockets[tag], rl.name, incoming)
    return outputs


def render_frame(scene, outputs, frame_index, exr_dir):
    """Render one camera position and return the EXR path per channel tag."""
    stem = f"{frame_index:05d}_"
    for node in outputs.values():
        node.file_name = stem
    bpy.ops.render.render(write_still=False)
    return {
        tag: os.path.join(exr_dir, tag, f"{stem}{tag}.exr") for tag in outputs
    }


def read_exr(path):
    """Load an EXR written by the compositor as a top-down (H, W, C) float32 array."""
    img = bpy.data.images.load(path)
    try:
        w, h = img.size
        ch = img.channels
        buf = np.empty(w * h * ch, dtype=np.float32)
        img.pixels.foreach_get(buf)
        arr = buf.reshape(h, w, ch)[::-1]  # bottom-up -> top-down
        return np.ascontiguousarray(arr)
    finally:
        bpy.data.images.remove(img)


def blender_provenance():
    return {
        "version": bpy.app.version_string,
        "version_tuple": list(bpy.app.version),
        "build_hash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
        "build_date": bpy.app.build_date.decode() if isinstance(bpy.app.build_date, bytes) else str(bpy.app.build_date),
        "numpy": np.__version__,
    }
