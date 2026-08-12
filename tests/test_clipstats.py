"""Tests for the clip measurements, built around one question per instrument:

    what value does this take when the arm does nothing, and when it works perfectly?

The law is CLAUDE.md's — grade an arm only on what it can move — and the fixture that
matters most here is `test_a_moving_subject_does_not_move_the_horizon`, because that is the
entire claim that makes `horizon_row` a camera measurement rather than a fourth way of
noticing that something in the picture changed.
"""

import numpy as np
import pytest

from armature_core import clipstats as CS


H, W = 120, 200
HORIZON = 40


def studio(subject_x=None, subject_w=14, shift=0, gain=1.0):
    """A grey backdrop over a white floor, optionally with a dark figure standing on it.

    `shift` moves the whole room down the frame — a camera tilt. `gain` scales the whole
    image — an exposure change that moves no geometry at all.
    """
    img = np.zeros((H, W, 3), dtype=np.float64)
    row = HORIZON + shift
    img[:row, :, :] = 40.0
    img[row:, :, :] = 230.0
    if subject_x is not None:
        x0 = int(subject_x)
        img[row - 30:row + 10, x0:x0 + subject_w, :] = 90.0
    return np.clip(img * gain, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------------------- luma

def test_luma_uses_rec_709_and_is_not_a_plain_mean():
    """A plain channel mean would call pure green and pure blue equally bright. Every
    luminance number in a report rests on which weights were used, so they are asserted."""
    green = np.zeros((2, 2, 3), dtype=np.uint8)
    green[..., 1] = 255
    blue = np.zeros((2, 2, 3), dtype=np.uint8)
    blue[..., 2] = 255
    assert CS.luma(green).mean() == pytest.approx(255 * 0.7152)
    assert CS.luma(blue).mean() == pytest.approx(255 * 0.0722)
    assert CS.luma(green).mean() > CS.luma(blue).mean()


def test_luma_refuses_a_frame_that_is_not_three_channel():
    with pytest.raises(ValueError):
        CS.luma(np.zeros((4, 4), dtype=np.uint8))


# ------------------------------------------------------------- the do-nothing baselines

def test_a_frozen_clip_reads_zero_movement_on_every_instrument():
    """The do-nothing arm. Anything that reads non-zero here is measuring noise."""
    frames = [studio(subject_x=90) for _ in range(8)]
    assert CS.frame_deltas(frames)["stats"]["max"] == 0.0
    assert CS.luma_series(frames)["stats"]["max"] == 0.0
    sim = CS.similarity_to_first(frames)
    assert max(sim["per_frame_mean_abs"]) == 0.0
    assert min(sim["per_frame_correlation"]) == pytest.approx(1.0)
    assert CS.distinct_frames(frames)["n_distinct"] == 1


def test_distinct_frames_counts_a_clip_that_froze_as_one():
    """65 files and one picture is a real outcome, and the count is what shows it."""
    frames = [studio(subject_x=90) for _ in range(65)]
    frames[10] = studio(subject_x=95)
    assert CS.distinct_frames(frames) == {"n_frames": 65, "n_distinct": 2}


# ------------------------------------------------------------------------- horizon_row

def test_the_horizon_is_found_where_it_was_drawn():
    ev = CS.horizon_row(studio())
    assert ev["verdict"] == "found"
    assert ev["row"] == pytest.approx(HORIZON, abs=1.0)
    assert ev["agreement"] == pytest.approx(1.0)


def test_a_moving_subject_does_not_move_the_horizon():
    """THE claim. A figure crossing a locked-off frame changes every whole-image
    statistic; if it also moved this one, nothing in the clip would separate a dancing
    figure from a drifting camera, and H-E11d would be unanswerable.
    """
    rows, sims = [], []
    base = studio(subject_x=20)
    for x in range(20, 160, 20):
        f = studio(subject_x=x)
        rows.append(CS.horizon_row(f)["row"])
        sims.append(CS.similarity_to_first([base, f])["per_frame_mean_abs"][1])
    assert len(set(rows)) == 1, rows
    assert max(sims) > 0.0, "the fixture must actually change the picture"


def test_a_tilting_camera_does_move_the_horizon():
    """The works-perfectly arm. Same instrument, opposite answer."""
    rows = [CS.horizon_row(studio(subject_x=90, shift=s))["row"] for s in (0, 5, 10, 15)]
    assert rows == sorted(rows) and rows[-1] - rows[0] == pytest.approx(15, abs=1.0)


def test_a_repainted_room_reports_not_found_rather_than_a_number():
    """The instrument's own failure mode, reported as a failure. Random texture has no
    single horizontal edge, and returning a plausible row for it would be a measurement of
    nothing — which is the shape of the two diagnostics E08 had to report as failed."""
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 255, size=(H, W, 3), dtype=np.uint8)
    ev = CS.horizon_row(noise)
    assert ev["row"] is None
    assert ev["verdict"].startswith("NOT FOUND")
    assert ev["agreement"] < ev["min_agreement"]


def test_the_horizon_search_refuses_a_band_with_nothing_in_it():
    with pytest.raises(ValueError):
        CS.horizon_row(studio(), band=(10, 11))


# ------------------------------------------------------------------ similarity_to_first

def test_correlation_separates_a_dimmed_picture_from_a_different_picture():
    """The reason both numbers are reported. A clip that only loses exposure reads a large
    mean-abs at a correlation still pinned to 1; a clip whose content changed reads a
    correlation that actually falls. One number alone cannot tell those apart."""
    base = studio(subject_x=90)
    dimmed = studio(subject_x=90, gain=0.6)
    moved = studio(subject_x=150)

    dim = CS.similarity_to_first([base, dimmed])
    mov = CS.similarity_to_first([base, moved])

    assert dim["per_frame_mean_abs"][1] > 10.0
    assert dim["per_frame_correlation"][1] == pytest.approx(1.0, abs=1e-6)
    assert mov["per_frame_correlation"][1] < 0.9999


def test_similarity_to_the_first_frame_is_zero_at_the_first_frame():
    frames = [studio(subject_x=x) for x in (20, 60, 100)]
    sim = CS.similarity_to_first(frames)
    assert sim["per_frame_mean_abs"][0] == 0.0
    assert sim["per_frame_correlation"][0] == pytest.approx(1.0)


# ------------------------------------------------------------------------ luma_series

def test_the_segment_medians_expose_a_swing_a_single_median_would_hide():
    """E10's clip was quiet in its first quarter and violent in its second; one median over
    the whole clip reported neither. The quarters are what showed the shape."""
    frames = [studio(subject_x=90, gain=1.0) for _ in range(20)]
    frames += [studio(subject_x=90, gain=1.0 if i % 2 else 0.5) for i in range(20)]
    ev = CS.luma_series(frames)
    assert ev["segment_medians"]["q1"] == pytest.approx(0.0, abs=1e-9)
    assert ev["segment_medians"]["q4"] > 20.0


def test_frame_deltas_returns_one_fewer_number_than_there_are_frames():
    frames = [studio(subject_x=x) for x in range(20, 120, 20)]
    assert len(frame_delta_list(frames)) == len(frames) - 1


def frame_delta_list(frames):
    return CS.frame_deltas(frames)["per_frame"]
