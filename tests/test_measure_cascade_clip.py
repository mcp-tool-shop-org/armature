"""The cascade decode comparison: what dimensions the decode uses, and where "the middle" is.

**The dimensions.** `ffprobe_stream` parses the stream's own width and height off ffmpeg's
report, and then the decode was called with `sources[0].shape` instead. `encode_control.decode`
reshapes a raw byte stream at `stride = width*height*3`, so a clip whose real resolution
differs from the source frames is reinterpreted at the wrong stride: the frames become
garbage, and `n_decoded_frames` can still land on `--expect-frames`, letting the count andon
pass and every fidelity and order number below it be computed over scrambled pixels. The
sibling `extract_clip_frames` gets this right and its docstring states the rule — the
dimensions are read off the stream *because* supplying them is how a decode silently
reshapes.

**The middle.** `gradient_split_frame40` hard-coded index 40, which is the middle only of the
default 81. A legal shorter run (`--expect-frames=17`, a generator-legal bucket) passed the
count andon and then died at that line with a bare IndexError — after the decode had been
spent and the record written. A global constant governing a local feature, applied to a frame
index.

ffmpeg is not invoked here: its path is pinned to this rig, and the questions in this file
are about what the tool does with what ffmpeg returns.
"""

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import measure_cascade_clip as MCC  # noqa: E402


def _sources(tmp_path, n, h=32, w=32):
    d = tmp_path / "frames"
    d.mkdir()
    frames = []
    for i in range(n):
        a = np.zeros((h, w, 3), dtype=np.uint8)
        a[:, :, 0] = (i * 13) % 256
        a[i % h, :, 1] = 255          # a moving band, so the order check has a diagonal
        a[:, i % w, 2] = 200
        Image.fromarray(a).save(d / f"{i:05d}.png")
        frames.append(a)
    return d, frames


def _stub(monkeypatch, frames, width, height, fps=16.0):
    monkeypatch.setattr(MCC, "ffprobe_stream", lambda path: {
        "raw": [], "stream": f"Video: h264, {width}x{height}", "fps": fps,
        "width": width, "height": height})
    seen = {}

    def fake_decode(path, w, h):
        seen["wh"] = (w, h)
        return [f.copy() for f in frames]

    monkeypatch.setattr(MCC, "decode", fake_decode)
    return seen


def _clip(tmp_path):
    p = tmp_path / "clip.mp4"
    p.write_bytes(b"not a real container; ffprobe is stubbed")
    return p


# ------------------------------------------------------------------- the dimensions


def test_the_decode_uses_the_streams_own_dimensions(tmp_path, monkeypatch):
    d, frames = _sources(tmp_path, 3)
    seen = _stub(monkeypatch, frames, 32, 32)
    MCC.main([f"--clip={_clip(tmp_path)}", f"--frames={d}", f"--out={tmp_path / 'o'}",
              "--expect-frames=3", "--step=8"])
    assert seen["wh"] == (32, 32)


def test_a_stream_whose_resolution_differs_from_the_sources_raises(tmp_path, monkeypatch):
    """THE fixture: the clip really is 64x48 and the source frames are 32x32. Decoded at
    the sources' stride the bytes reshape into something, and the count can still be right."""
    d, frames = _sources(tmp_path, 3)
    _stub(monkeypatch, frames, 64, 48)

    with pytest.raises(MCC.ClipShapeError) as e:
        MCC.main([f"--clip={_clip(tmp_path)}", f"--frames={d}", f"--out={tmp_path / 'o'}",
                  "--expect-frames=3"])
    ev = e.value.evidence
    assert ev["stream_shape"] == [48, 64]
    assert ev["source_shape"] == [32, 32]
    assert not os.path.exists(tmp_path / "o" / "cascade_decode_compare.json")


def test_a_stream_that_reported_no_dimensions_raises_rather_than_assuming(tmp_path, monkeypatch):
    """The fallback that caused this: when the parse fails, `sources[0].shape` was used
    and the failure became invisible."""
    d, frames = _sources(tmp_path, 3)
    monkeypatch.setattr(MCC, "ffprobe_stream", lambda path: {"raw": [], "fps": 16.0})
    monkeypatch.setattr(MCC, "decode", lambda p, w, h: frames)

    with pytest.raises(MCC.ClipShapeError, match="did not report"):
        MCC.main([f"--clip={_clip(tmp_path)}", f"--frames={d}", f"--out={tmp_path / 'o'}",
                  "--expect-frames=3"])


# ----------------------------------------------------------------------- the middle


def test_a_seventeen_frame_clip_is_measurable(tmp_path, monkeypatch):
    """17 is a legal bucket. Under the hard-coded index this died with a bare IndexError
    after the decode had already been spent."""
    d, frames = _sources(tmp_path, 17)
    _stub(monkeypatch, frames, 32, 32)

    rec = MCC.main([f"--clip={_clip(tmp_path)}", f"--frames={d}", f"--out={tmp_path / 'o'}",
                    "--expect-frames=17", "--step=8"])
    assert rec["gradient_split_mid_frame"]["frame_index"] == 8
    assert rec["gradient_split_first_frame"]["frame_index"] == 0
    assert "gradient_split_frame40" not in rec


def test_the_key_is_named_after_the_value_it_holds(tmp_path, monkeypatch):
    """81 frames: the mid frame is 40, and the record says which index it used rather
    than naming it in the key."""
    d, frames = _sources(tmp_path, 81, h=8, w=8)
    _stub(monkeypatch, frames, 8, 8)

    rec = MCC.main([f"--clip={_clip(tmp_path)}", f"--frames={d}", f"--out={tmp_path / 'o'}",
                    "--expect-frames=81", "--step=2"])
    assert rec["gradient_split_mid_frame"]["frame_index"] == 40
    on_disk = json.loads(
        (tmp_path / "o" / "cascade_decode_compare.json").read_text(encoding="utf-8"))
    assert on_disk["gradient_split_mid_frame"]["frame_index"] == 40


def test_the_count_andon_still_fires_first(tmp_path, monkeypatch):
    """The guard the other way: the shape check must not have displaced the count check."""
    d, frames = _sources(tmp_path, 5)
    _stub(monkeypatch, frames, 32, 32)
    with pytest.raises(MCC.ClipCountError):
        MCC.main([f"--clip={_clip(tmp_path)}", f"--frames={d}", f"--out={tmp_path / 'o'}",
                  "--expect-frames=81"])
