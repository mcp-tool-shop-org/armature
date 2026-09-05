"""Wave 18 (core-gates): the walk could not see the SHAPE it was written for.

Wave 16 closed the empty-population family on five gates and gave the recursion's own
container a refusal. Wave 17's auditors measured that the walk itself still keys node
identity on a value that is not unique, answers a malformed API entry with a silent
`continue`, and reads a hosted tier's enums by position with nothing checking the
position:

  * **F-10af549a** Gate S resolves each seed record back to its node by NODE ID ALONE and
    discards the `where` `seeds()` records, so a blueprint node sharing an id with a
    disabled top-level expert reads the WRONG node's `add_noise` — and an unregistered
    seed runs under a green receipt;
  * **F-039202b9** the subgraph walk's cycle guard is keyed on the blueprint's `id`
    VALUE, so two DISTINCT blueprints declaring one id collapse to one and every node in
    the second is never walked — a BANNED weight inside it is invisible;
  * **F-7eb1ba2a** `_walk_nodes`' API branch — the format every builder submits — drops a
    node-shaped mapping that has lost its `class_type` with a silent `continue`, while
    the save-format branch beside it raises `unreadable_node` on the same stray;
  * **F-d83e5879** Gate S guards the SEED's type and never the COMMITTED LIST's, so a
    registry of `[True]` / `[1.0]` pre-registers nothing and reports "seed is
    pre-registered";
  * **F-7854d570** `hosted_enums` reads a hosted tier's three enum values purely
    positionally, with nothing checking that a converted widget has not SHIFTED the list;
  * **F-4f5de43c** `camera_widget_order_evidence` states `agrees: True` over ZERO nodes —
    the last member of the empty-population family, and the one whose affirmative arrives
    exactly when the class name has drifted out from under the table;
  * **F-04197047** Gate DONOR guards its empty population and never the SHAPE of a row it
    reads, so a 17-landmark record raises `IndexError` and the halt line names no gate.

Every test here goes RED on the tree at base `6b984dd`, and each red is proved on the
OPERAND the finding named — a blueprint node at seed 999999999 beside a disabled
top-level node 3; two blueprints declaring one id with `causvid_x.safetensors` in the
second; a `LoraLoaderModelOnly` with no `class_type`; an empty camera population; a
non-list committed registry; a `Wan2ReferenceVideoApi` whose `duration` widget was
converted to an input; a COCO-topology detection row.
"""

import os
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from armature_core import donor_gate as DG  # noqa: E402
from armature_core import gates as G  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402
from armature_core import lift_solve as LS  # noqa: E402

BASE = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
BANNED = "causvid_x.safetensors"


# =======================================================================================
# F-10af549a · CRITICAL (unanimous) — Gate S resolved a seed record to its node by ID
# ALONE. `seeds()` already records `where`; node identity is the PAIR.
# =======================================================================================


def _two_expert_graph(inner_id):
    """The auditor's graph: the two-expert split this gate documents, plus a blueprint
    holding its OWN sampler. `inner_id` is the blueprint node's id — 3 collides with the
    disabled top-level expert, 9 is the control that already refuses."""
    return {"nodes": [
        {"id": 1, "type": "UNETLoader", "widgets_values": [BASE]},
        {"id": 2, "type": "KSamplerAdvanced", "widgets_values": ["enable", 7, "fixed"]},
        {"id": 3, "type": "KSamplerAdvanced", "widgets_values": ["disable", 7, "fixed"]},
    ], "definitions": {"subgraphs": [
        {"id": "bpA", "name": "inner", "nodes": [
            {"id": inner_id, "type": "KSamplerAdvanced",
             "widgets_values": ["enable", 999999999, "fixed"]}]},
    ]}}


def test_a_blueprint_node_sharing_an_id_with_a_disabled_expert_is_not_that_expert():
    """RED on base: `gate_s_registration` RETURNED with `seeds_noise_bearing: 1` and
    `seeds_exempt_add_noise_disable: [3, 3]`, because the blueprint node's `add_noise` was
    read off the FIRST node the walk yielded — always the top-level one. The renumbered
    control refused. Blueprint ids are a separate namespace by construction, so the
    collision is ordinary."""
    g = _two_expert_graph(3)
    assert [(s["where"], s["node_id"], s["seed"]) for s in RG.seeds(g)] == [
        ("top", 2, 7), ("top", 3, 7), ("inner", 3, 999999999)]
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(g, [7])
    assert "999999999" in str(exc.value)
    assert exc.value.evidence["clause"] == "gate_s_registration"


def test_the_renumbered_control_still_refuses():
    """The control the auditor measured green-to-red against: identical graph, blueprint
    node renumbered so no id collides. It refused before this fix and must still."""
    with pytest.raises(RG.RouteGate, match=r"999999999"):
        RG.gate_s_registration(_two_expert_graph(9), [7])


def test_the_receipt_no_longer_prints_one_node_id_twice():
    """The receipt's own tell. A duplicate id in `seeds_exempt_add_noise_disable` is what
    a reader would have had to notice to catch the wrong-node read, so the exempt list
    names the LEVEL beside the id and cannot repeat an identity."""
    g = {"nodes": [
        {"id": 1, "type": "UNETLoader", "widgets_values": [BASE]},
        {"id": 2, "type": "KSamplerAdvanced", "widgets_values": ["enable", 7, "fixed"]},
        {"id": 3, "type": "KSamplerAdvanced", "widgets_values": ["disable", 7, "fixed"]},
    ], "definitions": {"subgraphs": [
        {"id": "bpA", "name": "inner", "nodes": [
            {"id": 3, "type": "KSamplerAdvanced",
             "widgets_values": ["disable", 7, "fixed"]}]},
    ]}}
    ev = RG.gate_s_registration(g, [7])
    assert ev["seeds_exempt_add_noise_disable"] == [3, 3]
    assert ev["seeds_exempt_nodes"] == [{"where": "top", "node_id": 3},
                                        {"where": "inner", "node_id": 3}]
    assert "top/3" in ev["verdict"] and "inner/3" in ev["verdict"]


def test_a_seed_record_whose_node_cannot_be_refound_refuses_rather_than_defaulting():
    """The resolution must be TOTAL. `adds = True` was the default for an unresolvable
    record, which grades a seed whose node nothing found — and the permissive direction
    for `add_noise` is the one that puts a seed INTO the graded population under a receipt
    that cannot say which node it came from."""
    g = _two_expert_graph(9)
    found = RG.seeds(g)
    assert found  # the fixture carries seeds
    real_seeds = RG.seeds

    def _lying_seeds(graph):
        rows = [dict(r) for r in real_seeds(graph)]
        rows[0]["where"] = "a-level-that-does-not-exist"
        return rows

    RG.seeds = _lying_seeds
    try:
        with pytest.raises(RG.RouteGate) as exc:
            RG.gate_s_registration(g, [7])
    finally:
        RG.seeds = real_seeds
    assert exc.value.evidence["clause"] == "seed_node_unresolvable"
    assert "a-level-that-does-not-exist" in str(exc.value)


# =======================================================================================
# F-039202b9 · CRITICAL (unanimous) — the cycle guard keyed on the blueprint's `id` VALUE,
# so a duplicate id silently DROPPED the second blueprint. A duplicate id is not a cycle.
# =======================================================================================


def _duplicate_blueprint_graph(second_id="bp"):
    return {"nodes": [
        {"id": 1, "type": "UNETLoader", "widgets_values": [BASE]},
        {"id": 2, "type": "KSampler", "widgets_values": [7, "fixed"]},
    ], "definitions": {"subgraphs": [
        {"id": "bp", "name": "first", "nodes": [
            {"id": 10, "type": "LoraLoaderModelOnly",
             "widgets_values": ["clean_style.safetensors"]}]},
        {"id": second_id, "name": "second", "nodes": [
            {"id": 11, "type": "LoraLoaderModelOnly", "widgets_values": [BANNED]}]},
    ]}}


def test_two_blueprints_under_one_id_refuse_instead_of_dropping_the_second():
    """RED on base: `components()` returned only `[BASE, 'clean_style.safetensors']` and
    `verify(g, frame=(832,480,81))` RETURNED GREEN with a CC-BY-NC LoRA inside the second
    blueprint. `link_table` already refuses `duplicate_link_id` on the stated ground that
    a file ambiguous about where its conditioning comes from is not a file this gate can
    vouch for; the blueprint-id table is the third member of that family."""
    g = _duplicate_blueprint_graph()
    with pytest.raises(RG.RouteGate) as exc:
        RG.components(g)
    assert exc.value.evidence["clause"] == "duplicate_subgraph_id"
    assert exc.value.evidence["subgraph_id"] == "bp"
    assert exc.value.evidence["declared_by"] == ["first", "second"]
    with pytest.raises(RG.RouteGate, match=r"duplicate|ambiguous"):
        RG.verify(g, frame=(832, 480, 81))


def test_the_renamed_control_finds_the_banned_weight():
    """The auditor's first control: give the second blueprint its own id and the licence
    walk reaches it. This passed on base and must keep passing — the fix is not allowed to
    turn a duplicate refusal into a licence refusal by accident."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_duplicate_blueprint_graph("bp2"), frame=(832, 480, 81))
    assert BANNED in str(exc.value)


def test_two_blueprints_with_no_id_at_all_are_both_walked():
    """The auditor's second control: with `id` deleted from both blueprints the old
    `id(d)` object-identity fallback was used and the banned file WAS found. Nothing about
    the fix may make an id-less blueprint disappear."""
    g = _duplicate_blueprint_graph()
    for d in g["definitions"]["subgraphs"]:
        del d["id"]
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 81))
    assert BANNED in str(exc.value)


def test_a_self_referencing_blueprint_still_terminates():
    """Cycle protection is the guard's OTHER job and it is the one that must survive: the
    gate before a spend must halt or answer, never hang. The recursion path is keyed on
    object identity, so a blueprint that contains itself is entered once."""
    inner = {"id": "loop", "name": "loop", "nodes": [
        {"id": 20, "type": "LoraLoaderModelOnly",
         "widgets_values": ["clean_style.safetensors"]}]}
    inner["definitions"] = {"subgraphs": [inner]}
    g = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [BASE]}],
         "definitions": {"subgraphs": [inner]}}
    assert [c["file"] for c in RG.components(g)] == [BASE, "clean_style.safetensors"]


def test_a_deeper_self_reference_terminates_too():
    """A -> B -> A. The path is popped on the way back up, so the guard is a cycle guard
    and not a global dedup that would drop a legitimately repeated blueprint."""
    a = {"id": "A", "name": "A", "nodes": [
        {"id": 30, "type": "LoraLoaderModelOnly", "widgets_values": ["a.safetensors"]}]}
    b = {"id": "B", "name": "B", "nodes": [
        {"id": 31, "type": "LoraLoaderModelOnly", "widgets_values": ["b.safetensors"]}],
        "definitions": {"subgraphs": [a]}}
    a["definitions"] = {"subgraphs": [b]}
    g = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [BASE]}],
         "definitions": {"subgraphs": [a]}}
    assert [c["file"] for c in RG.components(g)] == [
        BASE, "a.safetensors", "b.safetensors"]


# =======================================================================================
# F-7eb1ba2a · CRITICAL (unanimous) — the API branch answered a malformed entry with a
# silent `continue`, and nothing counted what it dropped.
# =======================================================================================


def _api_with_lora(class_type=True):
    node = {"inputs": {"lora_name": BANNED}}
    if class_type:
        node["class_type"] = "LoraLoaderModelOnly"
    return {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}},
            "2": {"class_type": "KSampler", "inputs": {"seed": 7}},
            "3": node}


def test_an_api_node_that_lost_its_class_type_refuses_like_the_save_format_branch():
    """RED on base: with `class_type` deleted, `components()` returned only the
    UNETLoader's weight and `verify` RETURNED with "0 of 1 component(s) classified" — no
    key in the receipt recorded that a mapping entry existed and was not read. The same
    stray in save format raises `unreadable_node`; both formats now answer with the one
    clause."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.components(_api_with_lora(class_type=False))
    ev = exc.value.evidence
    assert ev["clause"] == "unreadable_node"
    assert ev["where"] == "api"
    assert ev["key"] == "3"
    with pytest.raises(RG.RouteGate,
                       match=r"no `class_type` and no envelope meaning"):
        RG.verify(_api_with_lora(class_type=False), frame=(832, 480, 81))


def test_the_same_graph_with_class_type_present_still_finds_the_banned_file():
    """The green-to-red pair. Nothing about the refusal may depend on the licence walk."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_api_with_lora(class_type=True), frame=(832, 480, 81))
    assert BANNED in str(exc.value)


def test_ordinary_api_envelope_metadata_is_still_tolerated_and_now_counted():
    """`last_node_id: 12` beside real nodes is ordinary submission metadata, which is why
    F-85d2b7a3 made the walk tolerate it. What was missing is the COUNT: the licence
    clause's `of {len(comp)}` denominator could not be reconciled against what the walk
    entered."""
    g = dict(_api_with_lora(class_type=True))
    del g["3"]
    g["last_node_id"] = 12
    g["extra_data"] = {"extra_pnginfo": {}}
    assert [c["file"] for c in RG.components(g)] == [BASE]
    census = RG.api_walk_census(g)
    assert census["n_top_level_values"] == 4
    assert census["n_nodes_walked"] == 2
    assert census["skipped_non_node_keys"] == ["extra_data", "last_node_id"]
    ev = RG.verify(g, frame=(832, 480, 81))
    assert ev["walk_census"] == census


def test_the_walk_census_is_absent_rather_than_faked_on_save_format():
    """A census that reported zero skipped keys on a save-format graph would be a number
    about a walk that never ran. The key is written only where the API branch runs."""
    g = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [BASE]},
                   {"id": 2, "type": "KSampler", "widgets_values": [7, "fixed"]}]}
    assert RG.api_walk_census(g) is None
    assert RG.verify(g, frame=(832, 480, 81))["walk_census"] is None


def test_a_non_dict_top_level_value_is_still_skipped_not_raised():
    """The wave-12 pin: the API branch skips a non-dict by design. It is now counted."""
    g = {"1": "not a node",
         "2": {"class_type": "UNETLoader", "inputs": {"unet_name": BASE}}}
    assert [c["file"] for c in RG.components(g)] == [BASE]
    assert RG.api_walk_census(g)["skipped_non_node_keys"] == ["1"]


# =======================================================================================
# F-d83e5879 · CRITICAL — Gate S guarded the SEED's type and never the COMMITTED LIST's.
# =======================================================================================


@pytest.mark.parametrize("seed,registry", [
    (1, [True]), (0, [False]), (1, [1.0]), (7, ["7"]), (7, [7, None]), (7, [7, 8.0]),
])
def test_a_committed_list_that_is_not_a_list_of_ints_refuses(seed, registry):
    """RED on base: `gate_s_seed_registration(1, [True], 'E14', True)` returned "seed is
    pre-registered" with `registry_index: 0`, because `in` is `==` membership and `bool`
    and `float` compare equal to ints. Wave 16 closed this on the SEED; the registry
    arrives by the same route — a spec field, a `.get('seeds')`, a JSON list."""
    with pytest.raises(G.GateSSeedRegistration) as exc:
        G.gate_s_seed_registration(seed, registry, "E14", True)
    assert exc.value.evidence["clause"] == "registry_member_not_an_int"
    assert exc.value.evidence["offending_members"]


def test_a_registry_of_mixed_unorderable_types_refuses_by_name_not_by_TypeError():
    """Same line, the other exit: `sorted(registry).index(seed)` raised a bare `TypeError`,
    which is not an `ArmatureError` and bypasses the halt contract's receipt branch."""
    with pytest.raises(G.GateSSeedRegistration,
                       match=r"index 0 is a str \('7'\)"):
        G.gate_s_seed_registration(7, ["7", 7], "E14", True)


def test_the_integer_registries_this_repo_actually_commits_stay_green():
    """The direction that must not move: an andon that fires on a correct call is not one
    anybody keeps."""
    ev = G.gate_s_seed_registration(7, [3, 7, 11], "E14", True)
    assert ev["verdict"] == "seed is pre-registered"
    assert ev["registry_index"] == 1


# =======================================================================================
# F-7854d570 · HIGH — the hosted tier's three enum values were read purely positionally.
# =======================================================================================

# The repo's own fixture widget layout (tests/test_route_gates.py:1611):
# model, prompt, negative, resolution, ratio, duration, seed, control.
_R2V_UNSHIFTED = {"id": 1, "type": "Wan2ReferenceVideoApi", "inputs": [],
                  "widgets_values": ["wan2.7-r2v", "p", "n", "720P", "16:9", 5,
                                     7, "fixed"]}


def test_a_converted_duration_widget_refuses_rather_than_reading_the_seed_slot():
    """RED on base: `hosted_enums` returned `[(1,'720P','16:9',5), (2,'720P','16:9',7)]` —
    node 2's `duration` read off the SEED slot, a value legal under
    `HOSTED_TIER_RULES['wan2.7-r2v']['duration_s'] == (2, 10)` and not the number that
    runs, which arrives over the link. `_save_format_input_names` already exists precisely
    to pull a converted widget's name out of the save-format `inputs` list."""
    shifted = {"id": 2, "type": "Wan2ReferenceVideoApi",
               "inputs": [{"name": "duration", "widget": {"name": "duration"}}],
               "widgets_values": ["wan2.7-r2v", "p", "n", "720P", "16:9", 7, "fixed"]}
    with pytest.raises(RG.RouteGate) as exc:
        RG.hosted_enums({"nodes": [_R2V_UNSHIFTED, shifted]})
    ev = exc.value.evidence
    assert ev["clause"] == "converted_widget_shifts_enum_indices"
    assert ev["node_id"] == 2
    assert ev["converted"] == ["duration"]


def test_a_widget_converted_below_the_enum_indices_also_refuses():
    """`prompt` sits at index 1, below all three enum indices, so converting it shifts
    every one of them — the direction a check on the named field alone would miss."""
    below = {"id": 4, "type": "Wan2ReferenceVideoApi",
             "inputs": [{"name": "prompt", "widget": {"name": "prompt"}}],
             "widgets_values": ["wan2.7-r2v", "n", "720P", "16:9", 5, 7, "fixed"]}
    with pytest.raises(RG.RouteGate) as exc:
        RG.hosted_enums({"nodes": [below]})
    assert exc.value.evidence["clause"] == "converted_widget_shifts_enum_indices"
    assert exc.value.evidence["converted"] == ["prompt"]


def test_a_truncated_widget_list_refuses_rather_than_dropping_the_node():
    """The same defect wearing the other hat: a node whose widget list falls below the
    highest enum index contributed NOTHING to `found`, and `verify`'s per-node billing
    clause then counted a population the graph does not have."""
    trunc = {"id": 3, "type": "Wan2ReferenceVideoApi", "inputs": [],
             "widgets_values": ["wan2.7-r2v", "p", "n"]}
    with pytest.raises(RG.RouteGate) as exc:
        RG.hosted_enums({"nodes": [_R2V_UNSHIFTED, trunc]})
    ev = exc.value.evidence
    assert ev["clause"] == "hosted_enum_widgets_truncated"
    assert ev["node_id"] == 3
    assert ev["n_widgets"] == 3


def test_the_unshifted_r2v_fixture_stays_green():
    """The population that must not move."""
    # WAVE 22 (core-gates, F-2fa07723): the tuple is `(where, node_id, resolution, ratio,
    # duration)`; `where` was discarded and the per-node billing refusal could not say
    # which node it stopped.
    assert RG.hosted_enums({"nodes": [_R2V_UNSHIFTED]}) == [
        ("top", 1, "720P", "16:9", 5)]


def test_an_unrelated_converted_input_does_not_fire_the_clause():
    """`negative` sits ABOVE nothing — it is at index 2, below the enum block — so it
    shifts. `seed`, at index 6, is above all three and shifts none of them. An andon that
    fires on a correct graph is not one anybody keeps."""
    ok = {"id": 5, "type": "Wan2ReferenceVideoApi",
          "inputs": [{"name": "seed", "widget": {"name": "seed"}}],
          "widgets_values": ["wan2.7-r2v", "p", "n", "720P", "16:9", 5, "fixed"]}
    # WAVE 22 (core-gates, F-2fa07723) — see the note above.
    assert RG.hosted_enums({"nodes": [ok]}) == [("top", 5, "720P", "16:9", 5)]


# =======================================================================================
# F-4f5de43c · HIGH — an affirmative verdict over ZERO nodes, the last member of the
# empty-population family this repo has closed five times.
# =======================================================================================


def test_the_camera_second_reading_is_indeterminate_over_an_empty_population():
    """RED on base: a save-format graph with no camera node at all returned
    `{"verdict": "the declared indices carry the builder's numbers on 0 node(s)",
    "agrees": true, "nodes": []}`. Its four siblings on these two pages all refuse an
    empty declared population."""
    g = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": [BASE]},
                   {"id": 2, "type": "KSampler", "widgets_values": [7, "fixed"]}]}
    ev = RG.camera_widget_order_evidence(g, {"width": 832, "height": 480, "length": 81})
    assert ev["agrees"] is None
    assert ev["verdict"].startswith("INDETERMINATE")
    assert ev["nodes"] == []


def test_a_camera_node_whose_class_drifted_reads_indeterminate_not_agreed():
    """The drift this function exists to catch. On base a renamed class returned the
    identical affirmative — a confirmation that the indices were never read."""
    g = {"nodes": [{"id": 45, "type": "WanCameraImageToVideoV2",
                    "widgets_values": ["Static", 832, 480, 65]}]}
    ev = RG.camera_widget_order_evidence(g, {"width": 832, "height": 480, "length": 65})
    assert ev["agrees"] is None
    assert ev["verdict"].startswith("INDETERMINATE")


def test_the_api_format_answer_is_untouched():
    """`not_applicable` is a DIFFERENT fact — there is nothing positional to confirm —
    and the finding is explicit that the two must not be conflated."""
    api = {"50": {"class_type": "WanCameraEmbedding",
                  "inputs": {"width": 832, "height": 480, "length": 65}}}
    ev = RG.camera_widget_order_evidence(api, {"width": 832, "height": 480, "length": 65})
    assert ev["verdict"].startswith("not_applicable")
    assert "agrees" not in ev


def test_a_populated_camera_graph_still_answers_true():
    """The green direction the two existing pins already cover, repeated here so this
    file's own red proof has its control beside it."""
    g = {"nodes": [{"id": 45, "type": "WanCameraEmbedding",
                    "widgets_values": ["Static", 832, 480, 65, 1.0, 0.5, 0.5, 0.5, 0.5]}]}
    ev = RG.camera_widget_order_evidence(g, {"width": 832, "height": 480, "length": 65})
    assert ev["agrees"] is True


# =======================================================================================
# F-04197047 · HIGH — Gate DONOR guarded its empty population and never the SHAPE of a row.
# =======================================================================================


def _rows(image):
    return [{"frame": i, "fired": True, "image": image} for i in range(3)]


_OK_33 = [[0.5, 0.5]] * len(LS.POSE_LANDMARKS)


@pytest.mark.parametrize("label,image", [
    ("coco-17", [[0.5, 0.5]] * 17),
    ("none-landmark", _OK_33[:27] + [None] + _OK_33[28:]),
    ("dict-landmarks", [{"x": 0.5, "y": 0.5}] * len(LS.POSE_LANDMARKS)),
    ("scalar-landmark", _OK_33[:27] + [0.5] + _OK_33[28:]),
    ("short-pair", _OK_33[:27] + [[0.5]] + _OK_33[28:]),
    ("image-not-a-list", {"left_ankle": [0.5, 0.5]}),
])
def test_a_malformed_detection_row_refuses_as_gate_donor_not_as_a_crash(label, image):
    """RED on base: a 17-landmark row raised `IndexError`, a `None` landmark `TypeError`,
    a dict-shaped landmark `KeyError` — none of them an `ArmatureError`, so `lift_clip`'s
    halt handler classified a deliberate-shaped refusal as an unhandled crash and wrote a
    halt line naming no gate and carrying no receipt."""
    with pytest.raises(DG.DonorGate) as exc:
        DG.ankle_framing(_rows(image))
    ev = exc.value.evidence
    assert ev["clause"] == "unreadable_landmark_row"
    assert ev["gate"] == "DONOR"
    assert ev["required_index"] == max(LS.POSE_LANDMARKS.index(a) for a in DG.ANKLES)
    assert ev["frame"] == 0


def test_a_well_formed_33_landmark_clip_stays_green():
    """The live producer's shape: MediaPipe's `detect()` always emits 33 landmarks."""
    out = DG.ankle_framing(_rows(_OK_33))
    assert out["both_ankles_in_image"] == 1.0
    assert out["n_frames_considered"] == 3


def test_a_frame_the_detector_did_not_fire_on_is_not_read_for_shape():
    """A row that never fired carries no landmarks to check, and the CLIP-denominator
    reading counts it as not-in-frame. Guarding its shape would refuse a legitimate clip."""
    rows = _rows(_OK_33) + [{"frame": 3, "fired": False, "image": None}]
    out = DG.ankle_framing(rows)
    assert out["n_frames_considered"] == 4
    assert out["both_ankles_in_image"] == 0.75


# =======================================================================================
# Family census — every clause added this wave raises a NAMED subclass with evidence, and
# survives `-O` (no `assert`, no skip flag, no environment escape).
# =======================================================================================


#: Which tool's `__main__` handler an operator would actually see each clause through, and
#: the sentinel that handler prints. Wave-18 rule 4: the halt line is READ, not assumed.
#: Measured 2026-09-04 by driving each handler with the real refusal — every one exits 2
#: (a gate refused) and carries the clause and its operand in `evidence`, which is what
#: separates a deliberate-shaped refusal from the unhandled crash three of these findings
#: produced before the fix (`IndexError`, `TypeError`, `KeyError`, `AttributeError`).
HALT_ROUTES = [
    ("duplicate_subgraph_id", "gate_saved_graph.py", "SAVED_ADMISSION_HALT"),
    ("unreadable_node", "gate_saved_graph.py", "SAVED_ADMISSION_HALT"),
    ("seed_node_unresolvable", "gate_saved_graph.py", "SAVED_ADMISSION_HALT"),
    ("converted_widget_shifts_enum_indices", "gate_saved_graph.py",
     "SAVED_ADMISSION_HALT"),
    ("hosted_enum_widgets_truncated", "gate_saved_graph.py", "SAVED_ADMISSION_HALT"),
    ("registry_member_not_an_int", "build_t2v_payload.py", "BUILD_T2V_HALT"),
    ("unreadable_landmark_row", "lift_clip.py", "LIFT_CLIP_HALT"),
]


def _refusal_for(clause):
    """The REAL call that raises `clause`, so the halt record read below is the one an
    operator gets rather than a hand-built exception wearing the clause's name."""
    if clause == "duplicate_subgraph_id":
        return lambda: RG.components(_duplicate_blueprint_graph())
    if clause == "unreadable_node":
        return lambda: RG.components(_api_with_lora(class_type=False))
    if clause == "seed_node_unresolvable":
        def _call():
            real = RG.seeds
            try:
                RG.seeds = lambda g: [dict(r, where="nowhere") for r in real(g)]
                RG.gate_s_registration(_two_expert_graph(9), [7])
            finally:
                RG.seeds = real
        return _call
    if clause == "converted_widget_shifts_enum_indices":
        return lambda: RG.hosted_enums({"nodes": [{
            "id": 2, "type": "Wan2ReferenceVideoApi",
            "inputs": [{"name": "duration", "widget": {"name": "duration"}}],
            "widgets_values": ["wan2.7-r2v", "p", "n", "720P", "16:9", 7, "fixed"]}]})
    if clause == "hosted_enum_widgets_truncated":
        return lambda: RG.hosted_enums({"nodes": [{
            "id": 3, "type": "Wan2ReferenceVideoApi", "inputs": [],
            "widgets_values": ["wan2.7-r2v"]}]})
    if clause == "registry_member_not_an_int":
        return lambda: G.gate_s_seed_registration(1, [True], "E14", True)
    if clause == "unreadable_landmark_row":
        return lambda: DG.ankle_framing(_rows([[0.5, 0.5]] * 17))
    raise AssertionError(clause)


@pytest.mark.parametrize("clause,tool,sentinel", HALT_ROUTES)
def test_the_halt_line_an_operator_reads_names_the_andon_that_pulled(
        clause, tool, sentinel, capsys):
    """Wave-18 rule 4. Three of these findings ended in an `IndexError`, a `TypeError` or
    a `KeyError` — none of them an `ArmatureError` — so the handler's exit-2 receipt
    branch was BYPASSED and the run was recorded as an unhandled crash naming no gate.
    This drives the tool's real `__main__` and reads the record back."""
    import json

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from blender_stub import exit_code_of_main_block

    code, escaped = exit_code_of_main_block(
        tool, raiser=_refusal_for(clause),
        argv=["python", tool, "--out", "nope"])
    out = capsys.readouterr().out
    assert escaped is None, f"{tool}: {escaped!r} escaped the handler"
    assert code == 2, f"{tool} ({clause}): exit {code!r}, the contract says 2 for a gate"
    lines = [l for l in out.splitlines() if l.split(" ", 1)[0] == sentinel]
    assert len(lines) == 1, f"{tool} ({clause}): {len(lines)} sentinel line(s)"
    rec = json.loads(lines[0][len(sentinel):].strip())
    ev = rec["evidence"]
    assert isinstance(ev, dict), f"{tool} ({clause}): evidence {ev!r}"
    assert ev["clause"] == clause
    assert ev["andon"] == rec["error"]
    assert ev["gate"] in ("ROUTE", "S", "DONOR")


def test_every_clause_added_this_wave_raises_a_named_subclass_with_evidence():
    from armature_core.errors import ArmatureError

    cases = [
        ("duplicate_subgraph_id", RG.RouteGate,
         lambda: RG.components(_duplicate_blueprint_graph())),
        ("unreadable_node", RG.RouteGate,
         lambda: RG.components(_api_with_lora(class_type=False))),
        ("converted_widget_shifts_enum_indices", RG.RouteGate,
         lambda: RG.hosted_enums({"nodes": [
             {"id": 2, "type": "Wan2ReferenceVideoApi",
              "inputs": [{"name": "duration", "widget": {"name": "duration"}}],
              "widgets_values": ["wan2.7-r2v", "p", "n", "720P", "16:9", 7, "fixed"]}]})),
        ("hosted_enum_widgets_truncated", RG.RouteGate,
         lambda: RG.hosted_enums({"nodes": [
             {"id": 3, "type": "Wan2ReferenceVideoApi", "inputs": [],
              "widgets_values": ["wan2.7-r2v"]}]})),
        ("registry_member_not_an_int", G.GateSSeedRegistration,
         lambda: G.gate_s_seed_registration(1, [True], "E14", True)),
        ("unreadable_landmark_row", DG.DonorGate,
         lambda: DG.ankle_framing(_rows([[0.5, 0.5]] * 17))),
    ]
    for clause, cls, call in cases:
        with pytest.raises(cls) as exc:
            call()
        assert isinstance(exc.value, ArmatureError), clause
        assert exc.value.evidence["clause"] == clause
        assert exc.value.evidence.get("andon") == cls.__name__
