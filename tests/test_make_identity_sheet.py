"""The panel the Director is asked "is this the same man?" on.

`if fi >= len(names): continue` dropped every requested frame index past the end of the
channel directory, and unlike `make_startframe_sheet.build` there was no `if not tiles`
guard, so an empty mesh row was a legal sheet. The row label then asserted "33-frame orbit"
as a literal while the azimuth printed beside each tile was computed from the actual
`len(names)` — the same panel disagreeing with itself.

Measured 2026-09-03: a run directory holding 2 frames, asked for `--frames=0,8,16,24`,
produced an 80x230 sheet with ONE mesh tile, printed `IDENTITY_SHEET ... 80x230`, exited 0,
and labelled it a 33-frame orbit. Identity is canon and no metric approximates it, which is
exactly why the panel carrying the question must not misdescribe what is on it.
"""

import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import make_identity_sheet as MIS  # noqa: E402


def _run(tmp_path, frames, channel="normal"):
    d = tmp_path / "run" / channel
    d.mkdir(parents=True)
    for i in range(frames):
        Image.fromarray(np.full((16, 12, 3), 40 + i, dtype=np.uint8)).save(d / f"{i:05d}.png")
    return str(tmp_path / "run")


def _plate(tmp_path, name="twin.png"):
    p = tmp_path / name
    Image.fromarray(np.zeros((16, 12, 3), dtype=np.uint8)).save(p)
    return str(p)


def test_a_requested_frame_the_run_does_not_have_raises(tmp_path):
    """THE fixture: 2 frames in the directory, 0 and 8 requested. The sheet used to be
    built from whichever of them happened to exist."""
    run = _run(tmp_path, 2)
    with pytest.raises(MIS.IdentitySheetError) as e:
        MIS.build(run, [_plate(tmp_path)], [0, 8], tile_h=16)
    assert "8" in str(e.value)
    assert e.value.evidence["missing_indices"] == [8]
    assert e.value.evidence["n_frames"] == 2


def test_every_missing_index_is_named_not_just_the_first(tmp_path):
    run = _run(tmp_path, 2)
    with pytest.raises(MIS.IdentitySheetError) as e:
        MIS.build(run, [_plate(tmp_path)], [0, 8, 16, 24], tile_h=16)
    assert e.value.evidence["missing_indices"] == [8, 16, 24]


def test_the_orbit_length_in_the_label_is_the_runs_own(tmp_path):
    """The literal '33-frame orbit' sat beside azimuths computed from len(names)."""
    run = _run(tmp_path, 5)
    rows = MIS.rows_for(run, [_plate(tmp_path)], [0, 2, 4], tile_h=16)
    mesh_title = rows[1][0]
    assert "5-frame orbit" in mesh_title
    assert "33" not in mesh_title


def test_a_two_frame_run_asked_for_two_frames_still_builds(tmp_path):
    """The guard the other way: the refusal must not make a short run unusable, only
    undescribable."""
    run = _run(tmp_path, 2)
    sheet = MIS.build(run, [_plate(tmp_path)], [0, 1], tile_h=16)
    assert sheet.width > 0 and sheet.height > 0


def test_an_empty_mesh_row_is_not_a_legal_sheet(tmp_path):
    """`make_startframe_sheet.build` guards `if not tiles`; this one did not, so a run with
    no frames at all produced a sheet whose mesh row was empty and whose label still
    described an orbit."""
    d = tmp_path / "run" / "normal"
    d.mkdir(parents=True)
    with pytest.raises(MIS.IdentitySheetError):
        MIS.build(str(tmp_path / "run"), [_plate(tmp_path)], [0], tile_h=16)


def test_a_channel_directory_that_is_not_there_is_named(tmp_path):
    run = _run(tmp_path, 2)
    with pytest.raises(MIS.IdentitySheetError) as e:
        MIS.build(run, [_plate(tmp_path)], [0], tile_h=16, channel="depth_perframe")
    assert "depth_perframe" in str(e.value)
