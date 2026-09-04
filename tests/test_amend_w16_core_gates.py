"""Wave 16 (core-gates): the guard covered the OPERAND and not the POPULATION around it.

Wave 14 closed `unreadable_node` over the recursion's node ARRAY, routed the measured
quantities of six rig andons through `require_finite`, and re-classed `subject`'s three
shape refusals into the family. Wave 15's auditors measured that each landed one level,
one coercion or one filter away from the population the property has to hold over:

  * `_iter_definitions` guards every entry of `definitions.subgraphs` and never its own
    CONTAINER — a mapping-shaped `subgraphs` yields its string keys, every one is
    `continue`d, and a BANNED weight inside a blueprint is reported as a clean graph;
  * Gate S grades only the noise-bearing samplers, and then states a property of the
    committed list over the empty population an `add_noise=disable` widget leaves behind;
  * `verify`'s receipt is identified downstream by the CO-PRESENCE of two fact keys, one
    of which a public keyword argument of `verify` decides whether to write;
  * `subject.extent_summary`'s `float()` coercion sits one line ABOVE the guards the wave-14
    fix re-classed, so five neighbouring input shapes still leave the family as builtins;
  * `errors.ArmatureError`'s docstring states the evidence contract and cites a check that
    does not make it;
  * Gate DONOR is the one andon in this package whose two MEASURED quantities never pass a
    finiteness test;
  * `seeds()`' save-format branch answers `seed_is_literal` unconditionally while the API
    branch beside it answers three states.

Every test here goes RED on the tree at base `041027c`, and each red is proved on a member
OUTSIDE the population the old check walked — one level up from the array, an all-disable
graph, a receipt written with the seed clause declared NOT CHECKED, a coercion input rather
than a guarded one.
"""

import json
import math
import os
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import gate_saved_graph as GSG  # noqa: E402
from armature_core import donor_gate, subject  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402
from armature_core.errors import ArmatureError, SubjectExtentError  # noqa: E402

NAN = float("nan")
INF = float("inf")

BASE_WEIGHT = "wan2.1_vace_14B_fp16.safetensors"
BANNED_LORA = "causvid_x.safetensors"


def loader(node_id, filename, cls="UNETLoader"):
    return {"id": node_id, "type": cls, "widgets_values": [filename, "default"]}


def ksampler(node_id, seed, control="fixed"):
    return {"id": node_id, "type": "KSampler",
            "widgets_values": [seed, control, 20, 7.0, "euler", "normal", 1.0]}


def advanced(node_id, seed, add_noise="enable", control="fixed"):
    """A `KSamplerAdvanced` in save format: widget 0 is `add_noise`, 1 the seed, 2 control."""
    return {"id": node_id, "type": "KSamplerAdvanced",
            "widgets_values": [add_noise, seed, control, 20, 8.0,
                               "euler", "simple", 0, 10000, "disable"]}


# ==================================================================== F-8c3931cd (CRITICAL)
# `_iter_definitions` guarded the node ARRAY and left its own CONTAINER unguarded — one
# level up from the hole wave 14 closed.


def container(definitions):
    """A save-format graph with one well-formed loader and a caller-shaped `definitions`."""
    return {"nodes": [loader(1, BASE_WEIGHT), ksampler(2, 7)],
            "definitions": definitions}


BLUEPRINT = {"id": "blue1", "name": "blue1",
             "nodes": [loader(83, BANNED_LORA, cls="LoraLoaderModelOnly")]}


@pytest.mark.parametrize("fn", ["components", "seeds", "latents"])
@pytest.mark.parametrize("defs,where", [
    ([{"nodes": []}], "definitions"),
    ("x", "definitions"),
    (7, "definitions"),
])
def test_a_definitions_container_that_is_not_a_mapping_is_gate_route(fn, defs, where):
    """RED on base: measured in this worktree, `components()` on a graph whose
    `definitions` is `[{'nodes': []}]` or the string `'x'` raised a bare
    `AttributeError: 'list' object has no attribute 'get'`. `AttributeError` is not an
    `ArmatureError`, so the halt contract's exit-2 six-key `<TOOL>_HALT` receipt branch is
    bypassed and Gate ROUTE refusing a shape it cannot read is recorded as an unhandled
    crash."""
    with pytest.raises(RG.RouteGate) as exc:
        getattr(RG, fn)(container(defs))
    ev = exc.value.evidence
    assert ev["clause"] == "unreadable_node"
    assert ev["where"] == where
    assert ev["entry_type"] == type(defs).__name__


@pytest.mark.parametrize("subs", [
    {"blue1": BLUEPRINT},
    "x",
    7,
])
def test_a_subgraphs_container_that_is_not_a_list_is_gate_route(subs):
    """RED on base: with `definitions.subgraphs` spelled as a MAPPING keyed by blueprint
    id, iterating the dict yields its string KEYS, every one fails `isinstance(d, dict)`
    and is `continue`d — so the walk entered no blueprint at all and reported the graph
    clean. A string is the same shape one character at a time."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.components(container({"subgraphs": subs}))
    ev = exc.value.evidence
    assert ev["clause"] == "unreadable_node"
    assert ev["where"] == "definitions.subgraphs"
    assert ev["entry_type"] == type(subs).__name__


@pytest.mark.parametrize("stray", [None, "x", 7])
def test_a_definition_entry_that_is_not_a_dict_is_refused_not_skipped(stray):
    """RED on base: the entry was `continue`d. A skipped blueprint is a blueprint no
    clause examined, and this file's whole argument is that "nothing was checkable" and
    "everything checked out" are not the same verdict."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.components(container({"subgraphs": [stray, BLUEPRINT]}))
    ev = exc.value.evidence
    assert ev["clause"] == "unreadable_node"
    assert ev["where"] == "definitions.subgraphs"
    assert ev["index"] == 0
    assert ev["entry_type"] == type(stray).__name__


def test_verify_refuses_the_banned_lora_hidden_under_a_mapping_shaped_subgraphs():
    """THE population proof, and GREEN on base — the direction that spends money.

    Measured in this worktree at base: this graph returned a GREEN verdict reading
    '0 of 1 component(s) classified, 1 unclassified, 0 conditional (credited), 0
    attribution entries matching no loaded component, 1 seed(s) all pinned, 0 of 0
    latent(s) checkable, 1 frame(s) checked and generator-legal' while a CC-BY-NC weight
    sat inside a blueprint the walk never entered. The SAME graph with `subgraphs` as a
    LIST raised RouteGate naming causvid_x.safetensors BANNED."""
    g = container({"subgraphs": {"blue1": BLUEPRINT}})
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 81))
    assert exc.value.evidence["clause"] == "unreadable_node"


def test_the_same_blueprint_under_a_list_is_still_walked_and_still_banned():
    """The direction the new guard may not break: a well-formed container is READ, and the
    weight two levels down is still the headline."""
    g = container({"subgraphs": [BLUEPRINT]})
    with pytest.raises(RG.RouteGate) as exc:
        RG.verify(g, frame=(832, 480, 81))
    assert "causvid" in str(exc.value)


@pytest.mark.parametrize("defs", [{}, None, {"subgraphs": []}, {"subgraphs": None}])
def test_an_absent_or_empty_container_is_still_an_ordinary_graph(defs):
    """The other direction the guard may not break: a graph with no blueprints at all is
    the common case, and `None`/absent/empty is its ordinary spelling."""
    assert [c["file"] for c in RG.components(container(defs))] == [BASE_WEIGHT]


# ==================================================================== F-b6613860 (CRITICAL)
# Gate S's registration clause grades only `live` and then states a property of the
# committed list over the population the `adds_noise` filter emptied.


ALL_DISABLE = {"nodes": [loader(1, BASE_WEIGHT),
                         advanced(4, 999999999, add_noise="disable")]}


def test_gate_s_refuses_a_graph_whose_every_sampler_declines_noise():
    """RED on base: measured in this worktree, `seeds()` returns one record
    `{seed: 999999999, control_after_generate: 'fixed', pinned: True}`,
    `unrecorded_seed_sources` is empty, and `gate_s_registration(g, [7])` RETURNED with
    verdict '0 noise-bearing seed(s), all pinned and all drawn from the committed list of
    1' — a receipt asserting the committed list governed a run whose only sampler carries
    999999999 and whose list is [7]. Gate S's own empty-registry clause and the four
    sibling clauses on these two pages all refuse an empty declared population."""
    with pytest.raises(RG.RouteGate) as exc:
        RG.gate_s_registration(ALL_DISABLE, [7])
    ev = exc.value.evidence
    assert ev["seed_clause_verdict"] == "INDETERMINATE"
    assert ev["seeds"] and all(s["adds_noise"] is False for s in ev["seeds"])
    assert "999999999" in str(exc.value)


def test_the_gate_s_verdict_states_the_population_it_graded():
    """RED on base: the PASS verdict named only the live count and the committed list, so
    a record where one of two samplers was exempted read exactly like a record where every
    seed found was checked. The verdict now carries both numbers and names the exempted
    node."""
    g = {"nodes": [loader(1, BASE_WEIGHT),
                   advanced(3, 4242, add_noise="enable"),
                   advanced(4, 0, add_noise="disable")]}
    ev = RG.gate_s_registration(g, [4242])
    # The prefix the repo's records and reports already quote is unchanged.
    assert ev["verdict"].startswith("1 noise-bearing")
    assert "of 2 seed(s) found" in ev["verdict"]
    assert "add_noise=disable" in ev["verdict"]
    assert "4" in ev["verdict"].split("add_noise=disable")[1]
    assert ev["seeds_found"] == 2 and ev["seeds_noise_bearing"] == 1


def test_the_two_expert_split_still_passes():
    """The direction the new clause may not break: a correct two-expert split has one live
    sampler and one inert one, and demanding the inert seed be registered would be a check
    that fires on a correct graph."""
    g = {"nodes": [loader(1, BASE_WEIGHT),
                   advanced(3, 4242, add_noise="enable"),
                   advanced(4, 0, add_noise="disable")]}
    ev = RG.gate_s_registration(g, [4242])
    assert [s["adds_noise"] for s in ev["seeds"]] == [True, False]


# ======================================================================== F-069ae942 (HIGH)
# The key that IDENTIFIES a `verify` receipt was conditional on a public keyword argument
# of the function that produces it.


RECEIPT_GRAPH = {"nodes": [loader(1, BASE_WEIGHT), ksampler(2, 7)]}


def test_the_verify_receipt_declares_its_own_kind():
    """RED on base: no `receipt` key existed at all, so every downstream reader had to
    infer the receipt's kind from the co-presence of two FACT keys."""
    ev = RG.verify(RECEIPT_GRAPH, frame=(832, 480, 81))
    assert ev["receipt"] == "verify"


@pytest.mark.parametrize("require_pinned_seeds", [True, False])
def test_the_verify_receipt_carries_both_fact_keys_on_every_path(require_pinned_seeds):
    """RED on base for `require_pinned_seeds=False`: measured in this worktree,
    `ev['attribution']` is written on every path but `ev['carries_no_sampler_asserted']`
    is written inside `_seed_population_andon`, which `verify` calls ONLY under
    `if require_pinned_seeds:`. A payload record whose Gate ROUTE receipt was produced with
    the seed clause declared NOT CHECKED was then read by `gate_saved_graph --record` as
    carrying no verify receipt at all, and the run halted naming the wrong defect."""
    ev = RG.verify(RECEIPT_GRAPH, frame=(832, 480, 81),
                   require_pinned_seeds=require_pinned_seeds)
    assert set(GSG.VERIFY_RECEIPT_KEYS) <= set(ev)
    assert ev["carries_no_sampler_asserted"] is False


def test_a_record_built_from_an_unchecked_seed_receipt_is_recognised_not_refused():
    """The converse, in the reader that spends the money: `gate_saved_graph.verify_receipts`
    finds the receipt by CONTENT, and a receipt written with `require_pinned_seeds=False`
    was invisible to it. RED on base."""
    ev = RG.verify(RECEIPT_GRAPH, frame=(832, 480, 81), require_pinned_seeds=False)
    record = {"gates": {"ROUTE": json.loads(json.dumps(ev))}}
    found = GSG.verify_receipts(record)
    assert len(found) == 1
    assert found[0]["receipt"] == "verify"


# ====================================================================== F-3ef0d4b3 (MEDIUM)
# `subject.extent_summary`'s `float()` coercion sits one line ABOVE the guards wave 14
# re-classed, and the wave-14 red proof exercises only the shapes that reach them.


@pytest.mark.parametrize("bad", [
    3.0,                       # TypeError: 'float' object is not iterable
    "abc",                     # ValueError on the character 'a'
    ("a", "b", "c"),           # ValueError on the string component
    {"x": 1, "y": 2, "z": 3},  # ValueError on the KEY 'x'
    [1, 2, None],              # TypeError: float() argument must be ... not 'NoneType'
    object(),                  # TypeError: not iterable
])
def test_the_coercion_refuses_through_the_family_like_the_guards_below_it(bad):
    """RED on base for all six: each left the `ArmatureError` family with a bare builtin,
    so `probe_subject`'s halt handler classified a malformed half-extent as exit 1 (an
    unhandled crash) with no receipt instead of exit 2 with the offending value in the
    evidence — precisely the outcome `SubjectExtentError` exists to prevent."""
    with pytest.raises(SubjectExtentError) as exc:
        subject.extent_summary(bad)
    assert isinstance(exc.value, ArmatureError)
    assert exc.value.evidence["half_extent"] == repr(bad)
    assert exc.value.evidence["andon"] == "SubjectExtentError"


def test_the_live_producers_shape_still_reads():
    """The direction the coercion guard may not break: `blender_scene.world_bounds` hands
    a triple of floats, and integers and numpy-ish reals coerce as before."""
    out = subject.extent_summary([1, 2, 3])
    assert out["extents"] == [2.0, 4.0, 6.0]


# ====================================================================== F-46f34dcb (MEDIUM)
# The base class's docstring stated the evidence contract and cited a check that does not
# make it.


def test_the_base_docstring_cites_the_check_that_actually_pins_the_contract():
    """RED on base: the docstring said `"evidence": null` "is asserted for every tool in
    `tests/test_instrument_exits.py`". Measured in this worktree, `sentinel_violations`
    (:247-250) asserts `isinstance(rec['evidence'], (dict, type(None)))` — 'want an object
    or null' — for the refusal kind, and demands a specific dict ONLY for `kind ==
    'gate'`. With `ArmatureError.__init__` reverted to the pre-wave-14 `evidence or {}`,
    the halt census over `test_instrument_exits.py` stayed GREEN and the single red was
    `test_amend_w14_core_gates.py::test_the_base_class_stores_the_evidence_it_is_given`."""
    doc = ArmatureError.__doc__
    assert "test_the_base_class_stores_the_evidence_it_is_given" in doc
    assert "an object OR a null" in doc


def test_the_halt_contracts_own_checker_accepts_an_object_or_a_null_for_a_refusal():
    """The measurement the corrected docstring now states, asserted rather than described.
    This is what makes the citation checkable instead of a second claim."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_instrument_exits import CONTRACT, SENTINEL_KEYS, sentinel_violations

    def halt(evidence):
        rec = {"tool": "probe", "outcome": CONTRACT["refusal"][1], "gate": None,
               "error": "ArmatureError", "message": "a refusal, not a crash",
               "evidence": evidence}
        assert set(rec) == SENTINEL_KEYS, sorted(rec)
        return "probe_HALT " + json.dumps(rec)

    for evidence in (None, {}, {"k": 1}):
        assert sentinel_violations("probe", halt(evidence), "refusal", 2) == [], evidence


# ====================================================================== F-b935294a (MEDIUM)
# Gate DONOR is the one andon in `armature_core` whose two MEASURED quantities never pass a
# finiteness test.


def _motion(mean):
    return {"mean": mean, "per_pair": [], "n_pairs": 64}


def _framing(fraction):
    return {"both_ankles_in_image": fraction, "frames": [],
            "per_ankle_fraction_of_frames_in_image": {"left_ankle": fraction,
                                                      "right_ankle": fraction}}


@pytest.mark.parametrize("bad", [NAN, INF, -INF])
def test_gate_donor_refuses_a_non_finite_motion_mean(bad):
    """RED on base for NaN: measured in this worktree, `gate_donor` RETURNED with verdict
    'mean consecutive-frame difference nan/255 (>= 2.0) and ankles in image on at least
    nan% of frames (>= 80%)' — an affirmative pass printing the NaN inside the verdict it
    just asserted, because `nan < m_min` is False. Gate DONOR decides whether a clip may be
    a baseline at all."""
    with pytest.raises(donor_gate.DonorGate) as exc:
        donor_gate.gate_donor(_motion(bad), _framing(0.95))
    assert "motion.mean" in str(exc.value)


@pytest.mark.parametrize("bad", [NAN, INF, -INF])
def test_gate_donor_refuses_a_non_finite_framing_fraction(bad):
    """The second measured quantity, on the same page and by the same helper."""
    with pytest.raises(donor_gate.DonorGate) as exc:
        donor_gate.gate_donor(_motion(9.0), _framing(bad))
    assert "framing.both_ankles_in_image" in str(exc.value)


def test_gate_donor_still_passes_a_finite_clip_and_still_fails_a_still_one():
    """Both directions the finiteness guard may not move."""
    ev = donor_gate.gate_donor(_motion(9.0), _framing(0.95))
    assert ev["verdict"].startswith("mean consecutive-frame difference 9.0000/255")
    with pytest.raises(donor_gate.DonorGate, match=r"motion: mean consecutive-frame "
                                                   r"difference 0\.1000/255 is below"):
        donor_gate.gate_donor(_motion(0.1), _framing(0.95))


# ====================================================================== F-c0d9db44 (MEDIUM)
# `seeds()`' save-format branch answers `seed_is_literal` unconditionally while the API
# branch beside it answers three states.


def test_a_truncated_save_format_sampler_is_not_reported_as_a_literal_seed():
    """RED on base: `seed_is_literal` read True unconditionally, including when
    `widgets_values` is shorter than the class's seed slot and `seed` is therefore None —
    and the value is quoted verbatim in Gate S's own refusal message (`literal=...`), so an
    operator reading a Gate S halt on a truncated sampler was told the seed is a literal
    beside a `seed` of None. The API branch two lines above answers three states."""
    g = {"nodes": [{"id": 3, "type": "KSampler", "widgets_values": []}]}
    rec = RG.seeds(g)[0]
    assert rec["seed"] is None
    assert rec["seed_input_present"] is False
    assert rec["seed_is_literal"] is False
    assert rec["pinned"] is False


def test_a_full_save_format_sampler_still_answers_present_and_literal():
    """The direction the mirror may not break: `pinned` stays on the `control == 'fixed'`
    reading, and a complete widget list answers True to both."""
    rec = RG.seeds({"nodes": [ksampler(3, 7)]})[0]
    assert rec["seed"] == 7
    assert rec["seed_input_present"] is True
    assert rec["seed_is_literal"] is True
    assert rec["pinned"] is True
