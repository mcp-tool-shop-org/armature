"""The route gate, against graphs built to be wrong in the specific ways it exists to catch.

Every fixture below is a graph that a name-level or top-level check would call clean.
"""

import pytest

from conftest import TOOLS  # noqa: F401
from armature_core import canon
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
    with pytest.raises(RG.RouteGate,
                       match=r"\[ROUTE\] no recorded frame rules for generator family"):
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
    with pytest.raises(RG.RouteGate,
                       match=r"\[ROUTE\] Gate S: no seed list was pre-registered, so no"):
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
    """A camera graph with the CORRECT pairing: the embedding, the camera conditioning node,
    and the camera-trained experts that can receive it.

    ⚠ These loaders said `wan2.2_i2v_*` until 2026-08-12, when Gate PAIR went red on seven
    tests in this file at once. That was the gate working: the helper had encoded wave 2's
    defect — a camera node over the plain I2V base — into every fixture built on it, so the
    clauses below were quietly being checked on a graph that could only produce noise. The
    wrong pairing now lives in exactly one place, `tests/fixtures/E11-w2-camera-i2v.api.json`,
    where it is the subject of a test rather than the substrate of one.
    """
    return {
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name":
                          "wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors",
                          "weight_dtype": "default"}},
        "11": {"class_type": "UNETLoader",
               "inputs": {"unet_name":
                          "wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors",
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


# =======================================================================================
# GATE PAIR (E11 w2 ruling R3). The first two tests are the ones that matter: the gate runs
# on the REAL graphs, banked under tests/fixtures/ because outputs/ is gitignored and a red
# test against a file nobody can check out is not a test.

import json  # noqa: E402
import os  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


def test_gate_pair_goes_RED_on_the_exact_wave_2_graph():
    """THE red test. This is the graph that ran on 2026-08-12, byte for byte, and produced
    65 frames with no subject after the first. Every other clause in route_gates passed on
    it — so this test also asserts that, because a gate that only goes red where the others
    already did would not have saved the generation."""
    g = fixture("E11-w2-camera-i2v.api.json")

    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(g)
    ev = exc.value.evidence
    assert ev["verdict"] == "CONTRADICTED"
    assert "WanCameraImageToVideo" in str(exc.value)
    assert "'fun_camera'" in str(exc.value)
    assert ev["families_present"] == ["i2v"]
    assert sorted(w["file"] for w in ev["model_weights"]) == [
        "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"]

    # and the whole gate now refuses the graph, where before it admitted it
    with pytest.raises(RG.PairGate, match=r"\[PAIR\] node 50 is WanCameraImageToVideo, which requires a"):
        RG.verify(g, frame=(832, 480, 65))


def test_every_other_clause_still_passes_on_the_wave_2_graph():
    """The measurement that makes the gate necessary rather than redundant: licence, seeds,
    latents, frame legality and the camera/frame agreement were all green on the graph that
    could only produce noise."""
    g = fixture("E11-w2-camera-i2v.api.json")
    assert [c for c in RG.components(g)
            if c["ruling"]["verdict"] in ("BANNED", "EXCLUDED")] == []
    assert all(s["pinned"] for s in RG.seeds(g))
    lat = RG.latents(g)
    assert len(lat) == 1 and lat[0]["checkable"] is True
    assert RG.frame_legality(832, 480, 65)["legal"] is True
    cams = RG.cameras(g)
    assert len(cams) == 1
    assert (cams[0]["width"], cams[0]["height"], cams[0]["length"]) == (832, 480, 65)


def test_gate_pair_is_GREEN_on_the_wave_1_graph():
    """Wave 1 wired WanImageToVideo over the I2V experts — the pairing that ran clean."""
    g = fixture("E11-w1-probe-i2v.api.json")
    ev = RG.pairing(g)
    assert ev["families_present"] == ["i2v"]
    assert ev["conditioning_nodes"] == [
        {"node_id": "50", "class": "WanImageToVideo", "requires": "i2v"}]
    assert "1 conditioning node(s) paired" in ev["verdict"]
    RG.verify(g, frame=(832, 480, 65))       # the whole gate still admits it


def test_gate_pair_is_GREEN_on_the_corrected_pairing():
    """What wave 3 must look like: the same conditioning class over the camera experts."""
    g = _camera_api()
    g["10"]["inputs"]["unet_name"] = "wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors"
    g["11"] = {"class_type": "UNETLoader", "inputs": {
        "unet_name": "wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors"}}
    ev = RG.pairing(g)
    assert ev["families_present"] == ["fun_camera"]
    assert ev["verdict"].startswith("1 conditioning node(s) paired")


@pytest.mark.parametrize("cls,fam,good", [
    ("WanAnimateToVideo", "animate", "wan2.2_animate_14B_bf16.safetensors"),
    ("WanVaceToVideo", "vace", "Wan2.1-VACE-14B_fp8.safetensors"),
    ("WanImageToVideo", "i2v", "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"),
])
def test_each_mapped_class_pairs_with_its_own_family_and_refuses_the_others(cls, fam, good):
    base = {"10": {"class_type": "UNETLoader", "inputs": {"unet_name": good}},
            "50": {"class_type": cls, "inputs": {}}}
    assert RG.pairing(base)["families_present"] == [fam]
    wrong = dict(base)
    wrong["10"] = {"class_type": "UNETLoader",
                   "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}}
    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(wrong)
    assert exc.value.evidence["verdict"] == "CONTRADICTED"


def test_a_conditioning_class_in_neither_table_halts():
    """Fail-closed, the pattern that stopped this wave twice in gate_saved_graph."""
    g = {"10": {"class_type": "UNETLoader",
                "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"}},
         "50": {"class_type": "WanSomethingNewToVideo", "inputs": {}}}
    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(g)
    assert "neither" in str(exc.value)
    assert exc.value.evidence["verdict"] == "INDETERMINATE"


def test_a_graph_with_conditioning_and_no_readable_model_is_unproven():
    g = {"50": {"class_type": "WanCameraImageToVideo", "inputs": {}}}
    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(g)
    assert "UNPROVEN" in str(exc.value)
    assert exc.value.evidence["verdict"] == "INDETERMINATE"


def test_the_vae_and_text_encoder_do_not_count_as_family_evidence():
    """Counting wan_2.1_vae as 'a Wan model' would make the gate answer the wrong question:
    the denoiser is the thing that either has the channel or does not."""
    g = {"21": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
         "20": {"class_type": "CLIPLoader",
                "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors"}},
         "50": {"class_type": "WanCameraImageToVideo", "inputs": {}}}
    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(g)
    assert exc.value.evidence["model_weights"] == []


def test_controlnet_appliers_are_exempt_by_record_not_by_omission():
    g = {"10": {"class_type": "UNETLoader",
                "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"}},
         "50": {"class_type": "WanImageToVideo", "inputs": {}},
         "90": {"class_type": "ControlNetApplyAdvanced", "inputs": {}}}
    ev = RG.pairing(g)
    assert {"node_id": "90", "class": "ControlNetApplyAdvanced", "requires": None} \
        in ev["conditioning_nodes"]


def test_the_two_tables_cover_every_latent_sizing_conditioning_class():
    """Completeness, checked rather than assumed: any Wan conditioning node that sizes a
    latent must have a pairing row, or the next one repeats wave 2."""
    covered = set(RG.CONDITIONING_WEIGHT_FAMILY) | RG.CONDITIONING_FAMILY_EXEMPT
    conditioning_latents = {c for c in RG.LATENT_NODES if c.startswith("Wan")}
    assert conditioning_latents <= covered, conditioning_latents - covered


def test_gate_pair_walks_into_subgraph_definitions():
    """A served template hides its loaders; the pairing question must reach them."""
    g = graph(top=[{"id": 50, "type": "WanCameraImageToVideo", "widgets_values": [832, 480, 65, 1]}],
              sub=[loader(83, "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors")])
    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(g)
    assert exc.value.evidence["model_weights"][0]["where"] != "top"


# =====================================================================================
# W3 amend — seven clauses that could not fire in the direction that mattered.
# =====================================================================================


# --- the walk stops one level too shallow (F-2b29d1ff) ----------------------------

def _nested(deep_file):
    """A subgraph definition that itself carries a definitions block.

    The docstring on `_iter_nodes` argues "4 nodes visible, 30 hidden". This is the same
    argument one level further down: a walker that reads `definitions.subgraphs[*].nodes`
    and stops there cannot see a blueprint nested inside a blueprint.
    """
    return {
        "nodes": [latent(3, 832, 480, 65), sampler(2, 1, "fixed"),
                  loader(1, "base.safetensors")],
        "definitions": {"subgraphs": [{
            "id": "sg-1", "name": "outer",
            "nodes": [loader(80, "clean.safetensors", cls="LoraLoaderModelOnly")],
            "definitions": {"subgraphs": [{
                "id": "sg-2", "name": "inner",
                "nodes": [loader(90, deep_file, cls="LoraLoaderModelOnly")],
            }]},
        }]},
    }


def test_a_banned_weight_two_levels_down_is_seen():
    files = {c["file"] for c in RG.components(_nested("causvid_x.safetensors"))}
    assert "causvid_x.safetensors" in files
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_nested("causvid_x.safetensors"))
    assert "causvid" in str(exc.value)


def test_the_nested_walk_terminates_on_a_cycle():
    """A visited set, not a recursion limit. A blueprint that references itself must
    report its nodes once rather than hang the gate that stands before a spend."""
    inner = {"id": "sg-1", "name": "loop",
             "nodes": [loader(90, "clean.safetensors", cls="LoraLoaderModelOnly")]}
    inner["definitions"] = {"subgraphs": [inner]}
    g = {"nodes": [latent(3, 832, 480, 65), sampler(2, 1, "fixed")],
         "definitions": {"subgraphs": [inner]}}
    assert [c["file"] for c in RG.components(g)] == ["clean.safetensors"]


# --- an API seed that is not there at all (F-20ba67ae) ----------------------------

def test_an_api_sampler_with_no_seed_input_is_not_pinned():
    """`literal = not isinstance(value, list)` reads a MISSING key as a pinned literal
    None. Gate S's registration clause does fail closed on it, but `verify`'s pinned
    clause reported "all pinned" on a graph with no seed at all."""
    g = api_graph()
    del g["3"]["inputs"]["noise_seed"]
    found = [s for s in RG.seeds(g) if s["node_id"] == "3"]
    assert found and found[0]["pinned"] is False
    assert found[0]["seed_is_literal"] is False
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "Gate S" in str(exc.value)


# --- the verdict must describe what actually ran (F-59f86a72, pair P10) -----------

def test_skipping_the_seed_clause_is_said_in_the_verdict_not_hidden_by_it():
    """`require_pinned_seeds=False` skipped the clause and still returned "N seed(s) all
    pinned" — the string builders store in the spend meta and sheets print. A record may
    not assert a property nobody checked."""
    g = graph(top=[loader(1, "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"),
                   sampler(2, 999, "randomize"), latent(3, 832, 480, 65)])
    ev = RG.verify(g, require_pinned_seeds=False)
    assert ev["seeds"][0]["pinned"] is False
    assert "all pinned" not in ev["verdict"]
    assert "NOT CHECKED" in ev["verdict"]
    assert ev["seed_clause_verdict"] == "NOT CHECKED (require_pinned_seeds=False)"


def test_a_checked_seed_clause_still_says_so():
    ev = RG.verify(graph(top=CLEAN_TOP))
    assert "all pinned" in ev["verdict"]
    assert ev["seed_clause_verdict"].startswith("CHECKED")


# --- `allow` may wave a methodology ruling, never a licence one (F-9602ad65) ------

def test_allow_cannot_wave_a_non_commercial_weight():
    """CLAUDE.md's non-negotiable: no non-commercially-licensed weight anywhere in the
    pipeline, including experiments. One keyword argument used to move causvid (CC-BY-NC)
    through with a verdict that said nothing about it."""
    g = graph(top=CLEAN_TOP + [loader(9, "Wan21_CausVid_14B_T2V_lora_rank32.safetensors",
                                      cls="LoraLoaderModelOnly")])
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, allow=("causvid",))
    assert "causvid" in str(exc.value)
    assert "BANNED" in str(exc.value)


def test_allowing_a_banned_key_is_refused_even_on_a_graph_that_does_not_load_it():
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(graph(top=CLEAN_TOP), allow=("openpose",))
    assert "openpose" in str(exc.value)


def test_a_waived_component_is_named_in_the_verdict_not_only_in_the_evidence():
    """The receipt is the verdict string. A waiver absent from it is a waiver the
    record does not carry."""
    g = graph(top=CLEAN_TOP,
              sub=[loader(83, "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors",
                          cls="LoraLoaderModelOnly")])
    ev = RG.verify(g, allow=("lightx2v",))
    assert ev["waived"] == ["lightx2v"]
    assert "lightx2v" in ev["verdict"]


# --- Gate PAIR's fail-closed clause is disarmed by a prefix (F-aa3a50b4) ----------

def test_a_non_wan_conditioning_class_still_halts_gate_pair():
    """The clause only looked at classes starting with "Wan", so a graph loading a t2v
    model and wiring `HunyuanImageToVideo` reported "0 conditioning node(s) paired" —
    green, having checked nothing. The class this gate was built for passed every other
    check in the file."""
    g = graph(top=[loader(1, "wan2.2_t2v_high_noise.safetensors"),
                   {"id": 5, "type": "HunyuanImageToVideo", "widgets_values": [832, 480, 65]},
                   sampler(2, 1, "fixed"), latent(3, 832, 480, 65)])
    with pytest.raises(RG.PairGate) as exc:
        RG.pairing(g)
    assert "HunyuanImageToVideo" in str(exc.value)
    assert exc.value.evidence["verdict"] == "INDETERMINATE"


def test_a_latent_suffixed_conditioning_class_halts_too():
    g = graph(top=[loader(1, "wan2.2_t2v_high_noise.safetensors"),
                   {"id": 5, "type": "SomeVendorImageToVideoLatent", "widgets_values": []},
                   sampler(2, 1, "fixed"), latent(3, 832, 480, 65)])
    with pytest.raises(RG.PairGate, match=r"\[PAIR\] conditioning class\(es\)"):
        RG.pairing(g)


def test_the_known_classes_are_still_not_reported_as_unknown():
    """The other direction: broadening the detector must not make every mapped class
    look new."""
    g = graph(top=[loader(1, "wan2.2_i2v_high_noise.safetensors"),
                   {"id": 5, "type": "WanImageToVideo",
                    "widgets_values": [832, 480, 65, 1]},
                   sampler(2, 1, "fixed")])
    ev = RG.pairing(g)
    assert ev["verdict"].startswith("1 conditioning node(s) paired")


# --- Gate L reads its own rules, and refuses a frame that is not one (F-f77fd337) --

def test_a_zero_or_negative_frame_is_not_legal():
    """Measured: frame_legality(0, 0, 1) and (-16, -16, 1) both returned legal=True with
    no problems, because 0 % 16 == 0 and (1 - 1) % 4 == 0."""
    assert RG.frame_legality(0, 0, 1)["legal"] is False
    assert RG.frame_legality(-16, -16, 1)["legal"] is False
    assert RG.frame_legality(832, 480, 0)["legal"] is False


def test_a_non_integer_dimension_raises_the_gates_own_error():
    """It used to be a bare TypeError from the modulo — an exception no caller of a gate
    is catching."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.frame_legality("832", 480, 65)
    assert "832" in str(exc.value)
    with pytest.raises(RG.RouteGate, match=r"\[ROUTE\] length True is not an int \(bool\); Gate L compares"):
        RG.frame_legality(832, 480, True)


def test_the_declared_frame_form_is_the_one_enforced(monkeypatch):
    """`GENERATOR_RULES` declares `frame_form: '4n+1'` as data and the code tested
    `(length - 1) % 4` against a literal 4. A second family would have been graded on
    wan's temporal rule while its own row said otherwise."""
    rules = dict(RG.GENERATOR_RULES)
    rules["eightly"] = {"dim_multiple": 16, "frame_form": "8n+1", "max_frames": 81}
    monkeypatch.setattr(RG, "GENERATOR_RULES", rules)
    assert RG.frame_legality(832, 480, 65, family="eightly")["legal"] is True
    illegal = RG.frame_legality(832, 480, 61, family="eightly")
    assert illegal["legal"] is False
    assert "8n+1" in " ".join(illegal["problems"])
    # and wan is unmoved by the neighbour's row
    assert RG.frame_legality(832, 480, 61)["legal"] is True


def test_an_unparseable_frame_form_raises_rather_than_defaulting_to_wans(monkeypatch):
    rules = dict(RG.GENERATOR_RULES)
    rules["nonsense"] = {"dim_multiple": 16, "frame_form": "every other one",
                         "max_frames": 81}
    monkeypatch.setattr(RG, "GENERATOR_RULES", rules)
    with pytest.raises(RG.RouteGate) as exc:
        RG.frame_legality(832, 480, 65, family="nonsense")
    assert "frame_form" in str(exc.value)


# =====================================================================================
# W6 amend — the wrapped-graph shape, one loader (F-c0ff220c, F-e9aa7390)
# =====================================================================================


def _banned_api():
    """An API graph that loads a BANNED weight and pins a randomisable-looking seed."""
    return {
        "3": {"class_type": "KSamplerAdvanced",
              "inputs": {"add_noise": "enable", "noise_seed": 999999, "model": ["11", 0]}},
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
        "11": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"lora_name": "causvid_x.safetensors", "model": ["10", 0]}},
    }


@pytest.mark.parametrize("key", list(canon.GRAPH_WRAPPER_KEYS))
def test_every_wrapper_key_the_tuple_names_is_unwrapped_by_the_one_loader(key):
    """`canon.GRAPH_WRAPPER_KEYS` names three keys and `load_graph` unwrapped the LAST
    two — `prompt`, the standard submission envelope, was precisely the one it did not
    unwrap, while the comment beside the tuple implied it was handled."""
    inner = _banned_api()
    assert RG.normalise_graph({key: inner}) is inner


def test_the_wrapper_key_list_is_the_one_canon_publishes():
    assert RG.WRAPPER_KEYS is canon.GRAPH_WRAPPER_KEYS


@pytest.mark.parametrize("reader", ["verify", "components", "seeds", "gate_s"])
def test_a_wrapped_graph_is_not_read_as_an_empty_one(reader):
    """THE clause. Measured 2026-09-03: wrapped in the standard `{"prompt": ...}`
    envelope, `components()`, `seeds()` and `latents()` all returned [] and `verify`
    returned "0 weight file(s), 0 seed(s) all pinned, ... 1 frame(s) checked and
    generator-legal" on a graph loading a CC-BY-NC weight. A banned file would have been
    submitted under a green receipt."""
    wrapped = {"prompt": _banned_api()}
    if reader == "verify":
        with pytest.raises(RG.RouteGate) as exc:
            RG.verify(wrapped, frame=(832, 480, 81))
        assert "causvid" in str(exc.value)
    elif reader == "components":
        assert [c["file"] for c in RG.components(wrapped)] == \
            ["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "causvid_x.safetensors"]
    elif reader == "seeds":
        assert [s["seed"] for s in RG.seeds(wrapped)] == [999999]
    else:
        with pytest.raises(RG.RouteGate) as exc:
            RG.gate_s_registration(wrapped, [7])
        assert "999999" in str(exc.value)


def test_a_shape_this_module_cannot_read_raises_rather_than_walking_zero_nodes():
    """"This graph has no nodes" and "I cannot read this shape" were the same answer."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.components({"last_node_id": 12, "extra": {"not": "a node"}})
    assert "neither API format" in str(exc.value)
    ev = exc.value.evidence
    assert ev["top_level_keys"] == ["extra", "last_node_id"]
    assert ev["wrapper_keys"] == list(RG.WRAPPER_KEYS)


def test_is_api_format_refuses_an_unreadable_shape_instead_of_answering_false():
    """Answering False sent the caller down the save-format branch to walk a `nodes`
    list that does not exist, which is where the zero-population pass came from."""
    with pytest.raises(RG.RouteGate,
                       match=r"\[ROUTE\] this is not a graph this module can read: a dict"):
        RG.is_api_format({"foo": 1})
    assert RG.is_api_format(_banned_api()) is True
    assert RG.is_api_format(graph(top=CLEAN_TOP)) is False


def test_load_graph_unwraps_the_submission_envelope_and_refuses_by_name(tmp_path):
    import json as _json

    p = tmp_path / "saved.json"
    p.write_text(_json.dumps({"prompt": _banned_api()}), encoding="utf-8")
    assert sorted(RG.load_graph(str(p))) == ["10", "11", "3"]

    bad = tmp_path / "bad.json"
    bad.write_text(_json.dumps({"last_node_id": 4}), encoding="utf-8")
    with pytest.raises(RG.RouteGate) as exc:
        RG.load_graph(str(bad))
    assert "bad.json" in str(exc.value)
    assert exc.value.evidence["path"].endswith("bad.json")


# --- the licence clause took the FIRST matching row (F-ebef0135) ----------------------


def _loads(filename):
    return {"10": {"class_type": "UNETLoader",
                   "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
            "12": {"class_type": "LoraLoaderModelOnly",
                   "inputs": {"lora_name": filename, "model": ["10", 0]}},
            "3": {"class_type": "KSamplerAdvanced",
                  "inputs": {"add_noise": "enable", "noise_seed": 7, "model": ["12", 0]}}}


@pytest.mark.parametrize("filename,strictest,also", [
    ("technically_color_instagirl_v2.safetensors", "BANNED", "technically_color"),
    ("smartphonesnapshot_vintage_film_grain.safetensors", "BANNED", "smartphonesnapshot"),
    ("causvid_lightx2v_merge.safetensors", "BANNED", "lightx2v"),
])
def test_a_filename_matching_two_rows_is_governed_by_the_strictest(filename, strictest, also):
    """Measured 2026-09-03: `technically_color_instagirl_v2.safetensors` matches
    technically_color (ALLOWED, typed in at index 4) and instagirl (BANNED, index 9), and
    components() returned ALLOWED with the BANNED row named nowhere in the evidence."""
    rec = RG.components(_loads(filename))[1]
    assert rec["ruling"]["verdict"] == strictest
    assert also in [m["matched_on"] for m in rec["ruling"]["matches"]]
    assert len(rec["ruling"]["matches"]) >= 2

    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_loads(filename), frame=(832, 480, 81))
    assert "also matches" in str(exc.value)
    named = {m["matched_on"] for c in exc.value.evidence["components"]
             for m in c["ruling"]["matches"]}
    assert also in named


def test_the_strictest_match_governs_and_allow_still_cannot_wave_a_licence_row():
    """`allow` waves a METHODOLOGY ruling; a concatenated name that also carries a BANNED
    row is still refused, and the refusal names the row that governs."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_loads("causvid_lightx2v_merge.safetensors"),
                  frame=(832, 480, 81), allow=("lightx2v",))
    assert "causvid" in str(exc.value)


def test_the_licence_clause_records_every_match_the_way_families_of_already_does():
    """The sibling that carries the rule: `families_of` records every family a filename
    matches and its table's comment says why. The licence clause got the weaker rule."""
    assert RG.families_of("wan2.2_fun_camera_i2v.safetensors") == ["fun_camera", "i2v"]
    hits = RG.rulings_for("technically_color_instagirl_v2.safetensors")
    assert [h["matched_on"] for h in hits] == ["instagirl", "technically_color"]


def test_a_filename_matching_nothing_is_still_reported_as_not_in_this_table():
    rec = RG.components(_loads("some_unruled_style.safetensors"))[1]
    assert rec["ruling"]["verdict"] == "NOT IN THIS TABLE"
    assert rec["ruling"]["matches"] == []


# --- the seed clause had no "nothing was checkable" answer (F-61768a9f) --------------


def _unrecorded_sampler_api():
    """SamplerCustomAdvanced fed by RandomNoise — the shape E13 met, one tier over."""
    return {
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
        "25": {"class_type": "RandomNoise", "inputs": {"noise_seed": 123456789}},
        "13": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["25", 0], "model": ["10", 0]}},
        "40": {"class_type": "EmptyHunyuanLatentVideo",
               "inputs": {"width": 832, "height": 480, "length": 81}},
    }


def test_a_sampler_class_with_no_seed_row_halts_instead_of_reporting_every_seed_pinned():
    """Measured 2026-09-03: seeds() returned [], verify reported "0 seed(s) all pinned"
    and gate_s_registration reported "0 noise-bearing seed(s), all pinned and all drawn
    from the committed list of 1" — while the seed that would run was 123456789 and the
    committed list was [7]."""
    g = _unrecorded_sampler_api()
    assert RG.seeds(g) == []
    found = RG.unrecorded_seed_sources(g)
    # `RandomNoise` is caught by BOTH clauses (a `noise_seed` input, and a class name
    # ending in `Noise`). `SamplerCustomAdvanced` is caught by neither — it ends in
    # `Advanced` and its inputs are links — which is recorded rather than papered over:
    # the seed itself lives on the noise node, and that is the node the andon names.
    assert {u["class"] for u in found} == {"RandomNoise"}

    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "INDETERMINATE" in str(exc.value) or "no SEED_NODES row" in str(exc.value)
    assert "RandomNoise" in str(exc.value)
    assert exc.value.evidence["seed_clause_verdict"] == "INDETERMINATE"

    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(g, [7])
    assert "SEED_NODES" in str(exc.value)


def test_a_graph_with_no_seed_at_all_is_indeterminate_rather_than_all_pinned():
    g = {"10": {"class_type": "UNETLoader",
                "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "40": {"class_type": "EmptyHunyuanLatentVideo",
                "inputs": {"width": 832, "height": 480, "length": 81}}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "UNPROVEN" in str(exc.value)
    with pytest.raises(RG.RouteGate,
                       match=r"\[ROUTE\] the seed clause is INDETERMINATE on this graph"):
        RG.gate_s_registration(g, [7])

    # the assertion is available, and it is CHECKED rather than obeyed
    ev = RG.verify(g, carries_no_sampler=True)
    assert "all pinned" not in ev["verdict"]
    assert ev["seed_clause_verdict"].startswith("CHECKED")
    assert RG.gate_s_registration(g, [7], carries_no_sampler=True)["verdict"] \
        .startswith("no sampler")


def test_the_no_sampler_assertion_is_refused_when_the_graph_carries_one():
    g = {"10": {"class_type": "UNETLoader",
                "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "3": {"class_type": "KSamplerAdvanced",
               "inputs": {"add_noise": "enable", "noise_seed": 7, "model": ["10", 0]}},
         "40": {"class_type": "EmptyHunyuanLatentVideo",
                "inputs": {"width": 832, "height": 480, "length": 81}}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, carries_no_sampler=True)
    assert "checked, not obeyed" in str(exc.value)
    with pytest.raises(RG.RouteGate, match=r"\[ROUTE\] the caller asserted this graph carries no sampler"):
        RG.gate_s_registration(g, [7], carries_no_sampler=True)
    # and the ordinary graph still passes
    assert "1 seed(s) all pinned" in RG.verify(g)["verdict"]


def test_the_verdict_string_never_says_all_pinned_over_zero_seeds():
    """The phrase is what a spend meta stores and a provenance sheet prints."""
    g = {"10": {"class_type": "UNETLoader",
                "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "40": {"class_type": "EmptyHunyuanLatentVideo",
                "inputs": {"width": 832, "height": 480, "length": 81}}}
    ev = RG.verify(g, carries_no_sampler=True)
    assert "0 seed(s) all pinned" not in ev["verdict"]
    ev2 = RG.verify(g, require_pinned_seeds=False)
    assert "all pinned" not in ev2["verdict"]
    assert ev2["seed_clause_verdict"] == "NOT CHECKED (require_pinned_seeds=False)"


def test_a_scheduler_picker_is_not_mistaken_for_an_unrecorded_seed_source():
    """`KSamplerSelect` picks a scheduler and carries no seed; an andon that fires on a
    correct graph is not one anybody keeps."""
    g = {"10": {"class_type": "UNETLoader",
                "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
         "3": {"class_type": "KSamplerAdvanced",
               "inputs": {"add_noise": "enable", "noise_seed": 7, "model": ["10", 0]}},
         "40": {"class_type": "EmptyHunyuanLatentVideo",
                "inputs": {"width": 832, "height": 480, "length": 81}}}
    assert RG.unrecorded_seed_sources(g) == []
    assert RG.verify(g)["seed_clause_verdict"] == "CHECKED — 1 seed(s) all pinned"


# --- WAVE 8, F-f4f61b9c: the seed andon had one format, and the paid path reads the other

# Every fixture in the seed-population block above is API format. There was no SAVE-format
# fixture anywhere in this suite for this andon, and `unrecorded_seed_sources` gates its
# input-name half behind `if api:` (route_gates.py:667). Measured 2026-09-04 on ONE graph
# expressed both ways — a UNETLoader, a pinned KSamplerAdvanced, an EmptyHunyuanLatentVideo,
# and a node of class `SeedGeneratorAdvanced` carrying a seed input with no SEED_NODES row
# (it ends in neither `Sampler` nor `Noise`, so the class-name half cannot see it either):
#
#   API format   unrecorded_seed_sources names node 55; verify() raises
#                "[ROUTE] the seed clause is INDETERMINATE"; gate_s_registration raises.
#   SAVE format  unrecorded_seed_sources returns []; verify() returns
#                seed_clause_verdict "CHECKED — 1 seed(s) all pinned"; gate_s_registration
#                returns "1 noise-bearing seed(s), all pinned and all drawn from the
#                committed list of 1".
#
# Save format is the format `gate_saved_graph` reads, and `gate_saved_graph` is the LAST
# check before a paid submission on the `--saved` admission path. So the run's recorded
# seed would not be the seed that ran, under a green Gate S.
#
# The save-format signal exists and needs no new table: a converted widget input appears in
# the node's `inputs` LIST with a `name` field, which is what these fixtures carry.

_TWIN_UNET = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"


def _seed_twin_api(with_unrecorded=True):
    g = {
        "10": {"class_type": "UNETLoader", "inputs": {"unet_name": _TWIN_UNET}},
        "3": {"class_type": "KSamplerAdvanced",
              "inputs": {"add_noise": "enable", "noise_seed": 7, "model": ["10", 0]}},
        "40": {"class_type": "EmptyHunyuanLatentVideo",
               "inputs": {"width": 832, "height": 480, "length": 81}},
    }
    if with_unrecorded:
        g["55"] = {"class_type": "SeedGeneratorAdvanced", "inputs": {"seed": 999999999}}
    return g


def _seed_twin_save(with_unrecorded=True):
    """The same graph as `_seed_twin_api`, in the format a saved workflow file carries.

    `widgets_values` is POSITIONAL, so KSamplerAdvanced's three SEED_NODES indices —
    add_noise 0, seed 1, control 2 — are "enable", 7, "fixed". Node 55's seed is a
    CONVERTED WIDGET: in save format that is an entry in the `inputs` list carrying a
    `name`, which is the signal the API branch reads off the inputs mapping.
    """
    nodes = [
        {"id": 10, "type": "UNETLoader", "widgets_values": [_TWIN_UNET], "inputs": []},
        {"id": 3, "type": "KSamplerAdvanced",
         "widgets_values": ["enable", 7, "fixed", 20, 8.0, "euler", "simple", 0, 10000,
                            "disable"],
         "inputs": [{"name": "model", "type": "MODEL", "link": 1}]},
        {"id": 40, "type": "EmptyHunyuanLatentVideo",
         "widgets_values": [832, 480, 81, 1], "inputs": []},
    ]
    if with_unrecorded:
        nodes.append(
            {"id": 55, "type": "SeedGeneratorAdvanced", "widgets_values": [999999999],
             "inputs": [{"name": "seed", "type": "INT", "widget": {"name": "seed"},
                         "link": None}]})
    return {"nodes": nodes, "links": [[1, 10, 0, 3, 0, "MODEL"]]}


def test_the_two_formats_really_are_the_same_graph():
    """The premise of every assertion below, checked rather than assumed. If the twins
    disagreed about their weights, their pinned seed or their latent, a difference in the
    seed andon would say nothing about the andon."""
    api, save = _seed_twin_api(), _seed_twin_save()
    assert RG.is_api_format(api) is True
    assert RG.is_api_format(save) is False
    assert [c["file"] for c in RG.components(api)] == [c["file"] for c in RG.components(save)]
    assert [(s["class"], s["seed"], s["pinned"]) for s in RG.seeds(api)] \
        == [(s["class"], s["seed"], s["pinned"]) for s in RG.seeds(save)]
    assert len(RG.latents(api)) == len(RG.latents(save))


def test_the_clean_twin_passes_in_both_formats():
    """The direction the fix must not break: with the unrecorded node removed, both
    formats verify, and both report the SAME seed verdict. Without this, the andon could
    satisfy the tests below by refusing every saved graph ever handed to it."""
    api, save = _seed_twin_api(False), _seed_twin_save(False)
    assert RG.unrecorded_seed_sources(api) == []
    assert RG.unrecorded_seed_sources(save) == []
    assert RG.verify(api)["seed_clause_verdict"] == RG.verify(save)["seed_clause_verdict"]
    assert "1 seed(s) all pinned" in RG.verify(save)["seed_clause_verdict"]


@pytest.mark.parametrize("fmt,build", [("api", _seed_twin_api), ("save", _seed_twin_save)])
def test_an_unrecorded_seed_source_is_named_in_both_formats(fmt, build):
    """The andon's own population question, asked of the format the paid path reads."""
    found = RG.unrecorded_seed_sources(build())
    assert [u["class"] for u in found] == ["SeedGeneratorAdvanced"], (
        f"{fmt} format: the node whose seed nothing records was not named. In save format "
        f"the converted widget is an entry in the node's `inputs` LIST carrying "
        f"name='seed'; reading only the API mapping leaves the format that Gate S "
        f"actually admits unpoliced.")
    assert str(found[0]["node_id"]) == "55"


@pytest.mark.parametrize("fmt,build", [("api", _seed_twin_api), ("save", _seed_twin_save)])
def test_verify_is_indeterminate_on_the_unrecorded_seed_source_in_both_formats(fmt, build):
    with pytest.raises(RG.RouteGate,
                       match=r"\[ROUTE\] the seed clause is INDETERMINATE") as exc:
        RG.verify(build())
    assert "SeedGeneratorAdvanced" in str(exc.value), fmt


@pytest.mark.parametrize("fmt,build", [("api", _seed_twin_api), ("save", _seed_twin_save)])
def test_gate_s_refuses_the_unrecorded_seed_source_in_both_formats(fmt, build):
    """`gate_saved_graph` reads save format and is the last check before a paid
    submission. A saved workflow whose seed is produced by an unrecorded class must not
    pass Gate S reporting every seed pinned — the run's recorded seed would not be the
    seed that ran."""
    with pytest.raises(RG.RouteGate, match=r"SEED_NODES") as exc:
        RG.gate_s_registration(build(), [7])
    assert "SeedGeneratorAdvanced" in str(exc.value), fmt




# --- W8 amend ----------------------------------------------------------------------
#
# Four findings and one routed CRITICAL, all in this module. Each fixture answers the
# repo's question of a fixture: what would this look like if the code were wrong in the
# specific way this check exists to catch?


def _unrecorded_sampler_save():
    """The save-format twin of `_unrecorded_sampler_api()`, and the shape the finding
    measured: a recorded KSampler beside a hosted partner node whose positional widget
    list carries a seed nobody registered."""
    return {"nodes": [
        {"id": 3, "type": "KSampler", "inputs": [],
         "widgets_values": [7, "fixed", 20, 6.0, "euler", "simple", 1.0]},
        {"id": 4, "type": "KlingVideoApi", "inputs": [],
         "widgets_values": ["kling-v2", "720P", "16:9", 5, 999999999]},
        {"id": 10, "type": "UNETLoader",
         "widgets_values": ["wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"]},
        {"id": 49, "type": "WanImageToVideo", "widgets_values": [832, 480, 81, 1]},
    ]}


def test_the_seed_population_andon_runs_in_save_format_too():
    """Measured 2026-09-04 before the fix: on this graph `unrecorded_seed_sources`
    returned [], `seeds()` returned only the KSampler, `gate_s_registration(g, [7])`
    returned "1 noise-bearing seed(s), all pinned and all drawn from the committed list
    of 1", and `verify(g, frame=(832,480,81))` returned "CHECKED - 1 seed(s) all pinned"
    - while node 4's seed 999999999 was never examined. The SAME node in API format was
    caught, so the two formats gave opposite answers about one graph, and save format is
    the one the cloud hands back and `load_graph` reads before submission."""
    g = _unrecorded_sampler_save()
    found = RG.unrecorded_seed_sources(g)
    assert [u["class"] for u in found] == ["KlingVideoApi"]
    assert found[0]["node_id"] == 4

    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(g, [7])
    assert "KlingVideoApi" in str(exc.value)
    assert exc.value.evidence["seed_clause_verdict"] == "INDETERMINATE"

    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 81))
    assert "KlingVideoApi" in str(exc.value)


def test_a_save_format_converted_widget_named_seed_is_read_by_name():
    """Save format names inputs too - as a list of slot dicts, a converted widget
    carrying `{"widget": {"name": "seed"}}`. The input-name clause reads each format's
    own spelling rather than running in one of them."""
    g = {"nodes": [
        {"id": 7, "type": "SomeVendorSampl3r",
         "inputs": [{"name": "model", "type": "MODEL", "link": 1},
                    {"name": "seed", "type": "INT", "link": 2,
                     "widget": {"name": "seed"}}],
         "widgets_values": [42]},
    ]}
    found = RG.unrecorded_seed_sources(g)
    assert [u["class"] for u in found] == ["SomeVendorSampl3r"]
    assert "seed" in found[0]["why"]


def test_the_save_format_clause_does_not_fire_on_a_graph_it_can_read():
    """The other direction: an andon that fires on a correct graph is not one anybody
    keeps. A recorded sampler and a recorded hosted node both have SEED_NODES rows."""
    g = {"nodes": [
        {"id": 3, "type": "KSampler", "inputs": [],
         "widgets_values": [7, "fixed", 20, 6.0, "euler", "simple", 1.0]},
        {"id": 10, "type": "UNETLoader",
         "widgets_values": ["wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"]},
        {"id": 49, "type": "WanImageToVideo", "widgets_values": [832, 480, 81, 1]},
    ]}
    assert RG.unrecorded_seed_sources(g) == []
    assert RG.gate_s_registration(g, [7])["verdict"].startswith("1 noise-bearing")


# --- the class-level licence clause (builders' unanimous CRITICAL, routed here) ------


def _detector_graph_api(cls="DWPreprocessor"):
    """A graph wiring the banned detector tier. It brings NO weight filename with it -
    the preprocessor fetches its own weights at run time - so every clause that read
    `widgets_values` for a weight suffix saw nothing at all."""
    return {
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
        "11": {"class_type": cls, "inputs": {"image": ["12", 0], "resolution": 512}},
        "3": {"class_type": "KSamplerAdvanced",
              "inputs": {"add_noise": "enable", "noise_seed": 7, "model": ["10", 0]}},
        "40": {"class_type": "EmptyHunyuanLatentVideo",
               "inputs": {"width": 832, "height": 480, "length": 81}},
    }


def test_a_banned_node_class_is_visible_to_the_licence_clause():
    """Measured 2026-09-04 before the fix: `components()` on this graph returned one row
    (the UNET file) and `verify(g)` returned green, while node 11 is the `dwpose` row's
    tier - BANNED, "weights not fetched", UNVERIFIED-treated-as-NO. A licence row is not
    a wiring claim, and a wiring claim is not always a filename."""
    g = _detector_graph_api()
    rows = RG.ruled_node_classes(g)
    assert [r["class_type"] for r in rows] == ["DWPreprocessor"]
    assert rows[0]["verdict"] == "BANNED"
    assert rows[0]["matched_on"] == "dwpose"
    assert rows[0]["licence"] and rows[0]["reason"]

    banned = [c for c in RG.components(g) if c["verdict"] == "BANNED"]
    assert [c["class_type"] for c in banned] == ["DWPreprocessor"]

    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g)
    assert "DWPreprocessor" in str(exc.value)
    assert "BANNED" in str(exc.value)


def test_the_openpose_row_catches_its_own_preprocessor_class_too():
    g = _detector_graph_api("OpenposePreprocessor")
    rows = RG.ruled_node_classes(g)
    assert rows[0]["matched_on"] == "openpose"
    with pytest.raises(RG.RouteGate, match=r"BANNED"):
        RG.verify(g)


def test_the_class_clause_reads_save_format_and_subgraphs_like_every_other_clause():
    g = graph([{"id": 1, "type": "UNETLoader",
                "widgets_values": ["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"]}],
              [{"id": 2, "type": "DWPreprocessor", "widgets_values": [512]}])
    rows = RG.ruled_node_classes(g)
    assert [r["class_type"] for r in rows] == ["DWPreprocessor"]
    assert rows[0]["where"] != "top"


def test_an_unruled_node_class_is_not_invented_into_a_ruling():
    """The red direction of the matcher: a class whose name matches no row contributes
    nothing, and the ordinary graphs this repo builds stay clean."""
    g = {"10": {"class_type": "UNETLoader",
                "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "3": {"class_type": "KSamplerAdvanced",
               "inputs": {"add_noise": "enable", "noise_seed": 7, "model": ["10", 0]}},
         "40": {"class_type": "EmptyHunyuanLatentVideo",
                "inputs": {"width": 832, "height": 480, "length": 81}}}
    assert RG.ruled_node_classes(g) == []
    assert all(c["kind"] == "weight" for c in RG.components(g))


def test_every_ruled_row_is_matched_on_its_own_key_even_with_no_alias():
    """`RULED_COMPONENT_CLASSES` only ADDS aliases: a row absent from it is still
    matched on its own name, so no row is silently exempt from the class clause.
    Derived over the whole table rather than typed."""
    for key in RG.RULED_COMPONENTS:
        pats = RG.class_patterns_for(key)
        assert key.lower() in pats, key
        hits = RG.rulings_for_class(f"Some{key}Node")
        assert [h["matched_on"] for h in hits][:1] == [key], key


# --- the evidence names the andon that raises (F-1844be26) ---------------------------


def test_gate_s_registrations_evidence_names_the_andon_that_actually_raises():
    """`gate_s_registration` built `ev = {"gate": "S", ...}` and every failure path
    raises `RouteGate`, whose class attribute is `gate = "ROUTE"`. `stage_render`
    prints GATE_FAILURE <exc.gate> and GATE_EVIDENCE <json> as two lines, so a receipt
    said ROUTE on one and S on the other - and "S" is already the id of
    `errors.GateSSeedRegistration`, a different andon with different evidence keys."""
    g = {"nodes": [{"id": 3, "type": "KSampler", "inputs": [],
                    "widgets_values": [7, "fixed", 20, 6.0, "euler", "simple", 1.0]}]}
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(g, [99])
    assert exc.value.gate == exc.value.evidence["gate"] == "ROUTE"
    assert exc.value.evidence["clause"] == "gate_s_registration"

    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(g, [])
    assert exc.value.gate == exc.value.evidence["gate"] == "ROUTE"

    ev = RG.gate_s_registration(g, [7])
    assert ev["gate"] == "ROUTE" and ev["clause"] == "gate_s_registration"


# --- load_graph refuses a file it cannot parse, by name (F-c55e4571) -----------------


def test_load_graph_names_the_file_it_could_not_parse(tmp_path):
    """The parse sat OUTSIDE the try that prefixes the path. Measured 2026-09-04: a file
    containing `{ not json at all }` raised json.JSONDecodeError with the path nowhere in
    the message, and neither error is an ArmatureError, so a caller catching GateFailure
    around a submission step did not catch it."""
    bad = tmp_path / "broken.api.json"
    bad.write_text("{ not json at all }", encoding="utf-8")
    with pytest.raises(RG.RouteGate) as exc:
        RG.load_graph(str(bad))
    assert "broken.api.json" in str(exc.value)
    assert exc.value.evidence["clause"] == "unparseable_file"


def test_load_graph_refuses_an_empty_file_by_name_rather_than_parsing_nothing(tmp_path):
    """`find` and `rfind` both return -1 on an empty file and the slice is '', so
    json.loads was handed the empty string."""
    empty = tmp_path / "empty.api.json"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(RG.RouteGate) as exc:
        RG.load_graph(str(empty))
    assert "empty.api.json" in str(exc.value)
    assert exc.value.evidence["n_chars"] == 0

    braceless = tmp_path / "braceless.json"
    braceless.write_text("not a graph, just prose\n", encoding="utf-8")
    with pytest.raises(RG.RouteGate, match=r"contains no JSON object at all"):
        RG.load_graph(str(braceless))


def test_load_graph_still_reads_a_good_file(tmp_path):
    good = tmp_path / "ok.api.json"
    good.write_text('{"prompt": {"3": {"class_type": "KSampler", "inputs": {"seed": 7}}}}',
                    encoding="utf-8")
    assert RG.is_api_format(RG.load_graph(str(good)))


# --- W10 amend: the hosted clause runs in BOTH formats (F-e1a36cfc) -------------------
#
# Wave 8 closed the save-format half of the hosted-seed andon and left the API half open,
# and API is the format every builder submits.


def _hosted_seed_pair(seed_input=None):
    """ONE graph, written in both formats: UNETLoader + WanImageToVideo + a recorded
    KSampler + a `KlingVideoApi` node that has no `SEED_NODES` row.

    `seed_input` optionally namespaces the hosted node's seed the way this repo's own
    hosted node namespaces every other input (`build_r2v_payload.py:79-83` writes
    `model.prompt` / `model.resolution` / `model.ratio` / `model.duration`).
    """
    hosted_inputs = {"model": "kling-v2", "model.resolution": "720P",
                     "model.ratio": "16:9", "model.duration": 5}
    if seed_input:
        hosted_inputs[seed_input] = 999999999
    api = {
        "3": {"class_type": "KSampler",
              "inputs": {"seed": 7, "control_after_generate": "fixed",
                         "model": ["10", 0]}},
        "4": {"class_type": "KlingVideoApi", "inputs": dict(hosted_inputs)},
        "10": {"class_type": "UNETLoader",
               "inputs": {"unet_name":
                          "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"}},
        "49": {"class_type": "WanImageToVideo",
               "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1}},
    }
    save = {"nodes": [
        {"id": 3, "type": "KSampler", "inputs": [],
         "widgets_values": [7, "fixed", 20, 6.0, "euler", "simple", 1.0]},
        {"id": 4, "type": "KlingVideoApi", "inputs": [],
         "widgets_values": ["kling-v2", "720P", "16:9", 5]
                           + ([999999999] if seed_input else [])},
        {"id": 10, "type": "UNETLoader",
         "widgets_values": ["wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"]},
        {"id": 49, "type": "WanImageToVideo", "widgets_values": [832, 480, 81, 1]},
    ]}
    return {"api": api, "save": save}


@pytest.mark.parametrize("seed_input", [None, "model.seed", "seed"])
def test_one_graph_two_formats_gets_one_verdict_on_an_unrecorded_hosted_node(seed_input):
    """The finding's own fixture, asserted AS A PAIR rather than as two independent
    cases — the defect was that the two formats disagreed about one graph.

    Measured 2026-09-04 before the fix, with no seed input at all: save format gave
    `unrecorded_seed_sources` one row and both `gate_s_registration(g, [7])` and
    `verify(g, frame=(832,480,81))` raised; the SAME graph in API format gave
    `unrecorded_seed_sources() == []`, "1 noise-bearing seed(s), all pinned and all drawn
    from the committed list of 1", and `seed_clause_verdict = 'CHECKED - 1 seed(s) all
    pinned'`. Repeated with an explicit `model.seed` of 999999999: API still green, that
    seed never examined.
    """
    pair = _hosted_seed_pair(seed_input)
    verdicts = {}
    for fmt, g in pair.items():
        rows = RG.unrecorded_seed_sources(g)
        assert [u["class"] for u in rows] == ["KlingVideoApi"], fmt
        assert str(rows[0]["node_id"]) == "4", fmt

        with pytest.raises(RG.RouteGate) as exc:
            RG.gate_s_registration(g, [7])
        assert "KlingVideoApi" in str(exc.value), fmt
        assert exc.value.evidence["seed_clause_verdict"] == "INDETERMINATE", fmt

        with pytest.raises(RG.RouteGate) as exc:
            RG.verify(g, frame=(832, 480, 81))
        assert "KlingVideoApi" in str(exc.value), fmt
        verdicts[fmt] = rows[0]["why"]

    assert RG.is_api_format(pair["api"]) and not RG.is_api_format(pair["save"])
    assert set(verdicts) == {"api", "save"}


def test_a_namespaced_seed_input_is_read_by_its_last_dotted_segment():
    """The docstring's stated ground for gating the hosted clause on `not api` was that
    "in API format inputs are keyed by name and the input-name clause already answers".
    That holds only while a vendor spells its seed input exactly seed/noise_seed/rand_seed
    — and this repo's own hosted node namespaces every other input under `model.`."""
    g = {"5": {"class_type": "SomeVendorThing",
               "inputs": {"model.noise_seed": 12345, "model.prompt": "x"}}}
    rows = RG.unrecorded_seed_sources(g)
    assert [u["class"] for u in rows] == ["SomeVendorThing"]
    assert "model.noise_seed" in rows[0]["why"]


def test_the_hosted_clause_does_not_fire_on_a_class_that_has_a_row():
    """The red-adjacent direction: an andon that fires on a correct graph is not one
    anybody keeps. `Wan2ReferenceVideoApi` — the hosted node this repo actually submits —
    ends in `Api` and carries a `SEED_NODES` row, so it is READ rather than flagged, in
    both formats."""
    api = {"6": {"class_type": "Wan2ReferenceVideoApi",
                 "inputs": {"model": "wan2.7-r2v", "model.prompt": "p", "seed": 7,
                            "model.resolution": "720P"}}}
    save = {"nodes": [{"id": 6, "type": "Wan2ReferenceVideoApi", "inputs": [],
                       "widgets_values": ["wan2.7-r2v", "p", "n", "720P", "16:9", 5,
                                          7, "fixed"]}]}
    assert RG.unrecorded_seed_sources(api) == []
    assert RG.unrecorded_seed_sources(save) == []


def test_no_graph_this_repo_builds_is_caught_by_the_widened_api_clause():
    """The population that must stay green: the clean fixture at the top of this file and
    the detector-free API graph, in both readings."""
    assert RG.unrecorded_seed_sources(graph(top=CLEAN_TOP)) == []
    assert RG.verify(graph(top=CLEAN_TOP))["frame_legality"][0]["legal"] is True


# --- W10 amend: the alias table's REVERSE direction is pinned (F-62accd2c) ------------


def test_every_alias_key_names_a_ruled_component_row():
    """The forward direction — every row is matched on its own key — is pinned above by
    `test_every_ruled_row_is_matched_on_its_own_key_even_with_no_alias`. This is the
    reverse, and it was pinned nowhere.

    `class_patterns_for` is only ever reached through `rulings_for_class`, which iterates
    `RULED_COMPONENTS.items()` — so an alias entry whose key is no longer a row is never
    consulted and never reported. `RULED_COMPONENTS` is a MIRROR of docs/license-map.md,
    and a re-fetch renaming or retiring a row is a normal, expected edit."""
    assert set(RG.RULED_COMPONENT_CLASSES) <= set(RG.RULED_COMPONENTS)
    assert RG.orphaned_component_class_aliases() == []


def test_an_orphaned_alias_is_refused_where_a_wrong_table_is_loudest(monkeypatch):
    """The RED direction, by mutation: rename the row and the alias orphans.

    Measured 2026-09-04 before the fix: on a save-format graph carrying one
    `DWPreprocessor`, `ruled_node_classes` returned one row ('DWPreprocessor', 'BANNED');
    renaming the `RULED_COMPONENTS` key 'dwpose' to 'dwpose_ts' while leaving the alias
    entry under 'dwpose' made `ruled_node_classes` return [] and
    `class_patterns_for('dwpose_ts')` return only ('dwpose_ts',) — the class clause fell
    back to matching the row key literally, which is the exact state this table's header
    describes as the defect it was built to close."""
    rows = dict(RG.RULED_COMPONENTS)
    rows["dwpose_ts"] = rows.pop("dwpose")
    monkeypatch.setattr(RG, "RULED_COMPONENTS", rows)

    assert RG.orphaned_component_class_aliases() == ["dwpose"]
    with pytest.raises(RG.RouteGate, match=r"alias") as exc:
        RG.gate_alias_table()
    assert exc.value.evidence["orphaned"] == ["dwpose"]
    assert exc.value.evidence["clause"] == "orphaned_component_class_alias"

    # And a graph may not be verified while the table is orphaned — the detector tier the
    # aliases exist for would pass unseen.
    with pytest.raises(RG.RouteGate, match=r"alias"):
        RG.verify(graph(top=CLEAN_TOP))


def test_the_alias_table_is_checked_at_import_too():
    """The module-level derivation: a wrong table is loudest where every tool reads it,
    so the check runs at import as well as inside `verify`. Pinned behaviourally — the
    module imported, so it ran and returned."""
    import ast
    import inspect as _inspect

    src = _inspect.getsource(RG)
    calls = [n for n in ast.parse(src).body
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
             and getattr(n.value.func, "id", None) == "gate_alias_table"]
    assert len(calls) == 1, "the import-time call is the module-level one"
    assert RG.gate_alias_table()["verdict"].startswith("every alias key")


def test_a_row_with_no_alias_is_still_not_orphaned():
    """The green direction of the same reading: the table only ADDS aliases, so the many
    rows absent from it are matched on their own names and are not members of the orphan
    population."""
    assert set(RG.RULED_COMPONENTS) - set(RG.RULED_COMPONENT_CLASSES)
    assert RG.orphaned_component_class_aliases() == []
    assert RG.rulings_for_class("DWPreprocessor")[0]["matched_on"] == "dwpose"
