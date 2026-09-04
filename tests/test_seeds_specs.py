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


# ---- the SPECS' own copy of the paragraph says what is true (wave 8, F-6c5c537b)
#
# The wave-6 correction landed in this file's docstring and in
# `test_only_seeds_is_read_by_a_tool` above, and the eight `specs/*seeds.json` files kept
# the original sentence verbatim inside `ceiling.why_machine_readable`: "no tool under
# tools/ read the key, while `seeds` and `allocation` — its machine-readable siblings — are
# both consumed and gated", closing "and the number a submission step can count against sits
# beside it". A session reading the spec that governs the one unrecoverable resource in this
# repo was told the credit ceiling is machine-enforced. It is not: no tool reads `ceiling`
# from a seeds spec at all.

FALSIFIED_CLAUSE = "machine-readable siblings"
CORRECTION_MARK = "CORRECTION, 2026-09-04"


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_every_spec_carries_the_correction_rather_than_the_original_claim_alone(path):
    """Correct in place, with the measurement that overturned the claim — never a quiet
    delete. The original sentence stays; the correction stands beside it."""
    why = _load(path)["ceiling"]["why_machine_readable"]
    assert FALSIFIED_CLAUSE in why, (
        "the original claim was deleted rather than corrected; the correction is more "
        "useful than the original and both belong in the record")
    assert CORRECTION_MARK in why, (
        f"{os.path.basename(path)} still carries the wave-3 claim with no correction "
        f"beside it")
    assert "`allocation` has no reader at all" in why
    assert "no tool reads `ceiling` from a seeds spec" in why


def test_the_specs_correction_agrees_with_the_tree_it_describes():
    """The claim and the measurement, taken here rather than trusted. If a builder starts
    counting against `ceiling.submissions`, this test fails and the eight paragraphs are
    rewritten with it — which is the point of pinning a claim about code to a walk.

    family: derived by walking every module under `tools/` (the package included,
    `superseded/` excluded) for `x["k"]` / `x.get("k")` over the three seed-spec keys ->
    `seeds` 6 modules, `allocation` 0, `ceiling` 0.
    """
    readers = {key: [] for key in SEED_SPEC_KEYS}
    for path, src in _tool_sources():
        keys = _subscript_and_get_keys(src)
        for key in SEED_SPEC_KEYS:
            if key in keys:
                readers[key].append(os.path.basename(path))

    assert readers["allocation"] == [], readers["allocation"]
    # `ceiling` IS subscripted under tools/ — by `armature_core.assembly`'s CASCADE slot
    # gate and the builders passing that one, which has nothing to do with a seeds spec.
    # The claim the specs make is narrower and is checked as such: no module that reads a
    # seeds registry also reads a `ceiling` key.
    seeds_readers = set(readers["seeds"])
    assert seeds_readers, "no tool reads `seeds`; this walk is not reaching tools/"
    both = sorted(seeds_readers & set(readers["ceiling"]))
    assert both == [], (
        f"{both} now read BOTH a seeds list and a `ceiling` key; the eight specs' "
        f"correction says nothing counts against ceiling.submissions and it is stale")


# -------------------------------- every spec's citations, not `SEED_SPECS[0]`'s (F-c92a6cfb)
#
# The clause below enforces the repo's law that "a report may not contain a placeholder
# shaped like evidence", and `<file>.py:<line>` is exactly that shape. It used to read
# `_load(SEED_SPECS[0])` inside a NON-parametrized test while its four siblings in this file
# parametrize over the whole derived population — so it examined ONE spec, and `[0]` is
# `E08-seeds.json` by alphabetical accident, which is the one spec re-anchored at the
# wave-10 merge.
#
# Measured 2026-09-04 by running the clause's own three checks over all eight specs: E08 has
# 0 stale of 7 cited; each of E09-A3, E09, E10, E11, E12, E13 and E14 has 4 stale of 7 — 28
# stale citations in committed spend-ceiling specs that the census never opened. Three
# examples, identical across the seven: `build_animate_payload.py:475` is cited as a `seeds`
# reader and reads `uploads = json.load(fh)`; `build_camera_i2v_payload.py:1004` reads an
# f-string about a noise sampler; `build_i2v_payload.py:496` reads
# `if "clip_vision_output" in inp:`.
#
# Correcting the 28 is BUILDERS' (F-5e7fe9dc). This file's half is opening every spec, so
# the ceiling below can only fall.


def _citations(path):
    import re

    why = _load(path)["ceiling"]["why_machine_readable"]
    return re.findall(r"\b([A-Za-z0-9_]+[.]py):([0-9]+)\b", why)


def stale_citations(path):
    """`[(file, line, what that line actually says)]` for one spec's citation paragraph."""
    out = []
    for name, lineno in _citations(path):
        target = os.path.join(TOOLS, name)
        if not os.path.isfile(target):
            out.append((name, lineno, "the file does not exist"))
            continue
        lines = open(target, encoding="utf-8").read().splitlines()
        if not 1 <= int(lineno) <= len(lines):
            out.append((name, lineno, "past the end of the file"))
            continue
        if "seeds" not in lines[int(lineno) - 1]:
            out.append((name, lineno, lines[int(lineno) - 1].strip()))
    return out


#: Measured 2026-09-04 per spec. A CEILING, not equality: builders is re-anchoring the 28
#: stale citations this wave (F-5e7fe9dc), so a spec that gets corrected leaves this file
#: green and its entry merely becomes deletable. A citation that GOES stale fails here.
STALE_CITATIONS_TODAY = {
    "E08-seeds.json": 0,
    "E09-A3-seeds.json": 4,
    "E09-seeds.json": 4,
    "E10-seeds.json": 4,
    "E11-seeds.json": 4,
    "E12-seeds.json": 4,
    "E13-seeds.json": 4,
    "E14-seeds.json": 4,
}


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_every_specs_citations_resolve_to_the_lines_they_claim(path):
    """The clause its four siblings already have: run over EVERY spec.

    A reader re-deriving the ceiling before a spend reads a cited line that says something
    else and concludes the clause moved, while the test written to make exactly that
    impossible passes over one file in eight.
    """
    name = os.path.basename(path)
    assert len(_citations(path)) == 7, (name, _citations(path))
    assert name in STALE_CITATIONS_TODAY, (
        f"{name} is a committed seeds spec with no measured citation count; measure it and "
        f"record it rather than letting it join a census that never opened it")
    stale = stale_citations(path)
    assert len(stale) <= STALE_CITATIONS_TODAY[name], {
        "spec": name,
        "stale now": stale,
        "stale on 2026-09-04": STALE_CITATIONS_TODAY[name],
    }


def test_the_citation_census_opens_every_spec_and_not_the_first_one():
    """The measurement that justifies the widening, kept runnable.

    `SEED_SPECS[0]` is `E08-seeds.json`, and it is the ONLY spec with no stale citation. A
    clause indexed at [0] therefore reported a clean tree over 28 stale `<file>.py:<line>`
    citations in seven committed spend-ceiling specs.
    """
    assert os.path.basename(SEED_SPECS[0]) == "E08-seeds.json", SEED_SPECS[0]
    assert stale_citations(SEED_SPECS[0]) == [], (
        "E08 has stale citations too, so the [0] index was not merely lucky; re-derive this")
    others = {os.path.basename(p): len(stale_citations(p)) for p in SEED_SPECS[1:]}
    assert sum(others.values()) <= 28, others
    assert set(others) == set(STALE_CITATIONS_TODAY) - {"E08-seeds.json"}, sorted(others)
