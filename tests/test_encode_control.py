"""The control-video bridge's *input* contract: which files are frames, and what a frame is.

Two defects, both silent by construction, both caught here before an upload is paid for.

**The population.** `load_frames` used to take every `*.png` in the directory. The stick
renderer writes a `strip_every{N}.png` contact sheet into the very directory it just filled
with `NNNNN.png` frames, so the stray sorts last and becomes the final frame of the encoded
control — while G2 (which iterates the EXPECTED names) reports `present: 5, expected: 5` and
Gate R compares the same six-frame population against its own decode and passes too. Every
gate green, one frame of contact sheet in the control video.

**The coercion.** `load_frames` used to reshape anything into (H, W, 3) uint8: a 4th channel
dropped outright, and a 16-bit PNG cast through `np.ascontiguousarray(..., uint8)`, which
wraps mod 256 (a depth level of 40000 becomes 64) rather than raising. The receipt then
recorded the sha256 of the ALREADY-coerced array, so neither is visible afterwards, and
Gate R compares the coerced frames against the decode so it cannot fire on either.

The fixtures ask CLAUDE.md's question of a fixture — what would this look like if the code
were wrong in the way the check exists to catch? — so every one of them is an input that
produced a *plausible* wrong answer before, not an input that crashed.
"""

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import encode_control as EC  # noqa: E402


def _gray(path, arr):
    Image.fromarray(np.asarray(arr, dtype=np.uint8), mode="L").save(path)


def _frames_dir(tmp_path, n=5, h=8, w=6):
    d = tmp_path / "depth_perframe"
    d.mkdir()
    rng = np.random.default_rng(11)
    for i in range(n):
        _gray(str(d / f"{i:05d}.png"), rng.integers(0, 256, (h, w), dtype=np.uint8))
    return d


# ------------------------------------------------------------------ the population


def test_a_stray_contact_sheet_beside_the_frames_is_refused(tmp_path):
    """THE fixture, and it is not hypothetical: `render_pose_sticks` writes exactly this
    file into exactly this directory. Same size as the frames, so nothing about the shape
    of the array gives it away — only its name does."""
    d = _frames_dir(tmp_path, n=5)
    _gray(str(d / "strip_every8.png"), np.zeros((8, 6), dtype=np.uint8))

    with pytest.raises(EC.EncodeFailure) as e:
        EC.load_frames(str(d))
    assert "strip_every8.png" in str(e.value)
    assert e.value.evidence["unexpected"] == ["strip_every8.png"]
    assert len(e.value.evidence["frames"]) == 5


def test_the_population_is_ordered_by_number_not_by_string(tmp_path):
    """A directory numbered past 9 without padding sorts `10` before `9` lexically. The
    frames are the order; a reordered control is a different performance."""
    d = tmp_path / "f"
    d.mkdir()
    for i in (0, 2, 9, 10):
        _gray(str(d / f"{i}.png"), np.full((4, 4), i, dtype=np.uint8))
    names, frames = EC.load_frames(str(d))
    assert names == ["0.png", "2.png", "9.png", "10.png"]
    assert [int(f[0, 0, 0]) for f in frames] == [0, 2, 9, 10]


def test_an_expected_count_pins_the_population_to_the_spec(tmp_path):
    d = _frames_dir(tmp_path, n=5)
    assert len(EC.load_frames(str(d), expect=5)[0]) == 5
    with pytest.raises(EC.EncodeFailure) as e:
        EC.load_frames(str(d), expect=6)
    assert e.value.evidence["missing"] == ["00005.png"]


def test_a_directory_with_no_numbered_frames_raises(tmp_path):
    d = tmp_path / "f"
    d.mkdir()
    with pytest.raises(EC.EncodeFailure, match="no NNNNN.png"):
        EC.load_frames(str(d))


# ------------------------------------------------------------------- the coercion


def test_an_rgba_frame_directory_raises_rather_than_dropping_the_channel(tmp_path):
    """The Director's alpha law: the RGB composite a route submits is a deliberate,
    recorded choice. Dropping the 4th channel makes it an accidental one."""
    d = tmp_path / "f"
    d.mkdir()
    rgba = np.zeros((8, 8, 4), dtype=np.uint8)
    rgba[..., 3] = 255
    Image.fromarray(rgba, mode="RGBA").save(d / "00000.png")

    with pytest.raises(EC.EncodeFailure) as e:
        EC.load_frames(str(d))
    assert "RGBA" in str(e.value)
    assert e.value.evidence["alpha_present"] is True


def test_a_named_plate_makes_the_alpha_disposition_an_explicit_choice(tmp_path):
    """The other half of the law: the drop is allowed when a plate is NAMED, and then the
    composite is what the plate says it is — here, alpha 0 over (10, 20, 30)."""
    d = tmp_path / "f"
    d.mkdir()
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[..., :3] = 200
    rgba[..., 3] = 0            # fully transparent: the plate must show through entirely
    Image.fromarray(rgba, mode="RGBA").save(d / "00000.png")

    _, frames = EC.load_frames(str(d), alpha_over=(10, 20, 30))
    assert frames[0].shape == (4, 4, 3)
    np.testing.assert_array_equal(frames[0][0, 0], np.array([10, 20, 30], dtype=np.uint8))


def test_a_sixteen_bit_frame_directory_raises_rather_than_wrapping_mod_256(tmp_path):
    """40000 -> 64 under the old cast, and the receipt hashed the wrapped array."""
    d = tmp_path / "f"
    d.mkdir()
    Image.fromarray(np.full((8, 8), 40000, dtype=np.uint16)).save(d / "00000.png")

    with pytest.raises(EC.EncodeFailure) as e:
        EC.load_frames(str(d))
    assert "uint16" in str(e.value)
    assert e.value.evidence["dtype"] == "uint16"


def test_a_palette_frame_directory_raises(tmp_path):
    d = tmp_path / "f"
    d.mkdir()
    Image.fromarray(np.zeros((8, 8), dtype=np.uint8), mode="L").convert("P").save(d / "00000.png")
    with pytest.raises(EC.EncodeFailure, match="palette"):
        EC.load_frames(str(d))


# ------------------------------------------------------------------------ the receipt


def _stub_bridge(monkeypatch):
    """Encode/decode replaced by an identity bridge: this file is about the INPUT contract,
    and ffmpeg's own path is pinned to this rig. Gate R still runs, on real arrays."""
    def fake_encode(frames, path, codec, fps=16):
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"".join(f.tobytes() for f in frames))
        fake_encode.frames = [f.copy() for f in frames]
        return path

    monkeypatch.setattr(EC, "encode", fake_encode)
    monkeypatch.setattr(EC, "decode", lambda path, w, h: fake_encode.frames)
    return fake_encode


def test_the_receipt_states_the_alpha_and_dtype_of_what_it_read(tmp_path, monkeypatch):
    _stub_bridge(monkeypatch)
    d = _frames_dir(tmp_path, n=3)
    out = tmp_path / "out" / "control.mkv"

    receipt = EC.build(str(d), str(out), "ffv1-gbrp")
    assert receipt["source_alpha_present"] is False
    assert receipt["alpha_disposition"] == "no alpha channel in any source frame"
    assert receipt["source_dtype"] == "uint8"
    assert receipt["source_modes"] == ["L"]
    on_disk = json.loads((tmp_path / "out" / "control.mkv.receipt.json").read_text(encoding="utf-8"))
    assert on_disk["source_dtype"] == "uint8"


def test_a_stray_png_never_reaches_the_receipts_frame_names(tmp_path, monkeypatch):
    _stub_bridge(monkeypatch)
    d = _frames_dir(tmp_path, n=3)
    _gray(str(d / "strip_every8.png"), np.zeros((8, 6), dtype=np.uint8))
    out = tmp_path / "out" / "control.mkv"

    with pytest.raises(EC.EncodeFailure):
        EC.build(str(d), str(out), "ffv1-gbrp")
    assert not os.path.exists(str(out) + ".receipt.json")


# --------------------------------------------------------------------- the decoder


def test_a_partial_trailing_frame_is_refused_rather_than_dropped(tmp_path, monkeypatch):
    """`n = len(raw) // stride` drops a trailing partial frame in silence. A decode whose
    byte count is not a whole number of frames is a decode at the wrong stride — which is
    what a clip returned at a resolution nobody read off the stream looks like."""
    class _Proc:
        returncode = 0
        stdout = b"\x00" * (4 * 4 * 3 + 7)
        stderr = b""

    monkeypatch.setattr(EC, "_run", lambda cmd, **kw: _Proc())
    with pytest.raises(EC.EncodeFailure) as e:
        EC.decode("nowhere.mkv", 4, 4)
    assert e.value.evidence["stride"] == 48
    assert e.value.evidence["n_bytes"] == 55
