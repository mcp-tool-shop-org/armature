"""Subject proportions, fixtured on the two assets E01 actually measured.

The fixtures are not invented shapes. `longsword_hero.glb` and
`blackguard_unirig_rigged.glb` are the real E01 subjects, and the reason this module
exists is that the first was believed to be the second for a whole dispatch. So the
question each test asks is: **what would this look like if the code were wrong in the
specific way that let a sword pass for a character?**

Two ways, both covered here:

  * halving — reporting the half-extent as the extent, so every dimension in a report
    is 2x too small while every *ratio* still looks right;
  * the wrong denominator — dividing longest by the middle axis instead of the
    shortest, which drops the blade from 15.8 to 3.6 and lands it among figures.
"""

import math

import pytest

from armature_core.subject import extent_summary

# E01, measured: half-extents. The sword's numbers are back-derived from the extents
# quoted in E01-ruling.md (0.226 x 1.002 x 0.063); the blackguard's are lifted from
# outputs/E01/runF_blackguard/manifest.json `scene.subject_bbox_half_extent`.
SWORD_HALF = (0.113, 0.501, 0.0315)
BLACKGUARD_HALF = (0.3016614466905594, 0.15501657873392105, 0.500672310590744)


def test_extents_are_the_full_box_not_the_half_box():
    """The off-by-2 that would halve every dimension a report quotes."""
    s = extent_summary(BLACKGUARD_HALF)
    assert s["extents"] == pytest.approx([0.60332289, 0.31003316, 1.00134462], abs=1e-6)
    # and it is emphatically not the input passed through
    assert s["extents"][2] != pytest.approx(BLACKGUARD_HALF[2])


def test_sword_reads_as_a_blade():
    """E01's ruling quotes 15.8. If this drifts, the discriminator has changed."""
    s = extent_summary(SWORD_HALF)
    assert s["aspect_longest_over_shortest"] == pytest.approx(15.9, abs=0.2)
    assert s["longest_axis"] == "Y"


def test_blackguard_reads_as_a_figure():
    s = extent_summary(BLACKGUARD_HALF)
    assert s["aspect_longest_over_shortest"] == pytest.approx(3.23, abs=0.02)
    assert s["longest_axis"] == "Z"


def test_the_two_subjects_are_not_confusable_on_the_chosen_unit():
    """The whole point: one number has to separate them by a wide margin."""
    sword = extent_summary(SWORD_HALF)["aspect_longest_over_shortest"]
    figure = extent_summary(BLACKGUARD_HALF)["aspect_longest_over_shortest"]
    assert sword > 4 * figure


def test_longest_over_middle_separates_them_too_but_by_less():
    """Why the denominator is the shortest axis — on the margin, not on a story.

    The first version of this test asserted that longest/middle *fails* to separate
    the two subjects. It does not: 4.43 vs 1.66 is a 2.7x gap, and the test failed on
    the arithmetic. The rejected alternative is rejected because it separates ~1.8x
    less widely, which is a real but much weaker reason than the one first claimed.
    Kept as a test so the margin is pinned and the wrong story cannot come back.
    """
    sword_m = extent_summary(SWORD_HALF)["aspect_longest_over_middle"]
    figure_m = extent_summary(BLACKGUARD_HALF)["aspect_longest_over_middle"]
    sword_s = extent_summary(SWORD_HALF)["aspect_longest_over_shortest"]
    figure_s = extent_summary(BLACKGUARD_HALF)["aspect_longest_over_shortest"]

    assert sword_m / figure_m == pytest.approx(2.67, abs=0.05)
    assert sword_s / figure_s == pytest.approx(4.92, abs=0.05)
    assert (sword_s / figure_s) > (sword_m / figure_m)


def test_degenerate_axis_reports_rather_than_raising():
    s = extent_summary((0.5, 0.5, 0.0))
    assert s["degenerate_axis"] is True
    assert math.isinf(s["aspect_longest_over_shortest"])


@pytest.mark.parametrize(
    "bad", [None, (1.0, 2.0), (1.0, 2.0, 3.0, 4.0), (1.0, -2.0, 3.0)]
)
def test_malformed_input_raises(bad):
    with pytest.raises(ValueError):
        extent_summary(bad)
