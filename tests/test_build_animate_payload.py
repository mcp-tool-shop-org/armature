"""The Animate graph builder, against the ways a one-variable experiment stops being one.

The tool had no tests when E10 opened it; these ride the commit that parameterised it.
Nothing here touches the network, and `build` takes its prompts as arguments, so every
fixture is arithmetic on a dict.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import build_animate_payload as BAP
from armature_core import gates as G
from armature_core import route_gates as RG


UPLOADS_65 = {"reference": "ref.png", "pose_pack": "pack.png", "pose_frames": 65}
UPLOADS_81 = {"reference": "ref.png", "pose_pack": "pack.png", "pose_frames": 81}
POS, NEG = "a figure dancing in a bar", "blurry, low quality"
E08_SEEDS = [2026081211, 2026081212, 2026081213]
E10_SEEDS = [2026081221, 2026081222]


def e08():
    return BAP.build(UPLOADS_65, 2026081211, NEG, POS, E08_SEEDS, "letterbox")


def e10():
    return BAP.build(UPLOADS_81, 2026081221, NEG, POS, E10_SEEDS, "letterbox",
                     experiment="E10", length=81, fps=20.0)


# ------------------------------------------------------------------ the shot's shape

def test_the_e08_defaults_still_build_the_e08_shot():
    """The defaults are the banked shot: nothing about E10 moved them."""
    wf, meta = e08()
    assert (meta["resolution"], meta["length"], meta["fps"]) == ([832, 480], 65, 16)
    assert wf["49"]["inputs"]["length"] == 65
    assert wf["68"]["inputs"]["fps"] == 16
    assert meta["experiment"] == "E08"


def test_the_e10_shot_is_eighty_one_frames_at_true_tempo():
    wf, meta = e10()
    assert wf["49"]["inputs"]["length"] == 81
    assert wf["68"]["inputs"]["fps"] == 20.0
    assert meta["length"] == 81 and meta["fps"] == 20.0


def test_only_the_declared_variables_move_between_the_two_shots():
    """THE one-variable statement, checked mechanically rather than by reading the diff.

    E10 pins everything to E08 except the frame count, the seed, and the presentation rate
    that follows from the frame count. Anything else that moved would be a second variable
    nobody registered, and every gate would pass on it.
    """
    a, _ = e08()
    b, _ = e10()
    assert set(a) == set(b)
    moved = set()
    for nid in a:
        assert a[nid]["class_type"] == b[nid]["class_type"], nid
        for key in set(a[nid]["inputs"]) | set(b[nid]["inputs"]):
            if a[nid]["inputs"].get(key) != b[nid]["inputs"].get(key):
                moved.add(f"{nid}.{key}")
    assert moved == {
        "49.length",                # the experiment's variable
        "3.seed",                   # a new frame count is a new generation
        "68.fps",                   # presentation: the same dance, more samples
        "301.filename_prefix",      # server-side foldering, not a generation input
        "302.filename_prefix",
        "114.filename_prefix",
    }, sorted(moved)


def test_the_prompt_and_the_sampler_are_byte_identical_across_the_two_shots():
    a, ma = e08()
    b, mb = e10()
    assert a["6"]["inputs"]["text"] == b["6"]["inputs"]["text"]
    assert a["7"]["inputs"]["text"] == b["7"]["inputs"]["text"]
    assert ma["sampler"] == mb["sampler"]
    assert ma["models"] == mb["models"]
    for key in ("steps", "cfg", "sampler_name", "scheduler", "denoise"):
        assert a["3"]["inputs"][key] == b["3"]["inputs"][key]


# --------------------------------------------------------------- the pose-pack count

def test_a_pose_pack_of_the_wrong_length_halts():
    """The conditioning node pads a short pose video by repeating its last frame and
    truncates a long one, both silently — a freeze or an early ending, every gate green."""
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.build(UPLOADS_65, 2026081221, NEG, POS, E10_SEEDS, "letterbox",
                  experiment="E10", length=81, fps=20.0)
    assert "declares 65 frames and the shot is 81" in str(exc.value)


def test_the_e08_pack_still_fits_the_e08_shot():
    wf, _ = e08()
    assert wf["200"]["inputs"]["image"] == "pack.png"


# --------------------------------------------------------------------------- the gates

def test_gate_L_refuses_a_frame_count_off_the_four_n_plus_one_form():
    with pytest.raises(G.G1GeneratorLegality):
        BAP.build(dict(UPLOADS_81, pose_frames=80), 2026081221, NEG, POS, E10_SEEDS,
                  "letterbox", experiment="E10", length=80, fps=20.0)


def test_gate_ROUTE_runs_in_tool_on_the_graph_this_tool_built():
    _wf, meta = e10()
    ev = meta["gate_ROUTE_built"]
    assert ev["frame_legality_verdict"] == "PROVEN"
    lengths = {f["length"] for f in ev["frame_legality"]}
    assert lengths == {81}
    # both halves examined the same number: the node's own literal AND the stated frame
    assert {f["source"] for f in ev["frame_legality"]} == {"graph", "supplied"}


def test_gate_ROUTE_would_go_red_past_the_trained_horizon():
    """Gate L in `gates` checks the 4n+1 form; the 81-frame trained horizon lives only in
    the route gate, so 85 has to be refused THERE or it is refused nowhere."""
    with pytest.raises(RG.RouteGate) as exc:
        BAP.build(dict(UPLOADS_81, pose_frames=85), 2026081221, NEG, POS, E10_SEEDS,
                  "letterbox", experiment="E10", length=85, fps=20.0)
    assert "81-frame" in str(exc.value)


def test_gate_S_refuses_a_seed_the_committed_list_does_not_carry():
    with pytest.raises(G.GateSSeedRegistration):
        BAP.build(UPLOADS_81, 2026089999, NEG, POS, E10_SEEDS, "letterbox",
                  experiment="E10", length=81, fps=20.0)


def test_gate_S_refuses_any_chosen_seed_when_nothing_was_pre_registered():
    with pytest.raises(G.GateSSeedRegistration):
        BAP.build(UPLOADS_81, 2026081221, NEG, POS, None, "letterbox",
                  experiment="E10", length=81, fps=20.0)


# ------------------------------------------------------------------------- topology

def test_the_five_sockets_this_wave_leaves_empty_are_absent_not_null():
    wf, meta = e10()
    inp = wf["49"]["inputs"]
    for absent in ("background_video", "face_video", "character_mask",
                   "clip_vision_output", "continue_motion"):
        assert absent not in inp
        assert absent in meta["unconnected_inputs"]


def test_a_connected_background_video_is_refused():
    """It would make the scene-from-prompt clause unmeasurable, and nothing else looks."""
    wf, _ = e10()
    wf["49"]["inputs"]["background_video"] = ["200", 0]
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.verify_topology(wf)
    assert "background_video is connected" in str(exc.value)


def test_the_lossless_tap_reads_the_decoder_and_the_gate_B_probe_reads_the_pack():
    wf, _ = e10()
    assert wf["302"]["inputs"]["images"] == ["8", 0]
    assert wf["301"]["inputs"]["images"] == ["200", 0]
    assert wf["68"]["inputs"]["images"] == ["8", 0]


def test_a_sampler_fed_from_the_wrong_latent_is_refused():
    wf, _ = e10()
    wf["3"]["inputs"]["latent_image"] = ["8", 0]
    with pytest.raises(BAP.PayloadError):
        BAP.verify_topology(wf)


def test_a_link_to_a_node_that_does_not_exist_is_refused():
    wf, _ = e10()
    wf["8"]["inputs"]["samples"] = ["999", 0]
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.verify_topology(wf)
    assert "missing node 999" in str(exc.value)


def test_a_banned_preprocessor_tier_cannot_enter_the_graph():
    wf, _ = e10()
    wf["77"] = {"class_type": "DWPreprocessor", "inputs": {"image": ["200", 0]}}
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.verify_topology(wf)
    assert "DWPreprocessor" in str(exc.value)


def test_the_pack_and_the_reference_may_not_name_the_same_upload():
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.build({"reference": "same.png", "pose_pack": "same.png", "pose_frames": 81},
                  2026081221, NEG, POS, E10_SEEDS, "letterbox",
                  experiment="E10", length=81, fps=20.0)
    assert "same uploaded file" in str(exc.value)


def test_the_payload_hash_changes_with_the_frame_count_and_not_with_nothing():
    a, ma = e08()
    b, mb = e10()
    assert ma["payload_sha256"] != mb["payload_sha256"]
    _c, mc = e08()
    assert ma["payload_sha256"] == mc["payload_sha256"]


def test_the_negative_is_read_from_a_file_and_never_retyped(tmp_path):
    src = tmp_path / "shared_config.py"
    src.write_text("sample_neg_prompt = '色调艳丽，过曝'\n", encoding="utf-8")
    assert BAP.read_negative(str(src)) == "色调艳丽，过曝"


def test_a_config_with_no_negative_assignment_halts_rather_than_inventing_one(tmp_path):
    src = tmp_path / "shared_config.py"
    src.write_text("something_else = 1\n", encoding="utf-8")
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.read_negative(str(src))
    assert "not retyped from memory" in str(exc.value)
