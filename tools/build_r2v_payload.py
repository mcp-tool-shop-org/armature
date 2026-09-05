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
from build_assembly_payload import (  # noqa: E402
    canonical_payload_digest, read_seed_registration)
from armature_core import assembly as AS  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402
from armature_core.route_gates import RouteGate  # noqa: E402
from armature_core.canon import add_spend_flags  # noqa: E402
from armature_core.errors import GateSSeedRegistration  # noqa: E402
# WAVE 25, F-af838b99: `GateFailure` / `ArmatureError` used to be named in this
# file's own `__main__` block, which chose the exit code by `isinstance`. That
# choice belongs to `armature_core.parts.halt_outcome` now, so the names that are
# no longer referenced here are dropped rather than left dangling.
from canon_gate import canon_line, canon_spend  # noqa: E402

TOOL_VERSION = "E13.2"

TIER = "wan2.7-r2v"
#: Kept clear of the cascade's own 200..280 / 400..410 / 420 range, so an A2 graph reads as
#: two named parts rather than as one block of numbers.
FIRST_IMAGE_ID = 100
R2V_ID = 500
SAVE_ID = 501

#: `Wan2ReferenceVideoApi` is `output_node: false` (get_node, 2026-08-13) — it emits a
#: VIDEO and saves nothing, so the graph supplies its own save class.
SAVE_CLASS = "SaveVideo"


class SpendCeiling(RouteGate):
    """Gate CEILING, raised under its own id.

    Wave 16, F-f85c37f0. `gate_one_paid_node` built `ev = {"gate": "CEILING", ...}` and
    raised it as a bare `RouteGate`, whose class attribute is `gate = "ROUTE"`, so the
    record's `gates.CEILING` entry and the printed `[ROUTE] …` halt line named two
    different gate ids for one event. `gate_seed_registered` had the same shape with `S`
    and no `andon`/`clause` keys at all; that one is fixed by raising the id's EXISTING
    owner (`errors.GateSSeedRegistration`, the class `build_lora_arm_payload.gate_s`
    already raises), because `tests/test_gates.py` forbids a second andon on an id another
    andon already uses. No class owned `CEILING`, so this one is defined.

    It is a `RouteGate`, so every caller that catches `RG.RouteGate` still catches it.

    ⚠ **The base is imported BY NAME, and that is load-bearing** (wave 18, F-d8593862).
    This was declared `class SpendCeiling(RG.RouteGate)` — the one family class in the
    whole tree with a DOTTED base — and `tests/test_gates._armature_error_family` builds
    its transitive base map from `b.id for b in node.bases if isinstance(b, ast.Name)`, so
    an `ast.Attribute` base contributes nothing and this class never joined the family.
    Measured on the base tree: `'SpendCeiling' in _armature_error_family(TOOLS_DIR)` was
    **False**, while `GateSSeedRegistration`, `PayloadOutHalt`, `SeedRegistrationError`,
    `FetchHalt`, `LedgerGate`, `TierGate` and `PayloadError` were all True; an AST sweep of
    `tools/**` for family classes with a dotted base returned exactly ONE row — this one.
    So the wave-16 evidence contract, the `POLICED` partition and the very clause this
    docstring cites (`tests/test_gates.py` forbidding a second andon on an id another andon
    already uses) all SKIPPED it. It happens to define no `__init__` today, so rule 5 held
    by luck rather than by check.

    The plain name changes no behaviour — `RouteGate` here is the same object `RG.RouteGate`
    names, and every caller catching `RG.RouteGate` still catches this class. It changes
    only whether the censuses can SEE it. Widening `test_gates`' own walk to resolve an
    `ast.Attribute` base by its final attribute name is the out-of-domain half and is a
    Stage B item; this half stands alone.
    """

    gate = "CEILING"


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
            raise RG.RouteGate(
                "arm A1 needs reference images",
                {"gate": "ROUTE", "andon": "RouteGate", "clause": "arm_input_missing",
                 "arm": arm, "flag": "--refs"})
        for i, name in enumerate(refs):
            nid = str(FIRST_IMAGE_ID + i)
            wf[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
            inputs[f"model.reference_images.image{i + 1}"] = [nid, 0]
    elif arm == "A2":
        if not upload_names:
            raise RG.RouteGate(
                "arm A2 needs the cascade's frame uploads",
                {"gate": "ROUTE", "andon": "RouteGate", "clause": "arm_input_missing",
                 "arm": arm, "flag": "--uploads"})
        cascade, group_ids = CASCADE.build(upload_names, fps=16.0, group_size=group_size)
        # Everything the cascade builds EXCEPT its own SaveVideo: here the constructed
        # VIDEO goes into the reference slot instead of to disk.
        cascade.pop(str(CASCADE.SAVE_ID))
        wf.update(cascade)
        cascade_ids = {"groups": group_ids, "final_batch": str(CASCADE.FINAL_BATCH_ID),
                       "create_video": str(CASCADE.VIDEO_ID)}
        inputs["model.reference_videos.video1"] = [str(CASCADE.VIDEO_ID), 0]
    else:
        raise RG.RouteGate(
            f"unknown arm {arm!r}; the spec names A1 and A2",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "unknown_arm",
             "arm": arm, "known": ["A1", "A2"]})

    wf[str(R2V_ID)] = {"class_type": R2V_CLASS, "inputs": inputs}
    wf[str(SAVE_ID)] = {"class_type": SAVE_CLASS, "inputs": {
        "filename_prefix": prefix, "format": "auto", "codec": "auto",
        "video": [str(R2V_ID), 0]}}
    return wf, cascade_ids


#: The hosted generator this route submits. Named once so Gate CEILING's "expected
#: identity" half and the builder cannot drift apart (wave 14, F-eec3f145).
R2V_CLASS = "Wan2ReferenceVideoApi"


def gate_seed_registered(seed, registered):
    """Gate S · ANDON, at build time — this number is on the committed list.

    `route_gates.gate_s_registration` runs the same clause against the SAVED file the cloud
    converts. This one runs before the graph exists on the cloud at all, because the
    cheapest place to refuse an unregistered seed is before anything has been submitted
    for it.
    """
    # ONE andon per receipt (wave 16, F-f85c37f0). This built `{"gate": "S", …}` and
    # raised it as a bare `RouteGate`, whose class id is `ROUTE`: measured 2026-09-04,
    # `gate_seed_registered(999, [1, 2])` rendered `[ROUTE] seed 999 is not on the
    # committed registration [1, 2]` while `exc.evidence["gate"]` said `S`, with `andon`
    # and `clause` both absent. The id's owner already exists - `GateSSeedRegistration`,
    # which `build_lora_arm_payload.gate_s` raises for this same clause - so it is raised
    # here rather than a second class being defined on the same id, which
    # `tests/test_gates.py` forbids.
    ev = {"gate": GateSSeedRegistration.gate, "andon": "GateSSeedRegistration",
          "clause": "seed_not_registered",
          "seed": int(seed), "registered": list(registered)}
    if int(seed) not in [int(s) for s in registered]:
        raise GateSSeedRegistration(
            f"seed {seed} is not on the committed registration {sorted(registered)}. A rule "
            f"forbids; a list removes the possibility, and git timestamps the list ahead of "
            f"the artifacts it governs", ev)
    ev["verdict"] = f"seed {int(seed)} is on the pre-registered list"
    return ev


def hosted_api_nodes(graph):
    """Every node in this graph that draws its own charge, keyed on BEHAVIOUR.

    `route_gates.HOSTED_API_CLASS_SUFFIXES` is the census core-gates already exports for
    exactly this question — a class whose name ends in `Api`/`API` is a partner tier that
    bills and draws its own seed (route_gates.py:983). Reading it here rather than naming
    one class means a second partner tier wired into this graph tomorrow is counted by the
    gate that bounds the spend, without an edit in this file.
    """
    suffixes = tuple(getattr(RG, "HOSTED_API_CLASS_SUFFIXES", ("Api", "API")))
    return sorted(nid for nid, n in graph.items()
                  if str((n or {}).get("class_type") or "").endswith(suffixes))


def gate_one_paid_node(graph):
    """Gate CEILING · ANDON — exactly one billable node, so one submission is one charge.

    The spec's ceiling is counted in SUBMISSIONS at 106-211 credits each. That arithmetic
    is only true if a submission bills once. A graph carrying two partner nodes would run,
    would look correct in every other gate, and would silently double the spend against a
    ceiling computed per submission.

    ⚠ **Wave 14, F-eec3f145.** The count was `n.get("class_type") == "Wan2ReferenceVideoApi"`
    — one hard-coded class SPELLING — on the gate whose whole justification is that the
    arithmetic holds only if a submission bills once. Measured 2026-09-04 on
    `{'1': Wan2ReferenceVideoApi, '2': KlingVideoApi}`: this gate returned `n_paid: 1`,
    `paid_nodes: ['1']` and the full green verdict "one billable node (1); one submission is
    one charge", while `route_gates.HOSTED_API_CLASS_SUFFIXES` matches BOTH nodes. The graph
    is built entirely from this tool's own constants today, so that was the SHAPE and not a
    live escape — but a verdict stating a fact about a population it did not measure is the
    class wave 12 closed everywhere else, and this is the one gate standing in front of the
    repo's single unrecoverable resource.

    Two numbers now, and both are in the evidence: the hosted/partner population counted by
    behaviour, and the expected identity counted by name. They must be the same set.
    """
    hosted = hosted_api_nodes(graph)
    expected = sorted(nid for nid, n in graph.items()
                      if (n or {}).get("class_type") == R2V_CLASS)
    ev = {"gate": SpendCeiling.gate, "andon": "SpendCeiling",
          "paid_nodes": expected, "n_paid": len(expected),
          "hosted_nodes": hosted, "n_hosted": len(hosted),
          "hosted_classes": sorted({str((graph[n] or {}).get("class_type"))
                                    for n in hosted}),
          "expected_class": R2V_CLASS,
          "counted_by": (
              "route_gates.HOSTED_API_CLASS_SUFFIXES "
              f"{list(getattr(RG, 'HOSTED_API_CLASS_SUFFIXES', ('Api', 'API')))} — a class "
              f"whose name ends in one of these is a partner tier that bills, whatever it "
              f"is spelled")}
    if hosted != expected:
        raise SpendCeiling(
            f"the graph's billable population is {hosted} "
            f"({ev['hosted_classes']}) and the node this route expects to be charged for "
            f"is {expected} ({R2V_CLASS}). A partner tier this tool did not put in the "
            f"graph still draws its own charge, and the spec's ceiling is counted in "
            f"submissions at one charge each — so the two populations must be the same set "
            f"before that arithmetic means anything",
            dict(ev, clause="hosted_population_is_not_the_expected_node"))
    if len(expected) != 1:
        raise SpendCeiling(
            f"the graph carries {len(expected)} `{R2V_CLASS}` node(s); the spec's "
            f"credit ceiling counts one charge per submission, and that arithmetic is only "
            f"true at exactly one", dict(ev, clause="not_exactly_one_billable_node"))
    ev["verdict"] = (
        f"one billable node ({expected[0]}, {R2V_CLASS}); {len(hosted)} node(s) in the "
        f"graph draw a partner charge and it is that same one; one submission is one charge")
    return ev


def build_and_write(argv=None):
    """Build, gate, write — and hand `(graph, record)` back to an in-process caller.

    Split out of `main` in wave 10 (F-c236304b). `main` used to end `return wf, record`
    under `raise SystemExit(main())`, so on the SUCCESS path CPython printed the tuple to
    stderr and exited 1. Measured as a subprocess: the full green block ending
    `BUILD_R2V_OK <path>` on stdout, both artifacts written, 6,047 bytes of the tuple on
    stderr, exit code 1 — on the spend builder for E13's hosted r2v tier, whose own comment
    declares "2 = a gate refused ... 1 = this tool crashed". `verify.ps1` reads `-ne 0`, so
    a wrapper recorded the successful authoring of a paid submission as a failure.
    """
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

    # Each arm needs exactly one of these, and until wave 6 neither requirement was
    # enforced or reported: both flags default to None, `--arm A1` opened `a.refs` and
    # `--arm A2` opened `a.uploads`, and an omitted flag arrived as
    # `TypeError: expected str, bytes or os.PathLike object, not NoneType` — no typed
    # error, no flag named, no arm named — AFTER Gate CANON and Gate S had already passed.
    # The check runs on the invocation itself, before anything is read.
    # `build_camera_i2v_payload.resolve_start_frame` is the shape carried: name the flag,
    # name what the file is for.
    ARM_INPUT = {"A1": ("--refs", "refs",
                        "the reference record JSON whose views become this arm's "
                        "reference image slots"),
                 "A2": ("--uploads", "uploads",
                        "the frame uploads map JSON the in-graph cascade assembles the "
                        "reference VIDEO from")}
    flag, attr, what = ARM_INPUT[a.arm]
    if not getattr(a, attr):
        raise RG.RouteGate(
            f"arm {a.arm} needs {flag}: it is {what}, and this arm cannot be built "
            f"without it. The omission used to surface as a NoneType traceback from "
            f"`open`, two gates later",
            {"gate": "ROUTE", "andon": "RouteGate", "clause": "missing_arm_input",
             "arm": a.arm, "flag": flag})

    out = os.path.abspath(a.out)

    # ONE reader, eight callers (wave 16, F-0682bd00): the bare `registration["seeds"]`
    # below used to raise a stdlib KeyError on a registration with no `seeds` key.
    registered = read_seed_registration(a.seeds, flag="--seeds")
    with open(a.prompt_file, encoding="utf-8") as fh:
        prompt_spec = json.load(fh)
    # The SHIPPED prompt is what is gated. `--canon-prompt` used to be gated in its place
    # while `build()` always sent `prompt_spec["prompt"]`, so an operator who hit a canon
    # refusal could paste the ratified phrases into the flag and send the very text the
    # gate had just refused. See `gate_canon_ships_what_it_gated` below.
    canon_ev = canon_spend(a.subject, prompt_spec["prompt"], no_canon=a.no_canon,
                           out_dir=out, canon_prompt=a.canon_prompt)

    gate_seed = gate_seed_registered(a.seed, registered)

    refs = ref_record = upload_names = frame_order = None
    if a.arm == "A1":
        with open(a.refs, encoding="utf-8") as fh:
            ref_record = json.load(fh)
        refs = [v["upload_name"] for v in ref_record["views"]]
    else:
        with open(a.uploads, encoding="utf-8") as fh:
            uploads = json.load(fh)
        # LOCAL names carry the frame order, and the shape that makes that true is now
        # checked rather than assumed: an unpadded key sorts lexicographically and a
        # non-frame key is absorbed as an extra frame, both into the reference slot of a
        # tier that bills per submission.
        frame_order = CASCADE.frame_order(uploads)
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
             "CEILING_one_paid_node": gate_ceiling, "CANON": canon_ev}
    shared_params = None
    if a.arm == "A2":
        # The gate owns the ceiling; `cap=max(--group, 1)` made it check a direction the
        # construction already bounds, on the arm that spends.
        gates["CASCADE_ceiling"] = AS.gate_slot_ceiling(wf, group_size=int(a.group))
        # The cascade's OWN first image id (200), not this tool's (100): the ids the gate
        # compares are the LoadImage nodes the cascade built inside this graph.
        ordered_ids = CASCADE.frame_source_ids(upload_names, CASCADE.FIRST_IMAGE_ID)
        gates["CASCADE_topology"] = AS.gate_cascade_topology(
            wf, len(upload_names), cascade_ids["groups"], CASCADE.FINAL_BATCH_ID,
            CASCADE.VIDEO_ID, R2V_ID, "model.reference_videos.video1",
            group_size=a.group, expected_sources=list(ordered_ids))
        # `strict=True` — see the same pairing in `build_cascade_payload` (wave 8,
        # F-ad45bc42): an un-strict zip truncates to the shorter of the two and hands the
        # gate a plan that does not cover the clip. This is the arm that spends.
        slot_plan = [(gid, start, stop) for (start, stop), gid
                     in zip(AS.cascade_plan(len(upload_names), a.group),
                            cascade_ids["groups"], strict=True)]
        gates["CASCADE_slot_frame_index"] = CASCADE.gate_slot_frame_index(
            wf, upload_names, slot_plan, CASCADE.FIRST_IMAGE_ID)
        shared_params = {"expected_sources_first_image_id": CASCADE.FIRST_IMAGE_ID,
                         "expected_sources": list(ordered_ids)}

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
        "shared_gate_parameters": shared_params,
        "gate_pair_note": (
            "Gate PAIR is n/a on this tier and is RECORDED as n/a, not skipped: the graph "
            "loads no local weights, so no conditioning class can be unpaired from a "
            "weight family. route_gates.pairing() ran and examined an empty set."),
        "gate_l_note": (
            "The pixel clause of Gate L is INAPPLICABLE here, not passed: this tier "
            "receives no width, height or frame count from us. Gate ROUTE records that "
            "verbatim in `frame_legality_verdict` and checks the tier's own enum "
            "constraints instead, which is the clause that binds and can fail."),
        # ---- Wave 20, F-dba1bcd8. The record this tool writes carries the two facts that
        # admit a paid submission (`gates.ROUTE`'s `attribution` and its no-sampler
        # assertion) and, until this line, nothing tying them to the graph written beside
        # them. This is the HOSTED PARTNER TIER: one submission is one charge, and
        # `gate_saved_graph.route_facts` reported `payload_sha256: null` on this record and
        # ADMITTED, with `source` reading "the facts below are NOT tied to the graph being
        # admitted". The digest is the canonical one the gate compares against - the graph
        # as an object, not the pretty-printed file - through the one shared function.
        "payload_sha256": canonical_payload_digest(wf),
    }

    # Below the last in-tool gate. `os.makedirs` used to sit above Gate S, so a refused
    # spend left an empty run directory beside real ones — the invariant build_payload.py
    # states for Gate CANON, applied to every gate in this tool.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories
    graph_path = os.path.join(out, f"E13-{a.arm}-seed{a.seed}.api.json")
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=1)
    with open(os.path.join(out, f"E13-{a.arm}-seed{a.seed}-payload-record.json"), "w",
              encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    print(canon_line(canon_ev))
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


def main(argv=None):
    """The process exit code, and nothing else. 0 = built; a gate raises."""
    build_and_write(argv)
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9), through the ONE handler wave 22 built and
    # wave 25 adopted here (F-af838b99): 2 = a gate refused (any `ArmatureError`;
    # `GateFailure` is one), 1 = this tool crashed, and the record is the six keys
    # `run_tool_main` prints — `tool`, `outcome`, `gate`, `error`, `message`, `evidence` —
    # as strict JSON (`allow_nan=False`) with `halt_keysafe` applied to the evidence.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the
    # `BUILD_R2V_HALT` sentinel this handler prints, never on the code alone.
    # The local three-key copy this replaces, and what it cost, are described in full at
    # `gate_saved_graph.py`'s block — one description, thirteen adopters, no second spelling.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "BUILD_R2V")
