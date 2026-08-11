"""The atlas gate — the promise the rigid-parts route was chosen for.

Consult #5 ranked the route partly on "the atlas survives with zero re-bake". That claim is
about **bytes**, not about how the texture looks: a visually identical re-encode still breaks
it. So these fixtures build GLB containers by hand and check the gate reads the image bytes
out of the container rather than trusting anything Blender reports.
"""

import hashlib
import json
import struct

import pytest

from armature_core import glb


def _glb(path, image_bytes, mime="image/png", name="atlas", images=1):
    """A minimal but real GLB: header, JSON chunk, BIN chunk, 4-byte aligned."""
    binary = b""
    views, image_defs = [], []
    for i in range(images):
        blob = image_bytes if i == 0 else image_bytes[::-1]
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(blob)})
        image_defs.append({"bufferView": i, "mimeType": mime, "name": f"{name}{i or ''}"})
        binary += blob + b"\x00" * (-len(blob) % 4)

    js = json.dumps({"asset": {"version": "2.0"},
                     "buffers": [{"byteLength": len(binary)}],
                     "bufferViews": views, "images": image_defs}).encode("utf-8")
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", glb.GLB_MAGIC, 2, total))
        fh.write(struct.pack("<II", len(js), glb.CHUNK_JSON))
        fh.write(js)
        fh.write(struct.pack("<II", len(binary), glb.CHUNK_BIN))
        fh.write(binary)
    return path


ATLAS = bytes(range(256)) * 8


def test_the_embedded_image_is_read_and_hashed_out_of_the_container(tmp_path):
    p = _glb(str(tmp_path / "a.glb"), ATLAS)
    images = glb.embedded_images(p)
    assert len(images) == 1
    assert images[0]["bytes"] == len(ATLAS)
    assert images[0]["sha256"] == hashlib.sha256(ATLAS).hexdigest()
    assert images[0]["mime_type"] == "image/png"


def test_the_gate_passes_when_the_image_survives_byte_for_byte(tmp_path):
    a = _glb(str(tmp_path / "src.glb"), ATLAS)
    b = _glb(str(tmp_path / "out.glb"), ATLAS)
    assert "byte-identical" in glb.gate_atlas_untouched(a, b)["verdict"]


def test_the_gate_fires_when_the_texture_was_re_encoded(tmp_path):
    """One byte different is a re-encode. It would be invisible on screen and it breaks the
    only claim this gate exists to protect."""
    # Flip one byte rather than substituting a chosen value: ATLAS is a full byte range, so
    # two earlier versions of this fixture "changed" a byte to the value it already held and
    # the test passed while comparing a file with itself.
    tweaked = bytearray(ATLAS)
    tweaked[100] ^= 0xFF
    assert bytes(tweaked) != ATLAS, "fixture is not actually different"

    a = _glb(str(tmp_path / "src.glb"), ATLAS)
    b = _glb(str(tmp_path / "out.glb"), bytes(tweaked))
    with pytest.raises(glb.GateAtlasUntouched) as exc:
        glb.gate_atlas_untouched(a, b)
    assert "re-encoded or resampled" in str(exc.value)


def test_the_gate_fires_when_the_export_dropped_the_image(tmp_path):
    a = _glb(str(tmp_path / "src.glb"), ATLAS)
    b = _glb(str(tmp_path / "out.glb"), ATLAS, images=0)
    with pytest.raises(glb.GateAtlasUntouched):
        glb.gate_atlas_untouched(a, b)


def test_the_gate_refuses_a_source_with_no_embedded_image(tmp_path):
    """Otherwise it is a check that cannot fail: nothing to compare reads as a pass."""
    a = _glb(str(tmp_path / "src.glb"), ATLAS, images=0)
    b = _glb(str(tmp_path / "out.glb"), ATLAS, images=0)
    with pytest.raises(glb.GateAtlasUntouched) as exc:
        glb.gate_atlas_untouched(a, b)
    assert "cannot fail" in str(exc.value)


def test_the_gate_does_not_care_about_image_ORDER(tmp_path):
    """Two images swapped between source and export is not a re-encode. Comparing ordered
    lists would fire on a correct export and send a session chasing a defect that is not
    there."""
    one, two = ATLAS, ATLAS[::-1]
    a = _glb(str(tmp_path / "src.glb"), one, images=2)
    b = _glb(str(tmp_path / "out.glb"), two, images=2)
    assert glb.gate_atlas_untouched(a, b)["verdict"].startswith("2 embedded")


def test_a_file_that_is_not_a_glb_raises_rather_than_returning_nothing(tmp_path):
    bad = tmp_path / "bad.glb"
    bad.write_bytes(b"this is not a container")
    with pytest.raises(ValueError):
        glb.read_chunks(str(bad))
