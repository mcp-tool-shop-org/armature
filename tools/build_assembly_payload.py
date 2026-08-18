#!/usr/bin/env python
"""build_assembly_payload — the frames->VIDEO chain, built in-repo. S03 Task C.

    <venv-python> tools\\build_assembly_payload.py --uploads=<uploads.json> \\
        --out=<dir> [--fps=16] [--prefix=video/S03_assembly]

Builds the API-format graph the halt ruling (R2) proposed as the rescue for the r2v tier's
unreachable video slot:

    81 x LoadImage -> BatchImagesNode -> CreateVideo(fps=16) -> SaveVideo

**A served template is a reference, never a route** — so this graph is built here, from the
node contracts re-measured with `get_node` on 2026-08-13, and it passes Gate ROUTE and both
Gate ASSEMBLY clauses in code before anything is submitted. Nothing here submits anything.

`--uploads` is the JSON written by the upload step: local frame filename -> the server's
content-addressed name. Frames are ordered by their LOCAL name, which is the frame order;
the server's names are content-addressed and sort into a meaningless order, and sorting by
them would assemble the clip's 81 frames in an arbitrary sequence while every count in every
gate still read correctly.

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory; owner: the executor session. The uploads it references have **no delete endpoint**
on this API surface — they are content-addressed and inert unless a graph names them (the
E12 w2/w3 §7 convention).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import assembly as AS  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402

TOOL_VERSION = "S03.1"

#: Node ids. Kept away from 1..99 so the graph reads as its own thing beside E02's, which
#: used 200+ for its LoadImages and 300/301 for its batch and probe.
FIRST_IMAGE_ID = 200
BATCH_ID = 400
VIDEO_ID = 401
SAVE_ID = 402

#: The frame the uploaded clip actually is — 1024x576, 81 frames, measured off the PNGs
#: rather than carried from a spec. Supplied to Gate L so the clause is decided rather than
#: INDETERMINATE; see the report for what that clause does and does not prove here.
WIDTH, HEIGHT = 1024, 576


def build(names, fps=16.0, prefix="video/S03_assembly"):
    """The API-format graph. `names` is the server-side upload name per frame, IN ORDER."""
    wf = {}
    batch_inputs = {}
    for i, name in enumerate(names):
        nid = str(FIRST_IMAGE_ID + i)
        wf[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
        batch_inputs[f"images.image{i}"] = [nid, 0]
    wf[str(BATCH_ID)] = {"class_type": "BatchImagesNode", "inputs": batch_inputs}
    wf[str(VIDEO_ID)] = {"class_type": "CreateVideo", "inputs": {
        "fps": float(fps), "bit_depth": 8, "images": [str(BATCH_ID), 0]}}
    wf[str(SAVE_ID)] = {"class_type": "SaveVideo", "inputs": {
        "filename_prefix": prefix, "format": "auto", "codec": "auto",
        "video": [str(VIDEO_ID), 0]}}
    return wf


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--uploads", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=16.0)
    ap.add_argument("--prefix", default="video/S03_assembly")
    a = ap.parse_args(argv)

    out = os.path.abspath(a.out)
    # Not a spend: Gate ASSEMBLY_paid requires zero billable nodes. Gate CANON
    # lives in the builders that author a generation, not in a frames->VIDEO pack.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    order = sorted(uploads)                  # LOCAL names: 00000.png .. 00080.png
    names = [uploads[k] for k in order]
    if len(set(names)) != len(names):
        raise AS.AssemblyGate(
            f"the upload map carries {len(names)} frames but only {len(set(names))} "
            f"distinct server names: two local frames uploaded to the same object, so the "
            f"batch would carry a duplicate while every count still read right",
            {"n": len(names), "distinct": len(set(names))})

    wf = build(names, fps=a.fps, prefix=a.prefix)

    # ---- the gates, in code, before anything is submitted.
    gate_paid = AS.gate_no_paid_nodes(wf)
    gate_topo = AS.gate_batch_topology(wf, len(names), BATCH_ID, VIDEO_ID, SAVE_ID)
    # Gate ROUTE. `require_pinned_seeds=False` is not a skip: this graph has no
    # noise-bearing node at all, so the seed clause has nothing to decide and saying so is
    # honest where a green "0 seeds, all pinned" would be the vacuous shape the E13
    # executor was ruled right to refuse. The clauses that DO bind here are the licence one
    # (no weights are loaded, so none can be banned) and Gate PAIR (no conditioning node,
    # so none can be unpaired) — both reported below with what they actually examined.
    gate_route = RG.verify(wf, family="wan", require_pinned_seeds=False,
                           frame=(WIDTH, HEIGHT, len(names)))

    record = {
        "tool": "build_assembly_payload", "tool_version": TOOL_VERSION,
        "chain": "LoadImage x N -> BatchImagesNode -> CreateVideo -> SaveVideo",
        "n_frames": len(names), "fps": float(a.fps),
        "resolution": [WIDTH, HEIGHT],
        "filename_prefix": a.prefix,
        "frame_order": order,
        "uploads": {k: uploads[k] for k in order},
        "node_ids": {"first_image": FIRST_IMAGE_ID, "batch": BATCH_ID,
                     "video": VIDEO_ID, "save": SAVE_ID},
        "node_contracts_measured": {
            "when": "2026-08-13, get_node",
            "BatchImagesNode": "images COMFY_AUTOGROW_V3 -> IMAGE; api_node false",
            "CreateVideo": ("images IMAGE + fps FLOAT (1-120, default 30), optional audio "
                            "and bit_depth INT (8-10) -> VIDEO; api_node false, "
                            "output_node false"),
            "SaveVideo": ("video VIDEO + filename_prefix STRING + format COMBO(auto,mp4) + "
                          "codec dynamic COMBO(auto,h264) -> VIDEO; api_node false, "
                          "output_node TRUE"),
            "LoadImage": "image COMBO -> IMAGE, MASK; api_node false",
        },
        "gates": {"ASSEMBLY_paid": gate_paid, "ASSEMBLY_topology": gate_topo,
                  "ROUTE": gate_route},
    }

    graph_path = os.path.join(out, "S03-assembly.api.json")
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=1)
    with open(os.path.join(out, "S03-assembly-payload-record.json"), "w",
              encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    print(f"nodes            {len(wf)}")
    print(f"paid-node gate   {gate_paid['verdict']}")
    print(f"topology gate    {gate_topo['verdict']}")
    print(f"route components {len(gate_route['components'])}  "
          f"seeds {len(gate_route['seeds'])}  latents {len(gate_route['latents'])}")
    print(f"frame legality   {[f['legal'] for f in gate_route['frame_legality']]}")
    print(f"BUILD_ASSEMBLY_OK {graph_path}")
    return wf


if __name__ == "__main__":
    main()
