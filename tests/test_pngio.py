"""The PNG writer, read back by Pillow.

Deliberately checked by a *different* implementation: a writer read back by its own
reader has been checked against nothing. Pillow is not in Blender's python, which is why
the writer exists — and is exactly why it is the right decoder here.
"""

import numpy as np
import pytest
from PIL import Image

from armature_core import pngio


def test_gray8_round_trip(tmp_path):
    rng = np.random.default_rng(0)
    arr = rng.integers(0, 256, size=(37, 53), dtype=np.uint8)
    path = tmp_path / "g.png"
    pngio.write_png(str(path), arr, bit_depth=8)
    back = np.array(Image.open(path))
    assert back.dtype == np.uint8 and back.shape == arr.shape
    assert np.array_equal(back, arr)


def test_rgb8_round_trip(tmp_path):
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 256, size=(29, 41, 3), dtype=np.uint8)
    path = tmp_path / "c.png"
    pngio.write_png(str(path), arr, bit_depth=8)
    back = np.array(Image.open(path).convert("RGB"))
    assert np.array_equal(back, arr)


def test_bit1_round_trip_including_a_width_that_is_not_a_byte_multiple(tmp_path):
    """Row padding is where a 1-bit writer goes wrong; 53 px is 6 bytes + 5 bits."""
    rng = np.random.default_rng(2)
    arr = (rng.random((23, 53)) > 0.5).astype(np.uint8)
    path = tmp_path / "m.png"
    pngio.write_png(str(path), arr, bit_depth=1)
    img = Image.open(path)
    assert img.mode == "1"
    back = np.array(img).astype(np.uint8)
    assert np.array_equal(back, arr)


def test_orientation_row_zero_is_the_top(tmp_path):
    """A vertical flip is invisible on a symmetric subject and wrong everywhere else."""
    arr = np.zeros((16, 8), dtype=np.uint8)
    arr[0:4, :] = 255  # top band
    path = tmp_path / "o.png"
    pngio.write_png(str(path), arr, bit_depth=8)
    back = np.array(Image.open(path))
    assert back[0:4].mean() == 255 and back[12:16].mean() == 0


def test_rejects_wrong_dtype(tmp_path):
    with pytest.raises(ValueError):
        pngio.write_png(str(tmp_path / "x.png"), np.zeros((4, 4), dtype=np.float32), 8)


def test_rejects_non_binary_array_at_one_bit(tmp_path):
    with pytest.raises(ValueError):
        pngio.write_png(str(tmp_path / "x.png"), np.full((4, 4), 7, dtype=np.uint8), 1)


def test_writer_is_deterministic(tmp_path):
    """G3 compares pixels, not bytes — but a writer that emits different bytes for the
    same array would put noise into every hash in the manifest."""
    arr = np.arange(64, dtype=np.uint8).reshape(8, 8)
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    pngio.write_png(str(a), arr, 8)
    pngio.write_png(str(b), arr, 8)
    assert a.read_bytes() == b.read_bytes()
