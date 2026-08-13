"""The dailies composer sizes itself to its text as well as to its panels.

Sheets are how numbers reach the Director, and Gate LOOK is a human gate whose entire
output is one image. A sheet sized to its panels alone crops every title and label that
overruns them — and it crops from the right, which is where the measurements sit. It still
saves, still opens, and looks entirely finished; the only symptom is that the evidence is
not on it.

Found on E12's Gate LOOK sheet: 1024-wide panels, a 1076-wide sheet, and gate labels
around 150 characters that ran off the edge.
"""

import json
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

import sheet_compose


pytestmark = pytest.mark.skipif(
    not os.path.isdir(sheet_compose.FONT_DIR),
    reason=f"no font directory at {sheet_compose.FONT_DIR}",
)


def _panel(path, w=120, h=80):
    Image.new("RGB", (w, h), (90, 90, 90)).save(path)
    return str(path)


def _run(tmp_path, spec):
    p = tmp_path / "panels.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    import sys

    argv = sys.argv
    sys.argv = ["sheet_compose", str(p)]
    try:
        sheet_compose.main()
    finally:
        sys.argv = argv
    return Image.open(os.path.join(spec["out"], spec.get("filename", "sheet.png")))


def _spec(tmp_path, title="t", subtitle="", row_title="r", label=""):
    return {
        "title": title, "subtitle": subtitle,
        "out": str(tmp_path), "filename": "sheet.png",
        "rows": [{"title": row_title,
                  "panels": [{"body": _panel(tmp_path / "p.png"), "label": label}]}],
    }


def test_a_label_longer_than_the_panels_widens_the_sheet(tmp_path):
    """THE fixture. The label below is far wider than the 120px panel; if the sheet comes
    back panel-width, every measurement on it has been cropped away."""
    long_label = ("ALPHA 0.9419 transparent   BACKDROP 0.192/255 from plate, 34.934 "
                  "separation   COVERAGE 0.0612   WHOLE margin 26.6px")
    sheet = _run(tmp_path, _spec(tmp_path, label=long_label))

    font = ImageFont.truetype(os.path.join(sheet_compose.FONT_DIR, "arial.ttf"), 26)
    needed = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(long_label, font=font)
    assert sheet.width >= needed + sheet_compose.PAD, (
        f"the sheet is {sheet.width}px wide and the label needs {needed:.0f}px — it was "
        f"cropped")


def test_a_long_title_widens_the_sheet_too(tmp_path):
    title = "E12 GATE LOOK - the two world treatments, full size, before any upload"
    sheet = _run(tmp_path, _spec(tmp_path, title=title))
    font = ImageFont.truetype(os.path.join(sheet_compose.FONT_DIR, "arialbd.ttf"), 44)
    needed = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(title, font=font)
    assert sheet.width >= needed + sheet_compose.PAD


def test_a_long_row_title_widens_the_sheet_too(tmp_path):
    row = ("A2w  -  FULL-BLEED PLATE   (floor dropped from the picture; only the shadow "
           "it catches is kept)")
    sheet = _run(tmp_path, _spec(tmp_path, row_title=row))
    font = ImageFont.truetype(os.path.join(sheet_compose.FONT_DIR, "arialbd.ttf"), 30)
    needed = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(row, font=font)
    assert sheet.width >= needed + sheet_compose.PAD


def test_short_text_still_sizes_to_the_panels(tmp_path):
    """The guard the other direction: text must not be able to SHRINK a sheet below its
    panels, or a row would be cropped instead of a label."""
    sheet = _run(tmp_path, _spec(tmp_path, title="t", row_title="r", label="x"))
    assert sheet.width >= 120 + 2 * sheet_compose.PAD


def test_panels_are_never_resampled(tmp_path):
    """The property the module was written for, pinned: a panel is pasted at its rendered
    size, so a 1:1 claim on a sheet is true."""
    spec = _spec(tmp_path)
    spec["rows"][0]["panels"][0]["body"] = _panel(tmp_path / "big.png", 300, 200)
    sheet = _run(tmp_path, spec)
    assert sheet.height >= 200
