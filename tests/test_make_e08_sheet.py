r"""The Gate 0 sheet's provenance panel: every line read from the run, or `NOT RECORDED`.

The panel carried a comment asserting "Every number below is READ from the run's own payload
record" and that the hardcoded-literal defect was "Corrected E10, 2026-08-12". It was not,
for five lines: `(Gate L: legal, 4n+1, <=81)` printed unconditionally; the control line named
`Wan convention @ 29d4a35d` and "rendered from the E09 A3 rig - no detector anywhere"; the
whole reference line was the literal `twin_r3_v0.png letterboxed 352x1024 -> 832x480`; and
the meters line printed `estimate_credits 0 (no paid API nodes)`.

Measured 2026-09-03: a sheet built from a synthetic record with `length: 50` (not 4n+1) and
no reference at all printed `E08_SHEET_OK`, and the panel still asserted Gate L legal and
named a reference letterbox that did not happen. `make_gate0_sheet` and
`make_startframe_sheet` both record this exact defect class as fixed in their own docstrings;
this file kept it while claiming otherwise. It is the repo's named "placeholder shaped like
evidence", on the surface the Director reads a verdict off.

Second finding in the same file: five `cv2.imread(...)` results went straight into `fit()`
with no None check, so an unreadable tile surfaced as
`AttributeError: 'NoneType' object has no attribute 'shape'` naming none of the five inputs —
while `--previz` defaulted to an absolute path inside a DIFFERENT working tree
(`E:\AI\armature-E09\...`), which is where that AttributeError would come from on any other
machine.

Assertions here are on the rendered provenance LINES, not on the PNG: the question is what
the panel says, and a pixel comparison would answer a different one.
"""

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import make_e08_sheet as M8  # noqa: E402


def _record(**over):
    rec = {
        "experiment": "E99",
        "resolution": [832, 480],
        "length": 50,                      # NOT of the form 4n+1
        "fps": 16,
        "seed": 4242,
        "models": {"unet": "u.safetensors", "clip": "c.safetensors", "vae": "v.safetensors"},
        "sampler": {"steps": 6, "cfg": 1.0, "sampler_name": "euler",
                    "scheduler": "simple", "shift": 5.0},
        "payload_sha256": "0" * 64,
    }
    rec.update(over)
    return rec


def _lines(rec, **kw):
    kw.setdefault("prompt_id", "abc-123")
    kw.setdefault("seeds_file", "specs/seeds.json")
    return M8.provenance_lines(rec, **kw)


def _find(lines, prefix):
    return next(line for line in lines if line.startswith(prefix))


# ------------------------------------------------------------------ the gate verdict


def test_a_record_with_no_gate_L_does_not_assert_gate_L_legality():
    """THE fixture. length 50 is not 4n+1 and the record carries no gate_L key at all."""
    lines = _lines(_record())
    blob = "\n".join(lines)
    assert "Gate L: legal" not in blob
    assert "4n+1" not in blob
    assert M8.MISSING in _find(lines, "Gate L")


def test_the_gate_L_verdict_is_the_records_own_when_it_has_one():
    lines = _lines(_record(length=81, gate_L={"verdict": "PASS - 81 is 4n+1, <= 81"}))
    assert "PASS - 81 is 4n+1" in _find(lines, "Gate L")


def test_the_frame_line_quotes_the_records_own_length():
    assert "832x480x50" in _find(_lines(_record()), "frame")


# ------------------------------------------------------------------- the control line


def test_a_record_with_no_pose_video_does_not_name_a_convention_or_a_rig():
    blob = "\n".join(_lines(_record()))
    assert "29d4a35d" not in blob
    assert "E09 A3 rig" not in blob
    assert "no detector anywhere" not in blob


def test_the_control_line_is_read_from_the_record_when_it_is_there():
    rec = _record(pose_video={"declared_frames": 81,
                              "convention": "AAPose-20 @ deadbeef",
                              "source": "the E09 A3 rig - no detector anywhere"})
    blob = "\n".join(_lines(rec))
    assert "81" in blob and "AAPose-20 @ deadbeef" in blob
    assert "the E09 A3 rig - no detector anywhere" in blob


# ----------------------------------------------------------------- the reference line


def test_a_run_with_no_reference_does_not_describe_one():
    """The whole line was a literal, so a route with no reference image at all still
    printed a letterbox that never happened."""
    line = _find(_lines(_record()), "reference")
    assert "twin_r3_v0" not in line
    assert "352x1024" not in line
    assert M8.MISSING in line


def test_the_reference_line_is_read_from_the_record():
    rec = _record(reference_image={"server_name": "twin_r3_v0.png",
                                   "fit": "letterboxed 352x1024 -> 832x480"})
    line = _find(_lines(rec), "reference")
    assert "twin_r3_v0.png" in line and "letterboxed 352x1024 -> 832x480" in line


# -------------------------------------------------------------------- the meters line


def test_a_record_with_no_meter_does_not_claim_zero_credits():
    line = _find(_lines(_record()), "meters")
    assert "estimate_credits 0" not in line
    assert M8.MISSING in line


def test_the_meter_is_read_from_the_record():
    line = _find(_lines(_record(meters={"estimate_credits": 12})), "meters")
    assert "12" in line


# ------------------------------------------------------------------- unreadable tiles


def _png(path, h=8, w=8):
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    Image.fromarray(np.zeros((h, w, 3), dtype=np.uint8)).save(str(path))
    return str(path)


def test_a_missing_previz_frame_raises_an_error_naming_the_path(tmp_path):
    """The sibling sheets (make_overlay_sheet, make_zoom_sheet, make_plate) all raise a
    named error on `img is None`; this one produced an opaque AttributeError that named
    none of its five inputs."""
    previz = tmp_path / "previz"
    previz.mkdir()
    sticks, painted = tmp_path / "sticks", tmp_path / "painted"
    _png(sticks / "00000.png")
    _png(painted / "00000.png")
    ref = _png(tmp_path / "ref.png")
    prov = tmp_path / "rec.json"
    prov.write_text(json.dumps(_record()), encoding="utf-8")

    with pytest.raises(M8.SheetInputError) as e:
        M8.main([f"--previz={previz}", f"--sticks={sticks}", f"--painted={painted}",
                 f"--reference={ref}", f"--provenance={prov}", "--frames=0",
                 f"--out={tmp_path / 'out' / 'sheet.png'}",
                 "--prompt-id=abc", "--seeds-file=specs/seeds.json"])
    assert os.path.join(str(previz), "00000.png") in str(e.value)


def test_previz_is_required_rather_than_defaulted_into_another_working_tree():
    """The default was an absolute path inside `armature-E09`, a sibling scratch tree."""
    with pytest.raises(SystemExit):
        M8.parse_args(["--out=x.png", "--prompt-id=a", "--seeds-file=b"])


def test_the_module_docstring_is_a_raw_string():
    """It carries a Windows path; as a non-raw docstring it was the tree's only invalid
    escape sequence and the single SyntaxWarning in a compile sweep of all 64 tools."""
    import warnings

    src = open(M8.__file__, encoding="utf-8").read()
    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)
        compile(src, M8.__file__, "exec")
