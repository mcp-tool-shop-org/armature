"""Synthetic CPU tests for Tier A shot camera diagnostics (`C1`–`C12` + `measure_shot` CLI).

Every test runs on CPU with deterministic geometric or procedural planar-homography image
fixtures and zero learned weights (`docs/dispatches/shot-diagnostics-design.md` §5).
"""

import json
import math
import os

import cv2
import numpy as np
import pytest

from conftest import load_ok_payload

from armature_core import framing
from armature_core import pngio
from armature_core import shotdiag as SD
from armature_core.shotdiag import ShotDiagError
import measure_shot as MS
import sheet_compose as SC


# ---------------------------------------------------------------------------
# Deterministic synthetic geometry & rendered-like image helpers
# ---------------------------------------------------------------------------


def _blender_pose_matrix(position, target):
    """4x4 Blender `matrix_world` (cam->world, -Z forward, +Y up) from `framing.camera_basis`."""
    right, up, back = framing.camera_basis(target, position)
    m = np.eye(4, dtype=np.float64)
    m[:3, 0] = right
    m[:3, 1] = up
    m[:3, 2] = back
    m[:3, 3] = position
    return m


def _orbit_matrices(
    n_frames=6,
    *,
    target=(0.0, 0.0, 0.0),
    radius=5.0,
    elevation_deg=8.0,
    az_start_deg=-102.0,
    az_end_deg=-72.0,
):
    """Blender `matrix_world` sequence along a smooth azimuth orbit."""
    azimuths = np.linspace(az_start_deg, az_end_deg, n_frames)
    mats = []
    for az in azimuths:
        pos = framing.camera_position(target, radius, elevation_deg, float(az))
        mats.append(_blender_pose_matrix(pos, target))
    return mats


def _pure_pan_matrices(
    n_frames=5,
    *,
    position=(0.0, -4.95, 0.70),
    pan_span_deg=18.0,
):
    """Rotation-only Blender `matrix_world` sequence with fixed camera centre `position`."""
    angles = np.linspace(-0.5 * pan_span_deg, 0.5 * pan_span_deg, n_frames)
    mats = []
    for ang in angles:
        rad = math.radians(float(ang))
        look_target = (
            position[0] + 5.0 * math.sin(rad),
            position[1] + 5.0 * math.cos(rad),
            0.20,
        )
        mats.append(_blender_pose_matrix(position, look_target))
    return mats


def _push_in_matrices(
    n_frames=5,
    *,
    target=(0.0, 0.0, 0.0),
    r_start=5.2,
    r_end=3.6,
    elevation_deg=8.0,
    azimuth_deg=-90.0,
):
    """Forward dolly / push-in Blender `matrix_world` sequence along a constant ray."""
    radii = np.linspace(r_start, r_end, n_frames)
    return [
        _blender_pose_matrix(
            framing.camera_position(target, float(r), elevation_deg, azimuth_deg),
            target,
        )
        for r in radii
    ]


def _project_points_cv(pts_world, r_cv, c_world, k_mat):
    """Project `(N, 3)` world points into `(N, 2)` OpenCV pixel coordinates."""
    pts = np.asarray(pts_world, dtype=np.float64)
    cam = (r_cv.T @ (pts - c_world[None, :]).T).T
    if np.any(cam[:, 2] <= 0.05):
        raise ValueError("synthetic 3D fixture placed points behind or on the camera plane")
    pix_h = (k_mat @ cam.T).T
    return pix_h[:, :2] / pix_h[:, 2:3]


def _two_plane_points(seed=17, n_per_plane=48):
    """Seeded 3D background points on two distinct depth planes in front of `-Y` cameras."""
    rng = np.random.default_rng(seed)
    near = np.column_stack(
        [
            rng.uniform(-1.4, 1.4, size=n_per_plane),
            np.full(n_per_plane, -1.1),
            rng.uniform(-0.9, 0.2, size=n_per_plane),
        ]
    )
    far = np.column_stack(
        [
            rng.uniform(-2.6, 2.6, size=n_per_plane),
            np.full(n_per_plane, 3.2),
            rng.uniform(-1.3, 1.3, size=n_per_plane),
        ]
    )
    return np.vstack([near, far])


def _sift_rich_texture(height, width, *, seed=101, n_blobs=160):
    """Deterministic multi-scale blob texture yielding dense, unique SIFT keypoints."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0.0, 1.0, size=(height, width)).astype(np.float32)
    f1 = cv2.GaussianBlur(base, (0, 0), sigmaX=2.2)
    f2 = cv2.GaussianBlur(base, (0, 0), sigmaX=6.5)
    gray = 128.0 + 38.0 * (f1 / (float(np.std(f1)) + 1e-6)) + 26.0 * (
        f2 / (float(np.std(f2)) + 1e-6)
    )
    canvas = np.stack(
        [gray, gray * 0.97 + 4.0, gray * 1.03 - 4.0], axis=-1
    )
    canvas = np.clip(canvas, 18.0, 238.0).astype(np.uint8)

    for _ in range(n_blobs):
        cx = int(rng.integers(10, width - 10))
        cy = int(rng.integers(10, height - 10))
        rad = int(rng.integers(3, 10))
        val = int(rng.integers(15, 245))
        ring = 245 - val
        cv2.circle(canvas, (cx, cy), rad + 2, (ring, ring, ring), thickness=-1, lineType=cv2.LINE_AA)
        cv2.circle(canvas, (cx, cy), rad, (val, int(0.9 * val), min(255, val + 15)), thickness=-1, lineType=cv2.LINE_AA)
    return canvas


def _plane_homography(origin, u_axis, v_axis, tex_scale, r_cv, c_world, k_mat):
    """Exact 3x3 texel-to-pixel homography for a 3D world plane."""
    col0 = float(tex_scale) * (r_cv.T @ np.asarray(u_axis, dtype=np.float64))
    col1 = float(tex_scale) * (r_cv.T @ np.asarray(v_axis, dtype=np.float64))
    col2 = r_cv.T @ (np.asarray(origin, dtype=np.float64) - c_world)
    return k_mat @ np.column_stack([col0, col1, col2])


def _render_synthetic_sequence(
    cam_matrices,
    *,
    width=320,
    height=192,
    lens_mm=50.0,
    sensor_mm=36.0,
    include_character=True,
    dense_character=False,
    sparse_background=False,
):
    """Render `(frames, masks, intr)` by exact perspective homographies of two 3D planes."""
    intr = SD.intrinsics_from_spec(lens_mm, sensor_mm, width, height)
    k_mat = intr["K"]

    far_tex = _sift_rich_texture(
        420, 680, seed=11, n_blobs=10 if sparse_background else 220
    )
    near_tex = _sift_rich_texture(
        200, 640, seed=29, n_blobs=8 if sparse_background else 160
    )
    if sparse_background:
        far_tex = cv2.GaussianBlur(far_tex, (0, 0), sigmaX=7.0)
        near_tex = cv2.GaussianBlur(near_tex, (0, 0), sigmaX=7.0)

    char_tex = _sift_rich_texture(
        140, 120, seed=73, n_blobs=180 if dense_character else 45
    )
    far_alpha = np.full((far_tex.shape[0], far_tex.shape[1]), 255, dtype=np.uint8)
    near_alpha = np.full((near_tex.shape[0], near_tex.shape[1]), 255, dtype=np.uint8)
    char_alpha = np.zeros((char_tex.shape[0], char_tex.shape[1]), dtype=np.uint8)
    cv2.rectangle(
        char_alpha,
        (10, 10),
        (char_tex.shape[1] - 11, char_tex.shape[0] - 11),
        255,
        thickness=-1,
    )

    frames = []
    masks = []
    n_frames = len(cam_matrices)
    for idx, m_bl in enumerate(cam_matrices):
        r_cv, c_w = SD.blender_to_opencv_pose(m_bl)
        frame = np.full((height, width, 3), 118, dtype=np.uint8)

        # Far backdrop at y = +3.5 m
        h_far = _plane_homography(
            origin=(-7.48, 3.5, 4.62),
            u_axis=(1.0, 0.0, 0.0),
            v_axis=(0.0, 0.0, -1.0),
            tex_scale=0.022,
            r_cv=r_cv,
            c_world=c_w,
            k_mat=k_mat,
        )
        far_img = cv2.warpPerspective(far_tex, h_far, (width, height), flags=cv2.INTER_LINEAR)
        far_m = cv2.warpPerspective(far_alpha, h_far, (width, height), flags=cv2.INTER_NEAREST) > 0
        frame = np.where(far_m[:, :, None], far_img, frame)

        # Near static foreground structure at y = -1.2 m (lower half of frame)
        h_near = _plane_homography(
            origin=(-3.52, -1.2, -0.08),
            u_axis=(1.0, 0.0, 0.0),
            v_axis=(0.0, 0.0, -1.0),
            tex_scale=0.011,
            r_cv=r_cv,
            c_world=c_w,
            k_mat=k_mat,
        )
        near_img = cv2.warpPerspective(near_tex, h_near, (width, height), flags=cv2.INTER_LINEAR)
        near_m = cv2.warpPerspective(near_alpha, h_near, (width, height), flags=cv2.INTER_NEAREST) > 0
        frame = np.where(near_m[:, :, None], near_img, frame)

        mask_bool = np.zeros((height, width), dtype=bool)
        if include_character:
            frac = idx / max(1, n_frames - 1)
            # Move character opposite to camera motion to violate static-scene rigidity.
            char_x = 0.55 - 1.10 * frac
            char_scale = 0.010 if dense_character else 0.0055
            h_char = _plane_homography(
                origin=(char_x, -1.9, 0.55),
                u_axis=(1.0, 0.0, 0.0),
                v_axis=(0.0, 0.0, -1.0),
                tex_scale=char_scale,
                r_cv=r_cv,
                c_world=c_w,
                k_mat=k_mat,
            )
            char_img = cv2.warpPerspective(char_tex, h_char, (width, height), flags=cv2.INTER_LINEAR)
            mask_bool = (
                cv2.warpPerspective(char_alpha, h_char, (width, height), flags=cv2.INTER_NEAREST)
                > 127
            )
            frame = np.where(mask_bool[:, :, None], char_img, frame)

        frames.append(frame)
        masks.append(mask_bool)
    return frames, masks, intr


def _write_stage_render_fixture(
    base_dir,
    frames,
    masks,
    cam_matrices,
    *,
    lens_mm=50.0,
    sensor_mm=36.0,
):
    """Write `frames/NNNNN.png` and `render_run/{manifest.json,spec.json,mask/NNNNN.png}`."""
    frames_dir = os.path.join(base_dir, "frames")
    run_dir = os.path.join(base_dir, "render_run")
    mask_dir = os.path.join(run_dir, "mask")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(mask_dir, exist_ok=True)

    h, w = frames[0].shape[:2]
    frame_records = []
    for i, (rgb, m_bool) in enumerate(zip(frames, masks)):
        pngio.write_png(os.path.join(frames_dir, f"{i:05d}.png"), rgb)
        mask_u8 = np.where(m_bool, 255, 0).astype(np.uint8)
        mask_rgb = np.stack([mask_u8, mask_u8, mask_u8], axis=-1)
        pngio.write_png(os.path.join(mask_dir, f"{i:05d}.png"), mask_rgb)

        ys, xs = np.nonzero(m_bool)
        bbox = (
            [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
            if ys.size
            else None
        )
        frame_records.append(
            {
                "frame": i,
                "camera_matrix": (
                    np.asarray(cam_matrices[i], dtype=np.float64).tolist()
                    if cam_matrices[i] is not None
                    else None
                ),
                "mask_px": int(np.sum(m_bool)),
                "mask_bbox": bbox,
            }
        )

    manifest = {
        "tool": "stage_render",
        "resolution": [int(w), int(h)],
        "frames": frame_records,
    }
    with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    spec = {
        "camera": {"lens_mm": float(lens_mm), "sensor_mm": float(sensor_mm)},
        "render": {"width": int(w), "height": int(h)},
    }
    with open(os.path.join(run_dir, "spec.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)

    return frames_dir, run_dir


# ---------------------------------------------------------------------------
# C1–C12: Geometric and image-level Tier A camera recovery tests
# ---------------------------------------------------------------------------


def test_c1_noiseless_orbit_recovers_zero_rotation_and_direction_error():
    """C1: Fails if two-view pose recovery, frame-0 anchoring, or SO(3) composition order is wrong."""
    pts_w = _two_plane_points(seed=17, n_per_plane=48)
    intr = SD.intrinsics_from_spec(50.0, 36.0, 832, 480)
    k_mat = intr["K"]
    mats = _orbit_matrices(n_frames=5, az_start_deg=-105.0, az_end_deg=-75.0)
    gt_poses = [SD.blender_to_opencv_pose(m) for m in mats]

    p0 = _project_points_cv(pts_w, *gt_poses[0], k_mat)
    pairs = []
    for t in range(1, len(gt_poses)):
        pt = _project_points_cv(pts_w, *gt_poses[t], k_mat)
        pairs.append(SD.estimate_pair_pose(p0, pt, k_mat))

    cam = SD.score_camera_trajectory(gt_poses, pairs, intrinsics_info=intr)
    assert cam["n_fired"] == 4
    assert all(row["model"] == "E" for row in cam["per_pair"])
    assert cam["rot_err_deg"]["max"] < 1e-2
    assert cam["tdir_err_deg"]["max"] < 5e-2
    assert abs(cam["est_to_gt_rot_span_ratio"] - 1.0) < 1e-3


def test_c2_orbit_scored_against_static_gt_reports_true_angular_departure():
    """C2: Fails if a moving camera scored against a static GT reads as low error, or if static span divides by zero."""
    pts_w = _two_plane_points(seed=23, n_per_plane=48)
    intr = SD.intrinsics_from_spec(50.0, 36.0, 832, 480)
    k_mat = intr["K"]
    # Pure azimuth orbit on the horizontal plane (elevation 0 deg) gives exact 30.0 deg rotation span.
    mats = _orbit_matrices(
        n_frames=5, elevation_deg=0.0, az_start_deg=-105.0, az_end_deg=-75.0
    )
    gt_true = [SD.blender_to_opencv_pose(m) for m in mats]
    p0 = _project_points_cv(pts_w, *gt_true[0], k_mat)
    pairs = [
        SD.estimate_pair_pose(p0, _project_points_cv(pts_w, *gt_true[t], k_mat), k_mat)
        for t in range(1, len(gt_true))
    ]

    true_cam = SD.score_camera_trajectory(gt_true, pairs, intrinsics_info=intr)
    assert abs(true_cam["est_to_gt_rot_span_ratio"] - 1.0) < 1e-3

    gt_static = [(gt_true[0][0].copy(), gt_true[0][1].copy()) for _ in mats]
    wrong_cam = SD.score_camera_trajectory(
        gt_static, pairs, gt_source="static", intrinsics_info=intr
    )
    assert abs(wrong_cam["per_pair"][-1]["rot_err_deg"] - 30.0) < 0.15
    assert wrong_cam["gt_rot_span_deg"] == 0.0
    assert wrong_cam["est_to_gt_rot_span_ratio"] is None


def test_c3_scale_invariance_of_direction_errors_and_ate_not_computable():
    """C3: Fails if real estimator unit directions report a numeric `fitted_scale`/`ate` or if scene metric scale leaks into direction error."""
    pts_w = _two_plane_points(seed=29, n_per_plane=48)
    intr = SD.intrinsics_from_spec(50.0, 36.0, 832, 480)
    k_mat = intr["K"]
    mats = _orbit_matrices(n_frames=5, elevation_deg=0.0, az_start_deg=-105.0, az_end_deg=-75.0)
    gt_poses = [SD.blender_to_opencv_pose(m) for m in mats]

    k_factor = 3.75
    pts_w_scaled = k_factor * pts_w
    gt_poses_scaled = [(r, k_factor * c) for r, c in gt_poses]

    p0_unit = _project_points_cv(pts_w, *gt_poses[0], k_mat)
    p0_scaled = _project_points_cv(pts_w_scaled, *gt_poses_scaled[0], k_mat)
    pairs_unit = []
    pairs_scaled = []
    for t in range(1, len(gt_poses)):
        pt_unit = _project_points_cv(pts_w, *gt_poses[t], k_mat)
        pt_scaled = _project_points_cv(pts_w_scaled, *gt_poses_scaled[t], k_mat)
        est_u = SD.estimate_pair_pose(p0_unit, pt_unit, k_mat)
        est_s = SD.estimate_pair_pose(p0_scaled, pt_scaled, k_mat)
        assert est_u["fired"] is True and est_u["model"] == "E"
        assert est_s["fired"] is True and est_s["model"] == "E"
        assert abs(float(np.linalg.norm(est_u["t_dir_in_f0"])) - 1.0) < 1e-9
        assert abs(float(np.linalg.norm(est_s["t_dir_in_f0"])) - 1.0) < 1e-9
        pairs_unit.append(est_u)
        pairs_scaled.append(est_s)

    res_unit = SD.score_camera_trajectory(gt_poses, pairs_unit, intrinsics_info=intr)
    res_scaled = SD.score_camera_trajectory(gt_poses_scaled, pairs_scaled, intrinsics_info=intr)

    assert res_unit["rot_err_deg"]["max"] < 1e-2
    assert res_unit["tdir_err_deg"]["max"] < 5e-2
    assert abs(res_unit["tdir_err_deg"]["max"] - res_scaled["tdir_err_deg"]["max"]) < 1e-9

    expected_not_computable = "NOT COMPUTABLE — pairwise unit directions carry no relative scale"
    assert res_unit["fitted_scale"] == expected_not_computable
    assert res_unit["ate"] == expected_not_computable
    assert res_scaled["fitted_scale"] == expected_not_computable
    assert res_scaled["ate"] == expected_not_computable


def test_c4_blender_to_opencv_axis_convention_flip():
    """C4: Fails if the `diag(1, -1, -1)` Blender->OpenCV camera axis flip is missing or doubled."""
    pts_w = _two_plane_points(seed=31, n_per_plane=48)
    intr = SD.intrinsics_from_spec(50.0, 36.0, 832, 480)
    k_mat = intr["K"]
    # Combine azimuth + elevation change so rotation axis is oblique to Y and Z;
    # omitting `diag(1, -1, -1)` flips the rotation axis components and produces large error.
    pos0 = framing.camera_position((0.0, 0.0, 0.0), 5.0, 5.0, -110.0)
    pos1 = framing.camera_position((0.0, 0.0, 0.0), 5.0, 42.0, -55.0)
    mats = [_blender_pose_matrix(pos0, (0.0, 0.0, 0.0)), _blender_pose_matrix(pos1, (0.0, 0.0, 0.0))]

    gt_flipped = [SD.blender_to_opencv_pose(m, convert_axes=True) for m in mats]
    gt_unflipped = [SD.blender_to_opencv_pose(m, convert_axes=False) for m in mats]

    # Also verify raw OpenCV vs Blender camera orientation directly: ~180 deg around X.
    axis_diff_deg = SD.geodesic_angle_deg(gt_flipped[0][0].T @ gt_unflipped[0][0])
    assert abs(axis_diff_deg - 180.0) < 1e-6

    p0 = _project_points_cv(pts_w, *gt_flipped[0], k_mat)
    p1 = _project_points_cv(pts_w, *gt_flipped[1], k_mat)
    pair = SD.estimate_pair_pose(p0, p1, k_mat)

    ok_cam = SD.score_camera_trajectory(gt_flipped, [pair])
    bad_cam = SD.score_camera_trajectory(gt_unflipped, [pair])
    assert ok_cam["rot_err_deg"]["max"] < 1e-2
    assert bad_cam["rot_err_deg"]["max"] > 90.0


def test_c5_world_gauge_offset_cancels_while_per_frame_drift_is_not_absorbed():
    """C5: Fails if trajectory alignment fits away per-frame rotation drift (Sim(3) absorption)."""
    mats = _orbit_matrices(n_frames=5, elevation_deg=0.0, az_start_deg=-100.0, az_end_deg=-80.0)
    gt_poses = [SD.blender_to_opencv_pose(m) for m in mats]

    # Apply an arbitrary global world rotation `R_world_offset` to EVERY pose:
    # anchored relative rotations `R_0.T @ R_t` must stay bit-for-bit identical up to float roundoff.
    ang_off = math.radians(37.0)
    r_world_offset = np.array(
        [
            [math.cos(ang_off), -math.sin(ang_off), 0.0],
            [math.sin(ang_off), math.cos(ang_off), 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    shifted_world = [(r_world_offset @ r, r_world_offset @ c) for r, c in gt_poses]
    r0_s, c0_s = shifted_world[0]
    anchored_pairs = [
        {
            "fired": True,
            "n_matches": 50,
            "n_inliers": 50,
            "model": "E",
            "R_rel": r0_s.T @ rt_s,
            "t_dir_in_f0": (r0_s.T @ (ct_s - c0_s)) / np.linalg.norm(ct_s - c0_s),
            "tdir_reason": None,
            "parallax_residual_px": 8.0,
        }
        for rt_s, ct_s in shifted_world[1:]
    ]
    gauge_res = SD.score_camera_trajectory(gt_poses, anchored_pairs)
    assert gauge_res["rot_err_deg"]["max"] < 1e-9

    # Now inject a 2.5 deg/frame drift into the estimated trajectory: anchored scoring
    # must report exact linear drift (2.5, 5.0, 7.5, 10.0 deg), never fitting it away.
    drifted_pairs = []
    for step, base_pair in enumerate(anchored_pairs, start=1):
        d_rad = math.radians(2.5 * step)
        r_drift = np.array(
            [
                [math.cos(d_rad), 0.0, math.sin(d_rad)],
                [0.0, 1.0, 0.0],
                [-math.sin(d_rad), 0.0, math.cos(d_rad)],
            ],
            dtype=np.float64,
        )
        drifted_pairs.append({**base_pair, "R_rel": base_pair["R_rel"] @ r_drift})

    drift_res = SD.score_camera_trajectory(gt_poses, drifted_pairs)
    reported = [row["rot_err_deg"] for row in drift_res["per_pair"]]
    for step, err_deg in enumerate(reported, start=1):
        assert abs(err_deg - 2.5 * step) < 1e-6


def test_c6_pure_rotation_selects_homography_and_marks_translation_unobservable():
    """C6: Fails if pure pan invents a translation-direction number instead of `t_unobservable`."""
    pan_mats = _pure_pan_matrices(n_frames=5, pan_span_deg=16.0)
    frames, masks, _ = _render_synthetic_sequence(
        pan_mats, include_character=False
    )
    cam = SD.measure_camera_from_frames(
        frames, pan_mats, lens_mm=50.0, sensor_mm=36.0, masks=masks
    )
    assert cam["n_fired"] == 4
    assert cam["n_rotation_only_t_unobservable"] == 4
    assert cam["n_tdir_observable"] == 0
    assert cam["tdir_err_deg"]["n"] == 0
    assert cam["tdir_err_deg"]["median"] is None
    assert cam["rot_err_deg"]["max"] < 0.6
    for row in cam["per_pair"]:
        assert row["model"] == "H"
        assert row["tdir_err_deg"] is None
        assert row["tdir_reason"] == "t_unobservable"


def test_c7_too_few_correspondences_or_all_masked_reports_not_fired_with_null_metrics():
    """C7: Fails if a pair below `MIN_SOLVER_INLIERS` or fully inside the character mask emits numbers."""
    intr = SD.intrinsics_from_spec(50.0, 36.0, 320, 192)
    k_mat = intr["K"]
    pts_w = _two_plane_points(seed=41, n_per_plane=6)
    mats = _orbit_matrices(n_frames=2)
    gt_poses = [SD.blender_to_opencv_pose(m) for m in mats]
    p0 = _project_points_cv(pts_w[:5], *gt_poses[0], k_mat)
    p1 = _project_points_cv(pts_w[:5], *gt_poses[1], k_mat)

    sub_min = SD.estimate_pair_pose(p0, p1, k_mat)
    assert sub_min["fired"] is False
    assert sub_min["R_rel"] is None
    assert sub_min["t_dir_in_f0"] is None
    assert sub_min["tdir_reason"] == "not_fired"

    # All correspondences sitting inside the character mask -> filtered below minimum -> NOT FIRED.
    full_mask = np.ones((192, 320), dtype=bool)
    f0, f1 = SD.filter_correspondences_by_masks(p0, p1, full_mask, full_mask)
    assert len(f0) == 0 and len(f1) == 0
    masked_est = SD.estimate_pair_pose(f0, f1, k_mat)
    scored = SD.score_camera_trajectory(gt_poses, [masked_est])
    assert scored["n_fired"] == 0
    assert scored["rot_err_deg"]["median"] is None
    assert scored["tdir_err_deg"]["median"] is None
    assert scored["est_rot_span_deg"] is None
    assert scored["per_pair"][0]["rot_err_deg"] is None
    assert scored["per_pair"][0]["tdir_err_deg"] is None


def test_c8_character_mask_excludes_moving_performer_in_core_and_cli(tmp_path, capsys):
    """C8: Fails if the dilated Blender character mask is not applied before feature matching."""
    # Static camera hold while a large textured character translates across the frame:
    # without the mask, SIFT locks onto the moving character and hallucinates camera motion;
    # with the mask (and via `measure_shot.main`), only static background features survive.
    hold_pos = framing.camera_position((0.0, 0.0, 0.0), 5.0, 8.0, -90.0)
    hold_mat = _blender_pose_matrix(hold_pos, (0.0, 0.0, 0.0))
    mats = [hold_mat.copy() for _ in range(4)]

    frames, masks, _ = _render_synthetic_sequence(
        mats,
        include_character=True,
        dense_character=True,
        sparse_background=False,
    )
    # Place extra dense moving features on a large central character patch so unmasked RANSAC is corrupted.
    rng_tex = _sift_rich_texture(128, 170, seed=99, n_blobs=260)
    patched_frames = []
    patched_masks = []
    for i, rgb in enumerate(frames):
        f_copy = (rgb * 0.35 + 80).astype(np.uint8)
        # Keep crisp static corner patches in background outside mask, plus huge moving central character.
        f_copy[:44, :80] = rgb[:44, :80]
        f_copy[:44, -80:] = rgb[:44, -80:]
        f_copy[-44:, :80] = rgb[-44:, :80]
        f_copy[-44:, -80:] = rgb[-44:, -80:]
        x0 = 40 + i * 28
        y0 = 36
        f_copy[y0 : y0 + 120, x0 : x0 + 160] = rng_tex[:120, :160]
        m = np.zeros(rgb.shape[:2], dtype=bool)
        m[y0 : y0 + 120, x0 : x0 + 160] = True
        patched_frames.append(f_copy)
        patched_masks.append(m)

    unmasked = SD.measure_camera_from_frames(
        patched_frames, mats, lens_mm=50.0, sensor_mm=36.0, masks=None
    )
    masked = SD.measure_camera_from_frames(
        patched_frames, mats, lens_mm=50.0, sensor_mm=36.0, masks=patched_masks
    )
    assert masked["mask_applied"] == "yes"
    assert unmasked["rot_err_deg"]["max"] > masked["rot_err_deg"]["max"] + 1.0
    assert masked["rot_err_deg"]["max"] < 0.5

    # Verify CLI `measure_shot.main` wires `render_run/mask/` automatically.
    frames_dir, run_dir = _write_stage_render_fixture(
        str(tmp_path), patched_frames, patched_masks, mats
    )
    out_json = str(tmp_path / "shot_c8.json")
    rc = MS.main(["--frames", frames_dir, "--render-run", run_dir, "--out", out_json])
    assert rc == 0
    ok = load_ok_payload(capsys.readouterr().out, "MEASURE_SHOT_OK")
    assert ok["out"] == os.path.abspath(out_json)
    with open(out_json, encoding="utf-8") as fh:
        rec = json.load(fh)
    assert rec["camera"]["mask_applied"] == "yes"
    assert rec["camera"]["rot_err_deg"]["max"] < 0.5


def test_c9_end_to_end_image_sequence_separates_true_orbit_from_reversed_gt(tmp_path, capsys):
    """C9: Fails if end-to-end SIFT + E/H image recovery cannot separate the true path from a reversed GT."""
    true_mats = _orbit_matrices(
        n_frames=6, elevation_deg=6.0, az_start_deg=-102.0, az_end_deg=-78.0
    )
    wrong_mats = list(reversed(true_mats))
    frames, masks, _ = _render_synthetic_sequence(true_mats, include_character=True)

    frames_dir, true_run = _write_stage_render_fixture(
        str(tmp_path / "true_case"), frames, masks, true_mats
    )
    _, wrong_run = _write_stage_render_fixture(
        str(tmp_path / "wrong_case"), frames, masks, wrong_mats
    )

    out_true = str(tmp_path / "true_shot.json")
    out_wrong = str(tmp_path / "wrong_shot.json")
    assert MS.main(
        [
            "--frames",
            frames_dir,
            "--render-run",
            true_run,
            "--floor-frames",
            frames_dir,
            "--out",
            out_true,
        ]
    ) == 0
    load_ok_payload(capsys.readouterr().out, "MEASURE_SHOT_OK")

    assert MS.main(
        ["--frames", frames_dir, "--render-run", wrong_run, "--out", out_wrong]
    ) == 0
    load_ok_payload(capsys.readouterr().out, "MEASURE_SHOT_OK")

    with open(out_true, encoding="utf-8") as fh:
        rec_true = json.load(fh)
    with open(out_wrong, encoding="utf-8") as fh:
        rec_wrong = json.load(fh)

    assert rec_true["camera"]["n_fired"] == 5
    assert rec_true["camera"]["rot_err_deg"]["median"] < 1.0
    assert rec_true["camera"]["instrument_floor"]["note"] == "NOT A VERDICT"
    # Reversing a ~24 deg azimuth sweep doubles the final-frame angular discrepancy (~48 deg).
    assert rec_wrong["camera"]["per_pair"][-1]["rot_err_deg"] > 35.0
    assert (
        rec_wrong["camera"]["rot_err_deg"]["median"]
        > rec_true["camera"]["rot_err_deg"]["median"] + 15.0
    )


def test_c10_static_request_detects_push_in_parallax_and_reads_zero_on_pure_hold(tmp_path, capsys):
    """C10: Fails if `--static` misses background parallax on an uncommanded push-in or reports parallax on a hold."""
    push_mats = _push_in_matrices(n_frames=5, r_start=5.2, r_end=3.5)
    push_frames, push_masks, _ = _render_synthetic_sequence(push_mats, include_character=True)

    hold_mats = [push_mats[0].copy() for _ in range(5)]
    hold_frames, hold_masks, _ = _render_synthetic_sequence(hold_mats, include_character=True)

    push_cam = SD.measure_camera_from_frames(
        push_frames, masks=push_masks, is_static=True, lens_mm=50.0, sensor_mm=36.0
    )
    hold_cam = SD.measure_camera_from_frames(
        hold_frames, masks=hold_masks, is_static=True, lens_mm=50.0, sensor_mm=36.0
    )

    assert push_cam["gt_source"] == "static"
    assert push_cam["static_parallax_px"]["median"] > 1.5
    assert push_cam["static_parallax_px"]["max"] > 3.0
    assert hold_cam["static_parallax_px"]["max"] < 0.05

    # Exercise CLI `--static` + `--masks` without `--render-run` and check sheet lines.
    push_dir, push_run = _write_stage_render_fixture(
        str(tmp_path / "push"), push_frames, push_masks, push_mats
    )
    out_static = str(tmp_path / "static_push.json")
    assert MS.main(
        [
            "--frames",
            push_dir,
            "--static",
            "--masks",
            os.path.join(push_run, "mask"),
            "--lens-mm",
            "50",
            "--sensor-mm",
            "36",
            "--out",
            out_static,
        ]
    ) == 0
    load_ok_payload(capsys.readouterr().out, "MEASURE_SHOT_OK")
    lines = SC.diagnostic_lines(out_static)
    joined = "\n".join(lines)
    assert "static parallax med" in joined
    assert "NO THRESHOLD — CALIBRATION NOT YET RUN" in joined


def test_c11_input_refusals_and_same_aspect_intrinsics_scaling(tmp_path):
    """C11: Fails if mismatched frame counts, unknowable cropped `K`, or missing GT reach the solver."""
    # Same aspect (16:9 -> 640x360 vs 1280x720): scales `K` by 0.5 and records `k_scale`.
    scaled = SD.intrinsics_from_spec(
        50.0, 36.0, 1280, 720, frame_width=640, frame_height=360
    )
    assert abs(scaled["k_scale"] - 0.5) < 1e-9

    # Different aspect ratio -> `aspect_ratio_mismatch`.
    with pytest.raises(ShotDiagError) as exc:
        SD.intrinsics_from_spec(50.0, 36.0, 832, 480, frame_width=512, frame_height=512)
    assert exc.value.evidence["clause"] == "aspect_ratio_mismatch"

    # Non-positive intrinsics -> `invalid_camera_intrinsics`.
    with pytest.raises(ShotDiagError) as exc:
        SD.intrinsics_from_spec(-50.0, 36.0, 832, 480)
    assert exc.value.evidence["clause"] == "invalid_camera_intrinsics"

    # Invalid camera matrix -> `invalid_camera_matrix`.
    with pytest.raises(ShotDiagError) as exc:
        SD.blender_to_opencv_pose(np.zeros((4, 4)))
    assert exc.value.evidence["clause"] == "invalid_camera_matrix"

    # Invalid dilation fraction -> `invalid_dilation_fraction`.
    with pytest.raises(ShotDiagError) as exc:
        SD.dilate_mask_proportional(np.ones((16, 16), dtype=bool), dilation_frac=1.5)
    assert exc.value.evidence["clause"] == "invalid_dilation_fraction"

    # Mismatched correspondence lengths -> `correspondence_length_mismatch`.
    with pytest.raises(ShotDiagError) as exc:
        SD.estimate_pair_pose(np.zeros((10, 2)), np.zeros((9, 2)), scaled["K"])
    assert exc.value.evidence["clause"] == "correspondence_length_mismatch"

    dummy_frames = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(3)]
    mats_two = _orbit_matrices(n_frames=2)

    # Frame count mismatch -> `frame_count_mismatch`.
    with pytest.raises(ShotDiagError) as exc:
        SD.measure_camera_from_frames(dummy_frames, mats_two)
    assert exc.value.evidence["clause"] == "frame_count_mismatch"

    # Missing ground-truth camera without `--static` -> `no_ground_truth_camera`.
    with pytest.raises(ShotDiagError) as exc:
        SD.measure_camera_from_frames(dummy_frames, None, is_static=False)
    assert exc.value.evidence["clause"] == "no_ground_truth_camera"

    # Empty / 1-frame / bad-shape / size-mismatch refusals.
    with pytest.raises(ShotDiagError) as exc:
        SD.measure_camera_from_frames([], mats_two)
    assert exc.value.evidence["clause"] == "empty_frames"

    with pytest.raises(ShotDiagError) as exc:
        SD.measure_camera_from_frames(dummy_frames[:1], mats_two[:1])
    assert exc.value.evidence["clause"] == "clip_has_no_camera_pair"

    with pytest.raises(ShotDiagError) as exc:
        SD.measure_camera_from_frames([np.zeros((32, 32), dtype=np.uint8)] * 2, mats_two)
    assert exc.value.evidence["clause"] == "frame_shape_invalid"

    with pytest.raises(ShotDiagError) as exc:
        SD.measure_camera_from_frames(
            [np.zeros((32, 32, 3), dtype=np.uint8), np.zeros((48, 32, 3), dtype=np.uint8)],
            mats_two,
        )
    assert exc.value.evidence["clause"] == "frame_sizes_differ"

    # Directory & manifest refusals (`frames_not_numerically_named`, `render_run_missing_manifest`),
    # plus write-ordering check: refused CLI run leaves no `--out` directory behind.
    bad_dir = tmp_path / "bad_frames"
    bad_dir.mkdir()
    pngio.write_png(str(bad_dir / "contact_strip.png"), dummy_frames[0])
    with pytest.raises(ShotDiagError) as exc:
        SD.load_numbered_rgb_frames(str(bad_dir))
    assert exc.value.evidence["clause"] == "frames_not_numerically_named"

    empty_run = tmp_path / "empty_run"
    empty_run.mkdir()
    with pytest.raises(ShotDiagError) as exc:
        SD.load_stage_render_run(str(empty_run))
    assert exc.value.evidence["clause"] == "render_run_missing_manifest"

    refused_out = tmp_path / "never_created_dir" / "out.json"
    with pytest.raises(ShotDiagError) as exc:
        MS.main(["--frames", str(bad_dir), "--out", str(refused_out)])
    assert exc.value.evidence["clause"] == "no_ground_truth_camera"
    assert not refused_out.parent.exists()


def test_c12_followed_field_is_no_threshold_string_and_carries_no_verdict_boolean():
    """C12: Fails if `followed` becomes a boolean or invents a pass/fail threshold before calibration."""
    pts_w = _two_plane_points(seed=53, n_per_plane=40)
    intr = SD.intrinsics_from_spec(50.0, 36.0, 832, 480)
    k_mat = intr["K"]
    mats = _orbit_matrices(n_frames=3)
    gt_poses = [SD.blender_to_opencv_pose(m) for m in mats]
    p0 = _project_points_cv(pts_w, *gt_poses[0], k_mat)
    pairs = [
        SD.estimate_pair_pose(p0, _project_points_cv(pts_w, *gt_poses[t], k_mat), k_mat)
        for t in range(1, len(gt_poses))
    ]
    cam = SD.score_camera_trajectory(gt_poses, pairs, intrinsics_info=intr)
    rec = SD.build_shot_record(cam, label="shot")

    assert rec["camera"]["followed"] == "NO THRESHOLD — CALIBRATION NOT YET RUN"
    assert not isinstance(rec["camera"]["followed"], bool)
    # Only per-pair `fired` may be boolean; no top-level or summary verdict boolean may exist.
    for key, val in rec["camera"].items():
        if key != "per_pair":
            assert not isinstance(val, bool), f"unexpected boolean camera field {key!r}"
    for key, val in rec.items():
        assert not isinstance(val, bool), f"unexpected boolean record field {key!r}"
