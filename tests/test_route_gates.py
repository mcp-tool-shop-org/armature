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


def test_gate_s_reads_a_save_format_sampler_that_has_connected_inputs():
    """Measured at use, E10 2026-08-12: save format spells `inputs` as a LIST of slot
    dicts and API format as a mapping, and the noise check called `.get` on it. E09's
    saved samplers had EMPTY input arrays, so `or {}` swallowed the difference and the
    defect waited for a graph whose sampler was actually wired — which every real one is."""
    saved = {"nodes": [
        {"id": 49, "type": "WanAnimateToVideo", "widgets_values": [832, 480, 81, 1, 5, 0]},
        {"id": 3, "type": "KSampler",
         "inputs": [{"name": "model", "type": "MODEL", "link": 1},
                    {"name": "latent_image", "type": "LATENT", "link": 4}],
         "widgets_values": [2026081221, "fixed", 20, 6, "uni_pc", "simple", 1]}]}
    ev = RG.gate_s_registration(saved, [2026081221])
    live = [s for s in ev["seeds"] if s["adds_noise"]]
    assert len(live) == 1 and live[0]["seed"] == 2026081221


def test_a_plain_KSampler_is_never_read_as_noise_free():
    """`KSampler` has no `add_noise` input at all. Reading widget 0 for it — which the
    table used to invite — asks whether its SEED equals "disable"."""
    saved = {"nodes": [{"id": 3, "type": "KSampler", "inputs": [],
                        "widgets_values": ["disable", "fixed", 20, 6, "euler", "simple", 1]}]}
    assert RG.seeds(saved)[0]["seed"] == "disable"
    ev = RG.gate_s_registration(saved, ["disable"])
    assert ev["seeds"][0]["adds_noise"] is True


def test_a_save_format_advanced_sampler_with_noise_disabled_is_still_read_as_inert():
    saved = {"nodes": [
        {"id": 4, "type": "KSamplerAdvanced",
         "inputs": [{"name": "model", "type": "MODEL", "link": 1}],
         "widgets_values": ["disable", 0, "fixed", 40, 3.0, "euler", "simple", 25, 10000,
                            "disable"]},
        {"id": 3, "type": "KSamplerAdvanced",
         "inputs": [{"name": "model", "type": "MODEL", "link": 1}],
         "widgets_values": ["enable", 4242, "fixed", 40, 4.0, "euler", "simple", 0, 25,
                            "enable"]}]}
    ev = RG.gate_s_registration(saved, [4242])
    assert sorted(s["adds_noise"] for s in ev["seeds"]) == [False, True]


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
    assert ev["frame_legality_verdict"] == "PROVEN"
    assert "1 of 1 latent(s) checkable" in ev["verdict"]


def test_wan_animate_latent_is_read_in_save_format_too():
    """The saved file is what the cloud receives, and its widgets are positional."""
    save = {"nodes": [{"id": 49, "type": "WanAnimateToVideo",
                       "widgets_values": [832, 480, 65, 1, 5, 0]}]}
    lat = RG.latents(save)
    assert (lat[0]["width"], lat[0]["height"], lat[0]["length"]) == (832, 480, 65)
    assert lat[0]["checkable"] is True


# ------------------------------------------------- E08's commission, shipped E10 2026-08-12
#
# Adding `WanAnimateToVideo` to the table fixed one graph. The SHAPE of the failure —
# "nothing was checkable" reported as "everything checked out" — needed the gate to stop
# treating an empty examination as a pass. These fixtures are that clause.

def _unrecorded_latent_api():
    """A graph whose latent is sized by a node nobody has put in the table yet.

    This is not hypothetical: it is exactly the state the first E08 Animate graph was in,
    and the state the NEXT unrecorded conditioning node will put a graph in.
    """
    return {
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.2_animate_14B_bf16.safetensors",
                          "weight_dtype": "default"}},
        "49": {"class_type": "SomeFutureConditioningNodeThatSizesItsOwnLatent",
               "inputs": {"width": 832, "height": 480, "length": 999, "vae": ["105", 0]}},
        "3": {"class_type": "KSampler",
              "inputs": {"seed": 2026081211, "steps": 20, "cfg": 6.0,
                         "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0,
                         "model": ["10", 0], "latent_image": ["49", 2]}},
    }


def test_a_graph_with_no_checkable_latent_and_no_supplied_frame_goes_RED():
    """THE red test. Before this clause, this graph passed Gate L having checked nothing."""
    g = _unrecorded_latent_api()
    assert RG.latents(g) == []
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "INDETERMINATE" in str(exc.value)
    assert exc.value.evidence["frame_legality_verdict"] == "INDETERMINATE"
    assert exc.value.evidence["frame_legality"] == []


def test_the_same_graph_is_admitted_when_the_builder_states_the_frame():
    """`frame` is not a skip flag: the supplied numbers are checked like any others and
    are labelled `supplied` in the evidence, so a report cannot pretend the graph proved
    them."""
    ev = RG.verify(_unrecorded_latent_api(), frame=(832, 480, 81))
    assert ev["frame_legality_verdict"] == "PROVEN"
    assert [f["source"] for f in ev["frame_legality"]] == ["supplied"]
    assert ev["latents_checkable"] == 0


def test_a_supplied_frame_that_is_illegal_still_raises():
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_unrecorded_latent_api(), frame=(832, 480, 82))
    assert "4n+1" in str(exc.value)


def test_a_supplied_frame_contradicting_the_graphs_own_latent_raises():
    """Both numbers legal, one of them wrong. Nothing downstream compares them."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_animate_api(length=65), frame=(832, 480, 81))
    assert "not the number that runs" in str(exc.value)
    assert exc.value.evidence["frame_legality_verdict"] == "CONTRADICTED"


def test_a_latent_whose_dimensions_arrive_over_links_is_not_checkable():
    """A `None` is not a small frame — it is no answer, and it must not read as one."""
    g = _animate_api()
    g["49"]["inputs"]["length"] = ["77", 0]
    lat = RG.latents(g)
    assert lat[0]["checkable"] is False and lat[0]["length"] is None
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "INDETERMINATE" in str(exc.value)


def test_a_supplied_frame_must_carry_all_three_numbers():
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_unrecorded_latent_api(), frame={"width": 832, "height": 480})
    assert "two out of three proves nothing" in str(exc.value)


def test_the_e08_shot_would_have_gone_red_under_this_clause():
    """The historical case, reconstructed: the table WITHOUT `WanAnimateToVideo`.

    The point of the fixture is that the fix does not depend on the table being complete.
    """
    table = dict(RG.LATENT_NODES)
    table.pop("WanAnimateToVideo")
    saved = RG.LATENT_NODES
    try:
        RG.LATENT_NODES = table
        with pytest.raises(RG.RouteGate) as exc:
            RG.verify(_animate_api(length=65))
        assert "INDETERMINATE" in str(exc.value)
    finally:
        RG.LATENT_NODES = saved


# ---------------------------------------------------------------------------------------
# The camera tier (E11 wave 2). Every fixture below is a graph that Gate L, Gate S and the
# licence clause all pass, because the defect being caught is invisible to all three.

def _camera_api(length=65, cam_length=None, cam_wh=(832, 480)):
    """The wave-2 shape: an embedding feeding a camera conditioning node feeding a sampler."""
    return {
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
                          "weight_dtype": "default"}},
        "45": {"class_type": "WanCameraEmbedding", "inputs": {
            "camera_pose": "Static", "width": cam_wh[0], "height": cam_wh[1],
            "length": length if cam_length is None else cam_length, "speed": 1.0}},
        "50": {"class_type": "WanCameraImageToVideo", "inputs": {
            "width": 832, "height": 480, "length": length, "batch_size": 1,
            "positive": ["30", 0], "negative": ["31", 0], "vae": ["21", 0],
            "start_image": ["40", 0], "camera_conditions": ["45", 0]}},
        "60": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "enable", "noise_seed": 2026081232, "steps": 20, "cfg": 3.5,
            "sampler_name": "euler", "scheduler": "simple", "start_at_step": 0,
            "end_at_step": 10, "return_with_leftover_noise": "enable",
            "latent_image": ["50", 2]}},
    }


def test_the_camera_conditioning_node_sizes_its_own_latent():
    """Without its `LATENT_NODES` row Gate L would examine zero frames on this graph and,
    with a frame supplied, still report PROVEN — the E08 shape, one route later."""
    lat = RG.latents(_camera_api())
    assert [l["class"] for l in lat] == ["WanCameraImageToVideo"]
    assert (lat[0]["width"], lat[0]["height"], lat[0]["length"]) == (832, 480, 65)
    assert lat[0]["checkable"] is True


def test_an_illegal_frame_on_the_camera_route_is_caught_from_the_graph_alone():
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_camera_api(length=64))
    assert "4n+1" in str(exc.value)


def test_the_camera_trajectory_must_be_solved_for_the_generated_frame():
    """THE clause this tier exists for. The node's own default length is 81 and this route
    runs 65, so a forgotten argument produces exactly this graph: 65 frames of a camera path
    solved for 81. Gate L passes it, Gate S passes it, the licence clause passes it."""
    g = _camera_api(length=65, cam_length=81)
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 65))
    assert "solved for a different frame" in str(exc.value)
    assert exc.value.evidence["camera_agreement_verdict"] == "CONTRADICTED"
    # and every other clause was clean on it
    assert all(f["legal"] for f in exc.value.evidence["frame_legality"])
    assert all(s["pinned"] for s in exc.value.evidence["seeds"])


def test_a_camera_aspect_that_disagrees_is_caught_too():
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_camera_api(cam_wh=(1280, 720)), frame=(832, 480, 65))
    assert exc.value.evidence["camera_agreement_verdict"] == "CONTRADICTED"


def test_an_agreeing_camera_passes_and_is_reported():
    ev = RG.verify(_camera_api(), frame=(832, 480, 65))
    assert ev["camera_agreement_verdict"] == "AGREES"
    assert [c["class"] for c in ev["cameras"]] == ["WanCameraEmbedding"]


def test_the_camera_node_does_not_inflate_the_count_of_frames_checked():
    """A trajectory node sizes no frame. If it were counted as one, Gate L's
    'nothing was checkable' andon could be satisfied by a node that checks nothing."""
    ev = RG.verify(_camera_api(), frame=(832, 480, 65))
    assert [l["class"] for l in ev["latents"]] == ["WanCameraImageToVideo"]
    assert ev["latents_checkable"] == 1
    assert {f["source"] for f in ev["frame_legality"]} == {"graph", "supplied"}


def test_a_camera_length_arriving_over_a_link_is_unproven_not_assumed():
    g = _camera_api()
    g["45"]["inputs"]["length"] = ["99", 0]
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 65))
    assert "UNPROVEN" in str(exc.value)
    assert exc.value.evidence["camera_agreement_verdict"] == "INDETERMINATE"


def test_a_camera_with_nothing_to_check_against_halts_rather_than_passing():
    """Two disagreeing graph frames and no supplied one: there is no single answer to
    compare the trajectory against, and 'no answer' must not read as agreement."""
    g = _camera_api()
    g["51"] = {"class_type": "EmptyLatentVideo",
               "inputs": {"width": 832, "height": 480, "length": 33}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert exc.value.evidence["camera_agreement_verdict"] == "INDETERMINATE"


def test_camera_widget_order_is_confirmed_empirically_on_save_format():
    """`CAMERA_NODES` was derived from ONE source. This is the second reading."""
    g = graph(top=[{"id": 45, "type": "WanCameraEmbedding",
                    "widgets_values": ["Static", 832, 480, 65, 1.0, 0.5, 0.5, 0.5, 0.5]}])
    ev = RG.camera_widget_order_evidence(g, {"width": 832, "height": 480, "length": 65})
    assert ev["agrees"] is True
    assert ev["nodes"][0]["found"] == {"width": 832, "height": 480, "length": 65}


def test_camera_widget_order_evidence_catches_a_shifted_index():
    """If the declared indices were off by one — the failure a single-source derivation
    invites — the values found would not be the builder's."""
    g = graph(top=[{"id": 45, "type": "WanCameraEmbedding",
                    "widgets_values": [832, 480, 65, 1.0]}])  # camera_pose omitted
    ev = RG.camera_widget_order_evidence(g, {"width": 832, "height": 480, "length": 65})
    assert ev["agrees"] is False
    assert ev["verdict"].startswith("CONTRADICTED")


def test_camera_widget_order_evidence_is_honest_about_api_format():
    """There is nothing positional to confirm in API format, and the honest verdict for a
    check that cannot run is not PASS."""
    ev = RG.camera_widget_order_evidence(_camera_api(),
                                         {"width": 832, "height": 480, "length": 65})
    assert ev["verdict"].startswith("not_applicable")
    assert "agrees" not in ev
