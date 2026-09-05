"""Wave 25, core-gates — the nine approved findings, each with the measurement it closes.

Every test here names the operand the wave-24 auditor measured on `580af47` and the state
that operand was in BEFORE the fix. The red proof for each is written in its docstring as
the measured behaviour of the base, because the base is one `git stash` away and the
sentence is what survives.

Read the module docstrings the fixes edited for the full argument; these are the pins.
"""

import ast
import inspect
import textwrap
import json
import os
import pathlib
import tempfile

import pytest

from armature_core import canon as C
from armature_core import donor_gate as D
from armature_core import gates as G
from armature_core import route_gates as RG
from armature_core import shotspec as S
from armature_core.errors import (
    G4BboxSanity,
    G6SubjectMotion,
    GateCanon,
    SpecError,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
CORE = REPO / "tools" / "armature_core"

#: The eleven files this domain owns in the frozen wave-25 domain map.
OWNED = {
    "__init__.py", "gates.py", "route_gates.py", "rig_gates.py", "donor_gate.py",
    "canon.py", "canon_census.py", "errors.py", "subject.py", "shotspec.py", "cli.py",
}


# ===================================================================== F-ebb1ebb4 (CRIT)
#
# `WEIGHT_SUFFIXES` filtered the licence walk's population BEFORE `rulings_for` was ever
# consulted, so a hand-maintained tuple of seven extensions decided which names the licence
# table was allowed to rule on.

def _lora_graph(name):
    """`UNETLoader` + pinned `KSampler` + a LoRA loader carrying `name`."""
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name":
                         "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
        "2": {"class_type": "KSampler",
              "inputs": {"seed": 7, "control_after_generate": "fixed"}},
        "3": {"class_type": "LoraLoaderModelOnly", "inputs": {"lora_name": name}},
    }


@pytest.mark.parametrize("spelling", ["causvid_x.safetensors", "causvid_x.bin",
                                      "causvid_x", "causvid_x.onnx"])
def test_a_banned_weight_is_refused_whatever_its_extension(spelling):
    """RED on the base, measured in this worktree on `580af47`: only the `.safetensors`
    spelling raised. The other three RETURNED "0 of 1 component(s) classified, 1
    unclassified, … 1 frame(s) checked and generator-legal", `ev["unclassified"]` named only
    the `UNETLoader`, and `json.dumps(ev)` contained "causvid" ZERO times — while
    `rulings_for('causvid_x.bin')` returned the BANNED row the whole time."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_lora_graph(spelling), frame=(832, 480, 81))
    assert spelling in str(exc.value), str(exc.value)
    assert exc.value.evidence["clause"] == "banned_or_excluded_component"
    assert spelling in json.dumps(exc.value.evidence, default=str)


def test_the_banned_name_is_a_component_rather_than_a_dropped_string():
    """The receipt half: `components()` must NAME it, so the licence clause's `of {n}`
    denominator counts the thing that was ruled on."""
    rows = [c for c in RG.components(_lora_graph("causvid_x.bin"))
            if c["kind"] == "weight"]
    named = {c["file"]: c for c in rows}
    assert "causvid_x.bin" in named, sorted(named)
    assert named["causvid_x.bin"]["verdict"] == "BANNED"
    assert named["causvid_x.bin"]["suffix_recorded"] is False
    assert named["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"][
        "suffix_recorded"] is True


def test_an_allowed_ruled_name_with_an_unrecorded_suffix_refuses_by_name():
    """The direction that stays unbounded once the BANNED kill is closed: an ALLOWED row's
    name in an artifact format nobody recorded. Refusing means `WEIGHT_SUFFIXES` is
    extended in a commit rather than by a converter's choice of filename."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_lora_graph("technically_color_v2.bin"), frame=(832, 480, 81))
    assert exc.value.evidence["clause"] == "ruled_name_with_unknown_suffix"
    assert exc.value.evidence["ruled_names_with_unknown_suffix"] == [
        "technically_color_v2.bin"]
    assert exc.value.evidence["recorded_suffixes"] == list(RG.WEIGHT_SUFFIXES)


def test_a_prompt_carrying_a_ruled_substring_is_not_a_component():
    """`rulings_for` is a SUBSTRING test and a widget list holds prompts as well as
    filenames, so the ruling is only asked of NAME-shaped values. Prose has whitespace in
    it; a name does not."""
    g = {"1": {"class_type": "CLIPTextEncode",
               "inputs": {"text": "a candid_photography of a knight in plate armour"}}}
    assert [c for c in RG.components(g) if c["kind"] == "weight"] == []
    assert RG._is_name_shaped("causvid_x.bin") is True
    assert RG._is_name_shaped("a candid_photography of a knight") is False


def test_the_licence_walk_reads_a_superset_of_gate_pairs_population():
    """The two readers of one tuple failed in OPPOSITE directions — `model_weights` (Gate
    PAIR) closed, `components` open. PAIR keeps the suffix tuple deliberately, so the
    invariant that matters is containment: nothing PAIR can see escapes the licence walk."""
    g = _lora_graph("causvid_x.bin")
    licence = {c["file"] for c in RG.components(g) if c["kind"] == "weight"}
    pair = {w["file"] for w in RG.model_weights(g)}
    assert pair <= licence, sorted(pair - licence)
    assert "causvid_x.bin" in licence - pair


# ===================================================================== F-6fcab339 (CRIT)

def _r2v_save(resolution="4K", ratio="99:1", duration=900):
    return {"nodes": [{"id": 1, "type": "Wan2ReferenceVideoApi",
                       "widgets_values": ["a prompt", "a negative", "",
                                          resolution, ratio, duration]}]}


def test_a_graph_carrying_hosted_nodes_with_no_declared_tier_refuses():
    """RED on the base: `verify(g, frame=(832,480,81), require_pinned_seeds=False)`
    RETURNED with `frame_legality_verdict: 'PROVEN'` and no key beginning `hosted_` in the
    evidence at all, while `hosted_enums(g)` read `[('top', 1, '4K', '99:1', 900)]`."""
    g = _r2v_save()
    declared = RG.hosted_enums(g)
    assert len(declared) == 1 and declared[0][0] == "top"
    assert declared[0][2:] == ("4K", "99:1", 900), declared
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 81), require_pinned_seeds=False)
    ev = exc.value.evidence
    assert ev["clause"] == "hosted_nodes_without_a_tier"
    rows = ev["hosted_nodes_without_a_tier"]
    assert [(r["where"], r["class"]) for r in rows] == [
        ("top", "Wan2ReferenceVideoApi")], rows
    assert ev["recorded_hosted_tiers"] == sorted(RG.HOSTED_TIER_RULES)


def test_the_same_graph_with_the_tier_declared_still_refuses_on_the_enums():
    """The control: the clause this refusal exists to let run."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_r2v_save(), hosted_tier="wan2.7-r2v", require_pinned_seeds=False)
    assert exc.value.evidence["clause"] == "hosted_frame_illegal"
    assert "'4K' is not one of" in str(exc.value)


def test_the_told_the_tier_and_found_no_hosted_node_direction_stays_green():
    """The converse the block already bounded must keep firing in its own direction."""
    g = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan_t2v.safetensors"}}}
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, hosted_tier="wan2.7-r2v", require_pinned_seeds=False)
    assert exc.value.evidence["clause"] == "hosted_tier_without_hosted_nodes"


# ===================================================================== F-10bf02c5 (CRIT)

_TEXT = "a knight in plate armour"


def test_a_node_whose_inputs_is_not_a_mapping_refuses_rather_than_being_dropped():
    """RED on the base: this graph returned `['a knight in plate armour']` — ONE of two —
    with nothing recording that a node existed and was not read, while
    `route_gates.components` on the SAME graph raised `unreadable_node`. Two readers of one
    API graph, opposite verdicts, and the one that failed OPEN fed Gate CANON."""
    g = {"6": {"class_type": "CLIPTextEncode", "inputs": {"text": _TEXT}},
         "7": {"class_type": "CLIPTextEncode",
               "inputs": [["text", "a second, unchecked prompt with forbidden words"]]}}
    with pytest.raises(GateCanon) as exc:
        C.texts_from_api_graph(g)
    assert exc.value.evidence["clause"] == "unreadable_node"
    assert exc.value.evidence["container"] == "inputs"
    # the control one module over, which already answered this way
    with pytest.raises(RG.RouteGate) as route:
        RG.components(g)
    assert route.value.evidence["clause"] == "unreadable_node"


def test_the_well_formed_control_still_returns_every_text():
    g = {"6": {"class_type": "CLIPTextEncode", "inputs": {"text": _TEXT}},
         "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "a second prompt"}}}
    assert C.texts_from_api_graph(g) == [_TEXT, "a second prompt"]
    assert C.texts_from_api_graph({"prompt": g}) == [_TEXT, "a second prompt"]
    assert C.texts_from_api_graph(dict(g, last_node_id=12)) == [_TEXT, "a second prompt"]


def test_the_reader_adopted_the_walk_rather_than_a_second_isinstance():
    """Read as text, because the defect was a second spelling of a guard that has one home:
    a local `isinstance(inputs, dict)` with a bare `continue` put it back."""
    src = inspect.getsource(C.texts_from_api_graph)
    assert "_walk_nodes" in src
    fn = ast.parse(textwrap.dedent(src)).body[0]
    assert [n for n in ast.walk(fn) if isinstance(n, ast.Continue)] == [], (
        "a bare `continue` is back in the reader that feeds Gate CANON")


# ===================================================================== F-35820295 (CRIT)

def test_a_bbox_wholly_outside_the_frame_refuses():
    """RED on the base: `g4_bbox_sanity(0, (5000,5000,5010,5010), (5002,5002,5012,5012),
    832, 480)` returned `[2, 2, 2, 2]` — a PASS on two boxes entirely off the frame — and
    `(-900,-900,-880,-880)` against itself returned `[0,0,0,0]`. `width` and `height`
    occurred exactly once each in the function, both inside `ev['resolution']`."""
    with pytest.raises(G4BboxSanity) as exc:
        G.g4_bbox_sanity(0, (5000, 5000, 5010, 5010), (5002, 5002, 5012, 5012), 832, 480)
    assert exc.value.evidence["clause"] == "bbox_outside_the_frame"
    with pytest.raises(G4BboxSanity) as exc:
        G.g4_bbox_sanity(0, (-900, -900, -880, -880), (-900, -900, -880, -880), 832, 480)
    assert exc.value.evidence["clause"] == "bbox_outside_the_frame"


def test_a_bbox_whose_corners_are_out_of_order_refuses():
    """RED on the base: `g4_bbox_sanity(0, (500,400,10,10), (500,400,10,10), 832, 480)`
    returned `[0,0,0,0]` with `ev['projected_bbox_size_px'] == [-490, -390]` — a receipt
    asserting the projected silhouette is negative on both axes."""
    with pytest.raises(G4BboxSanity) as exc:
        G.g4_bbox_sanity(0, (500, 400, 10, 10), (500, 400, 10, 10), 832, 480)
    assert exc.value.evidence["clause"] == "bbox_corners_out_of_order"
    assert exc.value.evidence["failed_edges"] == ["x", "y"]


def test_a_bbox_clipped_to_the_frame_edge_still_passes():
    """The direction the new clauses must not touch: a legitimately clipped box touching
    0 or width-1 is what `projected_bbox_px` returns on a subject that fills the frame."""
    assert G.g4_bbox_sanity(0, (0, 0, 831, 479), (0, 0, 831, 479), 832, 480) == [0, 0, 0, 0]
    assert G.g4_bbox_sanity(0, (10, 10, 500, 500), (10, 10, 500, 500), 832, 480) == \
        [0, 0, 0, 0]


def test_an_unreadable_resolution_refuses_rather_than_disarming_the_containment_clause():
    """A check a bad argument can switch off is not a check (wave 10's rule: a disarming
    default is a refusal)."""
    for width, height in ((None, 480), (832, 0), (True, 480)):
        with pytest.raises(G4BboxSanity) as exc:
            G.g4_bbox_sanity(0, (0, 0, 10, 10), (0, 0, 10, 10), width, height)
        assert exc.value.evidence["clause"] == "resolution_is_not_a_frame_size"


def test_the_arity_clause_still_fires_first_on_a_short_bbox():
    """The sibling clauses this one sits beside must keep their order."""
    with pytest.raises(G4BboxSanity) as exc:
        G.g4_bbox_sanity(0, (10, 10), (10, 10, 500, 500), 832, 480)
    assert exc.value.evidence["clause"] == "bbox_is_not_four_numbers"


# ===================================================================== F-a546b5ce (HIGH)

@pytest.mark.parametrize("mode", ["per-frame", None, "PER_FRAME", ""])
def test_an_unrecognised_animation_mode_refuses_rather_than_reporting_not_applicable(mode):
    """RED on the base: `g6_subject_motion(['a'] * 33, 'per-frame')` and the same call with
    `None` both RETURNED the N/A verdict over 33 identical signatures — the exact input the
    gate exists to refuse — quoting the unrecognised value back as if it were a mode."""
    with pytest.raises(G6SubjectMotion) as exc:
        G.g6_subject_motion(["a"] * 33, mode)
    assert exc.value.evidence["clause"] == "unknown_animation_mode"
    assert exc.value.evidence["animation_modes"] == list(S.ANIMATION_MODES)


def test_a_recorded_mode_that_is_not_per_frame_still_answers_not_applicable():
    ev = G.g6_subject_motion(["same"] * 33, "static")
    assert ev["verdict"].startswith("N/A")


def test_g6_reads_the_vocabulary_from_its_one_home():
    """Not a re-typed tuple: a third mode added to the contract must have its G6 semantics
    chosen, and until then it joins on the REFUSING side."""
    assert G.ANIMATION_MODES is S.ANIMATION_MODES


# ===================================================================== F-99164b72 (HIGH)

@pytest.mark.parametrize("motion,framing", [
    ({"mean_over_255": 3.0}, {"both_ankles_in_image": 0.9}),
    ({"mean": 3.0}, {"ankles_in_image": 0.9}),
    ({"mean": 0.1}, {"both_ankles_in_image": 0.1}),
])
def test_a_record_whose_key_moved_refuses_by_name_rather_than_raising_keyerror(motion,
                                                                              framing):
    """RED on the base, measured in this worktree on `580af47`: these three raised
    `KeyError: 'mean'`, `KeyError: 'both_ankles_in_image'` and — the sharp one, on a clip
    that FAILS both of A3's clauses — `KeyError: 'per_ankle_fraction_of_frames_in_image'`.
    `isinstance(exc, ArmatureError)` is False for all three, so the halt contract's exit-2
    receipt branch was bypassed and a deliberate Gate DONOR refusal was classified exit 1."""
    with pytest.raises(D.DonorGate) as exc:
        D.gate_donor(motion, framing)
    assert exc.value.evidence["clause"] == "unreadable_gate_input"
    assert exc.value.evidence["producer"].startswith("donor_gate.")


def test_the_per_ankle_sub_record_the_refusal_message_indexes_is_guarded_too():
    """The fragile path was the REFUSAL path: nothing on the passing path reads it."""
    with pytest.raises(D.DonorGate) as exc:
        D.gate_donor({"mean": 0.1},
                     {"both_ankles_in_image": 0.1,
                      "per_ankle_fraction_of_frames_in_image": {"left_ankle": 0.1}})
    assert exc.value.evidence["clause"] == "unreadable_gate_input"
    assert exc.value.evidence["missing_keys"] == ["right_ankle"]


def test_a_failing_clip_still_refuses_as_a_donor_verdict():
    """The direction the guard must not swallow: a well-formed record that FAILS is still
    Gate DONOR's own refusal, with its verdict."""
    with pytest.raises(D.DonorGate) as exc:
        D.gate_donor({"mean": 0.1},
                     {"both_ankles_in_image": 0.1,
                      "per_ankle_fraction_of_frames_in_image": {"left_ankle": 0.1,
                                                                "right_ankle": 0.1}})
    assert exc.value.evidence["verdict"] == "FAILED"
    assert exc.value.evidence["clause"] == "donor_below_threshold"


# ===================================================================== F-b333ba7c (HIGH)

def _spec_error_sites():
    """Every `SpecError` refusal in `shotspec`, as `(lineno, has_evidence)`.

    Both spellings: the two remaining literal `raise SpecError(...)` sites and every call to
    the module's one `_refuse` helper.
    """
    tree = ast.parse((CORE / "shotspec.py").read_text(encoding="utf-8"))
    raises, refusals = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            if getattr(node.exc.func, "id", None) == "SpecError":
                raises.append((node.lineno, len(node.exc.args) > 1))
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_refuse":
            refusals.append((node.lineno, len(node.args) > 1))
    return raises, refusals


def test_every_spec_refusal_carries_a_clause_and_a_receipt():
    """RED on the base: of 25 `raise SpecError(...)` sites exactly TWO passed a second
    argument, so the halt line printed `"evidence": null` for 23 refusals — including all
    three in `resolve_asset`, the sha256 clause this module's docstring says it exists to
    fix."""
    raises, refusals = _spec_error_sites()
    assert refusals, "the module lost its one refusal helper"
    assert all(has_clause for _lineno, has_clause in refusals), refusals
    # the two literal raises left are the helper itself and the non-finite re-raise, both
    # of which carry a receipt
    assert all(has_evidence for _lineno, has_evidence in raises), raises


def test_the_sha256_mismatch_names_both_digests():
    """The one field this module exists to fix reached an operator as a message string with
    a null receipt."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "asset.glb")
        with open(path, "wb") as fh:
            fh.write(b"hello")
        with pytest.raises(SpecError) as exc:
            S.resolve_asset({"asset": {"path": path, "sha256": "deadbeef"}})
    ev = exc.value.evidence
    assert ev["clause"] == "asset_sha256_mismatch"
    assert ev["pinned"] == "deadbeef"
    assert len(ev["measured"]) == 64 and ev["measured"] != ev["pinned"]
    assert ev["gate"] is None and ev["andon"] == "SpecError"


@pytest.mark.parametrize("spec,clause", [
    ("not a mapping", "spec_is_not_an_object"),
    ({"spec_version": 99}, "spec_version_unsupported"),
    ({"spec_version": 1}, "missing_spec_key"),
])
def test_the_spec_contract_names_the_clause_that_refused(spec, clause):
    with pytest.raises(SpecError) as exc:
        S.normalise_spec(spec)
    assert exc.value.evidence["clause"] == clause


# ===================================================================== F-f1234354 (HIGH)

def test_a_declared_generator_family_that_the_weights_contradict_refuses():
    """RED on the base: nothing in `verify`, `frame_legality` or `_frame_form` read
    `components()`, `model_weights()` or `families_of()` when choosing the rules, and
    `GENERATOR_RULES` has one row — so `family='wan'` could never be refused, and the
    receipt would name family 'wan' beside a weight file that is not wan."""
    RG.GENERATOR_FAMILIES.setdefault("hunyuan", ("hunyuan",))
    try:
        g = {"1": {"class_type": "UNETLoader",
                   "inputs": {"unet_name": "hunyuan_video_720_fp8.safetensors"}},
             "2": {"class_type": "KSampler",
                   "inputs": {"seed": 7, "control_after_generate": "fixed"}}}
        with pytest.raises(RG.RouteGate) as exc:
            RG.verify(g, frame=(832, 480, 81))
        assert exc.value.evidence["clause"] == "generator_family_contradicted"
        assert exc.value.evidence["families_read"] == ["hunyuan"]
        assert exc.value.evidence["declared_family"] == "wan"
    finally:
        RG.GENERATOR_FAMILIES.pop("hunyuan", None)


def test_a_wan_route_reads_its_family_off_the_weights_and_stays_green():
    g = {"1": {"class_type": "UNETLoader",
               "inputs": {"unet_name":
                          "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "2": {"class_type": "KSampler",
               "inputs": {"seed": 7, "control_after_generate": "fixed"}}}
    ev = RG.verify(g, frame=(832, 480, 81))
    assert ev["generator_family"]["families_read"] == ["wan"]
    assert ev["generator_family"]["verdict"].startswith("PROVEN")
    assert ev["generator_family"]["declared"] == "wan"


def test_a_graph_that_loads_no_diffusion_model_records_the_reading_rather_than_refusing():
    """Measured rather than preferred: `build_assembly_payload` and `build_cascade_payload`
    reach `verify` with `model_weights(graph) == []`, so refusing the UNPROVEN direction
    would fire on correct work. It is RECORDED, and the receipt says so."""
    g = {"1": {"class_type": "LoadImage", "inputs": {"image": "0.png"}}}
    ev = RG.verify(g, frame=(832, 480, 81), carries_no_sampler=True)
    assert ev["generator_family"]["verdict"].startswith("not_applicable")
    assert ev["generator_family"]["model_weights"] == []


# ===================================================================== F-7285034a (HIGH)
#
# The clause words, and the converse population the existing census cannot bound.

#: Sites in this domain's files whose evidence the ONE judge cannot READ statically — each
#: a pass-through whose clause comes from the caller or from the refusal it re-raises. They
#: land in the judge's `unreadable` bucket rather than in `offenders`, and the runtime test
#: below proves each carries a clause when it actually fires.
CLAUSE_PASSTHROUGH_SITES = {
    "canon.py:_raise (GateCanon)",
    "canon_census.py:_refuse (GateCanon)",
    "shotspec.py:_refuse (SpecError)",
    "route_gates.py:load_graph (RouteGate)",
}

#: Modules OUTSIDE this domain that still carry a clause-less family raise, measured
#: 2026-09-05 on `580af47`. Asserted as an upper bound (a SUBSET), so a sibling domain
#: closing its own does not fail this file and a NEW offender in a file nobody owns does.
OUT_OF_DOMAIN_CLAUSE_OFFENDERS = {
    "blender_scene.py", "glb.py", "landmarks.py", "lift_solve.py", "parts.py",
    "resample.py", "startframe.py", "turnaround.py", "walk.py",
}


def _clause_census():
    from test_gates import evidence_dicts_missing

    return evidence_dicts_missing("clause", root=str(CORE))


def test_every_family_raise_in_this_domains_files_carries_a_clause():
    """The converse population to `_census_nodes.clause_literals`, which is keyed on the
    clause words that EXIST — so a refusal carrying none is not a member and no census
    reports it.

    RED on the base, measured 2026-09-05 in this worktree: 21 sites in these eleven files
    were offenders, including the licence kill (`route_gates.verify`), all three Gate PAIR
    refusals, Gate L's hosted illegal-enum and two-billable-node refusals, Gate L
    INDETERMINATE, every G1-G6 refusal, every Gate P/N/D refusal and `gate_donor`'s own."""
    offenders, examined, _unreadable, no_evidence = _clause_census()
    assert examined > 0
    mine = sorted(str(o) for o in offenders if str(o).split(":")[0] in OWNED)
    assert mine == [], mine
    mine_without_receipt = sorted(str(o) for o in no_evidence
                                 if str(o).split(":")[0] in OWNED)
    assert mine_without_receipt == [], mine_without_receipt


def test_the_only_unreadable_clause_sites_here_are_the_named_pass_throughs():
    _offenders, _examined, unreadable, _none = _clause_census()
    mine = {str(u) for u in unreadable if str(u).split(":")[0] in OWNED}
    assert mine == CLAUSE_PASSTHROUGH_SITES, sorted(mine)


def test_the_remaining_clause_offenders_are_outside_this_domain():
    """An upper bound, dated. It may only shrink."""
    offenders, _examined, _unreadable, _none = _clause_census()
    others = {str(o).split(":")[0] for o in offenders} - OWNED
    assert others <= OUT_OF_DOMAIN_CLAUSE_OFFENDERS, sorted(
        others - OUT_OF_DOMAIN_CLAUSE_OFFENDERS)


def test_each_pass_through_site_carries_a_clause_when_it_actually_fires():
    """The runtime half of the four static blind spots above."""
    with pytest.raises(GateCanon) as exc:          # canon._raise
        C.texts_from_api_graph({"last_node_id": 12, "version": 0.4})
    assert exc.value.evidence["clause"] == "unrecognised_graph"

    from armature_core import canon_census as CC   # canon_census._refuse
    with pytest.raises(GateCanon) as exc:
        CC.gate_census_table(["not", "a", "mapping"])
    assert exc.value.evidence["clause"]

    with tempfile.TemporaryDirectory() as tmp:     # route_gates.load_graph
        path = os.path.join(tmp, "g.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"last_node_id": 12, "version": 0.4}')
        with pytest.raises(RG.RouteGate) as exc:
            RG.load_graph(path)
    assert exc.value.evidence["clause"], exc.value.evidence

    with pytest.raises(SpecError) as exc:          # shotspec._refuse
        S.normalise_spec("not a mapping")
    assert exc.value.evidence["clause"] == "spec_is_not_an_object"


def test_the_licence_kill_and_the_spend_gates_carry_the_words_a_halt_reader_keys_on():
    """RED on the base: the licence kill's evidence read `gate: 'ROUTE'`, `andon:
    'RouteGate'`, `clause: None`, and `gate_saved_graph.route_facts` reads
    `refusals = [r for r in receipts if r.get('clause')]`."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(_lora_graph("causvid_x.safetensors"), frame=(832, 480, 81))
    assert exc.value.evidence["clause"] == "banned_or_excluded_component"

    with pytest.raises(RG.PairGate) as exc:        # Gate PAIR, all three words exist
        RG.pairing({"1": {"class_type": "WanCameraImageToVideo", "inputs": {}},
                    "2": {"class_type": "UNETLoader",
                          "inputs": {"unet_name": "wan2.2_t2v.safetensors"}}})
    assert exc.value.evidence["clause"] == "conditioning_family_absent"


def test_covers_five_refusals_carry_five_clause_words():
    """RED on the base: `ev['clause'] = 'cover'` was set once and only the blocked-additions
    branch overrode it, so four different operator actions reached a halt line under one
    key."""
    src = inspect.getsource(C.cover)
    for word in ("phrase_absent", "phrase_negated", "forbidden_word",
                 "blocked_addition", "unlicensed_residue"):
        assert f'ev["clause"] = "{word}"' in src, word
    assert 'ev["clause"] = "cover"' in src, "the receipt keeps its own word"


def test_a_returned_verify_receipt_still_carries_no_clause():
    """The invariant every clause word added this wave had to respect: `gate_saved_graph.
    route_facts` tells a returned receipt from a caught refusal by the ABSENCE of `clause`,
    so every one of them is written immediately before a raise and never on a return path."""
    g = {"1": {"class_type": "UNETLoader",
               "inputs": {"unet_name":
                          "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"}},
         "2": {"class_type": "KSampler",
               "inputs": {"seed": 7, "control_after_generate": "fixed"}}}
    ev = RG.verify(g, frame=(832, 480, 81))
    assert "clause" not in ev, sorted(ev)
    assert ev["receipt"] == "verify"


#: Every clause word this wave adds, by module — so each is NAMED BY A FIXTURE for
#: `tests/test_refusal_clauses.py::test_every_clause_word_is_named_by_a_fixture_or_listed_
#: with_a_reason`, and so a word that is deleted or respelled fails HERE as well as in the
#: vocabulary pin.
NEW_CLAUSE_WORDS = {
    "armature_core/route_gates.py": (
        "banned_or_excluded_component", "camera_frame_contradicted",
        "camera_frame_has_no_target", "camera_frame_unreadable",
        "conditional_allow_on_a_banned_row", "conditioning_family_absent",
        "frame_illegal", "frame_legality_indeterminate",
        "generator_family_contradicted", "hosted_frame_illegal",
        "hosted_multiple_billable_nodes", "hosted_nodes_without_a_tier",
        "hosted_tier_with_latent_nodes", "hosted_tier_without_hosted_nodes",
        "no_readable_model", "no_seed_population", "ruled_name_with_unknown_suffix",
        "sampler_assertion_contradicted", "sampler_assertion_unchecked",
        "seed_not_pinned", "supplied_frame_contradicts_graph",
        "unknown_conditioning_class", "unrecorded_seed_source",
    ),
    "armature_core/gates.py": (
        "batch_count_is_not_a_count", "batch_expectation_is_not_a_count",
        "batch_image_count_disagrees", "bbox_corners_out_of_order",
        "bbox_is_not_four_numbers", "bbox_outside_the_frame",
        "completeness_over_zero_channels", "experiment_has_no_seed_registry",
        "export_incomplete", "frame_count_changed_through_the_bridge",
        "frame_not_generator_legal", "mask_bbox_is_empty",
        "mask_disagrees_with_projection", "motion_undefined_over_one_frame",
        "openpose_convention_mismatch", "projected_bbox_is_empty",
        "resolution_is_not_a_frame_size", "round_trip_dtype_not_uint8",
        "round_trip_not_lossless", "round_trip_over_zero_frames", "seed_is_not_an_int",
        "seed_not_registered", "seed_registry_is_empty", "subject_never_moved",
        "unknown_animation_mode", "unknown_generator_profile",
    ),
    "armature_core/rig_gates.py": (
        "bbox_diagonal_is_degenerate", "binding_moved_the_mesh",
        "bone_names_do_not_match_registry", "evaluation_is_not_live",
        "fingerprints_carry_no_bones", "liveness_probe_shape_changed",
        "registry_is_empty", "rig_builds_disagree", "round_trip_moved_the_surface",
        "round_trip_probe_window_too_small", "vertex_array_is_empty",
        "vertex_arrays_do_not_correspond",
    ),
    "armature_core/donor_gate.py": (
        "clip_has_no_consecutive_pair", "donor_below_threshold", "frame_sizes_differ",
        "frames_not_numerically_named", "no_frame_carries_landmarks",
        "unreadable_gate_input",
    ),
    "armature_core/subject.py": (
        "half_extent_absent", "half_extent_negative", "half_extent_not_numbers",
        "half_extent_wrong_arity",
    ),
    "armature_core/canon.py": (
        "forbidden_word", "phrase_absent", "phrase_negated", "unlicensed_residue",
    ),
    "armature_core/shotspec.py": (
        "animation_mode_unknown", "asset_missing", "asset_sha256_absent",
        "asset_sha256_mismatch", "camera_clip_range_not_ordered",
        "camera_radius_not_a_number", "camera_target_shape",
        "camera_type_not_implemented", "channel_unknown", "channels_duplicated",
        "channels_empty", "depth_window_not_ordered", "depth_window_shape",
        "edge_normal_angle_out_of_domain", "missing_spec_key",
        "render_engine_unknown", "retired_gates_block", "retired_gates_key",
        "spec_is_not_an_object", "spec_value_not_finite", "spec_value_not_positive",
        "spec_value_wrong_type", "spec_version_unsupported",
    ),
}


def test_every_clause_word_this_wave_adds_is_live_where_it_was_added():
    """The table is load-bearing rather than decorative: a word deleted, respelled or moved
    to another module fails here naming itself, and the same table is what makes each word
    'named by a fixture' for the vocabulary census."""
    import _census_nodes

    sites = _census_nodes.clause_literals()
    for module, words in sorted(NEW_CLAUSE_WORDS.items()):
        for word in words:
            assert word in sites, f"{word} is in no evidence dict under tools/**"
            assert any(s.startswith(module + ":") for s in sites[word]), (
                word, module, sites[word])


#: MEASURED and recorded rather than fixed here: one clause word in this domain that the
#: vocabulary census cannot see, because it is spelled as a KEYWORD to
#: `dict(<comprehension>, gate=..., andon=..., clause=...)` and
#: `_census_nodes.clause_literals` reads a dict LITERAL's key or an `ev["clause"] = ...`
#: assignment. The shape is `donor_gate.ankle_framing`'s, and it is the exemplar
#: `test_gates._dict_call_keyword_keys`' docstring cites, so it is left standing and the
#: word is asserted at RUNTIME here instead. Widening the walk is the tests domain's, wave 26.
CLAUSE_WORDS_THE_VOCABULARY_WALK_CANNOT_SEE = {
    "ankle_fractions_off_different_populations": "armature_core/donor_gate.py",
}


def test_the_clause_word_the_vocabulary_walk_cannot_see_is_asserted_at_runtime():
    import _census_nodes

    sites = _census_nodes.clause_literals()
    for word in CLAUSE_WORDS_THE_VOCABULARY_WALK_CANNOT_SEE:
        assert word not in sites, (
            f"{word} is visible to the walk now — delete its row from "
            f"CLAUSE_WORDS_THE_VOCABULARY_WALK_CANNOT_SEE in the same commit")
    src = inspect.getsource(D.ankle_framing)
    assert 'clause="ankle_fractions_off_different_populations"' in src
