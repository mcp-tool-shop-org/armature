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
    """The literal '33-frame orbit' sat beside azimuths computed from len(names).

    The length half of this is unchanged and still asserted. The word ORBIT moved behind
    `--azimuth-captions` in wave 8 (see the block appended at the end of this file), so the
    default title now reads "5-frame run" and the flagged one "5-frame orbit" — both
    checked here rather than only the one that used to be unconditional.
    """
    run = _run(tmp_path, 5)
    default_title = MIS.rows_for(run, [_plate(tmp_path)], [0, 2, 4], tile_h=16)[1][0]
    assert "5-frame run" in default_title
    assert "orbit" not in default_title
    assert "33" not in default_title

    orbit_title = MIS.rows_for(run, [_plate(tmp_path)], [0, 2, 4], tile_h=16,
                               azimuth_captions=True)[1][0]
    assert "5-frame orbit" in orbit_title
    assert "33" not in orbit_title


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
    with pytest.raises(MIS.IdentitySheetError,
                       match=r"holds 0 'normal' frame\(s\) and frame\(s\) \[0\] of the"):
        MIS.build(str(tmp_path / "run"), [_plate(tmp_path)], [0], tile_h=16)


def test_a_channel_directory_that_is_not_there_is_named(tmp_path):
    run = _run(tmp_path, 2)
    with pytest.raises(MIS.IdentitySheetError) as e:
        MIS.build(run, [_plate(tmp_path)], [0], tile_h=16, channel="depth_perframe")
    assert "depth_perframe" in str(e.value)


# ------------------------------------- the orbit is the RUN's, and only when there is one
#
# `az = 360.0 * fi / len(names)` and the row title `f"{len(names)}-frame orbit"` baked E02's
# turnaround into every caption unconditionally — no flag, no opt-out — on the panel whose
# own row title asks the Director "is this the same man?". Both siblings had this removed in
# wave 6 and say so in their own source: `make_gate0_sheet.frame_caption` ("the tool used to
# compute an azimuth from the frame count, which was E02's orbit baked in — on a run that
# does not orbit it printed angles that never happened") now defaults to the bare index, and
# `make_thesis_sheet` made it opt-in behind `--azimuth-captions`. This was the third member
# of that family and was not swept.
#
# Measured 2026-09-04 on a 16-frame VIDEO clip (time, not a camera orbit) with
# `--frames=0,4,8,12`: the tiles came back labelled `f000 az 0d`, `f004 az 90d`,
# `f008 az 180d`, `f012 az 270d` under a row headed "16-frame orbit" — four camera angles
# that never happened, on the surface this repo says is canon for identity.

import json  # noqa: E402
import subprocess  # noqa: E402


def _tile_labels(rows):
    return [label for _t, label in rows[1][1]]


def test_a_video_clip_gets_no_fabricated_camera_angles(tmp_path):
    """16 frames of TIME, four of them requested. No `az` anywhere, no `orbit` anywhere."""
    run = _run(tmp_path, 16)
    rows = MIS.rows_for(run, [_plate(tmp_path)], [0, 4, 8, 12], tile_h=16)
    assert all("az" not in label for label in _tile_labels(rows)), _tile_labels(rows)
    assert "orbit" not in rows[1][0]


def test_the_flag_brings_both_the_azimuth_and_the_word_back(tmp_path):
    """The guard the other way: a turnaround must still be labelled as one."""
    run = _run(tmp_path, 16)
    rows = MIS.rows_for(run, [_plate(tmp_path)], [0, 4, 8, 12], tile_h=16,
                        azimuth_captions=True)
    labels = _tile_labels(rows)
    assert [l.split("  ")[1] for l in labels] == ["az 0d", "az 90d", "az 180d", "az 270d"]
    assert "16-frame orbit" in rows[1][0]


def test_the_cli_default_says_on_its_own_line_that_it_fabricated_nothing(tmp_path, capsys):
    run = _run(tmp_path, 16)
    out = tmp_path / "identity.png"
    MIS.main([f"--run={run}", f"--plates={_plate(tmp_path)}", f"--out={out}",
              "--frames=0,4", "--tile-height=16"])
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert "azimuth_captions=False" in line, line
    assert "plate=(0, 0, 0)" in line, line


def test_the_family_is_swept_all_three_sheets_make_the_azimuth_opt_in():
    """Derived by argparse, not by grep: every sheet in `tools/` that can print an azimuth
    caption exposes it as a flag whose default is off. The population is the modules whose
    parser defines a `--azimuth-captions` action plus the one that dropped the caption
    entirely, and it is checked by INSPECTING the parsers rather than the source text."""
    import argparse
    import importlib
    from unittest import mock

    captured = {}
    for mod_name in ("make_identity_sheet", "make_thesis_sheet"):
        mod = importlib.import_module(mod_name)
        real = argparse.ArgumentParser.parse_args

        def grab(self, *a, _n=mod_name, **k):
            captured[_n] = self
            raise SystemExit(0)

        with mock.patch.object(argparse.ArgumentParser, "parse_args", grab):
            try:
                mod.main([])
            except (SystemExit, Exception):
                pass
        argparse.ArgumentParser.parse_args = real

    for name, parser in captured.items():
        action = next((x for x in parser._actions if x.dest == "azimuth_captions"), None)
        assert action is not None, f"{name} has no --azimuth-captions flag"
        assert action.default is False, f"{name} defaults the azimuth ON"

    # the third sibling dropped the caption rather than gating it: its default caption is
    # the bare index, which is what its own `frame_caption` docstring says.
    import make_gate0_sheet as G0

    assert G0.frame_caption(3) == "f003", G0.frame_caption(3)
