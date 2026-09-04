"""Tests for the near-dark polarity transform.

The fixtures are built around one question: *what would this look like if the code were
wrong in the specific way the check exists to catch?* Inversion of uint8 cannot fail, so
nothing here tests that `255 - x` equals `255 - x`. What is tested is the set of inputs
where a silent, plausible-looking wrong answer is possible — 16-bit depth, alpha, palette
indices, colour — plus the semantic claim the docstring makes about the background.

Read back with **Pillow**, not with our own writer's reader: pngio has no reader on
purpose (EXTERNAL_VERIFIER), and a writer checked by its own reader has been checked
against nothing.
"""

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from armature_core import pngio  # noqa: E402
from invert_frames import InvertError, invert_dir, main  # noqa: E402


def _write_gray(path, arr):
    pngio.write_png(path, np.asarray(arr, dtype=np.uint8), bit_depth=8)


@pytest.fixture()
def src(tmp_path):
    d = tmp_path / "src"
    d.mkdir()
    return d


def test_inverts_every_value_and_pillow_agrees(src, tmp_path):
    # Every 8-bit value present exactly once per row block, so a partial mapping shows up.
    ramp = np.arange(256, dtype=np.uint8).reshape(16, 16)
    _write_gray(str(src / "00000.png"), ramp)
    _write_gray(str(src / "00001.png"), ramp[::-1])

    out = tmp_path / "dst"
    receipt = invert_dir(str(src), str(out))

    assert receipt["n_frames"] == 2
    back = np.array(Image.open(out / "00000.png"))
    assert back.dtype == np.uint8
    np.testing.assert_array_equal(back, 255 - ramp)
    # the full value set survives — a lookup table that dropped an entry would not
    assert sorted(np.unique(back).tolist()) == list(range(256))


def test_double_inversion_returns_the_original_pixels(src, tmp_path):
    rng = np.random.default_rng(3)
    for i in range(3):
        _write_gray(str(src / f"{i:05d}.png"), rng.integers(0, 256, (8, 12), dtype=np.uint8))

    once = invert_dir(str(src), str(tmp_path / "a"))
    twice = invert_dir(str(tmp_path / "a"), str(tmp_path / "b"))

    # An involution: the second pass must reproduce the first pass's INPUT hash exactly.
    assert twice["out_pixels_sha256"] == once["src_pixels_sha256"]
    assert twice["src_pixels_sha256"] == once["out_pixels_sha256"]


def test_background_zero_becomes_255_which_is_the_near_dark_claim(src, tmp_path):
    """The docstring's semantic claim, pinned: black-is-far survives the flip as white-is-far."""
    frame = np.zeros((32, 32), dtype=np.uint8)
    frame[10:20, 10:20] = 200  # a "near" subject over a 0 background
    _write_gray(str(src / "00000.png"), frame)

    receipt = invert_dir(str(src), str(tmp_path / "dst"))
    rec = receipt["per_frame"][0]
    assert rec["src_modal"] == 0, "fixture is wrong: the background must be the modal value"
    assert rec["out_modal"] == 255
    assert (rec["src_min"], rec["src_max"]) == (0, 200)
    assert (rec["out_min"], rec["out_max"]) == (55, 255)


def test_sixteen_bit_source_raises_rather_than_producing_garbage(src, tmp_path):
    # `255 - 40000` is not a polarity flip; without the check it would silently wrap.
    Image.fromarray(np.full((8, 8), 40000, dtype=np.uint16)).save(src / "00000.png")
    with pytest.raises(InvertError, match="8-bit"):
        invert_dir(str(src), str(tmp_path / "dst"))


def test_alpha_source_raises(src, tmp_path):
    rgba = np.zeros((8, 8, 4), dtype=np.uint8)
    rgba[..., 3] = 255
    Image.fromarray(rgba, mode="RGBA").save(src / "00000.png")
    with pytest.raises(InvertError, match="alpha"):
        invert_dir(str(src), str(tmp_path / "dst"))


def test_palette_source_raises(src, tmp_path):
    Image.fromarray(np.zeros((8, 8), dtype=np.uint8), mode="L").convert("P").save(src / "00000.png")
    with pytest.raises(InvertError, match="palette"):
        invert_dir(str(src), str(tmp_path / "dst"))


def test_true_colour_source_raises_but_r_equals_g_equals_b_is_accepted(src, tmp_path):
    gray = np.random.default_rng(1).integers(0, 256, (8, 8), dtype=np.uint8)
    Image.fromarray(np.repeat(gray[..., None], 3, axis=2), mode="RGB").save(src / "00000.png")
    receipt = invert_dir(str(src), str(tmp_path / "ok"))
    assert receipt["n_frames"] == 1

    colour = np.random.default_rng(2).integers(0, 256, (8, 8, 3), dtype=np.uint8)
    colour[0, 0] = (1, 2, 3)  # guarantee the channels differ
    d2 = tmp_path / "src2"
    d2.mkdir()
    Image.fromarray(colour, mode="RGB").save(d2 / "00000.png")
    with pytest.raises(InvertError, match="R=G=B"):
        invert_dir(str(d2), str(tmp_path / "bad"))


def test_empty_directory_raises(src, tmp_path):
    with pytest.raises(InvertError, match="nothing to invert"):
        invert_dir(str(src), str(tmp_path / "dst"))


def test_a_stray_contact_sheet_beside_the_frames_is_refused(src, tmp_path):
    """The other half of P1, on the tool that writes the files an upload is built from.

    `render_pose_sticks` writes `strip_every{N}.png` into the very directory it just
    filled with `NNNNN.png` frames. Under the old bare listdir the stray sorted last,
    was inverted like a frame, and appeared in the receipt's `frame_names` — while
    `--expect` counted it, so a 33-frame shot with a contact sheet in it satisfied
    `--expect=34` and nothing anywhere said what the 34th frame was.
    """
    for i in range(3):
        _write_gray(str(src / f"{i:05d}.png"), np.zeros((4, 4), dtype=np.uint8))
    _write_gray(str(src / "strip_every8.png"), np.zeros((4, 4), dtype=np.uint8))

    with pytest.raises(InvertError) as e:
        invert_dir(str(src), str(tmp_path / "dst"))
    assert "strip_every8.png" in str(e.value)
    assert e.value.evidence["unexpected"] == ["strip_every8.png"]
    assert e.value.evidence["frames"] == ["00000.png", "00001.png", "00002.png"]
    assert not os.path.exists(str(tmp_path / "dst"))


def test_the_declared_count_pins_the_population_to_the_specs_own_names(src, tmp_path):
    """`--expect` used to compare a length. A length is satisfied by any five files;
    the spec names five particular ones."""
    for i in (1, 2, 3):
        _write_gray(str(src / f"{i:05d}.png"), np.zeros((4, 4), dtype=np.uint8))
    with pytest.raises(InvertError) as e:
        invert_dir(str(src), str(tmp_path / "dst"), expect=3)
    assert e.value.evidence["missing"] == ["00000.png"]
    assert e.value.evidence["unexpected"] == ["00003.png"]


def test_frames_are_ordered_by_number_not_by_string(src, tmp_path):
    """Unpadded numbering sorts `10` before `9`; the receipt's order is the performance."""
    for i in (0, 2, 9, 10):
        _write_gray(str(src / f"{i}.png"), np.full((4, 4), i, dtype=np.uint8))
    receipt = invert_dir(str(src), str(tmp_path / "dst"))
    assert receipt["frame_names"] == ["0.png", "2.png", "9.png", "10.png"]


def test_short_directory_raises_when_a_count_is_declared(src, tmp_path):
    """A short control directory becomes a short batch, and Gate B only sees it after a spend."""
    for i in range(4):
        _write_gray(str(src / f"{i:05d}.png"), np.zeros((4, 4), dtype=np.uint8))
    # `match="expected 33"` also matches "expected 330". The clause phrase is pinned, the
    # number anchored, and the counts read off the structured evidence (F-02683edb).
    with pytest.raises(InvertError,
                       match=r"holds \b4 frames, expected \b33 named as the spec") as e:
        invert_dir(str(src), str(tmp_path / "dst"), expect=33)
    assert len(e.value.evidence["found"]) == 4
    assert len(e.value.evidence["expected"]) == 33
    # ...and passes when the count is right
    assert invert_dir(str(src), str(tmp_path / "ok"), expect=4)["n_frames"] == 4


def test_cli_writes_a_receipt_beside_the_output(src, tmp_path, capsys):
    _write_gray(str(src / "00000.png"), np.zeros((4, 4), dtype=np.uint8))
    out = tmp_path / "dst"
    assert main([f"--frames={src}", f"--out={out}", "--expect=1"]) == 0

    receipt = json.loads((tmp_path / "dst.receipt.json").read_text(encoding="utf-8"))
    assert receipt["transform"] == "255 - x, full image, 8-bit"
    assert receipt["n_frames"] == 1
    assert receipt["resolution"] == [4, 4]
    assert "INVERT_FRAMES" in capsys.readouterr().out


# --------------------------------- every refusal carries the measurement that fired it
#
# `InvertError`'s own class docstring says it does — "Carries an evidence dict, like every
# other refusal in this repo: the measurement that fired it is the useful half" — and
# `_read_u8_gray`'s five refusals all called it with the message alone, so `e.evidence` was
# `{}` on every one of them, while `frame_population`'s three refusals in the same file all
# carried one. Measured 2026-09-04: `InvertError('x').evidence == {}`.
#
# The first of the five is the alpha-law-adjacent one — the refusal that exists because
# inverting opacity is not a polarity flip. A halt on a control directory reached the run
# record with nothing machine-readable behind it; a human reading stderr still got the mode
# or the dtype from the message, and nothing else did.

import invert_frames as IF  # noqa: E402
import numpy as _np  # noqa: E402
from PIL import Image as _Image  # noqa: E402


def _write(path, arr, mode=None):
    _Image.fromarray(arr, mode=mode).save(path) if mode else _Image.fromarray(arr).save(path)
    return str(path)


def test_an_rgba_source_names_its_mode_in_the_evidence(tmp_path):
    p = _write(tmp_path / "a.png", _np.zeros((4, 4, 4), dtype=_np.uint8), mode="RGBA")
    with pytest.raises(IF.InvertError, match=r"carries alpha") as e:
        IF._read_u8_gray(p)
    assert e.value.evidence["mode"] == "RGBA"
    assert e.value.evidence["path"] == p


def test_a_palette_source_names_its_mode_in_the_evidence(tmp_path):
    p = tmp_path / "p.png"
    _Image.fromarray(_np.zeros((4, 4), dtype=_np.uint8)).convert("P").save(p)
    with pytest.raises(IF.InvertError, match=r"palette-indexed") as e:
        IF._read_u8_gray(str(p))
    assert e.value.evidence["mode"] == "P"


def test_a_sixteen_bit_source_names_its_dtype_in_the_evidence(tmp_path):
    p = tmp_path / "d.png"
    _Image.fromarray(_np.full((4, 4), 40000, dtype=_np.uint16)).save(p)
    with pytest.raises(IF.InvertError, match=r"polarity flip only for 8-bit") as e:
        IF._read_u8_gray(str(p))
    assert "dtype" in e.value.evidence and e.value.evidence["dtype"] != "uint8"


def test_a_colour_source_names_its_shape_in_the_evidence(tmp_path):
    arr = _np.zeros((4, 4, 3), dtype=_np.uint8)
    arr[..., 0] = 200                                   # R != G, so not a grayscale channel
    p = _write(tmp_path / "c.png", arr)
    with pytest.raises(IF.InvertError, match=r"not R=G=B") as e:
        IF._read_u8_gray(p)
    assert e.value.evidence["shape"] == [4, 4, 3]


def test_a_grayscale_source_still_reads(tmp_path):
    """The guard the other way: the evidence dicts must not have made a legal read fail."""
    p = _write(tmp_path / "g.png", _np.full((4, 4), 17, dtype=_np.uint8))
    assert IF._read_u8_gray(p).shape == (4, 4)


def test_no_refusal_in_this_module_reaches_a_report_empty_handed():
    """Derived by AST over the module: every `raise InvertError(...)` passes a second
    argument. Written as a walk so a sixth refusal added later cannot opt out."""
    import ast

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tree = ast.parse(open(os.path.join(root, "tools", "invert_frames.py"),
                          encoding="utf-8").read())
    raises = [n for n in ast.walk(tree)
              if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
              and getattr(n.exc.func, "id", "") == "InvertError"]
    assert len(raises) >= 8, len(raises)
    bare = [ast.unparse(r)[:70] for r in raises if len(r.exc.args) < 2]
    assert bare == [], bare
