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

TOOL_VERSION = "E10.1"

#: Where each API-format input lands in a save-format node's `widgets_values`. Written out
#: rather than zipped positionally, because the whole point is to catch a positional slip.
WIDGET_INDEX = {
    # ---- E10, 2026-08-12: the Animate route's classes. `KSampler` has the same
    # control_after_generate insertion `KSamplerAdvanced` does, one slot earlier, which is
    # the shift a positional zip would sail past for the second time.
    "KSampler": {"seed": 0, "steps": 2, "cfg": 3, "sampler_name": 4, "scheduler": 5,
                 "denoise": 6},
    "WanAnimateToVideo": {"width": 0, "height": 1, "length": 2, "batch_size": 3,
                          "continue_motion_max_frames": 4, "video_frame_offset": 5},
    # ---- E11, 2026-08-12: the I2V route's conditioning node. Four widgets, not six: its
    # schema carries no `continue_motion_max_frames` / `video_frame_offset` at all, so a
    # table entry copied from the Animate row would look right and compare `batch_size`
    # against nothing.
    "WanImageToVideo": {"width": 0, "height": 1, "length": 2, "batch_size": 3},
    "LoadImage": {"image": 0},
    # Every input this graph pins is a link; the empty entry is a recorded fact, not the
    # silence of a class nobody thought about (the table is looked up with `is None`).
    "TrimVideoLatent": {},
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
    "CreateVideo": {"fps": 0, "bit_depth": 1},
    "SaveImage": {"filename_prefix": 0},
    "SaveVideo": {"filename_prefix": 0, "format": 1, "codec": 2},
    # E11 wave 2's camera tier. **These two rows were written because this check HALTED the
    # wave-2 submission on its own hole** — the second time it has done so, after the
    # `VAEDecode` case recorded above, and both times before a credit was spent rather than
    # after. The gate refused to skip a class it had no row for, which is the entire point
    # of looking the table up with `is None`.
    #
    # Unlike every row above, these indices are not a derivation: they were READ OFF the
    # save-format file the cloud converted, 2026-08-12 —
    # `WanCameraEmbedding.widgets_values == ["Static", 832, 480, 65, 1, 0.5, 0.5, 0.5, 0.5]`
    # and `WanCameraImageToVideo.widgets_values == [832, 480, 65, 1]`. That makes them the
    # empirical SECOND reading that `route_gates.LATENT_NODES` promised and could not supply
    # from a served template, and they agree with the `get_node` schema order that
    # `route_gates.CAMERA_NODES` was derived from. Neither class takes a
    # `control_after_generate` insertion — that shift is particular to the sampler above.
    "WanCameraEmbedding": {"camera_pose": 0, "width": 1, "height": 2, "length": 3,
                           "speed": 4, "fx": 5, "fy": 6, "cx": 7, "cy": 8},
    "WanCameraImageToVideo": {"width": 0, "height": 1, "length": 2, "batch_size": 3},
    # ---- S03, 2026-08-13: the assembly chain's batch node. Every input is a dotted
    # COMFY_AUTOGROW_V3 link (`images.image0` …), so there is no literal to compare and the
    # row is empty — a recorded fact, exactly as `VAEDecode` and `TrimVideoLatent` above,
    # because the table is looked up with `is None` and an ABSENT class halts the check.
    #
    # This row is added by the spec that actually EXECUTES the class. E13's executor was
    # ruled correct for declining to teach this table for a route that submitted nothing:
    # a green row for an untravelled path marks it walked. `CreateVideo`, `SaveVideo` and
    # `LoadImage` — the assembly chain's other three classes — already carried rows above,
    # so this is the only one S03 adds.
    "BatchImagesNode": {},
    # ---- E13's re-arm, 2026-08-13: the composed route's hosted generator. The spec owed
    # this row to "the first spec that arms this tier", and the halt-era executor was ruled
    # correct for declining to write it for a route that submitted nothing.
    #
    # **Read off the file the cloud converted**, not derived — the standard the camera rows
    # were held to. The converted node's widgets_values are:
    #   ["wan2.7-r2v", <prompt>, <negative>, "720P", "16:9", 5, 2026081351, "fixed", false]
    # and the `get_node` declaration order (model, prompt, negative_prompt, resolution,
    # ratio, duration, seed, watermark, with the IMAGE/VIDEO reference slots dropped as
    # links) agrees with it — two readings, required to agree, and they do.
    #
    # ⚠ `control_after_generate` is inserted at index 7, immediately after the seed, which
    # shifts `watermark` from the 7 a positional zip would give it to 8. That is exactly the
    # off-by-one this table exists to catch, and it is the third class in it to carry the
    # insertion after the two samplers.
    "Wan2ReferenceVideoApi": {"model": 0, "model.prompt": 1, "model.negative_prompt": 2,
                              "model.resolution": 3, "model.ratio": 4, "model.duration": 5,
                              "seed": 6, "watermark": 8},
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


def link_round_trip(api_graph, saved_graph):
    """Every socket we wired is wired there, and every socket we left empty is empty there.

    The value round trip above compares literals; this compares TOPOLOGY, and it is the
    clause E08 checked by eye. The failure it guards is specific and silent: a save/convert
    round trip that attached something to `background_video` would produce a graph that
    runs, costs the same, and makes the scene-from-prompt clause unmeasurable — while every
    widget value still matched. It binds in both directions for the same reason Gate S
    does: a lost link and an invented link are different defects and both pass a
    value-only comparison.
    """
    saved_by_id = {str(n["id"]): n for n in saved_graph["nodes"]}
    wired, empty, problems = [], [], []
    for node_id, node in api_graph.items():
        s = saved_by_id.get(str(node_id))
        if s is None:
            continue                                  # `round_trip` already raised on this
        for slot in (s.get("inputs") or []):
            name = slot.get("name")
            ours = node["inputs"].get(name)
            we_linked = isinstance(ours, list)
            they_linked = slot.get("link") is not None
            if we_linked and not they_linked:
                problems.append(f"node {node_id}.{name}: we wired it and the saved file "
                                f"carries no link")
            elif they_linked and not we_linked:
                problems.append(f"node {node_id}.{name}: the saved file wired it and we "
                                f"left it empty")
            elif we_linked:
                wired.append(f"{node_id}.{name}")
            else:
                empty.append(f"{node_id}.{name}")
    if problems:
        raise RG.RouteGate(
            "the saved file's topology is not the topology this repo built: "
            + "; ".join(problems),
            {"wired": wired, "empty_in_both": empty, "problems": problems})
    return {"n_links": len(wired), "links": sorted(wired),
            "optional_sockets_empty_in_both": sorted(empty)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--saved", required=True)
    ap.add_argument("--api", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--experiment", default="E09")
    ap.add_argument("--stage", default="B2")
    ap.add_argument("--hosted-tier", default=None,
                    help="a tier from route_gates.HOSTED_TIER_RULES whose graph carries no "
                         "pixel dimension at all (wan2.7-r2v). Gate L's pixel clause is "
                         "INAPPLICABLE there, not skipped: the tier's own enum constraints "
                         "are checked instead and an illegal one still raises")
    ap.add_argument("--frame", default=None,
                    help="width,height,length — the shape the caller knows it is "
                         "generating. Gate L is INDETERMINATE and raises on a graph whose "
                         "latent it cannot read, so a route whose conditioning node sizes "
                         "its own latent states the shape here (argparse eats leading "
                         "minus signs: pass as --frame=832,480,81)")
    a = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    saved = RG.load_graph(a.saved)
    with open(a.api, encoding="utf-8") as fh:
        api = json.load(fh)
    with open(a.seeds, encoding="utf-8") as fh:
        registered = json.load(fh)["seeds"]

    frame = None
    if a.frame:
        parts = [int(v) for v in a.frame.split(",")]
        if len(parts) != 3:
            raise RG.RouteGate(f"--frame={a.frame!r} is not width,height,length; two out "
                               f"of three proves nothing", {"supplied": a.frame})
        frame = tuple(parts)

    equality = round_trip(api, saved)                       # 0 — is it even our graph
    topology = link_round_trip(api, saved)                  # 0b — is it wired as we wired it
    gate_route = RG.verify(saved, frame=frame, hosted_tier=a.hosted_tier)   # 1
    gate_s = RG.gate_s_registration(saved, registered)      # 2
    checked = [f for f in gate_route["frame_legality"]]     # 3 — already raised if illegal
    if a.hosted_tier:
        # The honest Gate L line for a tier that has no pixels to report.
        t = gate_route["hosted_frame_legality"]
        shapes = [f"{t['resolution']} {t['ratio']} {t['duration_s']}s"]
    else:
        shapes = sorted({f"{f['width']}x{f['height']}x{f['length']}" for f in checked})

    record = {
        "tool": "gate_saved_graph", "tool_version": TOOL_VERSION,
        "experiment": a.experiment, "stage": a.stage,
        "saved_file": {"path": os.path.abspath(a.saved),
                       "sha256": hashlib.sha256(open(a.saved, "rb").read()).hexdigest()},
        "api_file": {"path": os.path.abspath(a.api),
                     "sha256": hashlib.sha256(open(a.api, "rb").read()).hexdigest()},
        "round_trip": equality,
        "topology_round_trip": topology,
        "gates": {"ROUTE": gate_route, "S": gate_s, "L": checked},
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

    print("SAVED_ADMISSION_OK " + json.dumps({
        "round_trip_values_compared": equality["n_values_compared"],
        "links_compared": topology["n_links"],
        "optional_sockets_empty_in_both": topology["optional_sockets_empty_in_both"],
        "gate_ROUTE": gate_route["verdict"], "gate_S": gate_s["verdict"],
        "gate_L": f"{', '.join(shapes)} legal ({gate_route['frame_legality_verdict']})",
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
