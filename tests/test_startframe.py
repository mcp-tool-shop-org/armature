"""Tests for the start frame's geometry and its andon.

Every fixture here builds the WRONG implementation's answer and shows it failing, because
the failures this module exists to catch are all silent: a cropped conditioning image
renders, saves, uploads and generates without a single error anywhere.
"""

import math

import pytest

from armature_core import framing, startframe as SF


LENS, SENSOR, W, H = 50.0, 36.0, 832, 480
AZ, EL = 225.0, 6.0


# --------------------------------------------------------------- framing_cloud


def test_the_reduction_keeps_every_axis_extreme_a_stride_would_drop():
    """The dangerous reduction is the obvious one.

    The cloud below puts its topmost vertex at index 1, which every stride > 1 skips. A
    reduction that merely strided would hand `solve_camera` a figure shorter than the real
    one; the solve would then fit that shorter figure to the requested height fraction and
    the real one would come out too large — with nothing erroring, because a slightly
    oversized figure is a perfectly well-formed render.
    """
    pts = [(0.0, 0.0, 0.0)] * 40
    pts[1] = (0.0, 0.0, 9.0)          # the top of the head, at an index a stride skips
    pts[7] = (-5.0, 0.0, 0.0)         # the far hand
    pts[38] = (5.0, 0.0, 0.0)
    out = SF.framing_cloud(pts, cap=8)

    assert len(out) <= 8
    for axis in (0, 1, 2):
        assert max(p[axis] for p in out) == max(p[axis] for p in pts)
        assert min(p[axis] for p in out) == min(p[axis] for p in pts)

    strided = pts[::len(pts) // 8]
    assert max(p[2] for p in strided) != max(p[2] for p in pts), (
        "the fixture no longer demonstrates the failure it was built to demonstrate")


def test_the_reduction_is_deterministic():
    """A composition that changes between two runs of the same tool is not a recipe."""
    pts = [(math.sin(i), math.cos(i), i * 0.01) for i in range(5000)]
    assert SF.framing_cloud(pts, cap=200) == SF.framing_cloud(pts, cap=200)


def test_a_cloud_under_the_cap_is_returned_whole():
    pts = [(float(i), 0.0, 0.0) for i in range(11)]
    assert SF.framing_cloud(pts, cap=1500) == pts


def test_an_empty_cloud_raises_rather_than_framing_the_origin():
    with pytest.raises(SF.StartFrameGate):
        SF.framing_cloud([])


# ---------------------------------------------------------- silhouette_extent


def _extent_of(points, target=(0.0, 0.0, 0.0), radius=4.0):
    return SF.silhouette_extent(points, target, radius, AZ, EL, LENS, SENSOR, W, H)


def test_the_extent_is_unclipped_and_that_is_the_whole_point():
    """A vertex outside the frame must come back OUTSIDE it.

    `blender_scene.projected_bbox_px` clips to the frame before taking bounds, which is
    correct for comparing against a rendered mask and catastrophic here: an arm 200 px off
    the left edge returns `x0 = 0`, and a gate reading that number sees a figure sitting
    neatly against the border. This test fails the moment somebody clamps.
    """
    target = (0.0, 0.0, 0.0)
    inside = _extent_of([target], target)
    assert inside["x0"] == pytest.approx(W * 0.5, abs=1e-6)

    # A point pushed hard along screen-right of the same camera.
    pos = framing.camera_position(target, 4.0, EL, AZ)
    right, up, _ = framing.camera_basis(target, pos)
    far = tuple(target[i] - right[i] * 6.0 for i in range(3))
    out = _extent_of([target, far], target)
    assert out["x0"] < 0.0, "an off-frame point was clamped into the frame"


def test_a_point_behind_the_camera_is_counted_not_projected():
    """The perspective divide mirrors a point behind the lens into frame. Including it
    would move the bounds to somewhere the figure never was, and the bounds would look
    entirely reasonable."""
    target = (0.0, 0.0, 0.0)
    behind = framing.camera_position(target, 8.0, EL, AZ)
    ext = _extent_of([target, behind], target)
    assert ext["n_behind"] == 1
    assert ext["n_points"] == 2


def test_all_points_behind_the_camera_raises():
    target = (0.0, 0.0, 0.0)
    behind = framing.camera_position(target, 8.0, EL, AZ)
    with pytest.raises(SF.StartFrameGate):
        _extent_of([behind], target)


# ------------------------------------------------------------------ gate_whole


def test_the_gate_passes_a_figure_with_margin_and_reports_the_smallest_one():
    ext = {"x0": 300.0, "x1": 520.0, "y0": 24.0, "y1": 456.0, "n_behind": 0,
           "n_points": 100}
    ev = SF.gate_whole(ext, W, H, margin_px=8)
    assert ev["margins_px"]["top"] == pytest.approx(24.0)
    assert ev["margins_px"]["bottom"] == pytest.approx(23.0)
    assert ev["height_frac"] == pytest.approx(0.9, abs=1e-9)


@pytest.mark.parametrize("side,ext", [
    ("top", {"x0": 300.0, "x1": 520.0, "y0": -14.0, "y1": 450.0}),
    ("bottom", {"x0": 300.0, "x1": 520.0, "y0": 20.0, "y1": 479.0}),
    ("left", {"x0": -2.0, "x1": 520.0, "y0": 20.0, "y1": 450.0}),
    ("right", {"x0": 300.0, "x1": 831.0, "y0": 20.0, "y1": 450.0}),
])
def test_the_gate_fires_on_a_body_cut_by_any_border(side, ext):
    """Four separate fixtures rather than one, because "the figure is in frame" is a
    conjunction of four clauses and a gate that only ever saw one of them fail would be
    a gate nobody had checked the other three of."""
    ext = dict(ext, n_behind=0, n_points=100)
    with pytest.raises(SF.StartFrameGate) as exc:
        SF.gate_whole(ext, W, H, margin_px=8)
    assert side in str(exc.value)


def test_the_gate_fires_when_anything_is_behind_the_camera():
    ext = {"x0": 300.0, "x1": 520.0, "y0": 24.0, "y1": 456.0, "n_behind": 3,
           "n_points": 100}
    with pytest.raises(SF.StartFrameGate):
        SF.gate_whole(ext, W, H, margin_px=8)


def test_the_landmark_cloud_can_pass_while_the_silhouette_does_not():
    """The measurement this module exists for, made executable.

    A landmark cloud is a handful of joint centres; the silhouette is the body around them.
    Here `solve_camera` composes on the landmarks, reports `in_frame`, and the real
    silhouette is over the top of the frame — which is the E11 failure mode exactly: the
    composition looks solved and the conditioning image is of a decapitated character.
    """
    landmarks = [(0.0, 0.0, z) for z in (0.0, 0.4, 0.8, 1.2, 1.5)]
    sol = framing.solve_camera(landmarks, landmarks, AZ, EL, LENS, SENSOR, W, H,
                               height_frac=0.98, end_x_frac=0.5, target_y_frac=0.5)
    assert sol["in_frame"], "the fixture must start from a framing that reports itself fine"

    silhouette = landmarks + [(0.0, 0.0, 1.75), (0.0, 0.0, -0.2)]   # skull cap, heels
    ext = SF.silhouette_extent(silhouette, sol["target"], sol["radius"], AZ, EL,
                               LENS, SENSOR, W, H)
    with pytest.raises(SF.StartFrameGate):
        SF.gate_whole(ext, W, H, margin_px=8)


# -------------------------------------------------------------------- mask_bbox


def test_an_empty_mask_is_none_rather_than_a_zero_bbox():
    """A render nobody is in must not report a bbox at the origin: `(0,0,0,0)` is a
    1-pixel figure in the top-left corner as far as any consumer can tell."""
    assert SF.mask_bbox([[False] * 4 for _ in range(3)]) is None


def test_the_mask_bbox_is_inclusive_and_row_major():
    rows = [
        [False, False, False, False],
        [False, True, True, False],
        [False, False, True, False],
    ]
    assert SF.mask_bbox(rows) == (1, 1, 2, 2)
