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

import glob
import io
import os
import re
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

from armature_core import aapose, assembly, startframe, turnaround  # noqa: E402
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
    # Executed WITHOUT registering in `sys.modules`: the scratch copy imports
    # `armature_core.errors` absolutely and needs no entry, and an installer that mutates
    # `sys.modules` is an ordering hazard `tests/test_packaging.py`'s derived census
    # (rightly) refuses to let a test add without a pair to exercise its teardown.
    spec = importlib.util.spec_from_file_location("_aapose_scratch", str(scratch))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "SIXTH_DRAWING_CONSTANT" in mod.drawing_constants(), mod.drawing_constants()
    with pytest.raises(mod.ConventionError) as exc:
        mod.check_convention(mod.KEYPOINT_COUNT, mod.LIMB_SEQ, mod.PALETTE)
    ev = exc.value.evidence
    assert ev["clause"] == "drawing_constant_outside_the_record", ev
    assert ev["constants_outside_the_record"] == ["SIXTH_DRAWING_CONSTANT"], ev


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


# ====================================================================== F-0f035830
#
# `<file>.py:<line>` in module prose is a placeholder shaped like evidence: it resolves
# today and rots on the next edit to the file it points at. Measured on `041027c` by
# opening every one of them in the twenty-one owned modules: THIRTEEN were wrong — four
# had become blank lines and nine landed on unrelated code, and four of the thirteen were
# introduced or carried forward by wave-14 fixes. `tests/test_gates.py:860-864` already
# rules for this repo that `(file, function, class)` is the identity that survives an edit
# and a line number is not; the prose never adopted it.
#
# The population is EVERY citation in `tools/armature_core/*.py`, not the thirteen the
# finding named. The census below is the seeds-spec citation census
# (`tests/test_seeds_specs.py`) pointed at this package, with the anchor rule the specs'
# `test_every_citation_names_the_function_that_holds_it` already uses.

#: The anchor spellings this package's prose is allowed to carry.
#:
#: * `<file>.py::<symbol>` — the preferred form. No line number at all, so it cannot rot;
#:   `<symbol>` is a `def`/`class` in that file, a `Class.method`, a module-level
#:   assignment target, or `__main__` for the `if __name__ == "__main__":` handler.
#: * `<file>.py:<line> (<symbol>)` — kept where a test pins the bare `file:line` string
#:   (`tests/test_lift_solve.py` derives `round_trip_report`'s call sites by AST and asserts
#:   the docstrings name them). The symbol must hold the line, so a move out of the function
#:   fires here even though the line is not blank.
#:
#: Anything else is a bare citation and fails.

#: The bare anchors this package deliberately KEEPS, because it corrects in place with the
#: measurement rather than deleting: each is a WRONG anchor quoted inside the sentence that
#: records it as wrong. Measured 2026-09-04; a citation that is neither qualified nor
#: recorded here is what a fourteenth stale one would be.
CORRECTED_ANCHORS = {
    # blender_scene.unfiltered_world_bounds — the wave-10 anchor, now a blank line
    ("blender_scene.py", "probe_subject.py", 75),
    # blender_scene.CompositorWiring — the wave-12 anchor for stage_render's halt handler
    ("blender_scene.py", "stage_render.py", 508),
    # posearc.resolve_arc — drifted onto `gate_objects_registered`
    ("posearc.py", "rig_character.py", 661),
    # sitelist.SiteListError — the three-caller claim F-69733981 corrected
    ("sitelist.py", "rig_character.py", 1135),
    ("sitelist.py", "rig_parts.py", 480),
    ("sitelist.py", "project_pose_keypoints.py", 229),
    # startframe.gate_whole — the parser anchor F-dc4cf57e corrected
    ("startframe.py", "render_start_frame.py", 142),
}

#: Where a cited basename is looked up, in order. `tools/superseded/` is included because a
#: recorded failure kept runnable is a legitimate thing to cite.
CITATION_SEARCH_DIRS = ("tools/armature_core", "tools", "tools/superseded", "tests",
                        "tests/blender")

_LINE_ANCHOR = re.compile(r"\b([A-Za-z0-9_]+[.]py):([0-9]+)")
_QUALIFIED = re.compile(r"\b([A-Za-z0-9_]+[.]py):([0-9]+) \(([A-Za-z0-9_.]+)\)")
_SYMBOL_ANCHOR = re.compile(r"\b([A-Za-z0-9_]+[.]py)::([A-Za-z0-9_.]+)")


def _resolve_cited_file(name):
    for d in CITATION_SEARCH_DIRS:
        path = os.path.join(REPO, *d.split("/"), name)
        if os.path.isfile(path):
            return path
    return None


def _holder_of(path, lineno):
    """The innermost `def`/`class` containing `lineno`, or None for module scope."""
    import ast

    tree = ast.parse(io.open(path, encoding="utf-8").read())
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.lineno <= lineno <= (node.end_lineno or node.lineno):
                if best is None or node.lineno > best.lineno:
                    best = node
    return best


def _defines_symbol(path, symbol):
    """Is `symbol` defined in this file? `def`/`class` at any depth, `Class.method`, a
    module-level assignment target, or `__main__` for the `if __name__ == '__main__':`
    handler."""
    import ast

    src = io.open(path, encoding="utf-8").read()
    if symbol == "__main__":
        return '__name__ == "__main__"' in src or "__name__ == '__main__'" in src
    tree = ast.parse(src)
    if "." in symbol:
        owner, member = symbol.split(".", 1)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == owner:
                return any(isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef,
                                          ast.ClassDef)) and b.name == member
                           for b in node.body)
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == symbol:
                return True
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == symbol:
                    return True
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == symbol:
                return True
    return False


def bad_line_anchors(src, stem):
    """`[(cited, why)]` — every `<file>.py:<line>` in `src` that is not a live, qualified
    anchor and is not a recorded correction."""
    out = []
    qualified = {(m.group(1), int(m.group(2))): m.group(3)
                 for m in _QUALIFIED.finditer(src)}
    for m in _LINE_ANCHOR.finditer(src):
        name, lineno = m.group(1), int(m.group(2))
        if (stem, name, lineno) in CORRECTED_ANCHORS:
            continue
        path = _resolve_cited_file(name)
        if path is None:
            out.append((f"{name}:{lineno}", "the cited file does not exist"))
            continue
        lines = io.open(path, encoding="utf-8").read().splitlines()
        if not 1 <= lineno <= len(lines):
            out.append((f"{name}:{lineno}",
                        f"past the end of a {len(lines)}-line file"))
            continue
        if not lines[lineno - 1].strip():
            out.append((f"{name}:{lineno}", "the cited line is blank"))
            continue
        symbol = qualified.get((name, lineno))
        if symbol is None:
            out.append((f"{name}:{lineno}",
                        f"bare `<file>.py:<line>`; the line reads "
                        f"{lines[lineno - 1].strip()[:60]!r}. Write "
                        f"`{name}::<symbol>`, or `{name}:{lineno} (<symbol>)` where a test "
                        f"pins the bare string"))
            continue
        holder = _holder_of(path, lineno)
        got = holder.name if holder is not None else "<module>"
        if got != symbol.split(".")[-1]:
            out.append((f"{name}:{lineno} ({symbol})",
                        f"that line is in {got}, not in {symbol}"))
    return out


def bad_symbol_anchors(src):
    """`[(cited, why)]` — every `<file>.py::<symbol>` that does not resolve."""
    out = []
    for m in _SYMBOL_ANCHOR.finditer(src):
        name, symbol = m.group(1), m.group(2)
        path = _resolve_cited_file(name)
        if path is None:
            out.append((f"{name}::{symbol}", "the cited file does not exist"))
            continue
        if not _defines_symbol(path, symbol):
            out.append((f"{name}::{symbol}", f"{name} defines no such symbol"))
    return out


@pytest.mark.parametrize("stem", OWNED_MODULES)
def test_every_citation_in_an_owned_module_is_anchored_on_a_symbol(stem):
    """The thirteen, and everything that could become the fourteenth.

    A citation here is either `<file>.py::<symbol>` (no line at all), or
    `<file>.py:<line> (<symbol>)` with the symbol that holds the line, or one of the
    `CORRECTED_ANCHORS` kept as a record of a wrong anchor. Nothing else.
    """
    src = io.open(os.path.join(CORE, stem + ".py"), encoding="utf-8").read()
    bad = bad_line_anchors(src, stem + ".py") + bad_symbol_anchors(src)
    assert bad == [], {stem: bad}


def test_the_census_walks_every_citation_in_the_package_and_says_how_many():
    """The population before the property, and a count a reader can check.

    The nine `armature_core` modules this domain does NOT own are core-gates'; their prose
    is walked for the resolve/blank clause under a measured CEILING, exactly as
    `tests/test_seeds_specs.STALE_CITATIONS_TODAY` does for the specs it does not own — so
    a citation that GOES stale over there fails here and a correction merely makes an entry
    deletable.
    """
    owned = {}
    for stem in OWNED_MODULES:
        src = io.open(os.path.join(CORE, stem + ".py"), encoding="utf-8").read()
        owned[stem] = (len(_LINE_ANCHOR.findall(src)), len(_SYMBOL_ANCHOR.findall(src)))
    n_line = sum(a for a, _b in owned.values())
    n_symbol = sum(b for _a, b in owned.values())
    assert n_line + n_symbol >= 40, owned
    assert n_symbol >= 25, ("the re-anchoring did not happen", owned)

    others = {}
    for path in sorted(glob.glob(os.path.join(CORE, "*.py"))):
        stem = os.path.basename(path)[:-3]
        if stem in OWNED_MODULES:
            continue
        src = io.open(path, encoding="utf-8").read()
        stale = [c for c, _why in bad_line_anchors(src, stem + ".py")
                 if "blank" in _why or "does not exist" in _why or "past the end" in _why]
        if stale:
            others[stem] = len(stale)
    #: Measured 2026-09-04 across the `armature_core` modules core-gates owns. A CEILING,
    #: never an equality: a citation that goes stale over there fails here, and a
    #: correction over there leaves this green and merely makes an entry deletable — the
    #: same treatment `tests/test_seeds_specs.STALE_CITATIONS_TODAY` gives the specs it
    #: does not own.
    STALE_IN_MODULES_THIS_DOMAIN_DOES_NOT_OWN = {"rig_gates": 1, "shotspec": 2}
    over = {k: v for k, v in others.items()
            if v > STALE_IN_MODULES_THIS_DOMAIN_DOES_NOT_OWN.get(k, 0)}
    assert over == {}, {"stale now": others,
                        "measured 2026-09-04": STALE_IN_MODULES_THIS_DOMAIN_DOES_NOT_OWN}


def test_the_census_goes_red_on_a_citation_that_moved_out_of_its_function(tmp_path):
    """The member outside the walk a blank-line check reaches.

    Nine of the thirteen stale citations landed on a line that is NOT blank — that is the
    ordinary way a citation rots, because code grows above it. The scratch module below
    cites a real, non-blank line of a real file, and the symbol says otherwise.
    """
    src = ('"""x. `measure_cascade_clip.py:1 (main)` is the live consumer."""\n')
    lines = io.open(os.path.join(TOOLS, "measure_cascade_clip.py"),
                    encoding="utf-8").read().splitlines()
    assert lines[0].strip(), "line 1 must be non-blank for this proof to mean anything"
    bad = bad_line_anchors(src, "scratch.py")
    assert len(bad) == 1, bad
    assert "not in main" in bad[0][1], bad

    #: and the bare form, which is what the thirteen were
    bare = bad_line_anchors('"""`measure_cascade_clip.py:1` is the live consumer."""\n',
                            "scratch.py")
    assert len(bare) == 1 and "bare `<file>.py:<line>`" in bare[0][1], bare


def test_the_census_goes_red_on_a_symbol_anchor_that_does_not_resolve():
    """The other half: `<file>.py::<symbol>` cannot rot on a line move, but it can name a
    function that was renamed or deleted."""
    assert bad_symbol_anchors("`measure_cascade_clip.py::main`") == []
    bad = bad_symbol_anchors("`measure_cascade_clip.py::no_such_function`")
    assert len(bad) == 1 and "defines no such symbol" in bad[0][1], bad
    gone = bad_symbol_anchors("`no_such_tool.py::main`")
    assert len(gone) == 1 and "does not exist" in gone[0][1], gone


def test_every_recorded_correction_names_the_live_anchor_beside_the_wrong_one():
    """`CORRECTED_ANCHORS` is an exemption, so it is checked rather than trusted.

    Without this clause the exemption would forgive exactly the citations it was written
    for: a module could go on quoting `rig_character.py:1135` as a LIVE anchor and the
    census would wave it through. The rule that separates the two readings is mechanical —
    a correction records the wrong anchor and names the right one, so the module that
    carries a corrected `<file>.py:<line>` must also carry a `<file>.py::<symbol>` anchor
    for the same file. On `041027c` none of the seven modules did, which is what makes this
    a clause and not a formality.
    """
    for stem, name, lineno in sorted(CORRECTED_ANCHORS):
        src = io.open(os.path.join(CORE, stem), encoding="utf-8").read()
        assert f"{name}:{lineno}" in src, (
            stem, name, lineno, "recorded as corrected and no longer cited — delete it")
        live = [m.group(0) for m in _SYMBOL_ANCHOR.finditer(src) if m.group(1) == name]
        assert live, (
            stem, f"{name}:{lineno}",
            "is exempted as a CORRECTION and the module names no live "
            f"`{name}::<symbol>` anchor beside it, so it still reads as a live citation")


# ====================================================================== F-69733981
#
# `sitelist.SiteListError` stated the population its re-classing argument rests on:
# "`validate()` is called by three production Blender tools". Measured — two direct and one
# through a wrapper, and only one of the three line numbers was right. A stated population
# that the tree does not have is how a later session re-deriving it distrusts the whole
# paragraph.


def _direct_callers_of(func_name, module_alias):
    """`{basename: {enclosing symbol}}` for every `<alias>.<func>()` call under `tools/`."""
    import ast

    out = {}
    for root, _dirs, files in os.walk(TOOLS):
        if "superseded" in root.replace("\\", "/").split("/"):
            continue
        for fname in sorted(f for f in files if f.endswith(".py")):
            path = os.path.join(root, fname)
            tree = ast.parse(io.open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                if (isinstance(fn, ast.Attribute) and fn.attr == func_name
                        and getattr(fn.value, "id", None) == module_alias):
                    holder = _holder_of(path, node.lineno)
                    out.setdefault(fname, set()).add(
                        holder.name if holder else "<module>")
    return out


def test_the_sitelist_refusal_states_the_caller_population_the_tree_has():
    """Derived, not typed: the docstring must name the symbols the AST finds.

    Measured 2026-09-04 — `project_pose_keypoints.py:229` was right;
    `rig_character.py:1135` is a docstring line and the real call is inside
    `validate_sitelist`; `rig_parts.py:480` is `db = np.linalg.norm(...)` and
    `grep -n validate tools/rig_parts.py` returns ONE line, a call to the WRAPPER.
    """
    direct = _direct_callers_of("validate", "sitelist")
    assert direct == {"rig_character.py": {"validate_sitelist"},
                      "project_pose_keypoints.py": {"main"}}, direct

    doc = io.open(os.path.join(CORE, "sitelist.py"), encoding="utf-8").read()
    doc = doc.split("class SiteListError")[1].split("STRUCTURAL")[0]
    flat = " ".join(doc.split())
    # The overstated sentence is KEPT — this repo corrects in place with the measurement
    # rather than deleting — but only inside the quotation that records it as wrong.
    assert flat.count("three production Blender tools") == 1, flat[:400]
    assert 'This read "called by three production Blender tools' in flat, (
        "the overstated population is still asserted rather than quoted and corrected")
    assert "TWO direct" in flat and "ONE indirect" in flat, flat[:400]
    for anchor in ("rig_character.py::validate_sitelist",
                   "project_pose_keypoints.py::main", "rig_parts.py::main"):
        assert anchor in doc, anchor

    # and the wrapper, so "one through the wrapper" is the tree's word too
    wrapper = _direct_callers_of("validate_sitelist", "rig_character")
    assert wrapper == {"rig_parts.py": {"main"}}, wrapper


# ====================================================================== F-dc4cf57e
#
# `startframe.gate_whole` said, in the present tense and with a domain hand-off attached,
# that `render_start_frame.py:142-143` declares `--width`/`--height` as `type=int` with no
# positivity bound and that "the parser half is filed for that domain". Both halves are
# false on the merged tree: the anchor drifted onto a docstring line about the render
# engine, and the bound was added in wave 12 as F-34a858f5.


def test_the_start_frame_parser_bound_exists_and_the_docstring_says_so():
    """The claim and its anchor, both re-measured. `require_frame_size` is the symbol; a
    bare `--width=0` is refused there, so the sentence that filed it as open is stale."""
    import ast

    src = io.open(os.path.join(TOOLS, "render_start_frame.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = [n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef) and n.name == "require_frame_size"]
    assert len(fn) == 1, "the closed parser half's symbol is gone; re-derive this"
    body = ast.get_source_segment(src, fn[0])
    assert "v <= 0" in body and "isinstance(v, bool)" in body, body[:400]

    flat = " ".join(startframe.gate_whole.__doc__.split())
    assert flat.count("the parser half is filed for that domain") == 1, (
        "the closed finding is asserted somewhere other than inside the quotation that "
        "records it as closed")
    assert 'It read: "`tools/render_start_frame.py:142-143`' in flat, (
        "the corrected sentence is not quoted, so a reader cannot see what changed")
    assert "render_start_frame.py::require_frame_size" in flat, flat[-600:]
    assert "F-34a858f5" in flat, "the correction does not name what closed it"
    assert "this gate refuses regardless of who calls it" in flat, (
        "the part of the paragraph that is still true was deleted with the part that was not")


# ============================================================== the -O leg, per refusal
#
# CLAUDE.md: gates raise, never `assert` — an `assert` is deleted by `-O` or
# `PYTHONOPTIMIZE=1`, and 87 of facet's andons turned out to be removable by an environment
# variable. Every refusal this amend ADDED mutates the protected thing here and must still
# fire, under the same class name, with assertions gone. The probe runs in a subprocess so
# the flag is real rather than simulated, and the assertions in THIS file are deleted under
# `-O` — which is exactly why the check cannot be one of them.

import json as _json          # noqa: E402
import subprocess as _sub     # noqa: E402
import textwrap as _tw        # noqa: E402

PROBE16 = _tw.dedent(
    """
    import json, sys, types
    sys.path.insert(0, sys.argv[1])

    import numpy as np
    from armature_core import aapose, assembly as AS, turnaround as TA

    asserts_active = False
    try:
        assert False
    except AssertionError:
        asserts_active = True

    KLING = "KlingVideoNode"
    RECEIPT_PAID = {"api_node": True, "measured_with": "get_node",
                    "measured_on": "2026-08-13"}
    RECEIPT_UNDATED = {"api_node": False, "measured_with": "get_node",
                       "measured_on": "yesterday"}

    def _widen(receipt):
        AS.ALLOWED_CLASSES = tuple(AS.ALLOWED_CLASSES) + (KLING,)
        AS.MEASURED_FREE_CLASSES = dict(AS.MEASURED_FREE_CLASSES, **{KLING: receipt})

    def _restore():
        AS.ALLOWED_CLASSES = tuple(c for c in AS.ALLOWED_CLASSES if c != KLING)
        AS.MEASURED_FREE_CLASSES = {k: v for k, v in AS.MEASURED_FREE_CLASSES.items()
                                    if k != KLING}

    def receipt_records_a_paid_node():
        _widen(RECEIPT_PAID)
        try:
            AS.gate_no_paid_nodes({"1": {"class_type": KLING}})
        finally:
            _restore()

    def receipt_date_unreadable():
        _widen(RECEIPT_UNDATED)
        try:
            AS.gate_no_paid_nodes({"1": {"class_type": KLING}})
        finally:
            _restore()

    def hand_eps_moved():
        original = aapose.HAND_EPS
        try:
            aapose.HAND_EPS = 0.9
            aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ,
                                    aapose.PALETTE)
        finally:
            aapose.HAND_EPS = original

    def drawing_constant_outside_the_record():
        original = aapose.PIXEL_WRITERS
        try:
            aapose.PIXEL_WRITERS = tuple(original) + ("banked_source_state",)
            aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ,
                                    aapose.PALETTE)
        finally:
            aapose.PIXEL_WRITERS = original

    def _views(planes):
        return [{"view": i, "sha256": "%064x" % i,
                 **({"pixels": p} if p is not None else {})}
                for i, p in enumerate(planes)]

    def _distinct(n, shape=(64, 64, 4)):
        rng = np.random.default_rng(11)
        return [rng.normal(128.0, 40.0, shape) for _ in range(n)]

    def turn_pair_shapes_differ():
        planes = _distinct(8)
        planes[3] = np.random.default_rng(4).normal(128.0, 40.0, (72, 64, 4))
        TA.gate_set_distinct(_views(planes), 8)

    def turn_partly_attached():
        planes = _distinct(8)
        TA.gate_set_distinct(
            _views([p if i % 2 == 0 else None for i, p in enumerate(planes)]), 8)

    def turn_pixels_unreadable():
        planes = _distinct(8)
        recs = _views(planes)
        recs[5]["pixels"] = "not an array"
        TA.gate_set_distinct(recs, 8)

    def turn_pixels_not_a_plane():
        planes = _distinct(8)
        recs = _views(planes)
        recs[5]["pixels"] = np.zeros(16)
        TA.gate_set_distinct(recs, 8)

    CASES = {
        "receipt_records_a_paid_node": (receipt_records_a_paid_node, "AssemblyGate"),
        "receipt_date_unreadable": (receipt_date_unreadable, "AssemblyGate"),
        "hand_eps_moved": (hand_eps_moved, "ConventionError"),
        "drawing_constant_outside_the_record": (drawing_constant_outside_the_record,
                                                "ConventionError"),
        "turn_pair_shapes_differ": (turn_pair_shapes_differ, "TurnaroundGate"),
        "turn_partly_attached": (turn_partly_attached, "TurnaroundGate"),
        "turn_pixels_unreadable": (turn_pixels_unreadable, "TurnaroundGate"),
        "turn_pixels_not_a_plane": (turn_pixels_not_a_plane, "TurnaroundGate"),
    }

    out = {"asserts_active": asserts_active, "raised": {}}
    for name, (fn, want) in CASES.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
        except BaseException as exc:
            got = type(exc).__name__
            out["raised"][name] = "RAISED" if got == want else "WRONG_ERROR:" + got
    print("AMEND16 " + json.dumps(out))
    """
)


def _run_probe16(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"w16_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(PROBE16, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = ([sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS])
    proc = _sub.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr)
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("AMEND16 ")]
    if not line:
        raise AssertionError(proc.stdout + proc.stderr)
    return _json.loads(line[-1][len("AMEND16 "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_every_refusal_this_amend_added_survives_optimization(tmp_path, flag, env_var,
                                                              label):
    res = _run_probe16(tmp_path, flag=flag, env_var=env_var)
    assert len(res["raised"]) == 8, res["raised"]
    for name, outcome in res["raised"].items():
        assert outcome == "RAISED", f"{label}/{name}: {outcome}"


def test_the_optimization_actually_took_effect_for_the_wave_16_probe(tmp_path):
    """Otherwise the parametrisation above is three copies of the same run."""
    assert _run_probe16(tmp_path, flag=False)["asserts_active"] is True
    assert _run_probe16(tmp_path, flag=True)["asserts_active"] is False
    assert _run_probe16(tmp_path, env_var=True)["asserts_active"] is False
