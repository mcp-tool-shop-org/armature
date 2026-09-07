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
  bit_depth=8, 3-D uint8 array (H,W,4)-> truecolour RGBA (color type 6)

Row 0 of the array is the TOP row of the image, which is PNG's own order. Blender's
`image.pixels` is bottom-up; the caller flips before it gets here.

RGBA (F-219a7aba): the alpha law's authored master is an (H,W,4) array; without color
type 6 this writer refused it (`unsupported_shape`) and every Blender-side RGBA export
had to stay on Blender's own encoder.

`read_png` (F-69a1f058) loads the same filter-0 gray/RGB/RGBA surfaces this writer
emits, so a core-side alpha/composite check after disk does not have to import Pillow.
Pillow remains the EXTERNAL_VERIFIER for the *writer*; the reader exists so the alpha
law path stays inside this module.
"""

import struct
import zlib

import numpy as np

from .errors import ArmatureError


class PngWriteError(ArmatureError):
    """This writer will not write the file it was asked for.

    A deliberate refusal, and the five that existed were bare `ValueError`s (F-9fab7829,
    wave 12). The 21-tool halt contract classifies on the `ArmatureError` family, so a
    refusal here was recorded as "FAILED — an unhandled error" at exit 1 inside a render,
    where the honest record is "REFUSED" at exit 2 naming the array that could not be
    written. Carries an `evidence` dict; a plain refusal writes `gate: None` + `andon` +
    `clause`.

    **It defines no `__init__` of its own** (rule 5, wave 16). It carried
    `self.evidence = evidence or {}`, which manufactured an empty dict for a refusal raised
    with a bare message: the halt line then printed `"evidence": {}` for a refusal that
    carried no receipt, so "no receipt" and "a receipt with nothing in it" became the same
    record. `armature_core.errors.ArmatureError` stores what it is passed and normalises
    nothing; the one exemption is `GateFailure`, whose clauses index into `ev` while they
    measure. A bare-message refusal from this class now reads `"evidence": null`, which is
    the honest record; a refusal that passes a dict is unchanged in both directions, and the
    dict the raising line passed is the object the halt handler reads.

    **EVERY refusal names the file** (F-08eaf630, wave 28). Five of the six carried no
    `path` at all and none of the six opened its message with one, while the sixth
    (`zero_dimension`) already carried the key — the file's own convention, unfinished.
    Measured on the call side: `stage_render.run_export` calls `write_png` three times
    inside its per-frame loop, writing `depth_perframe`, `depth_pershot` and `p3_diff`, so
    `"bit_depth=8 needs uint8, got float64"` identified neither the frame nor the channel
    nor the file among 3xN writes and the operator could not tell what was on disk without
    listing the output tree by hand. Every message now opens `f"{path}: "` and
    every evidence dict carries `"path": str(path)`, which is the convention `glb.py`
    already applies to all sixteen of its `MalformedGLB` messages.
    """


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

COLOR_GRAY = 0
COLOR_RGB = 2
COLOR_RGBA = 6


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
    """Write `arr` to `path` as a PNG. Returns the number of bytes written.

    **A zero dimension is refused by name** (F-ae74741c, wave 12). The writer validated
    `arr.ndim`, the RGB channel count, the bit depth and the dtype, and never that `width`
    and `height` are non-zero — while the PNG spec requires both to be greater than zero in
    IHDR. Measured 2026-09-04: `write_png(p, np.zeros((0,64,3), uint8), bit_depth=8)` wrote
    65 bytes and returned 65 with no refusal; `np.zeros((64,0), uint8)` wrote 69. Both files
    exist on disk and PIL — the deliberately different reader this module's docstring names
    as its external verifier — raises `UnidentifiedImageError: cannot identify image file`
    on each. The contract line is "Returns the number of bytes written", so a caller
    checking the return saw success. (The `bit_depth=1` mask path failed loudly for an
    unrelated reason: `np.packbits` collapses first and `reshape` raises.)

    Every live caller derives H and W from a render resolution, so a zero dimension needs a
    zero-resolution render — the same door `startframe.gate_whole` left open until wave 12
    checked its own denominators. The consequence if it is ever reached is that a
    control-sequence frame is written, the write reports success, and the file is
    unreadable by every consumer including the upload path — discovered at submission
    rather than at write. The check sits ahead of `open()`, so a refusal leaves no file.
    """
    arr = np.asarray(arr)
    if arr.ndim == 2:
        channels, color_type = 1, COLOR_GRAY
    elif arr.ndim == 3 and arr.shape[2] == 3:
        channels, color_type = 3, COLOR_RGB
    elif arr.ndim == 3 and arr.shape[2] == 4:
        channels, color_type = 4, COLOR_RGBA
    else:
        raise PngWriteError(
            f"{path}: unsupported array shape {arr.shape}",
            {"gate": None, "andon": "PngWriteError", "clause": "unsupported_shape",
             "shape": list(arr.shape), "path": str(path)})

    if arr.shape[0] == 0 or arr.shape[1] == 0:
        raise PngWriteError(
            f"{path}: array shape {arr.shape} has a zero dimension, and IHDR requires both "
            f"width and height to be greater than zero. Writing it produces a structurally "
            f"invalid PNG that this function would report as a successful byte count, and "
            f"that every reader — PIL included — refuses to open",
            {"gate": None, "andon": "PngWriteError", "clause": "zero_dimension",
             "shape": list(arr.shape), "height": int(arr.shape[0]),
             "width": int(arr.shape[1]), "path": str(path)})

    if bit_depth == 1:
        if color_type != COLOR_GRAY:
            raise PngWriteError(
                f"{path}: bit_depth=1 is grayscale only, and this array is shape "
                f"{arr.shape}",
                {"gate": None, "andon": "PngWriteError", "clause": "bit1_not_grayscale",
                 "shape": list(arr.shape), "path": str(path)})
        if not np.isin(np.unique(arr), (0, 1)).all():
            _distinct = [int(v) for v in np.unique(arr)[:8]]
            raise PngWriteError(
                f"{path}: bit_depth=1 needs an array of only 0 and 1, and this one carries "
                f"{_distinct}",
                {"gate": None, "andon": "PngWriteError", "clause": "bit1_values",
                 "distinct_values": _distinct, "path": str(path)})
    elif bit_depth == 8:
        if arr.dtype != np.uint8:
            raise PngWriteError(
                f"{path}: bit_depth=8 needs uint8, got {arr.dtype}",
                {"gate": None, "andon": "PngWriteError", "clause": "bit8_dtype",
                 "dtype": str(arr.dtype), "path": str(path)})
    else:
        raise PngWriteError(
            f"{path}: unsupported bit depth {bit_depth}",
            {"gate": None, "andon": "PngWriteError", "clause": "unsupported_bit_depth",
             "bit_depth": bit_depth, "path": str(path)})

    height, width = arr.shape[0], arr.shape[1]
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)
    idat = zlib.compress(_raw_scanlines(arr, bit_depth, channels), 6)

    blob = _PNG_MAGIC + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(blob)
    return len(blob)


def _read_chunk(data, offset):
    if offset + 8 > len(data):
        raise PngWriteError(
            f"PNG truncated while reading chunk header at offset {offset}",
            {"gate": None, "andon": "PngWriteError", "clause": "png_truncated",
             "offset": offset})
    length = struct.unpack(">I", data[offset:offset + 4])[0]
    tag = data[offset + 4:offset + 8]
    start = offset + 8
    end = start + length
    crc_end = end + 4
    if crc_end > len(data):
        raise PngWriteError(
            f"PNG truncated while reading chunk {tag!r}",
            {"gate": None, "andon": "PngWriteError", "clause": "png_truncated",
             "tag": tag.decode("latin1", "replace"), "length": length})
    payload = data[start:end]
    want = struct.unpack(">I", data[end:crc_end])[0]
    got = zlib.crc32(tag + payload) & 0xFFFFFFFF
    if want != got:
        raise PngWriteError(
            f"PNG chunk {tag!r} CRC mismatch",
            {"gate": None, "andon": "PngWriteError", "clause": "png_crc_mismatch",
             "tag": tag.decode("latin1", "replace")})
    return tag, payload, crc_end


def read_png(path):
    """Read a filter-0 gray/RGB/RGBA PNG written by this module (F-69a1f058).

    Returns `(arr, color_type)` where `arr` is uint8 with shape (H,W), (H,W,3), or
    (H,W,4), and `color_type` is COLOR_GRAY / COLOR_RGB / COLOR_RGBA. Same path-named
    refusals as `write_png`. Interlaced, filtered, or exotic bit-depth files are refused
    rather than half-decoded — Pillow stays the EXTERNAL_VERIFIER for those.
    """
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        raise PngWriteError(
            f"{path}: cannot open for read ({exc})",
            {"gate": None, "andon": "PngWriteError", "clause": "png_unreadable",
             "path": str(path)}) from exc
    if not data.startswith(_PNG_MAGIC):
        raise PngWriteError(
            f"{path}: not a PNG (missing signature)",
            {"gate": None, "andon": "PngWriteError", "clause": "png_bad_signature",
             "path": str(path)})
    offset = len(_PNG_MAGIC)
    tag, ihdr, offset = _read_chunk(data, offset)
    if tag != b"IHDR" or len(ihdr) != 13:
        raise PngWriteError(
            f"{path}: first chunk is not a 13-byte IHDR",
            {"gate": None, "andon": "PngWriteError", "clause": "png_ihdr_missing",
             "path": str(path)})
    width, height, bit_depth, color_type, compression, filt, interlace = struct.unpack(
        ">IIBBBBB", ihdr)
    if compression != 0 or filt != 0 or interlace != 0:
        raise PngWriteError(
            f"{path}: only non-interlaced filter-method-0 zlib PNGs are readable here "
            f"(compression={compression}, filter={filt}, interlace={interlace})",
            {"gate": None, "andon": "PngWriteError", "clause": "png_unsupported_encoding",
             "path": str(path), "compression": compression, "filter": filt,
             "interlace": interlace})
    if width == 0 or height == 0:
        raise PngWriteError(
            f"{path}: IHDR width/height {width}x{height} has a zero dimension",
            {"gate": None, "andon": "PngWriteError", "clause": "zero_dimension",
             "path": str(path), "width": width, "height": height})
    if color_type == COLOR_GRAY:
        channels = 1
    elif color_type == COLOR_RGB:
        channels = 3
    elif color_type == COLOR_RGBA:
        channels = 4
    else:
        raise PngWriteError(
            f"{path}: color type {color_type} is not gray/RGB/RGBA",
            {"gate": None, "andon": "PngWriteError", "clause": "png_unsupported_color_type",
             "path": str(path), "color_type": color_type})
    if bit_depth not in (1, 8):
        raise PngWriteError(
            f"{path}: unsupported bit depth {bit_depth}",
            {"gate": None, "andon": "PngWriteError", "clause": "unsupported_bit_depth",
             "path": str(path), "bit_depth": bit_depth})
    if bit_depth == 1 and color_type != COLOR_GRAY:
        raise PngWriteError(
            f"{path}: bit_depth=1 is grayscale only",
            {"gate": None, "andon": "PngWriteError", "clause": "bit1_not_grayscale",
             "path": str(path)})

    idat = bytearray()
    while offset < len(data):
        tag, payload, offset = _read_chunk(data, offset)
        if tag == b"IDAT":
            idat.extend(payload)
        elif tag == b"IEND":
            break
    if not idat:
        raise PngWriteError(
            f"{path}: no IDAT chunks",
            {"gate": None, "andon": "PngWriteError", "clause": "png_no_idat",
             "path": str(path)})
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise PngWriteError(
            f"{path}: IDAT zlib decompress failed ({exc})",
            {"gate": None, "andon": "PngWriteError", "clause": "png_zlib_error",
             "path": str(path)}) from exc

    if bit_depth == 1:
        row_bytes = (width + 7) // 8
        expect = height * (1 + row_bytes)
        if len(raw) != expect:
            raise PngWriteError(
                f"{path}: bit1 scanline bytes {len(raw)} != expected {expect}",
                {"gate": None, "andon": "PngWriteError", "clause": "png_scanline_length",
                 "path": str(path)})
        rows = []
        for r in range(height):
            base = r * (1 + row_bytes)
            if raw[base] != 0:
                raise PngWriteError(
                    f"{path}: filter type {raw[base]} on row {r}; only filter 0 is read",
                    {"gate": None, "andon": "PngWriteError",
                     "clause": "png_unsupported_filter", "path": str(path),
                     "row": r, "filter_type": int(raw[base])})
            packed = np.frombuffer(raw[base + 1:base + 1 + row_bytes], dtype=np.uint8)
            bits = np.unpackbits(packed)[:width]
            rows.append(bits)
        arr = np.asarray(rows, dtype=np.uint8)
        return arr, COLOR_GRAY

    row_bytes = width * channels
    expect = height * (1 + row_bytes)
    if len(raw) != expect:
        raise PngWriteError(
            f"{path}: scanline bytes {len(raw)} != expected {expect}",
            {"gate": None, "andon": "PngWriteError", "clause": "png_scanline_length",
             "path": str(path), "got": len(raw), "expected": expect})
    rows = np.empty((height, width, channels), dtype=np.uint8)
    for r in range(height):
        base = r * (1 + row_bytes)
        if raw[base] != 0:
            raise PngWriteError(
                f"{path}: filter type {raw[base]} on row {r}; only filter 0 is read",
                {"gate": None, "andon": "PngWriteError",
                 "clause": "png_unsupported_filter", "path": str(path),
                 "row": r, "filter_type": int(raw[base])})
        rows[r] = np.frombuffer(
            raw[base + 1:base + 1 + row_bytes], dtype=np.uint8).reshape(width, channels)
    if channels == 1:
        return rows[:, :, 0], COLOR_GRAY
    return rows, color_type
