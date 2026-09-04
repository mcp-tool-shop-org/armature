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
