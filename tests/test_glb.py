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
    assert glb.gate_atlas_untouched(a, b)["verdict"].startswith("2 of 2 embedded")


def test_a_file_that_is_not_a_glb_raises_rather_than_returning_nothing(tmp_path):
    """The class moved from a bare `ValueError` to `MalformedGLB` (F-b725f541): every
    refusal in `read_chunks` is the same "this container cannot be read" refusal, and three
    of them were nameless — which also put them outside the `ArmatureError` family the halt
    contract discriminates on. The clause is pinned as well, because `MalformedGLB` is now
    raised from thirteen sites and a bare class name cannot tell them apart."""
    bad = tmp_path / "bad.glb"
    bad.write_bytes(b"this is not a container")
    with pytest.raises(glb.MalformedGLB, match=r"not a GLB \(magic"):
        glb.read_chunks(str(bad))


def _glb_mixed(path, blob, data_payload):
    """A GLB carrying one bufferView image (hashable) and one data-URI image (not)."""
    binary = blob + b"\x00" * (-len(blob) % 4)
    js = json.dumps({
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(blob)}],
        "images": [{"bufferView": 0, "mimeType": "image/png", "name": "atlas"},
                   {"uri": "data:image/png;base64," + data_payload,
                    "mimeType": "image/png", "name": "decal"}],
    }).encode("utf-8")
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", glb.GLB_MAGIC, 2, total))
        fh.write(struct.pack("<II", len(js), glb.CHUNK_JSON))
        fh.write(js)
        fh.write(struct.pack("<II", len(binary), glb.CHUNK_BIN))
        fh.write(binary)
    return path


def test_an_unhashable_source_image_is_not_certified_by_silence(tmp_path):
    """`embedded_images` sets sha256=None for a data URI or an external uri, and the
    vacuity guard fired only when NO image was hashable - a PARTIAL exclusion was silent.
    Measured: a pair each carrying one identical bufferView image and one data-URI image
    that DIFFERED passed with "1 embedded image(s) byte-identical through the route", a
    count rather than a coverage (F-ac4bdb63)."""
    a = _glb_mixed(str(tmp_path / "src.glb"), ATLAS, "AAAA")
    b = _glb_mixed(str(tmp_path / "out.glb"), ATLAS, "BBBBCCCC")
    with pytest.raises(glb.GateAtlasUntouched) as exc:
        glb.gate_atlas_untouched(a, b)
    assert "cannot be hashed" in str(exc.value)
    assert exc.value.evidence["n_images_in_source"] == 2
    assert exc.value.evidence["n_source_images_hashable"] == 1


def test_the_verdict_states_coverage_not_only_a_count(tmp_path):
    a = _glb(str(tmp_path / "src.glb"), ATLAS, images=2)
    b = _glb(str(tmp_path / "out.glb"), ATLAS, images=2)
    v = glb.gate_atlas_untouched(a, b)["verdict"]
    assert v.startswith("2 of 2 embedded")
    assert "0 unhashable" in v


def _glb_blobs(path, blobs, mime="image/png"):
    """A GLB carrying exactly the blobs given, in order — duplicates allowed.

    `_glb` derives its second image from the first (`image_bytes[::-1]`), so it cannot
    build the pair this fixture needs: a source that embeds the SAME image twice.
    """
    binary = b""
    views, image_defs = [], []
    for i, blob in enumerate(blobs):
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(blob)})
        image_defs.append({"bufferView": i, "mimeType": mime, "name": f"img{i}"})
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


def test_a_source_image_embedded_twice_is_not_satisfied_by_one_export_copy(tmp_path):
    """Membership is not multiplicity (F-937f8a81).

    Source embeds A twice; the export embeds A once and a different image B. The count
    clause does not fire (2 == 2) and neither image is unhashable, so a membership test
    reports "2 of 2 embedded image(s) byte-identical through the route" over an export
    that re-encoded one of them. The comparison is a multiset comparison.
    """
    A = ATLAS
    B = bytes(bytearray(ATLAS)[::-1]) + b"\x01"
    assert A != B
    src = _glb_blobs(str(tmp_path / "src.glb"), [A, A])
    out = _glb_blobs(str(tmp_path / "out.glb"), [A, B])
    with pytest.raises(glb.GateAtlasUntouched) as exc:
        glb.gate_atlas_untouched(src, out)
    ev = exc.value.evidence
    ha, hb = hashlib.sha256(A).hexdigest(), hashlib.sha256(B).hexdigest()
    assert ev["missing_hash_counts"] == {ha: 1}
    assert ev["source_hash_counts"] == {ha: 2}
    assert ev["export_hash_counts"] == {ha: 1, hb: 1}
    assert "re-encoded or resampled" in str(exc.value)


def test_a_source_image_embedded_twice_passes_when_both_copies_arrive(tmp_path):
    """The multiset comparison must not fire on a correct export — including a reordered
    one, which `test_the_gate_does_not_care_about_image_ORDER` already pins for the
    distinct case."""
    A, B = ATLAS, bytes(bytearray(ATLAS)[::-1]) + b"\x01"
    src = _glb_blobs(str(tmp_path / "src.glb"), [A, A, B])
    out = _glb_blobs(str(tmp_path / "out.glb"), [B, A, A])
    assert glb.gate_atlas_untouched(src, out)["verdict"].startswith("3 of 3 embedded")


def test_the_atlas_gate_carries_its_own_id_in_the_evidence(tmp_path):
    """F-f2f42e4a's family: `stage_render` records the halt as one `STAGE_RENDER_HALT
    <json>` line carrying `gate` and `evidence` as separate keys (CORRECTED wave 14: the
    two-line `GATE_FAILURE` / `GATE_EVIDENCE` receipt this named was deleted with the old
    handler), and a reader that keeps only the evidence dict had no id at all. Every other gate in assembly.py, turnaround.py, startframe.py, resample.py
    and lift_solve.py puts "gate" in the evidence; this one did not."""
    a = _glb(str(tmp_path / "src.glb"), ATLAS)
    b = _glb(str(tmp_path / "out.glb"), ATLAS)
    assert glb.gate_atlas_untouched(a, b)["gate"] == "ATLAS"
    c = _glb(str(tmp_path / "bad.glb"), ATLAS, images=0)
    with pytest.raises(glb.GateAtlasUntouched) as exc:
        glb.gate_atlas_untouched(a, c)
    assert exc.value.evidence["gate"] == exc.value.gate == "ATLAS"


# ---------------------------------------------------------------------------
# F-edbd890a: unchecked container reads
# ---------------------------------------------------------------------------


def _glb_raw(path, js_dict, binary):
    """A GLB carrying exactly the JSON and BIN bytes given — malformations included.

    `_glb` and `_glb_blobs` always write a self-consistent container, so neither can
    build the files these cases need: a bufferView index that is not an index, and a
    bufferView whose declared range runs past the BIN chunk.
    """
    js = json.dumps(js_dict).encode("utf-8")
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", glb.GLB_MAGIC, 2, total))
        fh.write(struct.pack("<II", len(js), glb.CHUNK_JSON))
        fh.write(js)
        fh.write(struct.pack("<II", len(binary), glb.CHUNK_BIN))
        fh.write(binary)
    return path


def _one_view_doc(byte_offset, byte_length, buffer_view_ref):
    return {"asset": {"version": "2.0"},
            "buffers": [{"byteLength": 64}],
            "bufferViews": [{"buffer": 0, "byteOffset": byte_offset,
                             "byteLength": byte_length}],
            "images": [{"bufferView": buffer_view_ref, "mimeType": "image/png",
                        "name": "atlas"}]}


def test_a_bufferView_index_past_the_table_is_named_not_an_IndexError(tmp_path):
    """`views[image['bufferView']]` indexed a list built from the file with a value taken
    straight out of the same file (F-edbd890a)."""
    p = _glb_raw(str(tmp_path / "a.glb"), _one_view_doc(0, 16, 7), b"\x00" * 16)
    with pytest.raises(glb.MalformedGLB) as exc:
        glb.embedded_images(p)
    assert "bufferView 7" in str(exc.value)
    assert "1 bufferView" in str(exc.value)


def test_a_negative_bufferView_index_is_refused_rather_than_hashing_another_view(tmp_path):
    """A negative index is a valid Python index and an invalid glTF one: it hashed a
    DIFFERENT bufferView and reported the digest as this image's."""
    doc = {"asset": {"version": "2.0"},
           "buffers": [{"byteLength": 32}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 16},
                           {"buffer": 0, "byteOffset": 16, "byteLength": 16}],
           "images": [{"bufferView": -1, "mimeType": "image/png", "name": "atlas"}]}
    p = _glb_raw(str(tmp_path / "a.glb"), doc, bytes(range(32)))
    with pytest.raises(glb.MalformedGLB) as exc:
        glb.embedded_images(p)
    assert "bufferView -1" in str(exc.value)


def test_a_bufferView_running_past_the_bin_chunk_raises_rather_than_hashing_short(tmp_path):
    """`binary[start:start + length]` is a Python slice, so an over-declared range yielded
    a SHORT blob whose sha256 was reported as though it were the whole image — and Gate
    ATLAS compares hashes on both sides, so an identical truncation cancels and the gate
    certifies bytes neither file contains."""
    p = _glb_raw(str(tmp_path / "a.glb"), _one_view_doc(0, 4096, 0), b"\x00" * 16)
    with pytest.raises(glb.MalformedGLB) as exc:
        glb.embedded_images(p)
    msg = str(exc.value)
    assert "the BIN chunk does not contain" in msg
    assert "4096" in msg and "16" in msg


def test_the_atlas_gate_halts_on_a_truncating_container_instead_of_certifying_it(tmp_path):
    """The gate's own failure mode: source and export both over-declare by the same
    amount, both hash the same short blob, and the verdict reads byte-identical."""
    doc = _one_view_doc(0, 4096, 0)
    a = _glb_raw(str(tmp_path / "src.glb"), doc, b"\x00" * 16)
    b = _glb_raw(str(tmp_path / "out.glb"), doc, b"\x00" * 16)
    with pytest.raises(glb.MalformedGLB, match=r"the BIN chunk does not contain"):
        glb.gate_atlas_untouched(a, b)


def test_a_bufferView_with_no_byteLength_is_named(tmp_path):
    doc = {"asset": {"version": "2.0"},
           "buffers": [{"byteLength": 16}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0}],
           "images": [{"bufferView": 0, "mimeType": "image/png", "name": "atlas"}]}
    p = _glb_raw(str(tmp_path / "a.glb"), doc, b"\x00" * 16)
    with pytest.raises(glb.MalformedGLB) as exc:
        glb.embedded_images(p)
    assert "byteLength" in str(exc.value)


def test_a_truncated_bin_chunk_is_refused_by_the_reader(tmp_path):
    """`fh.read(length)` returns what is there. A chunk header declaring more than the
    file holds gave a silently short BIN chunk, and every slice off it was then short.

    **The header total is honest here and the CHUNK lies** — corrected 2026-09-04 with
    F-b725f541. The original fixture declared a header `total` of `12 + 8 + len(js) + 8 +
    4096` over a file holding 16 bytes of BIN, so it carried TWO defects at once; the new
    `declared_total` clause catches that one first and this test would have gone green on a
    different refusal than the one its name claims. An internally inconsistent container
    whose top-level length is correct is what isolates the short-body clause, and the
    stale-`total` case gets its own test below.
    """
    js = json.dumps(_one_view_doc(0, 16, 0)).encode("utf-8")
    js += b" " * (-len(js) % 4)
    path = str(tmp_path / "trunc.glb")
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", glb.GLB_MAGIC, 2, 12 + 8 + len(js) + 8 + 16))
        fh.write(struct.pack("<II", len(js), glb.CHUNK_JSON))
        fh.write(js)
        fh.write(struct.pack("<II", 4096, glb.CHUNK_BIN))
        fh.write(b"\x00" * 16)
    with pytest.raises(glb.MalformedGLB, match=r"the container is truncated") as exc:
        glb.read_chunks(path)
    assert "4096" in str(exc.value) and "16" in str(exc.value)
    assert exc.value.evidence["clause"] == "short_chunk_body"


def test_a_well_formed_container_still_reads(tmp_path):
    """The guards bind in both directions: the happy path must not have moved."""
    p = _glb(str(tmp_path / "a.glb"), ATLAS, images=2)
    images = glb.embedded_images(p)
    assert [i["bytes"] for i in images] == [len(ATLAS), len(ATLAS)]
    assert images[0]["sha256"] == hashlib.sha256(ATLAS).hexdigest()


def _functions_subscripting(source, container_names):
    """Every function in `source` whose body subscripts one of `container_names`.

    Derived by walking the module's own AST — not a typed list — so a new unguarded read
    of the file's own tables joins the population the moment it is written.
    """
    import ast

    found = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Subscript)
                    and isinstance(sub.value, ast.Name)
                    and sub.value.id in container_names):
                found.add(node.name)
    return found


def test_every_read_of_the_containers_goes_through_the_one_checked_helper():
    """Census, derived by AST over glb.py: which functions subscript `views` or `binary`?

    Measured on this tree the answer must be exactly `_image_blob`, the helper that
    validates the index and the range before touching either. `embedded_images` used to
    index both directly (F-edbd890a); this census is what keeps a second such read from
    appearing without a check.
    """
    import inspect

    derived = _functions_subscripting(inspect.getsource(glb), {"views", "binary"})
    assert derived == {"_image_blob"}, (
        "container reads outside the checked helper: "
        + repr(sorted(derived - {"_image_blob"})))


def test_the_container_read_census_goes_red_on_an_unguarded_reader():
    """Prove the census can fail. The mutation adds a member without the property — a
    second function reading `views` — to a synthetic source, so nothing in the tree is
    weakened to demonstrate it."""
    mutated = (
        "def _image_blob(views, binary, image, index, path):\n"
        "    return binary[0:1]\n"
        "\n"
        "def sneaky(views, binary):\n"
        "    return views[0]\n"
    )
    derived = _functions_subscripting(mutated, {"views", "binary"})
    assert derived == {"_image_blob", "sneaky"}
    assert derived != {"_image_blob"}, "the census would not have caught the extra reader"


# ------------------------- wave 10: the other side of the `if`, and the header's two lies


def _glb_bytes(js_dict, binary, total=None, version=2):
    """The raw bytes of a GLB, so a test can cut them anywhere it likes."""
    js = json.dumps(js_dict).encode("utf-8")
    js += b" " * (-len(js) % 4)
    body = (struct.pack("<II", len(js), glb.CHUNK_JSON) + js
            + struct.pack("<II", len(binary), glb.CHUNK_BIN) + binary)
    if total is None:
        total = 12 + len(body)
    return struct.pack("<III", glb.GLB_MAGIC, version, total) + body


def _write(path, blob):
    with open(path, "wb") as fh:
        fh.write(blob)
    return str(path)


BLOB4 = b"\x01\x02\x03\x04"
DOC4 = {"asset": {"version": "2.0"},
        "buffers": [{"byteLength": 4}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 4}],
        "images": [{"bufferView": 0, "mimeType": "image/png", "name": "atlas"}]}


def test_the_intact_control_still_hashes_its_blob(tmp_path):
    """The direction all three refusals below must not break: this container is fine."""
    p = _write(tmp_path / "ok.glb", _glb_bytes(DOC4, BLOB4))
    assert glb.embedded_images(p)[0]["sha256"] == hashlib.sha256(BLOB4).hexdigest()


def test_a_file_that_ends_mid_chunk_header_raises_instead_of_breaking_out(tmp_path):
    """F-b725f541. The same truncation raised on one side of an `if` and was silent on the
    other: a short chunk BODY raised `MalformedGLB`, a short chunk HEADER took a bare
    `break` and `read_chunks` returned what it had. Measured on the wave-10 base with the
    final 12 bytes (the BIN header and its 4-byte payload) removed: it returned normally
    with `binary == b""` — an empty BIN chunk indistinguishable from a GLB that genuinely
    embeds nothing — while removing only the last 2 bytes raised.

    The header's `total` is rewritten to the truncated size so this fixture isolates the
    short-header branch rather than passing on the `declared_total` clause.
    """
    whole = _glb_bytes(DOC4, BLOB4)
    cut = whole[:-12] + b"\x00\x00\x00"      # 3 of the 8 bytes a chunk header needs
    cut = struct.pack("<III", glb.GLB_MAGIC, 2, len(cut)) + cut[12:]
    p = _write(tmp_path / "cut.glb", cut)
    with pytest.raises(glb.MalformedGLB, match=r"ends mid-chunk-header") as exc:
        glb.read_chunks(p)
    ev = exc.value.evidence
    assert ev["clause"] == "short_chunk_header"
    assert ev["bytes_read"] == 3 and ev["bytes_required"] == 8


def test_a_header_total_that_disagrees_with_the_file_is_refused(tmp_path):
    """The second unchecked value out of the same 12 bytes. Measured on the wave-10 base:
    a GLB whose `total` stopped just after the JSON chunk returned `binary = b""` from a
    100-byte file with no raise, because `while fh.tell() < total` simply never reached the
    BIN chunk. Under-declaring truncates the document silently; over-declaring is what a
    real truncation looks like from the outside."""
    whole = _glb_bytes(DOC4, BLOB4)
    short_total = len(whole) - 12
    under = struct.pack("<III", glb.GLB_MAGIC, 2, short_total) + whole[12:]
    with pytest.raises(glb.MalformedGLB, match=r"declares a total length") as exc:
        glb.read_chunks(_write(tmp_path / "under.glb", under))
    assert exc.value.evidence["clause"] == "declared_total_disagrees"
    assert exc.value.evidence["declared_total"] == short_total
    assert exc.value.evidence["file_size"] == len(whole)

    over = struct.pack("<III", glb.GLB_MAGIC, 2, len(whole) + 4096) + whole[12:]
    with pytest.raises(glb.MalformedGLB, match=r"declares a total length"):
        glb.read_chunks(_write(tmp_path / "over.glb", over))


def test_a_version_one_container_is_refused_by_name(tmp_path):
    """The third. `version` was unpacked at the top of `read_chunks` and never compared to
    2, so a glTF-1.0-era binary — a DIFFERENT chunk layout — was accepted and misread. A
    reader that produces a plausible wrong answer is the one failure this module exists to
    make impossible."""
    p = _write(tmp_path / "v1.glb", _glb_bytes(DOC4, BLOB4, version=1))
    with pytest.raises(glb.MalformedGLB, match=r"version 1 and this reader understands 2"
                       ) as exc:
        glb.read_chunks(p)
    assert exc.value.evidence["clause"] == "unsupported_version"


def test_every_refusal_this_reader_makes_is_one_named_class(tmp_path):
    """The family, derived rather than listed: no `raise` statement anywhere in `glb.py`
    names a class other than this module's own three.

    Before F-b725f541 three of them were bare `ValueError`s — shorter than a header, wrong
    magic, no JSON chunk — which is the same refusal wearing no name, and outside the
    `ArmatureError` family the halt contract discriminates on.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(glb))
    raised = sorted({(getattr(n.exc.func, "id", None) or getattr(n.exc.func, "attr", None))
                     for n in ast.walk(tree)
                     if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)})
    assert raised == ["GateAtlasUntouched", "MalformedGLB", "ReliftMismatch"], raised
