#!/usr/bin/env python
"""build_cascade_payload — the frames->VIDEO chain, batched in a cascade. E13 re-arm, Stage 0.

    <venv-python> tools\\build_cascade_payload.py --uploads=<uploads.json> \\
        --out=<dir> [--fps=16] [--group=27] [--prefix=video/E13_cascade]

S03 built the flat chain and measured it executing at 8 frames and failing at 81:

    BatchImagesNode.execute() got an unexpected keyword argument 'images.image50'

The E13 RE-ARM amendment's probe is the re-shape that failure allows — batch the batches,
with no single node loaded above the observed cap:

    81 x LoadImage -> 3 x BatchImagesNode(27) -> BatchImagesNode(3)
                   -> CreateVideo(fps=16) -> SaveVideo

Nothing here submits anything, and nothing here is new to the catalog: the five classes are
the same five S03 measured `api_node: false` with `get_node`, re-measured again on
2026-08-13 for this run. **A served template is a reference, never a route** — the graph is
built here and gated here.

`--uploads` is the JSON written by an upload step: local frame filename -> the server's
content-addressed name. Frames are ordered by their LOCAL name, which is the frame order;
the server's names are content-addressed and sort into a meaningless order. Sorting by them
would assemble the clip in an arbitrary sequence while every count in every gate still read
correctly — the reason `gate_cascade_topology` checks group ORDER and not only group counts.

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory; owner: the executor session. The uploads it references have **no delete
endpoint** on this API surface — they are content-addressed and inert unless a graph names
them, and they persist service-side (the E12 w2/w3 §7 convention).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import assembly as AS  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402

TOOL_VERSION = "E13.1"

#: Node ids. LoadImages from 200 as S03's flat chain used; the cascade's own nodes are
#: numbered so a group, the final batch and the tail are distinguishable at a glance in a
#: payload record.
FIRST_IMAGE_ID = 200
FIRST_GROUP_ID = 400
FINAL_BATCH_ID = 410
VIDEO_ID = 420
SAVE_ID = 421

#: The frame the uploaded clip actually is — 1024x576, 81 frames, measured off the PNGs by
#: S03 rather than carried from a spec. Supplied to Gate L so its clause is decided rather
#: than INDETERMINATE; what that clause does and does not examine here is in the report.
WIDTH, HEIGHT = 1024, 576


def build(names, fps=16.0, group_size=AS.GROUP_SIZE, prefix="video/E13_cascade"):
    """The API-format cascade. `names` is the server-side upload name per frame, IN ORDER."""
    plan = AS.cascade_plan(len(names), group_size)
    wf = {}

    for i, name in enumerate(names):
        wf[str(FIRST_IMAGE_ID + i)] = {"class_type": "LoadImage", "inputs": {"image": name}}

    group_ids = []
    for gi, (start, stop) in enumerate(plan):
        gid = str(FIRST_GROUP_ID + gi)
        group_ids.append(gid)
        wf[gid] = {"class_type": "BatchImagesNode", "inputs": {
            f"images.image{j}": [str(FIRST_IMAGE_ID + start + j), 0]
            for j in range(stop - start)}}

    wf[str(FINAL_BATCH_ID)] = {"class_type": "BatchImagesNode", "inputs": {
        f"images.image{i}": [gid, 0] for i, gid in enumerate(group_ids)}}
    wf[str(VIDEO_ID)] = {"class_type": "CreateVideo", "inputs": {
        "fps": float(fps), "bit_depth": 8, "images": [str(FINAL_BATCH_ID), 0]}}
    wf[str(SAVE_ID)] = {"class_type": "SaveVideo", "inputs": {
        "filename_prefix": prefix, "format": "auto", "codec": "auto",
        "video": [str(VIDEO_ID), 0]}}
    return wf, group_ids


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--uploads", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=16.0)
    ap.add_argument("--group", type=int, default=AS.GROUP_SIZE)
    ap.add_argument("--prefix", default="video/E13_cascade")
    a = ap.parse_args(argv)

    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    order = sorted(uploads)                  # LOCAL names: 00000.png .. 00080.png
    names = [uploads[k] for k in order]
    if len(set(names)) != len(names):
        raise AS.AssemblyGate(
            f"the upload map carries {len(names)} frames but only {len(set(names))} "
            f"distinct server names: two local frames uploaded to the same object, so the "
            f"cascade would carry a duplicate while every count still read right",
            {"n": len(names), "distinct": len(set(names))})

    wf, group_ids = build(names, fps=a.fps, group_size=a.group, prefix=a.prefix)

    # ---- the gates, in code, before anything is submitted.
    gate_paid = AS.gate_no_paid_nodes(wf)
    gate_ceiling = AS.gate_slot_ceiling(wf, cap=max(a.group, 1))
    gate_topo = AS.gate_cascade_topology(wf, len(names), group_ids, FINAL_BATCH_ID,
                                         VIDEO_ID, SAVE_ID, "video", group_size=a.group)
    # Gate ROUTE. `require_pinned_seeds=False` is not a skip: this graph has no
    # noise-bearing node at all, so the seed clause has nothing to decide, and a green
    # "0 seeds, all pinned" here would be the vacuous shape CLAUDE.md names. The clauses
    # that DO bind are the licence one (no weights load, so none can be banned) and Gate
    # PAIR (no conditioning node, so none can be unpaired) — both reported below for what
    # they examined rather than as green ticks.
    gate_route = RG.verify(wf, family="wan", require_pinned_seeds=False,
                           frame=(WIDTH, HEIGHT, len(names)))

    record = {
        "tool": "build_cascade_payload", "tool_version": TOOL_VERSION,
        "chain": ("LoadImage x N -> BatchImagesNode x G (group) -> BatchImagesNode (final) "
                  "-> CreateVideo -> SaveVideo"),
        "n_frames": len(names), "fps": float(a.fps),
        "group_size": int(a.group),
        "plan": [list(p) for p in AS.cascade_plan(len(names), a.group)],
        "inferred_slot_cap": AS.INFERRED_SLOT_CAP,
        "inferred_slot_cap_note": (
            "INFERRED from S03's single error message naming images.image50 as unexpected, "
            "with 8 slots executing. No submission was made at 49, 50 or 51 slots, so the "
            "boundary is not located and this number is not a measurement."),
        "resolution": [WIDTH, HEIGHT],
        "filename_prefix": a.prefix,
        "frame_order": order,
        "uploads": {k: uploads[k] for k in order},
        "node_ids": {"first_image": FIRST_IMAGE_ID, "groups": group_ids,
                     "final_batch": FINAL_BATCH_ID, "video": VIDEO_ID, "save": SAVE_ID},
        "node_contracts_measured": {
            "when": "2026-08-13, get_node (re-measured for the E13 re-arm)",
            "BatchImagesNode": "images COMFY_AUTOGROW_V3 -> IMAGE; api_node false",
            "CreateVideo": ("images IMAGE + fps FLOAT (1-120, default 30), optional audio "
                            "and bit_depth INT (8-10) -> VIDEO; api_node false, "
                            "output_node false"),
            "SaveVideo": ("video VIDEO + filename_prefix STRING + format COMBO(auto,mp4) + "
                          "codec dynamic COMBO(auto,h264) -> VIDEO; api_node false, "
                          "output_node TRUE"),
            "LoadImage": "image COMBO -> IMAGE, MASK; api_node false",
        },
        "gates": {"ASSEMBLY_paid": gate_paid, "CASCADE_ceiling": gate_ceiling,
                  "CASCADE_topology": gate_topo, "ROUTE": gate_route},
    }

    graph_path = os.path.join(out, "E13-cascade.api.json")
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=1)
    with open(os.path.join(out, "E13-cascade-payload-record.json"), "w",
              encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    print(f"nodes            {len(wf)}")
    print(f"groups           {len(group_ids)} of at most {a.group}")
    print(f"paid-node gate   {gate_paid['verdict']}")
    print(f"slot ceiling     {gate_ceiling['verdict']}")
    print(f"topology gate    {gate_topo['verdict']}")
    print(f"route components {len(gate_route['components'])}  "
          f"seeds {len(gate_route['seeds'])}  latents {len(gate_route['latents'])}")
    print(f"frame legality   {[f['legal'] for f in gate_route['frame_legality']]}")
    print(f"BUILD_CASCADE_OK {graph_path}")
    return wf


if __name__ == "__main__":
    main()
