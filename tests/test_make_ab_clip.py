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


# ------------------------------- the banner names the FILE's number, not its position
#
# The banner burned into every composite frame read `f{x}` / `f{y}`, where x and y are
# POSITIONS produced by `event_timeline(len(pa), ...)` — indices into `range(n_a)` — not the
# frame numbers in the file names `frame_paths` sorted. Measured 2026-09-04: two arms whose
# files are `00005.png, 00006.png, 00007.png` give timeline indices (0,0), (1,1), (2,2), so
# the clip the Director watches was captioned `f0 f1 f2` over frames 5, 6 and 7 — and the
# `_manifest.json` recorded only `frames: 3` and `fps`, so nothing in the record recovered
# the mapping. A note taken off the clip ("the hand melts around f12") then names a frame
# that is not the file, and the still pulled for the sheet is the wrong one.
#
# This is the same position-vs-number distinction `measure_lift.gate_pairing`'s docstring
# names as the defect it exists for. `make_ab_clip` is correctly OUTSIDE that gate — it
# pairs by TIME by design and its module docstring argues that at length — so this is the
# LABELLING half only, not a pairing defect.

import json as _json  # noqa: E402
import os  # noqa: E402

from PIL import Image  # noqa: E402


def _numbered_dir(tmp, name, numbers, size=(8, 6)):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for k, n in enumerate(numbers):
        Image.new("RGB", size, (10 * k, 20, 30)).save(d / f"{n:05d}.png")
    return str(d)


def test_the_manifest_records_each_arms_own_frame_numbers(tmp_path):
    a = _numbered_dir(tmp_path, "a", [5, 6, 7])
    b = _numbered_dir(tmp_path, "b", [5, 6, 7])
    out = tmp_path / "ab.webp"
    AB.main([f"--a={a}", f"--b={b}", "--a-fps=8", "--b-fps=8", f"--out={out}"])
    man = _json.loads((tmp_path / "ab_manifest.json").read_text(encoding="utf-8"))
    assert man["a"]["frame_numbers"] == [5, 6, 7]
    assert man["b"]["frame_numbers"] == [5, 6, 7]


def test_the_banner_text_is_built_from_the_file_number(tmp_path):
    """Read off the composite the tool builds, not off the source: `banner` is what burns
    the caption in, and the first composite frame must name 00005."""
    a = _numbered_dir(tmp_path, "a", [5, 6, 7])
    b = _numbered_dir(tmp_path, "b", [5, 6, 7])
    captured = []
    real_banner = AB.banner

    def spy(im, text, height=22):
        captured.append(text)
        return real_banner(im, text, height)

    AB.banner = spy
    try:
        AB.main([f"--a={a}", f"--b={b}", "--a-fps=8", "--b-fps=8",
                 f"--out={tmp_path / 'ab.webp'}"])
    finally:
        AB.banner = real_banner
    assert "00005" in captured[0], captured[:2]
    assert "f0 " not in captured[0] and not captured[0].rstrip().endswith("f0")
    assert [t for t in captured if "00007" in t], captured


def test_frame_numbers_reads_the_name_not_the_order(tmp_path):
    a = _numbered_dir(tmp_path, "a", [5, 6, 7])
    assert AB.frame_numbers(AB.frame_paths(a)) == [5, 6, 7]
