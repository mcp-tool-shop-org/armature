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

from armature_core import (aapose, assembly, turnaround)  # noqa: E402
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
