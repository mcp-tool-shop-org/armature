#!/usr/bin/env python
"""build_r2v_payload — the composed route's graph, built in-repo. E13's re-arm.

    <venv-python> tools\\build_r2v_payload.py --arm=A1 --seed=2026081351 \\
        --refs=outputs/E13/A1_refs/A1-reference-record.json \\
        --seeds=specs/E13-seeds.json --prompt-file=specs/E13-prompt.json --out=<dir>

    <venv-python> tools\\build_r2v_payload.py --arm=A2 --seed=2026081351 \\
        --uploads=<S03 uploads.json> --seeds=... --prompt-file=... --out=<dir>

**A served template is a reference, never a route.** The served `api_wan2_7_r2v` template
exists and was used only to price the tier; this graph is built here from the node contract
`get_node` returned, and it is gated here before anything is submitted.

The arms differ in ONE thing — what sits in the reference slot:

* **A1** — `model.reference_images.image1…image4`, the four composited kit views, fed by
  `LoadImage` nodes in the slot order the reference record pins.
* **A2** — `model.reference_videos.video1`, fed **directly by the cascade's own
  `CreateVideo`**, in the same graph. There is no upload of a video anywhere: E02 and the
  E13 halt both measured that no video loader exists on this API surface, and the rescue
  the halt ruling proposed was never to upload one but to CONSTRUCT it. Stage 0 measured
  that construction carrying all 81 frames in order; this wires its output into the slot
  instead of saving it.

Everything else is common and pinned: model, resolution, ratio, duration, prompt, negative
prompt, watermark, and the seed — which comes from the committed registration and nowhere
else.

⚠ **`characterN` ↔ slot binding is NOT VISIBLE.** Nothing in the node contract says which
reference `character1` refers to. This tool records exactly what is sent per slot, in
order, and claims nothing about what binds. Observing that is the experiment's job.

Compensator (NAMED_COMPENSATORS): writes JSON under `outputs/`. Compensator: delete the
directory; owner: the executor session. It submits nothing.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_cascade_payload as CASCADE  # noqa: E402
from armature_core import assembly as AS  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402
from armature_core.canon import add_spend_flags, gate_write  # noqa: E402

TOOL_VERSION = "E13.1"

TIER = "wan2.7-r2v"
#: Kept clear of the cascade's own 200..280 / 400..410 / 420 range, so an A2 graph reads as
#: two named parts rather than as one block of numbers.
FIRST_IMAGE_ID = 100
R2V_ID = 500
SAVE_ID = 501

#: `Wan2ReferenceVideoApi` is `output_node: false` (get_node, 2026-08-13) — it emits a
#: VIDEO and saves nothing, so the graph supplies its own save class.
SAVE_CLASS = "SaveVideo"


def build(*, arm, seed, prompt, negative, refs=None, upload_names=None,
          resolution="720P", ratio="16:9", duration=5, watermark=False,
          prefix="video/E13_r2v", group_size=AS.GROUP_SIZE):
    """The API-format graph for one submission.

    `refs` (A1) is the list of uploaded plate names IN SLOT ORDER.
    `upload_names` (A2) is the list of uploaded FRAME names in frame order.
    """
    wf = {}
    inputs = {
        "model": TIER,
        "model.prompt": prompt,
        "model.negative_prompt": negative,
        "model.resolution": resolution,
        "model.ratio": ratio,
        "model.duration": int(duration),
        "seed": int(seed),
        "watermark": bool(watermark),
    }
    cascade_ids = None

    if arm == "A1":
        if not refs:
            raise RG.RouteGate("arm A1 needs reference images", {"arm": arm})
        for i, name in enumerate(refs):
            nid = str(FIRST_IMAGE_ID + i)
            wf[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
            inputs[f"model.reference_images.image{i + 1}"] = [nid, 0]
    elif arm == "A2":
        if not upload_names:
            raise RG.RouteGate("arm A2 needs the cascade's frame uploads", {"arm": arm})
        cascade, group_ids = CASCADE.build(upload_names, fps=16.0, group_size=group_size)
        # Everything the cascade builds EXCEPT its own SaveVideo: here the constructed
        # VIDEO goes into the reference slot instead of to disk.
        cascade.pop(str(CASCADE.SAVE_ID))
        wf.update(cascade)
        cascade_ids = {"groups": group_ids, "final_batch": str(CASCADE.FINAL_BATCH_ID),
                       "create_video": str(CASCADE.VIDEO_ID)}
        inputs["model.reference_videos.video1"] = [str(CASCADE.VIDEO_ID), 0]
    else:
        raise RG.RouteGate(f"unknown arm {arm!r}; the spec names A1 and A2", {"arm": arm})

    wf[str(R2V_ID)] = {"class_type": "Wan2ReferenceVideoApi", "inputs": inputs}
    wf[str(SAVE_ID)] = {"class_type": SAVE_CLASS, "inputs": {
        "filename_prefix": prefix, "format": "auto", "codec": "auto",
        "video": [str(R2V_ID), 0]}}
    return wf, cascade_ids


def gate_seed_registered(seed, registered):
    """Gate S · ANDON, at build time — this number is on the committed list.

    `route_gates.gate_s_registration` runs the same clause against the SAVED file the cloud
    converts. This one runs before the graph exists on the cloud at all, because the
    cheapest place to refuse an unregistered seed is before anything has been submitted
    for it.
    """
    ev = {"gate": "S", "seed": int(seed), "registered": list(registered)}
    if int(seed) not in [int(s) for s in registered]:
        raise RG.RouteGate(
            f"seed {seed} is not on the committed registration {sorted(registered)}. A rule "
            f"forbids; a list removes the possibility, and git timestamps the list ahead of "
            f"the artifacts it governs", ev)
    ev["verdict"] = f"seed {int(seed)} is on the pre-registered list"
    return ev


def gate_one_paid_node(graph):
    """Gate CEILING · ANDON — exactly one billable node, so one submission is one charge.

    The spec's ceiling is counted in SUBMISSIONS at 106-211 credits each. That arithmetic
    is only true if a submission bills once. A graph carrying two partner nodes would run,
    would look correct in every other gate, and would silently double the spend against a
    ceiling computed per submission.
    """
    paid = sorted(nid for nid, n in graph.items()
                  if n.get("class_type") == "Wan2ReferenceVideoApi")
    ev = {"gate": "CEILING", "paid_nodes": paid, "n_paid": len(paid)}
    if len(paid) != 1:
        raise RG.RouteGate(
            f"the graph carries {len(paid)} `Wan2ReferenceVideoApi` node(s); the spec's "
            f"credit ceiling counts one charge per submission, and that arithmetic is only "
            f"true at exactly one", ev)
    ev["verdict"] = f"one billable node ({paid[0]}); one submission is one charge"
    return ev


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=("A1", "A2"))
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--seeds", required=True, help="the committed seed registration")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--refs", default=None, help="A1: the reference record JSON")
    ap.add_argument("--uploads", default=None, help="A2: the frame uploads map JSON")
    ap.add_argument("--resolution", default="720P")
    ap.add_argument("--ratio", default="16:9")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--group", type=int, default=AS.GROUP_SIZE)
    ap.add_argument("--prefix", default=None)
    add_spend_flags(ap)
    a = ap.parse_args(argv)

    out = os.path.abspath(a.out)

    with open(a.seeds, encoding="utf-8") as fh:
        registration = json.load(fh)
    with open(a.prompt_file, encoding="utf-8") as fh:
        prompt_spec = json.load(fh)
    gate_write(
        a.subject, a.canon_prompt or prompt_spec["prompt"],
        no_canon=a.no_canon, out_dir=out,
    )
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    gate_seed = gate_seed_registered(a.seed, registration["seeds"])

    refs = ref_record = upload_names = frame_order = None
    if a.arm == "A1":
        with open(a.refs, encoding="utf-8") as fh:
            ref_record = json.load(fh)
        refs = [v["upload_name"] for v in ref_record["views"]]
    else:
        with open(a.uploads, encoding="utf-8") as fh:
            uploads = json.load(fh)
        frame_order = sorted(uploads)          # LOCAL names carry the frame order
        upload_names = [uploads[k] for k in frame_order]

    prefix = a.prefix or f"video/E13_{a.arm}_seed{a.seed}"
    wf, cascade_ids = build(arm=a.arm, seed=a.seed, prompt=prompt_spec["prompt"],
                            negative=prompt_spec["negative_prompt"], refs=refs,
                            upload_names=upload_names, resolution=a.resolution,
                            ratio=a.ratio, duration=a.duration, watermark=False,
                            prefix=prefix, group_size=a.group)

    # ---- the gates, in code, before anything is submitted.
    #
    # Gate ROUTE walks the graph for banned components and for Gate PAIR. `frame=None` is
    # correct and is NOT a skip: this tier pins no latent and receives no pixel dimension,
    # so the pixel clause has nothing to decide — which is exactly why the enum clause
    # below exists and is reported beside it rather than instead of it.
    gate_route = RG.verify(wf, family="wan", require_pinned_seeds=True, hosted_tier=TIER)
    gate_l = gate_route["hosted_frame_legality"]
    gate_ceiling = gate_one_paid_node(wf)

    gates = {"S_build_time": gate_seed, "ROUTE": gate_route, "L_hosted": gate_l,
             "CEILING_one_paid_node": gate_ceiling}
    if a.arm == "A2":
        gates["CASCADE_ceiling"] = AS.gate_slot_ceiling(wf, cap=max(a.group, 1))
        gates["CASCADE_topology"] = AS.gate_cascade_topology(
            wf, len(upload_names), cascade_ids["groups"], CASCADE.FINAL_BATCH_ID,
            CASCADE.VIDEO_ID, R2V_ID, "model.reference_videos.video1",
            group_size=a.group)

    node_inputs = wf[str(R2V_ID)]["inputs"]
    record = {
        "tool": "build_r2v_payload", "tool_version": TOOL_VERSION,
        "experiment": "E13", "arm": a.arm, "tier": TIER,
        "seed": int(a.seed), "seed_registration": os.path.abspath(a.seeds),
        "prompt_file": os.path.abspath(a.prompt_file),
        "prompt_sha256": hashlib.sha256(
            json.dumps(prompt_spec, sort_keys=True).encode("utf-8")).hexdigest(),
        "filename_prefix": prefix, "n_nodes": len(wf),
        # The FULL payload, every dotted field, exactly as sent.
        "payload": dict(node_inputs),
        "slot_order": [k for k in node_inputs if k.startswith("model.reference_")],
        "slot_binding_note": (
            "characterN <-> slot binding is NOT VISIBLE in the node contract. What is "
            "recorded here is exactly what was SENT per slot, in order. Nothing is claimed "
            "about which reference `character1` resolves to; that is observed from output."),
        "references": ref_record["views"] if ref_record else None,
        "reference_video": (
            {"constructed_in_graph": True, "create_video_node": cascade_ids["create_video"],
             "n_frames": len(upload_names), "fps": 16.0,
             "frame_order": frame_order, "group_nodes": cascade_ids["groups"],
             "why": ("no video loader exists on this API surface (E02, and the E13 halt "
                     "re-measured it), so the VIDEO is CONSTRUCTED in-graph and wired "
                     "straight into the slot rather than uploaded")}
            if a.arm == "A2" else None),
        "node_ids": {"first_image": FIRST_IMAGE_ID, "r2v": R2V_ID, "save": SAVE_ID,
                     "cascade": cascade_ids},
        "gates": gates,
        "gate_pair_note": (
            "Gate PAIR is n/a on this tier and is RECORDED as n/a, not skipped: the graph "
            "loads no local weights, so no conditioning class can be unpaired from a "
            "weight family. route_gates.pairing() ran and examined an empty set."),
        "gate_l_note": (
            "The pixel clause of Gate L is INAPPLICABLE here, not passed: this tier "
            "receives no width, height or frame count from us. Gate ROUTE records that "
            "verbatim in `frame_legality_verdict` and checks the tier's own enum "
            "constraints instead, which is the clause that binds and can fail."),
    }

    graph_path = os.path.join(out, f"E13-{a.arm}-seed{a.seed}.api.json")
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=1)
    with open(os.path.join(out, f"E13-{a.arm}-seed{a.seed}-payload-record.json"), "w",
              encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    print(f"arm              {a.arm}")
    print(f"nodes            {len(wf)}")
    print(f"seed gate        {gate_seed['verdict']}")
    print(f"ceiling gate     {gate_ceiling['verdict']}")
    print(f"route            components {len(gate_route['components'])}  "
          f"seeds {len(gate_route['seeds'])}  pinned "
          f"{sum(1 for s in gate_route['seeds'] if s['pinned'])}")
    print(f"gate L (hosted)  {a.resolution} {a.ratio} {a.duration}s -> legal "
          f"{gate_l['legal']}")
    print(f"slots            {record['slot_order']}")
    print(f"BUILD_R2V_OK     {graph_path}")
    return wf, record


if __name__ == "__main__":
    main()
