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
from PIL import Image, ImageDraw

import sheet_compose
from conftest import pil_has_a_scalable_font, sheet_font


# These used to skip on `not os.path.isdir(sheet_compose.FONT_DIR)` — the literal
# `C:\Windows\Fonts` — so every one of them skipped on every CI run, which is
# ubuntu-latest. Nothing here needs Windows. The `sheet_fonts` fixture leaves the
# module's own font resolution alone where it works and falls back to PIL's bundled
# scalable face where there is no platform font, so the layout arithmetic these files
# measure runs everywhere. The only remaining gate is a Pillow too old to scale its own
# default font, which no supported version is.
pytestmark = [
    pytest.mark.skipif(not pil_has_a_scalable_font(),
                       reason="this Pillow cannot produce a scalable font at all"),
    pytest.mark.usefixtures("sheet_fonts"),
]


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

    font = sheet_font("arial.ttf", 26)
    needed = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(long_label, font=font)
    assert sheet.width >= needed + sheet_compose.PAD, (
        f"the sheet is {sheet.width}px wide and the label needs {needed:.0f}px — it was "
        f"cropped")


def test_a_long_title_widens_the_sheet_too(tmp_path):
    title = "E12 GATE LOOK - the two world treatments, full size, before any upload"
    sheet = _run(tmp_path, _spec(tmp_path, title=title))
    font = sheet_font("arialbd.ttf", 44)
    needed = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(title, font=font)
    assert sheet.width >= needed + sheet_compose.PAD


def test_a_long_row_title_widens_the_sheet_too(tmp_path):
    row = ("A2w  -  FULL-BLEED PLATE   (floor dropped from the picture; only the shadow "
           "it catches is kept)")
    sheet = _run(tmp_path, _spec(tmp_path, row_title=row))
    font = sheet_font("arialbd.ttf", 30)
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


# --------------------------------------------------------------- rows and directories

def test_a_row_whose_later_panels_are_taller_is_not_cropped(tmp_path):
    """`height` and the row advance both used `panels[0][0].height`, while the module's own
    rule is that panels are pasted at their rendered size and never resampled. A row whose
    first panel is the short one therefore overflowed into the next row and off the bottom
    — silently, with SHEET_OK printed."""
    spec = _spec(tmp_path)
    spec["rows"][0]["panels"] = [
        {"body": _panel(tmp_path / "short.png", 120, 80), "label": "short"},
        {"body": _panel(tmp_path / "tall.png", 120, 300), "label": "tall"},
    ]
    sheet = _run(tmp_path, spec)
    assert sheet.height >= sheet_compose.TITLE_H + sheet_compose.ROW_TITLE_H + 300 + \
        sheet_compose.LABEL_H


def test_a_ragged_rows_label_sits_below_the_tallest_panel(tmp_path):
    """The label baseline followed the same wrong height, so on a ragged row it was drawn
    across the tall panel's face rather than under the row."""
    spec = _spec(tmp_path)
    spec["rows"][0]["panels"] = [
        {"body": _panel(tmp_path / "short.png", 120, 80), "label": "under me"},
        {"body": _panel(tmp_path / "tall.png", 120, 300), "label": "and me"},
    ]
    import numpy as np
    sheet = np.asarray(_run(tmp_path, spec).convert("RGB"))
    band = sheet[sheet_compose.TITLE_H + sheet_compose.ROW_TITLE_H:
                 sheet_compose.TITLE_H + sheet_compose.ROW_TITLE_H + 300,
                 sheet_compose.PAD + 6: sheet_compose.PAD + 100]
    # the tall panel's own pixels are (90, 90, 90); no label ink may sit inside that band
    assert not (band > 150).any(), "a label was drawn across a panel's face"


def test_the_composer_creates_its_own_output_directory(tmp_path):
    """`sheet.save(path)` wrote into `spec['out']` with no makedirs, against the repo's
    'scripts create their own output directories' rule that two facet runs died on."""
    spec = _spec(tmp_path)
    spec["out"] = str(tmp_path / "not" / "yet" / "there")
    sheet = _run(tmp_path, spec)
    assert sheet.width > 0
    assert os.path.isfile(os.path.join(spec["out"], "sheet.png"))


def test_the_output_line_names_the_typeface_it_used(tmp_path, capsys):
    """A substituted face must be stated, not silent."""
    _run(tmp_path, _spec(tmp_path))
    out = capsys.readouterr().out
    # WAVE-12 (instruments-measure, F-9c43c029): `SHEET_OK` was printed by FOUR tools
    # (`make_cast_sheet`, `make_e13_sheet`, `rig_sheet_compose`, `sheet_compose`) — the
    # only shared success sentinel in the tree, so a caller keying on it could not say
    # which panel it had. Each now prints its own token; this driver's is
    # `SHEET_COMPOSE_OK`.
    assert "SHEET_COMPOSE_OK" in out and "font=" in out


# ------------------------------------------- the siblings that never got the text fix

def _rig_spec(tmp_path, subtitle_frames=200):
    """`rig_sheet_compose`'s panels.json, at the smallest shape it accepts."""
    body = _panel(tmp_path / "body.png", 60, 60)
    bones = _panel(tmp_path / "bones.png", 60, 60)
    out = tmp_path / "rigout"
    return {
        "geometry": {"pad": 26, "label_h": 54, "title_h": 150, "probe_frames": 33},
        "views": [["front", 0, "front"]],
        "full": {"front": [body, bones]},
        "arc": {"1": body, "33": body},
        "insets": {"elbow.L": [body, bones]},
        "joint_order": ["elbow.L"],
        "side": "left",
        "probe": {"which_arm_is_on_plus_x": "left", "frames": subtitle_frames, "fps": 16},
        "out": str(out),
    }


def test_the_rig_sheet_is_as_wide_as_its_own_parameter_line(tmp_path):
    """`W = max(PAD + sum(panel widths))` ignored every string drawn on the sheet, while
    the subtitle is a ~150-character line carrying the arm, the arc range, the key count
    and the fps. sheet_compose computes exactly this and records why; the fix was never
    carried across."""
    import rig_sheet_compose as RSC
    from PIL import Image as _I

    spec = _rig_spec(tmp_path)
    p = tmp_path / "panels.json"
    p.write_text(json.dumps(spec), encoding="utf-8")

    import sys
    argv = sys.argv
    sys.argv = ["rig_sheet_compose", str(p)]
    try:
        RSC.main()
    finally:
        sys.argv = argv

    sheet = _I.open(os.path.join(spec["out"], "E07-rig-sheet.png"))
    # Through `sheet_font`, i.e. `sheet_compose._font` — the binding the `sheet_fonts`
    # fixture patches — so the width is measured in the face the composer just drew
    # with. `sheet_compose.font` is a different object and on a runner with no
    # platform face it raises here after the sheet composed correctly (F-c707995d).
    f_lab = sheet_font("arial.ttf", 26)
    subtitle = (f"22 named bones placed from landmarks measured on the mesh  ·  the arc is "
                f"E03's: the +X-side arm (left), 0°→90° about +Y, "
                f"{spec['probe']['frames']} keys at 16 fps")
    needed = sheet_compose.max_text_width([(subtitle, f_lab)])
    assert sheet.width >= needed + spec["geometry"]["pad"], (
        f"the sheet is {sheet.width}px and the parameter line needs {needed:.0f}px")


def test_the_cast_sheet_is_as_wide_as_its_own_stats_label(tmp_path):
    import make_cast_sheet as MCS
    from PIL import Image as _I

    d = tmp_path / "preview"
    d.mkdir()
    name = "a_very_long_subject_name_that_makes_the_label_run"
    for suf in ("full_a", "full_b", "head_a", "head_b"):
        _panel(d / f"{name}_{suf}.png", 60, 60)
    (d / f"{name}_stats.json").write_text(json.dumps({
        "triangles": 123456, "mesh_objects": 3, "materials": 4,
        "images": [["tex_a", [2048, 2048]], ["tex_b", [2048, 2048]]],
        "empties": 2, "armatures": [["arm", 22, ["hips", "spine", "chest", "neck"]]],
    }), encoding="utf-8")

    out = tmp_path / "castout" / "cast.png"
    MCS.main([f"--dir={d}", f"--names={name}", "--title=cast", f"--out={out}"])

    sheet = _I.open(out)
    # Same binding the composer drew with; see the note above.
    font_r = sheet_font("arial.ttf", 24)
    label = (f"{name}   -   123,456 tris, 3 mesh obj, 4 mats, 2 tex (2048, 2048 px), "
             f"2 empties, armature: 22 bones (hips, spine, chest...)")
    needed = sheet_compose.max_text_width([(label, font_r)])
    assert sheet.width >= needed
