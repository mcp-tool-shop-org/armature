"""E09 B2's graph, checked before a credit is spent on it.

The fixtures ask CLAUDE.md's question of each check: what would this look like if the code
were wrong in the specific way it exists to catch? The two that carry the most weight are
the derived expert split — a two-expert model run as one and a half produces a plausible
clip and no error — and the LoRA clause, because the graph this replaces wired the licence
map's excluded trajectory at strength 1.0 and looked perfectly ordinary doing it.
"""

import json
import os

import pytest

from conftest import TOOLS, REPO  # noqa: F401
import build_t2v_payload as B
from armature_core import route_gates as RG


SEEDS = json.load(open(os.path.join(REPO, "specs", "E09-seeds.json"), encoding="utf-8"))


def test_the_reference_values_are_the_ones_fetched_from_wan22():
    """A guard against drift in the numbers this experiment is quoted against. If someone
    edits a value without re-fetching, this fails and names it."""
    assert B.REFERENCE["sample_steps"]["value"] == 40
    assert B.REFERENCE["sample_shift"]["value"] == 12.0
    assert B.REFERENCE["boundary"]["value"] == 0.875
    assert B.REFERENCE["guide_scale_low_noise"]["value"] == 3.0
    assert B.REFERENCE["guide_scale_high_noise"]["value"] == 4.0
    assert B.REFERENCE["num_train_timesteps"]["value"] == 1000
    for key, rec in B.REFERENCE.items():
        assert rec["source"], key


def test_every_reference_value_names_where_it_came_from():
    """Including the two that came from neither the Wan reference nor the template — they
    must SAY so rather than sit in the table looking like defaults."""
    for key in ("sampler_name", "scheduler"):
        src = B.REFERENCE[key]["source"]
        assert "NOT from the Wan reference" in src or "port necessity" in src, key


def test_the_expert_split_is_derived_and_lands_where_the_boundary_says():
    """The reference switches experts on the timestep; ComfyUI splits on a step index. A
    split that is off by a few steps runs part of the trajectory on the wrong expert and
    produces a clip that looks like a bad prompt."""
    split, table = B.boundary_step(40, 12.0, 0.875)
    assert split == 26
    # Every step before the split is above the boundary, every step after is below —
    # which is the property, not the number.
    for row in table[:split]:
        assert row["expert"] == "high" and row["sigma_shifted"] >= 0.875
    for row in table[split:]:
        assert row["expert"] == "low" and row["sigma_shifted"] < 0.875


def test_the_split_covers_every_step_with_no_gap_and_no_overlap():
    graph, split = B.build_graph(SEEDS["seeds"][0], profile="derived")
    hi, lo = graph["50"]["inputs"], graph["51"]["inputs"]
    assert hi["start_at_step"] == 0
    assert hi["end_at_step"] == lo["start_at_step"] == split["split_step"]
    assert lo["end_at_step"] >= hi["steps"]
    assert hi["steps"] == lo["steps"] == B.REFERENCE["sample_steps"]["value"]


def test_the_shift_formula_is_the_flow_shift():
    """Spot values, so a sign slip or an inverted formula cannot pass."""
    assert B.shifted_sigma(1.0, 12.0) == pytest.approx(1.0)
    assert B.shifted_sigma(0.0, 12.0) == pytest.approx(0.0)
    # the boundary solve, by hand: 12s/(1+11s) = 0.875 -> s = 0.875/2.375
    s = 0.875 / 2.375
    assert B.shifted_sigma(s, 12.0) == pytest.approx(0.875)


def test_a_degenerate_split_raises_rather_than_running_one_expert():
    with pytest.raises(RG.RouteGate):
        B.boundary_step(40, 12.0, 0.0)      # low-noise expert would never run
    with pytest.raises(RG.RouteGate):
        B.boundary_step(40, 12.0, 1.01)     # high-noise expert would never run


def test_the_graph_loads_no_lora_of_any_kind():
    """The clause the served template failed. Not 'no excluded LoRA' — no LoRA."""
    graph, _ = B.build_graph(SEEDS["seeds"][0], profile="derived")
    for node in graph.values():
        assert "lora" not in node["class_type"].lower(), node
        for v in node["inputs"].values():
            if isinstance(v, str):
                assert "lora" not in v.lower(), v


def test_the_graph_loads_only_weights_the_map_covers():
    graph, _ = B.build_graph(SEEDS["seeds"][0], profile="derived")
    files = {c["file"] for c in RG.components(graph)}
    assert files == {B.UNET_HIGH, B.UNET_LOW, B.CLIP_NAME, B.VAE_NAME}


def test_the_frame_is_the_one_the_spec_asks_for_and_is_legal():
    graph, _ = B.build_graph(SEEDS["seeds"][0], profile="derived")
    lat = graph["40"]["inputs"]
    assert (lat["width"], lat["height"], lat["length"]) == (832, 480, 65)
    assert RG.frame_legality(832, 480, 65)["legal"] is True


def test_the_registered_seed_is_the_one_that_adds_noise():
    """And the inert one is inert — a two-expert split where BOTH samplers add noise would
    re-noise the latent halfway through and the defect would read as model incoherence."""
    graph, _ = B.build_graph(SEEDS["seeds"][0], profile="derived")
    assert graph["50"]["inputs"]["add_noise"] == "enable"
    assert graph["50"]["inputs"]["noise_seed"] == SEEDS["seeds"][0]
    assert graph["51"]["inputs"]["add_noise"] == "disable"


def test_all_three_admission_gates_pass_on_the_built_graph():
    graph, _ = B.build_graph(SEEDS["seeds"][0], profile="derived")
    RG.verify(graph)
    RG.gate_s_registration(graph, SEEDS["seeds"])
    assert RG.frame_legality(B.WIDTH, B.HEIGHT, B.LENGTH)["legal"]


def test_an_unregistered_seed_is_refused_by_the_admission_path():
    graph, _ = B.build_graph(123456789, profile="derived")
    with pytest.raises(RG.RouteGate):
        RG.gate_s_registration(graph, SEEDS["seeds"])


def test_the_lossless_tap_is_wired_off_the_decode():
    """The review is at 0.5x from lossless, and a compressed clip cannot be un-compressed
    later. The PNG save must hang off the VAE decode, not off the video encoder."""
    graph, _ = B.build_graph(SEEDS["seeds"][0], profile="derived")
    save_image = [n for n in graph.values() if n["class_type"] == "SaveImage"]
    assert len(save_image) == 1
    assert save_image[0]["inputs"]["images"] == ["60", 0]
    assert graph["60"]["class_type"] == "VAEDecode"


def test_the_prompt_carries_the_bounds_the_findings_named():
    """B1's H2c missed by predicting the blank face would detect weakly; the measurement
    said the weak landmarks were the occluded far-side arm. The staging has to answer that
    finding, and the model card's own in-scope bounds."""
    p = B.PROBE_PROMPT.lower()
    assert "single dancer" in p or "one person" in p
    assert "head to feet" in p or "whole body" in p
    assert "clear of her torso" in p or "never cross" in p
    assert "camera does not move" in p


def test_every_link_points_at_a_node_that_exists():
    """Link integrity in code. `dry_run` checks this too, and CLAUDE.md's law is that a
    dry_run PASS does not prove link sanity — so it is checked here as well, on the object
    we actually wrote."""
    graph, _ = B.build_graph(SEEDS["seeds"][0], profile="derived")
    for node_id, node in graph.items():
        for name, v in node["inputs"].items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                assert v[0] in graph, f"{node_id}.{name} -> missing node {v[0]}"


def test_no_node_is_orphaned_from_the_two_outputs():
    """A node wired to nothing is a node that does not run, and a graph can carry one while
    every other check passes. Walk back from both save nodes and require full coverage."""
    graph, _ = B.build_graph(SEEDS["seeds"][0], profile="derived")
    seen, stack = set(), ["70", "81"]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        for v in graph[nid]["inputs"].values():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                stack.append(v[0])
    assert seen == set(graph), sorted(set(graph) - seen)
