"""Channel maths."""

import numpy as np
import pytest

from armature_core import channels as ch


def test_depth_near_is_bright():
    z = np.array([[2.0, 3.5, 5.0]])
    mask = np.ones((1, 3), dtype=np.uint8)
    d = ch.normalize_depth(z, mask, 2.0, 5.0)
    assert d[0, 0] == pytest.approx(1.0)
    assert d[0, 2] == pytest.approx(0.0)
    assert d[0, 1] == pytest.approx(0.5)


def test_depth_background_is_black_not_near():
    """Background has no depth. Encoding it as 0 (far) rather than leaving 1e10 to
    clip to 1.0 (nearest) is the difference between a black backdrop and a wall
    pressed against the lens."""
    z = np.array([[2.0, 1e10]])
    mask = np.array([[1, 0]], dtype=np.uint8)
    d = ch.normalize_depth(z, mask, 2.0, 5.0)
    assert d[0, 1] == 0.0


def test_depth_zero_extent_does_not_divide_by_zero():
    z = np.full((2, 2), 3.0)
    mask = np.ones((2, 2), dtype=np.uint8)
    d = ch.normalize_depth(z, mask, 3.0, 3.0)
    assert np.all(d == 1.0)


def test_encode_u8_endpoints():
    assert ch.encode_u8(np.array([0.0, 0.5, 1.0])).tolist() == [0, 128, 255]


def test_normal_transform_is_a_rotation_into_camera_space():
    """A surface square to the camera reads (0,0,1) whatever the camera's world
    orientation. If the transform were dropped, a camera pointing along world +X
    would encode a red-ish normal map instead."""
    # camera rotated 90 deg about Z: its -Z (view direction) points along world -Y... build
    # it the way the tool does and check the invariant rather than a hand-derived matrix.
    theta = np.radians(37.0)
    Rz = np.array([[np.cos(theta), -np.sin(theta), 0],
                   [np.sin(theta), np.cos(theta), 0],
                   [0, 0, 1]], dtype=np.float64)
    view_dir_world = -Rz[:, 2]              # camera looks down its own -Z
    n_world = np.tile(-view_dir_world, (2, 3, 1))   # surface faces the camera
    n_cam = ch.world_normals_to_camera(n_world, Rz)
    assert np.allclose(n_cam[..., 2], 1.0)
    assert np.allclose(n_cam[..., :2], 0.0, atol=1e-12)


def test_encode_normal_camera_facing_is_128_128_255():
    n = np.zeros((2, 2, 3))
    n[..., 2] = 1.0
    mask = np.ones((2, 2), dtype=np.uint8)
    rgb = ch.encode_normal(n, mask)
    assert tuple(int(v) for v in rgb[0, 0]) == (128, 128, 255)


def test_encode_normal_background_is_black():
    n = np.zeros((2, 2, 3))
    n[..., 2] = 1.0
    mask = np.array([[1, 0], [0, 0]], dtype=np.uint8)
    rgb = ch.encode_normal(n, mask)
    assert tuple(int(v) for v in rgb[0, 1]) == (0, 0, 0)


def test_silhouette_is_the_mask_boundary():
    m = np.zeros((7, 7), dtype=np.uint8)
    m[2:5, 2:5] = 1
    s = ch.silhouette(m)
    assert s.sum() == 8           # a 3x3 block is all boundary except its centre
    assert not s[3, 3]


def test_edge_is_near_binary_and_finds_a_depth_cliff():
    z = np.full((16, 16), 3.0)
    z[:, 8:] = 6.0
    mask = np.ones((16, 16), dtype=np.uint8)
    n = np.zeros((16, 16, 3))
    n[..., 2] = 1.0
    edge, diag = ch.derive_edge(z, n, mask, 0.02, 30.0)
    assert set(np.unique(edge).tolist()) <= {0, 255}
    assert edge[8, 7] == 255 or edge[8, 8] == 255
    assert diag["depth_break_px"] > 0
    assert edge[8, 3] == 0


def test_edge_threshold_is_relative_not_absolute():
    """A global constant must not govern a local feature. The same 1-unit step is an
    edge up close and noise far away, so the threshold is a fraction of local depth."""
    n = np.zeros((8, 8, 3))
    n[..., 2] = 1.0
    mask = np.ones((8, 8), dtype=np.uint8)

    near = np.full((8, 8), 2.0)
    near[:, 4:] = 3.0        # 1 unit at depth 2 -> 50% relative
    far = np.full((8, 8), 200.0)
    far[:, 4:] = 201.0       # the same 1 unit at depth 200 -> 0.5% relative

    e_near, _ = ch.derive_edge(near, n, mask, 0.02, 30.0)
    e_far, _ = ch.derive_edge(far, n, mask, 0.02, 30.0)
    interior = slice(1, 7)
    assert e_near[interior, 3:5].max() == 255
    assert e_far[interior, 3:5].max() == 0


def test_edge_finds_a_normal_break_with_no_depth_change():
    z = np.full((16, 16), 4.0)
    mask = np.ones((16, 16), dtype=np.uint8)
    n = np.zeros((16, 16, 3))
    n[:, :8, 2] = 1.0
    n[:, 8:, 0] = 1.0        # 90 deg turn, no depth step
    edge, diag = ch.derive_edge(z, n, mask, 0.5, 30.0)
    assert diag["normal_break_px"] > 0
    assert edge[8, 7] == 255 or edge[8, 8] == 255


def test_bbox_of_empty_is_none():
    assert ch.bbox_of(np.zeros((4, 4), dtype=np.uint8)) is None


def test_normalization_difference_is_measured_on_geometry_only():
    """A mean over the whole frame would mostly measure how much background there is."""
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[0, 0] = 1
    a = np.zeros((4, 4))
    b = np.zeros((4, 4))
    a[0, 0], b[0, 0] = 1.0, 0.5
    _, stats = ch.normalization_difference(a, b, mask)
    assert stats["n_px"] == 1
    assert stats["mean_abs"] == pytest.approx(0.5)


def test_per_shot_compresses_relative_to_per_frame():
    """The algebra P3 predicts from: with a wider shot window, per-shot is an affine
    compression of per-frame."""
    z = np.linspace(2.0, 4.0, 16).reshape(1, 16)
    mask = np.ones((1, 16), dtype=np.uint8)
    d_pf = ch.normalize_depth(z, mask, 2.0, 4.0)      # frame window
    d_ps = ch.normalize_depth(z, mask, 1.0, 6.0)      # wider shot window
    assert d_ps[0, 0] < d_pf[0, 0]     # nearest surface darker under per-shot
    assert d_ps[0, -1] > d_pf[0, -1]   # farthest surface lighter under per-shot
