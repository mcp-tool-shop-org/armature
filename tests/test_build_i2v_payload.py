"""The no-control I2V graph builder, against the ways E11 stops being E11.

E11's defining property is a NEGATIVE — nothing conditions the generation but one image
and one prompt — and a negative property is exactly the kind that decays without anybody
noticing: a control node added later still generates a video, still passes Gate L, Gate S,
Gate ROUTE and the saved round trip, and still costs the same. So most of what is checked
here is the absence, and each fixture builds the presence and shows it refused.

Nothing here touches the network, and `build` takes its prompts as arguments, so every
fixture is arithmetic on a dict.
"""

import copy
import json
import os

import pytest

from conftest import TOOLS, REPO  # noqa: F401
import build_i2v_payload as B
from armature_core import errors as E
from armature_core import gates as G
from armature_core import route_gates as RG


UPLOADS = {"start_frame": "start.png"}
POS, NEG = "a jointed clay mannequin dancing in a bar", "blurry, low quality"
E11_SEEDS = [2026081231, 2026081232, 2026081233]


def built(**kw):
    kw.setdefault("registry", E11_SEEDS)
    return B.build(UPLOADS, kw.pop("seed", E11_SEEDS[0]), kw.pop("negative", NEG),
                   kw.pop("positive", POS), kw.pop("registry"), **kw)


# ------------------------------------------------------------------- the shot's shape

def test_the_defaults_build_e08s_frame_because_the_ab_needs_them_to():
    """65 @ 16 fps is E08's, and the deliverable is the two probes side by side at true
    tempo. A different length or rate here would put a third variable into a comparison
    that already spans two models and two conditioning routes."""
    wf, meta = built()
    assert (meta["resolution"], meta["length"], meta["fps"]) == ([832, 480], 65, 16)
    assert wf["50"]["inputs"]["length"] == 65
    assert wf["80"]["inputs"]["fps"] == 16


def test_the_two_experts_are_both_loaded_and_neither_is_a_lora():
    wf, meta = built()
    unets = sorted(n["inputs"]["unet_name"] for n in wf.values()
                   if n["class_type"] == "UNETLoader")
    assert unets == sorted([B.UNET_HIGH, B.UNET_LOW])
    assert meta["models"]["loras"] == []
    assert not any(n["class_type"].startswith("LoraLoader") for n in wf.values())


def test_the_trajectory_values_are_the_ones_the_record_claims():
    wf, _ = built()
    hi, lo = wf["60"]["inputs"], wf["61"]["inputs"]
    assert (hi["steps"], hi["cfg"], hi["sampler_name"], hi["scheduler"]) == \
        (20, 3.5, "euler", "simple")
    assert (hi["start_at_step"], hi["end_at_step"]) == (0, 10)
    assert (lo["start_at_step"], lo["end_at_step"]) == (10, 10000)
    assert wf["12"]["inputs"]["shift"] == wf["13"]["inputs"]["shift"] == 8.0


# ---------------------------------------------------- the defining property: no control

@pytest.mark.parametrize("cls", ["WanVaceToVideo", "WanAnimateToVideo",
                                 "Wan22FunControlToVideo", "ControlNetApplyAdvanced"])
def test_any_control_capable_conditioning_class_refuses_the_graph(cls):
    """The failure this exists for is not an error — it is a different experiment wearing
    E11's file names. A control node present is one edit from being fed, and the licence
    map's own ruling on a bypassed node is that presence is presence."""
    wf, _ = built()
    wf["99"] = {"class_type": cls, "inputs": {}}
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert cls in str(exc.value)


def test_a_second_uploaded_image_refuses_the_graph():
    """A reference image, a scene plate, a last frame — whatever it is labelled, a second
    LoadImage is a second conditioning channel, and E11's question is what one channel
    does on its own."""
    wf, _ = built()
    wf["42"] = {"class_type": "LoadImage", "inputs": {"image": "reference.png"}}
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "second uploaded image" in str(exc.value)


def test_wiring_clip_vision_refuses_the_graph():
    wf, _ = built()
    wf["50"]["inputs"]["clip_vision_output"] = ["45", 0]
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "clip_vision_output" in str(exc.value)


def test_a_sampler_fed_straight_from_the_text_encode_refuses_the_graph():
    """The silent one. Wire the text encodes to the samplers instead of to the
    conditioning node's outputs and the graph still runs, still costs the same, and still
    returns 65 frames — of a video the start image never conditioned. Nothing else in the
    chain looks at which CONDITIONING a sampler received."""
    wf, _ = built()
    wf["60"]["inputs"]["positive"] = ["30", 0]
    wf["60"]["inputs"]["negative"] = ["31", 0]
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "conditioning" in str(exc.value)


def test_the_experts_must_hand_over_at_the_same_step():
    """A gap repeats part of the trajectory and an overlap skips part of it. Both produce
    a complete, well-formed clip at the same price."""
    wf, _ = built()
    wf["61"]["inputs"]["start_at_step"] = 12
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "hand over" in str(exc.value)


def test_the_low_noise_expert_must_continue_the_high_noise_latent():
    wf, _ = built()
    wf["61"]["inputs"]["latent_image"] = ["50", 2]
    with pytest.raises(B.PayloadError):
        B.verify_topology(wf, "start.png")


def test_the_gate_b_probe_must_read_the_upload_directly():
    """A probe reading anything but the LoadImage output proves nothing about what the
    server decoded, which is the only half the local round trip cannot check."""
    wf, _ = built()
    wf["41"]["inputs"]["images"] = ["70", 0]
    with pytest.raises(B.PayloadError):
        B.verify_topology(wf, "start.png")


def test_the_lossless_tap_must_read_the_decode_directly():
    wf, _ = built()
    wf["71"]["inputs"]["images"] = ["40", 0]
    with pytest.raises(B.PayloadError):
        B.verify_topology(wf, "start.png")


def test_a_link_to_a_node_that_does_not_exist_refuses_the_graph():
    wf, _ = built()
    wf["70"]["inputs"]["samples"] = ["999", 0]
    with pytest.raises(B.PayloadError):
        B.verify_topology(wf, "start.png")


# ------------------------------------------------------------------------- Gate L / S

@pytest.mark.parametrize("length", [64, 66, 85])
def test_gate_l_raises_on_an_illegal_frame_count(length):
    """64 and 66 are not 4n+1; 85 is past the trained horizon. Each would generate."""
    with pytest.raises((E.G1GeneratorLegality, RG.RouteGate)):
        built(length=length)


def test_gate_l_accepts_the_lengths_this_route_is_documented_at():
    for length in (65, 81):
        wf, meta = built(length=length)
        assert meta["gate_L"]["verdict"] == "PASS"


def test_gate_s_raises_on_a_seed_the_committed_list_does_not_carry():
    with pytest.raises(E.GateSSeedRegistration):
        built(seed=1234)


def test_gate_s_raises_when_a_seed_is_varied_with_no_registry_at_all():
    """An experiment that pre-registered nothing may not vary its seed — the clause that
    stops a `--seed` flag turning every unregistered experiment into a shoppable one."""
    with pytest.raises(E.GateSSeedRegistration):
        built(seed=2026081231, registry=None)


# -------------------------------------------------------------------- Gate ROUTE / L

def test_gate_route_finds_the_latent_without_being_handed_the_frame():
    """The load-bearing half of the LATENT_NODES addition.

    `WanImageToVideo` sizes its own latent, so this graph contains no `Empty*LatentVideo`
    node. Without the table entry Gate L examines zero latents — the exact E08 defect —
    and with `frame=` supplied that stays invisible, because the supplied number passes on
    its own. So this asks the gate the question with nothing supplied.
    """
    wf, _ = built()
    ev = RG.verify(wf)
    assert ev["latents_checkable"] == 1
    assert ev["frame_legality_verdict"] == "PROVEN"
    assert [(f["width"], f["height"], f["length"]) for f in ev["frame_legality"]] \
        == [(832, 480, 65)]


def test_without_the_table_entry_gate_l_goes_indeterminate_and_raises():
    """The companion, reconstructing the pre-fix world. If someone removes the entry as
    'unused', this fails rather than the gate quietly passing on nothing."""
    wf, _ = built()
    saved = RG.LATENT_NODES.pop("WanImageToVideo")
    try:
        with pytest.raises(RG.RouteGate) as exc:
            RG.verify(wf)
        assert "INDETERMINATE" in str(exc.value)
    finally:
        RG.LATENT_NODES["WanImageToVideo"] = saved


def test_gate_route_refuses_a_graph_carrying_the_excluded_speed_lora():
    """The served template at `main` wires exactly this, at strength 1.0, inside a
    subgraph blueprint. The route gate is what stands between that file and a run."""
    wf, _ = built()
    wf["101"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
        "lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
        "strength_model": 1.0, "model": ["12", 0]}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, frame=(832, 480, 65))
    assert "lightx2v" in str(exc.value)


def test_a_supplied_frame_that_disagrees_with_the_graph_raises():
    """Both numbers would be legal, so nothing downstream would notice that the number in
    the report is not the number that ran."""
    wf, _ = built()
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, frame=(832, 480, 81))
    assert "pins" in str(exc.value)


# ---------------------------------------------------------------------------- Gate PIN

def _fake_e08(tmp_path, positive=POS, negative=NEG):
    p = tmp_path / "E08-probe-payload-record.json"
    p.write_text(json.dumps({"experiment": "E08", "seed": 2026081211,
                             "positive": positive, "negative": negative}),
                 encoding="utf-8")
    return str(p)


def test_gate_pin_passes_when_the_strings_are_byte_identical(tmp_path):
    ev = B.pin_against_e08(POS, NEG, _fake_e08(tmp_path))
    assert ev["verdict"].startswith("positive and negative byte-identical")
    assert ev["positive"]["sha256_built"] == ev["positive"]["sha256_e08"]


@pytest.mark.parametrize("field", ["positive", "negative"])
def test_gate_pin_fires_on_a_single_character_of_drift(field):
    """One character. The A/B's whole claim is 'same prompt, different route', and a
    prompt that drifted by a word would make the sheet a comparison of two prompts as
    well — with no symptom anywhere, because both strings encode fine."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        kw = {field: (POS if field == "positive" else NEG) + "."}
        rec = _fake_e08(__import__("pathlib").Path(d), **kw)
        with pytest.raises(B.PayloadError) as exc:
            B.pin_against_e08(POS, NEG, rec)
        assert field in str(exc.value)


def test_gate_pin_fires_when_the_record_carries_no_string_at_all(tmp_path):
    """A missing field must not read as agreement — the failure mode this repo's stale
    labels keep producing."""
    p = tmp_path / "rec.json"
    p.write_text(json.dumps({"experiment": "E08"}), encoding="utf-8")
    with pytest.raises(B.PayloadError):
        B.pin_against_e08(POS, NEG, str(p))


# ------------------------------------------- the citation check, against the banked file

BANKED = os.path.join(REPO, "outputs", "E11", "route",
                      "i2v_template_5d6089c4250f.json")


@pytest.mark.skipif(not os.path.exists(BANKED),
                    reason="the banked template lives under gitignored outputs/")
def test_every_trajectory_value_is_actually_in_the_file_it_cites():
    """E09's citation check, pointed at E11's numbers.

    A source string in a record is a claim about a file. This reads the file. The failure
    it catches is the one that fired in E09 — a seat describing a banked source from
    memory — and the reason it matters here is that these six numbers are the entire
    difference between running the documented trajectory and running an invented one.
    """
    doc = json.load(open(BANKED, encoding="utf-8"))
    by_type = {}
    for n in doc["nodes"]:
        by_type.setdefault(n["type"], []).append(n)

    assert len(by_type["LoraLoaderModelOnly"] if "LoraLoaderModelOnly" in by_type
               else []) == 0, "the cited revision is supposed to carry no LoRA at all"

    samplers = sorted(by_type["KSamplerAdvanced"],
                      key=lambda n: n["widgets_values"][7])          # by start_at_step
    hi, lo = (n["widgets_values"] for n in samplers)
    assert hi[3] == lo[3] == B.TRAJECTORY["steps"]["value"]
    assert hi[4] == lo[4] == B.TRAJECTORY["cfg"]["value"]
    assert hi[5] == lo[5] == B.TRAJECTORY["sampler_name"]["value"]
    assert hi[6] == lo[6] == B.TRAJECTORY["scheduler"]["value"]
    assert hi[8] == lo[7] == B.TRAJECTORY["split_step"]["value"]

    shifts = [n["widgets_values"][0] for n in by_type["ModelSamplingSD3"]]
    assert all(abs(s - B.TRAJECTORY["shift"]["value"]) < 1e-9 for s in shifts), shifts

    assert by_type["CreateVideo"][0]["widgets_values"][0] == B.TRAJECTORY["fps"]["value"]

    unets = sorted(n["widgets_values"][0] for n in by_type["UNETLoader"])
    assert unets == sorted([B.UNET_HIGH, B.UNET_LOW])
    assert by_type["CLIPLoader"][0]["widgets_values"][0] == B.CLIP_NAME
    assert by_type["VAELoader"][0]["widgets_values"][0] == B.VAE_NAME


@pytest.mark.skipif(not os.path.exists(BANKED),
                    reason="the banked template lives under gitignored outputs/")
def test_the_cited_revision_leaves_clip_vision_unconnected_too():
    doc = json.load(open(BANKED, encoding="utf-8"))
    node = next(n for n in doc["nodes"] if n["type"] == "WanImageToVideo")
    slot = next(i for i in node["inputs"] if i["name"] == "clip_vision_output")
    assert slot["link"] is None
    start = next(i for i in node["inputs"] if i["name"] == "start_image")
    assert start["link"] is not None
