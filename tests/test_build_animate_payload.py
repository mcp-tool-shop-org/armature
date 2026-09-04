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
    with pytest.raises(G.G1GeneratorLegality,
                       match=r"\[G1\] frame is not legal for generator 'wan-animate'"):
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
    with pytest.raises(G.GateSSeedRegistration,
                       match=r"\[S\] seed 2026089999 is not in E10's pre-registered list"):
        BAP.build(UPLOADS_81, 2026089999, NEG, POS, E10_SEEDS, "letterbox",
                  experiment="E10", length=81, fps=20.0)


def test_gate_S_refuses_any_chosen_seed_when_nothing_was_pre_registered():
    with pytest.raises(G.GateSSeedRegistration,
                       match=r"\[S\] E10 has no pre-registered seed list, so its seed may"):
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
    with pytest.raises(BAP.PayloadError,
                       match=r"sampler does not take the conditioning node's latent"):
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


# ------------------------------------------------------------------ the seed default
#
# Wave 3, F-8898e2da. `seed_used = seed if seed is not None else (sorted(registry)[0] if
# registry else 0)` sat BELOW Gate S, which refuses a non-int first. Measured:
# `gates.gate_s_seed_registration(None, [2026081201, 2026081202], "E08",
# seed_was_explicit=False)` raises "[S] seed must be an int, got NoneType", with or without
# a registry — so the fallback was dead code and the documented invocation
# (`[--seed=2026081201]`, i.e. optional) always halted. The dead `else 0` branch was worse
# than dead: it read as a working default and would have silently picked seed 0 if the
# ordering were ever changed.


def test_omitting_the_seed_builds_on_the_first_registered_seed():
    """The invocation the usage block documents. It halted on a message about NoneType."""
    wf, meta = BAP.build(UPLOADS_65, None, NEG, POS, E08_SEEDS, "letterbox")
    assert meta["seed"] == sorted(E08_SEEDS)[0]
    assert wf["3"]["inputs"]["seed"] == sorted(E08_SEEDS)[0]
    assert meta["gate_S"]["seed_was_explicit"] is False


def test_omitting_the_seed_with_no_registry_names_the_missing_flag():
    """The other half: with no registry there is no committed number to default to, and
    Gate S refuses a varied one. The halt must say THAT rather than 'got NoneType'."""
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.build(UPLOADS_65, None, NEG, POS, None, "letterbox")
    assert "--seed" in str(exc.value)
    assert "--seeds-registry" in str(exc.value)


def test_the_zero_fallback_is_gone():
    """`else 0` would have shipped an unregistered seed the moment the ordering changed.

    Read off the executable lines only — the comment above the fix quotes the old
    expression on purpose, and a substring check over the whole source would be a check
    that fires on its own documentation."""
    import inspect

    code = [ln.split("#", 1)[0] for ln in inspect.getsource(BAP.build).splitlines()]
    assert "else 0" not in " ".join(code)


# ------------------------------ the upload map's keys, named (wave 6, F-ec05d8dc)


@pytest.mark.parametrize("key", ["pose_pack", "reference", "pose_frames"])
def test_an_upload_map_missing_a_key_names_the_key_rather_than_raising_keyerror(key):
    """`uploads["pose_pack"]` and `uploads["reference"]` were indexed with no guard, so an
    upload map missing either produced a bare `KeyError: 'pose_pack'` naming neither the
    file nor the flag — on the E08 Animate route, where the pose pack IS the conditioning.
    The adjacent `uploads.get("pose_frames")` was worse in a quieter way: its absence
    surfaced as "the pose pack declares None frames and the shot is 81", a message about a
    COUNT standing in for a missing key. `build_i2v_payload:476` and
    `build_camera_i2v_payload:971` guard the same shape explicitly, and the fix was never
    carried to the tool the other two were derived from."""
    missing = {k: v for k, v in UPLOADS_81.items() if k != key}
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.build(missing, 2026081221, NEG, POS, E10_SEEDS, "letterbox",
                  experiment="E10", length=81, fps=20.0)
    assert key in str(exc.value)
    assert exc.value.evidence["key"] == key


def test_a_complete_upload_map_still_builds():
    """The mutation that must NOT fire it."""
    wf, _ = e10()
    assert wf["200"]["inputs"]["image"] == "pack.png"
    assert wf["134"]["inputs"]["image"] == "ref.png"


def test_a_wrong_frame_count_still_reports_a_count_not_a_missing_key():
    """The two messages stay distinguishable: a key that IS there and disagrees is a count
    problem, and it must not be reported as an absence."""
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.build(dict(UPLOADS_81, pose_frames=65), 2026081221, NEG, POS, E10_SEEDS,
                  "letterbox", experiment="E10", length=81, fps=20.0)
    assert "declares 65 frames" in str(exc.value)


def test_main_names_the_file_beside_the_key(tmp_path):
    """The message shape build_i2v_payload already uses: name the file, name the key."""
    import json

    up = tmp_path / "uploads.json"
    up.write_text(json.dumps({"reference": "ref.png", "pose_frames": 81}),
                  encoding="utf-8")
    neg = tmp_path / "neg.yaml"
    neg.write_text("sample_neg_prompt: 'blurry'\n", encoding="utf-8")
    with pytest.raises(BAP.PayloadError) as exc:
        BAP.main(["--uploads", str(up), "--out", str(tmp_path / "fresh"),
                  "--negative-source", str(neg), "--subject", "BLACKGUARD", "--no-canon"])
    assert "pose_pack" in str(exc.value)
    assert str(up) in str(exc.value)
    assert not (tmp_path / "fresh").exists()

import json


# ---- the identity drop matches a WORD, not a substring (wave 8, routed from core-gates)


def _twin(tmp_path, entry):
    p = tmp_path / "twin.json"
    p.write_text(json.dumps({"_entry_verbatim": entry}), encoding="utf-8")
    return str(p)


def test_a_recorded_drop_removes_the_phrase_and_its_adjoining_comma(tmp_path):
    """The mutation that must NOT change: the two phrases E08 actually drops come out, and
    the surrounding clause reads as prose."""
    text, original, log = BAP.identity_clause(_twin(
        tmp_path,
        "A knight in dark plate, plain pale grey background, soft studio light, "
        "heavy cloak."))
    assert text == "A knight in dark plate, heavy cloak."
    assert [row["dropped"] for row in log] == [p for p, _ in BAP.IDENTITY_DROPS]
    assert "plain pale grey background" in original


def test_a_drop_phrase_that_is_only_a_SUBSTRING_is_refused(tmp_path, monkeypatch):
    """Routed from core-gates (F-138c009c's family): `phrase not in text` followed by
    `text.replace(", " + phrase, "").replace(phrase + ", ", "")` is a bare substring edit
    with no word boundary — the same class core-gates closed in `canon._find_phrase`, where
    'cape' matched inside 'landscape'. Short single-word phrases (cape, helm, arm, hood,
    mask) are exactly the form a drop is written with, and a drop that cut a hole in the
    middle of an unrelated word would still be recorded in the change log as a clean drop.

    The locator is `canon._find_phrase` — core-gates' ONE matcher, called rather than
    re-implemented — so the boundary rule arrives with that module.

    SEAM: on a tree where `_find_phrase` is still the bare `haystack.find(...)` this test is
    the pin that says so.
    """
    monkeypatch.setattr(BAP, "IDENTITY_DROPS", [("cape", "a short occupant phrase")])
    with pytest.raises(BAP.PayloadError, match=r"as a whole phrase"):
        BAP.identity_clause(_twin(tmp_path, "A figure against a wide landscape, lit warmly."))


def test_the_drop_still_fires_when_the_phrase_IS_a_whole_word(tmp_path, monkeypatch):
    """The other half of the same clause: the boundary must not stop a real match."""
    monkeypatch.setattr(BAP, "IDENTITY_DROPS", [("cape", "a short occupant phrase")])
    text, _original, log = BAP.identity_clause(_twin(
        tmp_path, "A figure in a long cape, against a wide landscape."))
    assert text == "A figure in a long against a wide landscape."
    assert log == [{"dropped": "cape", "reason": "a short occupant phrase"}]


def test_the_missing_drop_halt_carries_its_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(BAP, "IDENTITY_DROPS", [("helm", "a short occupant phrase")])
    with pytest.raises(BAP.PayloadError, match=r"as a whole phrase") as exc:
        BAP.identity_clause(_twin(tmp_path, "A figure with no headgear at all."))
    assert exc.value.evidence["phrase"] == "helm"
    assert len(exc.value.evidence["clause_sha256"]) == 64


def test_the_phrase_matcher_is_canons_and_not_a_second_one():
    """family: derived by AST over `tools/*.py` for a `str.replace` call whose argument is
    built from a phrase constant -> 1 site — tools/build_animate_payload.py:251 (now
    removed). The locator this file uses is `armature_core.canon._find_phrase`, the same
    object `canon.cover` and `canon.residue` search with."""
    from armature_core import canon as C

    assert BAP.C is C
    assert BAP.C._find_phrase is C._find_phrase
