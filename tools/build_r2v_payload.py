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
    canonical_payload_digest, disclosure_lines, fetch_recipe, read_seed_registration)
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


#: What each arm's ONE input is: the flag that supplies it, the `build()` keyword and the
#: `argparse` dest that carry it, and what the file is for. Lifted to module level in wave
#: 25 (F-9dd141d9) from a local inside `build_and_write`, so the CLI and the library call
#: read the same table.
ARM_INPUT = {
    "A1": {"flag": "--refs", "arg": "refs", "dest": "refs",
           "what": ("the reference record JSON whose views become this arm's reference "
                    "image slots")},
    "A2": {"flag": "--uploads", "arg": "upload_names", "dest": "uploads",
           "what": ("the frame uploads map JSON the in-graph cascade assembles the "
                    "reference VIDEO from")},
}


def gate_arm_input(arm, value):
    """One condition, ONE clause word: this arm was given no input. · ANDON

    Wave 25, F-9dd141d9. The condition carried TWO clause words on the hosted partner tier
    that bills per submission: `build()` raised `arm_input_missing` for arm A1 (`--refs`)
    and arm A2 (`--uploads`), while `build_and_write` raised `missing_arm_input` for the
    same two arms off its own local copy of this table. (The clause key and its value are
    written apart here on purpose — a census that regexes module SOURCE for the pair reads
    a quotation as a raise site.) Both words were live in the vocabulary census
    (`_census_nodes.clause_literals`, re-derived at the time as 385 distinct literals with
    both present) and neither was in `CLAUSES_NAMED_BY_NO_FIXTURE`, so the census carried
    two live clauses where one condition exists.

    Via the CLI only `missing_arm_input` was ever printed, because the CLI check ran BEFORE
    `build()`; a library caller of `build()` saw only `arm_input_missing`. No artifact was
    wrong and the refusal was correct in both spellings — what was wrong is that a wrapper
    keyed on the clause word had to know which layer refused.

    `missing_arm_input` is the word that survives: it is the one the CLI actually printed,
    and its message names the flag and says what the file is for. The other spelling is
    deleted, and `build()` calls this check rather than carrying a second one — so there is
    ONE raise, not two words agreeing.
    """
    spec = ARM_INPUT.get(arm)
    if spec is None or value:
        return
    raise RG.RouteGate(
        f"arm {arm} needs {spec['flag']}: it is {spec['what']}, and this arm cannot be "
        f"built without it. The omission used to surface as a NoneType traceback from "
        f"`open`, two gates later",
        {"gate": "ROUTE", "andon": "RouteGate", "clause": "missing_arm_input",
         "arm": arm, "flag": spec["flag"]})


#: The **wan2.7-r2v partner tier's disclosure row** — what a user of THIS route is exposed
#: to, mirrored from the licence map's own FETCHED documents and from the E13 probe report
#: that recorded them.
#:
#: Wave 28, F-2dcaf53a. This tool authors the ONLY hosted-partner-tier spend in this repo and
#: said nothing about what riding that tier costs its user. MEASURED end to end in this
#: worktree before the fix (`build_r2v_payload.main` on the committed `specs/E13-seeds.json`
#: + `specs/E13-prompt.json`, arm A1, seed 2026081351): the whole of stdout was nine lines —
#: the canon line, `arm`, `nodes`, `seed gate`, `ceiling gate`, `route`, `gate L (hosted)`,
#: `slots`, `BUILD_R2V_OK` — and not one of them named a data-use posture, an AI-content
#: disclosure duty or a watermark policy; the payload record beside the graph carried `tier`,
#: `payload`, `slot_order`, `gate_pair_note`, `gate_l_note` and `payload_sha256` and no
#: disclosure key either. Meanwhile the E14 sibling had been given exactly that surface a
#: wave earlier (F-92f67091) for a SMALLER obligation — one credits line on one LoRA.
#:
#: CLAUDE.md's per-route disclosure ruling (the Director, 2026-08-12) was born on THIS route:
#: a route that sends assets through a third-party tier documents its data-use posture, its
#: AI-content disclosure duty and its watermark policy, grounded in the licence map's fetched
#: documents. The obligations below are the map's words, not this builder's.
#:
#: ⚠ **Where this table would belong if it could.** `route_gates.HOSTED_TIER_RULES` is the
#: machine-readable home for what a hosted tier ALLOWS (its enums), and the natural home for
#: what a hosted tier OBLIGES is beside it, the way `RULED_COMPONENTS.condition` holds the
#: weight rows' obligations and `attribution_entry_for` builds a record entry from them. That
#: module is core-gates' and carries no finding for this row, so the row is declared here — in
#: the one tool in this tree that rides this tier — with its source documents named, and the
#: consolidation is posted to the relay rather than done by reaching into another domain's
#: file. If a second tool ever rides a hosted tier, this table moves; it does not get copied.
TIER_DISCLOSURE = {
    "tier": TIER,
    "surface": "Comfy Cloud hosted partner tier (Comfy-mediated)",
    "provider_terms": {
        "document": "Wan Terms of Service",
        "url": "https://wan.video/policy/termsofService",
        "updated": "2026-08-06",
        "fetched": "2026-08-12 (the Director's local export; fetchers get a JS shell)",
        "sha256": "26d81f01...cb4cd6",
        "recorded_in": ("docs/license-map.md, row 'Wan 2.6/2.7 partner tier'; "
                        "docs/experiments/E13-composed-route-probe.md"),
    },
    "output_ownership": ("the provider assigns to the submitter all right, title and "
                         "interest it has in Outputs (Wan ToS SIII.4), and Comfy's own row "
                         "fills our side of the chain"),
    "ruling": ("CONDITIONAL ACCEPTED by the Director, 2026-08-12 — proceed via Comfy. The "
               "condition he attached is DISCLOSURE, which is why these lines exist and why "
               "they are printed rather than filed"),
    "residual": ("WHICH paper governs Comfy-mediated partner calls is NOT established: the "
                 "Wan ToS governs services accessible via wan.video and its own SII.1(c) "
                 "bans automated extraction of Outputs, which cannot describe the API tier; "
                 "Comfy's row says no training on Input/Output; the Comfy-Alibaba reseller "
                 "agreement is unseeable. The exposure is stated at its WIDEST reading here, "
                 "because a disclosure that assumes the friendlier paper is not a disclosure"),
    "obligations": [
        {"kind": "training_use",
         "text": ("uploaded User Content — this submission's prompt, its reference images "
                  "or reference video, and the Outputs — is licensed to the provider "
                  "'unconditional, irrevocable ... fully transferable, sub-licensable, "
                  "perpetual, worldwide' (SIII.6), deemed non-confidential and "
                  "non-proprietary (SIII.3(c)) and expressly usable 'to develop and improve "
                  "our machine-learning and artificial-intelligence technologies' "
                  "(SIII.3(e)). That is the trade this route makes: the character plates "
                  "and frames you send carry a training-and-publication licence to the "
                  "provider on this surface"),
         "applies_to": "every asset and prompt this submission uploads",
         "source": "Wan ToS SIII.6 / SIII.3(c) / SIII.3(e), fetched 2026-08-12"},
        {"kind": "ai_content_disclosure",
         "text": ("footage published from this route must 'clearly and conspicuously "
                  "disclose' that it was generated by artificial intelligence (SIII.8(g)). "
                  "The duty is on the PUBLICATION, not on this build, so nothing downstream "
                  "of here will remind you of it — which is exactly why it is said at the "
                  "moment the spend is authored"),
         "applies_to": "published footage from this route",
         "source": "Wan ToS SIII.8(g), fetched 2026-08-12"},
        {"kind": "watermark",
         "text": ("`watermark` is a REQUEST in the payload and nothing more: it does not "
                  "promise the returned footage carries no mark. If a label or watermark IS "
                  "applied, REMOVING it is banned (SII.1(a)), and the Model Studio "
                  "service-specific terms repeat the ban on tampering with an 'AI-generated' "
                  "label. Inspect the returned frames before publishing rather than reading "
                  "this flag as an answer"),
         "applies_to": "the footage this submission returns",
         "source": ("Wan ToS SII.1(a); Model Studio service-specific terms "
                    "(help.aliyun.com/en/model-studio/bailian-service-notes), "
                    "fetched 2026-08-12")},
    ],
}


def disclosure(arm, route_ev, watermark_requested):
    """The per-route disclosure block for one E13 submission.

    Every field is READ from `TIER_DISCLOSURE` — the licence map's own row — or from Gate
    ROUTE's own receipt, except the watermark REQUEST, which is read from the payload this
    build actually sends. Nothing is typed twice, and the block is stored in the payload
    record under `disclosure` and rendered to stdout by
    `build_assembly_payload.disclosure_lines`, the ONE renderer the E14 sibling also uses.
    """
    obligations = [dict(o) for o in TIER_DISCLOSURE["obligations"]]
    for ob in obligations:
        if ob["kind"] == "watermark":
            ob["text"] = (f"`watermark={bool(watermark_requested)}` was sent. " + ob["text"])
    return {
        "route": f"E13 arm {arm} - {TIER} on the {TIER_DISCLOSURE['surface']}",
        "tier": TIER,
        "provider_terms": TIER_DISCLOSURE["provider_terms"],
        "output_ownership": TIER_DISCLOSURE["output_ownership"],
        "ruling": TIER_DISCLOSURE["ruling"],
        "residual": TIER_DISCLOSURE["residual"],
        "watermark_requested": bool(watermark_requested),
        "obligations": obligations,
        "route_verdict": route_ev.get("verdict"),
        "read_from": ("build_r2v_payload.TIER_DISCLOSURE, mirrored from "
                      "docs/license-map.md's 'Wan 2.6/2.7 partner tier' row and the fetched "
                      "documents it names"),
        "checked_by": ("nothing in code: this tier's obligations bind PUBLISHED FOOTAGE and "
                       "an uploaded asset already sent, neither of which a build-time gate "
                       "can observe. They are DISCLOSED at the moment the spend is authored, "
                       "which is the whole of what CLAUDE.md's per-route disclosure ruling "
                       "asks of this route - stated here rather than left as a silence a "
                       "reader could mistake for a gate"),
    }


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

    # ONE check, both layers (wave 25, F-9dd141d9): the same call `build_and_write` makes
    # before it opens anything, so a library caller and the CLI refuse the same condition
    # under the same word.
    gate_arm_input(arm, {"A1": refs, "A2": upload_names}.get(arm))

    if arm == "A1":
        for i, name in enumerate(refs):
            nid = str(FIRST_IMAGE_ID + i)
            wf[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
            inputs[f"model.reference_images.image{i + 1}"] = [nid, 0]
    elif arm == "A2":
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
    tier_rules = RG.HOSTED_TIER_RULES[TIER]
    ap = argparse.ArgumentParser(
        description=(
            "Build and gate ONE E13 submission for the wan2.7-r2v hosted partner tier - the "
            "only route in this repo that bills per submission. Writes the API graph and its "
            "payload record; submits nothing."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
                "ROUTE: E13, the composed route - a GLB-staged performance carried into video through a reference slot (A1: four composited kit views; A2: a reference VIDEO constructed in-graph by the cascade).\n"
                "\n"
                "WHAT A REFUSAL COSTS: nothing but your time, and that is the point - every gate here runs BEFORE a credit is spent, and spent credits have no compensator.\n"
                "\n"
                "WHAT THIS ROUTE COSTS ITS USER: the disclosure lines printed above BUILD_R2V_OK, per CLAUDE.md's per-route disclosure ruling - read them before you submit."))
    build_opts = ap.add_argument_group("build")
    output_opts = ap.add_argument_group("output")

    build_opts.add_argument("--arm", required=True, choices=("A1", "A2"),
                    help="A1 feeds the reference IMAGE slots from --refs; A2 feeds the "
                         "reference VIDEO slot from a cascade built in this same graph "
                         "out of --uploads")
    build_opts.add_argument("--seed", type=int, required=True,
                    help="the seed to submit. It must appear in --seeds: Gate S refuses an "
                         "unregistered number before anything is written")
    build_opts.add_argument("--seeds", required=True, help="the committed seed registration")
    build_opts.add_argument("--prompt-file", required=True,
                    help="JSON carrying `prompt` and `negative_prompt`. The SHIPPED prompt "
                         "is what Gate CANON gates, so a refusal cannot be worked around "
                         "with --canon-prompt")
    # ⚠ No `--overwrite` here, and that is MEASURED rather than an omission (wave 28,
    # F-5fd16451). This tool's re-run case is ALREADY CLOSED, one gate earlier and by
    # another domain's file: `canon_spend(..., out_dir=out)` reaches
    # `armature_core.canon._gate_out_dir`, whose `out_dir_not_empty` clause refuses a
    # non-empty `--out` outright. MEASURED as three subprocesses in this worktree on the
    # committed E13 specs, arm A1, seed 2026081351: the first run exits 0 with
    # BUILD_R2V_OK; the second into the same `--out` exits 2 with
    # `BUILD_R2V_HALT … "gate": "CANON" … "clause": "out_dir_not_empty" …` naming both
    # files; and the third with `--overwrite` ALSO halts at CANON, because that gate runs
    # above this point. So an `--overwrite` flag here would be a flag that cannot fire —
    # "a check that cannot fail is not a check" — and wiring a bypass around another
    # domain's gate is not this fix. The half of F-5fd16451 that IS open here is the
    # printed digest below, so two runs are distinguishable in a scrollback.
    output_opts.add_argument("--out", required=True,
                    help="the directory the graph and its payload record are written into. "
                         "Created below the last gate, so a refusal leaves nothing behind; "
                         "Gate CANON refuses a --out that already holds entries, so a "
                         "rebuild goes to a fresh directory")
    build_opts.add_argument("--refs", default=None, help="A1: the reference record JSON")
    build_opts.add_argument("--uploads", default=None, help="A2: the frame uploads map JSON")
    build_opts.add_argument("--resolution", default="720P",
                    help=f"one of {tier_rules['resolutions']} - the tier's own enum, "
                         f"measured by {tier_rules['measured']}. Gate L refuses anything "
                         f"else by name (default: %(default)s)")
    build_opts.add_argument("--ratio", default="16:9",
                    help=f"one of {tier_rules['ratios']} - the tier's own enum. Gate L "
                         f"refuses anything else by name (default: %(default)s)")
    build_opts.add_argument("--duration", type=int, default=5,
                    help=f"clip seconds, inside the tier's bound "
                         f"{tier_rules['duration_s']} inclusive (default: %(default)s)")
    build_opts.add_argument("--group", type=int, default=AS.GROUP_SIZE,
                    help="A2 only: frames per BatchImagesNode in the in-graph cascade. The "
                         "slot ceiling gate checks it against the cascade's own constant "
                         "(default: %(default)s)")
    build_opts.add_argument("--prefix", default=None,
                    help="the server-side filename prefix for the saved video; defaults to "
                         "video/E13_<arm>_seed<seed>, so two arms cannot write to one path")
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
    # ONE table, ONE raise (wave 25, F-9dd141d9): the local copy this replaces spelled the
    # same condition `missing_arm_input` here and `arm_input_missing` inside `build()`, so
    # which word a halt reader saw depended on which layer refused.
    gate_arm_input(a.arm, getattr(a, ARM_INPUT[a.arm]["dest"]))

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
    # The per-route disclosure block (wave 28, F-2dcaf53a), built from the licence map's own
    # row and Gate ROUTE's own receipt. The watermark half is read off the payload THIS build
    # actually sends, never off the literal at the `build()` call — a disclosure that
    # describes a value the graph does not carry is the wiring claim CLAUDE.md forbids.
    # Built ABOVE the record so the record carries it; printed BELOW, so an operator meets it
    # whether they read stdout or the JSON.
    disclosure_block = disclosure(a.arm, gate_route, node_inputs.get("watermark"))

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
        # The per-route disclosure CLAUDE.md's ruling requires of a route that rides a
        # third-party tier: the training-use trade, the AI-content disclosure duty on
        # published footage, and what the watermark request does and does not promise. It
        # rides the provenance, and `disclosure_lines` says it out loud below (wave 28,
        # F-2dcaf53a; the E14 sibling's shape, adopted through its renderer, not respelled).
        "disclosure": disclosure_block,
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
    # Wave 34, F-dc84b444 — fetch recipe for the SaveVideo tap (partner disclosure already
    # rides `disclosure` above; do not re-open that LOOK).
    record.update(fetch_recipe(
        node_map={}, video_nodes=(str(SAVE_ID),),
        root_hint="outputs/E13/runs",
        taps=[{"node": str(SAVE_ID), "class_type": SAVE_CLASS, "subdir": None}]))

    # Below the last in-tool gate. `os.makedirs` used to sit above Gate S, so a refused
    # spend left an empty run directory beside real ones — the invariant build_payload.py
    # states for Gate CANON, applied to every gate in this tool.
    graph_path = os.path.join(out, f"E13-{a.arm}-seed{a.seed}.api.json")
    record_path = os.path.join(out, f"E13-{a.arm}-seed{a.seed}-payload-record.json")
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories
    with open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    with open(record_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

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
    # Wave 28, F-5fd16451, the half that is open on this tool: the digest that ties this
    # record to this graph, on the success line, so two runs are distinguishable in a
    # scrollback. Before this, two builds of different arms printed nine lines that carried
    # no value differing between them. Gate CANON's `out_dir_not_empty` already closes the
    # re-run-into-one-directory half here (see the note at `--out`).
    print(f"payload sha256   {record['payload_sha256']}")
    # Wave 28, F-2dcaf53a. The one route in this repo that bills per submission now says
    # what riding it costs its user, at the moment the spend is authored — the E14 sibling's
    # renderer, imported, not respelled.
    for line in disclosure_lines(disclosure_block):
        print(line)
    print("BUILD_R2V_OK " + json.dumps({"path": graph_path}, ensure_ascii=False))
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

