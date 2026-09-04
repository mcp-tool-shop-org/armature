"""Wave-16 core-solvers amend — the red proofs for seven routed findings plus rule 5.

Every test here was written before the fix it names, run against the wave-16 base
(`041027c`) to see it fail, and run once more with the fix reverted to prove the guard and
not its neighbour is what turns it green.

**The rule this wave adds.** Wave 14's fixes were right one level down and blind one level
up: the fix covered the OPERAND and not the POPULATION around it. So every fixture below
names the population its property must hold over and is proven red on a member OUTSIDE the
subset the old check walked —

* rule 5: not one class but every non-`GateFailure` family class defined in the twenty-one
  modules this domain owns, derived from the modules rather than typed;
* Gate ASSEMBLY: not a missing receipt but a receipt PRESENT and recording `api_node: True`
  — the value, never the key;
* Gate CONV: not the four hand-typed names but every drawing constant the module defines,
  proven on `HAND_EPS`, which the four-name list could not see;
* Gate TURN: not the view records but the ADJACENT PAIRS, proven on a set where every
  record carries a plane and the pair population is still short;
* the citation census: not the seeds specs but `armature_core`'s own prose, proven on a
  citation whose target line is NOT blank — the shape a blank-line walk cannot see.
"""

import io
import json
import os
import sys

import numpy as np
import pytest

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")
CORE = os.path.join(TOOLS, "armature_core")
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import blender_stub  # noqa: E402

from armature_core import aapose, assembly, turnaround  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

#: The twenty-one modules the core-solvers domain owns, from the frozen wave-16 domain map.
#: Written down because the censuses below are claims about THIS population and a reader
#: has to be able to check that the walk covered it.
OWNED_MODULES = (
    "aapose", "assembly", "binding", "blender_scene", "channels", "clipcompare",
    "clipstats", "framing", "glb", "joints", "landmarks", "lift_solve", "openpose",
    "parts", "pngio", "posearc", "resample", "sitelist", "startframe", "turnaround",
    "walk",
)


# ====================================================================== rule 5
#
# ONE evidence contract, four domains, one wave. `armature_core.errors.ArmatureError`
# stores what it is passed; `GateFailure` alone keeps `evidence or {}` because a gate
# builds `ev` as it measures and its clauses index into it. Ten classes in this package
# overrode the base with `self.evidence = evidence or {}`, so the root fix was inert
# wherever one of them raised: a bare-message refusal printed `"evidence": {}` in the
# halt record, and "no receipt" and "a receipt with nothing in it" became the same record.
#
# The population is DERIVED from the twenty-one owned modules, not typed as ten names —
# the shape wave 14's four-name coverage list got wrong one level up.


def _family_classes_in_owned_modules():
    """`{qualified name: class}` for every `ArmatureError` subclass the owned modules
    define, read off the live modules so a class the AST finds and nothing instantiates
    cannot hide."""
    import ast
    import importlib

    out = {}
    with blender_stub.blender_stubbed():
        for stem in OWNED_MODULES:
            path = os.path.join(CORE, stem + ".py")
            tree = ast.parse(io.open(path, encoding="utf-8").read())
            names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            mod = importlib.import_module("armature_core." + stem)
            for name in names:
                cls = getattr(mod, name, None)
                if isinstance(cls, type) and issubclass(cls, ArmatureError):
                    out[f"{stem}.{name}"] = cls
    return out


def test_the_owned_modules_define_the_family_population_this_wave_rules_on():
    """The population before the property. A census that cannot say how many members it
    walked is a census a shrinking walk hides inside."""
    live = _family_classes_in_owned_modules()
    plain = {k: c for k, c in live.items() if not issubclass(c, GateFailure)}
    gates = {k: c for k, c in live.items() if issubclass(c, GateFailure)}
    assert len(live) >= 20, sorted(live)
    assert len(plain) >= 10, sorted(plain)
    assert gates, "the exempt subtree is empty; this census is not reaching the gates"


def test_no_plain_refusal_class_in_this_package_normalises_its_evidence():
    """Rule 5, over the population rather than over the ten names.

    Measured on `041027c`: ten classes across nine modules defined
    `def __init__(self, message, evidence=None): ...; self.evidence = evidence or {}`.
    A subclass outside the `GateFailure` subtree defines no `__init__` at all —
    inheritance already gives it the two-argument shape.
    """
    import ast
    import importlib

    offenders = {}
    for qualified, cls in sorted(_family_classes_in_owned_modules().items()):
        if issubclass(cls, GateFailure):
            continue
        stem, name = qualified.split(".", 1)
        tree = ast.parse(io.open(os.path.join(CORE, stem + ".py"),
                                 encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == name:
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef) and sub.name == "__init__":
                        offenders[qualified] = sub.lineno
    assert offenders == {}, {
        "defines its own __init__ outside the GateFailure subtree": offenders,
        "the contract": "ArmatureError stores what it is passed; GateFailure is the one "
                        "exemption, and its subclasses inherit it rather than redefining it",
    }


def test_a_bare_message_refusal_carries_a_null_receipt_not_an_empty_one():
    """The behaviour the deleted constructors changed, over the whole population.

    `"evidence": null` beside `"gate": null` is the honest halt record for a refusal that
    carries no measurement. `{}` says a receipt was built and came back empty.
    """
    wrong = {}
    for qualified, cls in sorted(_family_classes_in_owned_modules().items()):
        if issubclass(cls, GateFailure):
            continue
        got = cls("a refusal with no measurement").evidence
        if got is not None:
            wrong[qualified] = repr(got)
    assert wrong == {}, {"manufactured a receipt for a bare message": wrong}


def test_the_gate_subtree_keeps_its_empty_dict_because_clauses_index_into_ev():
    """The exemption, asserted so deleting the ten does not quietly delete the eleventh."""
    for qualified, cls in sorted(_family_classes_in_owned_modules().items()):
        if issubclass(cls, GateFailure):
            assert cls("a gate fired").evidence == {}, qualified


def test_every_family_class_here_stores_the_dict_it_is_given_by_identity():
    """Clause 2 of the contract: the dict the raising line passed is the dict the halt
    handler reads — identity, not equality."""
    for qualified, cls in sorted(_family_classes_in_owned_modules().items()):
        sentinel = {"measured": 1, "threshold": 2}
        assert cls("m", sentinel).evidence is sentinel, qualified


# ====================================================================== F-1f5282d5
#
# Gate ASSEMBLY's free-measurement clause keyed on the PRESENCE of a key in
# `MEASURED_FREE_CLASSES` while its refusal message and its verdict both said "a recorded
# api_node: false measurement". The population it must rule on is not "classes with a row"
# but "classes whose row RECORDS api_node false, on a date that can be read" — so the red
# proofs below drive the two members a membership test cannot see: a receipt PRESENT and
# recording `api_node: True`, and a receipt present, empty, and therefore recording nothing.
#
# The operand is the one widening `parts.narrowed` still permits and the one the module
# docstring names as this clause's reason for existing: a diff to `ALLOWED_CLASSES` itself.

KLING = "KlingVideoNode"


def _widened(monkeypatch, receipt):
    """`ALLOWED_CLASSES` widened by one partner class, with the receipt under test."""
    monkeypatch.setattr(assembly, "ALLOWED_CLASSES",
                        tuple(assembly.ALLOWED_CLASSES) + (KLING,))
    table = dict(assembly.MEASURED_FREE_CLASSES)
    if receipt is not None:
        table[KLING] = receipt
    monkeypatch.setattr(assembly, "MEASURED_FREE_CLASSES", table)
    return {"1": {"class_type": KLING}}


@pytest.mark.parametrize("receipt, why", [
    ({"api_node": True, "measured_with": "get_node", "measured_on": "2026-08-13"},
     "a receipt recording the class as a PAID node"),
    ({}, "a receipt with nothing recorded in it"),
    ({"measured_with": "get_node", "measured_on": "2026-08-13"},
     "a receipt with every key but the one the clause claims to read"),
    ({"api_node": "false", "measured_with": "get_node", "measured_on": "2026-08-13"},
     "the string 'false', which is truthy"),
    ({"api_node": 0, "measured_with": "get_node", "measured_on": "2026-08-13"},
     "0, which is equal to False and is not False"),
])
def test_a_receipt_that_does_not_record_api_node_false_is_refused(monkeypatch, receipt,
                                                                  why):
    """The member outside the population the membership test walked: the row EXISTS.

    On `041027c` every one of these five returned the full success verdict, because the
    class was in the dict. `is not False` is deliberate — `0 == False` is True in Python,
    and a receipt carrying `0` records a number, not a measurement.
    """
    graph = _widened(monkeypatch, receipt)
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes(graph)
    ev = exc.value.evidence
    assert ev["clause"] == "class_without_a_recorded_free_measurement", (why, ev)
    assert KLING in ev["classes_measured_as_paid"], (why, ev)
    assert ev["classes_without_a_free_measurement"] == [], ev


def test_the_class_with_no_receipt_at_all_is_still_refused_and_named_separately():
    """The reading the old clause DID catch, kept, and now reported under its own key so a
    reader can tell "nobody measured it" from "somebody measured it and it costs"."""
    graph = {"1": {"class_type": KLING}}
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes(graph, allowed=None)
    ev = exc.value.evidence
    assert ev["clause"] == "class_not_named_by_the_allowlist", ev


def test_a_receipt_whose_measurement_date_cannot_be_read_is_refused(monkeypatch):
    """The dating seed. Nothing in the tree read `measured_on`; the one assertion that
    mentioned it tested truthiness, so `'yesterday'` passed."""
    graph = _widened(monkeypatch, {"api_node": False, "measured_with": "get_node",
                                   "measured_on": "yesterday"})
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes(graph)
    ev = exc.value.evidence
    assert ev["clause"] == "class_with_an_unreadable_measurement_date", ev
    assert "'yesterday'" in ev["classes_with_an_unreadable_measurement_date"][KLING]


def test_a_receipt_with_no_measurement_date_at_all_is_refused(monkeypatch):
    """A default that disarms a clause is a refusal: an absent `measured_on` must not read
    as "current"."""
    graph = _widened(monkeypatch, {"api_node": False, "measured_with": "get_node"})
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes(graph)
    assert exc.value.evidence["clause"] == "class_with_an_unreadable_measurement_date"


def test_the_verdict_states_the_ages_it_read_and_the_window_it_read_them_against():
    """The sentence the gate prints is the sentence the gate checked."""
    ev = assembly.gate_no_paid_nodes({"1": {"class_type": "LoadImage"},
                                      "2": {"class_type": "SaveVideo"}})
    assert set(ev["measurement_age_days"]) == {"LoadImage", "SaveVideo"}, ev
    assert ev["measurement_window_days"] == assembly.MEASUREMENT_WINDOW_DAYS
    assert "recorded api_node value READS False" in ev["verdict"]
    assert f"{assembly.MEASUREMENT_WINDOW_DAYS}-day window" in ev["verdict"]
    assert ev["classes_measured_as_paid"] == {}


def test_a_reading_past_the_window_is_reported_advisory_rather_than_assumed_current():
    """The licence map's own convention, on this table. Pinned against a fixed `today` so
    the assertion is about the rule and not about the day the suite runs."""
    import datetime

    rec = {"api_node": False, "measured_with": "get_node", "measured_on": "2026-08-13"}
    fresh, raw = assembly.measurement_age_days(rec, today=datetime.date(2026, 9, 4))
    assert (fresh, raw) == (22, "2026-08-13")
    aged, _ = assembly.measurement_age_days(rec, today=datetime.date(2027, 1, 1))
    assert aged == 141 and aged > assembly.MEASUREMENT_WINDOW_DAYS
    assert assembly.measurement_age_days({}, today=datetime.date(2026, 9, 4)) == (None,
                                                                                 None)
    assert assembly.measurement_age_days(None)[0] is None


# ====================================================================== F-33d53180
#
# Gate CONV's coverage was a list of four names typed into `_compare_drawing_constants`,
# whose docstring called them "The four module constants that decide what pixels are
# drawn". A fifth already existed: `HAND_EPS`, read by `draw_hand` at every hand limb and
# every hand joint dot, in neither `RECORDED_CONVENTION` nor the comparison — so outside
# `RECORDED_CONVENTION_SHA256` and outside the gate.
#
# The population is not "four constants" and not "five". It is every module-level constant
# this module's PIXEL WRITERS read, derived from the module's own AST — so the proofs below
# drive both the instance (`HAND_EPS`) and the class (a constant that exists nowhere in this
# repo, added to a scratch copy of the module).


def test_hand_eps_is_in_the_record_and_gate_conv_fires_when_it_moves(monkeypatch):
    """The fifth constant the four-name list could not see.

    Measured on `041027c` with `HAND_EPS` set to 0.9 — which skips every hand stroke and
    every hand dot on a normalised coordinate — `check_convention(len(KEYPOINT_NAMES),
    LIMB_SEQ, PALETTE)` returned `verdict: PASS`, the unchanged detail line,
    `n_fields_compared: 9`, `n_fields_in_record: 13`.
    """
    assert aapose.RECORDED_CONVENTION["hand_eps"] == aapose.HAND_EPS
    monkeypatch.setattr(aapose, "HAND_EPS", 0.9)
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)
    ev = exc.value.evidence
    assert ev["clause"] == "convention_nonconformance", ev
    assert any("hand_eps" in p for p in ev["problems"]), ev["problems"]


@pytest.mark.parametrize("const, bad", [
    ("HAND_EPS", 0.9),
    ("KEYPOINT_COUNT", 18),
    ("LIMB_BRIGHTNESS", 1.0),
    ("HAND_KEYPOINT_COUNT", 18),
    ("HAND_JOINT_COLOR", (255, 0, 0)),
    ("DEFAULT_THRESHOLD", 0.0),
    ("HAND_EDGES", ((0, 1),)),
    ("LIMB_SEQ", ((2, 3),)),
])
def test_gate_conv_fires_on_every_constant_the_derivation_finds(const, bad, monkeypatch):
    """The wave-14 parametrize widened to the DERIVED population rather than to five
    names. `PALETTE` is the ninth and is driven by `_compare_against_record` as well, so
    it is covered twice and left out of this table to keep each case single-clause."""
    assert const in aapose.drawing_constants(), aapose.drawing_constants()
    monkeypatch.setattr(aapose, const, bad)
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)
    problems = exc.value.evidence["problems"]
    assert any(const.lower() in p.lower() for p in problems), problems


def test_the_compared_set_is_derived_from_the_module_not_typed():
    """Coverage as a measurement of this module. Every derived drawing constant has a
    recorded value and rides `RECORD_FIELDS_COMPARED`; nothing is a hand-typed name."""
    derived = aapose.drawing_constants()
    assert "HAND_EPS" in derived, derived
    for name in derived:
        assert name.lower() in aapose.RECORDED_CONVENTION, name
        assert name.lower() in aapose.RECORD_FIELDS_COMPARED, name
    assert set(aapose.RECORD_FIELDS_COMPARED) == (
        {n.lower() for n in derived} | set(aapose.NON_DRAWING_FIELDS_COMPARED))
    v = aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)
    assert v["n_fields_compared"] == len(aapose.RECORD_FIELDS_COMPARED)
    assert v["fields_compared"] == sorted(aapose.RECORD_FIELDS_COMPARED)


def test_the_digest_pins_the_record_as_written_after_the_deliberate_re_record():
    import hashlib as _h
    import json as _j

    blob = _j.dumps(aapose.RECORDED_CONVENTION, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")
    assert _h.sha256(blob).hexdigest() == aapose.RECORDED_CONVENTION_SHA256
    assert aapose.RECORDED_CONVENTION_SHA256 != (
        "90489445a74fe61343136677d99515256e663290c5ae49a27d5c06748eff84f5"), (
        "the record grew two fields and the pin was not recomputed")


def test_a_sixth_drawing_constant_cannot_be_added_silently(tmp_path):
    """The CLASS, proven on a member that exists nowhere in this repo.

    A scratch copy of the module gains a module-level constant and a read of it inside
    `draw_hand`. Nobody has typed its name anywhere, so a four-name list — or a nine-name
    one — cannot see it. The derivation finds it and `check_convention` refuses
    `drawing_constant_outside_the_record` before it compares anything.
    """
    import importlib.util

    src = io.open(os.path.join(CORE, "aapose.py"), encoding="utf-8").read()
    # The copy is imported as a standalone module, so the package-relative import has to
    # be spelled absolutely. Nothing else about the source changes but the sixth constant.
    src = src.replace("from .errors import ArmatureError",
                      "from armature_core.errors import ArmatureError", 1)
    src = src.replace("\nHAND_EPS = 0.01\n",
                      "\nHAND_EPS = 0.01\nSIXTH_DRAWING_CONSTANT = 3\n", 1)
    src = src.replace("    H, W = canvas.shape[:2]\n    sw = hand_stickwidth(H, W, stickwidth_type)\n",
                      "    H, W = canvas.shape[:2]\n    sw = hand_stickwidth(H, W, stickwidth_type)"
                      " + 0 * SIXTH_DRAWING_CONSTANT\n", 1)
    assert "SIXTH_DRAWING_CONSTANT = 3" in src and src.count("SIXTH_DRAWING_CONSTANT") == 2

    scratch = tmp_path / "aapose_scratch.py"
    scratch.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_aapose_scratch", str(scratch))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_aapose_scratch"] = mod
    try:
        spec.loader.exec_module(mod)
        assert "SIXTH_DRAWING_CONSTANT" in mod.drawing_constants(), mod.drawing_constants()
        with pytest.raises(mod.ConventionError) as exc:
            mod.check_convention(mod.KEYPOINT_COUNT, mod.LIMB_SEQ, mod.PALETTE)
        ev = exc.value.evidence
        assert ev["clause"] == "drawing_constant_outside_the_record", ev
        assert ev["constants_outside_the_record"] == ["SIXTH_DRAWING_CONSTANT"], ev
    finally:
        sys.modules.pop("_aapose_scratch", None)


# ============================================== F-e207fd20 and F-1935e0e1 (Gate TURN)
#
# `_pixel_pairs` returned `compared` = the number of view RECORDS carrying a plane, and
# `gate_set_distinct` spent that number in "distinct in PIXELS over {compared} of {n}
# view(s)" — a claim about COMPARISONS PERFORMED — and keyed the branch that calls
# `min(distances)` on it. The two are different populations: `distances` accumulates only
# for ADJACENT pairs where both planes are present and their strided shapes match.
#
# The population the verdict rules on is adjacent PAIRS. The proofs drive both members the
# record count cannot see: a set where every record carries a plane and pairs are still
# dropped (unequal shapes), and a set where only some records carry one.


def _turn_view(i, plane=None):
    rec = {"view": i, "sha256": f"{i:064x}"}
    if plane is not None:
        rec["pixels"] = plane
    return rec


def _distinct_planes(n, shape=(64, 64, 4), seed=11):
    rng = np.random.default_rng(seed)
    return [rng.normal(128.0, 40.0, shape) for _ in range(n)]


def test_a_view_whose_plane_is_a_different_size_is_refused_not_absorbed():
    """The finding's operand, and the member outside the record-count walk: EVERY record
    carries a plane, so `compared == 8`, and two of the seven adjacent pairs are still
    dropped.

    Measured on `041027c` with eight 64x64x4 planes and view 3 re-rendered at 72x64:
    `n_views_compared_in_pixels: 8` and verdict "...distinct in PIXELS over 8 of 8
    view(s): closest adjacent pair 1 mean absolute difference", while
    `adjacent_pixel_distances` carried 5 entries of 7 and view 3 was compared to nothing.
    """
    planes = _distinct_planes(8)
    planes[3] = np.random.default_rng(4).normal(128.0, 40.0, (72, 64, 4))
    records = [_turn_view(i, p) for i, p in enumerate(planes)]
    with pytest.raises(turnaround.TurnaroundGate) as exc:
        turnaround.gate_set_distinct(records, 8)
    ev = exc.value.evidence
    assert ev["clause"] == "adjacent_pair_shapes_differ", ev
    assert ev["n_views_carrying_pixels"] == 8, ev
    assert ev["n_adjacent_pairs"] == 7, ev
    assert ev["n_adjacent_pairs_compared"] == 5, ev
    assert ev["n_adjacent_pairs_skipped_for_shape"] == 2, ev
    assert [k["pair"] for k in ev["adjacent_pairs_skipped_for_shape"]] == [[2, 3], [3, 4]]


def test_a_partly_attached_set_is_refused_rather_than_partly_compared():
    """Operand (a) from the finding: only even-indexed views carry a plane, so
    `compared == 4` and `distances == []`. The verdict branch was keyed on `compared`, so
    it called `min([])` and raised `ValueError: min() iterable argument is empty` — not in
    the `ArmatureError` family, so the 21-tool halt contract records the render tool as
    "FAILED — an unhandled error" at exit 1, after the eight views are already on disk.
    """
    planes = _distinct_planes(8)
    records = [_turn_view(i, planes[i] if i % 2 == 0 else None) for i in range(8)]
    with pytest.raises(turnaround.TurnaroundGate) as exc:
        turnaround.gate_set_distinct(records, 8)
    ev = exc.value.evidence
    assert ev["clause"] == "views_without_pixels", ev
    assert ev["n_views_carrying_pixels"] == 4, ev
    assert ev["views_without_pixels"] == [1, 3, 5, 7], ev


def test_the_untyped_valueerror_is_gone_from_both_directions():
    """Both operands the finding measured, asserted on the FAMILY rather than on a
    message: whatever fires, it is a refusal the halt contract can classify."""
    planes = _distinct_planes(8)
    partial = [_turn_view(i, planes[i] if i % 2 == 0 else None) for i in range(8)]
    unequal = [_turn_view(i, np.random.default_rng(i).normal(
        128.0, 40.0, (64 + i, 64, 4))) for i in range(8)]
    for records, why in ((partial, "partial attachment"), (unequal, "unequal shapes")):
        with pytest.raises(turnaround.TurnaroundGate) as exc:
            turnaround.gate_set_distinct(records, 8)
        assert isinstance(exc.value, ArmatureError), why
        assert exc.value.gate == "TURN", why
        assert exc.value.evidence.get("clause"), why


@pytest.mark.parametrize("bad, clause", [
    ("not an array", "pixels_unreadable"),
    ([[1, 2], [3]], "pixels_unreadable"),
    (np.zeros(16), "pixels_not_a_plane"),
])
def test_a_pixels_value_numpy_cannot_read_as_a_plane_is_a_typed_refusal(bad, clause):
    """`np.asarray` raises whatever numpy raises, and none of it is in the family. A gate
    that cannot read its input refuses at exit 2 naming the view."""
    planes = _distinct_planes(8)
    records = [_turn_view(i, planes[i]) for i in range(8)]
    records[5]["pixels"] = bad
    with pytest.raises(turnaround.TurnaroundGate) as exc:
        turnaround.gate_set_distinct(records, 8)
    ev = exc.value.evidence
    assert ev["clause"] == clause, ev
    assert ev["unreadable_view"] == 5, ev


def test_the_verdict_is_quoted_over_the_pairs_it_compared():
    """The sentence names the population each number belongs to: pairs compared out of
    pairs available, and views carrying a plane out of views."""
    records = [_turn_view(i, p) for i, p in enumerate(_distinct_planes(8))]
    ev = turnaround.gate_set_distinct(records, 8)
    assert ev["n_views_carrying_pixels"] == 8
    assert ev["n_adjacent_pairs"] == 7
    assert ev["n_adjacent_pairs_compared"] == 7
    assert ev["n_adjacent_pairs_skipped_for_shape"] == 0
    assert "over 7 of 7 adjacent pair(s)" in ev["verdict"], ev["verdict"]
    assert "8 of 8 view(s) carried a plane" in ev["verdict"], ev["verdict"]
    assert "n_views_compared_in_pixels" not in ev, (
        "the key whose name claimed comparisons and counted records is gone")


def test_the_digest_only_diagnostic_path_still_says_it_ruled_on_bytes_only():
    """Rule 4: the clause is armed by its caller this wave, and where no caller attaches a
    plane the verdict says the pixel comparison did not happen rather than reading as
    though it did."""
    ev = turnaround.gate_set_distinct(
        [_turn_view(i) for i in range(8)], 8)
    assert ev["n_views_carrying_pixels"] == 0
    assert ev["n_adjacent_pairs_compared"] == 0
    assert ev["min_adjacent_pixel_distance"] is None
    assert "NOT compared" in ev["verdict"]
