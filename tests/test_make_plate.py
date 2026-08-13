"""Tests for the plate — the picture of the world the performer is composited over.

The failure this tool exists to prevent is silent by construction: a padded plate is a
well-formed PNG of exactly the right size that opens, uploads and generates without a
single error, and the bands it puts into the conditioning image only show up as washed
edges in the finished clip. So the fixtures below check the pixels at the border, not the
dimensions — the dimensions are right in both the correct and the wrong implementation.

Read back with Pillow rather than with cv2, which is what wrote them: a writer checked only
by its own reader has been checked against nothing (EXTERNAL_VERIFIER).
"""

import json
import os

import numpy as np
import pytest
from PIL import Image

import make_plate
from armature_core.errors import ArmatureError


def _write(path, arr):
    Image.fromarray(arr.astype(np.uint8), mode="RGB").save(path)
    return str(path)


def _gradient(w, h):
    """A source with no two rows or columns alike, so any crop or pad is locatable.

    uint8 deliberately: this is what `cv2.imread` hands the tool, and cv2's resize refuses
    int64 outright — a fixture in a wider dtype would exercise a path the tool never takes.
    """
    ys, xs = np.mgrid[0:h, 0:w]
    return np.stack([(xs * 251 // max(1, w - 1)) % 256,
                     (ys * 241 // max(1, h - 1)) % 256,
                     ((xs + ys) * 199 // max(1, w + h - 2)) % 256],
                    axis=-1).astype(np.uint8)


# ------------------------------------------------------------------- resolve_source


def test_exactly_one_source_or_it_halts(tmp_path):
    """Both is a caller who has not decided; neither is a caller who forgot. Defaulting
    either way would pick a plate on the caller's behalf, which is the one decision this
    experiment reserves for the Director."""
    src = _write(tmp_path / "a.png", _gradient(20, 10))
    frames = tmp_path / "f"
    frames.mkdir()
    _write(frames / "00003.png", _gradient(20, 10))

    with pytest.raises(ArmatureError):
        make_plate.resolve_source(None, None, None)
    with pytest.raises(ArmatureError):
        make_plate.resolve_source(src, str(frames), 3)


def test_a_frame_index_that_does_not_exist_halts_rather_than_choosing_a_neighbour(tmp_path):
    """A plate lifted from a missing frame would otherwise become whichever frame sorted
    nearest, and the provenance would record the index nobody rendered."""
    frames = tmp_path / "f"
    frames.mkdir()
    for i in (0, 8, 16):
        _write(frames / f"{i:05d}.png", _gradient(20, 10))

    path, origin = make_plate.resolve_source(None, str(frames), 8)
    assert origin["frame_index"] == 8 and origin["n_frames"] == 3
    assert os.path.basename(path) == "00008.png"

    with pytest.raises(ArmatureError) as exc:
        make_plate.resolve_source(None, str(frames), 9)
    assert "0..16" in str(exc.value)


def test_frames_without_an_index_halts(tmp_path):
    frames = tmp_path / "f"
    frames.mkdir()
    _write(frames / "00000.png", _gradient(20, 10))
    with pytest.raises(ArmatureError):
        make_plate.resolve_source(None, str(frames), None)


def test_a_missing_file_halts(tmp_path):
    with pytest.raises(ArmatureError):
        make_plate.resolve_source(str(tmp_path / "nope.png"), None, None)


# --------------------------------------------------------------------------- cover


def test_the_output_is_exactly_the_frame_and_none_of_it_is_invented():
    """THE fixture. A contain-fit produces a file of exactly the same dimensions, so size
    proves nothing — what separates the two is whether the border pixels came from the
    source. The source here is a gradient with a bright saturated frame painted on it; a
    letterbox would put flat bands outside that frame, so the corners would be the pad
    colour rather than the source's own edge.
    """
    src = _gradient(832, 480)
    src[:4, :] = (255, 0, 255)          # a magenta border the fit must carry to the edge
    src[-4:, :] = (255, 0, 255)
    src[:, :4] = (255, 0, 255)
    src[:, -4:] = (255, 0, 255)

    out, geom = make_plate.cover(src[:, :, ::-1], 1024, 576)      # cv2 arrays are BGR
    out = out[:, :, ::-1]

    assert out.shape == (576, 1024, 3)
    assert geom["pads"] is False
    # Left and right edges survive a cover fit of this aspect (only rows are cropped).
    for name, strip in (("left", out[:, 0]), ("right", out[:, -1])):
        assert strip.max() > 200 and strip[:, 1].mean() < 90, (
            f"the {name} edge is not the source's magenta border — the plate was padded")


def test_a_row_crop_takes_it_off_both_ends(tmp_path):
    """Centred, so the plate keeps its middle. An anchored crop would silently shift every
    horizon in every plate toward one edge of the frame."""
    src = _gradient(1000, 1000)
    _, geom = make_plate.cover(src, 1024, 576)
    x0, y0, x1, y1 = geom["crop_box"]
    nw, nh = geom["resized_size"]
    assert y0 == (nh - 576) // 2
    assert abs((nh - y1) - y0) <= 1


def test_the_geometry_reported_is_the_geometry_applied():
    """A record that describes a different transform from the one the pixels went through
    is worse than no record: the next reader reproduces the description and gets a
    different file."""
    src = _gradient(640, 360)
    out, geom = make_plate.cover(src, 1024, 576)
    assert list(out.shape[1::-1]) == geom["target_size"]
    assert geom["interpolation"] == "INTER_CUBIC"
    out, geom = make_plate.cover(_gradient(4096, 2304), 1024, 576)
    assert geom["interpolation"] == "INTER_AREA"


# ---------------------------------------------------------------------------- main


def test_end_to_end_writes_a_plate_and_a_record_that_names_its_source(tmp_path):
    frames = tmp_path / "lossless"
    frames.mkdir()
    for i in range(0, 65):
        _write(frames / f"{i:05d}.png", _gradient(832, 480) + i % 7)
    out = tmp_path / "plate"

    make_plate.main([f"--frames={frames}", "--index=32", f"--out={out}",
                     "--width=1024", "--height=576", "--why=the picked still"])

    plate = Image.open(out / "plate.png")
    assert plate.size == (1024, 576)

    rec = json.loads((out / "plate_provenance.json").read_text(encoding="utf-8"))
    assert rec["source"]["frame_index"] == 32
    assert rec["source"]["size"] == [832, 480]
    assert rec["derived"]["size"] == [1024, 576]
    assert rec["transform"]["pads"] is False
    assert rec["why"] == "the picked still"
    assert len(rec["source"]["sha256"]) == 64 and len(rec["derived"]["sha256"]) == 64
    assert rec["source"]["sha256"] != rec["derived"]["sha256"]


def test_a_plate_with_no_reason_never_gets_written(tmp_path):
    """'Deliberate and RECORDED' is two requirements, and the second one is checked before
    anything reaches disk — a half-written plate directory is how a reason gets supplied
    retroactively."""
    src = _write(tmp_path / "a.png", _gradient(832, 480))
    out = tmp_path / "plate"
    for missing in ([], ["--why="], ["--why=   "]):
        with pytest.raises(ArmatureError):
            make_plate.main([f"--src={src}", f"--out={out}",
                             "--width=1024", "--height=576"] + missing)
    assert not out.exists(), "the output directory was created before the reason was checked"


def test_the_named_anchors_resolve_and_a_bad_one_halts():
    assert make_plate.parse_anchor("bottom") == (0.5, 1.0)
    assert make_plate.parse_anchor("top") == (0.5, 0.0)
    assert make_plate.parse_anchor("0.25,0.75") == (0.25, 0.75)
    for bad in ("middle", "0.5", "a,b", ""):
        with pytest.raises(ArmatureError):
            make_plate.parse_anchor(bad)


def test_the_anchor_actually_moves_the_pixels_not_only_the_record(tmp_path):
    """A recorded choice that does not reach the file is worse than no record. The source
    below has a distinct stripe near its top; a top anchor keeps it and a bottom anchor
    does not, and the plate's own pixels are what says which happened."""
    src = _gradient(1248, 832)
    src[40:80, :] = (0, 255, 0)                      # a marker only the top crop keeps
    path = _write(tmp_path / "s.png", src)

    def band_of(anchor):
        out = tmp_path / anchor
        make_plate.main([f"--src={path}", f"--out={out}", "--width=1024", "--height=576",
                         f"--anchor={anchor}", "--why=x", "--visible-rows=0,182"])
        return np.asarray(Image.open(out / "plate.png"))[0:182]

    assert (band_of("top")[:, :, 1] > 200).any(), "the top anchor lost the marker"
    assert not (band_of("bottom")[:, :, 1] > 200).any(), (
        "the bottom anchor kept a marker that is 40 source rows from the top")


def test_the_band_the_record_claims_is_the_band_the_plate_has(tmp_path):
    """`band_carries` is a sentence about pixels; this checks the sentence is pointed at the
    right ones. The recorded source rows must be the rows that actually landed in the
    band."""
    src = _write(tmp_path / "s.png", _gradient(1248, 832))
    out = tmp_path / "p"
    make_plate.main([f"--src={src}", f"--out={out}", "--width=1024", "--height=576",
                     "--anchor=bottom", "--why=x", "--visible-rows=0,182",
                     "--band-carries=the crowd's faces and hands"])
    rec = json.loads((out / "plate_provenance.json").read_text(encoding="utf-8"))
    assert rec["anchor"]["fractions"] == [0.5, 1.0]
    assert rec["visible_band"]["target_rows"] == [0, 182]
    assert rec["visible_band"]["source_rows"][0] == pytest.approx(130.4, abs=0.1)
    assert rec["visible_band"]["carries"] == "the crowd's faces and hands"
    assert rec["transform"]["crop_offset"][1] == 107


def test_a_band_the_target_frame_does_not_contain_halts(tmp_path):
    src = _write(tmp_path / "s.png", _gradient(1248, 832))
    for bad in ("0,900", "300,100"):
        with pytest.raises(ArmatureError):
            make_plate.main([f"--src={src}", f"--out={tmp_path / 'b'}", "--width=1024",
                            "--height=576", "--why=x", f"--visible-rows={bad}"])


def test_an_unstated_band_records_not_recorded_rather_than_a_guess(tmp_path):
    src = _write(tmp_path / "s.png", _gradient(1248, 832))
    out = tmp_path / "p"
    make_plate.main([f"--src={src}", f"--out={out}", "--width=1024", "--height=576",
                     "--anchor=bottom", "--why=x", "--visible-rows=0,182"])
    rec = json.loads((out / "plate_provenance.json").read_text(encoding="utf-8"))
    assert rec["visible_band"]["carries"] == "NOT RECORDED"


def test_the_source_file_is_never_written_to(tmp_path):
    """The clip this plate came out of is an experiment's record. A tool that edited it in
    place would corrupt the evidence it was derived from."""
    import hashlib

    src = _write(tmp_path / "a.png", _gradient(900, 500))
    before = hashlib.sha256(open(src, "rb").read()).hexdigest()
    make_plate.main([f"--src={src}", f"--out={tmp_path / 'p'}",
                     "--width=1024", "--height=576", "--why=x"])
    assert hashlib.sha256(open(src, "rb").read()).hexdigest() == before
