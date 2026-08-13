"""The composed route's andons — E13's re-arm.

This is the graph that spends money, so every fixture here is about a defect that would
have cost credits and left the record looking correct:

* an unregistered seed — every gate green, and the number in the report belongs to no
  committed list;
* two billable nodes — one submission, two charges, against a ceiling counted per
  submission;
* an illegal enum on a hosted tier — the pixel clause of Gate L cannot see it, because
  this tier never receives a pixel dimension;
* a seed the SAVE format lets randomise — the number in the record is not the number that
  runs, and Gate S can only see it because `SEED_NODES` now names the class. The E13 halt
  report measured that table reporting "0 noise-bearing seed(s), all pinned" on this tier
  having checked nothing; `test_gate_s_is_not_vacuous_on_this_tier` is the pin against
  that returning.
"""

import json

import pytest

import build_cascade_payload as CASCADE
import build_r2v_payload as B
from armature_core import route_gates as RG


PROMPT = "character1 walks forward a few steps and turns the head over one shoulder."
NEG = "blurry, low quality, extra limbs, text overlay"
REFS = [f"{i:064x}.png" for i in range(4)]
SEEDS = [2026081351, 2026081352]


def _a1(seed=SEEDS[0], **kw):
    wf, _ = B.build(arm="A1", seed=seed, prompt=PROMPT, negative=NEG, refs=REFS, **kw)
    return wf


def _a2(seed=SEEDS[0], n=81, **kw):
    names = [f"{i:064x}.png" for i in range(n)]
    wf, ids = B.build(arm="A2", seed=seed, prompt=PROMPT, negative=NEG,
                      upload_names=names, **kw)
    return wf, ids


# ------------------------------------------------------------------ the payload shape


def test_a1_wires_four_reference_image_slots_in_order():
    wf = _a1()
    inp = wf[str(B.R2V_ID)]["inputs"]
    assert [k for k in inp if k.startswith("model.reference_")] == [
        "model.reference_images.image1", "model.reference_images.image2",
        "model.reference_images.image3", "model.reference_images.image4"]
    for i in range(4):
        nid = str(B.FIRST_IMAGE_ID + i)
        assert inp[f"model.reference_images.image{i + 1}"] == [nid, 0]
        assert wf[nid]["inputs"]["image"] == REFS[i]


def test_a1_carries_no_video_slot_and_a2_carries_no_image_slot():
    """The one variable between the arms, pinned as a test so a builder change cannot
    quietly make it two."""
    a1 = _a1()["500"]["inputs"]
    a2 = _a2()[0]["500"]["inputs"]
    assert not any(k.startswith("model.reference_videos") for k in a1)
    assert not any(k.startswith("model.reference_images") for k in a2)


def test_a2_feeds_the_slot_from_create_video_not_from_an_upload():
    """No video is uploaded anywhere: E02 and the E13 halt both measured that no video
    loader exists on this API surface. The VIDEO is constructed in-graph."""
    wf, ids = _a2()
    inp = wf[str(B.R2V_ID)]["inputs"]
    assert inp["model.reference_videos.video1"] == [str(CASCADE.VIDEO_ID), 0]
    assert wf[str(CASCADE.VIDEO_ID)]["class_type"] == "CreateVideo"
    assert ids["create_video"] == str(CASCADE.VIDEO_ID)
    assert not any(n["class_type"] == "LoadVideo" for n in wf.values())


def test_a2_drops_the_cascades_own_save_so_only_the_generation_is_saved():
    """The cascade's SaveVideo would write the REFERENCE to disk and, worse, make the
    graph's output ambiguous: two save nodes, two videos, and a report that has to guess
    which one the tier produced."""
    wf, _ = _a2()
    saves = [nid for nid, n in wf.items() if n["class_type"] == "SaveVideo"]
    assert saves == [str(B.SAVE_ID)]
    assert wf[str(B.SAVE_ID)]["inputs"]["video"] == [str(B.R2V_ID), 0]


def test_both_arms_pin_the_same_common_fields():
    a1 = _a1()["500"]["inputs"]
    a2 = _a2()[0]["500"]["inputs"]
    for k in ("model", "model.prompt", "model.negative_prompt", "model.resolution",
              "model.ratio", "model.duration", "seed", "watermark"):
        assert a1[k] == a2[k], k
    assert a1["watermark"] is False
    assert a1["model"] == "wan2.7-r2v"


def test_the_seed_is_a_literal_so_it_reads_as_pinned_in_api_format():
    wf = _a1()
    found = RG.seeds(wf)
    assert len(found) == 1
    assert found[0]["class"] == "Wan2ReferenceVideoApi"
    assert found[0]["seed"] == SEEDS[0] and found[0]["pinned"] is True


def test_gate_s_is_not_vacuous_on_this_tier():
    """The halt report's measured defect: with the class absent from SEED_NODES,
    `gate_s_registration` reported '0 noise-bearing seed(s), all pinned' having examined
    nothing. It must now FIND the seed, and must refuse one that is not registered."""
    wf = _a1()
    assert RG.gate_s_registration(wf, SEEDS)["seeds"], "Gate S found no seed to check"
    with pytest.raises(RG.RouteGate):
        RG.gate_s_registration(wf, [1234567890])


def test_a_seed_arriving_over_a_link_is_not_pinned():
    """The API-format meaning of pinned: a literal. A seed computed by another node is a
    number no committed list could have registered."""
    wf = _a1()
    wf["500"]["inputs"]["seed"] = ["999", 0]
    assert RG.seeds(wf)[0]["pinned"] is False


# ------------------------------------------------------------------ Gate S at build time


def test_an_unregistered_seed_raises_before_anything_is_submitted():
    with pytest.raises(RG.RouteGate) as exc:
        B.gate_seed_registered(1111111111, SEEDS)
    assert "not on the committed registration" in str(exc.value)


def test_a_registered_seed_passes():
    assert B.gate_seed_registered(SEEDS[1], SEEDS)["verdict"]


# ------------------------------------------------------------------ the ceiling gate


def test_two_billable_nodes_raise_because_the_ceiling_counts_per_submission():
    wf = _a1()
    wf["502"] = {"class_type": "Wan2ReferenceVideoApi", "inputs": dict(wf["500"]["inputs"])}
    with pytest.raises(RG.RouteGate) as exc:
        B.gate_one_paid_node(wf)
    assert "one charge per submission" in str(exc.value)


def test_zero_billable_nodes_also_raises():
    """Both directions: a graph that lost its generator would run, cost nothing, save
    nothing useful, and read as a completed submission in the ledger."""
    wf = _a1()
    del wf["500"]
    with pytest.raises(RG.RouteGate):
        B.gate_one_paid_node(wf)


def test_one_billable_node_passes_on_both_arms():
    assert B.gate_one_paid_node(_a1())["n_paid"] == 1
    assert B.gate_one_paid_node(_a2()[0])["n_paid"] == 1


# ------------------------------------------------------------------ Gate L, hosted


def test_the_pinned_frame_is_legal_for_the_tier():
    ev = RG.hosted_frame_legality("720P", "16:9", 5, "wan2.7-r2v")
    assert ev["legal"] and ev["problems"] == []


@pytest.mark.parametrize("res,ratio,dur,needle", [
    ("768P", "16:9", 5, "resolution"),
    ("720P", "21:9", 5, "ratio"),
    ("720P", "16:9", 1, "outside 2..10"),
    ("720P", "16:9", 11, "outside 2..10"),
    ("720P", "16:9", 5.5, "not an integer"),
])
def test_each_illegal_enum_value_is_named(res, ratio, dur, needle):
    ev = RG.hosted_frame_legality(res, ratio, dur, "wan2.7-r2v")
    assert not ev["legal"]
    assert any(needle in p for p in ev["problems"]), ev["problems"]


def test_an_unknown_tier_raises_rather_than_passing_vacuously():
    with pytest.raises(RG.RouteGate):
        RG.hosted_frame_legality("720P", "16:9", 5, "wan9.9-nonexistent")


def test_verify_refuses_a_frame_and_a_hosted_tier_together():
    """Two answers to one question; one of them would be the number nobody checked."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_a1(), hosted_tier="wan2.7-r2v", frame=(1024, 576, 81))
    assert "two answers to the same question" in str(exc.value)


def test_hosted_tier_is_not_a_skip_flag_an_illegal_enum_still_raises():
    wf = _a1()
    wf["500"]["inputs"]["model.duration"] = 42
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, hosted_tier="wan2.7-r2v")
    assert "Gate L (hosted tier)" in str(exc.value)


def test_hosted_tier_on_a_graph_with_no_such_node_raises_rather_than_passing():
    """The vacuous state this argument exists to remove: neither clause could decide
    anything, and the graph would come back green."""
    wf = {"1": {"class_type": "LoadImage", "inputs": {"image": "x.png"}}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, require_pinned_seeds=False, hosted_tier="wan2.7-r2v")
    assert "nothing to decide in EITHER clause" in str(exc.value)


def test_hosted_tier_on_a_graph_that_does_pin_a_latent_raises():
    """If a graph carries a pixel latent, calling it a hosted tier would leave the pixel
    clause unchecked. One of the two claims is wrong and the gate says so."""
    wf = _a1()
    wf["600"] = {"class_type": "EmptyHunyuanLatentVideo",
                 "inputs": {"width": 1024, "height": 576, "length": 81, "batch_size": 1}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(wf, hosted_tier="wan2.7-r2v")
    assert "latent-sizing node" in str(exc.value)


def test_the_verdict_says_inapplicable_rather_than_proven():
    ev = RG.verify(_a1(), hosted_tier="wan2.7-r2v")
    assert ev["frame_legality_verdict"].startswith("INAPPLICABLE")
    assert ev["hosted_frame_legality"]["legal"] is True
    assert "receives no width" in ev["frame_legality_inapplicable_reason"]


def test_hosted_enums_read_the_same_values_in_both_formats():
    """API format reads them by field name; SAVE format has no field names at all and must
    read them positionally. Disagreement here is the off-by-one the whole table exists for."""
    api = _a1()
    _, res_a, ratio_a, dur_a = RG.hosted_enums(api)
    saved = {"nodes": [{"id": 500, "type": "Wan2ReferenceVideoApi",
                        "widgets_values": ["wan2.7-r2v", PROMPT, NEG, "720P", "16:9", 5,
                                           SEEDS[0], "fixed", False]}]}
    _, res_s, ratio_s, dur_s = RG.hosted_enums(saved)
    assert (res_a, ratio_a, dur_a) == (res_s, ratio_s, dur_s) == ("720P", "16:9", 5)


def test_the_save_format_widget_row_puts_watermark_after_the_control_insertion():
    """`control_after_generate` is inserted at 7, so `watermark` is at 8 and not the 7 a
    positional zip would give it. Read off the converted file, 2026-08-13."""
    import gate_saved_graph as GS

    row = GS.WIDGET_INDEX["Wan2ReferenceVideoApi"]
    assert row["seed"] == 6 and row["watermark"] == 8
    assert RG.SEED_NODES["Wan2ReferenceVideoApi"]["seed"] == row["seed"]
    assert RG.SEED_NODES["Wan2ReferenceVideoApi"]["control"] == 7
    assert RG.HOSTED_ENUM_WIDGETS["Wan2ReferenceVideoApi"]["duration"] == row["model.duration"]


def test_a_randomising_seed_in_save_format_is_refused_however_concrete_it_looks():
    """The save-format meaning of pinned. This is what the class being absent from
    SEED_NODES used to hide."""
    saved = {"nodes": [{"id": 500, "type": "Wan2ReferenceVideoApi",
                        "widgets_values": ["wan2.7-r2v", PROMPT, NEG, "720P", "16:9", 5,
                                           SEEDS[0], "randomize", False]}]}
    found = RG.seeds(saved)
    assert found[0]["pinned"] is False
    with pytest.raises(RG.RouteGate):
        RG.gate_s_registration(saved, SEEDS)


def test_the_pixel_clause_would_have_been_a_category_error_here():
    """Why this clause exists at all. Gate L's `wan` rules ask whether a width is a
    multiple of 16 and a length is 4n+1. This tier never receives either, so the pixel
    clause on an r2v graph decides nothing — the vacuous shape the halt report recorded."""
    wf = _a1()
    assert RG.latents(wf) == [], "an r2v graph pins no latent for the pixel clause to read"


# ------------------------------------------------------------------ end to end


def _files(tmp_path, uploads=None):
    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps({"seeds": SEEDS}), encoding="utf-8")
    prompt = tmp_path / "prompt.json"
    prompt.write_text(json.dumps({"prompt": PROMPT, "negative_prompt": NEG}),
                      encoding="utf-8")
    refs = tmp_path / "refs.json"
    refs.write_text(json.dumps({"views": [
        {"slot": f"image{i + 1}", "view": f"turn_{i}", "upload_name": REFS[i]}
        for i in range(4)]}), encoding="utf-8")
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads or {f"{i:05d}.png": f"{i:064x}.png"
                                         for i in range(81)}), encoding="utf-8")
    return seeds, prompt, refs, up


def test_a1_end_to_end_writes_the_full_payload_and_the_slot_order(tmp_path):
    seeds, prompt, refs, _ = _files(tmp_path)
    out = tmp_path / "route"
    _, rec = B.main([f"--arm=A1", f"--seed={SEEDS[0]}", f"--seeds={seeds}",
                     f"--prompt-file={prompt}", f"--refs={refs}", f"--out={out}"])
    assert rec["payload"]["model.duration"] == 5
    assert rec["payload"]["watermark"] is False
    assert rec["slot_order"] == [f"model.reference_images.image{i}" for i in range(1, 5)]
    assert "NOT VISIBLE" in rec["slot_binding_note"]
    written = json.loads(
        (out / f"E13-A1-seed{SEEDS[0]}-payload-record.json").read_text(encoding="utf-8"))
    assert written["payload"]["model.prompt"] == PROMPT
    assert written["gates"]["L_hosted"]["legal"] is True


def test_a2_end_to_end_orders_frames_by_local_name(tmp_path):
    """A2's frames come from the same content-addressed map the cascade probe used, and
    the same ordering hazard applies: sorting by server name would shuffle the reference
    clip while every count still read right."""
    uploads = {f"{i:05d}.png": f"{(80 - i):064x}.png" for i in range(81)}
    seeds, prompt, _, up = _files(tmp_path, uploads=uploads)
    out = tmp_path / "route2"
    wf, rec = B.main([f"--arm=A2", f"--seed={SEEDS[1]}", f"--seeds={seeds}",
                      f"--prompt-file={prompt}", f"--uploads={up}", f"--out={out}"])
    assert rec["reference_video"]["frame_order"] == [f"{i:05d}.png" for i in range(81)]
    assert wf[str(CASCADE.FIRST_IMAGE_ID)]["inputs"]["image"] == uploads["00000.png"]
    assert rec["gates"]["CASCADE_topology"]["verdict"]
    assert rec["gates"]["CASCADE_ceiling"]["per_node"]


def test_an_unregistered_seed_stops_the_end_to_end_run(tmp_path):
    seeds, prompt, refs, _ = _files(tmp_path)
    with pytest.raises(RG.RouteGate):
        B.main([f"--arm=A1", "--seed=42", f"--seeds={seeds}", f"--prompt-file={prompt}",
                f"--refs={refs}", f"--out={tmp_path / 'x'}"])


def test_an_illegal_duration_stops_the_end_to_end_run(tmp_path):
    seeds, prompt, refs, _ = _files(tmp_path)
    with pytest.raises(RG.RouteGate) as exc:
        B.main([f"--arm=A1", f"--seed={SEEDS[0]}", f"--seeds={seeds}",
                f"--prompt-file={prompt}", f"--refs={refs}", f"--out={tmp_path / 'y'}",
                "--duration=30"])
    assert "Gate L (hosted tier)" in str(exc.value)
    assert "outside 2..10" in str(exc.value)
