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
    with pytest.raises(B.LedgerGate):
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
    ev = route_gates.verify(built, frame=(1024, 576, 81))
    verdicts = {c["file"]: c["ruling"]["verdict"] for c in ev["components"]}
    for node in ("14", "15"):
        assert verdicts[built[node]["inputs"]["lora_name"]] == "ALLOWED"


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
