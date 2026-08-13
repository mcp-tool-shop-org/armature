#!/usr/bin/env python
r"""render_start_frame — the one frame E11 hands an image-to-video model.

    blender -b -P tools\render_start_frame.py -- --glb=<performer.glb>
            --out=<dir> [--frame=0] [--width=832] [--height=480] [--height-frac=0.90]
            --composite=r,g,b --composite-why="..." [--plate=<plate.png> --plate-why="..."]

E11's commission. armature is image-to-video with a GLB instead of an image; this tool is
where the GLB becomes the image. It stages one frame of a performance, lights it, and
writes it at the **generation's own resolution**, so nothing scales, letterboxes or
centre-crops it on the way to the model.

**Why native size, stated as a decision.** E08 handed `WanAnimateToVideo` a 352x1024
portrait reference and measured what the node did to it: `common_upscale(..., "area",
"center")` kept 204 of its 1024 rows — hips and thighs, no head. The Director ruled
letterbox, and E08's own report named the fix this tool implements: a native 832x480 frame
with the figure filling it. Authoring the frame at the model's size removes the whole class
of failure rather than compensating for it.

**The staging is E09/E10's, reused verbatim rather than re-invented** — the same two suns,
the same 0.16/0.16/0.18 world, the same EEVEE + Standard view transform, the same ground
plane, the same 225 deg / 6 deg / 50 mm / 36 mm camera convention. One consequence is worth
naming before anybody reads a result off it: this staging is a grey studio, not a bar. On
the no-control route the start frame is the model's only picture of the world, so a scene
prompt is asking it to *replace* what the image shows rather than to fill a silence. That
is a property of the experiment, recorded here so the report does not have to discover it.

--------------------------------------------------------------------------------
The gates

* **the fps andon** — the scene rate is pinned on an empty scene before the import, or
  `blender_scene.import_glb` raises. glTF key times are SECONDS.
* **Gate WHOLE** (`armature_core.startframe`) — the entire silhouette is inside the frame
  with margin, measured UNCLIPPED on every evaluated vertex. This is the gate the tool
  exists for; the module docstring carries why `solve_camera`'s own `in_frame` cannot do
  it (it is solved over landmarks, which under-report the silhouette).
* **the coverage andon** — the rendered frame differs from an empty plate of the same
  camera, lights and floor with the character hidden. Bounds the other direction: WHOLE
  says nothing left the frame, COVERAGE says somebody is in it. A render of a floor passes
  every count-, size- and legality-based check ever written.
* **the pose andon** — the requested frame index exists inside the action's own range. A
  frame past the end holds the last pose and looks like a perfectly good render.
* **Gate BACKDROP** (`armature_core.startframe`, only when `--plate` is given) — the plate
  really is what stands behind the performer in the submitted file. Nothing else looks
  there: a compositor that failed to wire still writes a right-sized file containing the
  whole performer at healthy coverage, and the provenance still records a plate.

**The plate route, added by E12.** `--plate` replaces the flat void with a picture of a
world, and only that: `--composite` still names the world colour that LIGHTS the scene, the
floor is still geometry, the camera and pose are untouched, and the flat composite is still
rendered and kept beside the submitted one as the counterfactual. The plate must already be
at the frame's exact size — `make_plate.py` does the fit, so the fit is an artifact with a
hash and a recorded transform instead of a resize hidden inside a render.

Prints `RENDER_START_FRAME_OK`. A crashed `blender -b -P` exits 0, so that line is the
contract and `$LASTEXITCODE` proves nothing.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing PNGs and a
sidecar under `outputs/`. Compensator: delete the directory; owner: the executor session.
Inputs are opened read-only.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from armature_core import blender_scene, framing, pngio, startframe as SF  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E11.1"

#: The camera convention, carried verbatim from `render_performer` (E09/E10) so this frame
#: shows the performer from the angle the rest of the arc has been looking at him from.
#: 225 deg is a true three-quarter front on a performer who faces -Y; a profile would
#: occlude one arm and one leg outright.
AZIMUTH_DEG = 225.0
ELEVATION_DEG = 6.0
LENS_MM = 50.0
SENSOR_MM = 36.0

#: The generation's own frame. Both dimensions are divisible by 16 and this is the model
#: family's documented 480p bucket; Gate L checks it again downstream against the graph.
WIDTH, HEIGHT = 832, 480

#: Of the frame, over the performer's own silhouette at this pose — not over a landmark
#: cloud, and not over a whole performance. A composition decision, and it is E08's named
#: lever: its identity result was explicitly a FLOOR because the letterboxed reference put
#: the figure at ~165x480 with a face too small to hold. 0.90 leaves ~24 px of margin top
#: and bottom, which is headroom for Gate WHOLE and room for the model to put a room in.
HEIGHT_FRAC = 0.90
CENTRE_X_FRAC = 0.50
CENTRE_Y_FRAC = 0.50

#: Gate WHOLE's clearance. Small enough that it is not a second composition knob, large
#: enough that a body actually touching the border cannot creep under it.
MARGIN_PX = 8

#: A frame whose subject covers less of it than this is not a picture of the performer.
MIN_SUBJECT_FRAC = 0.01

#: Gate BACKDROP's two thresholds, in 8-bit levels, measured over the master's transparent
#: region only. The submitted composite reaches the plate through Blender's compositor, so
#: the plate is linearised on load and re-encoded by the Standard view transform on save;
#: that round trip is near-identity but not bit-exact, and `TOL` is the room it needs.
#: `MIN_SEPARATION` is the vacuity guard: below it, the plate and the flat fallback are the
#: same picture over that region and a PASS would be proving nothing. Both are calibrated
#: against the measured round trip in `tests/blender/check_plate_composite.py`, not guessed.
PLATE_TOL_255 = 2.0
PLATE_MIN_SEPARATION_255 = 4.0

#: Points handed to the framing solve. The solve is approximate by construction (see
#: `startframe.framing_cloud`); Gate WHOLE then runs on every vertex, so an under-report
#: here costs margin, never correctness.
FRAMING_CLOUD_CAP = 1500


class RenderGate(GateFailure):
    """A gate specific to rendering the start frame."""

    gate = "STARTFRAME"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frame", type=int, default=0,
                    help="which frame of the action to stage, 0-based (argparse eats "
                         "leading minus signs: pass flags as --flag=value)")
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--height", type=int, default=HEIGHT)
    ap.add_argument("--height-frac", type=float, default=HEIGHT_FRAC)
    ap.add_argument("--composite", default=None,
                    help="the submitted RGB composite's background, as linear floats "
                         "`r,g,b`. THE ALPHA LAW: the render is authored RGBA with a real "
                         "alpha channel and this names the deliberate choice composited "
                         "behind it. Required — there is no default, because a default is "
                         "how a grey void becomes accidental (argparse eats leading minus "
                         "signs: pass as --composite=r,g,b)")
    ap.add_argument("--composite-why", default=None,
                    help="one sentence, into the provenance, on why that colour. A choice "
                         "nobody wrote down is indistinguishable from a leftover")
    ap.add_argument("--plate", default=None,
                    help="a PLATE image, already at the generation's exact frame size (see "
                         "make_plate.py), composited BEHIND the authored master instead of "
                         "the flat colour. The flat composite is still rendered and kept as "
                         "the counterfactual, and --composite still names the world that "
                         "LIGHTS the scene, so the plate is the only thing that changes")
    ap.add_argument("--plate-why", default=None,
                    help="one sentence, into the provenance, on why THIS plate")
    ap.add_argument("--floor", type=int, default=1,
                    help="1 draws a ground plane; recorded either way")
    ap.add_argument("--shadow-layer", type=int, default=0,
                    help="1 drops the rendered floor from the picture and keeps only the "
                         "shadow it catches, multiplied onto the plate — so the figure "
                         "rides the WHOLE plate instead of a band above our own floor. "
                         "Needs --floor=1 (the plane must exist to catch anything) and "
                         "--plate. The alternative treatment, an EEVEE shadow catcher, was "
                         "measured shut on this build: see armature_core.startframe."
                         "shadow_ratio")
    ap.add_argument("--floor-material", default="default",
                    choices=("default", "wood"),
                    help="`default` leaves the plane unshaded, as every wave before E12 had "
                         "it — a pale studio slab. `wood` builds a PROCEDURAL dark-wood "
                         "material from shader nodes: no image file is read, so it adds no "
                         "licence surface of any kind")
    return ap.parse_args(argv)


#: The procedural floor, as numbers rather than as a picture. Kept out of the node-building
#: code so the values can be read and changed without a Blender session, and so the one
#: claim that matters for the licence map — *no image is involved* — is checkable by looking
#: at a dict rather than by trusting a comment.
WOOD = {
    "plank_scale": 3.0,        # bands across the plane; low = wide boards
    "grain_scale": 12.0,       # noise driving the grain within a board
    "grain_distortion": 2.2,   # how far the grain bends the bands
    "grain_detail": 6.0,
    "dark_linear": (0.0130, 0.0072, 0.0038),   # linear, in the plate's own key
    "light_linear": (0.0420, 0.0245, 0.0132),
    # Rough and barely specular, because of the CAMERA and not because of taste. The shot
    # sits at 6 degrees of elevation, a grazing view of the floor, and at grazing incidence
    # Fresnel drives the specular lobe toward 1.0: the first values here (roughness 0.55,
    # specular 0.30) measured a floor mean of 0.0999 looking down at 80 degrees and 0.3515
    # at the angle the pipeline actually shoots from — a dark wood washed pale by reflected
    # world. A rough surface scatters that grazing lobe instead of mirroring it.
    "roughness": 0.95,
    "specular": 0.02,
}


def build_wood_material(spec=WOOD):
    """A dark-wood floor material built entirely from procedural nodes.

    **The licence reason this is procedural.** A wood texture is the most ordinary asset in
    the world to download, and the most ordinary way for a CC-BY-NC or a
    research-only-derived image to enter a pipeline that has banned both outright. A shader
    graph of noise and waves has no provenance to check because there is no third-party work
    in it: the andon below refuses to return a material that reads any image at all, so the
    claim on the record is enforced rather than asserted.

    The colours are linear and dark on purpose. The plate this floor sits under is a dim bar;
    a floor lit to studio brightness would read as a lit stage in front of a photograph,
    which is the thing the Director's eye rejected in the band-only composite.
    """
    mat = bpy.data.materials.new("previz_floor_wood")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (spec["plank_scale"],) * 3

    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = spec["grain_scale"]
    grain.inputs["Detail"].default_value = spec["grain_detail"]

    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 1.0
    wave.inputs["Distortion"].default_value = spec["grain_distortion"]
    wave.inputs["Detail"].default_value = spec["grain_detail"]

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*spec["dark_linear"], 1.0)
    ramp.color_ramp.elements[1].color = (*spec["light_linear"], 1.0)

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = spec["roughness"]
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec["specular"]

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grain.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(grain.outputs["Fac"], wave.inputs["Distortion"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    image_nodes = [n.bl_idname for n in nt.nodes if "TexImage" in n.bl_idname
                   or "TexEnvironment" in n.bl_idname]
    if image_nodes:
        raise RenderGate(
            "the procedural floor material reads an image, which is the one thing it exists "
            "not to do: an image carries a licence, and this pipeline bans non-commercial "
            "and research-only assets outright",
            {"image_nodes": image_nodes})
    return mat, {"kind": "procedural", "reads_image_file": False,
                 "node_types": sorted({n.bl_idname for n in nt.nodes}),
                 "spec": {k: list(v) if isinstance(v, tuple) else v
                          for k, v in spec.items()},
                 "licence_surface": ("none — no image, no third-party asset, no downloaded "
                                     "texture; the material is shader nodes only")}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _alpha_channel(path, width, height):
    """The alpha plane of a rendered RGBA PNG, top row first."""
    img = bpy.data.images.load(path)
    try:
        buf = np.empty(width * height * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(height, width, 4)[::-1, :, 3])
    finally:
        bpy.data.images.remove(img)


def _pixels(path, width, height):
    """A rendered PNG as a top-down (H, W, 3) float array.

    `image.pixels` is bottom-up; the flip is what makes the reported bbox agree with the
    coordinates every other tool in this repo — and with the file a human opens — uses.

    Every image Gate BACKDROP compares is read through THIS function, so whatever colour
    convention Blender applies on load applies identically to all of them and the
    differences between them stay meaningful.
    """
    img = bpy.data.images.load(path)
    try:
        buf = np.empty(width * height * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(height, width, 4)[::-1, :, :3])
    finally:
        bpy.data.images.remove(img)


def _image_size(path):
    """(width, height) of an image on disk, without decoding it into numpy."""
    img = bpy.data.images.load(path)
    try:
        return int(img.size[0]), int(img.size[1])
    finally:
        bpy.data.images.remove(img)


def wire_plate_composite(scene, plate_path):
    """Point the render at `master OVER plate`, done by Blender's own compositor.

    Alpha-over in the renderer rather than by hand in byte space, for the same reason the
    flat composite is a second render rather than a numpy fill: the sRGB transfer is the
    renderer's, and the performer's antialiased edge has to blend against the plate in
    linear light or it acquires a fringe. The plate is declared sRGB on load so it is
    linearised going in and the Standard view transform re-encodes it going out.

    **The API here is Blender 5.x's, read off the running build rather than remembered.**
    `Scene.node_tree` and `CompositorNodeComposite` are gone: the scene's compositor is a
    `CompositorNodeTree` datablock hung on `Scene.compositing_node_group`, and its result
    leaves through a group output socket. `Alpha Over` names its sockets now, and its
    premultiply switch is the `Straight Alpha` boolean — left False, because Render Layers
    hands this node an already-premultiplied foreground and converting it again would
    darken every antialiased edge pixel against the plate.

    Sockets are addressed by NAME throughout. The one place this file ever used positional
    socket indices, it was addressing a node whose widget order had to be re-confirmed
    empirically at every size change; names survive a release, positions do not.
    """
    scene.render.film_transparent = True          # the render layer must carry its alpha
    scene.render.use_compositing = True

    tree = bpy.data.node_groups.new("start_frame_plate", "CompositorNodeTree")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = tree

    rl = tree.nodes.new("CompositorNodeRLayers")
    rl.scene = scene
    img = tree.nodes.new("CompositorNodeImage")
    plate_img = bpy.data.images.load(plate_path)
    plate_img.colorspace_settings.name = "sRGB"
    img.image = plate_img
    over = tree.nodes.new("CompositorNodeAlphaOver")
    over.inputs["Straight Alpha"].default_value = False
    out = tree.nodes.new("NodeGroupOutput")

    tree.links.new(img.outputs["Image"], over.inputs["Background"])
    tree.links.new(rl.outputs["Image"], over.inputs["Foreground"])
    tree.links.new(over.outputs["Image"], out.inputs["Image"])
    return plate_img


def action_frame_range():
    """(first, last) scene frames the imported actions actually key, or None.

    The pose andon's quantity. `frame_set` past the end of an action holds the last pose
    and renders it without complaint, so a frame index that misses the performance
    produces a well-formed picture of the wrong moment.
    """
    lo = hi = None
    for act in bpy.data.actions:
        try:
            a, b = act.frame_range
        except (AttributeError, TypeError):
            continue
        lo = a if lo is None else min(lo, a)
        hi = b if hi is None else max(hi, b)
    if lo is None:
        return None
    return float(lo), float(hi)


def main():
    started = time.time()
    a = parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories
    width, height = int(a.width), int(a.height)

    # ---- fps FIRST, on an empty scene, before the import. glTF key times are seconds.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, a.fps)
    meshes, arms, info = blender_scene.import_glb(a.glb, expected_fps=a.fps)

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    # THE ALPHA LAW (CLAUDE.md, the Director's ruling 2026-08-12). `film_transparent` was
    # False here until wave 3, which baked the world background into every authored input
    # as opaque pixels — the grey studio that bled through the E11 probe's frame 0 and is
    # the standing suspect for E08's washed bands. The render below is authored RGBA; the
    # RGB the route actually submits is composited afterwards over a colour named on the
    # command line and recorded in the provenance.
    composite_rgb = SF.composite_colour(a.composite)

    # ---- the plate, checked BEFORE anything renders. A plate at the wrong size would
    # otherwise be discovered after four renders, and a compositor fed a mismatched image
    # scales or tiles it rather than erroring — which is a reframed backdrop nobody chose.
    # `make_plate.py` is what puts a picked still at the frame's exact size.
    backdrop = os.path.abspath(a.plate) if a.plate else None
    if a.shadow_layer and not (backdrop and a.floor):
        raise RenderGate(
            "--shadow-layer needs both --floor=1 and --plate: the plane has to exist to "
            "catch a shadow, and the shadow has to be multiplied onto something",
            {"floor": a.floor, "plate": backdrop})
    if backdrop:
        if not os.path.isfile(backdrop):
            raise RenderGate("no such plate", {"plate": backdrop})
        pw, ph = _image_size(backdrop)
        if (pw, ph) != (width, height):
            raise RenderGate(
                f"the plate is {pw}x{ph} and the frame is {width}x{height}. Fitting is not "
                f"this tool's job precisely so that the fit is an artifact with its own "
                f"hash and a recorded transform: run make_plate.py first",
                {"plate": backdrop, "plate_size": [pw, ph],
                 "frame_size": [width, height]})

    # `render_visible_meshes` and not `type == 'MESH'`: the glTF importer drops a
    # 42-vertex Icosphere into a hidden `glTF_not_exported` collection, and framing against
    # it once pulled a whole shot's camera back (blender_scene, G4, 2026-08-10). Framing
    # here is *tighter* than that shot's, so the decoy would cost more, not less.
    subject = blender_scene.render_visible_meshes(scene, meshes)
    if not subject:
        raise RenderGate("the GLB imported no render-visible mesh", {"glb": a.glb})

    span = action_frame_range()
    scene.frame_start, scene.frame_end = 1, max(1, int(span[1]) if span else 1)
    blender_scene.set_scene_frame(scene, a.frame)
    if span is not None and not (span[0] <= scene.frame_current <= span[1]):
        raise RenderGate(
            f"frame {a.frame} maps to scene frame {scene.frame_current}, outside the "
            f"action's own keyed range {span}. Blender holds the nearest pose and renders "
            f"it with no error, so the start frame would be a well-formed picture of a "
            f"moment the performance never had",
            {"requested_frame": a.frame, "scene_frame": scene.frame_current,
             "action_range": list(span)})

    # ---- the silhouette: every evaluated world vertex the renderer is about to draw.
    verts = blender_scene._evaluated_world_vertices(subject)
    if verts.shape[0] == 0:
        raise RenderGate("the subject evaluates to no vertices at this frame", {})
    cloud = [tuple(map(float, p)) for p in verts]
    solve_cloud = SF.framing_cloud(cloud, cap=FRAMING_CLOUD_CAP)

    sol = framing.solve_camera(solve_cloud, solve_cloud, AZIMUTH_DEG, ELEVATION_DEG,
                               LENS_MM, SENSOR_MM, width, height,
                               height_frac=float(a.height_frac),
                               end_x_frac=CENTRE_X_FRAC, target_y_frac=CENTRE_Y_FRAC)
    target, radius = tuple(sol["target"]), float(sol["radius"])

    # ---- Gate WHOLE, on EVERY vertex and unclipped. The solve above is approximate.
    extent = SF.silhouette_extent(cloud, target, radius, AZIMUTH_DEG, ELEVATION_DEG,
                                  LENS_MM, SENSOR_MM, width, height)
    gate_whole = SF.gate_whole(extent, width, height, MARGIN_PX)

    world = bpy.data.worlds.new("performer")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (
        composite_rgb[0], composite_rgb[1], composite_rgb[2], 1.0)

    key = bpy.data.lights.new("key", type="SUN")
    key.energy = 3.2
    ko = bpy.data.objects.new("key", key)
    scene.collection.objects.link(ko)
    ko.rotation_euler = (math.radians(58), 0.0, math.radians(-25))
    fill = bpy.data.lights.new("fill", type="SUN")
    fill.energy = 1.1
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(65), 0.0, math.radians(150))

    floor_material = {"applied": None}
    gob = None
    if a.floor:
        ground = bpy.data.meshes.new("ground")
        ground.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [],
                           [(0, 1, 2, 3)])
        gob = bpy.data.objects.new("ground", ground)
        scene.collection.objects.link(gob)
        zs = [(o.matrix_world @ Vector(c)).z for o in subject for c in o.bound_box]
        gob.location = (0.0, 0.0, min(zs))
        if a.floor_material == "wood":
            mat, floor_material = build_wood_material()
            ground.materials.append(mat)
            floor_material["applied"] = "ground"
        else:
            floor_material = {"applied": None, "kind": "default",
                              "note": ("no material assigned; Blender's default surface — "
                                       "the pale studio slab every wave before E12 had")}

    cam_data = bpy.data.cameras.new("start_cam")
    cam_data.lens, cam_data.sensor_fit, cam_data.sensor_width = LENS_MM, "AUTO", SENSOR_MM
    cam_data.clip_start, cam_data.clip_end = 0.01, 100.0
    cam = bpy.data.objects.new("start_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.matrix_world = blender_scene.orbit_matrix(Vector(target), radius,
                                                  ELEVATION_DEG, AZIMUTH_DEG)

    # ---- (1) THE AUTHORED MASTER, RGBA. `film_transparent` makes the WORLD background
    # alpha=0 while the floor plane — real geometry — stays opaque, so what becomes
    # transparent is exactly the void the law is about and nothing else.
    # Under --shadow-layer the floor is not IN the picture — it exists only to catch what the
    # figure throws onto it. So it is hidden for every render that describes the frame, and
    # shown again below only for the two that measure the shadow.
    if a.shadow_layer:
        gob.hide_render = True

    rgba_path = os.path.join(out, "start_frame_rgba.png")
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = rgba_path
    bpy.ops.render.render(write_still=True)

    alpha_plane = _alpha_channel(rgba_path, width, height)
    gate_alpha = SF.gate_alpha(float((alpha_plane < 0.5).mean()), composite_rgb,
                               a.composite_why, master_path=rgba_path)

    # ---- (2) THE FLAT COMPOSITE, RGB, colour-managed by Blender over the chosen
    # background rather than composited by hand in byte space. Same camera, same lights,
    # same pose — only the film's treatment of the void differs between (1) and (2).
    # With no plate this IS the submitted image. With a plate it is kept anyway, as the
    # counterfactual Gate BACKDROP measures the plate's arrival against.
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"
    flat_path = os.path.join(out, "start_frame_flat.png" if backdrop else "start_frame.png")
    scene.render.filepath = flat_path
    bpy.ops.render.render(write_still=True)

    # ---- the empty plate: same camera, same lights, same floor, character hidden.
    # (An "empty plate" in the VFX sense — the background-only render. Not `--plate`.)
    for o in subject + arms:
        o.hide_render = True
    plate_path = os.path.join(out, "empty_plate.png")
    scene.render.filepath = plate_path
    bpy.ops.render.render(write_still=True)
    for o in subject + arms:
        o.hide_render = False

    # COVERAGE is measured on the FLAT composite in both routes. Against a scene-bearing
    # plate the empty-plate difference would count the whole backdrop as subject, and the
    # gate that says "somebody is in the frame" would pass on a picture of an empty bar.
    frame_px = _pixels(flat_path, width, height)
    plate_px = _pixels(plate_path, width, height)
    diff = np.abs(frame_px - plate_px).max(axis=2) > (1.0 / 255.0)
    frac = float(diff.mean())

    # ---- (2b) THE AUTHORED SHADOW LAYER. Two renders of the floor alone — one with the
    # figure casting onto it, one without — and their ratio in linear light is the shadow,
    # free of the floor's own colour and of its lighting gradient. The floor itself never
    # reaches the picture; only what the figure did to it does.
    shadow = None
    if a.shadow_layer:
        gob.hide_render = False
        for o in subject + arms:
            o.hide_render = True
        lit_path = os.path.join(out, "shadow_lit.png")
        scene.render.filepath = lit_path
        bpy.ops.render.render(write_still=True)
        for o in subject + arms:
            o.hide_render = False
        cast_path = os.path.join(out, "shadow_cast.png")
        scene.render.filepath = cast_path
        bpy.ops.render.render(write_still=True)
        gob.hide_render = True

        ratio = SF.shadow_ratio(_pixels(cast_path, width, height),
                                _pixels(lit_path, width, height))
        # Where the figure itself stands, the "cast" render is the figure, not the floor, so
        # its ratio is meaningless — and the figure is opaque over it anyway. Held at 1 so
        # no silhouette-shaped artefact is baked into the backdrop.
        ratio[alpha_plane > 0.0] = 1.0
        shadowed = SF.apply_shadow(_pixels(backdrop, width, height), ratio)
        shadowed_path = os.path.join(out, "plate_shadowed.png")
        pngio.write_png(shadowed_path,
                        np.clip(shadowed * 255.0, 0, 255).round().astype(np.uint8))
        darkened = ratio < 0.99
        shadow = {
            "treatment": "authored shadow layer (ratio of two floor renders, in linear)",
            "why_not_a_shadow_catcher": (
                "measured 2026-08-12 on this build: Object.is_shadow_catcher exists and "
                "EEVEE ignores it — the catcher render came back byte-identical to the "
                "ordinary opaque floor (mean alpha 0.7105664 both) — and Cycles is not in "
                "this build's engine list. The alternative the spec allows was shut, so "
                "this is the branch it left"),
            "lit_reference": {"path": lit_path, "sha256": _sha256(lit_path)},
            "cast_reference": {"path": cast_path, "sha256": _sha256(cast_path)},
            "shadowed_plate": {"path": shadowed_path, "sha256": _sha256(shadowed_path)},
            "darkened_fraction_of_frame": float(darkened.any(axis=2).mean()),
            "min_ratio": float(ratio.min()), "mean_ratio_where_darkened": (
                float(ratio[darkened].mean()) if darkened.any() else None),
            "held_at_one_over_the_figure": True,
            "eps": SF.SHADOW_FLOOR_EPS,
        }
        backdrop_for_composite = shadowed_path
    else:
        backdrop_for_composite = backdrop

    # ---- (3) THE SUBMITTED COMPOSITE when a plate was named: the same master, alpha-over
    # the plate, through the compositor. Everything the performer is lit by is unchanged;
    # what fills the void is the only thing that moves.
    frame_path, gate_backdrop = flat_path, None
    if backdrop:
        wire_plate_composite(scene, backdrop_for_composite)
        frame_path = os.path.join(out, "start_frame.png")
        scene.render.filepath = frame_path
        bpy.ops.render.render(write_still=True)

        void = alpha_plane < 0.5
        sub_px = _pixels(frame_path, width, height)
        # Against the image the compositor was actually handed. Under --shadow-layer that is
        # the SHADOWED plate: comparing to the unshadowed one would report the shadow as a
        # failure to deliver the plate, which is the opposite of what happened.
        back_px = _pixels(backdrop_for_composite, width, height)
        gate_backdrop = SF.gate_backdrop(
            void_vs_plate_255=float(np.abs(sub_px[void] - back_px[void]).mean() * 255.0),
            plate_vs_flat_255=float(np.abs(back_px[void] - frame_px[void]).mean() * 255.0),
            transparent_fraction=float(void.mean()),
            why=a.plate_why, tol_255=PLATE_TOL_255,
            min_separation_255=PLATE_MIN_SEPARATION_255,
            plate=backdrop_for_composite,
            plate_sha256=_sha256(backdrop_for_composite))
    ev_cov = {
        "gate": "COVERAGE", "min_fraction": MIN_SUBJECT_FRAC, "subject_fraction": frac,
        "empty_plate": plate_path,
        "note": ("fraction of pixels differing from an empty-plate render of the same "
                 "camera, lights and floor with the character hidden. It INCLUDES the "
                 "figure's shadow on the ground plane, so its bbox bounds subject+shadow "
                 "and is a diagnostic; Gate WHOLE is what bounds the body")}
    if frac < MIN_SUBJECT_FRAC:
        raise RenderGate(
            f"the render differs from the empty plate over only {frac:.5f} of the image "
            f"(floor {MIN_SUBJECT_FRAC}); the performer is not in it, and a frame of an "
            f"empty floor would condition the whole generation", ev_cov)
    ev_cov["verdict"] = f"subject covers {frac:.4f} of the frame"

    ys, xs = np.nonzero(diff)
    rendered_bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]

    provenance = {
        "tool": "render_start_frame", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "source": {"glb": os.path.abspath(a.glb), "sha256": _sha256(a.glb),
                   "frame_index": a.frame, "scene_frame": scene.frame_current,
                   "action_frame_range": list(span) if span else None,
                   "pose_signature":
                       blender_scene.evaluated_geometry_signature(subject)},
        "resolution": [width, height], "fps": a.fps, "floor_drawn": bool(a.floor),
        "floor_material": floor_material,
        "staging": {
            "inherited_from": ("render_performer (E09/E10) for lights, lens and framing; "
                               "the world background is NO LONGER inherited — see alpha"),
            "world_background": list(composite_rgb) + [1.0],
            "key_sun_energy": 3.2, "fill_sun_energy": 1.1,
            "engine": "BLENDER_EEVEE", "view_transform": "Standard",
            "consequence": ("on the no-control route this frame is the model's only "
                            "picture of the world, so whatever it shows is what the prompt "
                            "must either keep or replace. What it shows is now a recorded "
                            "choice rather than an inherited studio grey"),
            "residual_not_changed": ("the floor plane is still lit by the two studio suns "
                                     "and reads pale. Only the world void moved under the "
                                     "alpha law; re-lighting the floor would be a second "
                                     "variable this wave did not authorise")},
        "alpha": {
            "law": ("CLAUDE.md, the Director's ruling 2026-08-12 — authored image inputs "
                    "carry alpha, never a baked void"),
            "authored_master": {"path": rgba_path, "sha256": _sha256(rgba_path),
                                "color_mode": "RGBA", "film_transparent": True},
            "submitted_composite": {
                "path": frame_path, "color_mode": "RGB",
                "backdrop": "plate" if backdrop else "flat colour",
                "film_transparent": bool(backdrop),
                "background_linear_rgb": list(composite_rgb),
                "why": a.composite_why,
                "composited_by": (
                    ("Blender's compositor, alpha-over the plate on a second render of the "
                     "identical scene — the plate linearised on load and re-encoded by the "
                     "Standard view transform, so the performer's edge blends in linear "
                     "light rather than by hand in byte space")
                    if backdrop else
                    ("Blender's own colour management on a second render of the identical "
                     "scene, not by hand in byte space — the sRGB transfer is the "
                     "renderer's, not this tool's"))},
            "flat_counterfactual": {
                "path": flat_path,
                "role": ("the image this route would have submitted with no plate; kept as "
                         "Gate BACKDROP's separation reference and as the COVERAGE source"
                         if backdrop else "this run submitted the flat composite itself")},
            "plate": ({"path": backdrop, "sha256": _sha256(backdrop),
                       "size": [width, height], "why": a.plate_why,
                       "note": ("the world the performer stands in. It changes the void "
                                "only: the lights, the floor geometry, the camera and the "
                                "pose are the flat route's")}
                      if backdrop else None),
            "shadow_layer": shadow,
            "gate_ALPHA": gate_alpha,
            "gate_BACKDROP": gate_backdrop},
        "camera": {
            "azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG,
            "lens_mm": LENS_MM, "sensor_mm": SENSOR_MM,
            "target": list(target), "radius": radius,
            "position": list(framing.camera_position(target, radius,
                                                     ELEVATION_DEG, AZIMUTH_DEG)),
            "height_frac_requested": float(a.height_frac),
            "centre_x_frac": CENTRE_X_FRAC, "centre_y_frac": CENTRE_Y_FRAC,
            "solver_achieved": sol["achieved"], "solver_in_frame": sol["in_frame"],
            "framing_cloud": {"n_vertices": len(cloud), "n_solved_against": len(solve_cloud),
                              "cap": FRAMING_CLOUD_CAP}},
        "import_info": info,
        "outputs": {
            "start_frame_rgba": {"path": rgba_path, "sha256": _sha256(rgba_path),
                                 "role": "the authored master (RGBA)"},
            "start_frame": {"path": frame_path, "sha256": _sha256(frame_path),
                            "role": "the submitted composite (RGB)"},
            "start_frame_flat": ({"path": flat_path, "sha256": _sha256(flat_path),
                                  "role": "the flat-colour composite, not submitted"}
                                 if backdrop else None),
            "empty_plate": {"path": plate_path, "sha256": _sha256(plate_path)}},
        "measured": {
            "silhouette_extent_px": extent,
            "rendered_subject_bbox_px": rendered_bbox,
            "rendered_bbox_includes_shadow": True,
            "subject_fraction": frac},
        "gates": {
            "fps_ordering": {"verdict": "PASS", "detail": "import_glb(expected_fps)"},
            "POSE": {"verdict": "PASS", "scene_frame": scene.frame_current,
                     "action_frame_range": list(span) if span else None},
            "WHOLE": gate_whole,
            "ALPHA": gate_alpha,
            "BACKDROP": gate_backdrop or {"verdict": "NOT APPLICABLE",
                                          "detail": "no --plate; the void is a flat colour"},
            "COVERAGE": ev_cov},
        "elapsed_s": time.time() - started,
    }
    side = os.path.join(out, "start_frame_provenance.json")
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(provenance, fh, indent=2)

    print("RENDER_START_FRAME_OK " + json.dumps({
        "frame": frame_path, "sha256": provenance["outputs"]["start_frame"]["sha256"][:32],
        "resolution": [width, height], "scene_frame": scene.frame_current,
        "figure_height_frac": round(gate_whole["height_frac"], 4),
        "smallest_margin_px": round(min(gate_whole["margins_px"].values()), 1),
        "subject_fraction": round(frac, 4),
        "gate_WHOLE": gate_whole["verdict"], "gate_COVERAGE": ev_cov["verdict"],
        "gate_ALPHA": gate_alpha["verdict"],
        "gate_BACKDROP": (gate_backdrop or {}).get("verdict", "NOT APPLICABLE"),
        "provenance": side}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("RENDER_START_FRAME_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
