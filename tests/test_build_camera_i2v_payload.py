"""Wave 2's camera-held graph, against the ways wave 2 stops being wave 2.

Wave 1's defining property was an absence and its tests were mostly about absences. Wave 2
adds a PRESENCE that is optional at the socket level — `camera_conditions` — and an optional
socket is the more dangerous shape: a graph with the embedding built, gated, saved and
submitted but never CONNECTED generates a perfectly good video, passes Gate L, Gate S, Gate
ROUTE and the saved round trip, costs exactly the same, and differs from wave 1 only in the
prompt. The report would then credit a camera lever that never ran. Most of what is checked
here is that the lever is actually in the circuit, and that the things wave 2 holds constant
against wave 1 are held.
"""

import copy
import json
import os

import pytest

from conftest import TOOLS, REPO  # noqa: F401
import build_camera_i2v_payload as B
import build_i2v_payload as W1
from armature_core import route_gates as RG


UPLOADS = {"start_frame": "start.png"}
POS, NEG = "a jointed clay mannequin. He is dancing. Behind him, a bar.", "blurry"
E11_SEEDS = [2026081231, 2026081232, 2026081233]


def built(**kw):
    kw.setdefault("registry", E11_SEEDS)
    return B.build(UPLOADS, kw.pop("seed", E11_SEEDS[1]), kw.pop("negative", NEG),
                   kw.pop("positive", POS), kw.pop("registry"), **kw)


def w1_record(**over):
    """A stand-in for wave 1's committed payload record."""
    rec = {
        "experiment": "E11", "seed": 2026081231,
        "resolution": [832, 480], "length": 65,
        "start_image": {"server_name": "start.png"},
        "trajectory": {k: {"value": v["value"]} for k, v in W1.TRAJECTORY.items()},
        "positive": "wave one's positive, ending: The camera is static.",
    }
    rec.update(over)
    return rec


@pytest.fixture()
def w1_path(tmp_path):
    def _write(**over):
        p = tmp_path / "E11-probe-payload-record.json"
        p.write_text(json.dumps(w1_record(**over)), encoding="utf-8")
        return str(p)
    return _write


# ------------------------------------------------------------------ the lever is in circuit

def test_the_camera_embedding_is_actually_connected():
    """THE clause. `camera_conditions` is an OPTIONAL socket: an unwired embedding still
    builds, still gates, still generates, and differs from wave 1 only by the prompt."""
    wf, meta = built()
    assert wf["45"]["class_type"] == "WanCameraEmbedding"
    assert wf["50"]["inputs"]["camera_conditions"] == ["45", 0]
    assert meta["camera"]["camera_pose"] == "Static"


def test_an_unwired_camera_embedding_is_refused():
    wf, _ = built()
    del wf["50"]["inputs"]["camera_conditions"]
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "camera_conditions" in str(exc.value)
    assert "OPTIONAL" in str(exc.value)


def test_a_camera_embedding_that_is_present_but_feeds_nothing_is_refused():
    """The subtler shape of the same defect: the node exists, so a reader of the node list
    sees the lever, but its output goes nowhere."""
    wf, _ = built()
    wf["50"]["inputs"]["camera_conditions"] = ["45", 0]
    wf["46"] = copy.deepcopy(wf["45"])
    wf["50"]["inputs"]["camera_conditions"] = ["46", 0]
    wf["46"]["inputs"]["camera_pose"] = "Pan Left"
    # the wired one is no longer node 45, and the check names the node it requires
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "camera_conditions" in str(exc.value)


def test_the_pose_must_be_static_not_a_move():
    wf, _ = built()
    wf["45"]["inputs"]["camera_pose"] = "Zoom In"
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "holds the camera" in str(exc.value)


def test_the_camera_frame_matches_the_generated_frame():
    """`WanCameraEmbedding` defaults to length 81 and this route runs 65."""
    wf, _ = built()
    assert wf["45"]["inputs"]["length"] == wf["50"]["inputs"]["length"] == 65
    assert (wf["45"]["inputs"]["width"], wf["45"]["inputs"]["height"]) == (832, 480)
    ev = RG.verify(wf, frame=(832, 480, 65))
    assert ev["camera_agreement_verdict"] == "AGREES"


def test_a_camera_solved_for_the_nodes_default_length_is_caught_by_the_route_gate():
    wf, _ = built()
    wf["45"]["inputs"]["length"] = 81
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, frame=(832, 480, 65))
    assert "solved for a different frame" in str(exc.value)


# --------------------------------------------------- the performer is still uncontrolled

@pytest.mark.parametrize("cls", ["WanVaceToVideo", "WanAnimateToVideo",
                                 "Wan22FunControlToVideo", "ControlNetApplyAdvanced",
                                 "WanPhantomSubjectToVideo"])
def test_any_class_that_could_drive_the_performer_refuses_the_graph(cls):
    wf, _ = built()
    wf["99"] = {"class_type": cls, "inputs": {}}
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert cls in str(exc.value)


def test_the_camera_class_is_not_treated_as_performer_control():
    """The whole point of wave 2's re-drawn line — and the reason wave 1's builder is left
    alone rather than edited."""
    assert "WanCameraImageToVideo" in W1.CONTROL_CLASSES
    assert "WanCameraImageToVideo" not in B.PERFORMER_CONTROL_CLASSES
    assert "WanCameraEmbedding" not in B.PERFORMER_CONTROL_CLASSES


def test_a_second_uploaded_image_is_still_refused():
    wf, _ = built()
    wf["42"] = {"class_type": "LoadImage", "inputs": {"image": "reference.png"}}
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "second" in str(exc.value).lower()


def test_clip_vision_stays_absent():
    wf, _ = built()
    wf["50"]["inputs"]["clip_vision_output"] = ["44", 0]
    with pytest.raises(B.PayloadError) as exc:
        B.verify_topology(wf, "start.png")
    assert "clip_vision_output" in str(exc.value)


# ------------------------------------------------------------------- held constant vs wave 1

def test_the_trajectory_is_imported_not_retyped():
    """'Held constant against wave 1' is a property of the code here, not a claim."""
    wf, meta = built()
    assert meta["trajectory"] is W1.TRAJECTORY
    hi = wf["60"]["inputs"]
    assert (hi["steps"], hi["cfg"], hi["sampler_name"], hi["scheduler"]) == \
        (20, 3.5, "euler", "simple")
    assert wf["12"]["inputs"]["shift"] == 8.0
    assert (meta["resolution"], meta["length"], meta["fps"]) == ([832, 480], 65, 16)


def test_the_weights_are_wave_ones_weights():
    wf, meta = built()
    unets = sorted(n["inputs"]["unet_name"] for n in wf.values()
                   if n["class_type"] == "UNETLoader")
    assert unets == sorted([W1.UNET_HIGH, W1.UNET_LOW])
    assert meta["models"]["loras"] == []


def test_the_pin_passes_when_only_the_prompt_moved(w1_path):
    ev = B.pin_against_wave1("a different positive entirely", UPLOADS, 65, w1_path())
    assert ev["positive"]["differs"] is True
    assert all(v["agrees"] for v in ev["held_constant"].values())


def test_a_positive_identical_to_wave_ones_halts(w1_path):
    """The INVERTED check. A wave-2 build that quietly submitted wave 1's prompt would
    measure one lever while the report described two — and nothing else would notice."""
    same = w1_record()["positive"]
    with pytest.raises(B.PayloadError) as exc:
        B.pin_against_wave1(same, UPLOADS, 65, w1_path())
    assert "did not happen" in str(exc.value)


def test_a_different_start_frame_halts(w1_path):
    with pytest.raises(B.PayloadError) as exc:
        B.pin_against_wave1("new positive", {"start_frame": "other.png"}, 65, w1_path())
    assert "start_frame" in str(exc.value)


def test_a_different_length_halts(w1_path):
    with pytest.raises(B.PayloadError) as exc:
        B.pin_against_wave1("new positive", UPLOADS, 33, w1_path())
    assert "length" in str(exc.value)


def test_a_drifted_trajectory_halts(w1_path):
    drifted = {k: {"value": v["value"]} for k, v in W1.TRAJECTORY.items()}
    drifted["cfg"] = {"value": 6.0}
    with pytest.raises(B.PayloadError) as exc:
        B.pin_against_wave1("new positive", UPLOADS, 65, w1_path(trajectory=drifted))
    assert "trajectory" in str(exc.value)


# --------------------------------------------------------------------- the prompt surgery

def test_the_performance_clause_dominates_and_the_ratio_is_recorded():
    positive, log = B.build_prompt()
    d = log["dominance"]
    assert d["performance_words"] > d["set_dressing_words"] * B.PROMPT_DOMINANCE["min_ratio"]
    assert positive.index(B.PERFORMANCE_CLAUSE) < positive.index(B.SET_DRESSING_CLAUSE)


def test_a_prompt_whose_set_dressing_outweighs_the_performance_halts(monkeypatch):
    """The dispatch's instruction, made checkable. Wave 1's proportion was the defect."""
    monkeypatch.setattr(B, "SET_DRESSING_CLAUSE", B.PERFORMANCE_CLAUSE + " and more bar")
    with pytest.raises(B.PayloadError) as exc:
        B.build_prompt()
    assert "does not dominate" in str(exc.value)


def test_the_failed_camera_sentence_is_gone_from_the_positive():
    positive, log = B.build_prompt()
    assert B.CAMERA_SENTENCE_DROPPED not in positive
    assert log["dropped"]["sentence"] == B.CAMERA_SENTENCE_DROPPED


def test_the_identity_clause_is_carried_verbatim_from_its_own_source():
    positive, log = B.build_prompt()
    ident = log["carried_verbatim"]["identity_clause"]
    assert positive.startswith(ident)
    assert "clay" in ident


def test_the_negative_extension_records_what_was_already_there(tmp_path):
    src = tmp_path / "shared_config.py"
    src.write_text("sample_neg_prompt = '色调艳丽，画得不好的手部，畸形的，手指融合'",
                   encoding="utf-8")
    negative, log = B.build_negative(str(src))
    assert log["base_unedited"] is True
    assert set(log["hand_terms_already_present_in_base"]) == {
        "画得不好的手部", "畸形的", "手指融合"}
    assert all(t["term"] in negative for t in log["appended"])
    assert "attributed to this extension alone" in log["prior_recorded_before_the_run"]


# ------------------------------------------------------------------------- the taps and gates

def test_the_lossless_tap_and_gate_b_probe_survive():
    wf, _ = built()
    assert wf["71"]["inputs"]["images"] == ["70", 0]
    assert wf["41"]["inputs"]["images"] == ["40", 0]


def test_the_route_gate_runs_on_the_built_graph_with_the_frame_supplied():
    _, meta = built()
    assert meta["gate_ROUTE_built"]["frame_legality_verdict"] == "PROVEN"
    assert meta["gate_ROUTE_built"]["camera_agreement_verdict"] == "AGREES"


def test_an_unregistered_seed_halts():
    with pytest.raises(Exception) as exc:
        built(seed=12345)
    assert "seed" in str(exc.value).lower()


def test_the_record_names_the_route_change_rather_than_hiding_it():
    """A report calling wave 2 'the no-control route' would be describing wave 1."""
    _, meta = built()
    rc = meta["route_name_change"]
    assert rc["wave_1"] == "no control of any kind"
    assert "PERFORMER" in rc["wave_2"]
