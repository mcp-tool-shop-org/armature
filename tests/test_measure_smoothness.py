"""The smoothness diagnostic, against paths whose second differences are known exactly.

The fixtures are the two cases the report has to be able to tell apart: a path that is
genuinely straight (no acceleration at any sampling), and a path that turns at a knot (the
turn survives resampling and only its per-frame size changes).
"""

import math

import pytest

from conftest import TOOLS  # noqa: F401
import measure_smoothness as MS


def test_a_straight_constant_speed_path_has_no_second_difference():
    path = [(0.0, 0.0), (2.0, 0.0), (4.0, 0.0), (6.0, 0.0), (8.0, 0.0)]
    assert MS.second_differences(path) == pytest.approx([0.0, 0.0, 0.0])
    assert MS.first_differences(path) == pytest.approx([2.0, 2.0, 2.0, 2.0])


def test_a_single_corner_puts_the_whole_turn_in_one_step():
    """Right-angle turn at the middle sample: |Δv| = |(0,2) - (2,0)| = 2*sqrt(2)."""
    path = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)]
    assert MS.second_differences(path) == pytest.approx([2.0 * math.sqrt(2)])


def test_halving_the_step_quarters_the_second_difference_on_a_smooth_path():
    """A parabola sampled twice as densely: the (Δt)² law, which is the arithmetic the
    prediction for this experiment was reasoned from."""
    coarse = [(t, t * t) for t in (0.0, 1.0, 2.0, 3.0, 4.0)]
    fine = [(t / 2.0, (t / 2.0) ** 2) for t in range(9)]
    assert MS.second_differences(coarse) == pytest.approx([2.0] * 3)
    assert MS.second_differences(fine) == pytest.approx([0.5] * 7)


def test_the_per_second_unit_is_invariant_to_the_sampling_of_a_smooth_path():
    """THE control column. Same parabola, two sampling rates, same acceleration in wall
    clock — so a per-second number that moved would be measuring the resampling."""
    coarse = [(t, t * t) for t in (0.0, 1.0, 2.0, 3.0, 4.0)]
    fine = [(t / 2.0, (t / 2.0) ** 2) for t in range(9)]
    fps_c, fps_f = 10.0, 20.0
    ac = [v * fps_c * fps_c for v in MS.second_differences(coarse)]
    af = [v * fps_f * fps_f for v in MS.second_differences(fine)]
    assert MS.stats(ac)["median"] == pytest.approx(MS.stats(af)["median"])


def test_a_corner_survives_resampling_and_only_its_per_frame_size_changes():
    """What a piecewise-geodesic path does: the turn is still there, scaled by the interval
    ratio. This is why the report quotes a distribution and not a mean."""
    coarse = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)]
    fine = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (2.0, 2.0)]
    assert max(MS.second_differences(fine)) == pytest.approx(
        0.5 * max(MS.second_differences(coarse)))
    assert len([v for v in MS.second_differences(fine) if v > 1e-12]) == 1


def test_stats_reports_a_distribution_rather_than_a_number():
    st = MS.stats([1.0, 2.0, 3.0, 4.0, 100.0])
    assert st["median"] == 3.0 and st["max"] == 100.0
    assert st["mean"] == pytest.approx(22.0)
    assert st["n"] == 5


def test_ratios_refuse_to_divide_by_a_zero_baseline():
    a = MS.stats([0.0, 0.0, 0.0])
    b = MS.stats([1.0, 1.0, 1.0])
    assert MS.ratios(a, b)["median"] is None


def _record(paths, fps, res=(832, 480), radius=1.0, target=(0.0, 0.0, 0.0)):
    n = len(paths[0])
    return {"resolution": list(res), "fps": fps, "frames": n,
            "camera": {"radius": radius, "target": list(target)},
            "keypoint_names": [f"kp{i}" for i in range(len(paths))],
            "body": [[[p[i][0], p[i][1], 1.0] for p in paths] for i in range(n)]}


def test_pooled_and_per_keypoint_agree_on_a_single_keypoint_record():
    rec = _record([[(t, t * t) for t in range(5)]], 16)
    p = MS.pooled(rec, 16)
    k = MS.measure(rec, 16)[0]
    assert p["second_px_per_frame2"] == k["second_px_per_frame2"]


def test_a_keypoint_whose_second_difference_rose_is_named_not_averaged_away():
    """The report must be able to say WHICH joint got worse, not only that the mean fell."""
    steady = [(t, 0.0) for t in range(5)]
    jumpy = [(0.0, 0.0), (1.0, 0.0), (0.0, 0.0), (1.0, 0.0), (0.0, 0.0)]
    a = MS.measure(_record([steady, steady], 16), 16)
    b = MS.measure(_record([steady, jumpy], 16), 16)
    assert MS.ratios(a[1]["second_px_per_frame2"], b[1]["second_px_per_frame2"]) is not None
    assert b[1]["second_px_per_frame2"]["median"] > a[1]["second_px_per_frame2"]["median"]
