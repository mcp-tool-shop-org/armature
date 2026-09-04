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

    if len(before) != len(after):
        problems.append(f"{len(before)} embedded image(s) in the source, {len(after)} in "
                        f"the export")
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
        problems.append("the source carries no embedded image to compare, so this gate "
                        "would be a check that cannot fail")
    elif unhashable:
        problems.append(
            f"{len(unhashable)} of {len(before)} source image(s) cannot be hashed "
            f"(storage: {sorted({u['storage'] for u in unhashable})}), so 'the atlas "
            f"survives with zero re-bake' cannot be checked for them and a PASS would "
            f"certify the promise over a subset without saying so")
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
        problems.append(f"{sum(residual.values())} source image occurrence(s) do not "
                        f"appear byte-identical in the export - the texture was "
                        f"re-encoded or resampled (short by: {short})")

    if problems:
        raise GateAtlasUntouched(
            "the texture atlas did not survive the route unchanged: " + "; ".join(problems),
            ev)
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
        raise ReliftMismatch(
            "one of the two clips carries no frames, so there is nothing to compare and a "
            "PASS would be agreement about nothing", ev)
    if len(pinned) != len(fresh):
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
        raise ReliftMismatch(
            f"the re-solved lift diverges from the pinned GLB at frame {i} "
            f"({len(diverged)} of {len(pinned)} frames differ). Either the solver is not "
            f"deterministic or the pinned file is not what the recorded inputs produce — "
            f"and every generation conditioned on it has an unrecorded ancestor", ev)
    ev["verdict"] = (f"all {len(pinned)} frames of evaluated geometry identical")
    return ev
