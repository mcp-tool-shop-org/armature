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

from .errors import G6SubjectMotion

SKY_Z = 1e9


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


def import_glb(path, expected_fps=None):
    """Import a GLB and return (mesh_objects, armature_objects, info).

    `expected_fps` makes the ordering requirement executable rather than a comment.

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
    if expected_fps is not None and int(scene_fps()) != int(expected_fps):
        raise G6SubjectMotion(
            f"scene frame rate is {scene_fps()} fps but the shot is {expected_fps} fps, and "
            f"the glTF importer maps key times (seconds) to frames using the rate it finds "
            f"NOW. Importing here would silently place the action on the wrong frames and "
            f"the render would sample a fraction of the performance — call "
            f"`set_frame_rate(scene, fps)` before importing",
            {"scene_fps": scene_fps(), "expected_fps": expected_fps, "asset": path},
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


def world_bounds(objects):
    """(center, half_extent, bounding_sphere_radius) over evaluated geometry."""
    pts = _evaluated_world_vertices(objects)
    if pts.shape[0] == 0:
        return None
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    center = (lo + hi) * 0.5
    half = (hi - lo) * 0.5
    radius = float(np.linalg.norm(pts - center, axis=1).max())
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
    """
    lo = hi = None
    pts_max_r = 0.0
    centers = []
    for i in range(count):
        set_scene_frame(scene, i)
        pts = _evaluated_world_vertices(objects)
        if pts.shape[0] == 0:
            continue
        f_lo, f_hi = pts.min(axis=0), pts.max(axis=0)
        lo = f_lo if lo is None else np.minimum(lo, f_lo)
        hi = f_hi if hi is None else np.maximum(hi, f_hi)
        centers.append(pts)
    if lo is None:
        return None
    center = (lo + hi) * 0.5
    half = (hi - lo) * 0.5
    # The sphere is measured about the UNION centre, over every frame's vertices, so it
    # bounds the whole performance rather than the worst single frame about its own centre.
    for pts in centers:
        pts_max_r = max(pts_max_r, float(np.linalg.norm(pts - center, axis=1).max()))
    set_scene_frame(scene, 0)
    return center, half, pts_max_r


def evaluated_geometry_signature(objects):
    """A hash of the subject's evaluated world-space vertices at the current frame.

    G6's quantity. Taken from *evaluated* geometry so it follows the imported glTF action,
    parenting and modifiers — the authored intent is irrelevant here, only what the
    renderer is about to draw. Rounded to 1e-9 before hashing so float noise in the
    depsgraph cannot manufacture motion that is not there.
    """
    pts = _evaluated_world_vertices(objects)
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


def projected_bbox_px(cam, objects, width, height):
    """Pixel bbox of every mesh vertex pushed through the camera matrix.

    For a polygonal mesh whose silhouette outline runs along edges between vertices,
    this is the *exact* expected mask bbox — which is what lets G4's tolerance be
    tight enough to bind in both directions.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = _evaluated_world_vertices(objects)
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
        linked = [l for l in ng.links if l.to_node.name == node.name]
        if len(linked) != 1:
            raise RuntimeError(
                f"compositor wiring for {tag!r}: expected exactly 1 incoming link, got {len(linked)}"
            )
        link = linked[0]
        if link.from_node.name != rl.name:
            raise RuntimeError(
                f"compositor wiring for {tag!r}: source is {link.from_node.name!r}, "
                f"not the Render Layers node"
            )
        if link.from_socket.name != wanted_sockets[tag]:
            raise RuntimeError(
                f"compositor wiring for {tag!r}: connected to socket "
                f"{link.from_socket.name!r}, expected {wanted_sockets[tag]!r}"
            )
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
