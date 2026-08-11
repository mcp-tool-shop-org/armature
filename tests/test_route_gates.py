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


def test_the_gate_is_not_an_assert():
    import os
    src = open(os.path.join(TOOLS, "armature_core", "route_gates.py"),
               encoding="utf-8").read()
    for line in src.splitlines():
        assert not line.strip().startswith("assert "), line
