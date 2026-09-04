"""G3's instrument: what "zero difference" is allowed to mean, and what a pixel is.

Two defects, both of which produced the exact output of a run that genuinely reproduced.

**A clean report over nothing.** `compare_channel` initialised `max_abs_diff: 0` and never
distinguished "compared and equal" from "compared nothing". Measured: two runs whose channel
directories exist but hold zero PNGs printed
`{"max_abs_diff_any_channel": 0, "channels_with_any_pixel_difference": []}` and exited 0 —
byte for byte what a reproducing render prints. Two runs with no channel in common printed
the same line with a null max and exited 0 as well. A mistyped `--a`, a run whose channels
were written under other names, or an aborted render all land there.

**A pixel counted once per channel.** `n_differing_px = int((d > 0).sum())` sums over an
(H, W, C) array, so one differing RGB pixel counted 3. That is the unit/population/object
class this repo has missed nine arcs running, in the one number that says *where* a
difference lives.

The module still reports rather than halting on a nonzero difference — that is G3's whole
design. What raises is having compared nothing, which is not a measurement at all.
"""

import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import compare_runs as CR  # noqa: E402


def _png(path, arr):
    Image.fromarray(np.asarray(arr, dtype=np.uint8)).save(path)


def _run(root, name, chan="lossless", frames=1, mutate=None, h=4, w=4):
    d = os.path.join(str(root), name, chan)
    os.makedirs(d, exist_ok=True)
    for i in range(frames):
        a = np.full((h, w, 3), 100, dtype=np.uint8)
        if mutate is not None:
            a = mutate(a, i)
        _png(os.path.join(d, f"{i:05d}.png"), a)
    return os.path.join(str(root), name)


# ------------------------------------------------------------------- what a pixel is


def test_one_differing_rgb_pixel_counts_as_one_pixel(tmp_path):
    """THE fixture: a single pixel differing in all three channels. Counted over the
    (H, W, C) array it reads 3, and there is nothing beside it saying so."""
    def bump(a, i):
        a[0, 0] = (110, 110, 110)
        return a

    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b", mutate=bump)
    rec = CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))

    assert rec["worst_frame"]["n_differing_px"] == 1
    assert rec["worst_frame"]["n_differing_samples"] == 3
    assert rec["worst_frame"]["samples_per_pixel"] == 3


def test_a_pixel_differing_in_one_channel_still_counts_once(tmp_path):
    def bump(a, i):
        a[2, 3, 1] = 250
        return a

    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b", mutate=bump)
    rec = CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))
    assert rec["worst_frame"]["n_differing_px"] == 1
    assert rec["worst_frame"]["n_differing_samples"] == 1


def test_the_mean_is_named_after_the_thing_it_averages(tmp_path):
    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b")
    rec = CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))
    assert rec["mean_abs_diff_per_sample"] == 0.0
    assert rec["samples_per_pixel"] == 3


# --------------------------------------------------------- a report over nothing


def test_a_channel_with_no_frames_raises_rather_than_reporting_zero(tmp_path):
    a = _run(tmp_path, "a", frames=0)
    b = _run(tmp_path, "b", frames=0)
    with pytest.raises(CR.CompareError) as e:
        CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))
    assert e.value.evidence["frames_compared"] == 0
    assert e.value.evidence["names_a"] == []


def test_channels_whose_frames_are_all_shape_mismatched_raise(tmp_path):
    """The other way to compare nothing: every shared name exists on both sides and none
    of them is comparable. `continue` used to leave the record at its zero initialiser."""
    a = _run(tmp_path, "a", h=4, w=4)
    b = _run(tmp_path, "b", h=8, w=8)
    with pytest.raises(CR.CompareError) as e:
        CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))
    assert e.value.evidence["shape_mismatch"]


def test_runs_with_no_channel_in_common_raise(tmp_path):
    a = _run(tmp_path, "a", chan="lossless")
    b = _run(tmp_path, "b", chan="depth_perframe")
    with pytest.raises(CR.CompareError) as e:
        CR.compare_runs(a, b)
    assert e.value.evidence["channels_a"] == ["lossless"]
    assert e.value.evidence["channels_b"] == ["depth_perframe"]


def test_a_master_only_pair_is_not_a_comparison(tmp_path):
    """`master` is excluded by design, so two runs sharing only `master` share nothing."""
    a = _run(tmp_path, "a", chan="master")
    b = _run(tmp_path, "b", chan="master")
    with pytest.raises(CR.CompareError,
                       match=r"share no comparable channel directory \(master is excluded"):
        CR.compare_runs(a, b)


def test_the_printed_line_carries_how_many_frames_were_opened(tmp_path):
    """So a clean verdict cannot be read without the size of the population behind it."""
    a = _run(tmp_path, "a", frames=3)
    b = _run(tmp_path, "b", frames=3)
    report = CR.compare_runs(a, b)
    assert report["verdict_inputs"]["frames_compared"] == 3
    assert report["verdict_inputs"]["max_abs_diff_any_channel"] == 0


def test_a_real_difference_still_reports_rather_than_halting(tmp_path):
    """G3's design, pinned: a nonzero difference is a measurement, not an andon."""
    def bump(a, i):
        a[1, 1] = (200, 0, 0)
        return a

    a = _run(tmp_path, "a", frames=2)
    b = _run(tmp_path, "b", frames=2, mutate=bump)
    report = CR.compare_runs(a, b)
    assert report["verdict_inputs"]["max_abs_diff_any_channel"] == 100
    assert report["verdict_inputs"]["channels_with_any_pixel_difference"] == ["lossless"]


# ------------------------------------------------- a report over SOME of the population
#
# Wave 3's two andons refuse only a TOTAL absence of comparison. A PARTIAL one still read
# as a clean reproduction, with the evidence that contradicts it sitting in the JSON and
# absent from the verdict. Both measured 2026-09-03.


def test_a_six_frame_run_against_a_three_frame_one_is_not_a_reproduction(tmp_path):
    """An aborted render: A holds 6 frames, B holds the first 3, byte-identical. The old
    line read `frames_compared: 3, max_abs_diff_any_channel: 0` and exited 0, with
    `only_in_a: [00003,00004,00005]` unread in the per-channel record."""
    a = _run(tmp_path, "a", frames=6)
    b = _run(tmp_path, "b", frames=3)
    with pytest.raises(CR.CompareError) as e:
        CR.compare_runs(a, b)
    ev = e.value.evidence
    assert ev["frames_a"] == 6 and ev["frames_b"] == 3
    assert ev["only_in_a"] == ["00003.png", "00004.png", "00005.png"]


def test_some_shared_names_shape_mismatched_is_not_a_reproduction(tmp_path):
    """Four names on both sides, three of them rendered at another size with wholly
    different content: the pixel verdict said the render reproduced over one of four."""
    a = _run(tmp_path, "a", frames=4, h=8, w=8)
    b = os.path.join(str(tmp_path), "b")
    d = os.path.join(b, "lossless")
    os.makedirs(d, exist_ok=True)
    for i in range(4):
        side = 8 if i == 0 else 16
        _png(os.path.join(d, f"{i:05d}.png"), np.full((side, side, 3), 100, np.uint8))
    with pytest.raises(CR.CompareError) as e:
        CR.compare_runs(a, b)
    ev = e.value.evidence
    assert len(ev["shape_mismatch"]) == 3
    assert ev["frames_compared"] == 1


def test_the_printed_verdict_carries_the_two_populations_and_the_mismatch_counts(tmp_path):
    """A clean verdict may not be readable without the population behind it."""
    a = _run(tmp_path, "a", frames=3)
    b = _run(tmp_path, "b", frames=3)
    vi = CR.compare_runs(a, b)["verdict_inputs"]
    assert vi["frames_a"] == 3 and vi["frames_b"] == 3
    assert vi["n_name_mismatch"] == 0
    assert vi["n_shape_mismatch"] == 0


def test_the_partial_andon_survives_python_optimize(tmp_path):
    """It raises; it is not an `assert`. `-O` deletes an assert and this must survive."""
    import subprocess
    import sys as _sys

    a = _run(tmp_path, "a", frames=4)
    b = _run(tmp_path, "b", frames=2)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import compare_runs as CR\n"
        "try:\n"
        "    CR.compare_runs(r'%s', r'%s')\n"
        "except CR.CompareError:\n"
        "    print('RAISED')\n"
    ) % (os.path.join(repo, "tools"), a, b)
    out = subprocess.run([_sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "RAISED" in out.stdout, out.stderr
