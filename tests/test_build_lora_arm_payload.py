"""E14's arm builder — the checks that would catch it being wrong in the ways that cost money.

Every test below is written against a specific failure: not "does it work" but "what does
this look like if the code is wrong in the one way this check exists to catch". The
expensive failures here are silent ones — a crossed pair and an unnamed field both produce
a graph that runs fine and a report that describes a different experiment.
"""

import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_lora_arm_payload as B  # noqa: E402
from armature_core import route_gates  # noqa: E402
from armature_core.errors import (  # noqa: E402
    ArmatureError, GateCanon, GateFailure)

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "E12-w3-camera-i2v.api.json")
REGISTRY = os.path.join(ROOT, "specs", "E14-seeds.json")
SEED = 2026081233


@pytest.fixture
def base():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- the insertion

@pytest.mark.parametrize("arm", ["T", "S"])
def test_exactly_two_nodes_are_added_and_nothing_is_removed(base, arm):
    built, _ = B.build_arm(base, arm)
    assert sorted(set(built) - set(base)) == ["14", "15"]
    assert set(base) - set(built) == set()


@pytest.mark.parametrize("arm", ["T", "S"])
def test_loader_sits_between_the_unet_loader_and_model_sampling(base, arm):
    """The measured convention. If the splice went in on the far side of ModelSamplingSD3
    the graph would still run and still look plausible in a record — this is the check that
    the order actually matches what the served template demonstrates."""
    built, inserts = B.build_arm(base, arm)
    for tier, rec in inserts.items():
        loader = built[rec["loader_node"]]
        assert loader["class_type"] == "LoraLoaderModelOnly"
        # reads the UNETLoader...
        assert built[str(loader["inputs"]["model"][0])]["class_type"] == "UNETLoader"
        # ...and feeds ModelSamplingSD3, which feeds the expert sampler.
        sampling = built[rec["feeds_model_sampling_node"]]
        assert sampling["class_type"] == "ModelSamplingSD3"
        assert sampling["inputs"]["model"] == [rec["loader_node"], 0]
        assert built[rec["feeds_expert_sampler"]]["inputs"]["model"] == [
            rec["feeds_model_sampling_node"], 0]


@pytest.mark.parametrize("arm", ["T", "S"])
def test_strength_is_one_on_both_experts(base, arm):
    built, _ = B.build_arm(base, arm)
    assert [built[n]["inputs"]["strength_model"] for n in ("14", "15")] == [1.0, 1.0]


def test_the_doubled_suffix_survives_verbatim(base):
    """A 'tidy the filename' bug is a plausible edit and would name a file the catalog does
    not serve. The HIGH member really does end in .safetensors.safetensors."""
    built, _ = B.build_arm(base, "S")
    high = built["14"]["inputs"]["lora_name"]
    assert high.endswith(".safetensors.safetensors")
    assert built["15"]["inputs"]["lora_name"].endswith("_by-AI_Characters.safetensors")
    assert not built["15"]["inputs"]["lora_name"].endswith(".safetensors.safetensors")


def test_arm_T_loads_the_same_single_file_on_both_experts(base):
    built, _ = B.build_arm(base, "T")
    assert (built["14"]["inputs"]["lora_name"]
            == built["15"]["inputs"]["lora_name"]
            == B.TECHNICALLY_COLOR)


# ------------------------------------------------------------------------ the tier andon

def test_crossed_pair_raises(base):
    """THE red test. A crossed pair passes Gate PAIR, Gate ROUTE, Gate S, Gate L and Gate B
    — every other check in the chain — and turns a LoRA-transfer result into a wiring
    result that reads like one. It has to raise here or nowhere."""
    _, inserts = B.build_arm(base, "S")
    crossed = copy.deepcopy(inserts)
    crossed["high"]["lora_name"], crossed["low"]["lora_name"] = (
        crossed["low"]["lora_name"], crossed["high"]["lora_name"])
    crossed["high"]["lora_tier_in_name"] = "low"
    crossed["low"]["lora_tier_in_name"] = "high"
    with pytest.raises(B.TierGate) as exc:
        B.gate_pair_tier(crossed, "S")
    assert "CROSSED" in str(exc.value)


def test_correct_pair_passes_and_says_it_verified(base):
    _, inserts = B.build_arm(base, "S")
    ev = B.gate_pair_tier(inserts, "S")
    assert "tier-matched" in ev["verdict"]
    assert inserts["high"]["lora_tier_in_name"] == "high"
    assert inserts["low"]["lora_tier_in_name"] == "low"


def test_arm_T_reports_not_visible_rather_than_claiming_a_match(base):
    """A gate that cannot fail must not report a pass. T's served file has no tier in its
    name, so the honest verdict is NOT VISIBLE — never 'matched'."""
    _, inserts = B.build_arm(base, "T")
    ev = B.gate_pair_tier(inserts, "T")
    assert ev["tier_checkable"] is False
    assert "NOT VISIBLE" in ev["verdict"]
    assert "tier-matched" not in ev["verdict"]


def test_tier_token_reads_the_served_names():
    assert B._tier_token(B.SMARTPHONE_HIGH) == "high"
    assert B._tier_token(B.SMARTPHONE_LOW) == "low"
    assert B._tier_token(B.TECHNICALLY_COLOR) is None


# ----------------------------------------------------------------------------- the ledger

@pytest.mark.parametrize("arm", ["T", "S"])
def test_ledger_passes_and_counts_only_the_lora_as_generation_reaching(base, arm):
    built, inserts = B.build_arm(base, arm)
    ev = B.gate_ledger(base, built, inserts)
    reaching = {(d["node"], d["field"]) for d in ev["generation_reaching_differences"]}
    assert reaching == {("12", "model"), ("13", "model")}
    assert len(ev["differences"]) == 5  # 2 rewires + 3 filename_prefix


@pytest.mark.parametrize("field,value", [("cfg", 7.0), ("steps", 24),
                                         ("sampler_name", "euler")])
def test_ledger_raises_on_an_unnamed_generation_reaching_change(base, field, value):
    """The whole experiment is 'the LoRA is the only difference'. Anything else that moves
    makes the arm incomparable to the baseline it is read against."""
    built, inserts = B.build_arm(base, "T")
    built["60"]["inputs"][field] = value
    with pytest.raises(B.LedgerGate) as exc:
        B.gate_ledger(base, built, inserts)
    assert field in str(exc.value)


def test_ledger_raises_when_a_named_break_did_not_happen(base):
    """E12 wave 2's failure shape: a record describing a correction that did not occur.
    Here the loader exists but nothing was rewired onto it, so the LoRA is inert."""
    built, inserts = B.build_arm(base, "T")
    built["12"]["inputs"]["model"] = base["12"]["inputs"]["model"]  # undo the rewire
    with pytest.raises(B.LedgerGate) as exc:
        B.gate_ledger(base, built, inserts)
    assert "did NOT actually happen" in str(exc.value)


def test_ledger_raises_if_a_baseline_node_is_dropped(base):
    built, inserts = B.build_arm(base, "T")
    del built["41"]
    with pytest.raises(B.LedgerGate,
                       match=r"nothing authorises a deletion from a byte-pinned graph"):
        B.gate_ledger(base, built, inserts)


def test_prompt_and_negative_are_untouched(base):
    for arm in ("T", "S"):
        built, _ = B.build_arm(base, arm)
        assert built["30"]["inputs"]["text"] == base["30"]["inputs"]["text"]
        assert built["31"]["inputs"]["text"] == base["31"]["inputs"]["text"]
        assert built["40"]["inputs"]["image"] == base["40"]["inputs"]["image"]


# -------------------------------------------------------------------------------- gate S

def test_gate_s_accepts_the_registered_seed(base):
    built, _ = B.build_arm(base, "T")
    ev = B.gate_s(built, REGISTRY, SEED)
    assert ev["seed"] == SEED and SEED in ev["registered"]


def test_gate_s_raises_on_an_unregistered_seed(base):
    built, _ = B.build_arm(base, "T")
    built["60"]["inputs"]["noise_seed"] = 1234
    # The base class, deliberately: builders is narrowing this to a typed
    # GateSSeedRegistration, which is a GateFailure. What is pinned is the CLAUSE, so the
    # test survives that change and stops being satisfiable by any other refusal.
    with pytest.raises(GateFailure, match=r"Gate S: seed 1234 is not in"):
        B.gate_s(built, REGISTRY, 1234)


def test_experts_are_derived_not_assumed(base):
    assert B.experts(base) == {"high": "60", "low": "61"}


# ------------------------------------------------------- the licence mirror (Gate ROUTE)

@pytest.mark.parametrize("dead", [
    "wan22-candid_photography.safetensors",
    "wan22-14b-t2v-80s_fantasy_movie.safetensors",
    "wan2.2_instareal_highnoise.safetensors",
    "wan22-14b-t2v-instagirl.safetensors",
    "wan22-14b-t2v-vintage_film_grain.safetensors",
])
def test_gate_route_raises_on_every_gate_dead_lora(base, dead):
    """The four kills (and instagirl, which inherits) must HALT a graph that names them.
    Before these rows existed they came back 'NOT IN THIS TABLE', which is a shrug."""
    built, _ = B.build_arm(base, "T")
    built["14"]["inputs"]["lora_name"] = dead
    with pytest.raises(route_gates.RouteGate) as exc:
        route_gates.verify(built, frame=(1024, 576, 81))
    assert dead in str(exc.value)


@pytest.mark.parametrize("arm", ["T", "S"])
def test_gate_route_passes_the_two_survivors(base, arm):
    built, _ = B.build_arm(base, arm)
    # WAVE-12 MERGE (coordinator, 2026-09-04): arm T loads the CONDITIONAL LoRA (credit required — the coordinator's
    # ruling, core-gates' tier, builders' record); the record's attribution, built FROM the licence row,
    # is what lets `verify` pass it. Arm S's rows stay ALLOWED.
    attribution = B.conditional_attribution(built)
    ev = route_gates.verify(built, frame=(1024, 576, 81), attribution=attribution)
    verdicts = {c["file"]: c["ruling"]["verdict"] for c in ev["components"]}
    expected = "CONDITIONAL" if arm == "T" else "ALLOWED"
    for node in ("14", "15"):
        assert verdicts[built[node]["inputs"]["lora_name"]] == expected, (arm, verdicts)
    if arm == "T":
        assert attribution and attribution[0]["creditor"] == "renderartist", attribution
        assert ev["components_conditional_credited"] >= 1, ev


def test_the_lora_files_are_not_counted_as_diffusion_weights(base):
    """Arm T's filename contains 't2v'. If LoraLoaderModelOnly were read as a model loader,
    Gate PAIR would see a t2v family beside fun_camera and the pairing question would be
    answered about the wrong file."""
    built, _ = B.build_arm(base, "T")
    loaded = {w["file"] for w in route_gates.model_weights(built)}
    assert B.TECHNICALLY_COLOR not in loaded
    assert all("fun_camera" in f for f in loaded)


def test_gate_pair_still_sees_the_camera_family(base):
    built, _ = B.build_arm(base, "S")
    ev = route_gates.pairing(built)
    assert "fun_camera" in json.dumps(ev)


# --------------------------------------------------------------------------- the prompt


def test_the_positive_is_selected_by_node_identity_not_by_length(base):
    """Wave 3, F-815b8a85. The prompt handed to Gate CANON was
    `max(inherited, key=len)` over every text/prompt/positive string in the base graph, on
    the heuristic that negatives are shorter quality lists. Nothing checked the choice, so
    a base whose NEGATIVE is longer than its positive would have had the negative gated.
    """
    base["30"]["inputs"]["text"] = "short positive"
    base["31"]["inputs"]["text"] = "a very much longer negative " * 20
    text, nodes = B.positive_prompt_from_graph(base)
    assert text == "short positive"
    assert set(nodes.values()) == {"30"}


def test_a_save_format_base_raises_rather_than_yielding_none(base):
    """`canon.texts_from_api_graph` returns [] for any graph whose top-level values are not
    all dicts, so a `.saved.json` passed as --base yielded prompt=None — which
    `require_canon` never examines at all on the --no-canon path. Both formats sit side by
    side in this pipeline's output directories."""
    save_format = {"nodes": [{"id": 30, "type": "CLIPTextEncode",
                              "widgets_values": ["a positive prompt"]}], "links": []}
    # MEASURED, and it is not what the test name says: the refusal that actually fires
    # is the expert-derivation clause ("the baseline does not present one noise-adding
    # sampler starting at step 0 and one noise-free sampler; found {}"), because a save
    # format graph has no API-format nodes for `experts()` to read. The outcome is right
    # and the reason is a different gate; pinning the clause records that rather than
    # leaving a bare root-class raise that any refusal would satisfy.
    with pytest.raises(ArmatureError, match=r"one noise-adding sampler"):
        B.positive_prompt_from_graph(save_format)


def test_an_empty_positive_raises_rather_than_being_gated(base):
    base["30"]["inputs"]["text"] = "   "
    with pytest.raises(ArmatureError,
                       match=r"positive prompt this graph carries is empty"):
        B.positive_prompt_from_graph(base)


def test_the_two_experts_reading_different_positives_raises(base):
    """A base whose experts read different text is not this route, and gating one of them
    would leave the other ungoverned."""
    base["31"]["inputs"]["text"] = "x"
    base["61"]["inputs"]["positive"] = ["31", 0]
    with pytest.raises(ArmatureError,
                       match=r"two experts read different positive prompts"):
        B.positive_prompt_from_graph(base)


def test_the_emitted_graph_must_carry_the_text_the_gate_checked(base):
    """Wave 3, F-dfcc0bea, lora_arm's half: the payload's prompt lives inside the inherited
    --base graph, so the gated string is required to be byte-equal to a string actually
    present in the graph this tool emits."""
    built, _ = B.build_arm(base, "T")
    gated, nodes = B.positive_prompt_from_graph(built)
    assert B.gate_canon_text_is_in_graph(gated, built)["verdict"]
    assert set(nodes.values()) == {"30"}
    with pytest.raises(GateCanon) as exc:
        B.gate_canon_text_is_in_graph("phrases pasted in to get past the refusal", built)
    assert exc.value.evidence["clause"] == "gated_text_is_not_shipped_text"


# ---------------------- Gate S names its own gate id and evidence (wave 6, F-62e3a586)


def test_gate_s_raises_the_typed_gate_with_evidence_on_an_unregistered_seed(base):
    """Both raises constructed the BASE `GateFailure` with no second argument, so
    `evidence` was `{}` and the class attribute `gate` was errors.py's placeholder `"G?"`.
    Measured: `gate_s({}, <registry>, 99)` gave `e.gate == 'G?'`, `e.evidence == {}` and
    `str(e)` beginning `[G?] Gate S:` — the message says Gate S while the receipt says G?.
    `GateSSeedRegistration` (gate = "S") exists for exactly this clause and is what the two
    other implementations use: `route_gates.gate_s_registration` and
    `build_r2v_payload.gate_seed_registered` both raise with an evidence dict. This is the
    arm that spends E14's two generations, and its halt carried no machine-readable record
    of which seed, which registry or which samplers fired it."""
    from armature_core.errors import GateSSeedRegistration

    built, _ = B.build_arm(base, "T")
    built["60"]["inputs"]["noise_seed"] = 99
    with pytest.raises(GateSSeedRegistration) as exc:
        B.gate_s(built, REGISTRY, 99)
    assert exc.value.gate == "S"
    assert exc.value.evidence["seed"] == 99
    assert exc.value.evidence["registry"] == os.path.abspath(REGISTRY)
    assert SEED in exc.value.evidence["registered"]


def test_gate_s_raises_the_typed_gate_when_a_live_sampler_carries_another_seed(base):
    """The second raise site: the seed IS registered, and a noise-adding sampler carries a
    different one. The evidence must name the samplers that fired it."""
    from armature_core.errors import GateSSeedRegistration

    built, _ = B.build_arm(base, "T")
    built["60"]["inputs"]["noise_seed"] = SEED + 1
    with pytest.raises(GateSSeedRegistration) as exc:
        B.gate_s(built, REGISTRY, SEED)
    assert exc.value.gate == "S"
    assert exc.value.evidence["seed"] == SEED
    assert exc.value.evidence["noise_adding_samplers"]


def test_every_gate_s_implementation_in_this_tree_carries_a_gate_id_and_evidence(base):
    """The family census. Three Gate S implementations, and the receipt must be
    unambiguous in all three."""
    import build_r2v_payload as R

    built, _ = B.build_arm(base, "T")
    built["60"]["inputs"]["noise_seed"] = 99
    raisers = [
        lambda: B.gate_s(built, REGISTRY, 99),
        lambda: R.gate_seed_registered(99, [SEED]),
        lambda: route_gates.gate_s_registration(
            {"50": {"class_type": "KSamplerAdvanced",
                    "inputs": {"add_noise": "enable", "noise_seed": 99}}}, [SEED]),
    ]
    for call in raisers:
        with pytest.raises(GateFailure) as exc:
            call()
        assert exc.value.gate != "G?", f"{call} raises a gate with no id"
        assert exc.value.evidence, f"{call} raises a gate with no evidence"


# ---------------- the --base graph goes through the ONE loader (wave 8, F-562a53f1)


def _cli(tmp_path, base_doc, out=None):
    import json as _json

    p = tmp_path / "base.json"
    p.write_text(_json.dumps(base_doc), encoding="utf-8")
    out = out or (tmp_path / "fresh" / "run")
    return [f"--base={p}", "--arm=T", f"--out={out}", f"--seeds-registry={REGISTRY}",
            f"--seed={SEED}", "--subject", "PERFORMER", "--no-canon"], out


def test_a_save_format_base_is_refused_by_a_FORMAT_clause_not_a_route_clause(base,
                                                                             tmp_path):
    """The finding. `--base` was a bare `json.load`, so a save-format doc refused through
    the ROUTE clause: "the baseline does not present one noise-adding sampler starting at
    step 0 and one noise-free sampler; found {}. This tool only knows the E12 two-expert
    split-step route" — the operator is told the ROUTE is wrong when the FORMAT is wrong,
    while `route_gates.is_api_format` on the same doc already answers False. Both formats
    sit side by side in this pipeline's output directories."""
    save_doc = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": ["x"]}],
                "links": [], "last_node_id": 1}
    argv, out = _cli(tmp_path, save_doc)
    with pytest.raises(ArmatureError, match=r"not an API-format graph") as exc:
        B.main(argv)
    assert exc.value.evidence["clause"] == "not_an_api_format_graph"
    assert not out.parent.exists(), "a refused build created its output directory"


def test_a_prompt_wrapped_api_base_is_ACCEPTED(base, tmp_path):
    """The false refusal on the other side of the same clause: the standard submission
    envelope carries a correct two-expert split, and `load_graph` unwraps `prompt` — it is
    in `WRAPPER_KEYS`. Before the fix this raised the identical ROUTE message."""
    argv, out = _cli(tmp_path, {"prompt": base})
    assert B.main(argv) == 0
    assert (out / "E14-T-camera-i2v.api.json").exists()


def test_the_loader_is_route_gates_load_graph_not_a_second_one(base, tmp_path):
    """`load_base` returns the SAME object `route_gates.load_graph` does for a bare api
    file — one loader, and the format clause is the only thing added on top."""
    import json as _json

    p = tmp_path / "base.json"
    p.write_text(_json.dumps(base), encoding="utf-8")
    assert B.load_base(str(p)) == route_gates.load_graph(str(p))


# ------- no BANNED node CLASS rides in on an operator's baseline (wave 8, F-0c05b52e)


def _with_dwpose(base):
    """The repo's own E12 fixture with a `DWPreprocessor` spliced in, fed by a LoadImage.

    `DWPreprocessor` is the exact class the served Animate template wires, and the licence
    map rules its tier (`dwpose`) BANNED — "UNVERIFIED weights tier — treated as NO".
    """
    g = copy.deepcopy(base)
    g["901"] = {"class_type": "LoadImage", "inputs": {"image": "pose.png"}}
    g["900"] = {"class_type": "DWPreprocessor", "inputs": {"image": ["901", 0]}}
    return g


def test_a_banned_node_CLASS_in_the_base_halts_before_any_directory_exists(base, tmp_path):
    """The finding, end to end. Measured 2026-09-04 on this exact splice before the gate:
    `positive_prompt_from_graph` returned the prompt, `build_arm('T')` copied the node
    through, `gate_ledger` reported "2 generation-reaching difference(s), all of them the
    LoRA insertions", `gate_pair_tier` returned NOT VISIBLE, `gate_s` returned its S
    evidence and `route_gates.verify(built, frame=(1024, 576, 81))` returned "6 weight
    file(s), 2 seed(s) all pinned, 1 of 1 latent(s) checkable, 2 frame(s) checked and
    generator-legal" — every gate green — with `built['900']['class_type']` still
    `DWPreprocessor` in the graph written out and submitted.

    SEAM (core-gates -> builders): the class-level census is core-gates'
    (`route_gates.ruled_node_classes`, surfaced through `components()`), carried here rather
    than written a second time. On a tree where that census is not present yet this test is
    the pin that says so.
    """
    argv, out = _cli(tmp_path, _with_dwpose(base))
    with pytest.raises(ArmatureError, match=r"licence map rules BANNED") as exc:
        B.main(argv)
    ev = exc.value.evidence
    assert ev["gate"] == "ROUTE" and ev["andon"] == "RouteGate"
    assert ev["clause"] == "banned_component_in_base"
    assert [b["class_type"] for b in ev["banned"]] == ["DWPreprocessor"]
    assert not out.parent.exists(), "a refused build created its output directory"


def test_the_licence_gate_reads_ONE_census_and_fires_on_every_row_shape(base,
                                                                       monkeypatch):
    """The call site's own half, independent of which build of `route_gates` is in front of
    it: the gate is a filter over `components()` — core-gates' single census of weight rows
    AND class rows — and it refuses any row the map rules BANNED, printing the map's own
    licence and reason. Stubbing the census proves the filter, the evidence and the halt;
    the test above proves the whole path."""
    row = {"kind": "class", "file": None, "class_type": "DWPreprocessor", "node_id": "900",
           "where": "graph", "verdict": "BANNED", "licence": "weights not fetched",
           "reason": "UNVERIFIED weights tier — treated as NO", "matched_on": "dwpose"}
    monkeypatch.setattr(route_gates, "components", lambda g: [row])
    with pytest.raises(ArmatureError, match=r"licence map rules BANNED") as exc:
        B.gate_base_licence(base, "some/base.json")
    assert exc.value.evidence["banned"][0]["matched_on"] == "dwpose"
    assert "UNVERIFIED weights tier" in str(exc.value)

    # A weight row in the PRE-wave-8 shape (verdict under `ruling`) fires the same filter.
    old = {"file": "causvid_x.safetensors", "node_id": "12", "class": "LoraLoader",
           "where": "graph",
           "ruling": {"verdict": "BANNED", "licence": "CC-BY-NC",
                      "reason": "non-commercial", "matched_on": "causvid"}}
    monkeypatch.setattr(route_gates, "components", lambda g: [old])
    with pytest.raises(ArmatureError, match=r"licence map rules BANNED") as exc:
        B.gate_base_licence(base, "some/base.json")
    assert exc.value.evidence["banned"][0]["file"] == "causvid_x.safetensors"


def test_the_clean_baseline_passes_the_licence_gate_and_the_record_carries_its_verdict(
        base, tmp_path):
    """The mutation that must NOT fire it: the repo's own pinned E12 baseline, and the
    verdict lands in the payload record beside the other gates rather than only on stdout.
    """
    import json as _json

    ev = B.gate_base_licence(base, FIXTURE)
    assert ev["banned"] == []
    # Wave 14, F-b7e7c5c0. This assertion used to read `"none BANNED" in ev["verdict"]`,
    # against a verdict that read "{n} ruled component(s) read off the baseline, none
    # BANNED and none EXCLUDED" — and the measurement below is why that sentence had to
    # go: on the repo's OWN pinned E12 baseline the licence table classifies ZERO of the
    # four components it loads. "nothing banned" and "the table ruled nothing" were the
    # same receipt, and this test asserted the half that was not measured. The numbers are
    # pinned with `==` rather than re-derived, per the wave-14 rule on ceilings.
    assert ev["n_components_examined"] == 4
    assert ev["n_components_classified"] == 0
    assert ev["n_components_unclassified"] == 4
    assert "0 of 4 component(s)" in ev["verdict"]
    assert "4 unclassified" in ev["verdict"]
    assert "none of the classified is BANNED or EXCLUDED" in ev["verdict"]
    assert "wan_2.1_vae.safetensors" in " ".join(ev["unclassified"])

    argv, out = _cli(tmp_path, base)
    assert B.main(argv) == 0
    record = _json.loads((out / "E14-T-payload-record.json").read_text(encoding="utf-8"))
    assert record["gates"]["BASE_LICENCE"]["banned"] == []


def test_every_builder_puts_its_graph_through_the_licence_census():
    """The family, derived rather than typed.

    family: derived by AST over `tools/build_*payload*.py` + `tools/gate_saved_graph.py`
    for a call to `route_gates.verify` / `RG.verify` -> 10 sites — build_animate_payload,
    build_assembly_payload, build_camera_i2v_payload, build_cascade_payload,
    build_i2v_payload, build_lora_arm_payload, build_r2v_payload, build_t2v_payload,
    gate_saved_graph (one call each). `verify()` reads `components()`, which is the census
    that gained class rows, so every one of them refuses a licence-BANNED node class
    without a line of its own.

    `build_lora_arm_payload` needed a gate of its own anyway and is the ONE member whose
    graph arrives as a FILE: its `verify` call runs on the graph it BUILT, after
    `canon_spend`, so a baseline carrying a banned tier had already been read from and
    reasoned about. `gate_base_licence` sits immediately after the `--base` load.
    """
    import ast

    from conftest import TOOLS

    import _census_nodes as CN

    # Graph builders + the admission writer. Wave-34 submit/uploads match the build_*
    # payload glob but are not graph authors (`CN.NON_GRAPH_PAYLOAD`).
    population = CN.graph_payload_builders() + ["gate_saved_graph.py"]
    assert population == [
        "build_animate_payload.py", "build_assembly_payload.py",
        "build_camera_i2v_payload.py", "build_cascade_payload.py",
        "build_i2v_payload.py", "build_lora_arm_payload.py", "build_payload.py",
        "build_r2v_payload.py", "build_t2v_payload.py",
        "gate_saved_graph.py"], population
    assert CN.boundary_payload_tools() == [
        "build_routes_payload.py", "build_submit_payload.py", "build_uploads_payload.py"]

    #: The ONE exemption, named and dated: `build_payload.py` (E02/E03/E06's VACE route)
    #: predates `route_gates` and gates through `armature_core.gates` instead, so the
    #: licence census does not reach it through `verify`. The reason is re-derived below
    #: rather than asserted — the census is run on the graph it actually emits.
    EXEMPT = {"build_payload.py"}
    assert EXEMPT <= set(population)

    for name in sorted(set(population) - EXEMPT):
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
        calls = [n for n in ast.walk(ast.parse(src))
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "verify"
                 and isinstance(n.func.value, ast.Name)
                 and n.func.value.id in ("route_gates", "RG")]
        assert calls, f"{name} never puts its graph through route_gates.verify"

    # The exemption's reason, checked rather than trusted: the graph `build_payload` emits
    # is built entirely from its own module constants, so the census run over it directly
    # must report nothing the licence map rules BANNED. If a banned weight ever reaches
    # those constants this fails, exemption or not.
    import build_payload as bp

    wf, _meta = bp.build("B2", "E03")            # the null arm — no uploads, no reference
    ruled = route_gates.components(wf)
    banned = [r for r in ruled
              if (r.get("verdict") or (r.get("ruling") or {}).get("verdict")) == "BANNED"]
    assert ruled, "the census read no component at all off build_payload's graph"
    assert banned == [], banned

    # And the builder that reads a graph off disk checks BEFORE it builds anything.
    src = open(os.path.join(TOOLS, "build_lora_arm_payload.py"), encoding="utf-8").read()
    assert src.index("gate_base_licence(base") < src.index("canon_spend(")


# ================================ wave 12: the CONDITIONAL licence row, credited from the ROW
# The coordinator's ruling of 2026-09-04 (delegated by the Director): `docs/license-map.md:77`
# rules `wan22-14b-t2v-technically_color.safetensors` "YES — credit required" (CivitAI grant
# `allowCommercialUse [RentCivit, Rent, Image]`, `allowNoCredit: false`, creator renderartist,
# fetched 2026-08-13), while `route_gates.RULED_COMPONENTS` mirrored it as an unconditional
# ALLOWED. The condition is ACCEPTED as the map already records it, and becomes load-bearing
# in code: core-gates adds the CONDITIONAL tier and `verify(attribution=…)`; this builder
# writes the credit entry into the payload record and the provenance, BUILT FROM THE ROW and
# never typed here, and hands it to the gate that checks it.
#
# family: keyed on the RECORD FIELD a licence condition obliges — `credit_obligation` /
# `attribution` — over the builders that load a ruled component, via `ARMS[*]["row"]` naming
# the licence-map row rather than a prose sentence -> 1 arm carries a condition today (T),
# and the derivation picks up any future CONDITIONAL row without editing this file.


def test_the_credit_line_is_read_from_the_licence_row_not_typed_in_the_builder():
    """The ruling's mechanism: the record's obligation names where it came from, so a reader
    can tell a line derived from the map from a line a builder retyped."""
    ob = B.credit_obligation("T")
    assert ob["component"] == "technically_color"
    assert "route_gates.RULED_COMPONENTS" in ob["source_of_this_line"] or (
        "ARMS table" in ob["source_of_this_line"])
    if "route_gates.RULED_COMPONENTS" in ob["source_of_this_line"]:
        row = route_gates.RULED_COMPONENTS["technically_color"]
        assert ob["creditor"] == row["condition"]["creditor"]
        assert ob["text"] == row["condition"]["text"]


def test_arm_S_carries_no_licence_row_and_no_credit_condition():
    """The mutation that must not fire it. `allowNoCredit: true` on the smartphone pair, so
    the arm names no row and the record's obligation is not a condition."""
    assert B.ARMS["S"]["row"] is None
    assert "creditor" not in B.credit_obligation("S")


def test_the_attribution_entries_come_from_the_table_and_are_HANDED_to_the_gate(monkeypatch):
    """`conditional_attribution` asks `route_gates` which components the graph loads that
    carry a condition, and builds each entry from that row. This builder does not decide."""
    asked = {}

    def fake_keys(graph):
        asked["graph"] = graph
        return ["technically_color"]

    def fake_entry(key):
        return {"component": key, "creditor": "renderartist",
                "source": "CivitAI 2106471",
                "text": "Technically Color LoRA by renderartist (CivitAI)"}

    monkeypatch.setattr(route_gates, "conditional_component_keys", fake_keys,
                        raising=False)
    monkeypatch.setattr(route_gates, "attribution_entry_for", fake_entry, raising=False)
    graph = {"1": {"class_type": "LoraLoaderModelOnly", "inputs": {}}}
    entries = B.conditional_attribution(graph)
    assert asked["graph"] is graph
    assert entries == [fake_entry("technically_color")]


def test_a_CONDITIONAL_row_with_no_reader_for_it_is_a_REFUSAL_not_an_empty_list(monkeypatch):
    """The andon on the direction the pre-merge branch does not bound. `[]` is the right
    answer only while the table rules nothing CONDITIONAL — and that premise is CHECKED. A
    table that rules a row CONDITIONAL while the helpers that read it are absent means the
    answer is UNKNOWN, and an unknown attribution is not something this tool completes."""
    monkeypatch.delattr(route_gates, "conditional_component_keys", raising=False)
    monkeypatch.delattr(route_gates, "attribution_entry_for", raising=False)
    monkeypatch.setitem(route_gates.RULED_COMPONENTS, "a_conditional_row",
                        {"verdict": "CONDITIONAL", "licence": "x", "reason": "y"})
    with pytest.raises(route_gates.RouteGate,
                       match=r"CONDITIONAL and carries no `conditional_component_keys`") as e:
        B.conditional_attribution({})
    assert e.value.evidence["clause"] == "conditional_tier_without_its_readers"
    assert "a_conditional_row" in e.value.evidence["conditional_rows"]


def test_the_builder_types_no_creditor_name_of_its_own():
    """The ruling's words: `never a literal typed in the builder`. The census keys on the
    creditor STRING — if it appears anywhere in this module outside the ARMS prose fallback
    and the docstrings, the record can drift from the map."""
    import ast

    from conftest import TOOLS

    src = open(os.path.join(TOOLS, "build_lora_arm_payload.py"), encoding="utf-8").read()

    literals = []
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and "renderartist" in node.value):
            literals.append(node.lineno)
    assert len(literals) <= 1, (
        f"`renderartist` is typed at lines {literals}; the credit line comes from "
        f"route_gates.RULED_COMPONENTS' own row")
