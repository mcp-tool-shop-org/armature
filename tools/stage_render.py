#!/usr/bin/env python
"""stage_render — the control-sequence exporter.

Consumes a shot spec (JSON) plus a GLB and writes a directory of per-frame control
channels with a manifest that makes the run reproducible.

Run it headless, through PowerShell (Git Bash mangles the paths):

    blender -b -P tools\\stage_render.py -- --spec=<spec.json> --out=<run dir>

Note the `--key=value` form: argparse eats leading minus signs, and `--views=-30,0,30`
is the shape that survives.

--------------------------------------------------------------------------------
Where the gates live, and why here

`run_export` is the function that performs the write. **G1 is its first statement**,
before the backend is loaded, before the asset is opened, and before the output
directory exists — so an illegal frame cannot produce a single byte. G2 runs after the
frames and *before* the manifest, because the manifest is what makes a run look
finished. G4 runs inside the per-frame loop. All of them `raise`; none of them is an
`assert` (deleted by -O / PYTHONOPTIMIZE=1) and none takes a skip argument.

**No number a gate compares against arrives through this tool.** G4's tolerance used to:
`g4_tol = spec['gates']['g4_tolerance_px']`, passed straight into `g4_bbox_sanity` with
no range check, no type check and no record of the value used. `normalise_spec` validated
nothing under `gates` — measured 2026-09-03, `g4_tolerance_px: 100000` was accepted and
the gate then did not fire on facet's own recorded defect, so a spec with one extra zero
would have rendered and submitted a control sequence whose mask was not the subject, with
a full per-frame `g4_deltas_px` record and a manifest that looked finished. Note the
asymmetry that made it invisible: too-SMALL values still fired, so the only unbounded
direction was the one that DISARMED the gate. The constant now lives in
`gates.G4_TOLERANCE_PX`, `g4_bbox_sanity` takes no tolerance argument at all, a spec that
still names the key is refused by `normalise_spec`, and the manifest reads the value and
its provenance back off the gate rather than restating them.

Nothing here is chained behind a shell operator, because a chain can walk past a
failing exit code.

This module imports cleanly **without** bpy. That is deliberate: it lets the gate tests
drive the real write path and observe a gate firing before Blender could ever be
reached, rather than testing a copy of the gate.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is creating one new directory under `outputs/`.
Compensator: `delete_output_dir(run_dir)`, below. Owner: the executor session that
made the run. Source assets are opened read-only and never modified — `E:\\AI\\training`
is not in git and has no revert, so nothing is written there, ever.
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from armature_core import channels as ch  # noqa: E402
from armature_core import gates, openpose, pngio, shotspec  # noqa: E402
from armature_core.errors import (  # noqa: E402
    ArmatureError,
    GateFailure,
    NotInsideBlender,
    SpecError,
)

TOOL_VERSION = "E01.1"

#: Directories written per requested channel. `depth` produces both normalisations
#: plus their difference; which one ships is not this tool's decision (P3).
CHANNEL_DIRS = {
    "depth": ("depth_perframe", "depth_pershot", "p3_diff"),
    "normal": ("normal",),
    "mask": ("mask",),
    "edge": ("edge",),
    "pose": ("pose",),
}


# --------------------------------------------------------------------- compensator


def delete_output_dir(run_dir):
    """The named compensator for this tool's only irreversible act."""
    run_dir = os.path.abspath(run_dir)
    if not os.path.isdir(run_dir):
        return False
    marker = os.path.join(run_dir, ".armature_run")
    if not os.path.isfile(marker):
        raise ArmatureError(
            f"refusing to delete {run_dir}: it carries no .armature_run marker, so "
            f"this tool did not create it"
        )
    shutil.rmtree(run_dir)
    return True


# ------------------------------------------------------------------------- backend


class BlenderBackend:
    """The real backend. Imports bpy only when instantiated."""

    name = "blender"

    def __init__(self):
        try:
            from armature_core import blender_scene
        except ImportError as exc:  # pragma: no cover - exercised outside Blender
            raise NotInsideBlender(
                "stage_render needs Blender's python (bpy). Run it as: "
                "blender -b -P tools/stage_render.py -- --spec=... --out=..."
            ) from exc
        self._bs = blender_scene
        self._state = {}

    def prepare(self, spec, asset_path, width, height, work_dir, need_normal):
        bs = self._bs
        scene = bs.reset_scene()
        # The frame rate is pinned BEFORE the import, not by `configure_render` after it:
        # glTF key times are in seconds and the importer resolves them against whatever
        # rate the scene carries at that moment. See `import_glb`, which raises if this
        # ordering is ever broken again.
        bs.set_frame_rate(scene, spec["frames"]["fps"])
        imported_meshes, armatures, info = bs.import_glb(
            asset_path, expected_fps=spec["frames"]["fps"]
        )
        if not imported_meshes:
            raise SpecError(f"{asset_path} imported no mesh objects; nothing to render")
        bs.configure_render(scene, spec, width, height)

        # Only geometry that will actually render may define the framing or G4's
        # expected bbox. See blender_scene.render_visible_meshes for what fired.
        meshes = bs.render_visible_meshes(scene, imported_meshes)
        if not meshes:
            raise SpecError(
                f"{asset_path}: every imported mesh is hidden from render "
                f"({[o.name for o in imported_meshes]})"
            )
        info["mesh_objects_render_visible"] = len(meshes)
        info["mesh_objects_excluded_from_render"] = sorted(
            o.name for o in imported_meshes if o.name not in {m.name for m in meshes}
        )

        # A performance changes the subject's extent, so a camera fitted to the bind pose
        # would crop the shot exactly where the motion is. Fit the union of every frame.
        animation = spec["subject"]["animation"]
        if animation == "per_frame":
            bounds = bs.world_bounds_over_frames(scene, meshes, spec["frames"]["count"])
        else:
            # `scene=` passed, so the filtering happens inside the reader rather than
            # depending on this caller having filtered `meshes` fifteen lines above. The
            # bare form is the spelling `tests/test_render_visibility.py` bans: it is
            # correct here only because of a fact a reader has to go and check, and the
            # day the two lines drift the framing silently includes a hidden decoy.
            bounds = bs.world_bounds(meshes, scene=scene)
        if bounds is None:
            raise SpecError(f"{asset_path} has no evaluated geometry")
        center, half, sphere_r = bounds

        cam = bs.make_camera(scene, spec)
        c = spec["camera"]
        measured_center = [float(v) for v in center]
        if c["target"] != "bbox_center":
            center = np.asarray(c["target"], dtype=np.float64)
        radius = c["radius"]
        if radius == "auto":
            radius = bs.auto_radius(
                sphere_r, c["lens_mm"], c["sensor_mm"], width, height, c["fit_margin"]
            )
        radius = float(radius)
        if radius + sphere_r >= float(c["clip_end"]):
            raise SpecError(
                f"camera clip_end {c['clip_end']} is closer than the subject "
                f"(radius {radius:.3f} + sphere {sphere_r:.3f})"
            )

        exr_dir = os.path.join(work_dir, "master")
        outputs = bs.setup_passes_and_compositor(scene, exr_dir, need_normal=need_normal)

        self._state = dict(
            scene=scene, cam=cam, meshes=meshes, armatures=armatures,
            outputs=outputs, exr_dir=exr_dir, width=width, height=height,
            center=center, radius=radius, spec=spec, need_normal=need_normal,
            animation=animation,
        )
        return {
            "import": info,
            "subject_animation": animation,
            "bounds_fitted_over": (
                f"union of {spec['frames']['count']} frames" if animation == "per_frame"
                else "the bind pose"
            ),
            "subject_bbox_center": measured_center,
            "camera_target_resolved": [float(v) for v in center],
            "camera_target_source": (
                "spec.camera.target (pinned)" if c["target"] != "bbox_center"
                else "measured bbox centre"
            ),
            "subject_bbox_half_extent": [float(v) for v in half],
            "subject_sphere_radius": float(sphere_r),
            "camera_radius_resolved": radius,
            "armature_names": [a.name for a in armatures],
        }

    def render_frame(self, index, count):
        st = self._state
        bs, spec = self._bs, st["spec"]

        # The subject moves BEFORE anything is measured about it: the geometry signature,
        # the projected bbox and the render itself must all describe the same frame.
        scene_frame = None
        if st["animation"] == "per_frame":
            scene_frame = bs.set_scene_frame(st["scene"], index)
        # `scene=` passed, so the render-visibility filtering happens inside the reader
        # rather than depending on this caller having filtered `meshes` in `prepare`. The
        # bare form is the spelling `tests/test_render_visibility.py` bans, and it is the
        # spelling this line carried: correct only because of a fact a reader has to go and
        # check, and wrong the day the two drift.
        signature = bs.evaluated_geometry_signature(st["meshes"], scene=st["scene"])

        c = spec["camera"]
        az = bs.orbit_azimuth(index, count, c["azimuth_start_deg"], c["azimuth_sweep_deg"])
        st["cam"].matrix_world = bs.orbit_matrix(
            st["center"], st["radius"], c["elevation_deg"], az
        )
        bs.bpy.context.view_layer.update()

        paths = bs.render_frame(st["scene"], st["outputs"], index, st["exr_dir"])
        z = bs.read_exr(paths["depth"])[..., 0].astype(np.float64)
        alpha = bs.read_exr(paths["alpha"])[..., 0].astype(np.float64)
        normal_world = (
            bs.read_exr(paths["normal"])[..., :3].astype(np.float64)
            if st["need_normal"] else None
        )
        cam_rot = np.array(st["cam"].matrix_world.to_3x3().normalized(), dtype=np.float64)
        projected = bs.projected_bbox_px(st["cam"], st["meshes"], st["width"],
                                         st["height"], scene=st["scene"])

        return {
            "z": z,
            "alpha": alpha,
            "normal_world": normal_world,
            "cam_rot_3x3": cam_rot,
            "projected_bbox": projected,
            "azimuth_deg": float(az),
            "scene_frame": scene_frame,
            "geometry_signature": signature,
            "camera_matrix": [list(map(float, row)) for row in st["cam"].matrix_world],
            "master_paths": {k: os.path.relpath(v, os.path.dirname(st["exr_dir"]))
                             for k, v in paths.items()},
        }

    def provenance(self):
        return self._bs.blender_provenance()


# -------------------------------------------------------------------------- writer


def _sha256_dir(root, names):
    return {n: shotspec.sha256_file(os.path.join(root, n)) for n in names}


def run_export(spec, out_dir, backend=None):
    """Render a shot spec into `out_dir`. Returns the manifest dict.

    Raises GateFailure (G1/G2/G4/G5) or SpecError. Nothing is written before G1.

    The only step that precedes G1 is filling the spec's defaults, which touches no
    filesystem — it exists so a caller handing over a raw dict gets a named SpecError
    instead of a KeyError from somewhere in the middle of the render loop.
    """
    spec = shotspec.normalise_spec(spec)
    width = spec["resolution"]["width"]
    height = spec["resolution"]["height"]
    count = spec["frames"]["count"]

    # ---- G1 · ANDON — generator legality. First statement; nothing exists yet.
    profile = gates.g1_generator_legality(width, height, count, spec["generator"])

    requested = list(spec["channels"])
    if "pose" in requested:
        # Not a soft warning: emitting a skeleton needs a convention this repo has
        # not retrieved. openpose.require_drawing_convention() raises with the reason.
        openpose.require_drawing_convention()

    need_normal = ("normal" in requested) or ("edge" in requested)

    asset_path, asset_sha = shotspec.resolve_asset(spec)

    backend = backend if backend is not None else BlenderBackend()

    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)  # scripts create their own output directories
    with open(os.path.join(out_dir, ".armature_run"), "w", encoding="utf-8") as fh:
        fh.write(f"{TOOL_VERSION}\n")

    emitted = []
    for channel in requested:
        emitted.extend(CHANNEL_DIRS[channel])
    for d in emitted:
        os.makedirs(os.path.join(out_dir, d), exist_ok=True)

    scene_info = backend.prepare(spec, asset_path, width, height, out_dir, need_normal)

    names = shotspec.frame_names(count, "png")

    z_frames, mask_frames, per_frame = [], [], []

    # ---- render pass: everything that does not need shot-wide statistics
    for i in range(count):
        f = backend.render_frame(i, count)
        z = np.asarray(f["z"], dtype=np.float64)
        alpha = np.asarray(f["alpha"], dtype=np.float64)
        if z.shape != (height, width):
            raise ArmatureError(
                f"frame {i}: depth buffer is {z.shape}, expected {(height, width)}"
            )
        mask = ch.mask_from_alpha(alpha)
        mask_bbox = ch.bbox_of(mask)

        # ---- G4 · bbox sanity, inside the loop that writes the frame.
        #      **No tolerance argument.** One used to be read out of the spec here and
        #      handed over unvalidated; the number lives in `gates.G4_TOLERANCE_PX` and no
        #      caller may widen it, this one included. The module docstring records what a
        #      settable one cost.
        deltas = gates.g4_bbox_sanity(i, mask_bbox, f["projected_bbox"], width, height)

        rec = {
            "frame": i,
            "azimuth_deg": f.get("azimuth_deg"),
            "scene_frame": f.get("scene_frame"),
            "geometry_signature": f.get("geometry_signature"),
            "camera_matrix": f.get("camera_matrix"),
            "mask_px": int(mask.sum()),
            "mask_bbox": list(mask_bbox) if mask_bbox else None,
            "projected_bbox": list(f["projected_bbox"]) if f["projected_bbox"] else None,
            "g4_deltas_px": deltas,
            "alpha_soft_fraction": ch.alpha_binarity(alpha),
            "master_paths": f.get("master_paths"),
        }

        extent = ch.depth_extent(z, mask)
        if extent is None:
            raise ArmatureError(f"frame {i}: mask is non-empty but carries no finite depth")
        rec["z_min"], rec["z_max"] = extent
        rec["z_range"] = extent[1] - extent[0]

        if "mask" in requested:
            pngio.write_png(os.path.join(out_dir, "mask", names[i]), mask, bit_depth=1)

        n_cam = None
        if need_normal:
            n_cam = ch.world_normals_to_camera(f["normal_world"], f["cam_rot_3x3"])
            if "normal" in requested:
                pngio.write_png(
                    os.path.join(out_dir, "normal", names[i]),
                    ch.encode_normal(n_cam, mask),
                    bit_depth=8,
                )

        if "edge" in requested:
            edge, ediag = ch.derive_edge(
                z, n_cam, mask,
                spec["edge"]["depth_rel_threshold"], spec["edge"]["normal_angle_deg"],
            )
            pngio.write_png(os.path.join(out_dir, "edge", names[i]), edge, bit_depth=8)
            rec["edge"] = ediag

        z_frames.append(z)
        mask_frames.append(mask)
        per_frame.append(rec)

    # ---- depth pass: needs the whole shot's extent, so it runs after the loop
    p3 = None
    if "depth" in requested:
        mins = [r["z_min"] for r in per_frame]
        maxs = [r["z_max"] for r in per_frame]
        measured_min, measured_max = float(min(mins)), float(max(maxs))

        # A pinned window lets two arms share one tonal scale; see shotspec.normalise_spec.
        # The MEASURED extent is recorded either way, so a pinned window that no longer fits
        # its shot is visible in the manifest rather than silently clipping.
        window = spec["depth"]["window"]
        pinned = window != "per_shot"
        shot_min, shot_max = (float(window[0]), float(window[1])) if pinned else (
            measured_min, measured_max
        )
        p3 = {
            "shot_z_min": shot_min,
            "shot_z_max": shot_max,
            "shot_z_range": shot_max - shot_min,
            "window_source": "spec.depth.window (pinned)" if pinned else "measured per-shot",
            "measured_z_min": measured_min,
            "measured_z_max": measured_max,
            "measured_within_window": shot_min <= measured_min and measured_max <= shot_max,
            "per_frame": [],
        }
        for i in range(count):
            z, mask = z_frames[i], mask_frames[i]
            d_pf = ch.normalize_depth(z, mask, per_frame[i]["z_min"], per_frame[i]["z_max"])
            d_ps = ch.normalize_depth(z, mask, shot_min, shot_max)
            pngio.write_png(
                os.path.join(out_dir, "depth_perframe", names[i]), ch.encode_u8(d_pf), 8
            )
            pngio.write_png(
                os.path.join(out_dir, "depth_pershot", names[i]), ch.encode_u8(d_ps), 8
            )
            diff, stats = ch.normalization_difference(d_pf, d_ps, mask)
            pngio.write_png(os.path.join(out_dir, "p3_diff", names[i]), ch.encode_u8(diff), 8)
            stats["frame"] = i
            stats["z_min"] = per_frame[i]["z_min"]
            stats["z_max"] = per_frame[i]["z_max"]
            stats["z_range"] = per_frame[i]["z_range"]
            stats["window_ratio"] = (
                per_frame[i]["z_range"] / p3["shot_z_range"] if p3["shot_z_range"] > 0 else None
            )
            p3["per_frame"].append(stats)

        weights = np.array([s["n_px"] for s in p3["per_frame"]], dtype=np.float64)
        means = np.array([s["mean_abs"] for s in p3["per_frame"]], dtype=np.float64)
        total = float(weights.sum())
        p3["pixel_weighted_mean_abs"] = float((means * weights).sum() / total) if total else None
        p3["worst_frame_mean_abs"] = float(means.max()) if means.size else None
        p3["worst_frame_index"] = int(means.argmax()) if means.size else None
        p3["max_abs_any_pixel"] = float(max(s["max_abs"] for s in p3["per_frame"]))
        ranges = np.array([r["z_range"] for r in per_frame], dtype=np.float64)
        p3["z_range_min"] = float(ranges.min())
        p3["z_range_max"] = float(ranges.max())
        p3["z_range_swing"] = float(ranges.max() / ranges.min()) if ranges.min() > 0 else None
        p3["n_px_per_shot_darker"] = int(sum(s["n_darker"] for s in p3["per_frame"]))
        p3["n_px_per_shot_lighter"] = int(sum(s["n_lighter"] for s in p3["per_frame"]))
        with open(os.path.join(out_dir, "p3_normalization.json"), "w", encoding="utf-8") as fh:
            json.dump(p3, fh, indent=2)

    # ---- G6 · ANDON — the subject performed. Runs on the whole shot, so it cannot run
    #      inside the frame loop, and it runs before G2 because a control sequence of a
    #      figure standing still is a *worse* artifact than a short one: it is complete,
    #      well-formed, passes every other gate, and is wrong.
    g6_detail = gates.g6_subject_motion(
        [r["geometry_signature"] for r in per_frame], spec["subject"]["animation"]
    )

    # ---- G2 · ANDON — completeness. Before the manifest, which is what makes a run
    #      look finished.
    expected = {d: names for d in emitted}
    g2_detail = gates.g2_completeness(out_dir, expected, count)

    manifest = {
        "tool": "stage_render",
        "tool_version": TOOL_VERSION,
        "spec": {k: v for k, v in spec.items() if not k.startswith("_")},
        "asset": {"path": asset_path, "sha256": asset_sha},
        "generator_profile": profile.as_dict(),
        "resolution": [width, height],
        "frame_count": count,
        "channels_requested": requested,
        "channel_dirs": emitted,
        "backend": getattr(backend, "name", type(backend).__name__),
        "provenance": backend.provenance(),
        "scene": scene_info,
        "gates": {
            "G1": {"verdict": "PASS", "profile": profile.as_dict()},
            "G2": {"verdict": "PASS", "detail": g2_detail},
            # The tolerance is READ BACK from the gate that used it, so the manifest
            # cannot name a number the run did not actually check against.
            "G4": {"verdict": "PASS",
                   "tolerance_px": gates.G4_TOLERANCE_PX,
                   "tolerance_source": gates.G4_TOLERANCE_SOURCE,
                   "max_delta_px": max((max(r["g4_deltas_px"]) for r in per_frame), default=None)},
            # G5 is NEVER "PASS" here, and the branch that said so could not be
            # reached: `pose` in `channels` is refused by
            # `openpose.require_drawing_convention()` above — before the output directory
            # exists — so this tool emits no skeleton for `gates.g5_openpose_conformance`
            # to conform-check, and the verdict recorded a gate that had not run. A
            # verdict beside a gate nobody called is a placeholder shaped like evidence.
            # When a pose route lands here it calls that gate and records ITS return.
            "G5": {"verdict": "NOT RUN — this tool does not emit pose; "
                              "openpose.require_drawing_convention refuses the channel",
                   "gate_called": None},
            "G6": {
                "verdict": "PASS" if spec["subject"]["animation"] == "per_frame" else "N/A",
                "detail": g6_detail,
            },
        },
        "frames": per_frame,
        "p3": p3,
        "sha256": {d: _sha256_dir(os.path.join(out_dir, d), names) for d in emitted},
    }

    shotspec.dump_spec(spec, os.path.join(out_dir, "spec.json"))
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest


# ---------------------------------------------------------------------------- cli


def _parse_argv(argv):
    args = {}
    for token in argv:
        if not token.startswith("--") or "=" not in token:
            raise SpecError(f"expected --key=value, got {token!r}")
        key, _, value = token[2:].partition("=")
        args[key] = value
    for required in ("spec", "out"):
        if required not in args:
            raise SpecError(f"missing --{required}=<path>")
    return args


def _halt_keysafe(value, _seen=None):
    """`value` with every mapping key stringified, at every depth.

    `json.dumps(..., default=str)` applies `default` to VALUES ONLY: a tuple key or a
    `numpy.int64` key raises `TypeError` from inside a halt handler, the new exception
    leaves the whole `try` statement, `sys.exit` never runs -- and `blender -b -P` then
    exits **0** on a fired andon, with no sentinel line at all. Measured 2026-09-04 against
    all 21 Blender-side handlers; this is the 22nd tool joining the same contract.

    A container already on the path is written as the literal "<circular>" rather than
    re-entered: a self-referencing evidence dict recursed until `RecursionError` escaped.

    STAGE B: this is the ninth copy of a helper that belongs in `armature_core.errors`
    beside the halt vocabulary. `armature_core` is outside this domain's globs, so the
    lift is FILED, not done -- see this amend's `skipped[]` entry.
    """
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


def halt_sentinel(exc):
    """The six-key halt record for one exception. ONE construction, two callers.

    THREE outcomes, not two. A typed `GateFailure` is an andon that fired and names
    itself; a bare `ArmatureError` is a deliberate refusal with no gate behind it (a
    mistyped flag, a spec that names a hidden-mesh asset); anything else is a crash.
    Recording a crash as "a gate fired" is a false record.
    """
    return {
        "tool": "stage_render",
        "outcome": ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                    else "REFUSED — the tool declined to proceed"
                    if isinstance(exc, ArmatureError)
                    else "FAILED — an unhandled error"),
        "gate": getattr(exc, "gate", None),
        "error": type(exc).__name__,
        "message": str(exc),
        "evidence": (_halt_keysafe(getattr(exc, "evidence", None))
                     if isinstance(getattr(exc, "evidence", None), dict) else None),
    }


def print_halt(exc):
    """Print exactly one `STAGE_RENDER_HALT <json>` line for `exc`. Never raises.

    The sentinel is the contract and it may not be deleted by a failure to serialise the
    sentinel itself -- the fallback line carries only values that are already strings, so
    it cannot fail in turn.
    """
    try:
        rec = halt_sentinel(exc)
        line = json.dumps(rec, default=str)
    except BaseException:                                             # noqa: BLE001
        line = json.dumps({
            "tool": "stage_render",
            "outcome": "FAILED — an unhandled error",
            "gate": None, "error": type(exc).__name__, "message": str(exc),
            "evidence": None})
    print("STAGE_RENDER_HALT " + line, flush=True)


def main(argv=None):
    """Export one shot spec. Returns 0 on success and 2 on any deliberate refusal.

    **The handler covers the whole body, not `run_export` alone.** It used to wrap
    `run_export` in `except GateFailure` and nothing else: `_parse_argv`,
    `shotspec.load_spec` and every `SpecError` inside `BlenderBackend.prepare` (no mesh
    objects; every mesh hidden from render; no evaluated geometry; clip_end closer than the
    subject) sat OUTSIDE any handler, and `NotInsideBlender` with them. `SpecError` is not
    a `GateFailure` -- measured -- so all of those propagated, and under `blender -b -P` a
    propagating exception exits **0**. Measured 2026-09-04: `--spec=nope.json` ->
    FileNotFoundError escaped; `--out=x` alone -> SpecError escaped; `-spec=x` -> SpecError
    escaped. A PowerShell chain or CI step reading `$LASTEXITCODE` read "the control
    sequence was exported" and moved to the submission step.
    """
    try:
        if argv is None:
            argv = (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv
                    else sys.argv[1:])
        args = _parse_argv(argv)
        spec = shotspec.load_spec(args["spec"])
        if "asset" in args:
            spec["asset"]["path"] = args["asset"]
        manifest = run_export(spec, args["out"])
    except ArmatureError as exc:
        # The two lines this repo's evidence-id discipline keys on, kept: a reader holding
        # only the JSON needs the gate id, and `GATE_EVIDENCE` is where the measurement is.
        if isinstance(exc, GateFailure):
            print("GATE_FAILURE", exc.gate, str(exc), flush=True)
            print("GATE_EVIDENCE", json.dumps(_halt_keysafe(exc.evidence), default=str),
                  flush=True)
        # ...and the six-key line the 21 siblings deliver, so an existing reader can parse
        # this tool's halt without a second parser.
        print_halt(exc)
        return 2
    except OSError as exc:
        # A spec path that is not there is a refusal, not a crash: the operator mistyped a
        # flag. It reached no gate, so it carries no gate id.
        print_halt(exc)
        return 2
    print("EXPORT_OK", json.dumps({
        "run_dir": os.path.abspath(args["out"]),
        "frames": manifest["frame_count"],
        "channels": manifest["channel_dirs"],
    }), flush=True)
    return 0


if __name__ == "__main__":
    # THE HALT CONTRACT — the shape all 21 Blender-side tools carry, on the 22nd.
    # `blender -b -P` exits **0** when the script's exception propagates (E07, measured
    # three times), so a halt that does not exit deliberately is reported as a success.
    # This tool is invisible to `blender_stub.blender_tools()` because that census keys on
    # a MODULE-LEVEL `import bpy` and this module imports its backend lazily inside
    # `BlenderBackend.__init__` — deliberately, so the gate tests can drive the real write
    # path outside Blender. The re-keying of that population is the tests domain's half;
    # the handler is this one's.
    #
    # A deliberate refusal exits 2; a crash exits 1. The sentinel line and `sys.exit` are
    # both delivered from a `finally`, so neither is deleted by a secondary failure.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:                                      # noqa: BLE001
        import traceback
        traceback.print_exc()
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        try:
            print_halt(exc)
        finally:
            sys.exit(_code)
