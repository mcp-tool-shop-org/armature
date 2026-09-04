"""The lift sheet's claims, after E09 §26.

The sheet's docstring said the lifted column was rendered "on the identical camera"
while the run it served compared a frontal generated donor against the banked
three-quarter render (az 225 / elev 6). An instrument's labels derive from its inputs;
identity is never claimed for free — these tests are shaped to catch the wrong claim,
as the E09 calibration ruling asked.
"""

import json
import sys

from PIL import Image

from conftest import TOOLS  # noqa: F401
import make_lift_sheet as L


def test_the_identical_camera_claim_is_gone_from_the_tool():
    assert "identical camera" not in (L.__doc__ or "")


def test_default_labels_derive_from_the_frames_actually_loaded():
    """The first heading used to read "source render 1920x1080" as a literal, whatever
    the frames actually were."""
    assert L.default_labels((640, 360))[0] == "source 640x360"
    assert L.default_labels((1920, 1080))[0] == "source 1920x1080"
    assert "1920x1080" not in L.default_labels((832, 480))[0]


def test_the_camera_line_never_claims_identity_unprompted():
    line = L.camera_note()
    assert "identical" not in line
    assert line.count(L.MISSING) == 2
    told = L.camera_note("frontal (generated donor)", "az 225 elev 6 (banked)")
    assert "frontal (generated donor)" in told
    assert "az 225 elev 6 (banked)" in told


def test_end_to_end_the_sidecar_records_what_the_cameras_were_or_says_so(
        tmp_path, monkeypatch):
    """A run that states only the lifted camera gets NOT RECORDED for the source —
    never silence, never an implied match."""
    src = tmp_path / "src"
    lif = tmp_path / "lif"
    src.mkdir()
    lif.mkdir()
    base = Image.new("RGB", (64, 48), (10, 10, 12))
    for d in (src, lif):
        for n in ("000.png", "001.png"):
            im = base.copy()
            im.paste(Image.new("RGB", (12, 20), (200, 180, 60)), (26, 14))
            im.save(d / n)
    base.save(lif / "empty_plate.png")
    det = {"rows": [{"fired": False, "image": [], "visibility": []} for _ in range(2)]}
    (tmp_path / "det.json").write_text(json.dumps(det), encoding="utf-8")
    out = tmp_path / "sheet.png"

    monkeypatch.setattr(sys, "argv", [
        "make_lift_sheet.py", f"--source={src}", f"--detection={tmp_path / 'det.json'}",
        f"--lifted={lif}", f"--out={out}", "--frames=0,1", "--tile-h=60",
        "--source-uncropped", "--lifted-camera=az 225 elev 6",
    ])
    L.main()

    assert out.exists()
    side = json.loads((tmp_path / "sheet.json").read_text(encoding="utf-8"))
    assert side["lifted_camera"] == "az 225 elev 6"
    assert side["source_camera"] == L.MISSING


# =============================================================== the pairing, made visible
#
# Wave 6, F-b7e82665. THE INVARIANT WITH NO FIXTURE: the source frame, the detection row
# and the lifted frame shown in sheet row k are all frame k — paired by frame NUMBER, not
# by position in three independently `sorted(os.listdir(...))` listings that
# `make_lift_sheet.main` indexes with the same `i`.
#
# The fixture above could not observe any of it, three ways at once: both directories used
# the same two names (000.png, 001.png), every tile was the same pasted rectangle on the
# same base, and the detection rows carried no `frame` key. A lifted directory numbered
# from 1 would put lifted 001 beside source 000 under the label `frame 000`, the sheet
# would exit 0 with MAKE_LIFT_SHEET_OK, and the sidecar records `frames: idx` and the three
# directory paths — never the resolved per-column filenames — so the mis-pairing would
# leave no trace on the artifact the Director is asked to read the lift result off.
#
# The fixtures below fix all three: distinct directory numbering, a distinct colour per
# frame per column, and `frame` keys on the detection rows.
#
# The sibling fix to carry is `measure_lift.gate_pairing` / `measure_lift.PairingGate`
# (wave 3): the frame number is read from the file NAME, an unnumbered or disagreeing
# population raises, and the passing verdict is written down. `make_lift_sheet` is the
# instruments-measure half of this seam; three of the tests below are RED until it lands.

import os

import pytest

import measure_lift as ML


PLATE = (10, 10, 12)
#: A distinct colour per frame per column. Distinctness is the whole point: with one
#: colour everywhere, a row that pairs source 000 with lifted 001 is pixel-identical to a
#: row that pairs correctly.
SRC_COLOURS = {0: (200, 30, 30), 1: (30, 200, 30), 2: (30, 200, 200)}
LIF_COLOURS = {0: (30, 30, 200), 1: (200, 200, 30), 2: (200, 30, 200)}


def _numbered_clip(d, colours, frames, plate=False):
    """A frame directory whose file NAMES carry the frame numbers, one colour each."""
    d.mkdir(parents=True, exist_ok=True)
    base = Image.new("RGB", (64, 48), PLATE)
    for n in frames:
        im = base.copy()
        im.paste(Image.new("RGB", (24, 24), colours[n]), (20, 12))
        im.save(d / f"{n:03d}.png")
    if plate:
        base.save(d / "empty_plate.png")
    return d


def _detection(path, frames):
    """Detection rows that say WHICH frame each one describes."""
    rows = [{"frame": n, "fired": False, "image": [], "visibility": []} for n in frames]
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    return path


def _run(monkeypatch, src, lif, det, out, frames):
    monkeypatch.setattr(sys, "argv", [
        "make_lift_sheet.py", f"--source={src}", f"--detection={det}",
        f"--lifted={lif}", f"--out={out}", f"--frames={frames}", "--tile-h=60",
        "--source-uncropped", "--lifted-camera=az 225 elev 6",
    ])
    return L.main()


def _colours(path):
    return set(Image.open(path).convert("RGB").getdata())


@pytest.mark.parametrize("frame", [0, 1])
def test_the_sheet_shows_the_lifted_frame_that_belongs_to_the_row(
        tmp_path, monkeypatch, frame):
    """The fixture the old one could not be: one row, and the lifted colour on the sheet
    identifies WHICH lifted frame was pasted.

    What this looks like if the tool is wrong in the way the finding names: the sheet
    labelled `frame 000` carries lifted frame 1's colour, and nothing else on the artifact
    or in the sidecar says so.
    """
    src = _numbered_clip(tmp_path / "src", SRC_COLOURS, [0, 1])
    lif = _numbered_clip(tmp_path / "lif", LIF_COLOURS, [0, 1], plate=True)
    det = _detection(tmp_path / "det.json", [0, 1])
    out = tmp_path / "sheet.png"
    _run(monkeypatch, src, lif, det, out, str(frame))

    on_sheet = _colours(out)
    other = 1 - frame
    assert SRC_COLOURS[frame] in on_sheet, "the source column is not this row's frame"
    assert LIF_COLOURS[frame] in on_sheet, (
        f"row for frame {frame} does not carry lifted frame {frame}")
    assert LIF_COLOURS[other] not in on_sheet, (
        f"row for frame {frame} carries lifted frame {other}; the columns are paired by "
        f"position in two independent listings, not by frame number")


def test_a_lifted_directory_numbered_from_one_is_refused(tmp_path, monkeypatch):
    """The measured consequence, as a fixture: lifted numbered 001/002 against source
    000/001. Indexing both listings with the same `i` puts lifted 001 beside source 000
    under the label `frame 000`.

    The refusal carried from `measure_lift.gate_pairing`: the frame number is read from the
    file name, and a population that does not agree raises `PairingGate` rather than
    producing a sheet nobody can tell is wrong.
    """
    src = _numbered_clip(tmp_path / "src", SRC_COLOURS, [0, 1])
    lif = _numbered_clip(tmp_path / "lif", LIF_COLOURS, [1, 2], plate=True)
    det = _detection(tmp_path / "det.json", [0, 1])
    out = tmp_path / "sheet.png"
    with pytest.raises(ML.PairingGate) as exc:
        _run(monkeypatch, src, lif, det, out, "0,1")
    assert exc.value.evidence["gate"] == "PAIRING"
    assert not out.exists(), "a refused sheet must leave no artifact to be read as a result"


def test_detection_rows_that_describe_other_frames_are_refused(tmp_path, monkeypatch):
    """The third column has the same disease and no directory to read it from: the rows
    are indexed by the same `i`, so a detection file whose rows describe frames 1 and 2
    overlays frame 1's landmarks on frame 0's image.
    """
    src = _numbered_clip(tmp_path / "src", SRC_COLOURS, [0, 1])
    lif = _numbered_clip(tmp_path / "lif", LIF_COLOURS, [0, 1], plate=True)
    det = _detection(tmp_path / "det.json", [1, 2])
    out = tmp_path / "sheet.png"
    with pytest.raises(ML.PairingGate) as exc:
        _run(monkeypatch, src, lif, det, out, "0,1")
    assert exc.value.evidence["gate"] == "PAIRING"
    assert not out.exists()


def test_the_sidecar_records_the_file_each_column_actually_loaded(tmp_path, monkeypatch):
    """`frames: idx` records what was REQUESTED. The three resolved filenames are what a
    later reader needs to check the pairing, and they were never written down.
    """
    src = _numbered_clip(tmp_path / "src", SRC_COLOURS, [0, 1])
    lif = _numbered_clip(tmp_path / "lif", LIF_COLOURS, [0, 1], plate=True)
    det = _detection(tmp_path / "det.json", [0, 1])
    out = tmp_path / "sheet.png"
    _run(monkeypatch, src, lif, det, out, "0,1")

    side = json.loads((tmp_path / "sheet.json").read_text(encoding="utf-8"))
    rows = side.get("rows")
    assert isinstance(rows, list) and len(rows) == 2, (
        "the sidecar records no per-row resolution; a mis-pairing leaves no trace")
    for n, row in zip([0, 1], rows):
        assert row["frame"] == n
        assert os.path.splitext(os.path.basename(row["source"]))[0] == f"{n:03d}"
        assert os.path.splitext(os.path.basename(row["lifted"]))[0] == f"{n:03d}"
        assert row["detection_row"] == n
