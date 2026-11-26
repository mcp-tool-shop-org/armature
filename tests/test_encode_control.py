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

The fixtures ask docs/engineering-rules.md#fixture-falsification-question's question of a fixture — what would this look like if the code
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
    """The maintainer's alpha law: the RGB composite a route submits is a deliberate,
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

    with pytest.raises(EC.EncodeFailure,
                       match=r"holds 1 PNG\(s\) that are not numbered frames"):
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

    # WAVE 28 (instruments-measure, F-594d4efc): the private `_run` is now the public
    # `run_ffmpeg`, because it is the one home for the ffmpeg BOUND and its two sibling
    # consumers (`extract_clip_frames.probe`, `measure_cascade_clip.ffprobe_stream`) adopt
    # it by import rather than spelling a second timeout. Keyed on the resolved name here,
    # in the commit that resolves it — a fixture that pins a private spelling goes red on
    # the commit that fixes the thing it exists to police.
    monkeypatch.setattr(EC, "run_ffmpeg", lambda cmd, **kw: _Proc())
    with pytest.raises(EC.EncodeFailure) as e:
        EC.decode("nowhere.mkv", 4, 4)
    assert e.value.evidence["stride"] == 48
    assert e.value.evidence["n_bytes"] == 55


def test_resolve_ffmpeg_prefers_env_then_imageio_then_path(tmp_path, monkeypatch):
    """Item 4: without ARMATURE_FFMPEG, prefer pinned imageio-ffmpeg over PATH ffmpeg."""
    pinned = tmp_path / "pinned-ffmpeg.exe"
    pinned.write_bytes(b"stub")
    on_path = str(tmp_path / "path-ffmpeg.exe")

    assert EC._resolve_ffmpeg(
        env={"ARMATURE_FFMPEG": "/custom/ffmpeg"},
        imageio_getter=lambda: str(pinned),
        which_fn=lambda _n: on_path,
        sys_platform="win32",
        machine="AMD64",
    ) == ("/custom/ffmpeg", "env", None)

    assert EC._resolve_ffmpeg(
        env={},
        imageio_getter=lambda: str(pinned),
        which_fn=lambda _n: on_path,
        sys_platform="win32",
        machine="AMD64",
    ) == (str(pinned), "imageio_ffmpeg", None)

    def _missing_mod():
        raise ImportError("no imageio_ffmpeg")

    assert EC._resolve_ffmpeg(
        env={},
        imageio_getter=_missing_mod,
        which_fn=lambda _n: on_path,
        sys_platform="win32",
        machine="AMD64",
    ) == (on_path, "path", None)

    assert EC._resolve_ffmpeg(
        env={},
        imageio_getter=lambda: str(tmp_path / "absent.exe"),
        which_fn=lambda _n: "",
        sys_platform="win32",
        machine="AMD64",
    ) == ("", "none", None)


def test_resolve_ffmpeg_skips_imageio_on_intel_macos_and_keeps_arm64_and_env(tmp_path):
    """FIX-2: Intel macOS skips imageio-ffmpeg (nonfree build) and falls back to PATH."""
    pinned = tmp_path / "pinned-ffmpeg"
    pinned.write_bytes(b"stub")
    on_path = str(tmp_path / "system-ffmpeg")
    calls = []

    def _spy_getter():
        calls.append("called")
        return str(pinned)

    # Intel macOS with imageio present and ffmpeg on PATH -> skips getter and picks PATH
    assert EC._resolve_ffmpeg(
        env={},
        imageio_getter=_spy_getter,
        which_fn=lambda _n: on_path,
        sys_platform="darwin",
        machine="x86_64",
    ) == (on_path, "path", EC.IMAGEIO_FFMPEG_SKIP_MACOS_X86_64)
    assert calls == []

    # Intel macOS with imageio present and nothing on PATH -> ("", "none", skip_reason)
    assert EC._resolve_ffmpeg(
        env={},
        imageio_getter=_spy_getter,
        which_fn=lambda _n: "",
        sys_platform="darwin",
        machine="X86_64",
    ) == ("", "none", EC.IMAGEIO_FFMPEG_SKIP_MACOS_X86_64)
    assert calls == []

    # Apple Silicon macOS (arm64) still prefers imageio-ffmpeg over PATH
    assert EC._resolve_ffmpeg(
        env={},
        imageio_getter=_spy_getter,
        which_fn=lambda _n: on_path,
        sys_platform="darwin",
        machine="arm64",
    ) == (str(pinned), "imageio_ffmpeg", None)
    assert calls == ["called"]

    # ARMATURE_FFMPEG still wins everywhere
    for plat, arch in (
        ("darwin", "x86_64"),
        ("darwin", "arm64"),
        ("linux", "x86_64"),
        ("win32", "AMD64"),
    ):
        assert EC._resolve_ffmpeg(
            env={"ARMATURE_FFMPEG": "/custom/ffmpeg"},
            imageio_getter=_spy_getter,
            which_fn=lambda _n: on_path,
            sys_platform=plat,
            machine=arch,
        ) == ("/custom/ffmpeg", "env", None)


def test_receipt_and_gate_record_imageio_ffmpeg_skipped_on_intel_macos(tmp_path, monkeypatch):
    """FIX-2: receipts and missing-binary evidence record imageio_ffmpeg_skipped when bypassed."""
    _stub_bridge(monkeypatch)
    monkeypatch.setattr(EC, "ffmpeg_version", lambda: "ffmpeg version test")
    d = _frames_dir(tmp_path, n=2)

    on_path = str(tmp_path / "path-ffmpeg")
    monkeypatch.delenv("ARMATURE_FFMPEG", raising=False)
    monkeypatch.setattr(EC, "_IMPORT_FFMPEG", on_path)
    monkeypatch.setattr(EC, "FFMPEG", on_path)
    monkeypatch.setattr(EC, "FFMPEG_SOURCE", "path")
    monkeypatch.setattr(EC, "IMAGEIO_FFMPEG_SKIPPED", EC.IMAGEIO_FFMPEG_SKIP_MACOS_X86_64)

    r_path = EC.build(str(d), str(tmp_path / "out_mac" / "c.mkv"), "ffv1-gbrp")
    assert r_path["ffmpeg_source"] == "path"
    assert r_path["imageio_ffmpeg_skipped"] == EC.IMAGEIO_FFMPEG_SKIP_MACOS_X86_64

    override = str(tmp_path / "override-ffmpeg")
    monkeypatch.setenv("ARMATURE_FFMPEG", override)
    monkeypatch.setattr(EC, "FFMPEG", override)
    r_env = EC.build(str(d), str(tmp_path / "out_env" / "c.mkv"), "ffv1-gbrp")
    assert r_env["ffmpeg_source"] == "env"
    assert "imageio_ffmpeg_skipped" not in r_env

    monkeypatch.delenv("ARMATURE_FFMPEG", raising=False)
    monkeypatch.setattr(EC, "_IMPORT_FFMPEG", "")
    monkeypatch.setattr(EC, "FFMPEG", "")
    monkeypatch.setattr(EC, "FFMPEG_SOURCE", "none")
    with pytest.raises(EC.EncodeFailure) as exc:
        EC.gate_ffmpeg_binary()
    assert exc.value.evidence["imageio_ffmpeg_skipped"] == EC.IMAGEIO_FFMPEG_SKIP_MACOS_X86_64


def test_receipt_records_which_ffmpeg_source_was_used(tmp_path, monkeypatch):
    """Item 4: receipt carries ffmpeg_source matching env / imageio_ffmpeg / path."""
    _stub_bridge(monkeypatch)
    monkeypatch.setattr(EC, "ffmpeg_version", lambda: "ffmpeg version test")
    d = _frames_dir(tmp_path, n=2)

    monkeypatch.delenv("ARMATURE_FFMPEG", raising=False)
    monkeypatch.setattr(EC, "FFMPEG", str(tmp_path / "pinned.exe"))
    monkeypatch.setattr(EC, "FFMPEG_SOURCE", "imageio_ffmpeg")
    r_pinned = EC.build(str(d), str(tmp_path / "out1" / "c.mkv"), "ffv1-gbrp")
    assert r_pinned["ffmpeg_source"] == "imageio_ffmpeg"
    assert r_pinned["ffmpeg_from_env"] is False

    monkeypatch.setenv("ARMATURE_FFMPEG", str(tmp_path / "override.exe"))
    monkeypatch.setattr(EC, "FFMPEG", str(tmp_path / "override.exe"))
    r_env = EC.build(str(d), str(tmp_path / "out2" / "c.mkv"), "ffv1-gbrp")
    assert r_env["ffmpeg_source"] == "env"
    assert r_env["ffmpeg_from_env"] is True


def test_ffmpeg_source_and_from_env_follow_binary_actually_used(tmp_path, monkeypatch):
    """Part 6: ffmpeg_source() and from_env must reflect whether FFMPEG used the env value."""
    _stub_bridge(monkeypatch)
    monkeypatch.setattr(EC, "ffmpeg_version", lambda: "ffmpeg version test")
    d = _frames_dir(tmp_path, n=2)

    pinned = str(tmp_path / "pinned.exe")
    env_other = str(tmp_path / "env-other.exe")
    monkeypatch.setattr(EC, "_IMPORT_FFMPEG", pinned)
    monkeypatch.setattr(EC, "FFMPEG", pinned)
    monkeypatch.setattr(EC, "FFMPEG_SOURCE", "imageio_ffmpeg")
    monkeypatch.setenv("ARMATURE_FFMPEG", env_other)

    assert EC.ffmpeg_source() == "imageio_ffmpeg"
    r_pinned = EC.build(str(d), str(tmp_path / "out3" / "c.mkv"), "ffv1-gbrp")
    assert r_pinned["ffmpeg_source"] == "imageio_ffmpeg"
    assert r_pinned["ffmpeg_from_env"] is False

    missing = str(tmp_path / "missing-nonenv.exe")
    monkeypatch.setattr(EC, "FFMPEG", missing)
    with pytest.raises(EC.EncodeFailure) as exc:
        EC.gate_ffmpeg_binary()
    assert exc.value.evidence["from_env"] is False


def test_default_imageio_ffmpeg_getter_returns_existing_binary_when_installed():
    """Part 6: exercise the real _default_imageio_ffmpeg getter when media extra is present."""
    import importlib.util

    if EC._is_intel_macos():
        pytest.skip("imageio-ffmpeg is skipped on Intel macOS (nonfree build)")
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("optional extra armature-studio[media] (imageio-ffmpeg==0.6.0) is not installed")
    exe = EC._default_imageio_ffmpeg()
    assert isinstance(exe, str) and exe
    assert os.path.isfile(exe), f"imageio-ffmpeg getter returned missing binary path: {exe}"
    assert "ffmpeg" in os.path.basename(exe).lower()
