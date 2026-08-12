"""The A/B timeline: two arms at different rates, neither resampled, neither retimed.

All arithmetic, no images — the timing is the part that can be wrong in a way nobody sees.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import make_ab_clip as AB


def test_the_union_of_two_rates_counts_the_shared_instants_once():
    """65 at 16 fps and 81 at 20 fps share every t = k/4 s: 17 instants, so the composite
    is 129 frames rather than 146."""
    tl = AB.event_timeline(65, 16, 81, 20)
    assert len(tl) == 129
    assert tl[0] == (0.0, 0, 0)
    assert tl[-1][0] == pytest.approx(4.0)
    assert tl[-1][1] == 64 and tl[-1][2] == 80


def test_each_side_holds_its_own_frame_between_its_own_events():
    """At t = 1/20 s the 20 fps arm has advanced and the 16 fps arm has not."""
    tl = dict((round(t, 6), (x, y)) for t, x, y in AB.event_timeline(65, 16, 81, 20))
    assert tl[0.0] == (0, 0)
    assert tl[round(1 / 20, 6)] == (0, 1)          # B stepped, A held
    assert tl[round(1 / 16, 6)] == (1, 1)          # A stepped
    assert tl[round(1 / 4, 6)] == (4, 5)           # both land together at 0.25 s


def test_every_frame_of_both_arms_appears_exactly_once():
    tl = AB.event_timeline(65, 16, 81, 20)
    a_seen = [x for _t, x, _y in tl]
    b_seen = [_y for _t, _x, _y in tl]
    assert sorted(set(a_seen)) == list(range(65))
    assert sorted(set(b_seen)) == list(range(81))


def test_the_delays_are_whole_milliseconds_that_do_not_drift():
    """1/16 s is 62.5 ms. Rounding each delay on its own drifts half a millisecond per
    frame — half a frame over four seconds — so they come from rounded cumulative times."""
    tl = AB.event_timeline(65, 16, 81, 20)
    d = AB.durations_ms([t for t, _x, _y in tl], 1 / 16.0)
    assert all(isinstance(v, int) for v in d)
    assert all(v > 0 for v in d)
    # the whole clip is the longer arm's own length, to within a millisecond
    assert abs(sum(d) - 1000 * 65 / 16) <= 1
    # and no cumulative edge is ever more than half a millisecond from the true time
    cum = 0
    for (t, _x, _y), v in zip(tl, d):
        assert abs(cum - t * 1000.0) <= 0.5
        cum += v


def test_a_naive_per_delay_rounding_would_have_drifted_and_this_shows_it():
    """The implementation this test exists to catch, built and shown failing."""
    tl = AB.event_timeline(65, 16, 81, 20)
    times = [t for t, _x, _y in tl]
    naive = [int(round((times[i + 1] - times[i]) * 1000.0)) for i in range(len(times) - 1)]
    naive.append(int(round(1000 / 16)))
    good = AB.durations_ms(times, 1 / 16.0)
    assert abs(sum(good) - 1000 * 65 / 16) <= 1
    assert abs(sum(naive) - 1000 * 65 / 16) > 5


def test_two_arms_at_the_same_rate_produce_a_frame_per_frame_composite():
    tl = AB.event_timeline(10, 20, 10, 20)
    assert len(tl) == 10
    assert [(x, y) for _t, x, y in tl] == [(i, i) for i in range(10)]


def test_the_last_composite_frame_is_held_for_a_real_duration():
    tl = AB.event_timeline(65, 16, 81, 20)
    d = AB.durations_ms([t for t, _x, _y in tl], 1 / 16.0)
    assert d[-1] == pytest.approx(1000 / 16, abs=1)
