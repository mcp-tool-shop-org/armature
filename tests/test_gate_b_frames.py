"""Gate B's after-the-run half: did the pack the server decoded carry what we drew?

The frames here are tiny synthetic PNGs, so every fixture runs in milliseconds and none
of them needs a run.
"""

import os

import numpy as np
import pytest
from PIL import Image

from conftest import TOOLS  # noqa: F401
import gate_b_frames as GBF
from armature_core.errors import ArmatureError, GateBBatching, GateRRoundTrip


def write_frames(d, n, mutate=None):
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        a = np.zeros((4, 6, 3), dtype=np.uint8)
        a[i % 4, i % 6] = (200, 30, 40)
        if mutate:
            a = mutate(i, a)
        Image.fromarray(a).save(d / f"{i:05d}.png")
    return d


def test_a_faithful_bridge_passes_on_every_frame(tmp_path):
    src = write_frames(tmp_path / "sticks", 12)
    got = write_frames(tmp_path / "batch", 12)
    ev = GBF.frame_paths(src), GBF.frame_paths(got)
    assert len(ev[0]) == len(ev[1]) == 12


def test_the_contact_strip_beside_the_frames_is_not_counted_as_one(tmp_path):
    """Measured on this tool's own first run, 2026-08-12: `render_pose_sticks` writes a
    `strip_every8.png` next to its NNNNN.png frames, so a naive `*.png` glob counted 82
    frames where 81 were drawn — and the count andon then fired with a message about
    batching that had nothing to do with what was wrong."""
    d = write_frames(tmp_path / "sticks", 5)
    Image.fromarray(np.zeros((4, 30, 3), dtype=np.uint8)).save(d / "strip_every8.png")
    got = [os.path.basename(p) for p in GBF.frame_paths(d)]
    assert got == ["00000.png", "00001.png", "00002.png", "00003.png", "00004.png"]


def test_frames_are_ordered_by_index_not_by_string(tmp_path):
    """`00009` before `00010` is true either way; a directory that ever drops the padding
    is where a string sort silently reorders the performance."""
    d = tmp_path / "sticks"
    d.mkdir()
    for name in ("9.png", "10.png", "2.png"):
        Image.fromarray(np.zeros((2, 2, 3), dtype=np.uint8)).save(d / name)
    assert [os.path.basename(p) for p in GBF.frame_paths(d)] == \
        ["2.png", "9.png", "10.png"]


def test_a_directory_with_no_numbered_frames_raises_rather_than_passing_empty(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    Image.fromarray(np.zeros((2, 2, 3), dtype=np.uint8)).save(d / "strip_every8.png")
    with pytest.raises(ArmatureError) as exc:
        GBF.frame_paths(d)
    assert "proves nothing" in str(exc.value)


def test_a_short_pack_is_caught_by_the_count_andon(tmp_path):
    """The conditioning node pads a short pose video by repeating its last frame, silently."""
    from armature_core import gates
    with pytest.raises(GateBBatching):
        gates.gate_b_batching(81, 80)


def test_a_single_changed_pixel_anywhere_in_the_pack_is_caught(tmp_path):
    """Not a sample — every frame. A pack that recoloured one frame arrives as a
    well-formed run whose driving signal is not the one the report quotes."""
    from armature_core import gates
    src = [np.zeros((4, 6, 3), dtype=np.uint8) for _ in range(20)]
    got = [a.copy() for a in src]
    got[13][2, 3, 2] = 1
    with pytest.raises(GateRRoundTrip) as exc:
        gates.gate_r_round_trip(src, got)
    assert "13" in str(exc.value)


def test_the_distinct_frame_diagnostic_counts_pixels_not_names(tmp_path):
    d = write_frames(tmp_path / "out", 6, mutate=lambda i, a: a * 0)
    assert GBF.distinct_count(GBF.frame_paths(d)) == 1
    d2 = write_frames(tmp_path / "out2", 6)
    assert GBF.distinct_count(GBF.frame_paths(d2)) == 6


def test_the_frame_delta_diagnostic_is_zero_on_a_still_sequence(tmp_path):
    d = write_frames(tmp_path / "still", 4, mutate=lambda i, a: a * 0)
    assert GBF.mean_abs_frame_deltas(GBF.frame_paths(d)) == [0.0, 0.0, 0.0]
