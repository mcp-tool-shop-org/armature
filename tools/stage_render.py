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
        imported_meshes, armatures, info = bs.import_glb(asset_path)
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

        bounds = bs.world_bounds(meshes)
        if bounds is None:
            raise SpecError(f"{asset_path} has no evaluated geometry")
        center, half, sphere_r = bounds

        cam = bs.make_camera(scene, spec)
        c = spec["camera"]
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
        )
        return {
            "import": info,
            "subject_bbox_center": [float(v) for v in center],
            "subject_bbox_half_extent": [float(v) for v in half],
            "subject_sphere_radius": float(sphere_r),
            "camera_radius_resolved": radius,
            "armature_names": [a.name for a in armatures],
        }

    def render_frame(self, index, count):
        st = self._state
        bs, spec = self._bs, st["spec"]
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
        projected = bs.projected_bbox_px(st["cam"], st["meshes"], st["width"], st["height"])

        return {
            "z": z,
            "alpha": alpha,
            "normal_world": normal_world,
            "cam_rot_3x3": cam_rot,
            "projected_bbox": projected,
            "azimuth_deg": float(az),
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
    g4_tol = spec["gates"]["g4_tolerance_px"]

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

        # ---- G4 · bbox sanity, inside the loop that writes the frame
        deltas = gates.g4_bbox_sanity(
            i, mask_bbox, f["projected_bbox"], g4_tol, width, height
        )

        rec = {
            "frame": i,
            "azimuth_deg": f.get("azimuth_deg"),
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
        shot_min, shot_max = float(min(mins)), float(max(maxs))
        p3 = {
            "shot_z_min": shot_min,
            "shot_z_max": shot_max,
            "shot_z_range": shot_max - shot_min,
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
            "G4": {"verdict": "PASS", "tolerance_px": g4_tol,
                   "max_delta_px": max((max(r["g4_deltas_px"]) for r in per_frame), default=None)},
            "G5": {"verdict": "NOT RUN — pose was not emitted"}
            if "pose" not in requested else {"verdict": "PASS"},
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


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _parse_argv(argv)
    spec = shotspec.load_spec(args["spec"])
    if "asset" in args:
        spec["asset"]["path"] = args["asset"]
    try:
        manifest = run_export(spec, args["out"])
    except GateFailure as exc:
        print("GATE_FAILURE", exc.gate, str(exc), flush=True)
        print("GATE_EVIDENCE", json.dumps(exc.evidence, default=str), flush=True)
        return 2
    print("EXPORT_OK", json.dumps({
        "run_dir": os.path.abspath(args["out"]),
        "frames": manifest["frame_count"],
        "channels": manifest["channel_dirs"],
    }), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
