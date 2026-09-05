"""Channel maths."""

import numpy as np
import pytest

from armature_core import channels as ch


def test_depth_near_is_bright():
    z = np.array([[2.0, 3.5, 5.0]])
    mask = np.ones((1, 3), dtype=np.uint8)
    d = ch.normalize_depth(z, mask, 2.0, 5.0)
    f = ch.GEOMETRY_DEPTH_FLOOR
    assert d[0, 0] == pytest.approx(1.0)
    # These two moved with F-aa0ca08b, deliberately. The far end of the GEOMETRY range was
    # pinned here at 0.0 - the same value `normalize_depth` writes for "no geometry" and the
    # same byte `encode_u8` produces for it. Geometry now starts one byte above background.
    assert d[0, 2] == pytest.approx(f)
    assert d[0, 1] == pytest.approx(f + 0.5 * (1.0 - f))


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


def test_the_farthest_geometry_pixel_does_not_encode_to_the_background_byte():
    """The geometry pixel at `z == z_far` mapped to `(z_far - z_far)/span = 0.0`, which is
    BACKGROUND_DEPTH, and `encode_u8` took both to byte 0: the rearmost band of the
    silhouette dissolved into the void it is supposed to stand against, on every frame
    where the subject sits furthest under per-shot normalisation."""
    z = np.array([[1.0, 2.0], [3.0, 1e10]])
    mask = np.array([[1, 1], [1, 0]], dtype=np.uint8)
    b = ch.encode_u8(ch.normalize_depth(z, mask, 1.0, 3.0))
    assert b[1, 1] == 0, "background must keep byte 0"
    assert b[1, 0] != b[1, 1], (
        "the farthest geometry pixel and the void encode to the same byte")
    assert b[1, 0] == 1 and b[0, 0] == 255


def test_the_geometry_floor_costs_one_byte_and_no_more():
    z = np.linspace(2.0, 5.0, 256).reshape(1, 256)
    mask = np.ones((1, 256), dtype=np.uint8)
    b = ch.encode_u8(ch.normalize_depth(z, mask, 2.0, 5.0))
    assert int(b.min()) == 1 and int(b.max()) == 255


# ------------------------------------- wave 10: the three edge terms and the frame border


def test_the_frame_border_is_not_drawn_as_a_silhouette_on_any_side():
    """F-3d03d8bf. `silhouette` was `m & ~_erode3(m)` and `_erode3` padded with False, so
    every mask pixel on the outermost row or column was marked as a geometric edge — while
    the two sibling terms `derive_edge` ORs it with each build an `edge` mask and exclude
    it, with the comment "do not compare across the frame border".

    Measured on the wave-10 base, on the fixture below: `silhouette(m)[-1].sum()` was 6, a
    full row of invented edge along the crop. The edge channel is a control input, so that
    line is drawn into the picture a generation is conditioned on.

    One side per case, so a fix that only handled rows would fail on columns.
    """
    for side in ("bottom", "top", "left", "right"):
        m = np.zeros((6, 6), dtype=np.uint8)
        if side == "bottom":
            m[3:, :] = 1
            border = ch.silhouette(m)[-1, :]
        elif side == "top":
            m[:3, :] = 1
            border = ch.silhouette(m)[0, :]
        elif side == "left":
            m[:, :3] = 1
            border = ch.silhouette(m)[:, 0]
        else:
            m[:, 3:] = 1
            border = ch.silhouette(m)[:, -1]
        assert border.sum() == 0, (side, border)


def test_a_subject_that_ENDS_inside_the_frame_still_has_its_whole_boundary():
    """The direction the policy must not break, and the half that makes the fixture above
    mean something: the same 6x6 frame with the subject pulled one pixel off every edge
    keeps every boundary pixel, because there the mask boundary IS a discontinuity."""
    m = np.zeros((6, 6), dtype=np.uint8)
    m[1:5, 1:5] = 1
    s = ch.silhouette(m)
    assert s.sum() == 12                       # a 4x4 block: 16 minus its 2x2 interior
    assert not s[2, 2] and not s[3, 3]
    assert s[1, 1] and s[4, 4]


def test_the_interior_boundary_of_a_subject_that_runs_off_frame_is_still_marked():
    """A subject flush against the bottom is not edgeless — only the crop line is gone."""
    m = np.zeros((6, 6), dtype=np.uint8)
    m[3:, :] = 1
    s = ch.silhouette(m)
    assert s[3, :].all()                       # the real boundary, three rows up
    assert s[-1, :].sum() == 0


def test_the_edge_channel_of_a_full_frame_subject_carries_no_border_line():
    """End to end through `derive_edge`, because that is where the difference reaches a
    control image — and `silhouette_px` is a reported diagnostic, so it counted the crop."""
    z = np.full((8, 8), 3.0)
    n = np.zeros((8, 8, 3))
    n[..., 2] = 1.0
    mask = np.ones((8, 8), dtype=np.uint8)
    edge, diag = ch.derive_edge(z, n, mask, 0.02, 30.0)
    assert diag["silhouette_px"] == 0
    assert int(edge.sum()) == 0


def test_the_erosion_border_argument_is_the_whole_policy_and_can_be_read_both_ways():
    """The knob itself, both settings, so the policy is a decision in one place rather
    than a property of a call site nobody can see."""
    m = np.zeros((4, 4), dtype=np.uint8)
    m[2:, :] = 1
    assert ch._erode3(m, border=False)[-1, :].sum() == 0
    assert ch._erode3(m, border=True)[-1, 1:-1].all()


# ------------------- wave 22, F-4efe0fad: the normal half of the non-finite census
#
# Wave 18 gave this module a non-finite clause (`DepthError` + `_non_finite_census`) and it
# landed on the DEPTH half only. `encode_normal` read `n_cam` with no census at all, and its
# normalisation is `np.divide(n, norm, out=np.zeros_like(n), where=norm > 1e-8)` — `nan >
# 1e-8` is False, so an unreadable normal silently took the ZERO fallback and encoded as if
# it were the zero vector. MEASURED on `e8263a3` on a 4x4 field of camera-facing normals
# (baseline (128, 128, 255) everywhere): one NaN component -> (128, 128, 128); one +inf ->
# (0, 128, 128); one -inf -> (0, 128, 128), the SAME byte, so the sign was lost too; a
# legitimately zero-length normal -> (128, 128, 128), indistinguishable from the unreadable
# one; an all-NaN field -> a UNIFORM (128, 128, 128) plate, returned with no refusal and no
# key naming the population that took the fallback. The depth sibling, in the same run and
# the same module, raises `DepthError` with a seven-key census.
#
# These fixtures mirror the depth ones one for one — the depth ones are the template, and
# their absence on the normal side was the gap.


def _facing_field(h=4, w=4):
    n = np.zeros((h, w, 3))
    n[..., 2] = 1.0
    return n, np.ones((h, w), dtype=np.uint8)


def test_the_normal_baseline_is_camera_facing_everywhere():
    """What the arm looks like when it does nothing — the control the four rows below are
    read against."""
    n, mask = _facing_field()
    rgb = ch.encode_normal(n, mask)
    assert set(map(tuple, rgb.reshape(-1, 3).tolist())) == {(128, 128, 255)}


@pytest.mark.parametrize("bad,key", [
    (float("nan"), "n_nan"),
    (float("inf"), "n_pos_inf"),
    (float("-inf"), "n_neg_inf"),
])
def test_encode_normal_refuses_one_non_finite_component_by_name(bad, key):
    n, mask = _facing_field()
    n[1, 2, 0] = bad
    with pytest.raises(ch.NormalError, match=r"non-finite camera-space normal") as exc:
        ch.encode_normal(n, mask)
    ev = exc.value.evidence
    assert ev["clause"] == "non_finite_geometry_normal"
    assert ev[key] == 1 and ev["n_non_finite"] == 1
    assert ev["n"] == 48 and ev["n_finite"] == 47 and ev["n_geometry_px"] == 16


def test_encode_normal_refuses_an_all_nan_field_rather_than_returning_a_grey_plate():
    """The worst realistic consequence, on the path `stage_render.py` actually runs: the
    encoder writes straight to `out_dir/normal/` with no gate between them, so a flat grey
    plate is hashed into the manifest and steers a paid generation."""
    n, mask = _facing_field()
    n[:] = float("nan")
    with pytest.raises(ch.NormalError) as exc:
        ch.encode_normal(n, mask)
    assert exc.value.evidence["n_non_finite"] == 48


def test_encode_normal_refuses_a_zero_length_normal_inside_the_mask_by_its_own_clause():
    """It encodes to the SAME byte as the unreadable one, so the two are named apart."""
    n, mask = _facing_field()
    n[0, 0, :] = 0.0
    with pytest.raises(ch.NormalError) as exc:
        ch.encode_normal(n, mask)
    ev = exc.value.evidence
    assert ev["clause"] == "zero_length_geometry_normal"
    assert ev["n_zero_length_px"] == 1 and ev["n_geometry_px"] == 16


def test_a_non_finite_normal_OUTSIDE_the_mask_is_background_and_not_this_gate_s_business():
    """The population is the SELECTED one — the same rule `depth_extent` states. A value
    outside the mask is not a normal this module authored."""
    n, mask = _facing_field()
    mask[0, 0] = 0
    n[0, 0, 1] = float("nan")
    rgb = ch.encode_normal(n, mask)
    assert tuple(int(v) for v in rgb[0, 0]) == (0, 0, 0)
    assert tuple(int(v) for v in rgb[1, 1]) == (128, 128, 255)


def test_derive_edge_refuses_the_same_field_rather_than_dropping_the_normal_break():
    """The second consumer of the same unbounded array. `normal_break = m & (min_dot <
    cos_thresh)` is False for a NaN, so the break was silently NOT drawn and
    `diag['normal_break_px']` counted fewer, with no clause."""
    z = np.full((4, 4), 3.0)
    n, mask = _facing_field()
    n[2, 2, 1] = float("nan")
    with pytest.raises(ch.NormalError) as exc:
        ch.derive_edge(z, n, mask, 0.02, 30.0)
    assert exc.value.evidence["clause"] == "non_finite_geometry_normal"
    assert exc.value.evidence["where"] == "derive_edge"


def test_the_normal_refusal_is_in_the_family_and_carries_the_depth_sibling_s_key_set():
    """The seven keys `DepthError`'s census carries, so a reader that can reconcile one
    receipt can reconcile the other."""
    from armature_core.errors import ArmatureError

    assert issubclass(ch.NormalError, ArmatureError)
    n, mask = _facing_field()
    n[0, 1, 2] = float("nan")
    with pytest.raises(ch.NormalError) as exc:
        ch.encode_normal(n, mask)
    assert set(exc.value.evidence) >= {
        "gate", "andon", "clause", "where", "n", "n_finite", "n_non_finite", "n_nan",
        "n_pos_inf", "n_neg_inf", "n_geometry_px"}
    assert exc.value.evidence["gate"] is None
    assert exc.value.evidence["andon"] == "NormalError"
