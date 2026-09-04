#!/usr/bin/env python
r"""build_lora_arm_payload — E14's bake-off arms, built in this repo from E12's pinned graph.

    python tools\build_lora_arm_payload.py --base=<E12-w3-camera-i2v.api.json> --arm=T
           --out=<dir> --seeds-registry=specs\E14-seeds.json --seed=2026081233

E14 asks one question per arm: what does ONE style LoRA at its trained strength do to the
world, the subject and the camera hold, on a baseline that already holds. So the arm graph
is not authored — it is the **byte-pinned E12 wave-3 seed-1 graph with exactly two nodes
inserted**, and this tool's whole job is to make "exactly two" a property of the code
rather than a sentence in a report.

--------------------------------------------------------------------------------
WHERE THE LOADER SITS, AND WHY THAT IS MEASURED RATHER THAN ASSUMED

Both orders type-check: `LoraLoaderModelOnly` takes MODEL and returns MODEL, and so does
`ModelSamplingSD3`. Picking by taste would be inheriting a claim.

Measured 2026-08-13 off the served `video_wan2_2_14B_t2v` template — read as a REFERENCE,
never as a route (CLAUDE.md), by walking its subgraph blueprint's MODEL links:

    UNETLoader(75, high) -> LoraLoaderModelOnly(83, lightx2v high) -> ModelSamplingSD3(82) -> KSamplerAdvanced(81)
    UNETLoader(76, low)  -> LoraLoaderModelOnly(85, lightx2v low)  -> ModelSamplingSD3(86) -> KSamplerAdvanced(78)

Two facts come off that, and both are load-bearing here:

* the loader sits **between the UNETLoader and ModelSamplingSD3**, so the shift wraps a
  model that is already patched;
* the pair is **tier-matched** — the high-noise LoRA on the high-noise expert's line.

That second one is the demonstrated dual-expert convention consult #10 R2 cites off E09's
own evidence, and it is why `gate_pair_tier` below RAISES rather than reports.

--------------------------------------------------------------------------------
WHAT "GENERATION-REACHING" MEANS HERE, STATED BEFORE ANYTHING IS COUNTED

`filename_prefix` moves on three nodes (41, 71, 81) because two arms cannot write to one
output path. That is an output-routing field: it changes where bytes land, never what the
sampler computes. E12 wave 3 classified it exactly this way when it moved the same three
fields and still reported "generation-reaching differences: 4, all of them cfg or
sampler_name".

So the ledger sorts every difference into one of three boxes and the boxes are declared
here, not discovered later:

    NAMED_BREAK       the two LoRA insertions + the two MODEL rewires  -> generation-reaching, REQUIRED to have happened
    OUTPUT_ROUTING    filename_prefix on 41 / 71 / 81                  -> not generation-reaching, REQUIRED to have happened
    UNNAMED           anything else                                    -> the gate RAISES

A break that is named and did NOT happen raises too. That is E12 wave 2's failure shape —
a report describing a correction that did not occur — and it is cheaper to refuse than to
discover in a sheet.
"""

import argparse
import copy
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import route_gates  # noqa: E402
from armature_core.canon import add_spend_flags  # noqa: E402
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateCanon, GateFailure, GateSSeedRegistration)
from canon_gate import canon_line, canon_spend  # noqa: E402

TOOL_VERSION = "E14.2"
EXPERIMENT = "E14"

#: The served filenames, verbatim. The HIGH member of the SmartphoneSnapshot pair really
#: does carry `.safetensors` TWICE — a provisioning artifact on the Cloud's side, confirmed
#: against the served catalog 2026-08-13 (`search_models`, 2 hits, exact) and recorded in
#: the licence map. Normalising it to one suffix names a file the catalog does not serve.
TECHNICALLY_COLOR = "wan22-14b-t2v-technically_color.safetensors"
SMARTPHONE_HIGH = ("WAN2.2-HighNoise_SmartphoneSnapshotPhotoReality_v3_by-AI_Characters"
                   ".safetensors.safetensors")
SMARTPHONE_LOW = ("WAN2.2-LowNoise_SmartphoneSnapshotPhotoReality_v3_by-AI_Characters"
                  ".safetensors")

STRENGTH = 1.0

#: arm -> (high-noise expert's LoRA, low-noise expert's LoRA, tier-checkable?)
#:
#: Arm T loads ONE served file on BOTH experts. Its origin publishes a tier-labelled HN/LN
#: pair and the Cloud serves a single file whose tier is NOT VISIBLE in the name, so one of
#: T's two attachments is necessarily tier-mismatched and nothing in the graph can say
#: which. That is a premise of the spec, not a defect of this tool, and `tier_checkable`
#: False records it rather than letting a green gate imply a match was verified.
ARMS = {
    "T": {"high": TECHNICALLY_COLOR, "low": TECHNICALLY_COLOR, "tier_checkable": False,
          "lora": "technically_color",
          "credit": "renderartist — allowNoCredit: false; published footage from this arm "
                    "carries a credits line"},
    "S": {"high": SMARTPHONE_HIGH, "low": SMARTPHONE_LOW, "tier_checkable": True,
          "lora": "SmartphoneSnapshotPhotoReality v3 (pair)",
          "credit": "none required — allowNoCredit: true"},
}

#: The node ids the insertions take. 14/15 sit beside 12/13 in the model block rather than
#: at 100+, so a reader of the graph meets them where the model chain actually is.
LORA_HIGH_ID, LORA_LOW_ID = "14", "15"

#: The expert chain, read off the baseline rather than assumed: the KSamplerAdvanced that
#: starts at step 0 with add_noise enabled is the HIGH-noise expert; the one that starts at
#: the split with add_noise disabled is the LOW-noise expert.
LORA_CLASS = "LoraLoaderModelOnly"


class LedgerGate(GateFailure):
    """A difference from the baseline that no one named in advance — or a named one missing."""

    gate = "LEDGER"


class TierGate(GateFailure):
    """A tier-matched pair wired crossed — the E11-w2 class of wiring error."""

    gate = "PAIR_TIER"


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _tier_token(filename):
    """`WAN2.2-HighNoise_…` -> 'high'. Returns None when the name carries no tier."""
    squashed = "".join(ch for ch in str(filename).lower() if ch.isalnum())
    has_high = "highnoise" in squashed
    has_low = "lownoise" in squashed
    if has_high and not has_low:
        return "high"
    if has_low and not has_high:
        return "low"
    return None


def experts(graph):
    """Map 'high'/'low' -> the KSamplerAdvanced node id, derived from the graph itself.

    Derived, not hard-coded: the high-noise expert is the sampler that adds noise and starts
    at step 0. A graph whose two samplers do not split that way is not this route and says
    so rather than being silently mis-labelled.
    """
    found = {}
    for nid, node in graph.items():
        if not isinstance(node, dict) or node.get("class_type") != "KSamplerAdvanced":
            continue
        ins = node.get("inputs") or {}
        if ins.get("add_noise") == "enable" and ins.get("start_at_step") == 0:
            found["high"] = nid
        elif ins.get("add_noise") == "disable":
            found["low"] = nid
    if set(found) != {"high", "low"}:
        raise ArmatureError(
            "the baseline does not present one noise-adding sampler starting at step 0 and "
            f"one noise-free sampler; found {found!r}. This tool only knows the E12 "
            "two-expert split-step route")
    return found


def model_lineage(graph, node_id):
    """Every node id on the MODEL path feeding `node_id`, nearest first."""
    chain, seen = [], set()
    cur = node_id
    while True:
        node = graph.get(cur) or {}
        link = (node.get("inputs") or {}).get("model")
        if not isinstance(link, list) or not link:
            return chain
        nxt = str(link[0])
        if nxt in seen:
            raise ArmatureError(f"the MODEL chain from node {node_id} loops at {nxt}")
        seen.add(nxt)
        chain.append(nxt)
        cur = nxt


def positive_text_node(graph, sampler_id, max_hops=8):
    """Follow a sampler's `positive` CONDITIONING chain to the text node that feeds it.

    The chain is not one hop: on this route the sampler's `positive` is the conditioning
    node's output (`WanCameraImageToVideo`), whose own `positive` input is the
    `CLIPTextEncode`. Walking it is the whole point — a length heuristic over every
    text/prompt/positive string in the graph cannot tell a positive from a negative, and
    on a graph whose negative is the longer string it picks the negative.
    """
    cur, seen = str(sampler_id), set()
    for _ in range(max_hops):
        node = graph.get(cur)
        link = (node.get("inputs") or {}).get("positive") if isinstance(node, dict) else None
        if not isinstance(link, list) or not link:
            break
        nxt = str(link[0])
        if nxt in seen:
            raise ArmatureError(
                f"the CONDITIONING chain from node {sampler_id} loops at {nxt}")
        seen.add(nxt)
        cand = graph.get(nxt) or {}
        text = (cand.get("inputs") or {}).get("text")
        if cand.get("class_type") == "CLIPTextEncode" and isinstance(text, str):
            return nxt, text
        cur = nxt
    raise ArmatureError(
        f"no CLIPTextEncode is reachable along the positive CONDITIONING chain from "
        f"sampler {sampler_id}. This tool gates the text it ships, and a graph whose "
        f"positive it cannot LOCATE is a graph it must not gate by guessing")


def positive_prompt_from_graph(graph):
    """The positive prompt this graph carries, selected by node identity. Raises or returns.

    Wave 3, F-815b8a85. The prompt handed to Gate CANON used to be
    `max(texts_from_api_graph(base), key=len)` — the longest of every text/prompt/positive
    string — on the heuristic that negatives are shorter quality lists. Nothing checked the
    choice, so a base whose negative was the longer string would have had the NEGATIVE
    gated. Separately, `texts_from_api_graph` returns `[]` for any graph whose top-level
    values are not all dicts, so a `.saved.json` passed as `--base` yielded `prompt=None`,
    which `require_canon` never examines at all on the `--no-canon` path — and both formats
    sit side by side in this pipeline's output directories.

    Returns `(text, {tier: text_node_id})`.
    """
    ks = experts(graph)
    found = {}
    for tier in sorted(ks):
        found[tier] = positive_text_node(graph, ks[tier])
    texts = {t for _, t in found.values()}
    if len(texts) != 1:
        raise ArmatureError(
            f"the two experts read different positive prompts ({sorted(texts)!r}); gating "
            f"one of them would leave the other ungoverned, and this tool only knows the "
            f"E12 two-expert split-step route")
    text = texts.pop()
    if not text.strip():
        raise ArmatureError(
            "the positive prompt this graph carries is empty; a spend gated on an empty "
            "string is a check that cannot fail")
    return text, {tier: nid for tier, (nid, _) in found.items()}


def gate_canon_text_is_in_graph(gated, graph):
    """Gate CANON · ANDON — the gated string is byte-equal to the emitted graph's positive.

    Wave 3, F-dfcc0bea, this tool's half. The payload's prompt lives inside the inherited
    `--base` graph rather than in a value this tool holds, so the only way to bind the
    router's string to the shipped one is to read the shipped one back out of the graph
    that is about to be written and require byte equality.
    """
    shipped, nodes = positive_prompt_from_graph(graph)
    ev = {"gate": "CANON", "text_nodes": nodes, "gated_len": len(gated or ""),
          "shipped_len": len(shipped)}
    if gated != shipped:
        raise GateCanon(
            "the graph this tool emits does not carry the text Gate CANON checked. The "
            "router would have examined one string while the submission carried another, "
            "and every other gate would still be green",
            dict(ev, clause="gated_text_is_not_shipped_text",
                 gated=gated, shipped=shipped))
    ev["verdict"] = (f"the gated text is byte-equal to the positive carried by "
                     f"{sorted(nodes.values())} in the emitted graph")
    return ev


def build_arm(base, arm):
    """The baseline graph plus exactly two loaders. Returns (graph, insertion record)."""
    spec = ARMS[arm]
    wf = copy.deepcopy(base)

    for nid in (LORA_HIGH_ID, LORA_LOW_ID):
        if nid in wf:
            raise ArmatureError(
                f"node id {nid} already exists in the baseline — this tool would overwrite "
                "it, which is a silent edit to a byte-pinned graph")

    ks = experts(wf)
    # The ModelSamplingSD3 immediately feeding each expert is where the insertion goes: the
    # loader is spliced between IT and the UNETLoader it reads, per the served convention.
    inserts = {}
    for tier, lora_id in (("high", LORA_HIGH_ID), ("low", LORA_LOW_ID)):
        chain = model_lineage(wf, ks[tier])
        sampling_id = chain[0]
        if wf[sampling_id].get("class_type") != "ModelSamplingSD3":
            raise ArmatureError(
                f"expected ModelSamplingSD3 feeding the {tier}-noise expert, found "
                f"{wf[sampling_id].get('class_type')!r} at node {sampling_id}")
        unet_link = wf[sampling_id]["inputs"]["model"]
        unet_id = str(unet_link[0])
        if wf[unet_id].get("class_type") != "UNETLoader":
            raise ArmatureError(
                f"expected UNETLoader feeding node {sampling_id}, found "
                f"{wf[unet_id].get('class_type')!r} at node {unet_id}")

        wf[lora_id] = {"class_type": LORA_CLASS,
                       "inputs": {"model": [unet_id, 0],
                                  "lora_name": spec[tier],
                                  "strength_model": STRENGTH}}
        wf[sampling_id]["inputs"]["model"] = [lora_id, 0]
        inserts[tier] = {
            "loader_node": lora_id, "lora_name": spec[tier], "strength_model": STRENGTH,
            "reads_unet_node": unet_id,
            "reads_unet_file": wf[unet_id]["inputs"].get("unet_name"),
            "feeds_model_sampling_node": sampling_id,
            "feeds_expert_sampler": ks[tier],
            "expert_tier": tier,
            "lora_tier_in_name": _tier_token(spec[tier]),
        }

    for nid, prefix in (("41", f"{EXPERIMENT}/{arm}/startprobe"),
                        ("71", f"{EXPERIMENT}/{arm}/lossless"),
                        ("81", f"video/{EXPERIMENT}_{arm}")):
        if nid in wf:
            wf[nid]["inputs"]["filename_prefix"] = prefix

    return wf, inserts


def gate_pair_tier(inserts, arm):
    """Gate PAIR (tier clause) · ANDON — a tier-labelled pair must not be wired crossed.

    The andon points at the direction nothing else bounds. Gate PAIR proper asks whether the
    conditioning class has a model family that can receive it, and it would pass a graph
    with the high-noise LoRA on the low-noise expert: same family, same files, both present.
    The crossed pair is invisible to every other check in the chain and visible here.

    Arm T's single served file carries no tier in its name, so this clause reports NOT
    VISIBLE and does not pretend to have verified a match.
    """
    ev = {"gate": "PAIR_TIER", "arm": arm,
          "tier_checkable": ARMS[arm]["tier_checkable"], "attachments": inserts}
    if not ARMS[arm]["tier_checkable"]:
        ev["verdict"] = ("NOT VISIBLE — one served file on both experts; its tier is not in "
                         "the name, so one attachment is necessarily mismatched and the "
                         "graph cannot say which. Named in the spec as a candidate "
                         "explanation for any oddity in this arm")
        return ev
    crossed = [t for t, rec in inserts.items()
               if rec["lora_tier_in_name"] and rec["lora_tier_in_name"] != rec["expert_tier"]]
    if crossed:
        raise TierGate(
            "a tier-matched pair is wired CROSSED: " + "; ".join(
                f"the {inserts[t]['lora_tier_in_name']}-noise LoRA "
                f"{inserts[t]['lora_name']!r} is attached to the {t}-noise expert "
                f"(sampler {inserts[t]['feeds_expert_sampler']})" for t in crossed) +
            ". This is the E11-w2 class of wiring error: every other gate passes it, and the "
            "run would be reported as a LoRA-transfer result when it is a wiring result", ev)
    unlabelled = [t for t, rec in inserts.items() if not rec["lora_tier_in_name"]]
    if unlabelled:
        raise TierGate(
            f"arm {arm} is declared tier-checkable but the file(s) on {unlabelled} carry no "
            "tier in the name; the check would pass without checking anything", ev)
    ev["verdict"] = "tier-matched on both experts, verified from the served filenames"
    return ev


#: Fields whose movement is expected and NOT generation-reaching. Declared before the diff.
OUTPUT_ROUTING = {("41", "filename_prefix"), ("71", "filename_prefix"),
                  ("81", "filename_prefix")}


def gate_ledger(base, built, inserts):
    """Gate LEDGER, break-aware · ANDON — the LoRA insertions are the ONLY difference.

    Raises on an unnamed difference AND on a named break that did not actually happen.
    """
    added = sorted(set(built) - set(base), key=str)
    removed = sorted(set(base) - set(built), key=str)
    expected_added = sorted({LORA_HIGH_ID, LORA_LOW_ID})

    rewired = {rec["feeds_model_sampling_node"] for rec in inserts.values()}
    named_field_breaks = {(nid, "model") for nid in rewired}

    diffs, unnamed, routing_moved = [], [], []
    for nid in sorted(set(base) & set(built), key=str):
        b_in = (base[nid].get("inputs") or {})
        n_in = (built[nid].get("inputs") or {})
        if base[nid].get("class_type") != built[nid].get("class_type"):
            unnamed.append({"node": nid, "field": "class_type",
                            "base": base[nid].get("class_type"),
                            "built": built[nid].get("class_type")})
        for field in sorted(set(b_in) | set(n_in)):
            bv, nv = b_in.get(field), n_in.get(field)
            if bv == nv:
                continue
            rec = {"node": nid, "field": field, "base": bv, "built": nv}
            diffs.append(rec)
            if (nid, field) in OUTPUT_ROUTING:
                routing_moved.append((nid, field))
            elif (nid, field) in named_field_breaks:
                pass
            else:
                unnamed.append(rec)

    ev = {
        "gate": "LEDGER", "baseline_is": "the byte-pinned E12 wave-3 seed-1 graph",
        "nodes_added": added, "nodes_removed": removed,
        "named_breaks": {
            "insertions": expected_added,
            "model_rewires": sorted(named_field_breaks, key=str),
            "output_routing": sorted(OUTPUT_ROUTING, key=str)},
        "differences": diffs,
        "generation_reaching_differences": [
            d for d in diffs if (d["node"], d["field"]) not in OUTPUT_ROUTING],
    }

    if unnamed:
        raise LedgerGate(
            "differences from the baseline that nothing named in advance: " + "; ".join(
                f"node {d['node']}.{d['field']}: {d['base']!r} -> {d['built']!r}"
                for d in unnamed) +
            ". Every unnamed field must hold byte-identical: the LoRA is the only "
            "generation-reaching difference this experiment is allowed to have", ev)
    if removed:
        raise LedgerGate(f"the baseline lost node(s) {removed} — nothing authorises a "
                         "deletion from a byte-pinned graph", ev)
    if added != expected_added:
        raise LedgerGate(f"expected exactly the insertions {expected_added}, found {added}",
                         ev)

    # A named break that did not happen is E12 wave 2's failure shape, one experiment later.
    missing = [f"node {nid}.model was not rewired onto its loader"
               for nid in sorted(rewired, key=str)
               if (nid, "model") not in {(d["node"], d["field"]) for d in diffs}]
    missing += [f"{nid}.{field} did not move" for (nid, field) in sorted(OUTPUT_ROUTING)
                if (nid, field) not in set(routing_moved) and nid in base]
    if missing:
        raise LedgerGate("named breaks that did NOT actually happen: " + "; ".join(missing) +
                         ". A report describing an insertion that did not occur is the "
                         "failure this gate exists to refuse", ev)

    ev["verdict"] = (
        f"{len(ev['generation_reaching_differences'])} generation-reaching difference(s), "
        f"all of them the LoRA insertions; {len(routing_moved)} output-routing field(s) "
        "moved as named; every other field byte-identical to the baseline")
    return ev


def gate_s(graph, registry_path, seed):
    """Gate S · ANDON — the seed is on the committed list and every live sampler carries it.

    Both raises used to construct the BASE `GateFailure` with no second argument, so
    `evidence` was `{}` and the class attribute `gate` was errors.py's placeholder `"G?"`:
    the message said "Gate S" while the receipt said `[G?]`, and the halt on the arm that
    spends E14's two generations carried no machine-readable record of which seed, which
    registry or which samplers fired it. `GateSSeedRegistration` exists for this clause and
    is what the other two implementations in this tree already do —
    `route_gates.gate_s_registration` and `build_r2v_payload.gate_seed_registered` both
    raise with an evidence dict.
    """
    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)
    registered = registry.get("seeds") or []
    live = [(nid, n["inputs"].get("noise_seed")) for nid, n in graph.items()
            if isinstance(n, dict) and n.get("class_type") == "KSamplerAdvanced"
            and (n.get("inputs") or {}).get("add_noise") == "enable"]
    ev = {"gate": "S", "seed": seed, "registry": os.path.abspath(registry_path),
          "registered": registered, "noise_adding_samplers": live}
    if seed not in registered:
        raise GateSSeedRegistration(
            f"Gate S: seed {seed} is not in {registry_path} ({registered}). A number the "
            "committed list never pre-registered is a number nobody can hold this run to",
            ev)
    off = [(nid, s) for nid, s in live if s != seed]
    if off:
        raise GateSSeedRegistration(
            f"Gate S: noise-adding sampler(s) {off} do not carry {seed}",
            dict(ev, off_seed_samplers=off))
    return {"gate": "S", "seed": seed, "registry": os.path.abspath(registry_path),
            "registered": registered, "noise_adding_samplers": live,
            "inert_zero_seed_note": ("the low-noise expert carries noise_seed 0 with "
                                     "add_noise=disable; it draws nothing and is not "
                                     "required to be registered")}


def _verdict_of(row):
    """The licence verdict on a `route_gates.components` row, in either row shape.

    Wave 8's core-gates rows carry `verdict` at the top level on BOTH kinds (weight rows
    keep `ruling` too); the pre-wave-8 shape carried it only under `ruling`. Read here so
    this call site does not have to know which build of the module it is talking to — the
    RULING itself is core-gates', never re-derived here.
    """
    return row.get("verdict") or (row.get("ruling") or {}).get("verdict")


def load_base(path):
    """The `--base` graph, read through THE loader, or a refusal that names the FORMAT.

    Wave 8, F-562a53f1. This was a bare `json.load`, so neither wrapper unwrapping nor
    refusal-by-name happened and two wrong-SHAPE inputs refused through the ROUTE clause
    instead. Measured 2026-09-04 in this repo: a save-format doc (`{'nodes': [...],
    'links': [], 'last_node_id': 1}`) raised "the baseline does not present one
    noise-adding sampler starting at step 0 and one noise-free sampler; found {}. This tool
    only knows the E12 two-expert split-step route" — the operator is told the ROUTE is
    wrong when the FORMAT is wrong, and `route_gates.is_api_format` on the same doc returns
    False, i.e. the repo already owns the sentence. A `{'prompt': {...}}`-wrapped API graph
    carrying a correct two-expert split raised the IDENTICAL message, and that one is a
    FALSE refusal: `load_graph` unwraps `prompt` (it is in `WRAPPER_KEYS`) and would have
    handed back exactly the graph this tool wants.

    `gate_saved_graph.main` documents the same boundary for its own `--saved` side; this is
    that block's shape, on this tool's side of the pipeline.
    """
    graph = route_gates.load_graph(path)
    if not route_gates.is_api_format(graph):
        keys = sorted(map(str, graph)) if isinstance(graph, dict) else []
        raise route_gates.RouteGate(
            f"{path} is not an API-format graph: its values carry no `class_type`. Its "
            f"top-level keys are {keys}; a `nodes` list means this is the SAVE format, and "
            f"both formats sit side by side in this pipeline's output directories. The "
            f"loader unwraps {list(route_gates.WRAPPER_KEYS)}, so the standard submission "
            f"envelope is read for you — paste the api file, not the .saved.json beside it",
            {"gate": "ROUTE", "andon": "not_an_api_format_graph",
             "path": os.path.abspath(path), "top_level_keys": keys,
             "unwrapped_by_load_graph": list(route_gates.WRAPPER_KEYS),
             "clause": "not_an_api_format_graph"})
    return graph


def gate_base_licence(graph, path=None):
    """Gate LICENCE · ANDON — no licence-BANNED node CLASS rides in on an operator's base.

    Wave 8, F-0c05b52e. This is the ONE builder whose graph arrives as a FILE on disk, and
    it was the only one of the nine with no banned-node-class check at all.
    `build_animate_payload.py:420`, `build_camera_i2v_payload.py:953` and
    `build_i2v_payload.py:458` each carry a typed tuple and refuse a graph containing one —
    but all three build their graphs from their own constants, so that tuple guards a graph
    nobody else touched.

    Measured 2026-09-04 on the repo's own fixture `tests/fixtures/E12-w3-camera-i2v.api.json`
    with a `DWPreprocessor` node (id 900, fed by a LoadImage at 901) spliced in:
    `positive_prompt_from_graph` returned the prompt, `build_arm('T')` copied the node
    through, `gate_ledger` reported "2 generation-reaching difference(s), all of them the
    LoRA insertions", `gate_pair_tier` returned its NOT VISIBLE verdict, `gate_s` returned
    its S evidence, and `route_gates.verify(built, frame=(1024, 576, 81))` returned "6
    weight file(s), 2 seed(s) all pinned, 1 of 1 latent(s) checkable, 2 frame(s) checked and
    generator-legal" — every gate green — with `built['900']['class_type']` still
    `DWPreprocessor` in the graph written out and submitted. Gate ROUTE could not see it:
    `components()` was keyed on weight FILENAMES and a preprocessor loads none, while
    `RULED_COMPONENTS['dwpose']` carries verdict BANNED. That is a BANNED-tier preprocessor
    riding a paid submission past every gate, against the repo's hardest non-negotiable.

    **The census is core-gates' and is CALLED, never re-implemented here.**
    `route_gates.ruled_node_classes(graph)` reads node `class_type` against
    `RULED_COMPONENTS` through `RULED_COMPONENT_CLASSES` (a licence row's class aliases —
    `DWPreprocessor` does not contain the substring "dwpose", which is why the matching is
    a table and not a `in`), and `components(graph)` returns weight rows and class rows
    together. So the filter below is one filter over one census: a licence row added to the
    map tomorrow reaches this gate with no edit here, which the three typed tuples cannot
    claim. Those tuples stay where they are — three of their five entries (`LoadVideo`,
    `GetVideoComponents`, `SAM2`, and the two LoRA loader classes on the camera/i2v rows)
    carry no licence row at all and are ROUTE claims about the graph the spec describes.
    """
    banned = [r for r in route_gates.components(graph) if _verdict_of(r) == "BANNED"]
    # `gate` is the raising class's id and `andon` its name (the evidence contract every
    # census reads); the clause names this check. Aligned at the wave-8 merge — the first
    # draft put the clause under `andon` and its test expected a gate id no class carries.
    ev = {"gate": "ROUTE", "andon": "RouteGate", "clause": "banned_component_in_base",
          "path": os.path.abspath(path) if path else None,
          "banned": [{"kind": r.get("kind"), "file": r.get("file"),
                      "class_type": r.get("class_type") or r.get("class"),
                      "node_id": r.get("node_id"), "where": r.get("where"),
                      "matched_on": r.get("matched_on")
                      or (r.get("ruling") or {}).get("matched_on"),
                      "licence": r.get("licence") or (r.get("ruling") or {}).get("licence"),
                      "reason": r.get("reason") or (r.get("ruling") or {}).get("reason")}
                     for r in banned],
          "n_components_examined": len(route_gates.components(graph))}
    if banned:
        named = "; ".join(
            f"{b['class_type'] or b['file']!r} (matched the licence map's "
            f"{b['matched_on']!r} row — {b['licence']}: {b['reason']})"
            for b in ev["banned"])
        raise route_gates.RouteGate(
            f"the baseline graph {path or ''} carries {len(banned)} component(s) the "
            f"licence map rules BANNED: {named}. No non-commercially-licensed model, "
            f"weight, LoRA, preprocessor or code dependency goes anywhere in this "
            f"pipeline, experiments included, and an experiment concluded on a banned "
            f"component is a conclusion that has to be thrown away — so it never starts. "
            f"Nothing is built and no output directory is created",
            dict(ev, clause="banned_component_in_base"))
    ev["verdict"] = (f"{ev['n_components_examined']} ruled component(s) read off the "
                     f"baseline, none BANNED")
    return ev


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True,
                    help="the byte-pinned E12 wave-3 seed-1 API graph")
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds-registry", required=True)
    ap.add_argument("--seed", type=int, required=True)
    add_spend_flags(ap)
    args = ap.parse_args(argv)

    base = load_base(args.base)
    # BEFORE anything is read out of the graph and before `os.makedirs` — a BANNED tier
    # riding an operator-supplied baseline is the one defect on this path that costs the
    # whole arc rather than one submission.
    base_licence = gate_base_licence(base, args.base)

    prompt, prompt_nodes = positive_prompt_from_graph(base)
    canon_ev = canon_spend(args.subject, prompt, no_canon=args.no_canon,
                           out_dir=args.out, canon_prompt=args.canon_prompt)

    built, inserts = build_arm(base, args.arm)
    # The graph exists now: bind the router's string to the one the submission carries.
    gate_canon_graph = gate_canon_text_is_in_graph(prompt, built)

    ledger = gate_ledger(base, built, inserts)
    tier = gate_pair_tier(inserts, args.arm)
    seed_ev = gate_s(built, args.seeds_registry, args.seed)
    route = route_gates.verify(built, frame=(1024, 576, 81))

    os.makedirs(args.out, exist_ok=True)
    graph_path = os.path.join(args.out, f"E14-{args.arm}-camera-i2v.api.json")
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(built, fh, indent=2, ensure_ascii=False)

    record = {
        "experiment": EXPERIMENT, "arm": args.arm, "tool_version": TOOL_VERSION,
        "lora": ARMS[args.arm]["lora"],
        "credit_obligation": ARMS[args.arm]["credit"],
        "strength_model": STRENGTH,
        "seed": args.seed,
        "baseline": {"path": os.path.abspath(args.base), "sha256": sha256_file(args.base),
                     "is": "E12 wave 3, seed 2026081233 — the Director's ruled-strongest "
                           "result, reused as the comparison reference; NOT regenerated"},
        "insertion_convention": {
            "where": "between UNETLoader and ModelSamplingSD3",
            "measured_from": ("the served video_wan2_2_14B_t2v template's subgraph MODEL "
                              "links, read as a reference not a route, 2026-08-13"),
            "tier_matched": "high-noise LoRA on the high-noise expert's line"},
        "attachments": inserts,
        "prompt_nodes": prompt_nodes,
        "gates": {"LEDGER": ledger, "PAIR_TIER": tier, "S": seed_ev, "ROUTE": route,
                  "CANON": canon_ev, "CANON_graph_text": gate_canon_graph,
                  "BASE_LICENCE": base_licence},
        "graph": os.path.abspath(graph_path),
        "graph_sha256": sha256_file(graph_path),
    }
    record_path = os.path.join(args.out, f"E14-{args.arm}-payload-record.json")
    with open(record_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

    print(canon_line(canon_ev))
    print(f"arm {args.arm}: {ledger['verdict']}")
    for tier_name, rec in sorted(inserts.items()):
        print(f"  {tier_name}-noise expert (sampler {rec['feeds_expert_sampler']}) <- "
              f"loader {rec['loader_node']} <- {rec['lora_name']}")
    print(f"  PAIR_TIER: {tier.get('verdict')}")
    print(f"  graph   {graph_path}")
    print(f"  record  {record_path}")
    return 0


if __name__ == "__main__":
    # The exit convention, wave 8 (F-3f642bd9). The nine builders and the two fetchers
    # disagreed three ways on how a refusal leaves the process: three carried this block,
    # two exited 2 unconditionally (so a programming error was indistinguishable from a
    # gate refusal), and eight had no handler at all — a Gate CANON halt reached the
    # operator as a raw traceback with exit 1 and no machine-readable evidence.
    #
    # 2 = a gate refused (any `ArmatureError`; `GateFailure` is one). 1 = this tool crashed.
    # ⚠ argparse's own usage errors ALSO exit 2, so a wrapper keys on the `BUILD_LORA_ARM_HALT`
    # sentinel below, never on the code alone.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("BUILD_LORA_ARM_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
