"""The shot-set sheet: labels that fit their cell, and cells that are composited.

Two defects this file exists for, one of them measured on the sheet's own first build.

**Labels that overrun their cell.** `sheet_compose` sizes the SHEET to its longest label —
E12's fix, and the right one for a label that would otherwise be cropped off the right
edge. It does not stop a label from running under the NEXT panel's label, because each is
drawn at its own panel's x. The first build of S04's comparison sheet put 1153 px of label
in a 1024 px cell, so all eight cells' numbers overprinted their neighbours' and the row
read as one smear. It saved, it opened, and it looked finished.

**Cells that vanish into the sheet.** A turnaround master is RGBA with RGB black wherever
alpha is zero. Pasted straight onto a (22,22,24) sheet, the cell boundary disappears — and
the boundary is exactly what a constant-scale claim is read against, as is a figure that
touches its own cell edge.
"""

import json
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

import make_shotset_sheet as MSS
import sheet_compose

pytestmark = pytest.mark.skipif(
    not os.path.isdir(sheet_compose.FONT_DIR),
    reason=f"no font directory at {sheet_compose.FONT_DIR}",
)

CELL = 1024


def _view(i, az, bbox=(359, 108, 664, 937), armed=True):
    """A view record shaped like `render_turnaround`'s, in both gate_CROP shapes."""
    w, h = CELL, CELL
    clear = {"left": bbox[0], "right": (w - 1) - bbox[2],
             "top": bbox[1], "bottom": (h - 1) - bbox[3]}
    crop = ({"gate": "CROP", "view": i, "clearance_px": clear,
             "border_contact": {k: False for k in clear}, "cropped": False}
            if armed else
            {"gate": "CROP", "view": i, "armed": False,
             "border_contact": {"subject_bbox_px": list(bbox), "clearance_px": clear,
                                "touching": []}})
    return {
        "view": i, "azimuth_deg": az, "path": f"turn_{i}.png",
        "subject_bbox_px": list(bbox),
        "gate_ALPHA": {"alpha_extrema": [0, 255], "transparent_fraction": 0.907},
        "gate_WHOLE": {"height_frac": 0.80942, "width_frac": 0.29812},
        "gate_CROP": crop,
    }


def _label_px(label):
    font = ImageFont.truetype(os.path.join(sheet_compose.FONT_DIR, "arial.ttf"), 26)
    return ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(label, font=font)


@pytest.mark.parametrize("armed", [True, False])
def test_a_cell_label_fits_inside_its_own_cell(armed):
    """THE fixture, at the measured font and the production cell width.

    1024 px is the Task-C cell. The label is drawn at `x + 6`, so it has 1018 px before it
    reaches the next panel. A label that fits the SHEET and not the CELL is the failure
    this catches, and the sheet looks entirely finished either way.
    """
    label = MSS.view_label(_view(0, 270.0, armed=armed))
    assert _label_px(label) <= CELL - 6, f"{_label_px(label):.0f} px in a {CELL} px cell"


def test_the_label_still_carries_the_numbers_the_eye_is_comparing(armed=True):
    """Guard the other way: shortening a label until it fits is trivial if it may drop the
    evidence. These five are what the cell is asked to show; everything else is in the
    manifest."""
    label = MSS.view_label(_view(3, 405.0))
    for token in ("az 405", "alpha (0, 255)", "h 0.8094", "px h", "min clear"):
        assert token in label, f"{token!r} missing from {label!r}"


def test_both_gate_crop_shapes_yield_the_same_clearances():
    """Armed and unarmed records keep the clearances at different depths. A reader that
    understood only one shape would silently drop the clearance from every cell of the
    other row — the perspective row, where the gate is not armed."""
    armed = MSS.view_clearances(_view(0, 270.0, armed=True))
    unarmed = MSS.view_clearances(_view(0, 270.0, armed=False))
    assert armed == unarmed == {"left": 359, "right": 359, "top": 108, "bottom": 86}


def test_an_unmeasurable_view_yields_no_clearance_rather_than_a_wrong_one():
    v = _view(0, 270.0)
    v["gate_CROP"] = {"gate": "CROP", "view": 0}
    assert MSS.view_clearances(v) is None
    assert "min clear" not in MSS.view_label(v)


def test_the_ruler_brackets_every_silhouette_on_the_sheet():
    """The rules are derived from the cells so no figure is ruled off its own cell. A ruler
    taken from the first view only would sit inside the taller ones."""
    s = {"views": [_view(0, 270.0, bbox=(300, 120, 700, 900)),
                   _view(1, 315.0, bbox=(310, 90, 690, 950))]}
    assert MSS.rule_rows([s]) == (90, 950)


def test_a_set_with_no_silhouette_draws_no_rules_rather_than_rules_at_zero():
    s = {"views": [dict(_view(0, 270.0), subject_bbox_px=None)]}
    assert MSS.rule_rows([s]) is None


def test_a_transparent_cell_is_composited_over_the_field_not_dropped(tmp_path):
    """The RGB under a transparent pixel is black. Dropping alpha instead of compositing
    paints black cells on a near-black sheet, and the cell boundary — which is what a
    constant-scale claim is read against — disappears."""
    src = tmp_path / "cell.png"
    im = Image.new("RGBA", (40, 30), (0, 0, 0, 0))
    for x in range(15, 25):
        for y in range(10, 20):
            im.putpixel((x, y), (200, 150, 120, 255))
    im.save(src)

    dst = MSS.composite_cell(str(src), str(tmp_path / "out.png"), rules=(12, 18))
    got = Image.open(dst).convert("RGB")
    assert got.size == (40, 30)
    assert got.getpixel((2, 2)) == MSS.CELL_FIELD          # the void carries the field
    assert got.getpixel((20, 15)) == (200, 150, 120)       # the subject is untouched
    assert got.getpixel((0, 0)) == MSS.CELL_BORDER         # the cell is bordered
    assert got.getpixel((5, 12)) == MSS.RULE               # the ruler is drawn


def test_the_cell_is_never_resampled(tmp_path):
    """The property the whole sheet rests on: a millimetre of character is the same number
    of pixels in every cell, so the cells may be pasted 1:1 and compared by eye."""
    src = tmp_path / "cell.png"
    Image.new("RGBA", (137, 211), (10, 20, 30, 255)).save(src)
    dst = MSS.composite_cell(str(src), str(tmp_path / "out.png"), rules=None)
    assert Image.open(dst).size == (137, 211)


def test_a_comparison_across_elevations_is_refused(tmp_path, monkeypatch):
    """A sheet that put an ortho set at 30 degrees beside a perspective set at 0 would
    read as a comparison of projection while showing a comparison of camera height — and
    it is the sheet the repo already had the parts for, since S03's kit is at elevation 0.
    """
    def fake(directory):
        el = 30.0 if "ortho" in directory else 0.0
        return {"dir": directory, "camera": {"elevation_deg": el}, "views": [],
                "manifest": {}, "projection": "X", "ortho_scale": None, "radius": 1.0,
                "elevation_deg": el, "resolution": [8, 8]}

    monkeypatch.setattr(MSS, "load_set", fake)
    with pytest.raises(SystemExit) as exc:
        MSS.main(["--ortho=a/ortho", "--persp=b/persp", f"--out={tmp_path}",
                  "--mode=compare"])
    assert "different elevations" in str(exc.value)


def test_a_missing_manifest_names_itself_rather_than_composing_a_partial_set(tmp_path):
    with pytest.raises(SystemExit) as exc:
        MSS.load_set(str(tmp_path))
    assert "turnaround_manifest.json" in str(exc.value)


# ------------------------------------------------- S05: comparing where the scale came from


def _ortho_set(source, scale=1.1235359256161628, el=30.0):
    """A loaded set shaped like `load_set`'s return, with S05's recorded source."""
    return {"dir": f"d/{source}", "camera": {"elevation_deg": el}, "views": [],
            "manifest": {}, "projection": "ORTHO", "ortho_scale": scale,
            "ortho_scale_source": source, "radius": 2.05, "elevation_deg": el,
            "resolution": [1024, 1024]}


def test_the_row_tag_is_read_off_the_manifest_not_assigned_by_position():
    """The defect this whole mode exists for. `compare` hard-tags its second row PERSP by
    position, so pointing it at two ortho sets prints PERSP over a row whose own manifest
    says ORTHO — and that sheet saves, opens, rules itself and looks finished."""
    assert MSS.set_tag(_ortho_set("solved")) == "SOLVED"
    assert MSS.set_tag(_ortho_set("pinned")) == "PINNED"
    assert MSS.set_tag(dict(_ortho_set("solved"), projection="PERSP")) == "PERSP"


def test_a_set_rendered_before_the_pin_existed_says_so_rather_than_claiming_solved():
    """An S04 manifest has no source key. `None` there is silence about the question, not
    an answer to it, and labelling it `SOLVED` would put a claim on the sheet that the
    manifest never made."""
    older = dict(_ortho_set("solved"), ortho_scale_source=None)
    assert MSS.set_tag(older) == "ORTHO-SOURCE-NOT-RECORDED"
    assert "NOT RECORDED" in MSS.row_title(older, "ORTHO")


def test_the_row_title_names_the_source_and_keeps_the_scale_retypable():
    """`.6f` truncates 1.1235359256161628 to 1.123536, which is a different world span. On
    a pinned row the number IS the recipe — the next character in the roster is rendered by
    retyping it — so the row carries the full repr."""
    pinned = MSS.row_title(_ortho_set("pinned"), "PINNED")
    assert "1.1235359256161628" in pinned
    assert "PINNED, used verbatim" in pinned
    assert "SOLVED from the largest silhouette" in MSS.row_title(_ortho_set("solved"),
                                                                 "SOLVED")


def test_the_scale_mode_refuses_two_sets_whose_tags_would_collide(tmp_path, monkeypatch):
    """Not cosmetic: cells are written as `<tag>_<view>.png`, so two rows sharing a tag
    overwrite each other and the sheet shows ONE set twice — ruled, labelled, and entirely
    plausible as a comparison of two."""
    monkeypatch.setattr(MSS, "load_set", lambda d: _ortho_set("solved"))
    with pytest.raises(SystemExit) as exc:
        MSS.main(["--ortho=a", "--second=b", f"--out={tmp_path}", "--mode=scale"])
    assert "overwrite each other" in str(exc.value)


def test_the_scale_mode_refuses_a_perspective_set(tmp_path, monkeypatch):
    """A perspective set has no shared scale, so there is nothing to compare a source
    against — and the row would be drawn as though there were."""
    def fake(d):
        return (_ortho_set("solved") if d.endswith("a")
                else dict(_ortho_set("pinned"), projection="PERSP"))

    monkeypatch.setattr(MSS, "load_set", fake)
    with pytest.raises(SystemExit) as exc:
        MSS.main(["--ortho=a", "--second=b", f"--out={tmp_path}", "--mode=scale"])
    assert "no such scale to compare" in str(exc.value)


def test_the_scale_mode_refuses_across_elevations(tmp_path, monkeypatch):
    """Same refusal `compare` makes, for the same reason: two sets at different camera
    heights are not a comparison of anything else."""
    def fake(d):
        return (_ortho_set("solved", el=30.0) if d.endswith("a")
                else _ortho_set("pinned", el=0.0))

    monkeypatch.setattr(MSS, "load_set", fake)
    with pytest.raises(SystemExit) as exc:
        MSS.main(["--ortho=a", "--second=b", f"--out={tmp_path}", "--mode=scale"])
    assert "different elevations" in str(exc.value)


def test_the_scale_mode_needs_its_second_set(tmp_path, monkeypatch):
    monkeypatch.setattr(MSS, "load_set", lambda d: _ortho_set("solved"))
    with pytest.raises(SystemExit) as exc:
        MSS.main(["--ortho=a", f"--out={tmp_path}", "--mode=scale"])
    assert "--second" in str(exc.value)
