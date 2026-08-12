"""`fit_reference` — the contain-fit that keeps a portrait figure inside a landscape frame.

The failure being avoided is not an error, it is a silent amputation: `WanAnimateToVideo`
cover-crops its reference, and on E08's 352x1024 twin against an 832x480 frame that keeps
19.9% of the height — the hips and thighs. Everything downstream then runs perfectly on an
identity reference with no face in it.

`node_crop_that_this_avoids` reproduces the node's arithmetic so the report can state the
alternative in numbers; it is checked here against the numbers read off the source.
"""

import numpy as np
import pytest

from armature_core.errors import ArmatureError

import fit_reference as FR


def test_contain_fit_keeps_every_source_pixel_where_cover_crop_would_not():
    img = np.zeros((1024, 352, 3), np.uint8)
    img[:] = (10, 20, 30)
    out, pl = FR.letterbox(img, 832, 480, (128, 128, 128))
    assert out.shape == (480, 832, 3)
    # 352 * (480/1024) = 165
    assert pl["fitted_size"] == [165, 480]
    assert pl["scale"] == pytest.approx(480 / 1024)
    # the figure occupies its own area and the rest is margin
    assert pl["figure_fraction_of_frame"] == pytest.approx((165 * 480) / (832 * 480))
    assert pl["margin_fraction_of_frame"] == pytest.approx(1 - pl["figure_fraction_of_frame"])


def test_the_pad_reaches_the_margins_and_the_image_reaches_the_middle():
    img = np.zeros((1024, 352, 3), np.uint8)
    img[:] = (10, 20, 30)
    out, pl = FR.letterbox(img, 832, 480, (200, 100, 50))
    assert out[0, 0].tolist() == [200, 100, 50]
    assert out[-1, -1].tolist() == [200, 100, 50]
    ox = pl["offset"][0]
    assert out[240, ox + 80].tolist() == [10, 20, 30]


def test_a_landscape_source_letterboxes_top_and_bottom():
    """The other direction, so the fit is not accidentally portrait-only."""
    img = np.zeros((100, 1000, 3), np.uint8)
    out, pl = FR.letterbox(img, 832, 480, (7, 7, 7))
    assert pl["fitted_size"][0] == 832
    assert pl["offset"][0] == 0
    assert pl["offset"][1] > 0
    assert out[0, 416].tolist() == [7, 7, 7]


def test_a_source_already_at_the_frames_aspect_gets_no_margin():
    """A check that cannot fail is not a check — so the no-op case is pinned too."""
    img = np.zeros((240, 416, 3), np.uint8)
    out, pl = FR.letterbox(img, 832, 480, (7, 7, 7))
    assert pl["fitted_size"] == [832, 480]
    assert pl["margin_fraction_of_frame"] == pytest.approx(0.0)


def test_node_crop_reproduces_the_measured_twin_numbers():
    """Pinned against the arithmetic read off comfy/utils.py and computed on the real twin:
    y = round((1024 - 1024 * (0.34375 / 1.73333)) / 2) = 410, keeping 204 of 1024 rows."""
    rec = FR.node_crop_that_this_avoids(352, 1024, 832, 480)
    assert rec["crop_y"] == 410
    assert rec["crop_x"] == 0
    assert rec["kept_size"] == [352, 204]
    assert rec["kept_fraction_of_source_height"] == pytest.approx(204 / 1024, abs=1e-9)


def test_node_crop_trims_width_when_the_source_is_the_wider_one():
    rec = FR.node_crop_that_this_avoids(1000, 100, 832, 480)
    assert rec["crop_y"] == 0
    assert rec["crop_x"] > 0
    assert rec["kept_size"][1] == 100


def test_border_colour_is_the_plate_not_the_figure():
    """Median, not mean: a figure touching an edge must not drag the pad toward its colour."""
    img = np.zeros((400, 400, 3), np.uint8)
    img[:] = (200, 200, 200)                 # the plate
    img[150:250, 150:250] = (10, 10, 10)     # the figure, well inside
    img[0:40, 0:40] = (10, 10, 10)           # …and a corner of it touching the border
    assert FR.border_colour(img) == (200, 200, 200)


def test_border_colour_scales_with_the_image_rather_than_a_pixel_count():
    small = np.full((100, 100, 3), 50, np.uint8)
    big = np.full((1000, 1000, 3), 50, np.uint8)
    assert FR.border_colour(small) == FR.border_colour(big) == (50, 50, 50)


def test_a_degenerate_source_raises():
    with pytest.raises(ArmatureError):
        FR.letterbox(np.zeros((0, 10, 3), np.uint8), 832, 480, (0, 0, 0))
