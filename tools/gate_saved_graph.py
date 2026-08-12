#!/usr/bin/env python
"""gate_saved_graph — run admission on the SAVED file, and compare it to what we built.

    python tools/gate_saved_graph.py --saved=outputs/E09/route2/E09-B2-A3-t2v.saved.json \
                                     --api=outputs/E09/route2/E09-B2-A3-t2v.api.json \
                                     --seeds=specs/E09-A3-seeds.json \
                                     --out=outputs/E09/route2/E09-B2-A3-saved-admission.json

Why this exists as its own step. The cloud does not execute the API graph this repo builds;
it executes the SAVED graph, after a save->convert round trip that synthesises positions,
links and slot arrays. That round trip is a place a value can change, and CLAUDE.md's law is
that a `dry_run` PASS does not prove link sanity — so the file that will actually run is
gated in code, on its own bytes, before anything is submitted.

Two checks, and they answer different questions:

* **admission** — Gate ROUTE / S / L on the saved graph. Save format has a meaning API format
  does not: `control_after_generate`. A seed that reads `randomize` there is unpinned however
  concrete the number looks, and Gate S refuses it.
* **round-trip equality** — every value we wrote, found again in the saved file. A gate that
  passes on a graph which quietly lost the frame size or swapped an expert is a gate that
  passed on the wrong object.

Raises in-tool on any disagreement. Nothing here submits anything.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import route_gates as RG  # noqa: E402

TOOL_VERSION = "E09.3"

#: Where each API-format input lands in a save-format node's `widgets_values`. Written out
#: rather than zipped positionally, because the whole point is to catch a positional slip.
WIDGET_INDEX = {
    "UNETLoader": {"unet_name": 0, "weight_dtype": 1},
    "ModelSamplingSD3": {"shift": 0},
    "CLIPLoader": {"clip_name": 0, "type": 1, "device": 2},
    "VAELoader": {"vae_name": 0},
    "CLIPTextEncode": {"text": 0},
    "EmptyHunyuanLatentVideo": {"width": 0, "height": 1, "length": 2, "batch_size": 3},
    # save format inserts `control_after_generate` at index 2, which API format has no slot
    # for at all — so every index after the seed is shifted by one. This is exactly the
    # kind of off-by-one that a positional zip would sail past.
    "KSamplerAdvanced": {"add_noise": 0, "noise_seed": 1, "steps": 3, "cfg": 4,
                         "sampler_name": 5, "scheduler": 6, "start_at_step": 7,
                         "end_at_step": 8, "return_with_leftover_noise": 9},
    # Every input is a link, so there is nothing to compare — but the entry is present
    # ON PURPOSE. The table is looked up with `is None`, so an absent class halts and an
    # empty one passes: "this node has no literal widgets" is a recorded fact here, not the
    # silence of a node nobody thought about. (Caught by this check firing on its own hole
    # before the first submission, 2026-08-12.)
    "VAEDecode": {},
    "CreateVideo": {"fps": 0},
    "SaveImage": {"filename_prefix": 0},
    "SaveVideo": {"filename_prefix": 0, "format": 1, "codec": 2},
}


def round_trip(api_graph, saved_graph):
    """Every pinned value we wrote, found again in the saved file. Raises on any mismatch."""
    saved_by_id = {str(n["id"]): n for n in saved_graph["nodes"]}
    checked, problems = [], []
    for node_id, node in api_graph.items():
        s = saved_by_id.get(str(node_id))
        if s is None:
            problems.append(f"node {node_id} ({node['class_type']}) is absent from the "
                            f"saved file")
            continue
        if s["type"] != node["class_type"]:
            problems.append(f"node {node_id}: built {node['class_type']}, saved {s['type']}")
            continue
        index = WIDGET_INDEX.get(node["class_type"])
        if index is None:
            problems.append(f"no widget index recorded for {node['class_type']}; add one "
                            f"rather than skipping the node")
            continue
        wv = s.get("widgets_values") or []
        for name, value in node["inputs"].items():
            if isinstance(value, list):
                continue                      # a link, not a literal
            if name not in index:
                problems.append(f"node {node_id}.{name} has no recorded widget slot")
                continue
            i = index[name]
            if i >= len(wv):
                problems.append(f"node {node_id}.{name} expected at widget {i}, but the "
                                f"saved node has {len(wv)} widgets")
                continue
            got = wv[i]
            same = got == value or (
                isinstance(got, (int, float)) and isinstance(value, (int, float))
                and float(got) == float(value))
            checked.append({"node": node_id, "input": name, "built": value, "saved": got,
                            "equal": bool(same)})
            if not same:
                problems.append(f"node {node_id}.{name}: built {value!r}, saved {got!r}")
    extra = sorted(set(saved_by_id) - {str(k) for k in api_graph})
    if extra:
        problems.append(f"the saved file carries nodes we did not build: {extra}")
    if problems:
        raise RG.RouteGate(
            "the saved file is not the graph this repo built: " + "; ".join(problems),
            {"checked": checked, "problems": problems})
    return {"n_values_compared": len(checked), "all_equal": True, "values": checked}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--saved", required=True)
    ap.add_argument("--api", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    saved = RG.load_graph(a.saved)
    with open(a.api, encoding="utf-8") as fh:
        api = json.load(fh)
    with open(a.seeds, encoding="utf-8") as fh:
        registered = json.load(fh)["seeds"]

    equality = round_trip(api, saved)                       # 0 — is it even our graph
    gate_route = RG.verify(saved)                           # 1
    gate_s = RG.gate_s_registration(saved, registered)      # 2
    lat = RG.latents(saved)[0]
    gate_l = RG.frame_legality(lat["width"], lat["height"], lat["length"])   # 3
    if not gate_l["legal"]:
        raise RG.RouteGate(f"Gate L on the saved graph: {gate_l['problems']}", gate_l)

    record = {
        "tool": "gate_saved_graph", "tool_version": TOOL_VERSION,
        "experiment": "E09", "stage": "B2", "amendment": "A3",
        "saved_file": {"path": os.path.abspath(a.saved),
                       "sha256": hashlib.sha256(open(a.saved, "rb").read()).hexdigest()},
        "api_file": {"path": os.path.abspath(a.api),
                     "sha256": hashlib.sha256(open(a.api, "rb").read()).hexdigest()},
        "round_trip": equality,
        "gates": {"ROUTE": gate_route, "S": gate_s, "L": gate_l},
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

    print("SAVED_ADMISSION_OK " + json.dumps({
        "round_trip_values_compared": equality["n_values_compared"],
        "gate_ROUTE": gate_route["verdict"], "gate_S": gate_s["verdict"],
        "gate_L": f"{lat['width']}x{lat['height']}x{lat['length']} legal",
        "record": a.out}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("SAVED_ADMISSION_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2)
