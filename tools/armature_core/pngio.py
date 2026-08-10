"""A dependency-free PNG writer.

Blender's bundled Python has numpy but no Pillow, and the exporter writes its 8-bit
consumer images from inside Blender. Rather than add a dependency to the render
process, the writer is ~60 lines of stdlib zlib.

Deliberately **not** paired with a reader here: the tests read these files back with
Pillow, a different implementation by different authors. A writer checked only by its own
reader has been checked against nothing (EXTERNAL_VERIFIER).

Supported, and only what the exporter uses (tripwire 7 — the exporter ships what the
experiments need, not what the format can do):

  bit_depth=1, 2-D uint8/bool array   -> grayscale, exact silhouette mask
  bit_depth=8, 2-D uint8 array        -> grayscale
  bit_depth=8, 3-D uint8 array (H,W,3)-> truecolour RGB

Row 0 of the array is the TOP row of the image, which is PNG's own order. Blender's
`image.pixels` is bottom-up; the caller flips before it gets here.
"""

import struct
import zlib

import numpy as np

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

COLOR_GRAY = 0
COLOR_RGB = 2


def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _raw_scanlines(arr, bit_depth, channels):
    """Serialise rows with PNG filter type 0 (None) — deterministic, no heuristics."""
    height, width = arr.shape[0], arr.shape[1]
    if bit_depth == 1:
        packed = np.packbits(arr.astype(bool), axis=1)  # MSB-first, rows padded
        rows = packed.reshape(height, -1)
    else:
        rows = arr.reshape(height, width * channels).astype(np.uint8, copy=False)
    out = bytearray()
    for r in range(height):
        out.append(0)
        out += rows[r].tobytes()
    return bytes(out)


def write_png(path, arr, bit_depth=8):
    """Write `arr` to `path` as a PNG. Returns the number of bytes written."""
    arr = np.asarray(arr)
    if arr.ndim == 2:
        channels, color_type = 1, COLOR_GRAY
    elif arr.ndim == 3 and arr.shape[2] == 3:
        channels, color_type = 3, COLOR_RGB
    else:
        raise ValueError(f"unsupported array shape {arr.shape}")

    if bit_depth == 1:
        if color_type != COLOR_GRAY:
            raise ValueError("bit_depth=1 is grayscale only")
        if not np.isin(np.unique(arr), (0, 1)).all():
            raise ValueError("bit_depth=1 needs an array of only 0 and 1")
    elif bit_depth == 8:
        if arr.dtype != np.uint8:
            raise ValueError(f"bit_depth=8 needs uint8, got {arr.dtype}")
    else:
        raise ValueError(f"unsupported bit depth {bit_depth}")

    height, width = arr.shape[0], arr.shape[1]
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)
    idat = zlib.compress(_raw_scanlines(arr, bit_depth, channels), 6)

    blob = _PNG_MAGIC + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(blob)
    return len(blob)
