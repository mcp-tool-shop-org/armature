"""`pack_pose_pack` — one lossless animated WebP instead of 65 uploads.

The bridge only works if the encoding is lossless, so the tests are about exactly that and
about the two silent failure modes around it: frames read in the wrong order, and frames of
mixed size (which `LoadImage`'s PIL path SKIPS rather than errors on, arriving as a short
batch).

The fixtures use one-pixel-wide coloured lines on black, because that is what the real
frames are and it is the hardest thing for a codec to keep: a lossy encoder smears a
1-px stick immediately, where it might leave a large flat shape untouched.
"""

import os

import numpy as np
import pytest

from armature_core.errors import ArmatureError, GateRRoundTrip

import pack_pose_pack as PP


def stick_frame(width=64, height=48, offset=0):
    """A frame in the real subject's shape: thin bright lines on a zeroed-black canvas."""
    a = np.zeros((height, width, 3), np.uint8)
    a[10 + offset % 5, :] = (255, 0, 0)
    a[:, 20 + offset % 7] = (0, 85, 255)
    a[30, 5 + offset % 9] = (100, 100, 0)
    return a


def test_lossless_roundtrip_on_one_pixel_sticks(tmp_path):
    frames = [stick_frame(offset=i) for i in range(6)]
    dst = os.path.join(str(tmp_path), "p.webp")
    PP.write_pack(frames, dst, 16, 'webp')
    back = PP.read_pack(dst)
    assert len(back) == len(frames)
    for a, b in zip(frames, back):
        assert np.array_equal(a, b)


def test_the_gate_would_actually_fire_on_a_lossy_pack(tmp_path):
    """The check that the check works. A lossy WebP of these frames must NOT survive
    Gate R — otherwise the gate is decoration and the pack could smear the palette."""
    from PIL import Image
    frames = [stick_frame(offset=i) for i in range(4)]
    dst = os.path.join(str(tmp_path), "lossy.webp")
    imgs = [Image.fromarray(a, "RGB") for a in frames]
    imgs[0].save(dst, format="WEBP", save_all=True, append_images=imgs[1:],
                 lossless=False, quality=60, duration=62, loop=0)
    back = PP.read_pack(dst)
    with pytest.raises(GateRRoundTrip):
        from armature_core import gates
        gates.gate_r_round_trip(frames, back)


def test_frame_order_is_numeric_not_lexical(tmp_path):
    """A pose video in the wrong order still looks like a performance."""
    d = str(tmp_path)
    for i in (0, 2, 9, 10, 100):
        with open(os.path.join(d, f"{i:05d}.png"), "wb") as fh:
            fh.write(b"")
    got = [int(os.path.splitext(os.path.basename(p))[0]) for p in PP.frame_paths(d)]
    assert got == [0, 2, 9, 10, 100]


def test_unpadded_names_still_sort_numerically(tmp_path):
    """Zero padding makes lexical and numeric agree; this is the case where they do not."""
    d = str(tmp_path)
    for name in ("2.png", "10.png", "1.png"):
        with open(os.path.join(d, name), "wb") as fh:
            fh.write(b"")
    got = [int(os.path.splitext(os.path.basename(p))[0]) for p in PP.frame_paths(d)]
    assert got == [1, 2, 10]


def test_an_empty_directory_raises_rather_than_packing_nothing(tmp_path):
    with pytest.raises(ArmatureError):
        PP.frame_paths(str(tmp_path))


def test_mixed_frame_sizes_raise_before_the_pack(tmp_path):
    """LoadImage's PIL path skips any frame whose size differs from the first, so a mixed
    pack arrives as a SHORT batch with nothing erroring — and a short pose video is padded
    by repeating its last frame, which reads as a performance that freezes."""
    import pack_pose_pack as _PP
    from PIL import Image
    d = str(tmp_path)
    Image.fromarray(stick_frame(64, 48), "RGB").save(os.path.join(d, "00000.png"))
    Image.fromarray(stick_frame(32, 48), "RGB").save(os.path.join(d, "00001.png"))
    with pytest.raises(ArmatureError) as exc:
        _PP.load_frames(_PP.frame_paths(d))
    assert "same size" in str(exc.value)


def test_frame_count_survives_the_pack(tmp_path):
    """The count is the quantity Gate B compares against; a pack that dropped one would
    otherwise arrive as a 64-frame batch padded back to 65 by the conditioning node."""
    frames = [stick_frame(offset=i) for i in range(65)]
    dst = os.path.join(str(tmp_path), "p65.webp")
    PP.write_pack(frames, dst, 16, 'webp')
    assert len(PP.read_pack(dst)) == 65


def test_apng_is_lossless_too_and_is_the_default(tmp_path):
    """APNG is the default because Comfy Cloud's upload endpoint refused animated WebP with
    422 INVALID_IMAGE (measured 2026-08-12). It has to be just as lossless."""
    frames = [stick_frame(offset=i) for i in range(8)]
    dst = os.path.join(str(tmp_path), "p.apng.png")
    PP.write_pack(frames, dst, 16, "apng")
    back = PP.read_pack(dst)
    assert len(back) == len(frames)
    for a, b in zip(frames, back):
        assert np.array_equal(a, b)


def test_both_pack_formats_survive_sixtyfive_frames(tmp_path):
    """65 is the shot's own length; a pack that dropped one would arrive as a 64-frame
    batch that the conditioning node pads back to 65 by repeating the last frame."""
    frames = [stick_frame(offset=i) for i in range(65)]
    for fmt, name in (("apng", "a.apng.png"), ("webp", "w.webp")):
        dst = os.path.join(str(tmp_path), name)
        PP.write_pack(frames, dst, 16, fmt)
        assert len(PP.read_pack(dst)) == 65
