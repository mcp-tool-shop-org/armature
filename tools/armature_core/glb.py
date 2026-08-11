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
import struct

from .errors import GateFailure

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


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
    """(json_dict, bin_bytes) from a GLB, or raise on a container this cannot read."""
    with open(path, "rb") as fh:
        header = fh.read(12)
        if len(header) < 12:
            raise ValueError(f"{path}: shorter than a GLB header")
        magic, version, total = struct.unpack("<III", header)
        if magic != GLB_MAGIC:
            raise ValueError(f"{path}: not a GLB (magic {magic:#x})")
        js, binary = None, b""
        while fh.tell() < total:
            head = fh.read(8)
            if len(head) < 8:
                break
            length, kind = struct.unpack("<II", head)
            data = fh.read(length)
            if kind == CHUNK_JSON:
                js = json.loads(data.decode("utf-8"))
            elif kind == CHUNK_BIN:
                binary = data
        if js is None:
            raise ValueError(f"{path}: no JSON chunk")
        return js, binary


def embedded_images(path):
    """Every embedded image, with its sha256. Keyed by index so order changes are visible."""
    js, binary = read_chunks(path)
    views = js.get("bufferViews") or []
    out = []
    for i, image in enumerate(js.get("images") or []):
        rec = {"index": i, "name": image.get("name"), "mime_type": image.get("mimeType")}
        if "bufferView" in image:
            view = views[image["bufferView"]]
            start = int(view.get("byteOffset", 0))
            length = int(view["byteLength"])
            blob = binary[start:start + length]
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
    """Gate ATLAS · ANDON — every embedded image arrives byte for byte."""
    before = embedded_images(source_path)
    after = embedded_images(export_path)
    ev = {"source": source_path, "export": export_path,
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

    if not src_hashes:
        problems.append("the source carries no embedded image to compare, so this gate "
                        "would be a check that cannot fail")
    missing = [h for h in src_hashes if h not in out_hashes]
    if missing:
        problems.append(f"{len(missing)} source image(s) do not appear byte-identical in "
                        f"the export — the texture was re-encoded or resampled")

    if problems:
        raise GateAtlasUntouched(
            "the texture atlas did not survive the route unchanged: " + "; ".join(problems),
            ev)
    ev["verdict"] = f"{len(src_hashes)} embedded image(s) byte-identical through the route"
    return ev
