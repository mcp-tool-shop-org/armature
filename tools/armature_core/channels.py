"""Channel maths — pure numpy, no bpy, no I/O.

Conventions fixed here, each with the finding that fixes it:

  depth   inverse relative, **near = bright** (F19). Normalised min-max over the
          pixels where geometry exists; background is not depth and is written 0
          (black = far), which is a stated convention of this exporter, not a
          retrieved one.
  normal  camera-space, +X right / +Y up / +Z toward the viewer — Blender's own
          camera axes — encoded n*0.5+0.5. A surface square to the camera encodes
          (128, 128, 255). Blender's Normal pass is world-space, so the caller
          hands us the camera rotation and the transform happens here.
  edge    geometric discontinuity derived from depth and normal (F22 — a rendered
          edge pass sidesteps Canny's contrast-sensitive dual-threshold tuning).
          The depth term is **relative to local depth** and the normal term is an
          angle, so no global constant governs a local feature; the silhouette term
          is exact.

`depth` deliberately produces BOTH normalisations. F19 says the ControlNet
convention is per-frame, but per-frame normalisation on a moving camera re-maps the
range every frame. Which one ships is not this module's decision and not this
session's — E01 reports both.
"""

import numpy as np

BACKGROUND_DEPTH = 0.0  # black = far, for pixels with no geometry
SKY_Z = 1e9  # Blender writes 1e10 into the Z pass where nothing was hit


def mask_from_alpha(alpha, threshold=0.5):
    """Exact silhouette. With filter_size ~0 the alpha pass is already binary; the
    threshold exists for materials that render partial coverage, and the caller
    records how many pixels were not already 0 or 1."""
    return (alpha > threshold).astype(np.uint8)


def alpha_binarity(alpha):
    """Diagnostic: fraction of pixels whose alpha is neither 0 nor 1."""
    a = np.asarray(alpha, dtype=np.float32)
    soft = np.logical_and(a > 1e-6, a < 1.0 - 1e-6)
    return float(soft.mean())


def depth_extent(z, mask):
    """(min, max) camera-Z over the pixels where geometry exists, or None."""
    sel = np.logical_and(mask > 0, z < SKY_Z)
    if not sel.any():
        return None
    vals = z[sel]
    return float(vals.min()), float(vals.max())


def normalize_depth(z, mask, z_near, z_far):
    """Inverse relative depth on [0, 1] — near = bright (F19).

    z_near/z_far are the window this frame is normalised against. Passing the
    frame's own extent gives per-frame normalisation; passing the shot's extent
    gives per-shot. Background pixels get BACKGROUND_DEPTH.
    """
    z = np.asarray(z, dtype=np.float64)
    span = float(z_far) - float(z_near)
    if span <= 0:
        # A shot with zero depth extent has no gradient to encode. Everything that
        # is geometry is equally near; say so rather than dividing by zero.
        d = np.where(mask > 0, 1.0, BACKGROUND_DEPTH)
        return d.astype(np.float64)
    d = (float(z_far) - z) / span
    d = np.clip(d, 0.0, 1.0)
    return np.where(mask > 0, d, BACKGROUND_DEPTH)


def encode_u8(x01):
    """[0,1] float -> uint8, half-to-even rounding."""
    return np.clip(np.rint(np.asarray(x01, dtype=np.float64) * 255.0), 0, 255).astype(np.uint8)


def world_normals_to_camera(n_world, cam_rot_3x3):
    """Rotate world-space normals into camera space.

    cam_rot_3x3 is the camera's world rotation R (columns = camera axes in world
    space). Camera-space n = R^T n_world, which puts +Z toward the viewer because
    Blender's camera looks down its own -Z.
    """
    R = np.asarray(cam_rot_3x3, dtype=np.float64).reshape(3, 3)
    flat = np.asarray(n_world, dtype=np.float64).reshape(-1, 3)
    out = flat @ R  # (R^T n) per row == n @ R
    return out.reshape(np.asarray(n_world).shape)


def encode_normal(n_cam, mask):
    """Camera-space normals -> uint8 RGB, background black."""
    n = np.asarray(n_cam, dtype=np.float64)
    norm = np.linalg.norm(n, axis=-1, keepdims=True)
    n = np.divide(n, norm, out=np.zeros_like(n), where=norm > 1e-8)
    rgb = encode_u8(n * 0.5 + 0.5)
    m = np.asarray(mask) > 0
    return np.where(m[..., None], rgb, np.uint8(0))


def _erode3(binary):
    """3x3 binary erosion, numpy only (scipy is not in Blender's python)."""
    m = np.asarray(binary, dtype=bool)
    padded = np.pad(m, 1, mode="constant", constant_values=False)
    out = np.ones_like(m, dtype=bool)
    h, w = m.shape
    for dy in range(3):
        for dx in range(3):
            out &= padded[dy : dy + h, dx : dx + w]
    return out


def silhouette(mask):
    m = np.asarray(mask) > 0
    return np.logical_and(m, np.logical_not(_erode3(m)))


def _neighbour_max(values, mask):
    """Max over the 4-neighbourhood of |value - neighbour|, masked."""
    v = np.asarray(values, dtype=np.float64)
    m = np.asarray(mask) > 0
    out = np.zeros_like(v)
    for axis, shift in ((1, 1), (1, -1), (0, 1), (0, -1)):
        rolled_v = np.roll(v, shift, axis=axis)
        rolled_m = np.roll(m, shift, axis=axis)
        # do not compare across the frame border
        if axis == 1:
            edge = np.zeros_like(m)
            edge[:, 0 if shift == 1 else -1] = True
        else:
            edge = np.zeros_like(m)
            edge[0 if shift == 1 else -1, :] = True
        valid = m & rolled_m & ~edge
        out = np.maximum(out, np.where(valid, np.abs(v - rolled_v), 0.0))
    return out


def _neighbour_min_dot(n_cam, mask):
    """Min over the 4-neighbourhood of the dot product between unit normals."""
    n = np.asarray(n_cam, dtype=np.float64)
    m = np.asarray(mask) > 0
    out = np.ones(n.shape[:2], dtype=np.float64)
    for axis, shift in ((1, 1), (1, -1), (0, 1), (0, -1)):
        rolled_n = np.roll(n, shift, axis=axis)
        rolled_m = np.roll(m, shift, axis=axis)
        if axis == 1:
            edge = np.zeros_like(m)
            edge[:, 0 if shift == 1 else -1] = True
        else:
            edge = np.zeros_like(m)
            edge[0 if shift == 1 else -1, :] = True
        valid = m & rolled_m & ~edge
        dot = np.sum(n * rolled_n, axis=-1)
        out = np.minimum(out, np.where(valid, dot, 1.0))
    return out


def derive_edge(z, n_cam, mask, depth_rel_threshold, normal_angle_deg):
    """Geometric edge pass: relative depth break OR normal break OR silhouette.

    Returns (uint8 image, diagnostics). The image is near-binary by construction
    (F22): every pixel is 0 or 255.
    """
    m = np.asarray(mask) > 0
    z = np.asarray(z, dtype=np.float64)
    z_safe = np.where(m, z, np.nan)

    grad = _neighbour_max(np.nan_to_num(z_safe, nan=0.0), m)
    local = np.maximum(np.where(m, z, 1.0), 1e-6)
    rel = np.where(m, grad / local, 0.0)
    depth_break = rel > float(depth_rel_threshold)

    min_dot = _neighbour_min_dot(n_cam, m)
    cos_thresh = float(np.cos(np.radians(float(normal_angle_deg))))
    normal_break = np.logical_and(m, min_dot < cos_thresh)

    sil = silhouette(m)
    edge = np.logical_or(np.logical_or(depth_break, normal_break), sil)

    diag = {
        "depth_break_px": int(depth_break.sum()),
        "normal_break_px": int(normal_break.sum()),
        "silhouette_px": int(sil.sum()),
        "edge_px": int(edge.sum()),
        "depth_rel_threshold": float(depth_rel_threshold),
        "normal_angle_deg": float(normal_angle_deg),
    }
    return (edge.astype(np.uint8) * 255), diag


def bbox_of(binary):
    """(x0, y0, x1, y1) inclusive pixel bounds of the True region, or None."""
    m = np.asarray(binary) > 0
    if not m.any():
        return None
    rows = np.flatnonzero(m.any(axis=1))
    cols = np.flatnonzero(m.any(axis=0))
    return (int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1]))


def normalization_difference(d_per_frame, d_per_shot, mask):
    """P3's measurement: |per-frame - per-shot| over geometry pixels only.

    Returns (abs-difference image as float, stats dict). Pixels outside the mask are
    zero in both inputs by construction and are excluded from the statistics rather
    than diluting them toward zero — a mean over the whole frame would mostly be
    measuring how much background there is.
    """
    m = np.asarray(mask) > 0
    diff = np.abs(np.asarray(d_per_frame, dtype=np.float64) - np.asarray(d_per_shot, dtype=np.float64))
    diff = np.where(m, diff, 0.0)
    if not m.any():
        return diff, {"n_px": 0, "mean_abs": None, "max_abs": None,
                      "signed_mean": None, "n_darker": 0, "n_lighter": 0}
    vals = diff[m]
    signed = (np.asarray(d_per_shot, dtype=np.float64) - np.asarray(d_per_frame, dtype=np.float64))[m]
    return diff, {
        "n_px": int(m.sum()),
        "mean_abs": float(vals.mean()),
        "max_abs": float(vals.max()),
        "signed_mean": float(signed.mean()),
        "n_darker": int((signed < -1e-9).sum()),   # per-shot darker than per-frame
        "n_lighter": int((signed > 1e-9).sum()),
    }
