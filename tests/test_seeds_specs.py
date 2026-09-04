"""Every seed registration carries a machine-readable ceiling.

Wave 3, F-dbc4ed63. Six of the eight `specs/*seeds.json` files carried a `ceiling` key
(E08, E10, E11, E12, E13, E14) and `specs/E09-seeds.json` and `specs/E09-A3-seeds.json`
carried none. Where present the value was free prose ("SIX submissions total, amended
4 -> 6 by ..."), and no tool under `tools/` read the key. CLAUDE.md makes the credit
ceiling a per-spec obligation and records that spent credits have no compensator, so the
one unrecoverable resource in this repo was bounded by a string nothing could parse.

**Correction, wave 6.** This paragraph used to end "while `seeds` and `allocation`, its
machine-readable siblings, are both consumed and gated." Half of that is false and the
whole sentence was the argument for the fix. Measured: `grep -rn allocation tools/
--include=*.py` returns 0 — no tool reads `allocation` at all, so it is exactly as unread
as `ceiling` was. `seeds` alone is consumed and gated: seven builders load
`json.load(fh)["seeds"]` and hand the list to `gates.gate_s_seed_registration` /
`route_gates.gate_s_registration`. The fix to `ceiling` still stands on its own — a bound
nothing can parse is not a bound — but it never had the precedent this sentence claimed,
and `allocation` is a second unread key, recorded here rather than quietly dropped.
`test_only_seeds_is_read_by_a_tool` below is the pin. The same sentence is repeated in
every `specs/*seeds.json` under `ceiling.why_machine_readable`; those files are not this
domain's to edit and are routed.

The prose is not deleted. It moves into `ceiling.note` verbatim, and the number a
submission step can count against sits beside it in `ceiling.submissions`.
"""

import glob
import json
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_SPECS = sorted(glob.glob(os.path.join(REPO, "specs", "*seeds.json")))


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_the_seed_specs_are_found_at_all():
    """A glob that matches nothing would make every check below vacuously green."""
    assert len(SEED_SPECS) >= 8


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_every_seed_spec_carries_seeds_allocation_and_a_numeric_ceiling(path):
    doc = _load(path)
    assert isinstance(doc.get("seeds"), list) and doc["seeds"], "no seeds"
    assert isinstance(doc.get("allocation"), dict) and doc["allocation"], "no allocation"
    ceiling = doc.get("ceiling")
    assert isinstance(ceiling, dict), "ceiling is not machine-readable"
    assert isinstance(ceiling.get("submissions"), int), "ceiling.submissions is not an int"
    assert ceiling["submissions"] > 0
    assert isinstance(ceiling.get("note"), str) and ceiling["note"].strip(), (
        "the prose that used to BE the ceiling must survive in ceiling.note")


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_the_ceiling_is_at_least_the_number_of_seeds_it_registers(path):
    """A ceiling below the list it governs would be a bound the spec's own allocation
    breaks on its first pass. E12 and E13 deliberately run each seed on more than one arm,
    so the relation is >=, not ==."""
    doc = _load(path)
    assert doc["ceiling"]["submissions"] >= len(doc["seeds"]), (
        f"{os.path.basename(path)} registers {len(doc['seeds'])} seed(s) under a ceiling "
        f"of {doc['ceiling']['submissions']}")


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_every_registered_seed_has_an_allocation_row(path):
    doc = _load(path)
    missing = [s for s in doc["seeds"] if str(s) not in doc["allocation"]]
    assert missing == [], f"seeds with no allocation row: {missing}"


# ------------------------------------------------- which of the three keys a tool reads
#
# Wave 6, from the coordinator's tests worklist. The module docstring asserted that
# `allocation` was "consumed and gated". It is not, and this is the pin for the correction:
# a claim about what code reads is checkable in one walk, and it stayed wrong through a
# whole wave because nobody walked it.

import ast

TOOLS = os.path.join(REPO, "tools")
SEED_SPEC_KEYS = ("seeds", "allocation", "ceiling")


def _tool_sources():
    """Every module under `tools/`, the package included, as (path, source)."""
    for root, _dirs, names in os.walk(TOOLS):
        if "superseded" in root.replace("\\", "/").split("/"):
            continue
        for name in sorted(names):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as fh:
                yield path, fh.read()


def _subscript_and_get_keys(src):
    """Every string a module uses as `x["k"]` or `x.get("k")`."""
    keys = set()
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)):
            keys.add(node.slice.value)
        elif (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "get"
              and node.args and isinstance(node.args[0], ast.Constant)
              and isinstance(node.args[0].value, str)):
            keys.add(node.args[0].value)
    return keys


def test_only_seeds_is_read_by_a_tool():
    """The corrected claim, measured rather than asserted.

    What this looks like if the docstring were right: `allocation` would appear here beside
    `seeds`. It does not appear anywhere under `tools/` at all — the same state `ceiling`
    was in when it was filed as a defect.
    """
    readers = {key: [] for key in SEED_SPEC_KEYS}
    for path, src in _tool_sources():
        keys = _subscript_and_get_keys(src)
        for key in SEED_SPEC_KEYS:
            if key in keys:
                readers[key].append(os.path.basename(path))
    assert readers["seeds"], "no tool reads `seeds`; this walk is not reaching tools/"
    assert readers["allocation"] == [], (
        f"`allocation` now has readers ({readers['allocation']}); the module docstring's "
        f"correction is stale and should be rewritten with this measurement")


def test_the_seed_registry_readers_hand_the_list_to_gate_s():
    """What "consumed and gated" means for `seeds`, stated as the thing it is being
    contrasted against: the loaders exist AND a seed gate runs in the same module."""
    loaders = []
    for path, src in _tool_sources():
        if 'json.load(fh)["seeds"]' not in src and '["seeds"]' not in src:
            continue
        if "gate_s_seed_registration" in src or "gate_s_registration" in src \
                or "gate_seed_registered" in src or "def gate_s(" in src:
            loaders.append(os.path.basename(path))
    assert len(loaders) >= 5, (
        f"only {loaders} both read a seeds list and run a seed gate; the docstring's "
        f"surviving claim about `seeds` needs re-measuring")
