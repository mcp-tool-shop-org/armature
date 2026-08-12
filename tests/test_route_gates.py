"""The route gate, against graphs built to be wrong in the specific ways it exists to catch.

Every fixture below is a graph that a name-level or top-level check would call clean.
"""

import pytest

from conftest import TOOLS  # noqa: F401
from armature_core import route_gates as RG


def graph(top=(), sub=()):
    """A save-format graph with an optional subgraph definition."""
    return {
        "nodes": list(top),
        "definitions": {"subgraphs": [{"id": "sg-1", "name": "Text to Video(Wan2.2)",
                                       "nodes": list(sub)}]} if sub else {},
    }


def sampler(node_id, seed, control, cls="KSamplerAdvanced"):
    wv = ([ "enable", seed, control, 4, 1, "euler", "simple", 0, 2, "enable"]
          if cls == "KSamplerAdvanced" else [seed, control, 20, 7.0, "euler", "normal", 1.0])
    return {"id": node_id, "type": cls, "widgets_values": wv}


def latent(node_id, w, h, length):
    return {"id": node_id, "type": "EmptyHunyuanLatentVideo",
            "widgets_values": [w, h, length, 1]}


def loader(node_id, filename, cls="UNETLoader"):
    return {"id": node_id, "type": cls, "widgets_values": [filename, "default"]}


CLEAN_TOP = [loader(1, "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"),
             sampler(2, 12345, "fixed"), latent(3, 832, 480, 65)]


def test_a_clean_graph_passes():
    ev = RG.verify(graph(top=CLEAN_TOP))
    assert ev["frame_legality"][0]["legal"] is True
    assert len(ev["components"]) == 1


def test_it_walks_into_subgraph_definitions():
    """THE clause. The served Wan 2.2 template shows four nodes at the top level and hides
    thirty inside a subgraph blueprint; a walker that stopped at the top would report a
    clean graph with an excluded LoRA two levels down."""
    g = graph(top=[latent(3, 832, 480, 65), sampler(2, 1, "fixed")],
              sub=[loader(83, "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors",
                          cls="LoraLoaderModelOnly")])
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "lightx2v" in str(exc.value)
    hidden = [c for c in exc.value.evidence["components"] if c["where"] != "top"]
    assert hidden and hidden[0]["ruling"]["verdict"] == "EXCLUDED"


def test_a_randomising_seed_refuses_gate_s():
    """A seed that randomises is a seed no committed list pre-registered."""
    g = graph(top=[latent(3, 832, 480, 65), sampler(2, 999, "randomize")])
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "Gate S" in str(exc.value)
    assert exc.value.evidence["seeds"][0]["pinned"] is False


def test_a_banned_component_is_caught_even_when_it_looks_incidental():
    g = graph(top=CLEAN_TOP + [loader(9, "Wan21_CausVid_14B_T2V_lora_rank32.safetensors",
                                      cls="LoraLoaderModelOnly")])
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "BANNED" in str(exc.value)


def test_an_unruled_component_is_reported_not_silently_cleared():
    """The dangerous default. A file nobody has ruled on must read as UNKNOWN in the
    evidence rather than pass as clean because it matched nothing."""
    g = graph(top=[loader(1, "some_new_model_nobody_fetched.safetensors"),
                   sampler(2, 1, "fixed"), latent(3, 832, 480, 65)])
    ev = RG.verify(g)
    assert ev["components"][0]["ruling"]["verdict"] == "NOT IN THIS TABLE"


def test_allow_still_reports_what_it_allowed():
    """`allow` is not a skip flag: a component let through still appears in the evidence
    with its verdict, so a report cannot omit that it ran."""
    g = graph(top=CLEAN_TOP,
              sub=[loader(83, "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors",
                          cls="LoraLoaderModelOnly")])
    ev = RG.verify(g, allow=("lightx2v",))
    named = [c for c in ev["components"] if "lightx2v" in c["file"]]
    assert named and named[0]["ruling"]["verdict"] == "EXCLUDED"


@pytest.mark.parametrize("w,h,n,legal", [
    (832, 480, 65, True),
    (832, 480, 81, True),
    (640, 640, 81, True),
    (833, 480, 65, False),      # width off the 16 grid
    (832, 484, 65, False),      # height off the 16 grid
    (832, 480, 64, False),      # not 4n+1
    (832, 480, 85, False),      # past the trained horizon
])
def test_frame_legality_derive_then_round(w, h, n, legal):
    res = RG.frame_legality(w, h, n)
    assert res["legal"] is legal, res["problems"]
    if not legal:
        assert res["problems"] and any("nearest" in p or "horizon" in p
                                       for p in res["problems"])


def test_an_illegal_frame_stops_the_route():
    g = graph(top=[loader(1, "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"),
                   sampler(2, 1, "fixed"), latent(3, 832, 480, 64)])
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "Gate L" in str(exc.value)


def test_an_unknown_generator_family_raises_rather_than_assuming_wan():
    with pytest.raises(RG.RouteGate):
        RG.frame_legality(832, 480, 65, family="a-model-nobody-recorded")


# ------------------------------------------------------------------ API format

def api_graph(seed=4242, w=832, h=480, n=65, extra=None):
    """The shape we hand the cloud: node-id keyed, class_type + inputs, links as [id, slot]."""
    g = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "EmptyHunyuanLatentVideo",
              "inputs": {"width": w, "height": h, "length": n, "batch_size": 1}},
        "3": {"class_type": "KSamplerAdvanced",
              "inputs": {"add_noise": "enable", "noise_seed": seed, "steps": 40,
                         "cfg": 4.0, "sampler_name": "euler", "scheduler": "simple",
                         "start_at_step": 0, "end_at_step": 25,
                         "return_with_leftover_noise": "enable",
                         "model": ["1", 0], "positive": ["9", 0], "negative": ["9", 0],
                         "latent_image": ["2", 0]}},
        "4": {"class_type": "KSamplerAdvanced",
              "inputs": {"add_noise": "disable", "noise_seed": 0, "steps": 40,
                         "cfg": 3.0, "sampler_name": "euler", "scheduler": "simple",
                         "start_at_step": 25, "end_at_step": 10000,
                         "return_with_leftover_noise": "disable",
                         "model": ["1", 0], "positive": ["9", 0], "negative": ["9", 0],
                         "latent_image": ["3", 0]}},
    }
    if extra:
        g.update(extra)
    return g


def test_api_format_is_detected_and_walked():
    g = api_graph()
    assert RG.is_api_format(g) is True
    ev = RG.verify(g)
    assert [l["length"] for l in ev["latents"]] == [65]
    assert ev["frame_legality"][0]["legal"] is True
    assert {c["file"] for c in ev["components"]} == {
        "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}


def test_save_format_is_still_detected():
    assert RG.is_api_format(graph(top=CLEAN_TOP)) is False


def test_an_api_seed_arriving_over_a_link_is_not_pinned():
    """API format has no `control_after_generate` widget, so the failure looks different:
    a seed fed from another node could compute anything, and the run would not be the run
    the committed list registered."""
    g = api_graph()
    g["3"]["inputs"]["noise_seed"] = ["7", 0]
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "Gate S" in str(exc.value)


def test_an_excluded_lora_in_an_api_graph_is_caught_too():
    g = api_graph(extra={"9": {"class_type": "LoraLoaderModelOnly", "inputs": {
        "lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors",
        "strength_model": 1.0, "model": ["1", 0]}}})
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "lightx2v" in str(exc.value)


# ------------------------------------------------------------------ Gate S

def test_gate_s_passes_when_the_live_seed_is_registered():
    ev = RG.gate_s_registration(api_graph(seed=4242), [4242, 8484])
    live = [s for s in ev["seeds"] if s["adds_noise"]]
    assert len(live) == 1 and live[0]["seed"] == 4242


def test_gate_s_refuses_an_unregistered_seed():
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(api_graph(seed=999), [4242])
    assert "does not pre-register" in str(exc.value)


def test_gate_s_refuses_an_empty_registration():
    """An experiment that pre-registered nothing may not vary its seed at all."""
    with pytest.raises(RG.RouteGate):
        RG.gate_s_registration(api_graph(), [])


def test_gate_s_ignores_the_inert_seed_of_a_no_noise_sampler():
    """The second expert runs add_noise=disable, so its seed draws no noise. Demanding it
    be registered too would be a check that fires on a correct two-expert split."""
    ev = RG.gate_s_registration(api_graph(seed=4242), [4242])
    inert = [s for s in ev["seeds"] if not s["adds_noise"]]
    assert len(inert) == 1 and inert[0]["seed"] == 0


def test_gate_s_still_refuses_a_randomising_save_format_seed():
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(
            graph(top=[latent(3, 832, 480, 65), sampler(2, 4242, "randomize")]), [4242])
    assert "not pinned" in str(exc.value)


def test_the_gate_is_not_an_assert():
    import os
    src = open(os.path.join(TOOLS, "armature_core", "route_gates.py"),
               encoding="utf-8").read()
    for line in src.splitlines():
        assert not line.strip().startswith("assert "), line


# ------------------------------------------------------------------ E08, 2026-08-12
#
# A conditioning node that sizes its own latent disarms Gate L unless it is in the table.
# `WanAnimateToVideo` emits the latent itself, so an Animate graph carries no
# `Empty*LatentVideo` node — and the first E08 graph passed Gate L having examined zero
# latents. These fixtures fail if that regresses.

def _animate_api(width=832, height=480, length=65):
    return {
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.2_animate_14B_bf16.safetensors",
                          "weight_dtype": "default"}},
        "49": {"class_type": "WanAnimateToVideo",
               "inputs": {"width": width, "height": height, "length": length,
                          "batch_size": 1, "continue_motion_max_frames": 5,
                          "video_frame_offset": 0,
                          "positive": ["6", 0], "negative": ["7", 0], "vae": ["105", 0]}},
        "3": {"class_type": "KSampler",
              "inputs": {"seed": 2026081201, "steps": 20, "cfg": 6.0,
                         "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0,
                         "model": ["10", 0], "positive": ["49", 0], "negative": ["49", 1],
                         "latent_image": ["49", 2]}},
    }


def test_wan_animate_latent_is_seen_at_all():
    """The regression this exists for: an Animate graph has no Empty*LatentVideo node, so
    an empty result here means Gate L examined nothing and said the graph was legal."""
    lat = RG.latents(_animate_api())
    assert len(lat) == 1
    assert lat[0]["class"] == "WanAnimateToVideo"
    assert (lat[0]["width"], lat[0]["height"], lat[0]["length"]) == (832, 480, 65)


def test_wan_animate_illegal_frame_raises_rather_than_passing_vacuously():
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_animate_api(length=64))
    assert "4n+1" in str(exc.value)


def test_wan_animate_illegal_width_raises():
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_animate_api(width=833))
    assert "multiple of 16" in str(exc.value)


def test_wan_animate_over_the_trained_horizon_raises():
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_animate_api(length=85))
    assert "81-frame" in str(exc.value)


def test_the_shot_shape_is_legal_and_the_verdict_counts_the_latent():
    ev = RG.verify(_animate_api())
    assert ev["frame_legality"][0]["legal"] is True
    assert "1 latent(s) all generator-legal" in ev["verdict"]


def test_wan_animate_latent_is_read_in_save_format_too():
    """The saved file is what the cloud receives, and its widgets are positional."""
    save = {"nodes": [{"id": 49, "type": "WanAnimateToVideo",
                       "widgets_values": [832, 480, 65, 1, 5, 0]}]}
    lat = RG.latents(save)
    assert (lat[0]["width"], lat[0]["height"], lat[0]["length"]) == (832, 480, 65)
