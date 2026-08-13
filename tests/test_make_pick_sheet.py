"""Tests for Gate PLATE's instrument.

The sheet decides nothing, so the thing worth testing is not its layout — it is whether
every number printed on it is derived from the frames it was pointed at. A pick sheet that
printed a stale literal, or that mapped the visible band into the wrong coordinate system,
would put the Director's eye on the wrong part of the picture and no downstream check would
ever notice: the sheet renders, the JSON validates, the plate gets picked.
"""

import json

import numpy as np
import pytest
from PIL import Image

import make_pick_sheet as MPS
from armature_core.errors import ArmatureError


def _frame(path, w=832, h=480, seed=0, blur=False):
    rng = np.random.default_rng(seed)
    a = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    if blur:                                  # a low-frequency field: sharpness near zero
        a[:] = np.linspace(0, 255, w, dtype=np.uint8)[None, :, None]
    Image.fromarray(a, mode="RGB").save(path)
    return str(path)


@pytest.fixture
def clip(tmp_path):
    d = tmp_path / "lossless"
    d.mkdir()
    for i in range(6):
        _frame(d / f"{i:05d}.png", seed=i, blur=(i == 3))
    return str(d)


# ------------------------------------------------------------------ derived numbers


def test_sharpness_separates_a_detailed_frame_from_a_flat_one(tmp_path):
    """The measure has to actually measure something. A gradient has almost no second
    difference; noise has a great deal."""
    noisy = np.asarray(Image.open(_frame(tmp_path / "n.png", seed=1)).convert("L"))
    flat = np.asarray(Image.open(_frame(tmp_path / "f.png", seed=1, blur=True)).convert("L"))
    assert MPS.sharpness(noisy) > MPS.sharpness(flat) * 100


def test_sharpness_scales_with_contrast_which_is_why_it_is_printed_beside_luma():
    """The caveat on the sheet, made executable. Halving contrast quarters this number with
    nothing going out of focus — so a sheet that ranked a darkening clip by sharpness alone
    would call its dark half blurry. This test exists so nobody later 'fixes' the sheet by
    sorting on it."""
    rng = np.random.default_rng(7)
    a = rng.integers(0, 256, size=(64, 64), dtype=np.uint8)
    dim = (a // 2).astype(np.uint8)
    assert MPS.sharpness(dim) == pytest.approx(MPS.sharpness(a) / 4.0, rel=0.05)


def test_the_first_frame_has_no_motion_number_rather_than_a_zero(clip):
    """A zero would read as the stillest frame in the run — the exact opposite of 'unknown',
    and it would be the frame most likely to be picked."""
    cands = MPS.measure(clip, [0, 1])
    assert cands[0]["motion"] is None and cands[0]["motion_reference"] is None
    assert cands[1]["motion"] is not None and cands[1]["motion_reference"] == 0


def test_motion_is_measured_against_the_previous_frame_not_the_previous_candidate(clip):
    """f24's motion is f24-vs-f23, whether or not f23 is on the sheet. Measuring against the
    previous CANDIDATE would report the distance between two frames a dozen apart and call
    it motion blur."""
    cands = MPS.measure(clip, [1, 5])
    assert [c["motion_reference"] for c in cands] == [0, 4]


def test_a_candidate_that_does_not_exist_halts(clip):
    with pytest.raises(ArmatureError) as exc:
        MPS.measure(clip, [2, 99])
    assert "0..5" in str(exc.value)


# ------------------------------------------------------------------- the band map


def test_the_visible_band_maps_into_the_candidates_own_pixels():
    """THE arithmetic the sheet's blue rectangle is drawn from, on the measured case: E11
    wave 1's 832x480 into E12's 1024x576, with w3's transparent region rows 0..182.

    Getting this wrong is silent — the band still draws, just over the wrong part of the
    picture, and the Director judges bar content that will not survive.
    """
    from armature_core import startframe as SF

    geom = SF.cover_fit(832, 480, 1024, 576)
    lo, hi = MPS.source_rows_of((0, 182), geom)
    assert lo == pytest.approx(7 / (1024 / 832), abs=1e-6)
    assert hi == pytest.approx(189 / (1024 / 832), abs=1e-6)
    assert 5.0 < lo < 6.5 and 152.0 < hi < 154.0


def test_a_band_outside_the_target_frame_halts(tmp_path, clip):
    for bad in ("0,900", "300,100", "-5,100"):
        with pytest.raises((ArmatureError, SystemExit)):
            MPS.main([f"--frames={clip}", "--at=1,2", "--target=1024x576",
                      f"--visible-rows={bad}", f"--out={tmp_path / 's.png'}"])


def test_mixed_size_candidates_halt_rather_than_drawing_wrong_bands(tmp_path):
    """One cover fit describes one source size. Two sizes on one sheet means the red and
    blue rectangles are right on some tiles and wrong on others, with nothing to show
    which.

    The halt has to come from the size check, not from numpy failing to broadcast two
    arrays deep inside the motion measurement — which is what it did until this fixture
    was run. A `ValueError: operands could not be broadcast` names neither the frames nor
    the reason, and the reader's next move is to go read the tool.
    """
    d = tmp_path / "mixed"
    d.mkdir()
    _frame(d / "00000.png", 832, 480, seed=0)
    _frame(d / "00001.png", 640, 360, seed=1)
    with pytest.raises(ArmatureError) as exc:
        MPS.main([f"--frames={d}", "--at=0,1", "--target=1024x576",
                  "--visible-rows=0,182", f"--out={tmp_path / 's.png'}"])
    assert "not all one size" in str(exc.value)
    assert "broadcast" not in str(exc.value)


def test_the_motion_measure_refuses_mismatched_frames_in_its_own_right(tmp_path):
    """The size guard above is the caller's; this is the measurement's own. A helper that
    is correct only because someone else checked first is one refactor from silent."""
    a = np.zeros((10, 10), dtype=np.uint8)
    b = np.zeros((8, 12), dtype=np.uint8)
    with pytest.raises(ArmatureError) as exc:
        MPS.motion(a, b)
    assert "not a motion measurement" in str(exc.value)


# ------------------------------------------------------------------------ the sheet


def test_end_to_end_writes_a_sheet_and_a_record_of_what_it_drew(tmp_path, clip):
    out = tmp_path / "sheets" / "pick.png"
    MPS.main([f"--frames={clip}", "--at=1,2,4", "--target=1024x576",
              "--visible-rows=0,182", f"--out={out}"])

    assert Image.open(out).size[0] > 400
    rec = json.loads((out.parent / "pick.json").read_text(encoding="utf-8"))
    assert [c["index"] for c in rec["candidates"]] == [1, 2, 4]
    assert rec["source_size"] == [832, 480] and rec["target_size"] == [1024, 576]
    assert rec["cover_fit"]["pads"] is False
    assert rec["band_fraction_of_target"] == pytest.approx(182 / 576)
    assert "DIAGNOSTIC" in rec["status"]


def test_every_provenance_line_comes_from_the_inputs(tmp_path, clip):
    """No literals: point the tool at a different frame size and every geometry line has to
    move. A sheet with a baked number is a sheet that will lie the first time it is reused
    — which is why this tool exists instead of a flag on an older one."""
    out = tmp_path / "a.png"
    MPS.main([f"--frames={clip}", "--at=1,2", "--target=1024x576",
              "--visible-rows=0,182", f"--out={out}"])
    a = json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))

    d2 = tmp_path / "small"
    d2.mkdir()
    for i in range(3):
        _frame(d2 / f"{i:05d}.png", 640, 360, seed=i)
    out2 = tmp_path / "b.png"
    MPS.main([f"--frames={d2}", "--at=1,2", "--target=1024x576",
              "--visible-rows=0,182", f"--out={out2}"])
    b = json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))

    assert a["cover_fit"]["scale"] != b["cover_fit"]["scale"]
    assert a["visible_rows_source"] != b["visible_rows_source"]
    assert a["source_size"] != b["source_size"]


def test_the_source_run_is_read_from_a_record_not_typed_in(tmp_path, clip):
    """The fixture for a mistake this session actually made: a prompt_id typed into a title
    by hand, on the sheet a spending decision gets made from, naming a generation that does
    not exist. Read it or print NOT RECORDED — those are the only two options."""
    rec_path = tmp_path / "payload.json"
    rec_path.write_text(json.dumps(
        {"prompt_id": "ecedbe1c-8658-4119-8151-cfa693db1c50", "seed": 2026081231}),
        encoding="utf-8")

    out = tmp_path / "with.png"
    MPS.main([f"--frames={clip}", "--at=1,2", "--target=1024x576", "--visible-rows=0,182",
              f"--source-record={rec_path}", f"--out={out}"])
    got = json.loads((tmp_path / "with.json").read_text(encoding="utf-8"))["source_run"]
    assert got["prompt_id"] == "ecedbe1c-8658-4119-8151-cfa693db1c50"
    assert got["seed"] == 2026081231
    assert any("ecedbe1c" in ln for ln in MPS.provenance_lines(
        json.loads((tmp_path / "with.json").read_text(encoding="utf-8"))))


def test_no_source_record_prints_not_recorded_rather_than_a_plausible_id(tmp_path, clip):
    out = tmp_path / "without.png"
    MPS.main([f"--frames={clip}", "--at=1,2", "--target=1024x576",
              "--visible-rows=0,182", f"--out={out}"])
    rec = json.loads((tmp_path / "without.json").read_text(encoding="utf-8"))
    assert rec["source_run"]["prompt_id"] == MPS.MISSING
    assert any(MPS.MISSING in ln for ln in MPS.provenance_lines(rec))


def test_the_missing_motion_number_reaches_the_sheets_label_as_not_recorded(tmp_path, clip):
    """The convention `make_startframe_sheet` was split out to enforce, exercised on the one
    value this sheet can genuinely lack."""
    lines = MPS.provenance_lines({
        "frames_dir": "d", "n_frames": 3, "source_size": [832, 480],
        "cover_fit": {"target_size": [1024, 576], "scale": 1.2,
                      "resized_size": [1024, 591], "crop_box": [0, 7, 1024, 583],
                      "dropped_px_resized": {"x": 0, "y": 15},
                      "kept_fraction_of_source_area": 0.97},
        "visible_rows_target": [0, 182], "visible_rows_source": [5.7, 153.6],
        "band_fraction_of_target": 0.316})
    assert any("1024x576" in ln for ln in lines)
    assert MPS.MISSING == "NOT RECORDED"
