"""Shot diagnostics: Tier A two-view camera error and masked subject identity.

Both instruments here are **diagnostics** (`CLAUDE.md`):
- Camera error is printed first in every report and carries no pass/fail threshold;
  `followed` reads `"NO THRESHOLD — CALIBRATION NOT YET RUN"` until calibration runs on
  the F0, N and G populations (`docs/dispatches/shot-diagnostics-design.md` §2.5).
- Masked identity rides under the camera block, never without it, and **gates nothing**.
  This module defines **no `GateFailure` subclass** (`ShotDiagError` is a plain input/shape
  refusal with `gate: None`). Weight licence checks live in `armature_core.measure_weights`
  (`MeasureWeightGate`, gate `MEASURE_WEIGHT`).
- Neither instrument ever emits a number for a frame or pair where its detector did not
  fire (`fired: False` -> `null` metrics, with fired counts beside every summary).

Tier B (`facebook/map-anything-apache`, feed-forward multi-view pose recovery) is NOT
built in this module; it is reserved for a later grant run compared against Tier A.
"""

import hashlib
import importlib
import json
import math
import os

import numpy as np

from . import framing
from . import measure_weights
from .errors import ArmatureError

TOOL_VERSION = "shotdiag.1"

FOLLOWED_NO_THRESHOLD = "NO THRESHOLD — CALIBRATION NOT YET RUN"
DIAGNOSTIC_STATUS = "DIAGNOSTIC — every number here gates nothing"
IDENTITY_EYE_NOTE = "DIAGNOSTIC — gates nothing; identity is judged by eye on the sheet above"
FLOOR_NOTE = "NOT A VERDICT"

#: Neutral composite plate matching `SURVEY_PLATE = (154, 154, 157)` (`sheet_compose.py`).
IDENTITY_PLATE_RGB = (154, 154, 157)

DINOV2_REPO_ID = "facebook/dinov2-base"
DINOV2_REVISION = "f9e44c81"
DINOV2_FILENAME = "model.safetensors"
DINOV2_LABEL = "DINOv2-B/14"
DINOV2_INPUT_SIZE = 224
DINOV2_PATCH_SIZE = 14
DINOV2_GRID_SIDE = DINOV2_INPUT_SIZE // DINOV2_PATCH_SIZE  # 16x16 = 256 tokens

DEFAULT_MASK_DILATION_FRAC = 0.05
DEFAULT_CROP_MARGIN_FRAC = 0.10
MIN_SOLVER_INLIERS = 8
GRIC_SIGMA_PX = 1.5
LOWE_RATIO = 0.75

#: Blender camera axes (+X right, +Y up, -Z forward) -> OpenCV (+X right, +Y down, +Z forward).
BLENDER_TO_OPENCV_AXES = np.diag([1.0, -1.0, -1.0])


class ShotDiagError(ArmatureError):
    """Input or record-shape refusal in `shotdiag` (`gate: None`; never gates on a score)."""


def _cv2_module():
    import cv2

    return cv2


def _pil_image_module():
    from PIL import Image

    return Image


def _finite_positive(v):
    return (
        isinstance(v, (int, float))
        and not isinstance(v, bool)
        and math.isfinite(float(v))
        and float(v) > 0.0
    )


def _stats_over_fired(values):
    """Median, p90, max and count over finite numbers from fired frames/pairs only."""
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {"n": 0, "median": None, "p90": None, "max": None}
    arr = np.asarray(clean, dtype=np.float64)
    return {
        "n": int(arr.size),
        "median": float(np.median(arr)),
        "p90": float(np.percentile(arr, 90.0)),
        "max": float(np.max(arr)),
    }


# ===================================================================== camera conventions


def blender_to_opencv_pose(matrix_world, *, convert_axes=True):
    """Convert a 4x4 Blender `matrix_world` (cam->world) to OpenCV `(R_cv, C_world)`.

    Blender cameras look along `-Z` with `+Y` up; OpenCV cameras look along `+Z` with
    `+Y` down. Post-multiplying the camera-to-world rotation by `diag(1, -1, -1)` flips
    the camera's local Y and Z axes while keeping `det(R_cv) == +1` and leaving the
    world-space camera centre `C_world` unchanged. `convert_axes=False` is exposed only
    so tests can demonstrate the ~180-degree error when the convention flip is omitted.
    """
    try:
        m = np.asarray(matrix_world, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ShotDiagError(
            f"camera_matrix is not a numeric 4x4 array: {exc}",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "invalid_camera_matrix",
            },
        ) from exc

    if m.shape != (4, 4) or not np.all(np.isfinite(m)):
        raise ShotDiagError(
            f"camera_matrix must be a finite (4, 4) matrix; got shape {m.shape}",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "invalid_camera_matrix",
                "shape": list(m.shape),
            },
        )

    r_raw = m[:3, :3]
    det = float(np.linalg.det(r_raw))
    ortho_err = float(np.linalg.norm(r_raw.T @ r_raw - np.eye(3), ord="fro"))
    if det <= 0.0 or abs(det - 1.0) > 5e-2 or ortho_err > 5e-2:
        raise ShotDiagError(
            f"camera_matrix[:3, :3] is not a proper SO(3) rotation "
            f"(det={det:.6g}, ortho_err={ortho_err:.6g})",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "invalid_camera_matrix",
                "det": det,
                "ortho_err": ortho_err,
            },
        )

    u, _, vt = np.linalg.svd(r_raw)
    r_bl = u @ np.diag([1.0, 1.0, float(np.linalg.det(u @ vt))]) @ vt
    r_cv = (r_bl @ BLENDER_TO_OPENCV_AXES) if convert_axes else r_bl.copy()
    c_world = m[:3, 3].astype(np.float64).copy()
    return r_cv, c_world


def geodesic_angle_deg(r_mat):
    """Geodesic angle in degrees of a 3x3 rotation matrix on SO(3), in `[0, 180]`."""
    r = np.asarray(r_mat, dtype=np.float64)
    cos_val = max(-1.0, min(1.0, (float(np.trace(r)) - 1.0) * 0.5))
    return math.degrees(math.acos(cos_val))


def direction_angle_deg(vec_a, vec_b):
    """Angle in degrees between two non-zero 3-vectors, or `None` if either vanishes."""
    a = np.asarray(vec_a, dtype=np.float64).reshape(3)
    b = np.asarray(vec_b, dtype=np.float64).reshape(3)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 1e-12 or nb <= 1e-12:
        return None
    cos_val = max(-1.0, min(1.0, float(np.dot(a, b) / (na * nb))))
    return math.degrees(math.acos(cos_val))


def intrinsics_from_spec(
    lens_mm,
    sensor_mm,
    spec_width,
    spec_height,
    *,
    frame_width=None,
    frame_height=None,
):
    """Derive OpenCV pinhole matrix `K` from `framing.half_fovs` (Blender AUTO fit).

    When the generated frame resolution `(frame_width, frame_height)` differs from the
    spec resolution at the same aspect ratio, `K` is scaled proportionally and `k_scale`
    is recorded. When aspect ratios disagree, an unknown crop occurred and `K` is
    unknowable — refused with clause `aspect_ratio_mismatch`.
    """
    if not (
        _finite_positive(lens_mm)
        and _finite_positive(sensor_mm)
        and _finite_positive(spec_width)
        and _finite_positive(spec_height)
    ):
        raise ShotDiagError(
            f"intrinsics require finite positive lens_mm={lens_mm!r}, "
            f"sensor_mm={sensor_mm!r}, spec=({spec_width!r}, {spec_height!r})",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "invalid_camera_intrinsics",
                "lens_mm": lens_mm,
                "sensor_mm": sensor_mm,
                "spec_width": spec_width,
                "spec_height": spec_height,
            },
        )

    hx, hy = framing.half_fovs(
        float(lens_mm), float(sensor_mm), float(spec_width), float(spec_height)
    )
    fx_spec = (float(spec_width) * 0.5) / math.tan(hx)
    fy_spec = (float(spec_height) * 0.5) / math.tan(hy)

    fw = float(spec_width) if frame_width is None else float(frame_width)
    fh = float(spec_height) if frame_height is None else float(frame_height)
    if not (_finite_positive(fw) and _finite_positive(fh)):
        raise ShotDiagError(
            f"frame dimensions must be finite positive numbers; got ({frame_width!r}, {frame_height!r})",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "invalid_camera_intrinsics",
                "frame_width": frame_width,
                "frame_height": frame_height,
            },
        )

    spec_aspect = float(spec_width) / float(spec_height)
    frame_aspect = fw / fh
    if abs(frame_aspect - spec_aspect) / spec_aspect > 0.01:
        raise ShotDiagError(
            f"frame aspect {fw:.0f}x{fh:.0f} ({frame_aspect:.4f}) disagrees with "
            f"spec aspect {spec_width}x{spec_height} ({spec_aspect:.4f}); an unrecorded "
            f"crop makes K unknowable",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "aspect_ratio_mismatch",
                "spec_resolution": [int(spec_width), int(spec_height)],
                "frame_resolution": [int(round(fw)), int(round(fh))],
                "spec_aspect": spec_aspect,
                "frame_aspect": frame_aspect,
            },
        )

    sx = fw / float(spec_width)
    sy = fh / float(spec_height)
    fx = fx_spec * sx
    fy = fy_spec * sy
    cx = fw * 0.5
    cy = fh * 0.5
    k_mat = np.array(
        [[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64
    )
    return {
        "K": k_mat,
        "fx": float(fx),
        "fy": float(fy),
        "cx": float(cx),
        "cy": float(cy),
        "lens_mm": float(lens_mm),
        "sensor_mm": float(sensor_mm),
        "spec_resolution": [int(spec_width), int(spec_height)],
        "frame_resolution": [int(round(fw)), int(round(fh))],
        "k_scale": float(sx),
    }


def dilate_mask_proportional(mask, dilation_frac=DEFAULT_MASK_DILATION_FRAC):
    """Dilate a 2D boolean mask by `dilation_frac` of the mask's own bbox diagonal."""
    if (
        not isinstance(dilation_frac, (int, float))
        or isinstance(dilation_frac, bool)
        or not math.isfinite(float(dilation_frac))
        or float(dilation_frac) < 0.0
        or float(dilation_frac) > 1.0
    ):
        raise ShotDiagError(
            f"dilation_frac={dilation_frac!r} must be a finite fraction in [0, 1]",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "invalid_dilation_fraction",
                "dilation_frac": dilation_frac,
            },
        )

    m = np.asarray(mask) > 0
    if m.ndim != 2 or not m.any() or float(dilation_frac) == 0.0:
        return m.copy(), 0

    ys, xs = np.nonzero(m)
    diag = math.hypot(
        float(int(xs.max()) - int(xs.min()) + 1),
        float(int(ys.max()) - int(ys.min()) + 1),
    )
    radius_px = max(1, int(math.ceil(float(dilation_frac) * diag)))
    cv2 = _cv2_module()
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * radius_px + 1, 2 * radius_px + 1)
    )
    dilated = cv2.dilate(m.astype(np.uint8), kernel) > 0
    return dilated, int(radius_px)


def filter_correspondences_by_masks(
    pts0, ptst, mask0, maskt, *, dilation_frac=DEFAULT_MASK_DILATION_FRAC
):
    """Drop correspondence pairs whose endpoint in frame 0 or frame t hits the dilated mask."""
    p0 = np.asarray(pts0, dtype=np.float64)
    pt = np.asarray(ptst, dtype=np.float64)
    if len(p0) != len(pt):
        raise ShotDiagError(
            f"correspondence arrays differ in length ({len(p0)} vs {len(pt)})",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "correspondence_length_mismatch",
                "len_pts0": len(p0),
                "len_ptst": len(pt),
            },
        )
    if len(p0) == 0:
        return p0.reshape(0, 2), pt.reshape(0, 2)

    d0, _ = dilate_mask_proportional(mask0, dilation_frac=dilation_frac)
    dt, _ = dilate_mask_proportional(maskt, dilation_frac=dilation_frac)
    h0, w0 = d0.shape
    ht, wt = dt.shape

    x0 = np.clip(np.rint(p0[:, 0]).astype(np.intp), 0, w0 - 1)
    y0 = np.clip(np.rint(p0[:, 1]).astype(np.intp), 0, h0 - 1)
    xt = np.clip(np.rint(pt[:, 0]).astype(np.intp), 0, wt - 1)
    yt = np.clip(np.rint(pt[:, 1]).astype(np.intp), 0, ht - 1)

    keep = (~d0[y0, x0]) & (~dt[yt, xt])
    return p0[keep], pt[keep]


# ============================================================ Tier A two-view geometry


def _homography_residuals(h_mat, p0, pt):
    """`(sym_px_dist, gric_e_sq)` for a 3x3 homography `h_mat` on `(N, 2)` points."""
    n = len(p0)
    ones = np.ones((n, 1), dtype=np.float64)
    x0 = np.hstack([p0, ones])
    xt = np.hstack([pt, ones])

    hx0 = (h_mat @ x0.T).T
    z_fwd = hx0[:, 2:3]
    valid_fwd = np.abs(z_fwd[:, 0]) > 1e-12
    pred_t = np.where(valid_fwd[:, None], hx0[:, :2] / np.where(valid_fwd[:, None], z_fwd, 1.0), 1e6)

    h_inv = np.linalg.inv(h_mat)
    hinv_xt = (h_inv @ xt.T).T
    z_bwd = hinv_xt[:, 2:3]
    valid_bwd = np.abs(z_bwd[:, 0]) > 1e-12
    pred_0 = np.where(
        valid_bwd[:, None], hinv_xt[:, :2] / np.where(valid_bwd[:, None], z_bwd, 1.0), 1e6
    )

    d_fwd_sq = np.sum((pred_t - pt) ** 2, axis=1)
    d_bwd_sq = np.sum((pred_0 - p0) ** 2, axis=1)
    sym_px = 0.5 * (np.sqrt(d_fwd_sq) + np.sqrt(d_bwd_sq))
    # Under isotropic N(0, sigma^2 I_2) per view, E[d_fwd_sq + d_bwd_sq] = 8 sigma^2,
    # so dividing by 4 gives E[e_sq / sigma^2] = 2 = r - d_H.
    e_sq = 0.25 * (d_fwd_sq + d_bwd_sq)
    return sym_px, e_sq


def _sampson_residuals(e_mat, k_inv, p0, pt):
    """First-order Sampson epipolar squared pixel error (`chi^2_1` scaled by `sigma^2`)."""
    n = len(p0)
    ones = np.ones((n, 1), dtype=np.float64)
    x0 = np.hstack([p0, ones])
    xt = np.hstack([pt, ones])
    f_mat = k_inv.T @ e_mat @ k_inv

    fx0 = (f_mat @ x0.T).T
    fxt = (f_mat.T @ xt.T).T
    alg = np.sum(xt * fx0, axis=1)
    denom = fx0[:, 0] ** 2 + fx0[:, 1] ** 2 + fxt[:, 0] ** 2 + fxt[:, 1] ** 2
    return np.where(denom > 1e-18, (alg ** 2) / np.where(denom > 1e-18, denom, 1.0), 1e12)


def _decompose_essential_cheiral(e_mat, k_inv, p0, pt, inlier_mask):
    """Decompose `E` into `(r_21, t_21, cheiral_mask)` with positive finite ray depths.

    Pure-rotation pairs have parallel rays (`denom ~ 0`), yielding zero cheiral points so
    GRIC / model selection cleanly routes pure rotation to `H` (`t_unobservable`).
    """
    u, _, vt = np.linalg.svd(e_mat)
    if np.linalg.det(u) < 0.0:
        u = -u
    if np.linalg.det(vt) < 0.0:
        vt = -vt
    w_mat = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    r1 = u @ w_mat @ vt
    r2 = u @ w_mat.T @ vt
    t_u = u[:, 2]

    n = len(p0)
    ones = np.ones((n, 1), dtype=np.float64)
    q0 = (k_inv @ np.hstack([p0, ones]).T).T
    qt = (k_inv @ np.hstack([pt, ones]).T).T

    best = None
    best_count = -1
    for r_cand in (r1, r2):
        a = (r_cand @ q0.T).T
        b = qt
        aa = np.sum(a * a, axis=1)
        bb = np.sum(b * b, axis=1)
        ab = np.sum(a * b, axis=1)
        denom = aa * bb - ab * ab
        # Require non-degenerate ray intersection angle (> ~0.03 deg) and finite depth.
        non_parallel = denom > (1e-7 * aa * bb)
        safe_denom = np.where(non_parallel, denom, 1.0)
        for sign in (1.0, -1.0):
            t_cand = sign * t_u
            at = a @ t_cand
            bt = b @ t_cand
            s0 = (ab * bt - bb * at) / safe_denom
            st = (aa * bt - ab * at) / safe_denom
            cheiral = (
                inlier_mask
                & non_parallel
                & (s0 > 1e-4)
                & (st > 1e-4)
                & (s0 < 2000.0)
                & (st < 2000.0)
            )
            cnt = int(np.sum(cheiral))
            if cnt > best_count:
                best_count = cnt
                best = (r_cand, t_cand / float(np.linalg.norm(t_cand)), cheiral)
    return best


def _rotation_from_homography(h_mat, k_mat, k_inv, p0, pt, inlier_mask):
    """Project `K^-1 H K` onto `SO(3)` with sign chosen by positive ray chirality."""
    m = k_inv @ h_mat @ k_mat
    idx = np.flatnonzero(inlier_mask)
    if idx.size == 0:
        idx = np.arange(len(p0))
    ones = np.ones((idx.size, 1), dtype=np.float64)
    q0 = (k_inv @ np.hstack([p0[idx], ones]).T).T
    qt = (k_inv @ np.hstack([pt[idx], ones]).T).T
    dots = np.sum(((m @ q0.T).T) * qt, axis=1)
    if float(np.median(dots)) < 0.0:
        m = -m
    u, _, vt = np.linalg.svd(m)
    r_21 = u @ np.diag([1.0, 1.0, float(np.linalg.det(u @ vt))]) @ vt
    return r_21


def _gric_score(e_sq, sigma_px, d_manifold, k_params, n_matches):
    """Torr (1998) GRIC score in R^4 (`r = 4`). Lower is better."""
    r_data = 4.0
    sigma_sq = float(sigma_px) ** 2
    cap = 4.0 * (r_data - float(d_manifold))
    data_term = float(np.sum(np.minimum(e_sq / sigma_sq, cap)))
    dim_term = math.log(4.0) * float(d_manifold) * float(n_matches)
    param_term = float(k_params) * math.log(max(int(n_matches), 2))
    return data_term + dim_term + param_term


def estimate_pair_pose(
    pts0,
    ptst,
    k_mat,
    *,
    sigma_px=GRIC_SIGMA_PX,
    min_inliers=MIN_SOLVER_INLIERS,
):
    """Fit both `E` (known `K`) and `H` on background correspondences and select via GRIC.

    Returns `R_rel` (`R_0.T @ R_t`) and `t_dir_in_f0` (`R_0.T @ (C_t - C_0)` unit vector,
    or `None` with `tdir_reason="t_unobservable"` when `H` wins). Also computes
    `parallax_residual_px`: the median symmetric transfer residual of a single least-squares
    homography across all rigid background inliers (`E_inliers | H_inliers`), which is ~0
    for a static hold or pure rotation and > 0 when a camera translates over 3D structure.
    """
    p0 = np.asarray(pts0, dtype=np.float64)
    pt = np.asarray(ptst, dtype=np.float64)
    if p0.ndim != 2 or pt.ndim != 2 or p0.shape[1] != 2 or pt.shape[1] != 2 or len(p0) != len(pt):
        raise ShotDiagError(
            f"pts0 {p0.shape} and ptst {pt.shape} must be matching (N, 2) correspondence arrays",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "correspondence_length_mismatch",
                "shape_pts0": list(p0.shape),
                "shape_ptst": list(pt.shape),
            },
        )

    n_matches = int(len(p0))
    if n_matches < int(min_inliers):
        return {
            "fired": False,
            "n_matches": n_matches,
            "n_inliers": 0,
            "model": "none",
            "gric_e": None,
            "gric_h": None,
            "R_rel": None,
            "t_dir_in_f0": None,
            "tdir_reason": "not_fired",
            "parallax_residual_px": None,
        }

    cv2 = _cv2_module()
    k = np.asarray(k_mat, dtype=np.float64)
    k_inv = np.linalg.inv(k)
    thresh_px = 2.5 * float(sigma_px)

    # ---- Homography candidate (d=2, k=8)
    h_ok = False
    gric_h = None
    h_inliers = np.zeros(n_matches, dtype=bool)
    h_mat = None
    try:
        h_cand, _ = cv2.findHomography(
            p0, pt, method=cv2.RANSAC, ransacReprojThreshold=thresh_px, maxIters=2000, confidence=0.999
        )
        if (
            h_cand is not None
            and h_cand.shape == (3, 3)
            and np.all(np.isfinite(h_cand))
            and abs(float(np.linalg.det(h_cand))) > 1e-12
        ):
            sym_px, e_h_sq = _homography_residuals(h_cand, p0, pt)
            h_inliers = sym_px <= thresh_px
            if int(np.sum(h_inliers)) >= int(min_inliers):
                h_ok = True
                h_mat = h_cand
                gric_h = _gric_score(e_h_sq, sigma_px, d_manifold=2, k_params=8, n_matches=n_matches)
    except Exception:  # noqa: BLE001 — singular configuration leaves h_ok=False
        h_ok = False

    # ---- Essential matrix candidate with known K (d=3, k=5)
    e_ok = False
    gric_e = None
    e_cheiral_inliers = np.zeros(n_matches, dtype=bool)
    best_r21 = None
    best_t21 = None
    try:
        e_raw, _ = cv2.findEssentialMat(
            p0, pt, k, method=cv2.RANSAC, prob=0.999, threshold=thresh_px
        )
        if (
            e_raw is not None
            and e_raw.ndim == 2
            and e_raw.shape[1] == 3
            and e_raw.shape[0] >= 3
            and e_raw.shape[0] % 3 == 0
        ):
            best_cheiral_n = -1
            for row0 in range(0, e_raw.shape[0], 3):
                e_cand = e_raw[row0 : row0 + 3, :]
                if not np.all(np.isfinite(e_cand)) or float(np.linalg.norm(e_cand)) <= 1e-12:
                    continue
                e_sampson_sq = _sampson_residuals(e_cand, k_inv, p0, pt)
                epipolar_inliers = np.sqrt(e_sampson_sq) <= thresh_px
                if int(np.sum(epipolar_inliers)) < int(min_inliers):
                    continue
                r21_c, t21_c, cheiral_c = _decompose_essential_cheiral(
                    e_cand, k_inv, p0, pt, epipolar_inliers
                )
                cnt = int(np.sum(cheiral_c))
                if cnt > best_cheiral_n:
                    best_cheiral_n = cnt
                    if cnt >= int(min_inliers):
                        # Non-cheiral points act as outliers under E (capped in GRIC).
                        e_sq_cheiral = np.where(cheiral_c, e_sampson_sq, 1e9)
                        e_ok = True
                        e_cheiral_inliers = cheiral_c
                        best_r21 = r21_c
                        best_t21 = t21_c
                        gric_e = _gric_score(
                            e_sq_cheiral, sigma_px, d_manifold=3, k_params=5, n_matches=n_matches
                        )
    except Exception:  # noqa: BLE001 — degenerate configuration leaves e_ok=False
        e_ok = False

    if not h_ok and not e_ok:
        return {
            "fired": False,
            "n_matches": n_matches,
            "n_inliers": 0,
            "model": "none",
            "gric_e": gric_e,
            "gric_h": gric_h,
            "R_rel": None,
            "t_dir_in_f0": None,
            "tdir_reason": "not_fired",
            "parallax_residual_px": None,
        }

    # Parallax residual across ALL rigid background inliers (`e_cheiral_inliers | h_inliers`)
    # using a single least-squares homography (method=0) so multi-plane parallax is never
    # hidden by RANSAC locking onto one dominant plane.
    rigid_bg = e_cheiral_inliers | h_inliers
    parallax_px = None
    if int(np.sum(rigid_bg)) >= 4:
        h_ls, _ = cv2.findHomography(p0[rigid_bg], pt[rigid_bg], method=0)
        if (
            h_ls is not None
            and h_ls.shape == (3, 3)
            and np.all(np.isfinite(h_ls))
            and abs(float(np.linalg.det(h_ls))) > 1e-12
        ):
            sym_ls, _ = _homography_residuals(h_ls, p0[rigid_bg], pt[rigid_bg])
            parallax_px = float(np.median(sym_ls))

    choose_h = h_ok and (not e_ok or gric_h <= gric_e)
    if choose_h:
        r_21 = _rotation_from_homography(h_mat, k, k_inv, p0, pt, h_inliers)
        r_rel = r_21.T
        return {
            "fired": True,
            "n_matches": n_matches,
            "n_inliers": int(np.sum(h_inliers)),
            "model": "H",
            "gric_e": gric_e,
            "gric_h": gric_h,
            "R_rel": r_rel,
            "t_dir_in_f0": None,
            "tdir_reason": "t_unobservable",
            "parallax_residual_px": parallax_px,
        }

    r_rel = best_r21.T
    c_dir_f0 = -r_rel @ best_t21
    c_dir_f0 = c_dir_f0 / float(np.linalg.norm(c_dir_f0))
    return {
        "fired": True,
        "n_matches": n_matches,
        "n_inliers": int(np.sum(e_cheiral_inliers)),
        "model": "E",
        "gric_e": gric_e,
        "gric_h": gric_h,
        "R_rel": r_rel,
        "t_dir_in_f0": c_dir_f0,
        "tdir_reason": None,
        "parallax_residual_px": parallax_px,
    }


def score_camera_trajectory(
    gt_poses_cv,
    pair_estimates,
    *,
    consecutive_estimates=None,
    gt_source="stage_render",
    intrinsics_info=None,
    instrument_floor=None,
):
    """Compare anchored relative camera estimates `(0 -> t)` against OpenCV GT poses.

    Gauge alignment is strictly frame-0 anchoring (`R_rel(t) = R_0.T @ R_t` and
    `c_rel(t) = R_0.T @ (C_t - C_0)`): zero parameters are fitted for `rot_err_deg` or
    `tdir_err_deg`, so Sim(3) rotation absorption cannot occur. A single scalar `s` is
    fitted by least squares across fired `E` pairs solely to report scale-fitted `ate`.
    """
    n_frames = len(gt_poses_cv)
    if n_frames < 2 or len(pair_estimates) != n_frames - 1:
        raise ShotDiagError(
            f"score_camera_trajectory expects >=2 GT poses and N-1 pair estimates; "
            f"got {n_frames} poses and {len(pair_estimates)} pairs",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "frame_count_mismatch",
                "n_gt_poses": n_frames,
                "n_pair_estimates": len(pair_estimates),
            },
        )

    r0_gt, c0_gt = gt_poses_cv[0]
    r0_gt = np.asarray(r0_gt, dtype=np.float64)
    c0_gt = np.asarray(c0_gt, dtype=np.float64)

    per_pair = []
    rot_errs = []
    tdir_errs = []
    gt_spans = []
    est_spans = []
    parallax_vals = []
    n_h_unobservable = 0

    est_centres = []
    gt_centres_for_scale = []

    for idx, est in enumerate(pair_estimates):
        frame_t = idx + 1
        rt_gt, ct_gt = gt_poses_cv[frame_t]
        rt_gt = np.asarray(rt_gt, dtype=np.float64)
        ct_gt = np.asarray(ct_gt, dtype=np.float64)

        r_gt_rel = r0_gt.T @ rt_gt
        c_gt_rel = r0_gt.T @ (ct_gt - c0_gt)
        gt_rot_deg = geodesic_angle_deg(r_gt_rel)
        gt_spans.append(gt_rot_deg)

        fired = bool(est.get("fired"))
        model = est.get("model", "none")
        parallax_px = est.get("parallax_residual_px")
        if fired and parallax_px is not None and math.isfinite(float(parallax_px)):
            parallax_vals.append(float(parallax_px))

        if not fired or est.get("R_rel") is None:
            per_pair.append(
                {
                    "frame": frame_t,
                    "fired": False,
                    "n_matches": int(est.get("n_matches", 0)),
                    "n_inliers": int(est.get("n_inliers", 0)),
                    "model": "none",
                    "gric_e": est.get("gric_e"),
                    "gric_h": est.get("gric_h"),
                    "rot_err_deg": None,
                    "tdir_err_deg": None,
                    "tdir_reason": "not_fired",
                    "gt_rot_from_f0_deg": gt_rot_deg,
                    "est_rot_from_f0_deg": None,
                    "parallax_residual_px": None,
                }
            )
            continue

        r_est_rel = np.asarray(est["R_rel"], dtype=np.float64)
        est_rot_deg = geodesic_angle_deg(r_est_rel)
        rot_err = geodesic_angle_deg(r_est_rel.T @ r_gt_rel)
        rot_errs.append(rot_err)
        est_spans.append(est_rot_deg)

        t_vec = est.get("t_dir_in_f0")
        tdir_err = None
        tdir_reason = est.get("tdir_reason")
        if model == "H" or t_vec is None:
            if model == "H":
                n_h_unobservable += 1
                tdir_reason = "t_unobservable"
        else:
            t_arr = np.asarray(t_vec, dtype=np.float64).reshape(3)
            if float(np.linalg.norm(t_arr)) > 1e-12:
                est_centres.append(t_arr)
                gt_centres_for_scale.append(c_gt_rel)
            if float(np.linalg.norm(c_gt_rel)) <= 1e-12:
                tdir_reason = "gt_zero_translation"
            else:
                tdir_err = direction_angle_deg(t_arr, c_gt_rel)
                if tdir_err is not None:
                    tdir_errs.append(tdir_err)
                    tdir_reason = None

        per_pair.append(
            {
                "frame": frame_t,
                "fired": True,
                "n_matches": int(est.get("n_matches", 0)),
                "n_inliers": int(est.get("n_inliers", 0)),
                "model": model,
                "gric_e": est.get("gric_e"),
                "gric_h": est.get("gric_h"),
                "rot_err_deg": rot_err,
                "tdir_err_deg": tdir_err,
                "tdir_reason": tdir_reason,
                "gt_rot_from_f0_deg": gt_rot_deg,
                "est_rot_from_f0_deg": est_rot_deg,
                "parallax_residual_px": (
                    float(parallax_px) if parallax_px is not None else None
                ),
            }
        )

    # Single global scale `s` fitted by 1-DoF least squares for ATE only.
    fitted_scale = None
    ate = None
    if est_centres:
        c_est_mat = np.vstack(est_centres)
        c_gt_mat = np.vstack(gt_centres_for_scale)
        denom = float(np.sum(c_est_mat * c_est_mat))
        if denom > 1e-18:
            fitted_scale = float(np.sum(c_est_mat * c_gt_mat) / denom)
            diffs = fitted_scale * c_est_mat - c_gt_mat
            ate = float(np.sqrt(np.mean(np.sum(diffs * diffs, axis=1))))

    # Consecutive-frame RPE (rotation, degrees) where consecutive estimates fired.
    rpe_rot_errs = []
    if consecutive_estimates is not None and len(consecutive_estimates) == n_frames - 1:
        for idx, cest in enumerate(consecutive_estimates):
            if not cest.get("fired") or cest.get("R_rel") is None:
                continue
            ra_gt, _ = gt_poses_cv[idx]
            rb_gt, _ = gt_poses_cv[idx + 1]
            r_gt_step = np.asarray(ra_gt, dtype=np.float64).T @ np.asarray(rb_gt, dtype=np.float64)
            r_est_step = np.asarray(cest["R_rel"], dtype=np.float64)
            rpe_rot_errs.append(geodesic_angle_deg(r_est_step.T @ r_gt_step))

    n_pairs = n_frames - 1
    n_fired = sum(1 for row in per_pair if row["fired"])
    gt_rot_span = float(max(gt_spans)) if gt_spans else 0.0
    est_rot_span = float(max(est_spans)) if est_spans else None
    span_ratio = (
        float(est_rot_span / gt_rot_span)
        if (est_rot_span is not None and gt_rot_span > 1e-9)
        else None
    )

    out = {
        "tier": "A_opencv_sift_eh",
        "tier_b_note": (
            "Tier B (facebook/map-anything-apache) is not built here; reserved for a "
            "later grant run compared against Tier A"
        ),
        "gt_source": str(gt_source),
        "n_frames": int(n_frames),
        "n_pairs": int(n_pairs),
        "n_fired": int(n_fired),
        "n_tdir_observable": int(len(tdir_errs)),
        "n_rotation_only_t_unobservable": int(n_h_unobservable),
        "rot_err_deg": _stats_over_fired(rot_errs),
        "tdir_err_deg": _stats_over_fired(tdir_errs),
        "rpe_rot_deg": _stats_over_fired(rpe_rot_errs),
        "gt_rot_span_deg": gt_rot_span,
        "est_rot_span_deg": est_rot_span,
        "est_to_gt_rot_span_ratio": span_ratio,
        "fitted_scale": fitted_scale,
        "ate": ate,
        "static_parallax_px": _stats_over_fired(parallax_vals),
        "followed": FOLLOWED_NO_THRESHOLD,
        "intrinsics": (
            {k: v for k, v in intrinsics_info.items() if k != "K"}
            if isinstance(intrinsics_info, dict)
            else None
        ),
        "per_pair": per_pair,
    }
    if instrument_floor is not None:
        out["instrument_floor"] = instrument_floor
    return out


def _detect_masked_sift(frame_rgb, mask, *, dilation_frac=DEFAULT_MASK_DILATION_FRAC):
    """Detect SIFT keypoints/descriptors on `frame_rgb`, dropping points inside dilated `mask`."""
    cv2 = _cv2_module()
    gray = cv2.cvtColor(np.asarray(frame_rgb, dtype=np.uint8), cv2.COLOR_RGB2GRAY)
    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(gray, None)
    if not keypoints or descriptors is None:
        return np.zeros((0, 2), dtype=np.float64), np.zeros((0, 128), dtype=np.float32), 0

    pts = np.array([kp.pt for kp in keypoints], dtype=np.float64)
    desc = np.asarray(descriptors, dtype=np.float32)
    if mask is None:
        return pts, desc, 0

    dilated, radius_px = dilate_mask_proportional(mask, dilation_frac=dilation_frac)
    h, w = dilated.shape
    xs = np.clip(np.rint(pts[:, 0]).astype(np.intp), 0, w - 1)
    ys = np.clip(np.rint(pts[:, 1]).astype(np.intp), 0, h - 1)
    keep = ~dilated[ys, xs]
    return pts[keep], desc[keep], radius_px


def _match_sift_pair(pts0, desc0, ptst, desct, *, ratio=LOWE_RATIO):
    """Symmetric/ratio-tested SIFT matches between two frames."""
    if len(pts0) < 2 or len(ptst) < 2:
        return np.zeros((0, 2), dtype=np.float64), np.zeros((0, 2), dtype=np.float64)
    cv2 = _cv2_module()
    matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    raw = matcher.knnMatch(desc0, desct, k=2)
    idx0 = []
    idxt = []
    used_t = set()
    # Sort by distance so unique target assignment keeps the tightest correspondence.
    good = []
    for pair in raw:
        if len(pair) < 2:
            continue
        m, n = pair[0], pair[1]
        if m.distance < float(ratio) * n.distance:
            good.append(m)
    good.sort(key=lambda m: m.distance)
    for m in good:
        if m.trainIdx in used_t:
            continue
        used_t.add(m.trainIdx)
        idx0.append(m.queryIdx)
        idxt.append(m.trainIdx)
    if not idx0:
        return np.zeros((0, 2), dtype=np.float64), np.zeros((0, 2), dtype=np.float64)
    return pts0[idx0], ptst[idxt]


def measure_camera_from_frames(
    frames,
    gt_camera_matrices=None,
    *,
    lens_mm=50.0,
    sensor_mm=36.0,
    spec_width=None,
    spec_height=None,
    masks=None,
    is_static=False,
    index_map=None,
    mask_dilation_frac=DEFAULT_MASK_DILATION_FRAC,
    sigma_px=GRIC_SIGMA_PX,
    min_inliers=MIN_SOLVER_INLIERS,
):
    """End-to-end Tier A camera recovery on `(H, W, 3)` uint8 frames."""
    seq = list(frames) if frames is not None else []
    if not seq:
        raise ShotDiagError(
            "frames sequence is empty; camera error cannot be measured over zero frames",
            {"gate": None, "andon": "ShotDiagError", "clause": "empty_frames"},
        )
    if len(seq) < 2:
        raise ShotDiagError(
            f"a clip of {len(seq)} frame has no camera pair to measure",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "clip_has_no_camera_pair",
                "n_frames": len(seq),
            },
        )

    arr0 = np.asarray(seq[0], dtype=np.uint8)
    if arr0.ndim != 3 or arr0.shape[2] != 3:
        raise ShotDiagError(
            f"frame 0 must have shape (H, W, 3); got {arr0.shape}",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "frame_shape_invalid",
                "shape": list(arr0.shape),
            },
        )
    fh, fw = int(arr0.shape[0]), int(arr0.shape[1])
    rgb_frames = [arr0]
    for i, f in enumerate(seq[1:], start=1):
        arr = np.asarray(f, dtype=np.uint8)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ShotDiagError(
                f"frame {i} must have shape (H, W, 3); got {arr.shape}",
                {
                    "gate": None,
                    "andon": "ShotDiagError",
                    "clause": "frame_shape_invalid",
                    "frame": i,
                    "shape": list(arr.shape),
                },
            )
        if arr.shape != arr0.shape:
            raise ShotDiagError(
                f"frame {i} has shape {arr.shape}, expected {arr0.shape}",
                {
                    "gate": None,
                    "andon": "ShotDiagError",
                    "clause": "frame_sizes_differ",
                    "frame": i,
                },
            )
        rgb_frames.append(arr)

    n_frames = len(rgb_frames)
    sw = fw if spec_width is None else spec_width
    sh = fh if spec_height is None else spec_height
    intr_info = intrinsics_from_spec(
        lens_mm, sensor_mm, sw, sh, frame_width=fw, frame_height=fh
    )
    k_mat = intr_info["K"]

    if not is_static and not gt_camera_matrices:
        raise ShotDiagError(
            "no ground-truth camera_matrix sequence provided and --static was not set",
            {"gate": None, "andon": "ShotDiagError", "clause": "no_ground_truth_camera"},
        )

    # Align GT matrices and masks via `index_map` when supplied, otherwise require 1:1 count.
    if gt_camera_matrices is not None:
        gt_list = list(gt_camera_matrices)
        if index_map is not None:
            if len(index_map) != n_frames or any(
                (not isinstance(ix, int) or ix < 0 or ix >= len(gt_list)) for ix in index_map
            ):
                raise ShotDiagError(
                    "index_map does not map every generated frame onto a valid GT frame index",
                    {
                        "gate": None,
                        "andon": "ShotDiagError",
                        "clause": "frame_count_mismatch",
                        "n_frames": n_frames,
                        "n_gt": len(gt_list),
                    },
                )
            gt_list = [gt_list[ix] for ix in index_map]
        elif len(gt_list) != n_frames:
            raise ShotDiagError(
                f"generated clip has {n_frames} frames while render GT has {len(gt_list)} "
                f"frames, and no explicit index_map was given",
                {
                    "gate": None,
                    "andon": "ShotDiagError",
                    "clause": "frame_count_mismatch",
                    "n_frames": n_frames,
                    "n_gt": len(gt_list),
                },
            )
        if any(m is None for m in gt_list):
            raise ShotDiagError(
                "one or more render frames carry camera_matrix=None",
                {"gate": None, "andon": "ShotDiagError", "clause": "no_ground_truth_camera"},
            )
        gt_poses_cv = [blender_to_opencv_pose(m) for m in gt_list]
        gt_source = "static" if is_static else "stage_render"
    else:
        eye = np.eye(3, dtype=np.float64)
        zero = np.zeros(3, dtype=np.float64)
        gt_poses_cv = [(eye.copy(), zero.copy()) for _ in range(n_frames)]
        gt_source = "static"

    aligned_masks = None
    if masks is not None:
        mask_list = list(masks)
        if index_map is not None:
            if len(index_map) != n_frames or any(ix < 0 or ix >= len(mask_list) for ix in index_map):
                raise ShotDiagError(
                    "index_map does not map every generated frame onto a valid mask index",
                    {
                        "gate": None,
                        "andon": "ShotDiagError",
                        "clause": "frame_count_mismatch",
                        "n_frames": n_frames,
                        "n_masks": len(mask_list),
                    },
                )
            mask_list = [mask_list[ix] for ix in index_map]
        elif len(mask_list) != n_frames:
            raise ShotDiagError(
                f"generated clip has {n_frames} frames while mask sequence has {len(mask_list)}",
                {
                    "gate": None,
                    "andon": "ShotDiagError",
                    "clause": "frame_count_mismatch",
                    "n_frames": n_frames,
                    "n_masks": len(mask_list),
                },
            )
        cv2 = _cv2_module()
        aligned_masks = []
        for m in mask_list:
            m_arr = (np.asarray(m) > 0).astype(np.uint8)
            if m_arr.shape != (fh, fw):
                m_arr = cv2.resize(m_arr, (fw, fh), interpolation=cv2.INTER_NEAREST)
            aligned_masks.append(m_arr > 0)

    features = []
    dilation_radii = []
    for i, rgb in enumerate(rgb_frames):
        m_i = aligned_masks[i] if aligned_masks is not None else None
        pts_i, desc_i, rad_i = _detect_masked_sift(
            rgb, m_i, dilation_frac=mask_dilation_frac
        )
        features.append((pts_i, desc_i))
        dilation_radii.append(int(rad_i))

    pts0, desc0 = features[0]
    anchored_estimates = []
    consecutive_estimates = []
    for t in range(1, n_frames):
        ptst, desct = features[t]
        m0, mt = _match_sift_pair(pts0, desc0, ptst, desct)
        anchored_estimates.append(
            estimate_pair_pose(m0, mt, k_mat, sigma_px=sigma_px, min_inliers=min_inliers)
        )

        pts_prev, desc_prev = features[t - 1]
        mp, mc = _match_sift_pair(pts_prev, desc_prev, ptst, desct)
        consecutive_estimates.append(
            estimate_pair_pose(mp, mc, k_mat, sigma_px=sigma_px, min_inliers=min_inliers)
        )

    cam_block = score_camera_trajectory(
        gt_poses_cv,
        anchored_estimates,
        consecutive_estimates=consecutive_estimates,
        gt_source=gt_source,
        intrinsics_info=intr_info,
    )
    cam_block["mask_applied"] = "yes" if aligned_masks is not None else "no_mask_provided"
    cam_block["mask_dilation_fraction"] = (
        float(mask_dilation_frac) if aligned_masks is not None else None
    )
    cam_block["mask_dilation_radii_px"] = (
        dilation_radii if aligned_masks is not None else None
    )
    return cam_block


# ============================================================ masked subject identity


def _full_patch_grid(mask_224, patch_size=DINOV2_PATCH_SIZE):
    """Boolean `(256,)` mask of `14x14` tokens lying 100% inside `mask_224`."""
    m = np.asarray(mask_224) > 0
    side = m.shape[0] // patch_size
    blocks = m[: side * patch_size, : side * patch_size].reshape(
        side, patch_size, side, patch_size
    )
    return blocks.all(axis=(1, 3)).reshape(-1)


def _has_native_full_patch(mask, patch_size=DINOV2_PATCH_SIZE):
    """True when `mask` contains at least one contiguous `patch_size x patch_size` all-True block."""
    m = (np.asarray(mask) > 0).astype(np.int32)
    h, w = m.shape
    if h < patch_size or w < patch_size:
        return False
    # Integral image over (H+1, W+1) checks every 14x14 block in O(HW) with pure numpy.
    integ = np.pad(m, ((1, 0), (1, 0)), mode="constant").cumsum(axis=0).cumsum(axis=1)
    block_sums = (
        integ[patch_size:, patch_size:]
        - integ[:-patch_size, patch_size:]
        - integ[patch_size:, :-patch_size]
        + integ[:-patch_size, :-patch_size]
    )
    return bool(np.any(block_sums == patch_size * patch_size))


def _bbox_with_margin(mask, margin_frac):
    """`(x0, y0, x1_exclusive, y1_exclusive)` around `mask > 0` expanded by `margin_frac`."""
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    bw = x1 - x0
    bh = y1 - y0
    mx = int(math.ceil(bw * float(margin_frac)))
    my = int(math.ceil(bh * float(margin_frac)))
    return max(0, x0 - mx), max(0, y0 - my), min(w, x1 + mx), min(h, y1 + my)


def crop_rgba_reference(
    rgba,
    *,
    plate_rgb=IDENTITY_PLATE_RGB,
    margin_frac=DEFAULT_CROP_MARGIN_FRAC,
    out_size=DINOV2_INPUT_SIZE,
):
    """Composite an authored RGBA reference view over `plate_rgb` and crop to `(224, 224)`."""
    arr = np.asarray(rgba, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[2] != 4:
        raise ShotDiagError(
            f"reference view must be 4-channel RGBA (H, W, 4); got {arr.shape}",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "reference_missing_alpha",
                "shape": list(arr.shape),
            },
        )
    alpha_mask = arr[:, :, 3] > 0
    if not alpha_mask.any():
        raise ShotDiagError(
            "reference RGBA carries an all-zero alpha channel",
            {"gate": None, "andon": "ShotDiagError", "clause": "reference_alpha_empty"},
        )

    alpha_f = arr[:, :, 3:4].astype(np.float64) / 255.0
    plate = np.asarray(plate_rgb, dtype=np.float64).reshape(1, 1, 3)
    comp = np.rint(arr[:, :, :3].astype(np.float64) * alpha_f + plate * (1.0 - alpha_f)).astype(
        np.uint8
    )
    x0, y0, x1, y1 = _bbox_with_margin(alpha_mask, margin_frac)
    cv2 = _cv2_module()
    crop_rgb = cv2.resize(
        comp[y0:y1, x0:x1], (int(out_size), int(out_size)), interpolation=cv2.INTER_LINEAR
    )
    crop_mask = (
        cv2.resize(
            alpha_mask[y0:y1, x0:x1].astype(np.uint8),
            (int(out_size), int(out_size)),
            interpolation=cv2.INTER_NEAREST,
        )
        > 0
    )
    tokens = _full_patch_grid(crop_mask)
    if not tokens.any():
        # Ensure at least non-empty alpha interior tokens participate on small reference icons.
        blocks = crop_mask.reshape(
            DINOV2_GRID_SIDE, DINOV2_PATCH_SIZE, DINOV2_GRID_SIDE, DINOV2_PATCH_SIZE
        )
        tokens = blocks.any(axis=(1, 3)).reshape(-1)
    digest = hashlib.sha256(arr.tobytes()).hexdigest()
    return {"rgb": crop_rgb, "token_mask": tokens, "sha256": digest}


def crop_masked_frame(
    frame_rgb,
    mask,
    *,
    plate_rgb=IDENTITY_PLATE_RGB,
    margin_frac=DEFAULT_CROP_MARGIN_FRAC,
    out_size=DINOV2_INPUT_SIZE,
):
    """Composite `frame_rgb` inside `mask` over `plate_rgb`, crop, and check patch occupancy."""
    rgb = np.asarray(frame_rgb, dtype=np.uint8)
    m = np.asarray(mask) > 0
    mask_px = int(np.sum(m))
    if mask_px == 0 or not _has_native_full_patch(m, DINOV2_PATCH_SIZE):
        return {
            "occupied": False,
            "mask_px": mask_px,
            "n_full_patches": 0,
            "rgb": None,
            "token_mask": None,
        }

    plate = np.asarray(plate_rgb, dtype=np.uint8).reshape(1, 1, 3)
    comp = np.where(m[:, :, None], rgb, plate)
    x0, y0, x1, y1 = _bbox_with_margin(m, margin_frac)
    cv2 = _cv2_module()
    crop_rgb = cv2.resize(
        comp[y0:y1, x0:x1], (int(out_size), int(out_size)), interpolation=cv2.INTER_LINEAR
    )
    crop_mask = (
        cv2.resize(
            m[y0:y1, x0:x1].astype(np.uint8),
            (int(out_size), int(out_size)),
            interpolation=cv2.INTER_NEAREST,
        )
        > 0
    )
    tokens = _full_patch_grid(crop_mask)
    n_full = int(np.sum(tokens))
    return {
        "occupied": bool(n_full >= 1),
        "mask_px": mask_px,
        "n_full_patches": n_full,
        "rgb": crop_rgb,
        "token_mask": tokens,
    }


def _crop_background_outside_mask(
    frame_rgb,
    mask,
    *,
    plate_rgb=IDENTITY_PLATE_RGB,
    dilation_frac=DEFAULT_MASK_DILATION_FRAC,
    out_size=DINOV2_INPUT_SIZE,
):
    """Region outside the dilated character mask on the same frame, with inside replaced by plate."""
    rgb = np.asarray(frame_rgb, dtype=np.uint8)
    dilated, _ = dilate_mask_proportional(mask, dilation_frac=dilation_frac)
    outside = ~dilated
    plate = np.asarray(plate_rgb, dtype=np.uint8).reshape(1, 1, 3)
    comp = np.where(outside[:, :, None], rgb, plate)
    cv2 = _cv2_module()
    bg_rgb = cv2.resize(comp, (int(out_size), int(out_size)), interpolation=cv2.INTER_LINEAR)
    bg_mask = (
        cv2.resize(
            outside.astype(np.uint8),
            (int(out_size), int(out_size)),
            interpolation=cv2.INTER_NEAREST,
        )
        > 0
    )
    tokens = _full_patch_grid(bg_mask)
    if not tokens.any():
        tokens = np.ones(DINOV2_GRID_SIDE * DINOV2_GRID_SIDE, dtype=bool)
    return bg_rgb, tokens


def _normalise_vec(v):
    arr = np.asarray(v, dtype=np.float64)
    norms = np.linalg.norm(arr, axis=-1, keepdims=True)
    return arr / np.where(norms > 1e-12, norms, 1.0)


def _embed_one(embedder, rgb_224):
    """Run `embedder(rgb_224)` and return normalised `{"cls": (D,), "patches": (256, D)}`."""
    out = embedder(np.asarray(rgb_224, dtype=np.uint8))
    if isinstance(out, dict):
        cls_v = _normalise_vec(np.asarray(out["cls"], dtype=np.float64).reshape(-1))
        patches_v = _normalise_vec(np.asarray(out["patches"], dtype=np.float64))
        return {"cls": cls_v, "patches": patches_v}
    cls_v = _normalise_vec(np.asarray(out, dtype=np.float64).reshape(-1))
    patches_v = np.tile(cls_v, (DINOV2_GRID_SIDE * DINOV2_GRID_SIDE, 1))
    return {"cls": cls_v, "patches": patches_v}


def _score_against_refs(target_emb, target_tokens, ref_items):
    """Best `(cls_cosine, patch_cosine)` across canonical turnaround views."""
    best_cls = -2.0
    best_patch = -2.0
    t_idx = np.flatnonzero(target_tokens)
    t_patches = target_emb["patches"][t_idx] if t_idx.size else target_emb["patches"]
    for ref in ref_items:
        cls_sim = float(np.dot(target_emb["cls"], ref["emb"]["cls"]))
        r_idx = np.flatnonzero(ref["token_mask"])
        r_patches = ref["emb"]["patches"][r_idx] if r_idx.size else ref["emb"]["patches"]
        sim_mat = t_patches @ r_patches.T
        patch_sim = float(np.mean(np.max(sim_mat, axis=1)))
        if cls_sim > best_cls:
            best_cls = cls_sim
        if patch_sim > best_patch:
            best_patch = patch_sim
    return best_cls, best_patch


def load_dinov2_vitb14_embedder(
    weights_path,
    *,
    repo_id=DINOV2_REPO_ID,
    revision=DINOV2_REVISION,
    weight_table=None,
):
    """Build the DINOv2 ViT-B/14 (`facebook/dinov2-base`) CPU embedder behind two hard checks:

    1. **Presence check (`weights_not_present`):** never downloads weights from any network
       source. A missing or omitted path refuses immediately with `ShotDiagError`.
    2. **Licence load gate (`MeasureWeightGate`, gate `MEASURE_WEIGHT`):** hashes the file
       on disk before any ML library is imported and checks `MEASUREMENT_WEIGHTS`.
    """
    if not weights_path or not os.path.isfile(str(weights_path)):
        raise ShotDiagError(
            f"weights not present: {weights_path!r} — DINOv2 ViT-B/14 "
            f"({repo_id} @ {revision}) is never auto-downloaded; pass an existing "
            f"local model.safetensors file cleared by Gate MEASURE_WEIGHT",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "weights_not_present",
                "weights_path": str(weights_path) if weights_path is not None else None,
                "repo_id": repo_id,
                "revision": revision,
            },
        )

    receipt = measure_weights.gate_measurement_weight(
        weights_path,
        repo_id=repo_id,
        revision=revision,
        table=weight_table,
    )

    try:
        torch = importlib.import_module("torch")
        safetensors_torch = importlib.import_module("safetensors.torch")
        transformers = importlib.import_module("transformers")
    except ImportError as exc:
        raise ShotDiagError(
            f"DINOv2 runtime libraries (torch, safetensors, transformers) are not "
            f"installed in this environment: {exc}",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "dinov2_runtime_unavailable",
                "missing": str(exc),
                "weight_receipt": receipt,
            },
        ) from exc

    cfg = transformers.Dinov2Config(
        hidden_size=768,
        num_hidden_layers=12,
        num_attention_heads=12,
        image_size=DINOV2_INPUT_SIZE,
        patch_size=DINOV2_PATCH_SIZE,
    )
    model = transformers.Dinov2Model(cfg)
    state = safetensors_torch.load_file(str(weights_path), device="cpu")
    model.load_state_dict(state, strict=False)
    model.to("cpu")
    model.eval()

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)

    def _embed(rgb_224):
        arr = np.asarray(rgb_224, dtype=np.float32) / 255.0
        chw = np.transpose(arr, (2, 0, 1))[None, ...]
        normed = (chw - mean) / std
        with torch.no_grad():
            tokens = model(pixel_values=torch.from_numpy(normed)).last_hidden_state[0].cpu().numpy()
        n_spatial = DINOV2_GRID_SIDE * DINOV2_GRID_SIDE
        return {
            "cls": tokens[0].astype(np.float64),
            "patches": tokens[-n_spatial:].astype(np.float64),
        }

    _embed.weight_receipt = receipt
    return _embed


def measure_masked_identity(
    frames,
    masks,
    subject_references,
    decoy_references,
    *,
    embedder=None,
    dinov2_weights_path=None,
    decoy_label="decoy",
    plate_rgb=IDENTITY_PLATE_RGB,
    margin_frac=DEFAULT_CROP_MARGIN_FRAC,
    mask_dilation_frac=DEFAULT_MASK_DILATION_FRAC,
    index_map=None,
    model_label=DINOV2_LABEL,
):
    """Compute masked DINOv2 identity diagnostics and per-frame floors.

    **Gates nothing.** No low score, zero fired count, or floor overlap raises; only
    malformed/missing inputs (`ShotDiagError`, `gate: None`) or disallowed weights
    (`MeasureWeightGate`, inside `load_dinov2_vitb14_embedder`) refuse before scoring.
    """
    frame_list = list(frames) if frames is not None else []
    if not frame_list:
        raise ShotDiagError(
            "frames sequence is empty; masked identity cannot be measured over zero frames",
            {"gate": None, "andon": "ShotDiagError", "clause": "empty_frames"},
        )

    subj_refs_raw = list(subject_references) if subject_references is not None else []
    if not subj_refs_raw:
        raise ShotDiagError(
            "subject_references is empty; masked identity requires >=1 RGBA reference view",
            {"gate": None, "andon": "ShotDiagError", "clause": "missing_subject_reference"},
        )

    decoy_refs_raw = list(decoy_references) if decoy_references is not None else []
    if not decoy_refs_raw:
        raise ShotDiagError(
            "decoy_references is empty; masked identity requires a distinct canonical "
            "character for the decoy floor",
            {"gate": None, "andon": "ShotDiagError", "clause": "missing_decoy_reference"},
        )

    mask_list = list(masks) if masks is not None else []
    if index_map is not None:
        if len(index_map) != len(frame_list) or any(
            ix < 0 or ix >= len(mask_list) for ix in index_map
        ):
            raise ShotDiagError(
                "index_map does not map every generated frame onto a valid mask frame",
                {
                    "gate": None,
                    "andon": "ShotDiagError",
                    "clause": "frame_count_mismatch",
                    "n_frames": len(frame_list),
                    "n_masks": len(mask_list),
                },
            )
        mask_list = [mask_list[ix] for ix in index_map]
    elif len(mask_list) != len(frame_list):
        raise ShotDiagError(
            f"generated clip has {len(frame_list)} frames while masks has {len(mask_list)}",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "frame_count_mismatch",
                "n_frames": len(frame_list),
                "n_masks": len(mask_list),
            },
        )

    arr0 = np.asarray(frame_list[0], dtype=np.uint8)
    if arr0.ndim != 3 or arr0.shape[2] != 3:
        raise ShotDiagError(
            f"frame 0 must have shape (H, W, 3); got {arr0.shape}",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "frame_shape_invalid",
                "shape": list(arr0.shape),
            },
        )
    fh, fw = int(arr0.shape[0]), int(arr0.shape[1])
    rgb_frames = [arr0]
    for i, f in enumerate(frame_list[1:], start=1):
        arr = np.asarray(f, dtype=np.uint8)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ShotDiagError(
                f"frame {i} must have shape (H, W, 3); got {arr.shape}",
                {
                    "gate": None,
                    "andon": "ShotDiagError",
                    "clause": "frame_shape_invalid",
                    "frame": i,
                    "shape": list(arr.shape),
                },
            )
        if arr.shape != arr0.shape:
            raise ShotDiagError(
                f"frame {i} has shape {arr.shape}, expected {arr0.shape}",
                {
                    "gate": None,
                    "andon": "ShotDiagError",
                    "clause": "frame_sizes_differ",
                    "frame": i,
                },
            )
        rgb_frames.append(arr)

    subj_crops = [
        crop_rgba_reference(r, plate_rgb=plate_rgb, margin_frac=margin_frac)
        for r in subj_refs_raw
    ]
    decoy_crops = [
        crop_rgba_reference(r, plate_rgb=plate_rgb, margin_frac=margin_frac)
        for r in decoy_refs_raw
    ]

    subj_digests = {c["sha256"] for c in subj_crops}
    overlap = sorted(subj_digests & {c["sha256"] for c in decoy_crops})
    if overlap:
        raise ShotDiagError(
            "decoy_references contains an image identical to subject_references; "
            "self-comparison invalidates the decoy separation floor",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "decoy_matches_subject_reference",
                "matching_sha256": overlap[0],
            },
        )

    active_embedder = (
        embedder
        if embedder is not None
        else load_dinov2_vitb14_embedder(dinov2_weights_path)
    )

    subj_items = [
        {"emb": _embed_one(active_embedder, c["rgb"]), "token_mask": c["token_mask"]}
        for c in subj_crops
    ]
    decoy_items = [
        {"emb": _embed_one(active_embedder, c["rgb"]), "token_mask": c["token_mask"]}
        for c in decoy_crops
    ]

    # Neutral plate floor (computed once per clip: reference vs solid neutral plate).
    plate_canvas = np.broadcast_to(
        np.asarray(plate_rgb, dtype=np.uint8).reshape(1, 1, 3),
        (DINOV2_INPUT_SIZE, DINOV2_INPUT_SIZE, 3),
    ).copy()
    plate_tokens = np.ones(DINOV2_GRID_SIDE * DINOV2_GRID_SIDE, dtype=bool)
    plate_emb = _embed_one(active_embedder, plate_canvas)
    plate_floor_cls, _ = _score_against_refs(plate_emb, plate_tokens, subj_items)

    cv2 = _cv2_module()
    per_frame = []
    fired_scores = []
    fired_patch_scores = []
    bg_floors = []
    decoy_floors = []

    for i, rgb in enumerate(rgb_frames):
        m_arr = (np.asarray(mask_list[i]) > 0).astype(np.uint8)
        if m_arr.shape != (fh, fw):
            m_arr = cv2.resize(m_arr, (fw, fh), interpolation=cv2.INTER_NEAREST)
        mask_bool = m_arr > 0

        bg_rgb, bg_tokens = _crop_background_outside_mask(
            rgb, mask_bool, plate_rgb=plate_rgb, dilation_frac=mask_dilation_frac
        )
        bg_emb = _embed_one(active_embedder, bg_rgb)
        bg_floor_cls, _ = _score_against_refs(bg_emb, bg_tokens, subj_items)
        bg_floors.append(bg_floor_cls)

        cropped = crop_masked_frame(
            rgb, mask_bool, plate_rgb=plate_rgb, margin_frac=margin_frac
        )
        if not cropped["occupied"]:
            per_frame.append(
                {
                    "frame": i,
                    "fired": False,
                    "status": "BELOW ONE PATCH",
                    "reason": "below_one_patch",
                    "mask_px": cropped["mask_px"],
                    "n_full_patches": cropped["n_full_patches"],
                    "score": None,
                    "patch_score": None,
                    "floors": {
                        "background": bg_floor_cls,
                        "decoy": None,
                        "plate": plate_floor_cls,
                        "max_floor": max(bg_floor_cls, plate_floor_cls),
                    },
                }
            )
            continue

        subj_crop_emb = _embed_one(active_embedder, cropped["rgb"])
        subj_cls, subj_patch = _score_against_refs(
            subj_crop_emb, cropped["token_mask"], subj_items
        )
        decoy_cls, _ = _score_against_refs(
            subj_crop_emb, cropped["token_mask"], decoy_items
        )
        decoy_floors.append(decoy_cls)

        max_floor = max(bg_floor_cls, decoy_cls, plate_floor_cls)
        if subj_cls <= max_floor:
            per_frame.append(
                {
                    "frame": i,
                    "fired": False,
                    "status": "NOT SEPARABLE",
                    "reason": "not_separable_from_floors",
                    "mask_px": cropped["mask_px"],
                    "n_full_patches": cropped["n_full_patches"],
                    "score": None,
                    "patch_score": None,
                    "floors": {
                        "background": bg_floor_cls,
                        "decoy": decoy_cls,
                        "plate": plate_floor_cls,
                        "max_floor": max_floor,
                    },
                }
            )
            continue

        fired_scores.append(subj_cls)
        fired_patch_scores.append(subj_patch)
        per_frame.append(
            {
                "frame": i,
                "fired": True,
                "status": "FIRED",
                "reason": None,
                "mask_px": cropped["mask_px"],
                "n_full_patches": cropped["n_full_patches"],
                "score": subj_cls,
                "patch_score": subj_patch,
                "floors": {
                    "background": bg_floor_cls,
                    "decoy": decoy_cls,
                    "plate": plate_floor_cls,
                    "max_floor": max_floor,
                },
            }
        )

    return {
        "model": str(model_label),
        "variant": f"{DINOV2_REPO_ID}@{DINOV2_REVISION}",
        "input_size_px": DINOV2_INPUT_SIZE,
        "patch_size_px": DINOV2_PATCH_SIZE,
        "plate_rgb_srgb": [int(v) for v in plate_rgb],
        "margin_fraction": float(margin_frac),
        "decoy_label": str(decoy_label),
        "n_frames": len(rgb_frames),
        "n_fired": len(fired_scores),
        "score": _stats_over_fired(fired_scores),
        "patch_score": _stats_over_fired(fired_patch_scores),
        "floor_maxima": {
            "background": float(max(bg_floors)) if bg_floors else None,
            "decoy": float(max(decoy_floors)) if decoy_floors else None,
            "plate": float(plate_floor_cls),
        },
        "status": DIAGNOSTIC_STATUS,
        "reading": IDENTITY_EYE_NOTE,
        "per_frame": per_frame,
    }


def whole_frame_cosine_series(frames, subject_references, embedder, *, plate_rgb=IDENTITY_PLATE_RGB):
    """Unmasked whole-frame CLS cosine helper (used to contrast against masked identity in I1)."""
    cv2 = _cv2_module()
    subj_crops = [crop_rgba_reference(r, plate_rgb=plate_rgb) for r in subject_references]
    subj_items = [
        {"emb": _embed_one(embedder, c["rgb"]), "token_mask": c["token_mask"]}
        for c in subj_crops
    ]
    all_tokens = np.ones(DINOV2_GRID_SIDE * DINOV2_GRID_SIDE, dtype=bool)
    scores = []
    for f in frames:
        resized = cv2.resize(
            np.asarray(f, dtype=np.uint8),
            (DINOV2_INPUT_SIZE, DINOV2_INPUT_SIZE),
            interpolation=cv2.INTER_LINEAR,
        )
        emb = _embed_one(embedder, resized)
        cls_sim, _ = _score_against_refs(emb, all_tokens, subj_items)
        scores.append(cls_sim)
    return scores


# ============================================================ record & directory I/O


def build_shot_record(camera_block, identity_block=None, *, label="shot", source=None):
    """Assemble the canonical `measure_shot` record with camera serialized BEFORE identity.

    Refuses (`ShotDiagError`, clause `identity_without_camera_block`) if `identity_block`
    is present without a `camera_block`. A `camera_block` whose pairs read `fired: False`
    IS accepted.
    """
    if identity_block is not None and not isinstance(camera_block, dict):
        raise ShotDiagError(
            "cannot build a shot diagnostics record carrying an identity block without "
            "a camera block; camera diagnostics always precede identity",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "identity_without_camera_block",
            },
        )
    if not isinstance(camera_block, dict):
        raise ShotDiagError(
            "shot diagnostics record requires a camera block dict",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "no_ground_truth_camera",
            },
        )

    rec = {
        "tool": "measure_shot",
        "tool_version": TOOL_VERSION,
        "label": str(label),
        "source": dict(source or {}),
        "camera": camera_block,
    }
    if identity_block is not None:
        rec["identity"] = identity_block
    rec["status"] = DIAGNOSTIC_STATUS
    return rec


def load_numbered_rgb_frames(directory):
    """Load numerically named `NNNNN.png` lossless frames in integer index order."""
    if not directory or not os.path.isdir(directory):
        raise ShotDiagError(
            f"{directory!r} is not a directory of lossless PNG frames",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "empty_frames",
                "directory": str(directory),
            },
        )
    pngs = [n for n in os.listdir(directory) if n.lower().endswith(".png")]
    bad = [n for n in pngs if not os.path.splitext(n)[0].isdigit()]
    if bad:
        raise ShotDiagError(
            f"{len(bad)} PNG file(s) in {directory} are not numerically named: {sorted(bad)[:5]}",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "frames_not_numerically_named",
                "unnumbered": sorted(bad)[:20],
            },
        )
    if not pngs:
        raise ShotDiagError(
            f"{directory} carries no numbered PNG frames",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "empty_frames",
                "directory": os.path.abspath(directory),
            },
        )

    Image = _pil_image_module()
    ordered = sorted(pngs, key=lambda n: int(os.path.splitext(n)[0]))
    indices = [int(os.path.splitext(n)[0]) for n in ordered]
    frames = []
    for n in ordered:
        with Image.open(os.path.join(directory, n)) as im:
            frames.append(np.asarray(im.convert("RGB"), dtype=np.uint8))
    return frames, indices


def load_stage_render_run(run_dir, *, require_camera_matrices=True):
    """Read `manifest.json`, optional `spec.json`, and `mask/NNNNN.png` from a `stage_render` run."""
    manifest_path = os.path.join(str(run_dir), "manifest.json")
    if not os.path.isfile(manifest_path):
        raise ShotDiagError(
            f"stage_render run directory {run_dir!r} has no manifest.json",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "render_run_missing_manifest",
                "run_dir": str(run_dir),
            },
        )
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    frame_rows = manifest.get("frames")
    if not isinstance(frame_rows, list) or not frame_rows:
        raise ShotDiagError(
            f"manifest.json in {run_dir!r} carries no non-empty frames list",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "render_run_missing_manifest",
                "run_dir": str(run_dir),
            },
        )

    cam_matrices = [row.get("camera_matrix") for row in frame_rows]
    if require_camera_matrices and any(m is None for m in cam_matrices):
        raise ShotDiagError(
            f"manifest.json in {run_dir!r} carries missing per-frame camera_matrix entries",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "no_ground_truth_camera",
                "run_dir": str(run_dir),
            },
        )

    lens_mm = 50.0
    sensor_mm = 36.0
    res = manifest.get("resolution") or [None, None]
    spec_width, spec_height = res[0], res[1]

    spec_path = os.path.join(str(run_dir), "spec.json")
    if os.path.isfile(spec_path):
        with open(spec_path, encoding="utf-8") as fh:
            spec = json.load(fh)
        cam_spec = spec.get("camera") or {}
        lens_mm = float(cam_spec.get("lens_mm", lens_mm))
        sensor_mm = float(cam_spec.get("sensor_mm", sensor_mm))
        if spec_width is None and isinstance(spec.get("render"), dict):
            spec_width = spec["render"].get("width")
            spec_height = spec["render"].get("height")

    masks = None
    mask_dir = os.path.join(str(run_dir), "mask")
    if os.path.isdir(mask_dir):
        pngs = [
            n
            for n in os.listdir(mask_dir)
            if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()
        ]
        if pngs:
            Image = _pil_image_module()
            by_num = {}
            for n in pngs:
                with Image.open(os.path.join(mask_dir, n)) as im:
                    by_num[int(os.path.splitext(n)[0])] = np.asarray(im.convert("L"), dtype=np.uint8) > 127
            masks = []
            for idx, row in enumerate(frame_rows):
                fnum = int(row.get("frame", idx))
                if fnum in by_num:
                    masks.append(by_num[fnum])
            if len(masks) != len(frame_rows):
                masks = None

    return {
        "camera_matrices": cam_matrices,
        "lens_mm": lens_mm,
        "sensor_mm": sensor_mm,
        "spec_width": spec_width,
        "spec_height": spec_height,
        "masks": masks,
        "manifest": manifest,
    }


def load_rgba_references(path_or_dir):
    """Load one RGBA PNG or a directory of RGBA PNG views."""
    if not path_or_dir or not os.path.exists(str(path_or_dir)):
        raise ShotDiagError(
            f"RGBA reference path {path_or_dir!r} does not exist",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "missing_subject_reference",
                "path": str(path_or_dir),
            },
        )
    Image = _pil_image_module()
    paths = []
    if os.path.isfile(path_or_dir):
        paths = [str(path_or_dir)]
    elif os.path.isdir(path_or_dir):
        names = sorted(n for n in os.listdir(path_or_dir) if n.lower().endswith(".png"))
        paths = [os.path.join(path_or_dir, n) for n in names]
    if not paths:
        raise ShotDiagError(
            f"RGBA reference directory {path_or_dir!r} holds no PNG files",
            {
                "gate": None,
                "andon": "ShotDiagError",
                "clause": "missing_subject_reference",
                "path": str(path_or_dir),
            },
        )
    views = []
    for p in paths:
        with Image.open(p) as im:
            if im.mode != "RGBA":
                raise ShotDiagError(
                    f"reference image {p!r} has mode {im.mode!r}; authored RGBA with "
                    f"real alpha is required",
                    {
                        "gate": None,
                        "andon": "ShotDiagError",
                        "clause": "reference_missing_alpha",
                        "path": p,
                        "mode": im.mode,
                    },
                )
            views.append(np.asarray(im, dtype=np.uint8))
    return views
