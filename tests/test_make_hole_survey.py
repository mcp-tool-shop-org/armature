"""The hole survey's arithmetic — S03 Task B.

The survey judges nothing, so it has no gates. What it has is arithmetic that can be
quietly wrong in ways the resulting sheet still looks fine under, and those are what these
tests pin:

* a **premultiplied** composite instead of a straight one darkens every antialiased edge
  against the background. The figure still appears, the sheet still saves, and the new
  panel acquires a dark rim the old panel does not have — which a reader would attribute
  to the render rather than to this file.
* an **un-eroded** interior counts the antialiased rim, and the old set's rim is grey by
  construction because it blends into a baked grey void. That reports the *masking method*
  as if it were a texture defect, in exactly the direction that would make the old set look
  worse than it is.
"""

import numpy as np
import pytest

import make_hole_survey as HS


# ------------------------------------------------------------------ the composite


def test_transparent_pixels_become_exactly_the_background():
    rgba = np.zeros((2, 2, 4), dtype=np.uint8)
    rgba[..., :3] = 200                       # whatever RGB sits under alpha 0
    out = HS.composite_over(rgba, (154, 154, 157))
    assert (out == np.array([154, 154, 157], np.uint8)).all()


def test_opaque_pixels_are_left_exactly_alone():
    rgba = np.zeros((2, 2, 4), dtype=np.uint8)
    rgba[..., :3] = (136, 98, 79)
    rgba[..., 3] = 255
    out = HS.composite_over(rgba, (154, 154, 157))
    assert (out == np.array([136, 98, 79], np.uint8)).all()


def test_a_half_alpha_edge_lands_halfway_not_at_a_premultiplied_value():
    """The measured discriminator. Blender wrote STRAIGHT alpha here: edge pixels at
    alpha < 60 carry mean RGB (110, 86, 76) against a full-alpha mean of (136, 98, 79),
    where premultiplied edges would read near (16, 12, 9). Composite those straight
    values with a premultiplying formula and the rim goes dark."""
    rgba = np.zeros((1, 1, 4), dtype=np.uint8)
    rgba[..., :3] = (100, 100, 100)
    rgba[..., 3] = 128
    out = HS.composite_over(rgba, (200, 200, 200))
    assert out[0, 0].tolist() == [150, 150, 150]
    premultiplied_would_be = 100 + 200 * (1 - 128 / 255)
    assert abs(premultiplied_would_be - 150) > 40


# ------------------------------------------------------------------ the locator


def test_saturation_is_zero_on_grey_and_high_on_the_skin_tone():
    grey = np.full((1, 1, 3), 154, np.uint8)
    skin = np.array([[[136, 98, 79]]], np.uint8)
    assert HS.saturation(grey)[0, 0] == pytest.approx(0.0)
    assert HS.saturation(skin)[0, 0] == pytest.approx((136 - 79) / 136, rel=1e-6)


def test_erosion_removes_the_rim_and_keeps_the_core():
    mask = np.zeros((21, 21), bool)
    mask[5:16, 5:16] = True                   # an 11x11 square
    out = HS.erode(mask, 3)
    assert out.sum() == 25                    # 5x5 survives a 3 px erosion
    assert out[10, 10] and not out[5, 5]


def test_erosion_does_not_shrink_a_mask_that_runs_off_the_image_edge():
    """Recorded because it surprised this session's first expectation.

    PIL's min filter extends the border rather than treating outside-the-image as empty,
    so a mask touching the frame edge is not eroded there. It does not affect the real
    measurement — Gate WHOLE guarantees the figure clears every border by at least 2 px,
    so no view's silhouette ever touches the edge — but a reader deriving interior counts
    by hand would get a different number, so the behaviour is pinned rather than left to
    be rediscovered.
    """
    assert HS.erode(np.ones((30, 30), bool), 3).sum() == 900


def test_a_structure_thinner_than_the_erosion_disappears_entirely():
    """Stated so the limitation is on the record rather than discovered later: a finger
    narrower than 2*ERODE_PX+1 contributes no interior texels to the count at all. The
    patches on these views cluster at the hands, so this is the instrument's real blind
    spot and the reason the sheets — not the number — are the survey."""
    mask = np.zeros((21, 21), bool)
    mask[5:16, 10:13] = True                  # a 3 px wide bar
    assert HS.erode(mask, 3).sum() == 0


def test_the_rim_is_what_makes_the_two_masks_disagree():
    """The whole reason erosion is in this tool.

    One figure, rendered both ways: the new panel carries real alpha, the old panel is the
    same figure composited onto grey with an antialiased rim and no alpha. Counted
    un-eroded, the old view reports far more low-saturation interior than the new one —
    entirely from the rim, with the texture identical in both.
    """
    h = w = 41
    rgba = np.zeros((h, w, 4), np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - 20) ** 2 + (xx - 20) ** 2)
    rgba[..., :3] = (136, 98, 79)
    rgba[..., 3] = np.clip((14.0 - r) * 255.0, 0, 255).astype(np.uint8)   # soft rim
    old_rgb = HS.composite_over(rgba, HS.OLD_VOID_RGB)

    new_mask = HS.figure_mask_new(rgba)
    old_mask = HS.figure_mask_old(old_rgb)

    def low(rgb, mask, px):
        s = HS.saturation(rgb)[HS.erode(mask, px)]
        return float((s < 0.20).mean())

    # Un-eroded, the colour-difference mask reports low-saturation interior that the
    # alpha mask does not — every one of those pixels is rim, and the texture behind
    # them is identical in the two images.
    assert low(rgba[..., :3], new_mask, 0) == 0.0
    assert low(old_rgb, old_mask, 0) > 0.0

    # Eroded by the same amount, the disagreement is gone. This is the assertion the
    # erosion exists to make true.
    assert low(old_rgb, old_mask, HS.ERODE_PX) == pytest.approx(0.0, abs=1e-9)


def test_survey_view_reports_the_curve_and_not_only_one_cut():
    """A locator that quoted a single number would be read as a verdict."""
    rgb = np.full((30, 30, 3), (136, 98, 79), np.uint8)
    mask = np.ones((30, 30), bool)
    rec = HS.survey_view(rgb, mask)
    assert set(rec["low_saturation_fraction"]) == {"0.10", "0.15", "0.20", "0.25"}
    assert set(rec["saturation_percentiles"]) == {"1", "5", "10", "25", "50", "75", "95"}
    assert rec["interior_px"] == 900         # border-extended; see the erosion test above


def test_an_all_grey_figure_reads_as_entirely_unpainted():
    """The direction the instrument exists to detect, at its limit."""
    rgb = np.full((30, 30, 3), 200, np.uint8)
    rec = HS.survey_view(rgb, np.ones((30, 30), bool))
    assert rec["low_saturation_fraction"]["0.10"] == 1.0
