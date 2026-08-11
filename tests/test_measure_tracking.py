"""Tests for the timing-correlation instrument.

Every fixture here was written by asking the question the repo asks of a fixture: *what
would this look like if the code were wrong in the specific way this check exists to
catch?* The failures being guarded are, in order of how quietly they would pass:

* **the colour mode drifts to RGB** — returns numbers, plausible ones, ~0.037 off on A1a,
  which is over half the gap E04 exists to put a floor under;
* **the frame axis gets scrambled** by a lexical sort over ragged names — still returns a
  correlation, over the wrong time axis;
* **a constant clip returns nan** — printed beside real numbers, reads as "low";
* **the anchor passes vacuously** because E02's gitignored runs are not on disk.

The anchor leg itself needs E02's outputs, which are gitignored, so those tests skip
outside the rig. What does NOT skip is the check that the anchor *can* fail — a check
that cannot fail is not a check.
"""

import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import measure_tracking as mt  # noqa: E402

E02_ROOT = "outputs/E02"
HAVE_E02 = os.path.isdir(os.path.join(E02_ROOT, "runs"))


# ------------------------------------------------------------------ fixture helpers

def write_frames(d, arrays, width=8, height=8, pad=5):
    """Write frames from a list of per-frame (r, g, b) fill levels."""
    os.makedirs(d, exist_ok=True)
    for i, rgb in enumerate(arrays):
        a = np.zeros((height, width, 3), dtype=np.uint8)
        a[:, :] = rgb
        Image.fromarray(a, "RGB").save(os.path.join(d, f"{i:0{pad}d}.png"))
    return d


def gray_frames(d, levels, **kw):
    return write_frames(d, [(v, v, v) for v in levels], **kw)


# ---------------------------------------------------------------- floor and ceiling

def test_a_run_whose_energy_tracks_the_control_exactly_gives_plus_one(tmp_path):
    """The ceiling, stated before any real number is read."""
    levels = [0, 10, 40, 45, 90, 100, 160]
    run = gray_frames(str(tmp_path / "run"), levels)
    ctl = gray_frames(str(tmp_path / "ctl"), levels)
    assert mt.measure(run, ctl)["timing_correlation"] == pytest.approx(1.0)


def test_an_anti_correlated_run_gives_minus_one(tmp_path):
    """The floor. An arm can be anti-correlated, and the tool must be able to say so.

    A rising energy profile against a falling one is exactly -1. (An earlier version of
    this fixture used a profile against its own reverse, which is *not* anti-correlation:
    reversing [10,30,5,50,20] correlates at +0.61. The fixture was wrong, not the tool.)
    """
    run = gray_frames(str(tmp_path / "run"), np.cumsum([0, 10, 20, 30, 40]).tolist())
    ctl = gray_frames(str(tmp_path / "ctl"), np.cumsum([0, 40, 30, 20, 10]).tolist())
    assert mt.measure(run, ctl)["timing_correlation"] == pytest.approx(-1.0)


def test_correlation_is_scale_invariant(tmp_path):
    """A brighter clip that moves at the same moments must not read as tracking better.

    Levels are chosen even so halving is exact — integer rounding in the fixture would
    otherwise put the answer at 0.9997 and this would look like a tool defect.
    """
    base = [0, 20, 80, 90, 180, 200, 240]
    run = gray_frames(str(tmp_path / "run"), base)
    ctl = gray_frames(str(tmp_path / "ctl"), [v // 2 for v in base])
    assert mt.measure(run, ctl)["timing_correlation"] == pytest.approx(1.0)


# ------------------------------------------------- the colour mode is part of the definition

def test_the_statistic_is_GRAYSCALE_and_RGB_would_give_a_different_answer(tmp_path):
    """The pin on `convert("L")`.

    Frames move in R on some steps and in G on others. Grayscale weights those 0.299 and
    0.587; a per-channel RGB mean weights both 1/3 — so the two modes see different
    profile *shapes*, not just different scales, and correlation cannot absorb it.

    If someone changes the tool to RGB, this test fails. That is the whole job: E02's
    published +0.521 is the L-mode value, and the RGB-mode value for the same frames is
    +0.558.
    """
    # cumulative levels: R steps then G steps, alternating magnitudes
    frames = [(0, 0, 0), (30, 0, 0), (30, 30, 0), (40, 30, 0), (40, 40, 0)]
    run = write_frames(str(tmp_path / "run"), frames)
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 10, 30, 60, 100])

    got = mt.measure(run, ctl)["timing_correlation"]

    def rgb_mode_value():
        names = sorted(os.listdir(run))
        stack = np.stack([np.asarray(Image.open(os.path.join(run, n)).convert("RGB"),
                                     dtype=np.float64) for n in names])
        prof = np.abs(np.diff(stack, axis=0)).mean(axis=(1, 2, 3))
        cnames = sorted(os.listdir(ctl))
        cstack = np.stack([np.asarray(Image.open(os.path.join(ctl, n)).convert("L"),
                                      dtype=np.float64) for n in cnames])
        cprof = np.abs(np.diff(cstack, axis=0)).mean(axis=(1, 2))
        return float(np.corrcoef(prof, cprof)[0, 1])

    assert abs(got - rgb_mode_value()) > 0.05, (
        "the fixture no longer discriminates between L and RGB, so this test would pass "
        "for a tool that had silently switched colour mode"
    )
    assert mt.measure(run, ctl)["colour_mode"].startswith("L")


def test_the_control_profile_is_blind_to_polarity(tmp_path):
    """`255 - x` on the control must leave the statistic untouched.

    Measured on E02's own pair (max difference 0.0 over 32 deltas), and it is the reason
    both E04 conditions correlate against the same reference profile. A tool that squared
    or signed the deltas instead of taking their absolute value would break this.
    """
    levels = [10, 30, 35, 80, 120, 130]
    run = gray_frames(str(tmp_path / "run"), [0, 20, 25, 90, 100, 150])
    ctl = gray_frames(str(tmp_path / "ctl"), levels)
    inv = gray_frames(str(tmp_path / "inv"), [255 - v for v in levels])

    a, b = mt.load_profile(ctl)[0], mt.load_profile(inv)[0]
    assert np.abs(a - b).max() == 0.0
    assert (mt.measure(run, ctl)["timing_correlation"]
            == pytest.approx(mt.measure(run, inv)["timing_correlation"]))


# --------------------------------------------------------------------- refusals

def test_a_clip_that_never_moves_raises_rather_than_returning_nan(tmp_path):
    """nan is the absence of a measurement, not a low correlation."""
    run = gray_frames(str(tmp_path / "run"), [40] * 6)
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 10, 40, 45, 90, 100])
    with pytest.raises(mt.TrackingError, match="constant"):
        mt.measure(run, ctl)


def test_a_constant_CONTROL_also_raises(tmp_path):
    """Both directions. A control that does not move cannot grade an arm that does."""
    run = gray_frames(str(tmp_path / "run"), [0, 10, 40, 45, 90, 100])
    ctl = gray_frames(str(tmp_path / "ctl"), [40] * 6)
    with pytest.raises(mt.TrackingError, match="constant"):
        mt.measure(run, ctl)


def test_ragged_frame_names_raise_instead_of_scrambling_the_time_axis(tmp_path):
    """`1.png, 2.png, 10.png` sorts 1, 10, 2 — and still returns a correlation."""
    d = str(tmp_path / "ragged")
    os.makedirs(d)
    for i, v in enumerate([0, 10, 40, 45, 90, 100, 160, 200, 210, 240, 250]):
        a = np.full((8, 8, 3), v, dtype=np.uint8)
        Image.fromarray(a, "RGB").save(os.path.join(d, f"{i}.png"))
    with pytest.raises(mt.TrackingError, match="fixed width"):
        mt.load_profile(d)


def test_mismatched_frame_counts_raise(tmp_path):
    run = gray_frames(str(tmp_path / "run"), [0, 10, 40, 45, 90])
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 10, 40, 45, 90, 100, 160])
    with pytest.raises(mt.TrackingError, match="frame counts differ"):
        mt.measure(run, ctl)


def test_too_few_frames_raise(tmp_path):
    run = gray_frames(str(tmp_path / "run"), [0, 40])
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 40])
    with pytest.raises(mt.TrackingError, match="degenerate"):
        mt.measure(run, ctl)


def test_an_empty_or_missing_directory_raises(tmp_path):
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 10, 40, 45, 90])
    with pytest.raises(mt.TrackingError, match="no such frame directory"):
        mt.measure(str(tmp_path / "nope"), ctl)
    os.makedirs(str(tmp_path / "empty"))
    with pytest.raises(mt.TrackingError, match="no PNG frames"):
        mt.measure(str(tmp_path / "empty"), ctl)


def test_the_report_names_its_own_inputs(tmp_path):
    """A number with no provenance is not evidence."""
    run = gray_frames(str(tmp_path / "run"), [0, 10, 40, 45, 90])
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 20, 25, 90, 100])
    rec = mt.measure(run, ctl, label="probe")
    assert rec["label"] == "probe"
    assert rec["tool_version"] == mt.TOOL_VERSION
    assert len(rec["run"]["manifest_sha256"]) == 64
    assert rec["run"]["manifest_sha256"] != rec["control"]["manifest_sha256"]
    assert rec["n_deltas"] == rec["n_frames"] - 1 == 4


# ------------------------------------------------------------------- the anchor leg

def test_the_anchor_reports_NOT_RUN_rather_than_passing_vacuously(tmp_path):
    """An anchor that reports green when it read nothing is worse than no anchor."""
    assert mt.anchor(str(tmp_path / "no-such-root")) is None


@pytest.mark.skipif(not HAVE_E02, reason="E02 runs are gitignored output")
def test_the_anchor_reproduces_every_published_E02_figure():
    rows = mt.anchor(E02_ROOT)
    assert rows is not None and len(rows) == 5
    for r in rows:
        assert r["delta"] <= mt.ANCHOR_TOLERANCE, r


@pytest.mark.skipif(not HAVE_E02, reason="E02 runs are gitignored output")
def test_the_anchor_CAN_fail(monkeypatch):
    """Drive it to failure. A check that cannot fail is not a check."""
    monkeypatch.setitem(mt.E02_PUBLISHED, "A1a",
                        dict(mt.E02_PUBLISHED["A1a"], value=0.999))
    with pytest.raises(mt.AnchorMismatch, match="does not reproduce"):
        mt.anchor(E02_ROOT)


@pytest.mark.skipif(not HAVE_E02, reason="E02 runs are gitignored output")
def test_A1a_lossless_and_A1a_H264_are_NOT_the_same_number():
    """Why `E02_PUBLISHED` points A1a at A0r1's frames.

    A1a ran before the lossless tap existed. Its own frames came back through H.264, and
    the codec moves this statistic by ~0.025 — about 40% of the 0.060 gap E04 exists to
    put a floor under. Pointing the anchor at the wrong directory would miss by more than
    the tolerance, which is what makes this an anchor rather than a formality.
    """
    ctl = os.path.join(E02_ROOT, "control_480x832", "depth_pershot")
    lossless = mt.measure(os.path.join(E02_ROOT, "runs", "A0r1", "lossless"), ctl)
    h264_dir = os.path.join(E02_ROOT, "runs", "A1a", "frames")
    if not os.path.isdir(h264_dir):
        pytest.skip("A1a's H.264 frames are not on disk")
    h264 = mt.measure(h264_dir, ctl)
    assert abs(lossless["timing_correlation"] - h264["timing_correlation"]) > 0.02
    assert lossless["timing_correlation"] == pytest.approx(0.521, abs=0.0005)
