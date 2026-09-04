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

--------------------------------------------------------------------------------
Why the key SHAPE is now refused rather than sorted, and why a slot knows its frame

"Ordered by their LOCAL name" was true of the maps this pipeline happened to write and
false of the sort it relied on. Measured 2026-09-03: an 81-entry map keyed `0.png` ..
`80.png` built cleanly and recorded a frame order running `0.png, 1.png, 10.png, 11.png`
… `8.png, 80.png, 9.png` — `10.png` in slot 2 — with every gate green; and a 4-frame map
carrying one extra `reference.png` key absorbed it as a fifth frame, `n_frames: 5`, same
green verdict. Lexicographic sorting of unpadded names does exactly the shuffle the
docstring above says sorting by server name would do.

So `frame_order` refuses any key that is not `^[0-9]{5}\\.png$` and any gap in `0..n-1`:
the map either carries a total order this tool can read or it halts. And because no gate
downstream related a batch SLOT index to a FRAME index — `gate_batch_topology` checks slot
names, distinctness and class, never position — `gate_slot_frame_index` closes that: slot
`k` of a batch node must hold the upload name of frame `k`. Both helpers are used by
`build_cascade_payload.py` and, through it, by the arm that spends.

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory; owner: the executor session. The uploads it references have **no delete endpoint**
on this API surface — they are content-addressed and inert unless a graph names them (the
E12 w2/w3 §7 convention).
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import assembly as AS  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateFailure)

TOOL_VERSION = "S03.2"

#: The only shape a frame key in an upload map may take. Zero padded to five digits, so a
#: lexicographic sort of the keys IS the numeric order — the property the ordering rule
#: assumed and never checked.
#: An upload map key: five zero-padded digits, optionally suffixed `.png`.
#:
#: The suffix is matched case-INSENSITIVELY (wave 8, F-d85dafd9, routed from
#: instruments-measure). This was the `.png` case family's last builders site and the
#: only member keyed on an upload KEY rather than a directory listing. Measured before
#: the widening: a map keyed `00000.PNG` refused with "4 key(s) that are not a
#: zero-padded frame name" — safe, but through the wrong clause, telling an operator
#: their keys are not zero-padded frame names when they are, while every consumer of the
#: same frames (`encode_control.py:126`, `invert_frames.py:70`) and both fetchers'
#: EXTRA andon (`fetch_run.verify_downloads`, carried here) read `.PNG` as a frame.
FRAME_KEY = re.compile(r"^[0-9]{5}(\.png)?$", re.IGNORECASE)


def frame_order(uploads):
    """The clip's local frame names in temporal order, or raise saying which key broke it.

    Two clauses, each for a failure that is silent in the other's presence:

    * a key that is not `NNNNN.png` — unpadded names sort lexicographically, so `10.png`
      lands in slot 2, and a key that is not a frame at all (`reference.png`) is absorbed
      as an extra frame and lengthens the clip;
    * a gap in `0..n-1` — every key well formed, the count reading right, and every frame
      after the hole off by one.

    Both were measured on this tool on 2026-09-03 producing a clean topology verdict.
    """
    keys = list(uploads)
    malformed = sorted(k for k in keys if not FRAME_KEY.match(str(k)))
    ev = {"gate": "ASSEMBLY", "n_keys": len(keys), "malformed": malformed}
    if malformed:
        raise AS.AssemblyGate(
            f"the upload map carries {len(malformed)} key(s) that are not a zero-padded "
            f"frame name — {malformed[:8]}{' …' if len(malformed) > 8 else ''}. Frame "
            f"order is taken from a sort of these keys, and an unpadded name sorts "
            f"lexicographically (10.png before 2.png) while a key that is not a frame at "
            f"all is absorbed as one. Both shuffle or lengthen the clip with every count "
            f"in every gate still reading right. Keys must match 00000..NNNNN or 00000.png..NNNNN.png",
            ev)
    # Wave-3 merge (coordinator, 2026-09-04): every upload map on this rig — eleven E02/E03
    # files — is keyed by the bare zero-padded index (`00000`), while the cascade route keys
    # its maps `00000.png`. The defect this gate exists for is UNPADDED names sorting
    # lexicographically; the five zero-padded digits catch that in either shape, so both are
    # accepted — but one map must use one shape, because `00000` sorts before `00000.png`
    # and a mixed map has no single order to check.
    #
    # Each key's suffix VERBATIM, not normalised. Widening the case above must not reach
    # this line: the invariant here is SORT ORDER, and '.PNG' sorts before '.png' in ASCII,
    # so a map mixing the two cases genuinely has no single order and must still refuse —
    # through the mixed-shape clause below, which is the sentence that describes it. Taking
    # the suffix verbatim also keeps `want` reconstructing the operator's own key spelling.
    suffixes = {str(k)[5:] for k in keys}
    if len(suffixes) > 1:
        raise AS.AssemblyGate(
            f"the upload map mixes frame-key shapes {sorted(suffixes)!r} (bare 00000, "
            f".png-suffixed, or a differently-CASED suffix); a mixed map has no single "
            f"sort order, and '.PNG' sorts before '.png'. Use one shape throughout",
            {**ev, "suffixes": sorted(suffixes)})
    suffix = next(iter(suffixes)) if suffixes else ""
    ordered = sorted(keys)
    want = [f"{i:05d}{suffix}" for i in range(len(keys))]
    missing = [w for w in want if w not in uploads]
    ev["missing"] = missing
    if ordered != want:
        raise AS.AssemblyGate(
            f"the upload map's frame indices are not 0..{len(keys) - 1} with no gaps: "
            f"missing {missing[:8]}{' …' if len(missing) > 8 else ''}. A hole leaves every "
            f"frame after it off by one, and the count still reads right",
            ev)
    return ordered


def frame_source_ids(names, first_image_id):
    """The LoadImage node id holding each frame, in frame order.

    P3's other half: the shared topology gate is being taught to take these and compare
    slot k to frame k. Supplied by every caller here regardless of whether the gate it is
    handed to declares a parameter for them yet.
    """
    return [str(int(first_image_id) + i) for i in range(len(names))]


def gate_slot_frame_index(graph, names, slot_plan, first_image_id):
    """Gate ASSEMBLY · ANDON — batch slot k holds the upload name of the frame at k.

    `slot_plan` is `[(batch_node_id, first_frame_index, stop_frame_index), …]` in group
    order — the `(start, stop)` spans `cascade_plan` already produced, which every caller
    holds. Slot `k` of that node must resolve to a `LoadImage` carrying
    `names[first_frame_index + k]`, for every k in the span. The flat chain passes one
    entry; the cascade passes one per group.

    **The andon is on the direction the invariant does not bound.** `gate_batch_topology`
    and `gate_cascade_topology` check slot NAMES, source DISTINCTNESS and source CLASS, and
    (in the cascade) that the GROUP nodes appear in order. None of them relates a slot
    index to a frame index, so two slots swapped inside a batch leaves every count, every
    name and every group order correct and the clip out of sequence — the same defect
    `fetch_t2v_run.py` exists to catch on the way back, with no equivalent on the way out.

    **The population is the PLAN, and that is wave 6's correction.** Until 2026-09-04 the
    loop ran over `[k for k in inputs if k.startswith("images.image")]` — whatever dotted
    keys HAPPENED to exist on the node — while the verdict was built from `len(names)`, a
    number describing the clip rather than the inspection. Measured on a 6-frame assembly
    graph: the batch replaced by a bare `images` list PASSED with "6 frame(s) checked"
    having inspected zero slots; the tail dropped so only `image0..2` survived PASSED with
    the same verdict having inspected three; the batch node REMOVED from the graph
    entirely PASSED having inspected nothing, because `graph.get(str(nid)) or {}` turns an
    absent node into an empty inputs dict and an empty loop. A contiguous truncation could
    not fire it at any length, because dropping N keys also shortened the loop by N. The
    only missing-slot shape that fired it was a HOLE. All three vacuous shapes are caught
    upstream by `gate_batch_topology`, which runs first at every production call site
    today — but this gate is exported for standalone use, and a verdict naming a property
    no code checked is this repo's named worst class.
    """
    ev = {"gate": "ASSEMBLY_slot_frame_index", "andon": "slot_frame_index",
          "n_frames": len(names), "first_image_id": int(first_image_id),
          "slot_plan": [[str(nid), int(start), int(stop)] for nid, start, stop in slot_plan]}

    # ---- COVERAGE, wave 8 (F-ad45bc42). The population came from the CALLER's plan and no
    # clause required that plan to cover the clip, so the gate returned a PASS verdict
    # having inspected any number of slots INCLUDING ZERO — and the verdict string printed
    # both numbers side by side with nothing comparing them. Measured 2026-09-04 on the
    # real 81-frame cascade graph from `build_cascade_payload.build(names, fps=16.0,
    # group_size=AS.GROUP_SIZE)` (3 group nodes): the full plan returned "…81 slot(s)
    # inspected against a clip of 81 frame(s)"; `slot_plan=[]` returned "every slot across
    # 0 batch node(s) holds the upload name of its own frame index, 0 slot(s) inspected
    # against a clip of 81 frame(s)"; a ONE-GROUP plan returned the same green sentence at
    # 27 of 81; and a plan ONE GROUP SHORT — the shape an un-strict `zip` produces —
    # returned it at 54 of 81. No clause fired in any of the three. Both production call
    # sites build the plan through a `zip` (`build_cascade_payload.py:163`,
    # `build_r2v_payload.py:254`), which truncates to the shorter of `cascade_plan(...)` and
    # the group-id list rather than raising; both pass `strict=True` now, and this clause is
    # the andon that does not depend on them doing so.
    covered, overlapping, gaps = set(), set(), []
    cursor = 0
    for nid, start, stop in slot_plan:
        start, stop = int(start), int(stop)
        if stop <= start:
            gaps.append(f"node {nid} is planned an empty or reversed span [{start}, {stop})")
        if start != cursor:
            gaps.append(f"node {nid}'s span starts at {start}, and the plan's previous "
                        f"span ended at {cursor}; the plan is not contiguous")
        for frame in range(start, stop):
            (overlapping if frame in covered else covered).add(frame)
        cursor = max(cursor, stop)
    missing = sorted(set(range(len(names))) - covered)
    outside = sorted(f for f in covered if f >= len(names))
    if gaps or missing or overlapping or outside:
        ev.update({"frames_planned": len(covered), "frames_in_clip": len(names),
                   "frames_never_planned": missing[:12],
                   "frames_planned_twice": sorted(overlapping)[:12],
                   "frames_planned_past_the_clip": outside[:12],
                   "coverage_problems": gaps})
        raise AS.AssemblyGate(
            f"the slot plan does not cover the clip: {len(covered)} of {len(names)} "
            f"frame(s) are planned onto a batch node"
            + (f", {len(missing)} never ({missing[:6]}…)" if missing else "")
            + (f", {len(overlapping)} twice" if overlapping else "")
            + (f", {len(outside)} past the end of the clip" if outside else "")
            + ("; " + "; ".join(gaps[:4]) if gaps else "")
            + ". A gate whose population is the caller's plan reports what it inspected, "
              "not what the clip needed, and a swap inside an unplanned group ships as an "
              "out-of-order clip", ev)

    problems, inspected = [], 0
    for nid, start, stop in slot_plan:
        span = int(stop) - int(start)
        node = graph.get(str(nid))
        if node is None:
            problems.append(f"node {nid} is not in the graph at all, so its {span} slot(s) "
                            f"were never inspected — an absent node used to read as an "
                            f"empty loop and pass")
            continue
        if node.get("class_type") != "BatchImagesNode":
            problems.append(f"node {nid} is a {node.get('class_type')!r}, not a "
                            f"BatchImagesNode; there are no slots on it to inspect")
            continue
        inputs = node.get("inputs") or {}
        want_keys = {f"images.image{k}" for k in range(span)}
        got_keys = {k for k in inputs if k == "images" or k.startswith("images.image")}
        if got_keys != want_keys:
            problems.append(
                f"node {nid} carries dotted keys {sorted(got_keys)}, and the plan puts "
                f"{span} frame(s) ({sorted(want_keys)}) on it. A bare `images` list or a "
                f"truncated tail used to SHORTEN the loop rather than fail it")
            continue
        for k in range(span):
            frame = int(start) + k
            inspected += 1
            link = inputs.get(f"images.image{k}")
            src = str(link[0]) if isinstance(link, list) and len(link) == 2 else None
            loader = graph.get(src) if src else None
            got = (loader.get("inputs") or {}).get("image") if loader else None
            want = names[frame] if frame < len(names) else None
            if got != want:
                problems.append(
                    f"node {nid} slot {k} resolves to {got!r} via {src!r}; frame {frame} "
                    f"of the clip is {want!r}")
    ev["slots_inspected"] = inspected
    ev["frames_in_clip"] = len(names)
    if inspected != len(names):
        problems.append(f"{inspected} slot(s) were inspected against a clip of "
                        f"{len(names)} frame(s); the two numbers are the gate's whole "
                        f"claim and they must be the same number")
    if problems:
        ev["problems"] = problems
        raise AS.AssemblyGate(
            "a batch slot does not hold the frame the clip's order puts there: "
            + "; ".join(problems[:6]) + (" …" if len(problems) > 6 else ""), ev)
    ev["verdict"] = (f"every slot across {len(slot_plan)} batch node(s) holds the upload "
                     f"name of its own frame index, {inspected} slot(s) inspected against "
                     f"a clip of {len(names)} frame(s)")
    return ev

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
    #
    # `os.makedirs` used to sit HERE, above --uploads being read and above every gate
    # below. A refused build therefore left an empty run directory beside real ones, to be
    # read later as a run that happened. It now sits below the last in-tool gate, matching
    # the invariant build_payload.py states for Gate CANON.

    with open(a.uploads, encoding="utf-8") as fh:
        uploads = json.load(fh)
    order = frame_order(uploads)             # LOCAL names: 00000.png .. 00080.png
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
    ordered_ids = frame_source_ids(names, FIRST_IMAGE_ID)
    gate_topo = AS.gate_batch_topology(wf, len(names), BATCH_ID, VIDEO_ID, SAVE_ID,
                                       expected_sources=ordered_ids)
    gate_index = gate_slot_frame_index(wf, names, [(BATCH_ID, 0, len(names))],
                                      FIRST_IMAGE_ID)
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
        "frame_source_ids": list(ordered_ids),
        "gates": {"ASSEMBLY_paid": gate_paid, "ASSEMBLY_topology": gate_topo,
                  "ASSEMBLY_slot_frame_index": gate_index, "ROUTE": gate_route},
    }

    # Below the last in-tool gate: a refuse leaves no output directory.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories
    graph_path = os.path.join(out, "S03-assembly.api.json")
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=1)
    with open(os.path.join(out, "S03-assembly-payload-record.json"), "w",
              encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    print(f"nodes            {len(wf)}")
    print(f"paid-node gate   {gate_paid['verdict']}")
    print(f"topology gate    {gate_topo['verdict']}")
    print(f"slot->frame gate {gate_index['verdict']}")
    print(f"route components {len(gate_route['components'])}  "
          f"seeds {len(gate_route['seeds'])}  latents {len(gate_route['latents'])}")
    print(f"frame legality   {[f['legal'] for f in gate_route['frame_legality']]}")
    print(f"BUILD_ASSEMBLY_OK {graph_path}")
    return wf


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9). The nine builders and the two fetchers
    # disagreed three ways on how a refusal leaves the process: three carried this block,
    # two exited 2 unconditionally (so a programming error was indistinguishable from a
    # gate refusal), and eight had no handler at all — a Gate CANON halt reached the
    # operator as a raw traceback with exit 1 and no machine-readable evidence.
    #
    # 2 = a gate refused (any `ArmatureError`; `GateFailure` is one). 1 = this tool crashed.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the `BUILD_ASSEMBLY_HALT`
    # sentinel below, never on the code alone.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("BUILD_ASSEMBLY_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
