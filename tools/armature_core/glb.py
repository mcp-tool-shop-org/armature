"""Read a GLB container directly — enough to prove the texture atlas survived a route.

**Why the bytes and not the pixels.** This repo has a standing law that a file-hash mismatch
is not evidence a render changed, and that pixels are the contract for renders. For *this*
asset the contract runs the other way: the consult's ranked route promises **"the atlas
survives with zero re-bake"**, and the only thing that proves is that the embedded image
arrives byte for byte. A re-encode that is visually identical still breaks the promise,
because the promise was that nothing touched it. So here the image bytes ARE the contract,
and this module reads them out of the container rather than asking Blender what it thinks it
wrote.

Pure stdlib. No bpy, no numpy, no image decoding — it never has to understand PNG to hash it.
"""

import hashlib
import json
import math
import os
import struct
from collections import Counter

from .errors import ArmatureError, GateFailure

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


class MalformedGLB(ArmatureError):
    """The container declares something the file does not contain.

    **It subclassed `ValueError` and no longer does** (F-ba21426c's family, corrected
    2026-09-04). The old docstring's reason was "`read_chunks` already refused unreadable
    containers that way" — which was the defect, not the justification: a `ValueError`
    sits outside `ArmatureError`, so the ONE halt contract every tool runs recorded all
    six of these refusals as "FAILED — an unhandled error" at exit 1 rather than as
    "REFUSED" at exit 2, and `evidence_dicts_missing` examined none of them. The family
    was derived by an AST walk of the class hierarchy under `tools/` (three members:
    `walk.WalkError`, `framing.FramingError` and this one) and all three were rebased in
    one commit. It carries an optional `evidence` dict for the same reason
    `FramingError` now does.

    Why the module needs it (F-edbd890a). Every value this reader indexes with comes out
    of the same file it is reading, and two of those reads were unchecked. `views[ref]`
    took `image["bufferView"]` straight from the JSON chunk: past the end that is an
    `IndexError` with no id, and NEGATIVE it is a perfectly legal Python index that
    silently hashes a different bufferView and reports the digest as this image's.
    `binary[start:start + length]` is a Python slice, so a bufferView whose declared range
    runs past the BIN chunk yields a SHORT blob whose sha256 is computed and reported as
    though it were the whole image. Gate ATLAS compares hashes on both sides, so a
    truncation identical in source and export CANCELS: the gate reports "byte-identical
    through the route" over bytes that neither file actually contains. The promise the
    gate exists for is about the bytes, so a reader that can invent them is the one place
    the promise cannot be repaired downstream.

    **Every refusal in `read_chunks` is one of these now** (F-b725f541). Three of them were
    bare `ValueError`s — shorter than a header, wrong magic, no JSON chunk — which is the
    same "this container cannot be read" refusal wearing no name at all.

    **A refusal's evidence names `gate` explicitly as `None`.** Now that this class is in
    the family, `tests/test_gates.evidence_dicts_missing` examines every raise here that
    carries a dict, and it asks for `gate` and `andon`. A refusal is not an andon and has
    no gate id, so the honest answer is written down rather than left absent: the receipt
    line reads "REFUSED" with `gate` null and the class name under `andon`, which is a
    different fact from the crash line it used to read (outcome "FAILED", `gate` null
    because nothing knew what had happened).

    **It defines no `__init__` of its own** (rule 5, wave 16). It carried
    `self.evidence = evidence or {}`, which manufactured an empty dict for a refusal raised
    with a bare message: the halt line then printed `"evidence": {}` for a refusal that
    carried no receipt, so "no receipt" and "a receipt with nothing in it" became the same
    record. `armature_core.errors.ArmatureError` stores what it is passed and normalises
    nothing; the one exemption is `GateFailure`, whose clauses index into `ev` while they
    measure. A bare-message refusal from this class now reads `"evidence": null`, which is
    the honest record; a refusal that passes a dict is unchanged in both directions, and the
    dict the raising line passed is the object the halt handler reads.
    """


class GateAtlasUntouched(GateFailure):
    """Arm (c)'s andon on the promise the route was chosen for.

    The rigid-parts route was ranked first partly because bisect preserves UVs and the
    atlas therefore needs no re-bake — a claim the advisor calibrated on this very mesh
    before commissioning the arm (298,366 far-from-cut faces with byte-identical UVs).
    **Nothing else in the pipeline would notice if the exporter silently re-encoded the
    texture.** The GLB would load, the parts would articulate, every other gate would pass,
    and the 4096 atlas the studio paid for would have been through a lossy round trip.
    """

    gate = "ATLAS"


def read_chunks(path):
    """(json_dict, bin_bytes) from a GLB, or raise on a container this cannot read.

    **The same truncation used to raise on one side of an `if` and be silent on the
    other** (F-b725f541). A chunk whose BODY was short raised; a chunk whose 8-byte
    HEADER was short took a bare `break` and this function returned whatever had been read
    so far. Measured on the wave-10 base, on a synthetic GLB carrying a 4-byte BIN chunk:
    intact, `embedded_images` hashed the blob; with the final 12 bytes removed (the BIN
    header and its payload) `read_chunks` returned NORMALLY with `binary = b""` and no
    raise, while removing only the last 2 bytes raised. An empty BIN chunk is
    indistinguishable from a GLB that genuinely embeds nothing, which is the one thing a
    reader whose output is a byte-for-byte promise may not invent.

    Two further values came out of the same header and were never checked: the declared
    `total` was never compared with the file's real size (measured: a GLB whose `total`
    stopped just after the JSON chunk returned `binary = b""` from a 100-byte file with no
    raise), and `version` was unpacked and never compared to 2, so a glTF-1.0-era binary —
    a different chunk layout — was accepted and misread.

    Downstream cover was partial rather than absent: for a GLB declaring a bufferView
    image, `_image_blob`'s range clause fires one layer down, and `gate_atlas_untouched`
    refuses a source with no hashable image. That is cover on the production path
    (`rig_parts.py::main`, which calls `glb.gate_atlas_untouched`), not on this public
    function, and this is where the promise cannot be repaired.
    """
    declared_size = os.path.getsize(path)
    with open(path, "rb") as fh:
        header = fh.read(12)
        if len(header) < 12:
            raise MalformedGLB(
                f"{path}: shorter than a GLB header - it holds {len(header)} of the 12 "
                f"bytes every GLB begins with",
                {"gate": None, "andon": "MalformedGLB", "clause": "short_header",
                 "bytes_read": len(header), "bytes_required": 12, "file_size": declared_size})
        magic, version, total = struct.unpack("<III", header)
        if magic != GLB_MAGIC:
            raise MalformedGLB(
                f"{path}: not a GLB (magic {magic:#x}, expected {GLB_MAGIC:#x})",
                {"gate": None, "andon": "MalformedGLB", "clause": "bad_magic",
                 "magic": magic, "expected_magic": GLB_MAGIC})
        if version != 2:
            raise MalformedGLB(
                f"{path}: the container declares glTF binary version {version} and this "
                f"reader understands 2. Version 1 lays its chunks out differently, so "
                f"reading it as a version-2 container does not fail - it produces a "
                f"plausible wrong answer, which is the only kind this module must not give",
                {"gate": None, "andon": "MalformedGLB", "clause": "unsupported_version",
                 "version": version, "supported_version": 2})
        if total != declared_size:
            raise MalformedGLB(
                f"{path}: the header declares a total length of {total} bytes and the file "
                f"holds {declared_size}. Under-declaring stops the chunk loop early and "
                f"returns a partial document with no raise; over-declaring runs it off the "
                f"end. Either way the container and the file disagree about what this file "
                f"is",
                {"gate": None, "andon": "MalformedGLB", "clause": "declared_total_disagrees",
                 "declared_total": total, "file_size": declared_size})
        js, binary = None, b""
        while fh.tell() < total:
            at = fh.tell()
            head = fh.read(8)
            if len(head) < 8:
                raise MalformedGLB(
                    f"{path}: the file ends mid-chunk-header at offset {at} - it holds "
                    f"{len(head)} of the 8 bytes a chunk header needs, while the container "
                    f"declares {total} bytes in total. This branch used to `break` and "
                    f"return what had been read so far, which is a partial document "
                    f"indistinguishable from a complete one",
                    {"gate": None, "andon": "MalformedGLB", "clause": "short_chunk_header",
                     "offset": at, "bytes_read": len(head), "bytes_required": 8,
                     "declared_total": total, "file_size": declared_size})
            length, kind = struct.unpack("<II", head)
            data = fh.read(length)
            if len(data) < length:
                raise MalformedGLB(
                    f"{path}: chunk {kind:#x} declares {length} bytes and the file holds "
                    f"{len(data)} - the container is truncated, and every read off a "
                    f"short chunk is short without saying so",
                    {"gate": None, "andon": "MalformedGLB", "clause": "short_chunk_body",
                     "chunk_kind": kind, "declared_length": length,
                     "bytes_read": len(data), "offset": at})
            if kind == CHUNK_JSON:
                js = json.loads(data.decode("utf-8"))
            elif kind == CHUNK_BIN:
                binary = data
        if js is None:
            raise MalformedGLB(
                f"{path}: no JSON chunk - a GLB without one declares nothing at all",
                {"gate": None, "andon": "MalformedGLB", "clause": "no_json_chunk",
                 "declared_total": total, "file_size": declared_size})
        return js, binary


def _image_blob(views, binary, image, index, path):
    """The bytes one bufferView-stored image declares, or raise naming the declaration.

    **Every read of `views` and `binary` in this module happens here** — that is the point
    of the helper, and
    `tests/test_glb.py::test_every_read_of_the_containers_goes_through_the_one_checked_helper`
    derives the population by walking this module's AST for subscripts of either name and
    asserts the answer is this function alone. A second
    unchecked reader therefore cannot be added quietly.

    The three refusals correspond to the three ways the file can lie about itself: a
    `bufferView` that is not an index into the table it names, a view with no declared
    length, and a view whose range runs past the BIN chunk. See `MalformedGLB`.
    """
    ref = image["bufferView"]
    if isinstance(ref, bool) or not isinstance(ref, int):
        raise MalformedGLB(
            f"{path}: image {index} names bufferView {ref!r}, which is not an index",
            {"gate": None, "andon": "MalformedGLB", "clause": "bufferview_not_an_index",
             "image_index": index, "bufferView": repr(ref), "path": str(path)})
    if ref < 0 or ref >= len(views):
        raise MalformedGLB(
            f"{path}: image {index} names bufferView {ref} and the container declares "
            f"{len(views)} bufferView(s) - a negative index is a legal Python index and "
            f"would have hashed a different view",
            {"gate": None, "andon": "MalformedGLB", "clause": "bufferview_out_of_range",
             "image_index": index, "bufferView": ref, "n_views": len(views),
             "path": str(path)})
    view = views[ref]
    if "byteLength" not in view:
        raise MalformedGLB(
            f"{path}: image {index} names bufferView {ref}, which declares no byteLength, "
            f"so there is no range to hash",
            {"gate": None, "andon": "MalformedGLB", "clause": "bufferview_no_bytelength",
             "image_index": index, "bufferView": ref, "path": str(path)})
    start = int(view.get("byteOffset", 0))
    length = int(view["byteLength"])
    if start < 0 or length < 0:
        raise MalformedGLB(
            f"{path}: image {index} names bufferView {ref} with byteOffset {start} and "
            f"byteLength {length}; neither may be negative",
            {"gate": None, "andon": "MalformedGLB", "clause": "bufferview_negative_range",
             "image_index": index, "bufferView": ref, "byteOffset": start,
             "byteLength": length, "path": str(path)})
    if start + length > len(binary):
        raise MalformedGLB(
            f"{path}: image {index} declares bytes [{start}, {start + length}) and the "
            f"BIN chunk does not contain them - it holds {len(binary)} bytes. Slicing "
            f"anyway hashes a short blob and reports it as the whole image; a truncation "
            f"identical on both sides of Gate ATLAS would cancel and certify bytes the "
            f"files do not carry. This is a broken export, not a re-encode",
            {"gate": None, "andon": "MalformedGLB", "clause": "bufferview_past_bin_chunk",
             "image_index": index, "bufferView": ref, "byteOffset": start,
             "byteLength": length, "bin_bytes": len(binary), "path": str(path)})
    return binary[start:start + length]


def embedded_images(path):
    """Every embedded image, with its sha256. Keyed by index so order changes are visible."""
    js, binary = read_chunks(path)
    views = js.get("bufferViews") or []
    out = []
    for i, image in enumerate(js.get("images") or []):
        rec = {"index": i, "name": image.get("name"), "mime_type": image.get("mimeType")}
        if "bufferView" in image:
            blob = _image_blob(views, binary, image, i, path)
            rec.update({"bytes": len(blob),
                        "sha256": hashlib.sha256(blob).hexdigest(),
                        "storage": "bufferView"})
        elif "uri" in image and not str(image["uri"]).startswith("data:"):
            rec.update({"storage": "external uri", "uri": image["uri"], "sha256": None})
        else:
            rec.update({"storage": "data uri", "sha256": None})
        out.append(rec)
    return out


def gate_atlas_untouched(source_path, export_path):
    """Gate ATLAS - ANDON - every embedded image arrives byte for byte.

    `embedded_images` sets `sha256=None` for an image stored as a data URI or an external
    uri, and this gate can only compare the hashes it has. The vacuity guard fired only
    when NO image was hashable, so a PARTIAL exclusion was silent: measured 2026-09-03 on
    a pair of GLBs each carrying one identical bufferView image and one data-URI image
    that DIFFERED between them, the gate passed with "1 embedded image(s) byte-identical
    through the route" - a count, not a coverage. The promise this gate exists for is
    "the atlas survives with zero re-bake"; certifying it over a subset without saying so
    is the shape of receipt this repo pays for. So an unhashable source image now raises,
    and the verdict states coverage as N of M.

    That widened verdict was then measured false in a second way (F-937f8a81): the
    comparison was `h not in out_hashes`, a MEMBERSHIP test over two sorted lists, so a
    source hash appearing twice was satisfied by one occurrence in the export. Measured
    2026-09-04 on a source embedding the same 20-byte image twice against an export
    embedding it once plus a different image, this gate PASSED with the verdict "2 of 2
    embedded image(s) byte-identical through the route, 0 unhashable" - the count clause
    reads 2 == 2 and both images are hashable. The comparison is now a multiset residual
    (`Counter(src) - Counter(out)`), reported per hash in the evidence.
    """
    before = embedded_images(source_path)
    after = embedded_images(export_path)
    ev = {"gate": "ATLAS", "andon": "GateAtlasUntouched",
          "source": source_path, "export": export_path,
          "images_in_source": [{k: v for k, v in i.items() if k != "index"} for i in before],
          "images_in_export": [{k: v for k, v in i.items() if k != "index"} for i in after]}
    problems = []

    # F-f7449bc9, wave 28. This gate accumulates up to four structurally different failures
    # and used to raise ONE prose string over them with no `clause` anywhere in the
    # receipt. `assembly.gate_batch_topology` is where this repo settled the shape
    # (`assembly._problem`, F-8d0e4cf1): the message stays the same sentence over the same
    # details in the same order, and the evidence gains `problems` as `{clause, detail}`
    # records, `clauses`, and `clause` as the first. The records are spelled as dict
    # LITERALS here rather than through `assembly._problem`, for two reasons: importing
    # `assembly` would pull `route_gates` into the import graph of a module the Blender
    # tools import, and `_census_nodes.clause_literals` reads a Constant inside a Dict node,
    # so a word handed to a helper is invisible to the vocabulary census — measured on
    # `3380ae2`, not one of `_problem`'s own words is in it.
    if len(before) != len(after):
        problems.append({
            "clause": "embedded_image_count_differs",
            "detail": f"{len(before)} embedded image(s) in the source, {len(after)} in "
                      f"the export"})
    src_hashes = sorted(i["sha256"] for i in before if i["sha256"])
    out_hashes = sorted(i["sha256"] for i in after if i["sha256"])
    ev["source_hashes"] = src_hashes
    ev["export_hashes"] = out_hashes
    unhashable = [{"index": i["index"], "storage": i.get("storage"), "name": i.get("name")}
                  for i in before if not i["sha256"]]
    ev["n_images_in_source"] = len(before)
    ev["n_source_images_hashable"] = len(src_hashes)
    ev["source_images_not_hashable"] = unhashable

    if not src_hashes:
        problems.append({
            "clause": "source_carries_no_embedded_image",
            "detail": "the source carries no embedded image to compare, so this gate "
                      "would be a check that cannot fail"})
    elif unhashable:
        problems.append({
            "clause": "source_image_cannot_be_hashed",
            "detail": f"{len(unhashable)} of {len(before)} source image(s) cannot be "
                      f"hashed (storage: {sorted({u['storage'] for u in unhashable})}), so "
                      f"'the atlas survives with zero re-bake' cannot be checked for them "
                      f"and a PASS would certify the promise over a subset without saying "
                      f"so"})
    # Multiset, not membership (F-937f8a81). `h not in out_hashes` is satisfied by ONE
    # occurrence, so a source that embeds the same image twice was certified by an export
    # carrying it once and a different image beside it: the count clause did not fire
    # (2 == 2), nothing was unhashable, and the verdict read "2 of 2 byte-identical". The
    # sibling discipline is turnaround.gate_set_distinct, which counts occurrences rather
    # than testing membership. Order stays irrelevant — a swapped pair is not a re-encode.
    src_counts = Counter(src_hashes)
    out_counts = Counter(out_hashes)
    residual = src_counts - out_counts
    ev["source_hash_counts"] = dict(sorted(src_counts.items()))
    ev["export_hash_counts"] = dict(sorted(out_counts.items()))
    ev["missing_hash_counts"] = dict(sorted(residual.items()))
    if residual:
        short = ", ".join(f"{h[:12]} x{c}" for h, c in sorted(residual.items()))
        problems.append({
            "clause": "source_image_not_byte_identical_in_the_export",
            "detail": f"{sum(residual.values())} source image occurrence(s) do not "
                      f"appear byte-identical in the export - the texture was "
                      f"re-encoded or resampled (short by: {short})"})

    if problems:
        ev["problems"] = problems
        ev["clauses"] = [p["clause"] for p in problems]
        ev["clause"] = problems[0]["clause"]
        raise GateAtlasUntouched(
            "the texture atlas did not survive the route unchanged: "
            + "; ".join(p["detail"] for p in problems), ev)
    ev["verdict"] = (f"{len(src_hashes)} of {len(before)} embedded image(s) byte-identical "
                     f"through the route, 0 unhashable")
    return ev


class ReliftMismatch(GateFailure):
    """A re-solved lift is not the performance the pinned GLB carries."""

    gate = "RELIFT"


def compare_signatures(pinned, fresh, label=None):
    """Two per-frame signature lists -> a verdict, or a raise naming the first divergence.

    Pure, so the interesting cases are testable without Blender: unequal lengths (a lift that
    dropped or gained a frame is not the same performance however well its frames match), an
    empty pair (a comparison over nothing must not report agreement), and a divergence at a
    frame that is not the first (a check that only ever compared frame 0 would pass on a rest
    pose and miss the whole clip).
    """
    ev = {"gate": "RELIFT", "andon": "ReliftMismatch", "label": label,
          "n_pinned": len(pinned), "n_fresh": len(fresh)}
    if not pinned or not fresh:
        # F-f7449bc9, wave 28 — three raises, one `ev`, no `clause`. See
        # `gate_atlas_untouched` above.
        ev["clause"] = "one_clip_carries_no_frames"
        raise ReliftMismatch(
            "one of the two clips carries no frames, so there is nothing to compare and a "
            "PASS would be agreement about nothing", ev)
    if len(pinned) != len(fresh):
        ev["clause"] = "frame_counts_differ"
        raise ReliftMismatch(
            f"frame counts differ: pinned {len(pinned)}, fresh {len(fresh)}. A lift that "
            f"dropped or gained a frame is not the same performance however well the "
            f"frames it kept agree", ev)

    diverged = [i for i, (a, b) in enumerate(zip(pinned, fresh)) if a != b]
    ev["n_frames_compared"] = len(pinned)
    ev["n_frames_differing"] = len(diverged)
    if diverged:
        i = diverged[0]
        ev["first_divergent_frame"] = i
        ev["pinned_signature"] = pinned[i]
        ev["fresh_signature"] = fresh[i]
        ev["clause"] = "resolved_lift_diverges_from_the_pinned_glb"
        raise ReliftMismatch(
            f"the re-solved lift diverges from the pinned GLB at frame {i} "
            f"({len(diverged)} of {len(pinned)} frames differ). Either the solver is not "
            f"deterministic or the pinned file is not what the recorded inputs produce — "
            f"and every generation conditioned on it has an unrecorded ancestor", ev)
    ev["verdict"] = (f"all {len(pinned)} frames of evaluated geometry identical")
    return ev


# ---------------------------------------------------------- animation ingest (F-03853b93)

COMPONENT = {
    5120: ("b", 1),   # BYTE
    5121: ("B", 1),   # UNSIGNED_BYTE
    5122: ("h", 2),   # SHORT
    5123: ("H", 2),   # UNSIGNED_SHORT
    5125: ("I", 4),   # UNSIGNED_INT
    5126: ("f", 4),   # FLOAT
}
TYPE_COUNT = {
    "SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
    "MAT2": 4, "MAT3": 9, "MAT4": 16,
}


def _accessor_values(js, bin_chunk, accessor_index, path):
    """Decode one accessor into a flat list of floats (or ints promoted to float).

    Locals are deliberately not named `views`/`binary` — those names are reserved for
    the atlas path's `_image_blob` census (`test_glb.py` AST walk). Animation ingest
    validates its own index/range here and leaves Gate ATLAS untouched.
    """
    accessors = js.get("accessors") or []
    if not isinstance(accessor_index, int) or accessor_index < 0 or accessor_index >= len(accessors):
        raise MalformedGLB(
            f"{path}: animation names accessor {accessor_index!r} outside the "
            f"{len(accessors)} declared accessor(s)",
            {"gate": None, "andon": "MalformedGLB", "clause": "animation_accessor_out_of_range",
             "accessor": accessor_index, "n_accessors": len(accessors), "path": str(path)})
    acc = accessors[accessor_index]
    if "bufferView" not in acc:
        raise MalformedGLB(
            f"{path}: accessor {accessor_index} carries no bufferView; sparse/empty "
            f"accessors are not an animation channel this reader accepts",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_accessor_has_no_bufferview",
             "accessor": accessor_index, "path": str(path)})
    buffer_views = js.get("bufferViews") or []
    view_i = acc["bufferView"]
    if not isinstance(view_i, int) or view_i < 0 or view_i >= len(buffer_views):
        raise MalformedGLB(
            f"{path}: accessor {accessor_index} names bufferView {view_i!r} outside the "
            f"{len(buffer_views)} declared view(s)",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_bufferview_out_of_range",
             "accessor": accessor_index, "bufferView": view_i, "path": str(path)})
    view = buffer_views[view_i]
    ctype = acc.get("componentType")
    if ctype not in COMPONENT:
        raise MalformedGLB(
            f"{path}: accessor {accessor_index} has unsupported componentType {ctype!r}",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_unsupported_component_type",
             "accessor": accessor_index, "componentType": ctype, "path": str(path)})
    fmt, csize = COMPONENT[ctype]
    atype = acc.get("type")
    if atype not in TYPE_COUNT:
        raise MalformedGLB(
            f"{path}: accessor {accessor_index} has unsupported type {atype!r}",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_unsupported_accessor_type",
             "accessor": accessor_index, "type": atype, "path": str(path)})
    ncomp = TYPE_COUNT[atype]
    count = int(acc.get("count", 0))
    if count < 1:
        raise MalformedGLB(
            f"{path}: accessor {accessor_index} declares count {count}",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_accessor_empty",
             "accessor": accessor_index, "count": count, "path": str(path)})
    byte_offset = int(view.get("byteOffset", 0)) + int(acc.get("byteOffset", 0))
    stride = int(view["byteStride"]) if "byteStride" in view else csize * ncomp
    need = byte_offset + stride * (count - 1) + csize * ncomp
    if need > len(bin_chunk):
        raise MalformedGLB(
            f"{path}: accessor {accessor_index} reads past the BIN chunk "
            f"(need {need} bytes, BIN holds {len(bin_chunk)})",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_accessor_past_bin_chunk",
             "accessor": accessor_index, "need": need, "bin_bytes": len(bin_chunk),
             "path": str(path)})
    out = []
    for i in range(count):
        start = byte_offset + i * stride
        vals = struct.unpack_from("<" + fmt * ncomp, bin_chunk, start)
        out.append([float(v) for v in vals])
    return out, atype

def _quat_to_mat3(q):
    """Unit quaternion (x, y, z, w) -> 3x3 row-major rotation matrix."""
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n <= 0.0:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    x, y, z, w = x / n, y / n, z / n, w / n
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return [
        [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy)],
        [2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx)],
        [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy)],
    ]


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_vec(a, b, t):
    return [_lerp(a[i], b[i], t) for i in range(len(a))]


def _slerp_quat(a, b, t):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    dot = ax * bx + ay * by + az * bz + aw * bw
    if dot < 0.0:
        bx, by, bz, bw, dot = -bx, -by, -bz, -bw, -dot
    if dot > 0.9995:
        return _lerp_vec(a, [bx, by, bz, bw], t)
    theta = math.acos(max(-1.0, min(1.0, dot)))
    s = math.sin(theta)
    wa = math.sin((1.0 - t) * theta) / s
    wb = math.sin(t * theta) / s
    return [wa * ax + wb * bx, wa * ay + wb * by, wa * az + wb * bz, wa * aw + wb * bw]


def _sample_channel(times, values, t, path_kind, interpolation):
    if t <= times[0]:
        return list(values[0])
    if t >= times[-1]:
        return list(values[-1])
    for i in range(len(times) - 1):
        t0, t1 = times[i], times[i + 1]
        if t0 <= t <= t1:
            if interpolation == "STEP" or t1 == t0:
                return list(values[i])
            u = (t - t0) / (t1 - t0)
            if path_kind == "rotation":
                return _slerp_quat(values[i], values[i + 1], u)
            return _lerp_vec(values[i], values[i + 1], u)
    return list(values[-1])


def _default_retarget(node_names, sitelist_names):
    """Identity map where glTF node names already match sitelist bone names."""
    allowed = set(sitelist_names)
    return {n: n for n in node_names if n in allowed}


def read_animation(path, animation_index=0, fps=24.0, retarget=None,
                   sitelist_names=None):
    """Pure reader: glTF animation samplers -> per-frame local rotations + root translation.

    Returns a motion-shaped record:

      * `frames` — list of `{frame, t, local: {bone: 3x3}, root: [x,y,z]}`
      * `retarget` — node-name -> sitelist-bone map actually used
      * `source` — animation name/index, fps, duration

    Unmapped animated joints are refused by name (no silent drop). Atlas / mesh identity
    gates are untouched — this path never opens image bufferViews.
    """
    if sitelist_names is None:
        from . import sitelist as _sitelist
        sitelist_names = list(_sitelist.ALL_NAMES)

    js, bin_chunk = read_chunks(path)
    animations = js.get("animations") or []
    if not animations:
        raise MalformedGLB(
            f"{path}: the container carries no animations[]; a static mesh has nothing "
            f"for the lift/resample/aapose chain to ingest as a performance",
            {"gate": None, "andon": "MalformedGLB", "clause": "no_animations",
             "path": str(path)})
    if not isinstance(animation_index, int) or animation_index < 0 \
            or animation_index >= len(animations):
        raise MalformedGLB(
            f"{path}: animation_index {animation_index!r} is outside the "
            f"{len(animations)} animation(s) declared",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_index_out_of_range",
             "animation_index": animation_index, "n_animations": len(animations),
             "path": str(path)})
    anim = animations[animation_index]
    nodes = js.get("nodes") or []
    node_names = []
    for i, node in enumerate(nodes):
        node_names.append(node.get("name") or f"node_{i}")

    if retarget is None:
        retarget = _default_retarget(node_names, sitelist_names)
    else:
        retarget = dict(retarget)

    channels = anim.get("channels") or []
    samplers = anim.get("samplers") or []
    if not channels:
        raise MalformedGLB(
            f"{path}: animation {animation_index} declares no channels",
            {"gate": None, "andon": "MalformedGLB", "clause": "animation_has_no_channels",
             "animation_index": animation_index, "path": str(path)})

    # Collect per-target sampled tracks first; refuse unmapped joints up front.
    tracks = []  # (bone_or_None_for_root_only, path_kind, times, values, interpolation)
    unmapped = []
    duration = 0.0
    for ci, ch in enumerate(channels):
        target = ch.get("target") or {}
        node_i = target.get("node")
        path_kind = target.get("path")
        samp_i = ch.get("sampler")
        if path_kind not in ("rotation", "translation", "scale"):
            continue
        if path_kind == "scale":
            # Scale is not part of the sitelist motion record; refuse rather than drop.
            raise MalformedGLB(
                f"{path}: animation channel {ci} targets scale on node {node_i!r}; "
                f"this reader maps rotation + root translation only",
                {"gate": None, "andon": "MalformedGLB",
                 "clause": "animation_scale_channel_unsupported",
                 "channel": ci, "node": node_i, "path": str(path)})
        if not isinstance(node_i, int) or node_i < 0 or node_i >= len(nodes):
            raise MalformedGLB(
                f"{path}: animation channel {ci} names node {node_i!r} outside the "
                f"{len(nodes)} node(s)",
                {"gate": None, "andon": "MalformedGLB",
                 "clause": "animation_node_out_of_range",
                 "channel": ci, "node": node_i, "path": str(path)})
        node_name = node_names[node_i]
        bone = retarget.get(node_name)
        if bone is None or bone not in sitelist_names:
            unmapped.append({"channel": ci, "node": node_i, "name": node_name,
                             "mapped_to": bone, "path": path_kind})
            continue
        if not isinstance(samp_i, int) or samp_i < 0 or samp_i >= len(samplers):
            raise MalformedGLB(
                f"{path}: animation channel {ci} names sampler {samp_i!r} outside the "
                f"{len(samplers)} sampler(s)",
                {"gate": None, "andon": "MalformedGLB",
                 "clause": "animation_sampler_out_of_range",
                 "channel": ci, "sampler": samp_i, "path": str(path)})
        samp = samplers[samp_i]
        times_raw, ttype = _accessor_values(js, bin_chunk, samp["input"], path)
        values_raw, vtype = _accessor_values(js, bin_chunk, samp["output"], path)
        if ttype != "SCALAR":
            raise MalformedGLB(
                f"{path}: sampler {samp_i} input type is {ttype!r}, expected SCALAR",
                {"gate": None, "andon": "MalformedGLB",
                 "clause": "animation_sampler_input_not_scalar",
                 "sampler": samp_i, "type": ttype, "path": str(path)})
        times = [row[0] for row in times_raw]
        if path_kind == "rotation" and vtype != "VEC4":
            raise MalformedGLB(
                f"{path}: rotation sampler {samp_i} output type is {vtype!r}, expected VEC4",
                {"gate": None, "andon": "MalformedGLB",
                 "clause": "animation_rotation_not_vec4",
                 "sampler": samp_i, "type": vtype, "path": str(path)})
        if path_kind == "translation" and vtype != "VEC3":
            raise MalformedGLB(
                f"{path}: translation sampler {samp_i} output type is {vtype!r}, "
                f"expected VEC3",
                {"gate": None, "andon": "MalformedGLB",
                 "clause": "animation_translation_not_vec3",
                 "sampler": samp_i, "type": vtype, "path": str(path)})
        if len(values_raw) < len(times):
            raise MalformedGLB(
                f"{path}: sampler {samp_i} has {len(times)} times and "
                f"{len(values_raw)} values",
                {"gate": None, "andon": "MalformedGLB",
                 "clause": "animation_sampler_length_mismatch",
                 "sampler": samp_i, "n_times": len(times), "n_values": len(values_raw),
                 "path": str(path)})
        interp = samp.get("interpolation", "LINEAR")
        if interp not in ("LINEAR", "STEP", "CUBICSPLINE"):
            raise MalformedGLB(
                f"{path}: sampler {samp_i} interpolation {interp!r} is unsupported",
                {"gate": None, "andon": "MalformedGLB",
                 "clause": "animation_interpolation_unsupported",
                 "sampler": samp_i, "interpolation": interp, "path": str(path)})
        if interp == "CUBICSPLINE":
            # glTF packs [in-tangent, value, out-tangent] per key; take the middle.
            if len(values_raw) != len(times) * 3:
                raise MalformedGLB(
                    f"{path}: CUBICSPLINE sampler {samp_i} expected {len(times) * 3} "
                    f"values, got {len(values_raw)}",
                    {"gate": None, "andon": "MalformedGLB",
                     "clause": "animation_cubicspline_length_mismatch",
                     "sampler": samp_i, "path": str(path)})
            values_raw = [values_raw[i * 3 + 1] for i in range(len(times))]
            interp = "LINEAR"
        duration = max(duration, times[-1] if times else 0.0)
        tracks.append({
            "bone": bone,
            "path": path_kind,
            "times": times,
            "values": values_raw[:len(times)],
            "interpolation": interp,
            "node_name": node_name,
        })

    if unmapped:
        names = sorted({u["name"] for u in unmapped})
        raise MalformedGLB(
            f"{path}: animation {animation_index} drives {len(unmapped)} channel(s) on "
            f"joint(s) with no retarget into the sitelist: {names}. Pass an explicit "
            f"retarget table (glTF node name -> sitelist bone) or rename the nodes; "
            f"silent drops are refused",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_joint_unmapped",
             "unmapped": unmapped, "unmapped_names": names,
             "retarget": dict(retarget), "path": str(path)})

    if not tracks:
        raise MalformedGLB(
            f"{path}: animation {animation_index} produced no rotation/translation tracks "
            f"after retarget",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_no_usable_tracks",
             "animation_index": animation_index, "path": str(path)})

    fps = float(fps)
    if not (fps > 0.0) or fps != fps:
        raise MalformedGLB(
            f"{path}: fps={fps!r} is not a positive finite frame rate",
            {"gate": None, "andon": "MalformedGLB", "clause": "animation_fps_not_positive",
             "fps": fps, "path": str(path)})
    n_frames = max(1, int(math.floor(duration * fps + 1e-9)) + 1)
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    root_bone_candidates = [t["bone"] for t in tracks if t["path"] == "translation"]
    # Prefer sitelist root "hips" when present; otherwise the sole translation target.
    root_bone = "hips" if "hips" in root_bone_candidates else (
        root_bone_candidates[0] if len(root_bone_candidates) == 1 else None)
    if root_bone_candidates and root_bone is None:
        raise MalformedGLB(
            f"{path}: translation channels target multiple bones "
            f"{sorted(set(root_bone_candidates))} and none is 'hips'; name the root or "
            f"retarget exactly one translation channel to hips",
            {"gate": None, "andon": "MalformedGLB",
             "clause": "animation_ambiguous_root_translation",
             "translation_bones": sorted(set(root_bone_candidates)), "path": str(path)})

    frames = []
    for fi in range(n_frames):
        t = fi / fps
        local = {}
        root = [0.0, 0.0, 0.0]
        for tr in tracks:
            sample = _sample_channel(tr["times"], tr["values"], t, tr["path"],
                                     tr["interpolation"])
            if tr["path"] == "rotation":
                local[tr["bone"]] = _quat_to_mat3(sample)
            elif tr["path"] == "translation" and tr["bone"] == root_bone:
                root = sample
        for name in sitelist_names:
            local.setdefault(name, [row[:] for row in identity])
        frames.append({"frame": fi, "t": t, "local": local, "root": root})

    return {
        "frames": frames,
        "retarget": dict(retarget),
        "root_bone": root_bone,
        "source": {
            "path": str(path),
            "animation_index": animation_index,
            "animation_name": anim.get("name"),
            "fps": fps,
            "duration": duration,
            "n_frames": n_frames,
            "n_tracks": len(tracks),
        },
    }

