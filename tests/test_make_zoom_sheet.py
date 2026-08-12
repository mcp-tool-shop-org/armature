"""The zoom crop's box arithmetic. A still whose provenance is unrecorded is a picture."""

from conftest import TOOLS  # noqa: F401
import make_zoom_sheet as MZS


def test_a_crop_well_inside_the_frame_is_centred_and_not_clamped():
    box, moved = MZS.crop_box(400, 240, 140, 832, 480)
    assert box == (330, 170, 470, 310)
    assert moved is False
    assert box[2] - box[0] == box[3] - box[1] == 140


def test_a_crop_at_the_edge_slides_inside_and_says_so():
    """Clamped rather than padded — a padded crop invents pixels exactly where the
    interesting failures live — and the caption has to admit the centre moved."""
    box, moved = MZS.crop_box(10, 10, 140, 832, 480)
    assert box == (0, 0, 140, 140)
    assert moved is True


def test_a_crop_past_the_far_edge_slides_back_inside():
    box, moved = MZS.crop_box(830, 478, 140, 832, 480)
    assert box == (692, 340, 832, 480)
    assert moved is True


def test_the_box_is_always_the_requested_size_even_when_clamped():
    for cx, cy in ((0, 0), (832, 480), (416, 0), (0, 240)):
        box, _m = MZS.crop_box(cx, cy, 140, 832, 480)
        assert box[2] - box[0] == 140 and box[3] - box[1] == 140
        assert 0 <= box[0] and 0 <= box[1] and box[2] <= 832 and box[3] <= 480


def test_a_fractional_keypoint_rounds_rather_than_truncating():
    box, _m = MZS.crop_box(399.6, 239.5, 140, 832, 480)
    assert box[0] == 330 and box[1] == 170
