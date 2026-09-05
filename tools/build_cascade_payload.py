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

--------------------------------------------------------------------------------
Three corrections, 2026-09-03, all measured on this tool

* **The local sort was not a frame order.** An 81-entry map keyed `0.png` .. `80.png`
  built, printed "81 distinct LoadImage nodes -> 3 group batch(es) … groups in frame
  order, every link resolved" and BUILD_CASCADE_OK, while the recorded frame order ran
  `0.png, 1.png, 10.png, …` with `10.png` in slot 2; a 4-frame map plus one
  `reference.png` key was absorbed as a fifth frame. `frame_order` (in
  `build_assembly_payload`) now refuses any key that is not `NNNNN.png` and any gap.
* **No gate related a slot index to a frame index.** `gate_cascade_topology` checks that
  the GROUP nodes appear in order over whatever list `names` happens to be; two slots
  swapped INSIDE a group keeps every count right. `gate_slot_frame_index` is the clause
  that fires on it, and the ordered per-frame source ids go to the shared gate as well.
* **The slot ceiling was the CLI's number, not the module's.** `gate_slot_ceiling` was
  called with `cap=max(--group, 1)`, i.e. the same value that produced the group nodes, so
  for group nodes it checked a direction the construction already bounds: `--group=81`
  built ONE `BatchImagesNode` with 81 auto-grow slots and the gate printed "ceiling 81".
  `assembly.py` states the intended contract — `MAX_SLOTS_PER_NODE` equals `GROUP_SIZE`
  so a widening is a deliberate diff in both places — and the CLI defeated it at runtime
  with no diff. The gate now owns its ceiling; `--group` is passed for it to check
  against that constant, never as the ceiling itself.

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
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateFailure)
from build_assembly_payload import (  # noqa: E402
    FRAME_KEY, canonical_payload_digest, frame_order, frame_source_ids,
    gate_create_video_fps, gate_slot_frame_index)

TOOL_VERSION = "E13.2"

__all__ = ["FRAME_KEY", "frame_order", "frame_source_ids", "gate_create_video_fps",
           "gate_slot_frame_index", "build", "build_and_write", "main"]

#: The shared gates own their own ceiling and their own ordering clause:
#: `gate_slot_ceiling(graph, group_size=..., cap=...)` compares the caller's group size
#: against `MAX_SLOTS_PER_NODE` and raises above it, and both topology gates take
#: `expected_sources` — the ordered LoadImage node ids, one per frame, in frame order —
#: and compare slot k to frame k. This tool supplies both. `gate_slot_frame_index` above
#: is this tool's own copy of the slot-to-frame clause, kept because the builder is the
#: tool that authors the payload and the check belongs inside it.

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
    # `--fps` was written straight into `CreateVideo.fps` with no clause while this tool's
    # OWN record stated the node's measured contract as fps FLOAT (1-120). The gate lives
    # here, inside the function that emits the node, beside the `--group` clause that was
    # already bounded in both directions. One implementation, in `build_assembly_payload`,
    # imported by all five builders that take the flag.
    gate_create_video_fps(fps)
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


def build_and_write(argv=None):
    """Build, gate, write — and hand the GRAPH back to an in-process caller.

    Split out of `main` in wave 10 (F-4d6b26ec). `main` used to end `return wf` under
    `raise SystemExit(main())`, so a successful build exited 1: measured as a subprocess on
    an 81-entry padded map, stdout ended `BUILD_CASCADE_OK <path>` with seven green gate
    lines, stderr received 9,673 bytes of the graph dict, and the exit code was 1. This is
    the builder whose cascade helpers the E13 A2 spend arm shares.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--uploads", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=16.0)
    ap.add_argument("--group", type=int, default=AS.GROUP_SIZE)
    ap.add_argument("--prefix", default="video/E13_cascade")
    a = ap.parse_args(argv)

    out = os.path.abspath(a.out)
    # Not a spend: same frames->VIDEO pack as assembly, batched. Gate CANON
    # is not armed here because there is no generation to refuse.
    #
    # `os.makedirs` used to sit HERE, above --uploads being read and above every gate. A
    # refused build therefore left an empty run directory beside real ones. It now sits
    # below the last in-tool gate.

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    order = frame_order(uploads)             # LOCAL names: 00000.png .. 00080.png
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
    # Re-run for the RECORD; `build` already raised on an illegal rate.
    gate_fps = gate_create_video_fps(a.fps)
    # The gate owns the ceiling. `cap` is NOT passed: handing it the same --group value
    # that produced the group nodes made it check a direction the construction already
    # bounds. `group_size` is offered for the gate to check against its own constant.
    gate_ceiling = AS.gate_slot_ceiling(wf, group_size=int(a.group))
    ordered_ids = frame_source_ids(names, FIRST_IMAGE_ID)
    gate_topo = AS.gate_cascade_topology(wf, len(names), group_ids, FINAL_BATCH_ID,
                                         VIDEO_ID, SAVE_ID, "video", group_size=a.group,
                                         expected_sources=list(ordered_ids))
    # `strict=True`: an un-strict zip truncates to the shorter of the two, so a plan one
    # group short is silently produced and `gate_slot_frame_index` used to return its green
    # sentence having inspected 54 of 81 slots (wave 8, F-ad45bc42). The gate carries its
    # own coverage clause now; this is the pairing refusing to build the short plan at all.
    slot_plan = [(gid, start, stop) for (start, stop), gid
                 in zip(AS.cascade_plan(len(names), a.group), group_ids, strict=True)]
    gate_index = gate_slot_frame_index(wf, names, slot_plan, FIRST_IMAGE_ID)
    # Gate ROUTE. `carries_no_sampler=True` is the CHECKED form of the sentence this
    # comment used to make with `require_pinned_seeds=False` (wave 12, F-60a1222b) — the same
    # swap as in `build_assembly_payload`, one wording. The assertion is checked, not obeyed:
    # a sampler in this graph refuses here rather than riding a green "NOT CHECKED".
    gate_route = RG.verify(wf, family="wan", carries_no_sampler=True,
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
        "frame_source_ids": list(ordered_ids),
        "gates": {"ASSEMBLY_paid": gate_paid, "CREATE_VIDEO_fps": gate_fps,
                  "CASCADE_ceiling": gate_ceiling,
                  "CASCADE_topology": gate_topo,
                  "CASCADE_slot_frame_index": gate_index, "ROUTE": gate_route},
        # Wave 20, F-dba1bcd8. The tie between THIS record and the graph beside it.
        "payload_sha256": canonical_payload_digest(wf),
    }

    # Below the last in-tool gate: a refuse leaves no output directory.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories
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
    print(f"slot->frame gate {gate_index['verdict']}")
    print(f"route components {len(gate_route['components'])}  "
          f"seeds {len(gate_route['seeds'])}  latents {len(gate_route['latents'])}")
    print(f"frame legality   {[f['legal'] for f in gate_route['frame_legality']]}")
    print(f"BUILD_CASCADE_OK {graph_path}")
    return wf


def main(argv=None):
    """The process exit code, and nothing else. 0 = built; a gate raises."""
    build_and_write(argv)
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9). The nine builders and the two fetchers
    # disagreed three ways on how a refusal leaves the process: three carried this block,
    # two exited 2 unconditionally (so a programming error was indistinguishable from a
    # gate refusal), and eight had no handler at all — a Gate CANON halt reached the
    # operator as a raw traceback with exit 1 and no machine-readable evidence.
    #
    # 2 = a gate refused (any `ArmatureError`; `GateFailure` is one). 1 = this tool crashed.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the `BUILD_CASCADE_HALT`
    # sentinel below, never on the code alone.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("BUILD_CASCADE_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
