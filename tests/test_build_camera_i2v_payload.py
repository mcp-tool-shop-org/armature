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


UPLOADS = {"start_frame": "w3_start.png"}
POS, NEG = "a jointed clay mannequin. He is dancing. Behind him, a bar.", "blurry"
E11_SEEDS = [2026081231, 2026081232, 2026081233]


def built(**kw):
    kw.setdefault("registry", E11_SEEDS)
    return B.build(UPLOADS, kw.pop("seed", E11_SEEDS[2]), kw.pop("negative", NEG),
                   kw.pop("positive", POS), kw.pop("registry"), **kw)


def w1_record(**over):
    """A stand-in for wave 1's committed payload record."""
    rec = {
        "experiment": "E11", "seed": 2026081231,
        "resolution": [832, 480], "length": 65,
        "start_image": {"server_name": "w1_start.png"},
        "models": {"unet_high_noise": W1.UNET_HIGH, "unet_low_noise": W1.UNET_LOW},
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
    wf, _ = built()
    assert wf["45"]["inputs"]["length"] == wf["50"]["inputs"]["length"] == 81
    assert (wf["45"]["inputs"]["width"], wf["45"]["inputs"]["height"]) == (1024, 576)
    ev = RG.verify(wf, frame=(1024, 576, 81))
    assert ev["camera_agreement_verdict"] == "AGREES"


def test_a_camera_solved_for_a_different_frame_is_caught_by_the_route_gate():
    """⚠ The andon's original motivating case has INVERTED and the fixture says so rather
    than quietly still passing: `WanCameraEmbedding` defaults to length 81, which was a
    mismatch when this route ran 65 and is now the number we want. The check still matters —
    any disagreement silently applies a trajectory solved for one clip to another — so the
    fixture now uses a real mismatch instead of the default that no longer is one."""
    assert 81 == B.LENGTH, "the node default and this route's length now coincide"
    wf, _ = built()
    wf["45"]["inputs"]["length"] = 65          # wave 1/2's length, now the wrong one
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, frame=(1024, 576, 81))
    assert "solved for a different frame" in str(exc.value)


def test_a_camera_solved_for_the_old_resolution_is_caught_too():
    wf, _ = built()
    wf["45"]["inputs"]["width"], wf["45"]["inputs"]["height"] = 832, 480
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, frame=(1024, 576, 81))
    assert exc.value.evidence["camera_agreement_verdict"] == "CONTRADICTED"


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
    """The one property held against wave 1 — a property of the code, not a claim."""
    wf, meta = built()
    assert meta["trajectory"] is W1.TRAJECTORY
    hi = wf["60"]["inputs"]
    assert (hi["steps"], hi["cfg"], hi["sampler_name"], hi["scheduler"]) == \
        (20, 3.5, "euler", "simple")
    assert wf["12"]["inputs"]["shift"] == 8.0


def test_the_divergence_from_the_catalogs_recommendation_is_recorded_not_hidden():
    """The catalog recommends cfg 6.0 / uni_pc for these exact files and this graph runs
    3.5 / euler. Marked ASSUMED rather than silently adopted or silently ignored."""
    _, meta = built()
    prem = meta["trajectory_premise"]
    assert prem["status"].startswith("ASSUMED")
    assert "uni_pc" in prem["the_divergence_recorded"]
    assert "6.0" in prem["the_divergence_recorded"]


def test_the_experts_are_the_camera_tier_not_the_i2v_base():
    """The correction, asserted on the graph rather than trusted from a docstring."""
    wf, meta = built()
    unets = sorted(n["inputs"]["unet_name"] for n in wf.values()
                   if n["class_type"] == "UNETLoader")
    assert unets == sorted([B.UNET_HIGH, B.UNET_LOW])
    assert all("fun_camera" in u for u in unets)
    assert W1.UNET_HIGH not in unets and W1.UNET_LOW not in unets
    assert meta["models"]["loras"] == []


def test_gate_pair_passes_on_the_built_graph():
    """The gate that would have stopped wave 2, run on what this builder now emits."""
    _, meta = built()
    pair = meta["gate_ROUTE_built"]["pairing"]
    assert pair["families_present"] == ["fun_camera"]
    assert "1 conditioning node(s) paired" in pair["verdict"]


def test_the_frame_is_derived_against_the_cards_tiers_not_inherited():
    wf, meta = built()
    assert (meta["resolution"], meta["length"], meta["fps"]) == ([1024, 576], 81, 16)
    assert wf["50"]["inputs"]["length"] == wf["45"]["inputs"]["length"] == 81
    assert wf["50"]["inputs"]["width"] == wf["45"]["inputs"]["width"] == 1024
    chosen = [c for c in meta["frame_derivation"]["candidates"] if c.get("chosen")]
    assert len(chosen) == 1 and chosen[0]["tier"] == 768
    assert chosen[0]["frame"] == [1024, 576]
    # the tier is hit exactly — that is the whole reason it was chosen
    assert chosen[0]["area"] == 768 * 768 == 1024 * 576


def test_the_derivation_records_that_waves_1_and_2_matched_no_tier():
    _, meta = built()
    assert meta["frame_derivation"]["waves_1_and_2_ran"]["frame"] == [832, 480]
    assert "matches NO tier" in meta["frame_derivation"]["waves_1_and_2_ran"]["note"]


def test_81_frames_is_legal_and_is_the_cards_trained_horizon():
    _, meta = built()
    assert meta["gate_L"]["profile"]["name"] == "wan-fun-camera"
    assert (81 - 1) % 4 == 0


def test_the_ledger_passes_when_the_breaks_broke_and_the_trajectory_held(w1_path):
    ev = B.ledger_against_wave1("a different positive entirely", UPLOADS, 81, w1_path())
    assert ev["positive"]["differs"] is True
    assert ev["trajectory"]["agrees"] is True
    assert all(v["differs"] for v in ev["breaks_verified"].values())
    assert set(ev["deliberate_breaks"]) == {
        "weights", "length", "resolution", "start_frame_pixels"}


def test_a_positive_identical_to_wave_ones_halts(w1_path):
    """Wave 2's INVERTED check, unchanged. The prompt surgery has still never been tested,
    so a build that quietly reverted it would measure the weight swap alone."""
    same = w1_record()["positive"]
    with pytest.raises(B.PayloadError) as exc:
        B.ledger_against_wave1(same, UPLOADS, 81, w1_path())
    assert "did not happen" in str(exc.value)


def test_a_length_that_did_not_move_halts(w1_path):
    """The ledger's own direction: a 'corrected' run that silently kept wave 1's 65 frames
    would ship a report describing a correction that did not happen."""
    with pytest.raises(B.PayloadError) as exc:
        B.ledger_against_wave1("new positive", UPLOADS, 65, w1_path())
    assert "still wave 1's" in str(exc.value)
    assert "length" in str(exc.value)


def test_reusing_wave_ones_start_frame_upload_halts(w1_path):
    """The old 832x480 baked-void frame cannot be the input to a 1024x576 graph, and the
    alpha law re-authors it regardless."""
    with pytest.raises(B.PayloadError) as exc:
        B.ledger_against_wave1("new positive", {"start_frame": "w1_start.png"}, 81,
                               w1_path())
    assert "wave 1's upload" in str(exc.value)


def test_the_experts_still_being_the_i2v_pair_halts(w1_path, monkeypatch):
    """THE clause wave 2 earned. If the swap silently did not happen, every other gate
    passes and the report describes a correction that is not in the graph."""
    monkeypatch.setattr(B, "UNET_HIGH", W1.UNET_HIGH)
    monkeypatch.setattr(B, "UNET_LOW", W1.UNET_LOW)
    with pytest.raises(B.PayloadError) as exc:
        B.ledger_against_wave1("new positive", UPLOADS, 81, w1_path())
    assert "plain I2V pair" in str(exc.value)


def test_a_drifted_trajectory_halts(w1_path):
    """The one property this wave holds; if it moved too, nothing would be comparable."""
    drifted = {k: {"value": v["value"]} for k, v in W1.TRAJECTORY.items()}
    drifted["cfg"] = {"value": 6.0}
    with pytest.raises(B.PayloadError) as exc:
        B.ledger_against_wave1("new positive", UPLOADS, 81, w1_path(trajectory=drifted))
    assert "trajectory" in str(exc.value)


# --------------------------------------------------------------------- the prompt surgery
#
# build_prompt() reads the twin's identity clause from facet's tree — a rig-local asset
# armature consumes read-only and never copies (a fixture copy would fork canon). On a
# runner without that tree these tests SKIP VISIBLY, the same convention ci.yml documents
# for the Blender-dependent suite: the skip count is the honest record of what the runner
# could not exercise.
import build_animate_payload as E08_SRC

requires_facet_tree = pytest.mark.skipif(
    not os.path.isfile(E08_SRC.TWIN_PROMPT_JSON),
    reason="rig-local facet asset (E33 twin prompt JSON) not present on this runner",
)


@requires_facet_tree
def test_the_performance_clause_dominates_and_the_ratio_is_recorded():
    positive, log = B.build_prompt()
    d = log["dominance"]
    assert d["performance_words"] > d["set_dressing_words"] * B.PROMPT_DOMINANCE["min_ratio"]
    assert positive.index(B.PERFORMANCE_CLAUSE) < positive.index(B.SET_DRESSING_CLAUSE)


@requires_facet_tree
def test_a_prompt_whose_set_dressing_outweighs_the_performance_halts(monkeypatch):
    """The dispatch's instruction, made checkable. Wave 1's proportion was the defect."""
    monkeypatch.setattr(B, "SET_DRESSING_CLAUSE", B.PERFORMANCE_CLAUSE + " and more bar")
    with pytest.raises(B.PayloadError) as exc:
        B.build_prompt()
    assert "does not dominate" in str(exc.value)


@requires_facet_tree
def test_the_failed_camera_sentence_is_gone_from_the_positive():
    positive, log = B.build_prompt()
    assert B.CAMERA_SENTENCE_DROPPED not in positive
    assert log["dropped"]["sentence"] == B.CAMERA_SENTENCE_DROPPED


@requires_facet_tree
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


# --------------------------------------------------------------------- the wave label

def test_the_wave_label_follows_the_caller_and_is_not_a_baked_constant():
    """E12 reuses this builder, and `WAVE = 3` was a module literal.

    Left baked, it would have written a `"wave": 3` field and cloud output prefixes under
    `E12/w3/` for a run that is not wave 3 of anything — plausible labels pointing at the
    wrong run, which is the defect `make_gate0_sheet` was stripped of on its third stale-label
    sighting. The prefixes matter most: they name directories on the server that later runs
    read frames back out of.
    """
    _, meta = built(experiment="E12", wave=2)
    assert meta["wave"] == 2
    assert meta["experiment"] == "E12"

    wf, _ = built(experiment="E12", wave=2)
    prefixes = [n["inputs"]["filename_prefix"] for n in wf.values()
                if isinstance(n, dict) and isinstance(n.get("inputs"), dict)
                and "filename_prefix" in n["inputs"]]
    assert prefixes, "the graph writes nothing — the fixture is no longer exercising this"
    for p in prefixes:
        assert "w3" not in p, f"a wave-3 literal survived into {p!r}"
    assert any("E12/w2/" in p for p in prefixes)


def test_the_default_wave_is_still_the_one_the_shipped_run_used():
    """The label is now a parameter; the run that already happened must keep its name."""
    _, meta = built()
    assert meta["wave"] == B.WAVE == 3
