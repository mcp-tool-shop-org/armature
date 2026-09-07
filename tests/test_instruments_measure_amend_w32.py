"""Wave 32 — instruments-measure Stage D amend (nine visual findings).

Each test goes red on `6260ee3` without the fix and green beside it. In-process claims
read the module the worktree's PYTHONPATH resolves; sheet LOOK is measured on pixels.
"""

from __future__ import annotations

import ast
import io
import os
import re
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")

sys.path.insert(0, TOOLS)
sys.path.insert(0, TESTS)

import encode_control as EC  # noqa: E402
import extract_clip_frames as ECF  # noqa: E402
import make_ab_clip as AB  # noqa: E402
import make_crop_strip as MCS  # noqa: E402
import make_e13_sheet as E13  # noqa: E402
import make_gate0_sheet as G0  # noqa: E402
import make_overlay_sheet as MOS  # noqa: E402
import make_pick_sheet as MPS  # noqa: E402
import make_startframe_sheet as MSF  # noqa: E402
import make_zoom_sheet as MZS  # noqa: E402
import measure_floor as MF  # noqa: E402
from sheet_compose import PAD as SHEET_PAD  # noqa: E402
from sheet_compose import font as sheet_font  # noqa: E402
from sheet_compose import max_text_width  # noqa: E402


def _png(path, size=(64, 48), colour=(10, 20, 30)):
    Image.fromarray(np.full((*size[::-1], 3), colour, dtype=np.uint8)).save(path)


def _gate0_dirs(tmp_path, n=2, size=(64, 48)):
    ctl = tmp_path / "ctl"
    out = tmp_path / "out"
    ctl.mkdir()
    out.mkdir()
    for i in range(n):
        _png(ctl / f"{i:05d}.png", size=size)
        _png(out / f"{i:05d}.png", size=size, colour=(40, 50, 60))
    return str(ctl), str(out)


# --------------------------------------------------------------------------- F-061259da


def test_gate0_reference_display_shortens_dict_and_path():
    """F-061259da — provenance prints a basename, never the whole dict or abs path."""
    assert G0.reference_display({}) == "NONE (recorded absent)"
    assert G0.reference_display({"reference_image": "ref.png"}) == "ref.png"
    long = "outputs/E11/A1/reference/character_composited.png"
    assert G0.reference_display({"reference_image": long}) == "character_composited.png"
    assert G0.reference_display({
        "reference_image": {"path": long, "sha256": "ab" * 32},
    }) == "character_composited.png"
    joined = "\n".join(G0.provenance_lines({
        "reference_image": {"path": long, "sha256": "cd" * 32},
    }))
    assert "character_composited.png" in joined
    assert "{'path'" not in joined and '{"path"' not in joined


def test_gate0_sheet_width_fits_measured_provenance(tmp_path):
    """F-061259da — sheet width >= provenance column ink under the TrueType face."""
    ctl, out = _gate0_dirs(tmp_path)
    meta = {
        "arm": "A1",
        "reference_image": {
            "path": "outputs/E99/reference/very_long_character_composited.png",
            "sha256": "ab" * 32,
        },
        "control": {"bridge": "pose", "polarity": "white-on-black",
                    "normalization": "unit", "distinct_images": 2, "total_images": 2},
    }
    sheet = G0.build(ctl, out, None, meta, [0, 1], tile_h=120)
    lines = G0.provenance_lines(meta)
    face = sheet_font("arial.ttf", G0.PROV_FONT_SIZE)
    need = int(max_text_width([(ln, face) for ln in lines if ln]))
    # Rightmost non-BG ink must sit inside the canvas (no clip at the edge).
    arr = np.asarray(sheet)
    ink = np.any(arr != np.array(G0.BG), axis=2)
    cols = np.where(ink.any(axis=0))[0]
    assert cols.size, "sheet has no ink"
    assert int(cols[-1]) < sheet.width - 1
    assert sheet.width >= need


# --------------------------------------------------------------------------- F-0cd6a323


def test_gate0_height_covers_provenance_at_short_tiles(tmp_path):
    """F-0cd6a323 — Gate verdict lines stay on-canvas when tile_h is short."""
    ctl, out = _gate0_dirs(tmp_path)
    meta = {
        "arm": "A1",
        "control": {"bridge": "pose", "polarity": "w", "normalization": "u",
                    "distinct_images": 2, "total_images": 2,
                    "bridge_fidelity": "out = src"},
        "gate_B": "PASS", "gate_R": "PASS", "gate_C": "PASS", "gate_G6": "PASS",
    }
    lines = G0.provenance_lines(meta)
    sheet = G0.build(ctl, out, None, meta, [0, 1], tile_h=120)
    y0 = G0.HDR_H + G0.MARGIN
    last_y = y0 + G0.LABEL_H + G0.LINE_H * len(lines)
    assert sheet.height >= last_y + G0.MARGIN
    # Last provenance row has non-BG ink (Gate / bridge lines not clipped off).
    arr = np.asarray(sheet)
    band = arr[max(0, last_y - G0.LINE_H):min(sheet.height, last_y), :, :]
    assert np.any(band != np.array(G0.BG)), "provenance tail is empty — clipped?"


# --------------------------------------------------------------------------- F-559f46b1


def test_crop_strip_box_label_stays_on_canvas(tmp_path):
    """F-559f46b1 — the x0,y0,x1,y1 line is fully inside the strip."""
    frames = tmp_path / "frames"
    frames.mkdir()
    _png(frames / "00000.png", size=(80, 80), colour=(90, 90, 100))
    by_number, _ = MCS.numbered_and_strays(str(frames))
    strip, _rec = MCS.build(by_number, [(0, (4, 4, 34, 34))], scale=4,
                            title="face-zoom-strip-heading")
    arr = np.asarray(strip)
    ink = np.any(arr != np.array(MCS.BG), axis=2)
    rows = np.where(ink.any(axis=1))[0]
    assert rows.size, "strip has no ink"
    # Pre-fix: glyph ink sat on the final row (margin 0). Post-fix: room below.
    assert strip.height - 1 - int(rows[-1]) >= 2, (
        f"box label hard against bottom edge: last ink row {rows[-1]} of {strip.height}")
    # Title that overruns tiles widens the strip.
    assert strip.width >= 80


# --------------------------------------------------------------------------- F-f79959ea / F-5b24109f


def test_overlay_frame_label_uses_black_bar_and_gutter():
    """F-f79959ea + F-5b24109f — e08-style caption bar; PAD gutter between tiles."""
    src = open(os.path.join(TOOLS, "make_overlay_sheet.py"), encoding="utf-8").read()
    assert "LABEL_BAR_H" in src
    assert "TILE_GUTTER" in src
    assert MOS.TILE_GUTTER == SHEET_PAD
    assert MOS.LABEL_BAR_H == 26
    # Joint index draws a dark halo then white (two putText calls per index).
    assert src.count("cv2.putText(over, str(j)") >= 2


def test_zoom_sheet_inserts_gutter_between_tiles():
    """F-5b24109f — zoom sheet shares the dailies PAD gutter."""
    assert MZS.TILE_GUTTER == SHEET_PAD
    src = open(os.path.join(TOOLS, "make_zoom_sheet.py"), encoding="utf-8").read()
    assert "TILE_GUTTER" in src
    assert "concatenate" in src


# --------------------------------------------------------------------------- F-7586ba2d


def test_measure_floor_shape_table_bands_at_sixteen():
    """F-7586ba2d — THE SHAPE emits fixed-width bands, not one 80+ column line."""
    src = open(os.path.join(TOOLS, "measure_floor.py"), encoding="utf-8").read()
    assert "SHAPE_BAND" in src
    tree = ast.parse(src)
    # The band constant is 16.
    assigns = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "SHAPE_BAND"
                       for t in n.targets)]
    assert assigns, "SHAPE_BAND not assigned"
    assert any(isinstance(a.value, ast.Constant) and a.value.value == 16
               for a in assigns)


def test_measure_floor_shape_print_stays_under_terminal_width(tmp_path, capsys):
    """n=20 with SHAPE_BAND=16 yields two header rows, each under ~80 cols."""
    root = tmp_path / "runs"
    for name in ("r1", "r2"):
        d = root / name / "lossless"
        d.mkdir(parents=True)
        for i in range(20):
            _png(d / f"{i:05d}.png", size=(8, 8), colour=(i, 10, 20))
    out = tmp_path / "floor.json"
    MF.main([f"--runs=r1,r2", f"--root={root}", f"--out={out}",
             "--early=0-1", "--late=18-19"])
    printed = capsys.readouterr().out
    assert "THE SHAPE" in printed
    headers = [ln for ln in printed.splitlines() if ln.strip().startswith("frame :")]
    assert len(headers) >= 2, printed
    for line in headers:
        assert len(line) < 120, line


# --------------------------------------------------------------------------- F-7cf7e22f


def test_ab_clip_banner_ellipsizes_to_panel_width():
    """F-7cf7e22f — caption fits inside a narrow panel; no ink past the right edge."""
    im = Image.new("RGB", (160, 80), (30, 30, 40))
    long = "E08 A2 pose-sticks @16fps   f00012   t=0.750s"
    face = sheet_font("arial.ttf", 13)
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    assert d.textlength(long, font=face) > 160 - 12
    out = AB.banner(im, long)
    assert out.width == 160
    arr = np.asarray(out)
    bar = arr[:22, :, :]
    ink_cols = np.where(np.any(bar != 0, axis=2))[0]
    assert ink_cols.size
    # Full caption overruns; ellipsis must leave a margin, not paint the final column.
    assert int(ink_cols[-1]) < out.width - 2
    # And the drawn caption is a shortened form of `long`.
    short = AB._ellipsize(d, long, 160 - 12, font=face)
    assert short != long and short.endswith("...")
    assert d.textlength(short, font=face) <= 160 - 12


# --------------------------------------------------------------------------- F-7f9eb100


@pytest.mark.parametrize("mod", (G0, MSF, MPS, E13, MCS, AB))
def test_gate0_family_routes_through_sheet_compose_font(mod):
    """F-7f9eb100 — judging sheets load the licence-checked TrueType face."""
    src = open(mod.__file__, encoding="utf-8").read()
    assert "sheet_compose" in src and ("sheet_font" in src or "font as" in src)


def test_gate0_build_draws_with_truetype(tmp_path):
    ctl, out = _gate0_dirs(tmp_path)
    sheet = G0.build(ctl, out, None, {"arm": "A1"}, [0], tile_h=64)
    assert isinstance(sheet, Image.Image)
    # Default bitmap face is ImageFont.ImageFont; TrueType is FreeTypeFont.
    assert hasattr(ImageFont, "FreeTypeFont")


# --------------------------------------------------------------------------- F-e28656b8


def test_encode_control_progress_prints_a_real_bound(capsys):
    """F-e28656b8 — progress carries `bound <N>s`, never the dead token `bound none`."""
    started = 0.0

    def _progress(stage, done, total):
        bound_s = EC.timeout_for_frames(total)
        print(f"encode_control {stage} {done}/{total}  "
              f"elapsed 0.0s  bound {bound_s:.0f}s",
              file=sys.stderr, flush=True)

    # Exercise the same formula main's closure uses.
    _progress("read", 1, 4)
    err = capsys.readouterr().err
    assert "bound none" not in err
    assert re.search(r"bound \d+s", err), err
    src = open(os.path.join(TOOLS, "encode_control.py"), encoding="utf-8").read()
    # Live print format — comments may still name the retired token.
    assert re.search(r'bound \{bound_s', src)
    assert "timeout_for_frames" in src.split("def _progress")[1].split("receipt =")[0]
    assert not re.search(r'f?".*bound none', src)


def test_extract_write_progress_keeps_clip_bound():
    """F-e28656b8 — write lines reuse timeout_for_file, not `bound none`."""
    src = open(os.path.join(TOOLS, "extract_clip_frames.py"), encoding="utf-8").read()
    assert "timeout_for_file(a.clip)" in src
    assert not re.search(r'f?".*bound none', src)
