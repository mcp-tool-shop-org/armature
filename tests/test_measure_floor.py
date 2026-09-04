"""The fixed-seed floor: the denominator every later number in E02/E04 is read against.

Two ways this instrument produced a perfect zero floor from a comparison it never made.

**Truncation.** `pair_stats` paired frames with `zip(A, B)`, which stops at the shorter run,
and `n` came from the FIRST run alone. Measured: r1 with 5 frames against r2 with 9 whose
last four are wildly different printed `2 runs . 5 frames . 1 pairs`, `frames identical:
5/5`, `pair bit-identical overall: YES`, and wrote floor.json saying the same. Four frames
were never opened and nothing said so — on the day a provider returns a short or long
re-run, which is the exact non-determinism this instrument exists to catch.

**A comparison of a thing to itself.** `itertools.combinations` over the raw `--runs` list
had no distinctness check, so `--runs=r2,r2` printed `r2|r2 frames identical: 9/9` and
`=> 1 of 1 pairs are bit-identical`. The repo's named defect, in the one tool whose whole
output is a claim about repeat variance.

Both refusals fire before any pixel is read, and both carry the counts that fired them.
"""

import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import measure_floor as MF  # noqa: E402


def _run(root, name, frames, h=4, w=4, seed=0):
    d = os.path.join(str(root), name, "lossless")
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(seed)
    for i in range(frames):
        Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8)).save(
            os.path.join(d, f"{i:05d}.png"))
    return name


# ------------------------------------------------------------------ ragged populations


def test_runs_of_different_lengths_raise_before_any_pair_is_compared(tmp_path):
    """5 / 5 / 9. The old code paired the first 5 of every run and called the floor zero."""
    for name, n in (("r1", 5), ("r2", 5), ("r3", 9)):
        _run(tmp_path, name, n)
    stacks = {r: MF._stack(os.path.join(str(tmp_path), r)) for r in ("r1", "r2", "r3")}

    with pytest.raises(MF.FloorError) as e:
        MF.common_frame_count(stacks)
    ev = e.value.evidence
    assert ev["frames_per_run"] == {"r1": 5, "r2": 5, "r3": 9}
    assert ev["counts"] == [5, 9]
    assert "r3" in str(e.value)


def test_equal_lengths_return_the_verified_count(tmp_path):
    for name in ("r1", "r2"):
        _run(tmp_path, name, 6)
    stacks = {r: MF._stack(os.path.join(str(tmp_path), r)) for r in ("r1", "r2")}
    assert MF.common_frame_count(stacks) == 6


def test_the_cli_halts_on_a_ragged_set_and_writes_no_floor(tmp_path):
    """End to end: the andon is inside the tool, not in a shell chain around it."""
    for name, n in (("r1", 5), ("r2", 9)):
        _run(tmp_path, name, n)
    out = tmp_path / "floor.json"
    with pytest.raises(MF.FloorError):
        MF.main([f"--runs=r1,r2", f"--root={tmp_path}", "--early=0-1", "--late=2-3",
                 f"--out={out}"])
    assert not out.exists()


# ------------------------------------------------------- a comparison with itself


def test_a_repeated_run_label_is_refused_before_any_stack_is_loaded(tmp_path):
    with pytest.raises(MF.FloorError) as e:
        MF.check_runs(["r2", "r2"])
    assert e.value.evidence["repeated"] == ["r2"]


def test_one_run_is_not_a_repeat_measurement(tmp_path):
    with pytest.raises(MF.FloorError) as e:
        MF.check_runs(["r1"])
    assert e.value.evidence["runs"] == ["r1"]


def test_two_distinct_runs_pass_the_check(tmp_path):
    assert MF.check_runs(["r1", "r2"]) == ["r1", "r2"]


def test_the_cli_refuses_a_repeated_label_without_touching_the_disk(tmp_path):
    """No run directory exists at all: the refusal must arrive before the first _stack."""
    out = tmp_path / "floor.json"
    with pytest.raises(MF.FloorError) as e:
        MF.main([f"--runs=r2,r2", f"--root={tmp_path}", f"--out={out}"])
    assert e.value.evidence["repeated"] == ["r2"]
    assert not out.exists()


# -------------------------------------------------------------------- the happy path


def test_two_identical_runs_still_report_a_zero_floor(tmp_path):
    """The guard the other way: the refusals must not have made a real zero unreachable."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 4, seed=7)
    out = tmp_path / "floor.json"
    rec = MF.main([f"--runs=r1,r2", f"--root={tmp_path}", "--early=0-1", "--late=2-3",
                   f"--out={out}"])
    assert rec["n_frames"] == 4
    assert rec["whole_clip"]["frames_differing"] == 0
    assert out.exists()


# ------------------------------------------- windows the run's own length has to bound
#
# `--early`/`--late` defaulted to the literals `0-4` and `29-32` — E02's 33-frame clip
# written into the tool, with no relation to the run in front of it. Both directions were
# measured on 2026-09-03.
#
# SILENT: two 31-frame runs printed `EARLY (frames 0-4) vs LATE (frames 29-32)` with the
# late line computed over TWO frames (29, 30), and wrote `"late_window": [29,30,31,32]`
# into floor.json beside it — the window named four frames and the number under it was
# measured over two.
#
# LOUD: two 17-frame runs (a generator-legal 4n+1 bucket) died at `min() iterable argument
# is empty` after every PNG had been loaded and every pair compared, writing no floor.json.


def test_the_default_windows_come_from_the_run_not_from_one_experiments_length(tmp_path):
    """17 frames. The literal defaults named 29-32, which do not exist here."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 17, seed=3)
    out = tmp_path / "floor.json"
    rec = MF.main([f"--runs=r1,r2", f"--root={tmp_path}", f"--out={out}"])
    assert rec["n_frames"] == 17
    assert rec["early_window"] and rec["late_window"]
    assert max(rec["late_window"]) < 17
    assert rec["window_source"]["late"].startswith("derived")


def test_a_requested_window_past_the_end_of_the_run_raises_naming_both(tmp_path):
    """The silent direction, refused: 29-32 asked of a 31-frame run."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 31, seed=5)
    out = tmp_path / "floor.json"
    with pytest.raises(MF.FloorError) as e:
        MF.main([f"--runs=r1,r2", f"--root={tmp_path}", "--early=0-4", "--late=29-32",
                 f"--out={out}"])
    ev = e.value.evidence
    assert ev["window"] == "late"
    assert ev["n_frames"] == 31
    assert ev["out_of_range"] == [31, 32]
    assert ev["requested"] == [29, 30, 31, 32]
    assert not out.exists()


def test_no_window_may_report_over_fewer_frames_than_it_names(tmp_path):
    """The invariant behind both directions: the RECORDED window is the MEASURED one."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 9, seed=11)
    out = tmp_path / "floor.json"
    rec = MF.main([f"--runs=r1,r2", f"--root={tmp_path}", f"--out={out}"])
    n = rec["n_frames"]
    for key in ("early_window", "late_window"):
        assert rec[key] == sorted(set(rec[key]))
        assert all(0 <= i < n for i in rec[key]), rec[key]
    # and the realised windows are what the pairs were read over
    assert len(rec["early_window"]) == len(rec["late_window"])


def test_an_in_range_request_is_still_honoured(tmp_path):
    """The guard the other way: bounding the windows must not make a real one unreachable."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 9, seed=11)
    rec = MF.main([f"--runs=r1,r2", f"--root={tmp_path}", "--early=0-2", "--late=6-8",
                   f"--out={tmp_path / 'floor.json'}"])
    assert rec["early_window"] == [0, 1, 2]
    assert rec["late_window"] == [6, 7, 8]
    assert rec["window_source"]["early"].startswith("requested")


def test_a_run_too_short_for_two_distinct_ends_refuses_rather_than_reporting_one_frame_twice(
        tmp_path):
    """A one-frame run derives an EARLY and a LATE window over the same single frame —
    two rows of the same number under two different headings."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 1, seed=13)
    with pytest.raises(MF.FloorError) as e:
        MF.main([f"--runs=r1,r2", f"--root={tmp_path}",
                 f"--out={tmp_path / 'floor.json'}"])
    assert e.value.evidence["n_frames"] == 1
    assert "overlap" in str(e.value)


# --------------------------------------------------- the population the floor is read over
#
# The wave-6 fix corrected the WINDOW half of the literal defect and left the POPULATION
# half untouched: `_stack` took the floor's frames from a bare `*.png` listing with no
# numbered filter, while every sibling in this domain that feeds an upload
# (`encode_control.frame_population`, `invert_frames.frame_population`,
# `measure_clip.frame_paths`, `gate_b_frames.frame_paths`) already filters — and their
# docstrings name the exact mechanism: `render_pose_sticks` writes a `strip_every{N}.png`
# contact sheet into the directory it just filled with `NNNNN.png` frames.
#
# Measured 2026-09-04 on this branch, two synthetic runs of 8 numbered frames plus one
# `strip_every8.png` each: `_stack` returned 9 arrays, `common_frame_count` returned 9, and
# `bound_windows(9)` derived `early=[0]` / `late=[8]` — the LATE end of the clip WAS the
# contact sheet. Because the stray is byte-identical across runs it also contributed an
# `identical: True` pair and lowered the reported floor. `n_frames: 9`, `late_window: [8]`
# and `frames_per_run` all went into floor.json.


def _stray(root, name, filename="strip_every8.png", size=(4, 4)):
    """A contact strip beside the numbered frames — `render_pose_sticks`' own output."""
    d = os.path.join(str(root), name, "lossless")
    os.makedirs(d, exist_ok=True)
    Image.fromarray(np.full((size[0], size[1], 3), 200, dtype=np.uint8)).save(
        os.path.join(d, filename))
    return os.path.join(d, filename)


def test_a_contact_strip_beside_the_frames_is_refused_not_counted_as_a_frame(tmp_path):
    for name in ("r1", "r2"):
        _run(tmp_path, name, 8, seed=17)
        _stray(tmp_path, name)
    with pytest.raises(MF.FloorError) as e:
        MF._stack(os.path.join(str(tmp_path), "r1"))
    ev = e.value.evidence
    assert ev["unexpected"] == ["strip_every8.png"], ev
    assert len(ev["frames"]) == 8, ev


def test_the_cli_halts_on_a_stray_and_writes_no_floor(tmp_path):
    """The andon is inside the tool that publishes the denominator, not beside it."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 8, seed=19)
        _stray(tmp_path, name)
    out = tmp_path / "floor.json"
    with pytest.raises(MF.FloorError) as e:
        MF.main([f"--runs=r1,r2", f"--root={tmp_path}", f"--out={out}"])
    assert "strip_every8.png" in str(e.value)
    assert not out.exists()


def test_the_same_runs_without_the_stray_still_measure(tmp_path):
    """The guard the other way: the refusal must not make a real floor unreachable."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 8, seed=19)
    out = tmp_path / "floor.json"
    rec = MF.main([f"--runs=r1,r2", f"--root={tmp_path}", f"--out={out}"])
    assert rec["n_frames"] == 8
    assert rec["frames_per_run"] == {"r1": 8, "r2": 8}


def test_an_empty_lossless_directory_raises_rather_than_returning_nothing(tmp_path):
    d = os.path.join(str(tmp_path), "r1", "lossless")
    os.makedirs(d, exist_ok=True)
    with pytest.raises(MF.FloorError) as e:
        MF._stack(os.path.join(str(tmp_path), "r1"))
    assert e.value.evidence["png_files"] == []


def test_expect_pins_the_population_to_the_specs_own_names(tmp_path):
    """A short run is a refusal, not a shorter floor."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 7, seed=23)
    with pytest.raises(MF.FloorError) as e:
        MF.main([f"--runs=r1,r2", f"--root={tmp_path}", "--expect=8",
                 f"--out={tmp_path / 'floor.json'}"])
    ev = e.value.evidence
    assert len(ev["expected"]) == 8 and len(ev["found"]) == 7, ev


def test_expect_that_matches_still_measures(tmp_path):
    for name in ("r1", "r2"):
        _run(tmp_path, name, 8, seed=23)
    rec = MF.main([f"--runs=r1,r2", f"--root={tmp_path}", "--expect=8",
                   f"--out={tmp_path / 'floor.json'}"])
    assert rec["n_frames"] == 8
    assert rec["expect"] == 8


def test_the_png_match_is_case_insensitive_like_its_four_siblings(tmp_path):
    """`00099.PNG` is a frame to `fetch_run.verify_downloads` and to `encode_control`;
    a floor population that cannot see it would report over fewer frames than were
    downloaded."""
    for name in ("r1", "r2"):
        _run(tmp_path, name, 3, seed=29)
        d = os.path.join(str(tmp_path), name, "lossless")
        Image.fromarray(np.zeros((4, 4, 3), dtype=np.uint8)).save(
            os.path.join(d, "00003.PNG"))
    assert len(MF._stack(os.path.join(str(tmp_path), "r1"))) == 4


# --------------------------------------------- the two ends are the SAME size, always
#
# `derive_window`'s docstring states the invariant the wave-6 fix was written for — "Both
# ends are the SAME size, which the literals were not (five frames early against four
# late) -- two windows of different sizes are not comparable rows" — but on the DERIVED
# path `k` is computed once and used at both ends, so the equality cannot be violated
# there. The andon sat on the direction the arithmetic already bounds and was absent from
# the direction the defect actually arrived on. Measured 2026-09-04:
# `bound_windows(33, '0-4', '29-32')` returned an early of 5 and a late of 4, no refusal —
# the exact literals the module docstring records as the defect, accepted verbatim.


def test_two_requested_windows_of_different_sizes_are_refused(tmp_path):
    with pytest.raises(MF.FloorError) as e:
        MF.bound_windows(33, "0-4", "29-32")
    ev = e.value.evidence
    assert ev["n_early"] == 5 and ev["n_late"] == 4, ev
    assert ev["early"] == [0, 1, 2, 3, 4]
    assert ev["late"] == [29, 30, 31, 32]
    assert "window_source" in ev


def test_two_requested_windows_of_the_same_size_are_accepted(tmp_path):
    """The guard the other way."""
    early, late, source = MF.bound_windows(33, "0-4", "28-32")
    assert len(early) == len(late) == 5
    assert source["early"].startswith("requested")


def test_the_size_invariant_holds_on_the_cli(tmp_path):
    for name in ("r1", "r2"):
        _run(tmp_path, name, 33, seed=31)
    out = tmp_path / "floor.json"
    with pytest.raises(MF.FloorError):
        MF.main([f"--runs=r1,r2", f"--root={tmp_path}", "--early=0-4", "--late=29-32",
                 f"--out={out}"])
    assert not out.exists()


# ------------------------------------------------- a malformed window is this tool's refusal


@pytest.mark.parametrize("text", ["5", "abc-def", "", "1-2-3", "0-"])
def test_a_malformed_window_raises_the_tools_own_error_not_a_bare_valueerror(text):
    """Every other way of getting a window wrong here raises `FloorError` with an
    evidence dict. `--early=5` — one number instead of a span — escaped as a raw
    `ValueError: invalid literal for int() with base 10: ''`."""
    with pytest.raises(MF.FloorError) as e:
        MF.bound_windows(33, text, None)
    ev = e.value.evidence
    assert ev["window"] == "early"
    assert ev["requested_text"] == text
    assert ev["expected_shape"] == "a-b"


def test_a_well_formed_window_still_parses():
    assert MF._span("0-4", "early") == [0, 1, 2, 3, 4]


def test_the_floor_andons_survive_python_optimize(tmp_path):
    """They raise; they are not asserts. `-O` deletes an assert."""
    import subprocess

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("r1", "r2"):
        _run(tmp_path, name, 8, seed=37)
        _stray(tmp_path, name)
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import measure_floor as MF\n"
        "try:\n"
        "    MF._stack(r'%s')\n"
        "except MF.FloorError:\n"
        "    print('STRAY_RAISED')\n"
        "try:\n"
        "    MF.bound_windows(33, '0-4', '29-32')\n"
        "except MF.FloorError:\n"
        "    print('SIZE_RAISED')\n"
        "try:\n"
        "    MF.bound_windows(33, '5', None)\n"
        "except MF.FloorError:\n"
        "    print('SPAN_RAISED')\n"
    ) % (os.path.join(root, "tools"), os.path.join(str(tmp_path), "r1"))
    out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "STRAY_RAISED" in out.stdout, out.stderr
    assert "SIZE_RAISED" in out.stdout, out.stderr
    assert "SPAN_RAISED" in out.stdout, out.stderr
