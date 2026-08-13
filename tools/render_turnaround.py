#!/usr/bin/env python
"""render_turnaround — an RGBA-true N-view turnaround of a static character GLB.

    blender -b -P tools\\render_turnaround.py -- --glb=<textured.glb> --out=<dir>

Note the `--key=value` form: argparse eats leading minus signs, and `--azimuth-start=-90`
is the shape that survives.

S03 Task A's instrument. A turnaround is the reference kit a route is *handed* when it has
to bind identity, so this tool's whole product is eight pictures of one character that a
route can actually consume — which means **authored RGBA, per the Director's ruling of
2026-08-12**, and not the thing that ruling was made against.

**What it is not.** It is not `stage_render` (control channels — depth/normal/mask/edge —
orbiting a subject, no shaded pass), and it is not `render_performer` or
`render_start_frame` (both shade and light beautifully, both stand at ONE azimuth, both
render a *performance* frame). The orbit machinery lives in `blender_scene`
(`orbit_azimuth`, `orbit_matrix`, `auto_radius`) and the alpha law lives in
`armature_core.turnaround`; this file is the place they meet. Nothing here is re-invented:
the staging — two suns, the 0.16/0.16/0.18 world, EEVEE, the Standard view transform, the
50 mm lens on a 36 mm sensor — is E09/E10's, carried through `render_start_frame` verbatim.

Prints `RENDER_TURNAROUND_OK`. A crashed `blender -b -P` exits 0, so that line is the
contract and `$LASTEXITCODE` proves nothing.

--------------------------------------------------------------------------------
The gates

* **Gate ALPHA, per view** (`turnaround.gate_view_alpha`) — the view carries transparent
  pixels AND opaque ones. The defect it exists for is the reason S03 exists: the eight
  views of `facet_E33/turn_final/` are RGBA files whose alpha extrema are (255, 255), a
  flat grey void baked into the RGB, and no check anywhere reported it.
* **Gate TURN** (`turnaround.gate_set_distinct`) — as many views as were asked for, and no
  two byte-identical. A camera that never moved writes a well-formed set of N copies of the
  front view, and every per-view gate passes on every one of them.
* **Gate WHOLE, per view** (`startframe.gate_whole`) — the silhouette is inside the frame,
  measured **unclipped**. A turnaround's widest view is not its narrowest, so a radius that
  frames the front can still amputate the arms at three-quarter; this is the check that
  binds the axis the height fit does not.
* **Gate CROP, per view** (`turnaround.gate_view_crop`) — S04, and it arms on the
  `--ortho` path. Gate WHOLE reads the *projected decimated cloud*, which is the same
  measurement the scale solve was fitted to, so it cannot see a silhouette wider than the
  samples the solve saw. Gate CROP reads the **rendered alpha**. Border contact there is
  the failure the shared-scale solve does not bound.

Gate ALPHA and Gate TURN run after the frames and **before the manifest**, because the
manifest is what makes a run look finished (`stage_render`'s doctrine, and why its G2 sits
exactly there). All of them `raise`; none is an `assert` (deleted by -O / PYTHONOPTIMIZE=1)
and none takes a skip flag.

--------------------------------------------------------------------------------
`--ortho`: the sprite shot-set (S04)

Absent the flag nothing below applies and the perspective path above is what runs. The
branch itself is `turnaround.projection_plan` and nothing else, so the untouched-when-absent
claim is a property of one testable object rather than of a careful reading of this loop.

With the flag, the camera is parallel and **one `ortho_scale` is shared by every view**,
solved from the LARGEST silhouette over the whole azimuth set. Constant scale across the
sheet is the sprite property — a per-view solve would give eight correctly-framed cells that
cannot be laid beside each other, which is the one thing a shot-set is for. Screen size
under parallel projection does not depend on distance, so the radius keeps only a
positional role and is set to a clipping-safe standoff derived from the subject's own
bounding sphere rather than from a constant in metres.

**`predicted_vs_measured` rides each view as a diagnostic and gates nothing.** It sets the
projector's extent against the rendered alpha's bbox — two independent measurements of one
silhouette, and the pair that exposes a wrong ortho aspect convention, which no gate here
can see. It does NOT see a flipped row order, at any aspect: the solve centres the figure,
and a centred box maps to itself under a vertical flip to within a pixel. Nothing derived
from the box can see that, so the row order is settled by the orientation calibration and
by `_measure_alpha_plane`'s own test rather than by a per-view number. No calibrated
tolerance for the delta exists on this rig, so it is reported and the Director's eye reads
it.

--------------------------------------------------------------------------------
Why the radius is solved and not typed in

`auto_radius` fits the subject's bounding SPHERE, which is rotation-invariant and correct
for a control orbit whose framing must not breathe. It is wrong for a *portrait* turnaround
frame: fitting a sphere into a 352-wide, 1024-tall frame is bounded by the narrow axis and
spends two thirds of the frame on empty air. So the radius here is solved on the subject's
own projected HEIGHT — the axis that barely moves as the camera goes round — to a target
fraction of the frame, and the width is left to vary and gated per view.

The solve runs through `framing.project`, the same projector `startframe.silhouette_extent`
and Gate WHOLE use, rather than a closed form derived here. A hand-derived formula that
disagreed with the projector by a few percent would produce a composition that passes its
own arithmetic and fails the gate, and the disagreement would be invisible.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is writing PNGs and a manifest under `outputs/`. Compensator:
delete the directory; owner: the executor session. Inputs are opened read-only —
`E:\\AI\\training` and `E:\\AI\\facet` are not in git, have no revert, and are never
written to.
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

from armature_core import blender_scene, framing  # noqa: E402
from armature_core import startframe as SF  # noqa: E402
from armature_core import turnaround as TA  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "S04.1"

#: The staging, inherited verbatim from E09/E10 via `render_start_frame`. Every one of
#: these is a decision and belongs in the report rather than in a reader's assumptions.
LENS_MM = 50.0
SENSOR_MM = 36.0
KEY_ENERGY, FILL_ENERGY = 3.2, 1.1
#: The world colour LIGHTS the scene; it does not appear in the picture, because
#: `film_transparent` makes the world background alpha 0. Linear RGB.
WORLD_LINEAR = (0.16, 0.16, 0.18)

#: The frame. 352x1024 is `turn_final`'s size, measured on the old set this one is rendered
#: to stand beside — matching it is what makes the Task-B comparison a comparison rather
#: than a resize.
WIDTH, HEIGHT = 352, 1024

#: Of the frame height, over the widest view. Derived from the old set by measurement
#: (`turn_final` figures span rows 86..937 of 1024 = 0.831), so the new figure is drawn at
#: the same scale as the one it is compared against.
HEIGHT_FRAC = 0.831

#: The performer faces -Y — MEASURED, not assumed: `rig_manifest_auto.json` records
#: `facing_y_sign: -1.0` from the feet-primary instrument with the head cross-check
#: agreeing. A camera at azimuth 270 therefore stands in front of him, which is view 0.
AZIMUTH_START_DEG = 270.0
SWEEP_DEG = 360.0
ELEVATION_DEG = 0.0

#: Gate WHOLE's margin. The figure must clear every border by this much.
MARGIN_PX = 2.0

#: ORTHO standoff, in multiples of the subject's OWN bounding-sphere radius. A global
#: constant must not govern a local feature, so this is a fraction of the structure's own
#: size rather than a distance in metres — the same subject at half the scale stands off
#: half as far, and the clearance in front of the near surface is 3 sphere-radii either way.
#: Parallel projection makes screen size independent of distance, so this number cannot
#: affect the composition; it only has to keep the whole subject in front of the lens, which
#: Gate WHOLE's `n_behind` clause is what actually enforces.
ORTHO_STANDOFF_SPHERES = 4.0


class RenderTurnaroundGate(ArmatureError):
    """The turnaround could not be composed at all."""


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", type=int, default=8)
    ap.add_argument("--azimuth-start", type=float, default=AZIMUTH_START_DEG,
                    help="degrees; view 0 sits here. 270 puts the camera in front of a "
                         "performer who faces -Y")
    ap.add_argument("--sweep", type=float, default=SWEEP_DEG,
                    help="degrees of the CLOSED path; view `views` would coincide with 0")
    ap.add_argument("--elevation", type=float, default=ELEVATION_DEG)
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--height", type=int, default=HEIGHT)
    ap.add_argument("--height-frac", type=float, default=HEIGHT_FRAC)
    ap.add_argument("--lens", type=float, default=LENS_MM)
    ap.add_argument("--sensor", type=float, default=SENSOR_MM)
    ap.add_argument("--fps", type=int, default=16,
                    help="pinned before the import because glTF key times are SECONDS; a "
                         "static subject has no action, and this keeps that true rather "
                         "than assumed")
    ap.add_argument("--prefix", default="turn")
    ap.add_argument("--ortho", action="store_true",
                    help="parallel projection with ONE ortho_scale shared by every view "
                         "— the sprite shot-set. Absent, the perspective path runs "
                         "unchanged (S04)")
    return ap.parse_args(argv)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _measure_alpha_plane(plane_bottom_up):
    """Extrema, transparent fraction and the subject's TOP-DOWN bbox of an alpha plane.

    Takes the plane as Blender hands it back — **row 0 at the BOTTOM of the picture** —
    and flips it, because `framing.project` returns y increasing downward and
    `startframe.mask_bbox` reads its input row-major from the top.

    Split out of `_alpha_stats` so the flip is testable without Blender, which is the only
    way it gets tested at all. It needs to be: the extrema and the transparent fraction are
    orientation-invariant and would never notice, a bbox is not, and an unflipped one makes
    Gate CROP name `top` when the figure was amputated at the `bottom` — a gate that fires
    correctly and lies about where. **Neither the predicted-vs-measured delta nor any
    crown-position probe can catch this**, and that was measured rather than assumed: the
    solve centres the figure, so at `height_frac` 0.831 in 1024 rows the flipped box
    differs from the true one by ONE pixel and every quantity derived from it agrees.

    That leaves the premise "`Image.pixels` is bottom-up" carrying the flip on its own, so
    it is measured directly by the orientation calibration rather than trusted.

    The subject mask is `alpha >= TRANSPARENT_BELOW`, the module's existing convention, so
    the bbox and the reported transparent fraction partition the same frame.
    """
    a = plane_bottom_up[::-1]
    counts = np.rint(a * 255.0).astype(np.int32)
    mask = a >= TA.TRANSPARENT_BELOW
    return {
        "alpha_min": int(counts.min()),
        "alpha_max": int(counts.max()),
        "transparent_fraction": float((a < TA.TRANSPARENT_BELOW).mean()),
        "subject_bbox": SF.mask_bbox(mask.tolist()),
        "subject_pixels": int(mask.sum()),
    }


def _alpha_stats(path, width, height):
    """`_measure_alpha_plane` of the WRITTEN PNG's alpha channel.

    Measured off the file rather than off the render buffer. The buffer is what the
    renderer believes it produced; the file is what a route is handed, and the two differ
    exactly when the file format or the colour-mode setting drops the channel — which is
    the failure this whole tool is aimed at.
    """
    img = bpy.data.images.load(path)
    try:
        buf = np.empty(width * height * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        plane = buf.reshape(height, width, 4)[..., 3].copy()
    finally:
        bpy.data.images.remove(img)
    return _measure_alpha_plane(plane)


def _border_contact(bbox, width, height):
    """Which frame borders the rendered subject touches. A measurement, not a verdict."""
    if bbox is None:
        return {"subject_bbox_px": None,
                "note": "no subject pixels; border contact is undefined"}
    x0, y0, x1, y1 = (int(v) for v in bbox)
    clear = {"left": x0, "right": (int(width) - 1) - x1,
             "top": y0, "bottom": (int(height) - 1) - y1}
    return {"subject_bbox_px": [x0, y0, x1, y1], "clearance_px": clear,
            "touching": sorted(s for s, c in clear.items() if c <= 0)}


def _predicted_vs_measured(extent, bbox):
    """The projector's silhouette against the rendered alpha's — DIAGNOSTIC, gates nothing.

    Two independent measurements of one silhouette: `silhouette_extent` projects a
    decimated point cloud through `framing.project`, and the bbox comes off the written
    PNG's alpha. Nothing else in this tool compares them, and a wrong ortho aspect
    convention is invisible to every gate here while showing up in this delta immediately —
    on a SQUARE frame it is invisible even here, which is what the non-square calibration
    render is for. A flipped row order is invisible to this delta too, at any aspect, and
    `_orientation_probe` is what binds it.

    No calibrated threshold for acceptable disagreement exists on this rig. Anti-aliasing
    widens the rendered edge, the 0.5 alpha threshold pulls it back, and the decimated
    cloud under-reports the true silhouette — three effects of unmeasured relative size.
    So the numbers are reported and the Director's eye reads them; inventing a tolerance
    here would be a pass condition this tool could move.
    """
    if bbox is None:
        return {"measured_px": None,
                "note": "no subject pixels rendered; nothing to compare"}
    x0, y0, x1, y1 = (int(v) for v in bbox)
    pred = {k: float(extent[k]) for k in ("x0", "x1", "y0", "y1")}
    meas = {"x0": x0, "x1": x1, "y0": y0, "y1": y1}
    return {
        "predicted_px": {k: round(v, 2) for k, v in pred.items()},
        "measured_px": meas,
        "delta_px": {k: round(meas[k] - pred[k], 2) for k in pred},
        "note": ("measured minus predicted. The rendered silhouette is expected to be the "
                 "WIDER of the two (decimation under-reports, anti-aliasing over-reports), "
                 "so negative on x0/y0 and positive on x1/y1 is the ordinary sign pattern"),
    }


def solve_radius_for_height(cloud, target, azimuths, elevation_deg, lens_mm, sensor_mm,
                            width, height, height_frac):
    """Orbit radius whose WIDEST-view projected height is `height_frac` of the frame.

    Bisected through `framing.project` — the projector Gate WHOLE also uses — so the
    composition this returns and the composition the gate measures cannot disagree. The
    maximum is taken over every azimuth the run will actually render, so a view that
    happens to project taller than view 0 (perspective: the near shoulder at three-quarter
    sits closer to the lens than the front shoulder does) still fits.
    """
    def tallest(radius):
        best = 0.0
        for az in azimuths:
            ext = SF.silhouette_extent(cloud, target, radius, az, elevation_deg,
                                       lens_mm, sensor_mm, width, height)
            best = max(best, (ext["y1"] - ext["y0"]) / float(height))
        return best

    lo, hi = 1e-3, 1.0
    for _ in range(200):                      # grow until the figure is small enough
        if tallest(hi) <= height_frac:
            break
        hi *= 2.0
    else:                                     # pragma: no cover - unreachable in practice
        raise RenderTurnaroundGate(
            f"no orbit radius up to {hi:g} draws the subject at or below "
            f"{height_frac:g} of the frame height")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if tallest(mid) > height_frac:
            lo = mid
        else:
            hi = mid
    return hi


def solve_ortho_scale_for_height(cloud, target, radius, azimuths, elevation_deg,
                                 width, height, height_frac):
    """The ONE ortho_scale whose TALLEST view is `height_frac` of the frame.

    The sprite property is that this number is shared. A per-view solve would frame each
    cell beautifully and destroy the sheet: the figure would be the same height in all
    eight, so a character who is genuinely narrower from the side would be silently
    enlarged until he matched his own front view. Solving once over the maximum makes the
    largest view the one that fits and lets every other cell be honestly smaller.

    Bisected through `framing.project` for the same reason the radius solve is — a closed
    form derived here would be a second implementation of Blender's AUTO ortho fit, and a
    few percent of disagreement produces a composition that passes its own arithmetic and
    fails the gate with nothing pointing at why. Monotone for the same reason too: a larger
    span draws the subject smaller.

    `radius` is passed through only because the projector needs a camera position; under
    parallel projection it cannot move the result, and the run's own manifest records the
    invariance rather than asserting it.
    """
    def tallest(scale):
        best = 0.0
        for az in azimuths:
            ext = SF.silhouette_extent(cloud, target, radius, az, elevation_deg,
                                       None, None, width, height, ortho_scale=scale)
            best = max(best, (ext["y1"] - ext["y0"]) / float(height))
        return best

    lo, hi = 1e-6, 1.0
    for _ in range(200):                      # grow the span until the figure is small
        if tallest(hi) <= height_frac:
            break
        hi *= 2.0
    else:                                     # pragma: no cover - unreachable in practice
        raise RenderTurnaroundGate(
            f"no ortho_scale up to {hi:g} draws the subject at or below {height_frac:g} "
            f"of the frame height")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if tallest(mid) > height_frac:
            lo = mid
        else:
            hi = mid
    return hi


def main():
    started = time.time()
    a = parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)           # scripts create their own output directories
    width, height = int(a.width), int(a.height)

    azimuths = TA.orbit_azimuths(a.views, a.azimuth_start, a.sweep)

    # ---- fps FIRST, on an empty scene, before the import. glTF key times are seconds.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, a.fps)
    meshes, arms, info = blender_scene.import_glb(a.glb, expected_fps=a.fps)
    if not meshes:
        raise RenderTurnaroundGate(f"{a.glb} imported no mesh objects; nothing to render")

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"

    # The subject is STATIC: the scene frame is pinned so anything the asset carries cannot
    # move it while the camera does. A turnaround of a walking figure is eight views of
    # eight different poses, and nothing downstream could tell that from a bad mesh.
    scene.frame_start = scene.frame_end = 1
    scene.frame_set(1)

    world = bpy.data.worlds.new("turnaround")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (*WORLD_LINEAR, 1.0)

    key = bpy.data.lights.new("key", type="SUN")
    key.energy = KEY_ENERGY
    ko = bpy.data.objects.new("key", key)
    scene.collection.objects.link(ko)
    ko.rotation_euler = (math.radians(58), 0.0, math.radians(-25))
    fill = bpy.data.lights.new("fill", type="SUN")
    fill.energy = FILL_ENERGY
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(65), 0.0, math.radians(150))

    # NO floor. A ground plane is real geometry and renders opaque, so it would fill the
    # lower frame with exactly the kind of baked, non-transparent backdrop this tool exists
    # to stop shipping — and `turn_final`, the set this stands beside, has none either.

    subject = [o for o in meshes]
    verts = blender_scene._evaluated_world_vertices(subject)
    lo = verts.min(axis=0)
    hi = verts.max(axis=0)
    target = ((lo[0] + hi[0]) * 0.5, (lo[1] + hi[1]) * 0.5, (lo[2] + hi[2]) * 0.5)
    cloud = SF.framing_cloud(verts)

    # ---- THE BRANCH, and the only one. Everything that differs between a perspective
    # turnaround and an ortho shot-set is decided by `projection_plan` and read out below.
    plan = TA.projection_plan(a.ortho, a.lens, a.sensor)

    if plan["projection"] == TA.ORTHOGRAPHIC:
        # Standoff from the subject's OWN bounding sphere: parallel projection cannot let
        # this number reach the composition, so its only job is keeping the whole figure in
        # front of the lens — which Gate WHOLE's `n_behind` clause is what enforces.
        sphere_radius = float(
            np.linalg.norm(verts - np.asarray(target, dtype=verts.dtype), axis=1).max())
        radius = sphere_radius * ORTHO_STANDOFF_SPHERES
        ortho_scale = solve_ortho_scale_for_height(
            cloud, target, radius, azimuths, a.elevation, width, height, a.height_frac)
    else:
        sphere_radius, ortho_scale = None, None
        radius = solve_radius_for_height(cloud, target, azimuths, a.elevation, a.lens,
                                         a.sensor, width, height, a.height_frac)

    cam_data = bpy.data.cameras.new("turn_cam")
    cam_data.type = plan["blender_camera_type"]
    cam_data.lens, cam_data.sensor_fit, cam_data.sensor_width = a.lens, "AUTO", a.sensor
    if ortho_scale is not None:
        cam_data.ortho_scale = ortho_scale
    cam_data.clip_start, cam_data.clip_end = 0.01, 1000.0
    cam = bpy.data.objects.new("turn_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    # THE ALPHA LAW (CLAUDE.md, the Director's ruling 2026-08-12). `film_transparent`
    # makes the WORLD background alpha 0 while the subject's own geometry stays opaque,
    # so what becomes transparent is exactly the void the law is about and nothing else.
    # There is no composite here on purpose: this tool's deliverable IS the RGBA master,
    # and the RGB each consuming route submits is that route's own recorded choice.
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"

    views = []
    for i, az in enumerate(azimuths):
        cam.matrix_world = blender_scene.orbit_matrix(Vector(target), radius,
                                                      a.elevation, az)
        path = os.path.join(out, f"{a.prefix}_{i}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if not os.path.isfile(path):          # pragma: no cover - Blender-side failure
            raise RenderTurnaroundGate(f"view {i} rendered no file at {path}")

        m = _alpha_stats(path, width, height)
        extent = SF.silhouette_extent(cloud, target, radius, az, a.elevation, a.lens,
                                      a.sensor, width, height, ortho_scale=ortho_scale)
        rec = {
            "view": i, "azimuth_deg": az, "path": path,
            "bytes": os.path.getsize(path), "sha256": _sha256(path),
            "gate_ALPHA": TA.gate_view_alpha(i, m["alpha_min"], m["alpha_max"],
                                             m["transparent_fraction"], path),
            "gate_WHOLE": SF.gate_whole(extent, width, height, MARGIN_PX),
            "subject_bbox_px": (list(m["subject_bbox"])
                                if m["subject_bbox"] is not None else None),
            "subject_pixels": m["subject_pixels"],
            "predicted_vs_measured": _predicted_vs_measured(extent, m["subject_bbox"]),
        }
        # Gate CROP arms on the ORTHO path. It is the shared-scale solve's andon, and
        # Task A's structural invariant is that the perspective path is untouched when the
        # flag is absent — a new raising gate there would be a behaviour change to it. The
        # same measurement is taken on both paths either way and rides the manifest, so
        # ruling that CROP should arm on perspective too needs no re-run to decide.
        if plan["projection"] == TA.ORTHOGRAPHIC:
            rec["gate_CROP"] = TA.gate_view_crop(
                i, m["subject_bbox"], width, height, path,
                alpha_threshold=TA.TRANSPARENT_BELOW)
        else:
            rec["gate_CROP"] = {
                "gate": "CROP", "view": i, "armed": False,
                "why_not_armed": ("the shared-scale solve this andon bounds does not run "
                                  "on the perspective path; the measurement is reported"),
                "border_contact": _border_contact(m["subject_bbox"], width, height),
            }
        views.append(rec)

    # ---- the set-level andon, after the frames and BEFORE the manifest.
    gate_turn = TA.gate_set_distinct(views, a.views)

    manifest = {
        "tool": "render_turnaround", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "numpy": np.__version__,
        "source": {"glb": os.path.abspath(a.glb), "sha256": _sha256(a.glb),
                   "bytes": os.path.getsize(a.glb)},
        "import_info": info,
        "resolution": [width, height],
        "camera": {
            "type": "orbit", "n_views": int(a.views),
            "projection": plan["projection"],
            "blender_camera_type": plan["blender_camera_type"],
            "shared_across_views": plan["shared_across_views"],
            "radius_role": plan["radius_role"],
            "azimuth_start_deg": float(a.azimuth_start), "sweep_deg": float(a.sweep),
            "azimuths_deg": azimuths, "elevation_deg": float(a.elevation),
            "lens_mm": plan["lens_mm"], "sensor_mm": plan["sensor_mm"],
            "sensor_fit": "AUTO",
            "ortho_scale": ortho_scale,
            "ortho_scale_solved_for": (None if ortho_scale is None else {
                "height_frac": float(a.height_frac),
                "over": "the tallest projected view of the set",
                "shared": True,
                "why": ("one scale across every cell is the sprite property; a per-view "
                        "solve frames each cell correctly and destroys the sheet, because "
                        "a genuinely narrower profile view would be enlarged to match the "
                        "front view's height"),
                "subject_sphere_radius": sphere_radius,
                "standoff_spheres": ORTHO_STANDOFF_SPHERES,
            }),
            "radius": radius, "radius_solved_for": (None if ortho_scale is not None else {
                "height_frac": float(a.height_frac),
                "over": "the tallest projected view of the set",
                "why": ("a bounding-sphere fit is bounded by the narrow axis of a "
                        "352x1024 frame and would spend most of it on empty air; the "
                        "height is the axis that barely moves as the camera goes round"),
            }),
            "target": list(target),
        },
        "subject": {
            "animation": "static",
            "bbox_lo": [float(v) for v in lo], "bbox_hi": [float(v) for v in hi],
            "n_vertices": int(verts.shape[0]),
            "facing": ("-Y, MEASURED in rig_manifest_auto.json (facing_y_sign -1.0, feet "
                       "primary, head cross-check agrees) on this GLB's rigged descendant"),
        },
        "staging": {
            "inherited_from": ("E09/E10 via render_start_frame — the same two suns, the "
                               "same world, EEVEE, Standard view transform"),
            "world_linear_rgb": list(WORLD_LINEAR),
            "key_sun_energy": KEY_ENERGY, "fill_sun_energy": FILL_ENERGY,
            "engine": "BLENDER_EEVEE", "view_transform": "Standard",
            "floor_drawn": False,
            "floor_why": ("a ground plane is opaque geometry and would bake a non-"
                          "transparent backdrop into the lower frame, which is the defect "
                          "this tool exists to stop shipping"),
        },
        "alpha": {
            "law": "authored image inputs carry alpha, never a baked void",
            "master": {"color_mode": "RGBA", "film_transparent": True},
            "composite": ("NONE submitted by this tool. The deliverable is the RGBA "
                          "master; the RGB composite is the consuming route's own "
                          "recorded choice, per the law"),
        },
        "views": views,
        "gates": {"TURN": gate_turn,
                  "ALPHA": [v["gate_ALPHA"]["verdict"] for v in views],
                  "WHOLE": [v["gate_WHOLE"]["verdict"] for v in views],
                  "CROP": [v["gate_CROP"].get("verdict", "NOT ARMED (perspective path)")
                           for v in views]},
        "elapsed_s": round(time.time() - started, 2),
    }
    with open(os.path.join(out, "turnaround_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)

    for v in views:
        pvm = v["predicted_vs_measured"].get("delta_px")
        print(f"view {v['view']} az={v['azimuth_deg']:7.2f}  "
              f"alpha={tuple(v['gate_ALPHA']['alpha_extrema'])}  "
              f"transparent={v['gate_ALPHA']['transparent_fraction']:.4f}  "
              f"h={v['gate_WHOLE']['height_frac']:.4f} w={v['gate_WHOLE']['width_frac']:.4f}"
              + (f"  bbox={v['subject_bbox_px']}" if v["subject_bbox_px"] else "")
              + (f"  d(meas-pred)={pvm}" if pvm else ""))
    print(f"projection {plan['projection']}   radius {radius:.6f}"
          + ("" if ortho_scale is None else f"   ortho_scale {ortho_scale:.6f} (shared)")
          + f"   {gate_turn['verdict']}")
    print("RENDER_TURNAROUND_OK")


if __name__ == "__main__":
    main()
