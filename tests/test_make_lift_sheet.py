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
