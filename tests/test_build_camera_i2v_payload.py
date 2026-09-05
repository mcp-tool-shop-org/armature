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


def authored_start_frame(directory, name="w3_start.png", size=(B.WIDTH, B.HEIGHT)):
    """A real PNG on disk, written by the repo's own dependency-free writer.

    Carried from `tests/test_build_i2v_payload._authored_start_frame` — the sibling that
    already needed one. `resolve_start_frame` REFUSES a file whose IHDR it cannot read
    (wave 12, F-08853dfb), so a fixture standing in for the route's whole conditioning has
    to be an actual image rather than a handful of bytes beginning with the signature.
    """
    import numpy as np

    from armature_core import pngio

    path = os.path.join(str(directory), name)
    pngio.write_png(path, np.zeros((size[1], size[0], 3), dtype="uint8"))
    return path


_RESOLVED = {}


def resolved_start_frame(size=(B.WIDTH, B.HEIGHT)):
    """A resolved start frame at a given authored size, built once per size."""
    import tempfile

    if size not in _RESOLVED:
        d = tempfile.mkdtemp()
        _RESOLVED[size] = B.resolve_start_frame(
            authored_start_frame(d, f"start_{size[0]}x{size[1]}.png", size), None)
    return _RESOLVED[size]


def built(**kw):
    kw.setdefault("registry", E11_SEEDS)
    kw.setdefault("start_frame", resolved_start_frame())
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
    """The one property held against wave 1 — a property of the code, not a claim.

    This asserted object IDENTITY with `W1.TRAJECTORY` until E12 wave 3, which is directed
    to move cfg and sampler_name and so must be handed a copy. Identity was the mechanism,
    not the property: what has to stay true is that every value the graph runs is W1's own
    and none of it was retyped. The check is now field-by-field equality with W1 when
    nothing is overridden — which still fails the moment somebody hard-codes a number here,
    and which extends to the overridden case below, where identity could say nothing at all.
    The pin is re-pointed, not dropped.
    """
    wf, meta = built()
    assert meta["trajectory"] == W1.TRAJECTORY
    assert meta["trajectory_overrides"] == {}
    hi = wf["60"]["inputs"]
    assert (hi["steps"], hi["cfg"], hi["sampler_name"], hi["scheduler"]) == \
        (20, 3.5, "euler", "simple")
    assert wf["12"]["inputs"]["shift"] == 8.0


# ------------------------------------------------- the trajectory break (E12 wave 3's rung)

CATALOG = {"cfg": {"value": 6.0, "source": "catalog recommendation, re-read 2026-08-12"},
           "sampler_name": {"value": "uni_pc", "source": "catalog, same read"}}


def test_an_override_moves_exactly_the_named_fields_and_nothing_else():
    """The rung: cfg and sampler move, every other trajectory field stays W1's."""
    wf, meta = built(trajectory_overrides=CATALOG)
    hi, lo = wf["60"]["inputs"], wf["61"]["inputs"]
    assert (hi["cfg"], hi["sampler_name"]) == (6.0, "uni_pc")
    assert (lo["cfg"], lo["sampler_name"]) == (6.0, "uni_pc")
    assert (hi["steps"], hi["scheduler"], hi["start_at_step"], hi["end_at_step"]) == \
        (20, "simple", 0, 10)
    assert wf["12"]["inputs"]["shift"] == 8.0 == wf["13"]["inputs"]["shift"]
    for field in ("steps", "split_step", "shift", "scheduler", "fps"):
        assert meta["trajectory"][field] == W1.TRAJECTORY[field], (
            f"{field} drifted while only cfg and sampler were authorised to move")


def test_the_override_keeps_the_value_it_replaced():
    """A number with no history is indistinguishable from a typo a month later."""
    _, meta = built(trajectory_overrides=CATALOG)
    assert meta["trajectory"]["cfg"]["was"] == 3.5
    assert meta["trajectory"]["sampler_name"]["was"] == "euler"
    assert meta["trajectory_overrides"] == CATALOG


def test_an_override_that_changes_nothing_is_refused():
    """A break that did not happen is wave 2's failure shape — the report describes a lever
    that never moved, and every gate passes."""
    with pytest.raises(B.PayloadError) as exc:
        built(trajectory_overrides={"cfg": {"value": 3.5, "source": "x"}})
    assert "what it already was" in str(exc.value)


@pytest.mark.parametrize("field", ["steps", "split_step", "shift", "scheduler", "fps"])
def test_the_structural_fields_are_not_overridable(field):
    """Moving one of these makes the wave incomparable rather than informative, so the door
    is closed in code rather than in a docstring."""
    with pytest.raises(B.PayloadError) as exc:
        built(trajectory_overrides={field: {"value": 999, "source": "x"}})
    assert "structural" in str(exc.value)


def test_an_unknown_trajectory_field_is_refused():
    with pytest.raises(B.PayloadError,
                       match=r"'cfg_scale' is not a trajectory field"):
        built(trajectory_overrides={"cfg_scale": {"value": 6.0, "source": "x"}})


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
    """WAVE 8, F-e552e4e6 — two assertions were removed from here, not weakened.

    `ev["positive"]["differs"] is True` and `ev["trajectory"]["held_agrees"] is True`
    cannot be False in a RETURNED record: `ledger_against_wave1` appends to `problems`
    when `held != w1_held` and when the positive does not differ, and raises
    `PayloadError` if `problems` is non-empty BEFORE it returns `ev`.

    ⚠ RE-ANCHORED 2026-09-05 (wave 25): this paragraph cited three line numbers inside
    `ledger_against_wave1`, and two commits in one wave shifted all three. The citation is
    the SYMBOL now — `build_camera_i2v_payload::ledger_against_wave1` — which no edit above
    it moves. That is the form `test_amend_w16_core_solvers.stale_tests_citations` asks
    for, and the old numbers are dropped rather than re-measured a third time. So both lines took the same value when the ledger
    worked and when it did nothing at all. The clause they appeared to cover is pinned by
    the two refusal tests below, and `test_the_agreement_clauses_are_tautologies_on_the_
    returning_path` states the tautology as a fact about the function.

    What a returned record CAN still lose is the recorded quantities themselves — two
    hashes computed from the same string would leave `differs` True and the record
    useless — so those are what is asserted here.
    """
    ev = B.ledger_against_wave1("a different positive entirely", UPLOADS, 81, w1_path())
    # Wave 8, F-bc806f79: `positive.differs` and `trajectory.held_agrees` were assertions on
    # fields that could only ever read True in a record that reaches disk — replaced with
    # the values that vary. Asserting the two prompt hashes differ, and that the two sides
    # of the held comparison are equal, is the same claim on evidence that can go both ways.
    assert ev["positive"]["sha256_wave_3"] != ev["positive"]["sha256_wave_1"]
    assert ev["trajectory"]["held_this_wave"] == ev["trajectory"]["held_wave_1"]
    assert ev["trajectory"]["moved_on_purpose"] == []
    assert all(v["differs"] for v in ev["breaks_verified"].values())
    assert set(ev["deliberate_breaks"]) == {
        "weights", "length", "resolution", "start_frame_pixels"}


def test_the_ledger_lets_an_authorised_trajectory_break_through(w1_path):
    """E12's settings rung. cfg and sampler are named, so they are REQUIRED to differ from
    wave 1's; everything else in the trajectory is still required to match."""
    ev = B.ledger_against_wave1("a different positive entirely", UPLOADS, 81, w1_path(),
                                trajectory_overrides=CATALOG)
    assert ev["trajectory"]["moved_on_purpose"] == ["cfg", "sampler_name"]
    assert ev["trajectory"]["held_this_wave"] == ev["trajectory"]["held_wave_1"]
    assert "cfg" not in ev["trajectory"]["held_this_wave"]
    assert "moved on cfg, sampler_name" in ev["verdict"]


def test_a_byte_identical_positive_halts_the_wave(w1_path):
    """The clause `ev["positive"]["differs"] is True` appeared to cover, driven from the
    only direction that can fail it: hand the ledger wave 1's positive verbatim.

    The prompt surgery is one of two levers this wave claims to have moved. If the
    positive is byte-identical, the run measures the weight swap alone while the report
    describes two levers — which is wave 2's failure, one wave later.
    """
    with pytest.raises(B.PayloadError) as exc:
        B.ledger_against_wave1(w1_record()["positive"], UPLOADS, 81, w1_path())
    assert "byte-identical to wave 1's" in str(exc.value)
    assert "the prompt surgery did not happen" in str(exc.value).replace("\n", " ")


def test_a_wave_1_record_with_no_positive_at_all_halts_rather_than_comparing_nothing(
        w1_path):
    """The third state, and the one a `differs` boolean flattens: nothing to compare
    against is not the same answer as "these two differ"."""
    with pytest.raises(B.PayloadError,
                       match=r"wave 1's record carries no positive string to check"):
        B.ledger_against_wave1("a different positive entirely", UPLOADS, 81,
                               w1_path(positive=None))


def test_the_record_no_longer_carries_a_field_that_can_only_read_true(w1_path):
    """What F-e552e4e6 measured, resolved from BOTH sides at the wave-8 merge.

    The tests side (F-d945b60c) first pinned the two flags as tautologies — whenever
    `ledger_against_wave1` RETURNS, `positive.differs` and `trajectory.held_agrees` were True
    by construction, because the refusal happens first. The builders side (F-bc806f79) then
    DELETED both fields from the record, so the pin has no subject. What survives is the
    stronger claim: the record carries no field that can only read one way, and both paths
    that could have made either flag False still raise instead of returning.
    """
    ev = B.ledger_against_wave1("a different positive entirely", UPLOADS, 81, w1_path())
    assert "differs" not in ev["positive"], sorted(ev["positive"])
    assert "held_agrees" not in ev["trajectory"], sorted(ev["trajectory"])
    #: the two paths that could have made either flag False raise instead of returning
    with pytest.raises(B.PayloadError, match=r"byte-identical to wave 1"):
        B.ledger_against_wave1(w1_record()["positive"], UPLOADS, 81, w1_path())
    with pytest.raises(B.PayloadError,
                       match=r"a trajectory field this wave was NOT authorised to move"):
        B.ledger_against_wave1(
            "a different positive entirely", UPLOADS, 81,
            w1_path(trajectory={k: {"value": (v["value"] + 1
                                              if isinstance(v["value"], (int, float))
                                              and not isinstance(v["value"], bool)
                                              else v["value"])}
                                for k, v in W1.TRAJECTORY.items()}))


def test_an_unauthorised_trajectory_field_still_halts_the_wave(w1_path):
    """The andon's shape is unchanged: only the named fields may move. This is the clause
    that would catch a wave which moved the step split while claiming to move cfg."""
    with pytest.raises(B.PayloadError) as exc:
        B.ledger_against_wave1("a different positive entirely", UPLOADS, 81,
                               w1_path(trajectory=dict(
                                   w1_record()["trajectory"],
                                   steps={"value": 40})),
                               trajectory_overrides=CATALOG)
    assert "NOT authorised to move" in str(exc.value)


def test_a_declared_break_that_did_not_break_halts(w1_path):
    """Wave 2's failure shape, one experiment later: a report describing a lever that never
    moved, with every gate green."""
    with pytest.raises(B.PayloadError) as exc:
        B.ledger_against_wave1(
            "a different positive entirely", UPLOADS, 81,
            w1_path(trajectory=dict(w1_record()["trajectory"],
                                    cfg={"value": 6.0}, sampler_name={"value": "uni_pc"})),
            trajectory_overrides=CATALOG)
    assert "never moved" in str(exc.value)


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


import hashlib  # noqa: E402


# ------------------------------------------------------------------ the seed default


def test_omitting_the_seed_builds_on_the_first_registered_seed():
    """Wave 3, F-8898e2da. Gate S refuses a non-int before the fallback below it could
    ever run, so the documented optional --seed always halted."""
    _, meta = built(seed=None)
    assert meta["seed"] == sorted(E11_SEEDS)[0]
    assert meta["gate_S"]["seed_was_explicit"] is False


def test_omitting_the_seed_with_no_registry_names_the_missing_flag():
    with pytest.raises(B.PayloadError) as exc:
        built(seed=None, registry=None)
    assert "--seed" in str(exc.value)


# ------------------------------------------------------------------ the start frame hash
#
# Wave 3, F-d342f393. `--start-frame-sha256` defaulted to None and was threaded through
# `ledger_against_wave1` only to be STORED as ev["start_frame"]["wave_3_local_sha256"]. It
# appeared in no comparison and in no problems.append condition, so the sha256 of the
# re-authored start frame — the single load-bearing control input of an i2v route, and the
# artifact the alpha ruling governs — was an optional operator-typed string riding the
# record unverified, reading as null when omitted. CLAUDE.md requires every generation to
# record control-input hashes.


def test_the_start_frame_hash_is_computed_from_the_file_not_typed(tmp_path):
    f = tmp_path / "start.png"
    authored_start_frame(tmp_path, "start.png")
    ev = B.resolve_start_frame(str(f), None)
    assert ev["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest()
    assert ev["source"] == "hashed_in_tool"


def test_omitting_the_start_frame_raises(tmp_path):
    """A value nothing checks is worse than an absent one; the flag is now required and
    the tool reads the artifact rather than accepting a typed value."""
    with pytest.raises(B.PayloadError) as exc:
        B.resolve_start_frame(None, None)
    assert "--start-frame" in str(exc.value)


def test_a_declared_hash_that_disagrees_with_the_file_raises(tmp_path):
    """The mutation that proves the cross-check can fire: an operator-typed sha that is not
    the file's. Before this, a typed value was simply stored."""
    f = tmp_path / "start.png"
    authored_start_frame(tmp_path, "start.png")
    with pytest.raises(B.PayloadError) as exc:
        B.resolve_start_frame(str(f), "0" * 64)
    assert "does not hash to" in str(exc.value)


def test_a_declared_hash_that_agrees_is_recorded_as_confirmed(tmp_path):
    f = tmp_path / "start.png"
    authored_start_frame(tmp_path, "start.png")
    digest = hashlib.sha256(f.read_bytes()).hexdigest()
    ev = B.resolve_start_frame(str(f), digest)
    assert ev["source"] == "hashed_in_tool_and_confirmed_against_the_declared_value"


def test_a_missing_start_frame_file_raises(tmp_path):
    with pytest.raises(B.PayloadError, match=r"is not a file, so there is nothing to hash"):
        B.resolve_start_frame(str(tmp_path / "nope.png"), None)


# ------- the ledger's record carries values that can vary (wave 8, F-bc806f79)


def test_the_halt_carries_the_measurement_that_fired_it(w1_path):
    """`ev` was built, filled, and then NOT attached to the raise — `raise PayloadError(…)`
    took a message and nothing else — so the failing measurement never reached a record at
    all, while the passing one was written straight into `meta['gate_LEDGER_W3']`. The
    numbers are only interesting when the gate fires."""
    drifted = {k: {"value": v["value"]} for k, v in W1.TRAJECTORY.items()}
    drifted["cfg"] = {"value": 6.0}
    with pytest.raises(B.PayloadError, match=r"not the one the ruling describes") as exc:
        B.ledger_against_wave1("new positive", UPLOADS, 81, w1_path(trajectory=drifted))
    ev = exc.value.evidence
    assert ev["gate"] == "LEDGER_W3"
    assert ev["problems"], "the halt names no problem"
    assert ev["trajectory"]["held_this_wave"]["cfg"] != ev["trajectory"]["held_wave_1"]["cfg"]
    assert ev["trajectory"]["held_wave_1"]["cfg"] == 6.0


def test_the_record_carries_no_field_that_could_only_read_true(w1_path):
    """`ev['trajectory']['held_agrees'] = held == w1_held` and
    `ev['positive']['differs'] = isinstance(w1_pos, str) and w1_pos != positive` were both
    CONSTANT in any record that reaches disk: the very next clause appends a problem on the
    negation, and the function raises on any problem, so `ev` existed only when each read
    True. Both were written into the payload record as `meta['gate_LEDGER_W3']`, where a
    later session would read them as evidence a comparison was made. They are replaced by
    the values that vary — the two sides of the held comparison, beside the two prompt
    hashes that were already there."""
    ev = B.ledger_against_wave1("a different positive entirely", UPLOADS, 81, w1_path())
    assert "held_agrees" not in ev["trajectory"]
    assert "differs" not in ev["positive"]
    assert ev["trajectory"]["held_this_wave"] == ev["trajectory"]["held_wave_1"]
    assert ev["positive"]["sha256_wave_3"] != ev["positive"]["sha256_wave_1"]


def test_breaks_verified_differs_is_NOT_in_that_class(w1_path):
    """The boolean that is correctly a boolean and stays. Its problem clause is guarded by
    `theirs is not None`, so it can legitimately read False in a record that reaches disk —
    when wave 1's record lacks the key it is compared against. That is a comparison that
    can go both ways, which is exactly what the other two could not do."""
    ev = B.ledger_against_wave1("a different positive entirely", UPLOADS, 81,
                                w1_path(length=None))
    assert ev["breaks_verified"]["length"]["wave_1"] is None
    assert ev["breaks_verified"]["length"]["differs"] is True
    assert ev["breaks_verified"]["width"]["differs"] is True


def test_every_payload_error_in_this_tree_can_carry_its_evidence():
    """family: derived by AST over `tools/*.py` for a `class PayloadError` definition ->
    5 sites — build_animate_payload.py, build_camera_i2v_payload.py, build_i2v_payload.py,
    build_payload.py and, from wave 22, build_t2v_payload.py. All five take an optional
    evidence dict, so a halt in any of them can carry the measurement that fired it rather
    than a sentence alone.

    ⚠ RE-DERIVED with `==` (wave 22, builders, F-7e45e62b). `build_t2v_payload` declared no
    named andon of its own while `--tag` — a free string its own help says "goes in the
    written filenames" — was pasted into two written paths with no clause. The refusal has
    to name an andon rather than the bare base (wave-18 rule 3), so the class its three
    sibling builders already declare is declared there too: one wording, every builder.

    NOTE: four identical three-line `__init__`s is four implementations of one thing; the
    single one belongs beside `GateFailure` in `armature_core/errors.py`, which is
    core-gates' file. Recorded as an out-of-domain item rather than solved here.
    """
    import ast

    from conftest import TOOLS

    derived = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
        for node in ast.parse(src).body:
            if isinstance(node, ast.ClassDef) and node.name == "PayloadError":
                derived.append(name)
    assert derived == ["build_animate_payload.py", "build_camera_i2v_payload.py",
                       "build_i2v_payload.py", "build_payload.py",
                       "build_t2v_payload.py"], derived

    import importlib

    for name in derived:
        mod = importlib.import_module(name[:-3])
        err = mod.PayloadError("a message", {"gate": "X", "measured": 1})
        assert err.evidence == {"gate": "X", "measured": 1}, name
        # Wave 16, rule 5: the four `PayloadError.__init__`s are DELETED and the base's
        # inherited, so a bare-message refusal carries `None` where it carried `{}` -
        # `"evidence": null` beside `"gate": null` is the honest halt record for a refusal
        # that passed no receipt (`armature_core/errors.py`, the base's own docstring).
        assert mod.PayloadError("a message").evidence is None, name
        assert str(err) == "a message", name


# ------------------------------------------------- wave 12: the `start_image` block is MEASURED
# F-d979ec52. The payload record for E11 wave 3 — the provenance of a paid generation —
# stated in `start_image.fit` that the conditioning frame was "native — authored at 832x480,
# the same upload wave 1 ran", while the SAME record carried
# `DELIBERATE_BREAKS["resolution"] = wave_1 [832,480] -> wave_3 [1024,576]` and
# `DELIBERATE_BREAKS["start_frame_pixels"] = "1024x576, authored RGBA"`. Two fields of one
# record disagreed about the load-bearing conditioning input, and a reader who took the
# `fit` line would conclude the resolution correction did not happen — the exact failure
# `ledger_against_wave1` says it exists to refuse.
#
# The measurement that settles it already existed here (`png_header` / `resolve_start_frame`)
# and reached only `gate_ledger["start_frame"]["wave_3_local"]`. Measured by grep on
# 2026-09-04: `fit_agrees_with_the_file` occurred at build_i2v_payload.py:449 and NOWHERE in
# this module — the sibling that IMPORTS this module's `resolve_start_frame` carried the
# comparison and the module that owns the function did not.
#
# family: keyed on the RECORD FIELD (`meta["start_image"]`) of every builder whose graph
# conditions on one uploaded start image, via the two-module family
# `test_both_i2v_builders_declare_the_same_two_start_frame_flags` already derives from the
# parsers -> 2 sites: build_i2v_payload.py (had the comparison), build_camera_i2v_payload.py
# (asserted prose). One implementation now: `build_i2v_payload.start_image_record`, called by
# both. It lives in the sibling because this module imports that one at module scope
# (`import build_i2v_payload as W1`) and the reverse direction is a cycle.


def test_the_start_image_block_carries_the_files_own_measurement():
    start = built()[1]["start_image"]
    assert start["measured"]["width"] == B.WIDTH
    assert start["measured"]["height"] == B.HEIGHT
    assert start["sha256"] == resolved_start_frame()["sha256"]
    assert start["path"] == resolved_start_frame()["path"]
    assert start["fit_agrees_with_the_file"] is True


def test_a_start_frame_authored_at_wave_ones_resolution_is_REFUSED():
    """The mutation the block exists to catch, and the one that actually happened: wave 1's
    832x480 frame handed to a wave that generates at 1024x576. The prose `fit` line was
    unchanged by it.

    **Wave 14, F-e17613c2 — this test used to pin the non-refusal.** It read
    `assert start["fit_agrees_with_the_file"] is False` and let the build return: the
    comparison was computed into the record and read by no caller anywhere in the tree, so
    the wrong-sized frame — the whole of this route's conditioning — reached a paid
    generation with every printed gate line green. The comparison gates now, on both i2v
    builders, through the one `start_image_record` they share."""
    wrong = resolved_start_frame(size=(832, 480))
    with pytest.raises(W1.PayloadError, match=r"declares a NATIVE fit") as exc:
        built(start_frame=wrong)
    assert exc.value.evidence["clause"] == "fit_disagrees_with_the_file"
    assert exc.value.evidence["measured"] == [832, 480]
    assert exc.value.evidence["generation_frame"] == [B.WIDTH, B.HEIGHT]


def test_the_fit_sentence_names_THIS_waves_resolution_not_wave_ones():
    """The `fit` line said 832x480 in a record whose own `DELIBERATE_BREAKS` says the
    resolution moved to 1024x576."""
    meta = built()[1]
    fit = meta["start_image"]["fit"]
    assert f"{B.WIDTH}x{B.HEIGHT}" in fit
    assert "the same upload wave 1 ran" not in fit
    assert meta["resolution"] == [B.WIDTH, B.HEIGHT]


def test_build_refuses_to_emit_a_payload_with_no_resolved_start_frame():
    """The sibling's andon, carried: on a route whose start image is the whole of the
    conditioning, a record that cannot name its bytes is not a recipe. The clause lives
    inside `build`, not in `main`, so an in-process caller cannot route around it."""
    with pytest.raises(B.PayloadError, match="needs the resolved start frame"):
        B.build(UPLOADS, E11_SEEDS[2], NEG, POS, E11_SEEDS, start_frame=None)


def test_build_refuses_a_start_frame_whose_pixels_were_never_read():
    """The `None if not start_frame.get("image")` degradation, closed at both ends: the
    resolver refuses a file it could not open, and `build` refuses an evidence dict that
    carries no measurement, so `fit_agrees_with_the_file` can never be a null on the one
    input that most needs it."""
    unmeasured = dict(resolved_start_frame(), image=None)
    with pytest.raises(B.PayloadError, match="carries no measurement") as exc:
        B.build(UPLOADS, E11_SEEDS[2], NEG, POS, E11_SEEDS, start_frame=unmeasured)
    assert exc.value.evidence["andon"] == "start_frame"


def test_both_i2v_builders_read_the_start_image_block_through_ONE_implementation():
    """One implementation, named. Four copies of a three-line record shape is how the
    comparison came to exist in one of the two modules and not the other."""
    import ast

    from conftest import TOOLS

    callers = []
    for name in ("build_i2v_payload.py", "build_camera_i2v_payload.py"):
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            fn = node.func if isinstance(node, ast.Call) else None
            attr = getattr(fn, "attr", None) or getattr(fn, "id", None)
            if attr == "start_image_record":
                callers.append(name)
                break
    assert callers == ["build_i2v_payload.py", "build_camera_i2v_payload.py"], callers


# ------------------------------------ wave 12: a start frame that is not a PNG is REFUSED
# F-08853dfb. `png_header` returns None for anything without an IHDR, `resolve_start_frame`
# stored that as `image: None` with no clause, and `build`'s only start-frame requirement
# was `start_frame.get("sha256")` — so a 403-byte file with a JPEG header was ACCEPTED as
# the entire conditioning of an i2v route, `BUILD_I2V_OK` was printed, and the record's
# `fit` sentence stood unchallenged beside `fit_agrees_with_the_file: null`. Wave 10's
# stated purpose for opening the file was that `fit` "becomes a measurement instead of a
# claim"; on that input the measurement was absent and the claim survived.
#
# family: keyed on the RESOLVER both routes reach (this module's `resolve_start_frame`,
# which `build_i2v_payload.resolve_start_frame` carries) -> 1 implementation, 2 routes.


def test_a_start_frame_whose_IHDR_cannot_be_read_is_REFUSED(tmp_path):
    junk = tmp_path / "start.png"
    junk.write_bytes(bytes.fromhex("ffd8ffe0") + b"0123456789" * 40)   # a JPEG header
    with pytest.raises(B.PayloadError, match="is not a PNG this tool can read") as exc:
        B.resolve_start_frame(str(junk), None)
    ev = exc.value.evidence
    assert ev["path"] == os.path.abspath(str(junk))
    assert ev["first_8_bytes"] == junk.read_bytes()[:8].hex()
    assert ev["clause"] == "start_frame_not_a_png"


def test_a_file_too_short_to_hold_an_IHDR_is_REFUSED(tmp_path):
    """The shape wave 10's own fixtures used: the 8-byte signature and nothing else. The
    reader returns None for it, and returning None used to be the end of the matter."""
    stub = tmp_path / "start.png"
    stub.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"pixels")
    assert B.png_header(str(stub)) is None
    with pytest.raises(B.PayloadError, match="is not a PNG this tool can read"):
        B.resolve_start_frame(str(stub), None)


def test_the_refusal_reaches_the_OTHER_route_through_the_carried_resolver(tmp_path):
    """`build_i2v_payload` re-raises the sibling's refusal in its own family with the
    sibling named. The clause is one implementation and both routes are behind it."""
    junk = tmp_path / "start.png"
    junk.write_bytes(bytes.fromhex("ffd8ffe0") + b"not a png at all" * 8)
    with pytest.raises(W1.PayloadError, match="is not a PNG this tool can read") as exc:
        W1.resolve_start_frame(str(junk))
    assert exc.value.evidence["carried_from"] == (
        "build_camera_i2v_payload.resolve_start_frame")


def test_the_reader_still_declines_to_GUESS_and_the_RESOLVER_is_what_refuses(tmp_path):
    """The two jobs stay separate: `png_header` reports an absent measurement (None) rather
    than an invented one, and the refusal lives in the resolver, which is the function a
    route's conditioning actually passes through."""
    junk = tmp_path / "x.png"
    junk.write_bytes(b"this is not a png" * 4)
    assert B.png_header(str(junk)) is None
