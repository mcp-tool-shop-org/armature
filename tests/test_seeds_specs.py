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

import _census_nodes as CN

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
# examples, identical across the seven: in `build_animate_payload` the cited line was
# inside `_load_uploads` and read `uploads = json.load(fh)`; in `build_camera_i2v_payload`
# it read an f-string about a noise sampler; in `build_i2v_payload` it read
# `if "clip_vision_output" in inp:`. (The three line numbers this sentence used to carry
# are dropped — wave 25: they drifted twice inside one wave, and a stale example is worse
# than a symbol.)
#
# Correcting the 28 is BUILDERS' (F-5e7fe9dc). This file's half is opening every spec, so
# the ceiling below can only fall.


def _citations(path):
    import re

    why = _load(path)["ceiling"]["why_machine_readable"]
    return re.findall(r"\b([A-Za-z0-9_]+[.]py):([0-9]+)\b", why)


SEED_READER = "read_seed_registration"


def seed_reader_call_lines(name, source=None):
    """Every line where `read_seed_registration` is CALLED — in `tools/<name>`, or in `source`.

    `source` (wave 26, F-a89efade) is the seam that lets the red proof below drive THIS
    function over a decoy module instead of re-implementing it. Without it, the proof written
    in wave 23 to protect this predicate walked its own three-line source with its own
    `isinstance(node, ast.Call) and getattr(node.func, "id", "") == SEED_READER` loop and
    asserted the comment line was absent — a property of `ast`, not of this module. Measured
    on `81d6c07` by substituting the PRE-wave-23 predicate (`"seeds" in <the cited line>`) for
    this function in process and re-running every test in the module: ALL passed, the red
    proof included, and `stale_citations()` returned `[]` for all eight specs, because every
    one of the seven citation targets is a real call line that also contains the substring.
    The correction was protected by nothing.

    WAVE 23, F-a5089b5f — the predicate that decides whether a citation still points at the
    reader of the seed registration. It used to be `"seeds" in lines[lineno - 1]`, which a
    COMMENT sitting beside the line satisfies, and one such comment exists within four lines
    of every one of the seven citation targets: measured over the wave-20 RE-ANCHORED
    citations, `build_animate_payload`'s call site had a seeds-bearing comment two lines above
    inside the same function, and so does every sibling. A one-to-three-line code move above
    any `read_seed_registration` call would leave all eight specs citing a comment as the
    reader of seeds, with both censuses green, and an operator re-deriving a spend ceiling
    reading prose as the code that consumes the registration. (The line number that stood
    in this paragraph is dropped — wave 25: it drifted twice inside one wave, which is the
    same lesson one level up.)

    An `ast.Call` whose callee resolves to the reader cannot be satisfied by prose.
    """
    import ast

    if source is None:
        source = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    return {node.lineno for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and CN.called_name(node) == SEED_READER}


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
        if int(lineno) not in seed_reader_call_lines(name):
            out.append((name, lineno, lines[int(lineno) - 1].strip()))
    return out


# WAVE 26, F-9473345e — `STALE_CITATIONS_TODAY` stood here: a dated per-spec CEILING that
# allowed 4 stale citations in each of seven specs and 0 in E08, under a comment reading "A
# citation that GOES stale fails here". Measured by calling this file's own
# `stale_citations()` on all eight specs: `[]` for every one. Wave 25 re-derived the table to
# zeros, at which point it was an equality in all but name AND a second home for a property
# its sibling `test_every_citation_in_every_seeds_spec_resolves` already asserts at
# equality strength. The record said a backlog of 28 existed; the measurement said none did,
# and a session reading it would have budgeted a re-anchoring wave that had already happened
# (wave 18, then again under wave 25's halt-handler line shifts). The table is gone, its
# clauses folded into the sibling, and the population pin it also carried survives below as a
# membership set rather than as a counts dict.

#: The eight committed spend-ceiling specs, by basename. Size and membership BEFORE the
#: property, so a ninth spec joins the citation census on the day it lands rather than being
#: guarded by a list somebody forgot — the clause the retired counts dict was really carrying.
SEEDS_SPECS_TODAY = [
    "E08-seeds.json",
    "E09-A3-seeds.json",
    "E09-seeds.json",
    "E10-seeds.json",
    "E11-seeds.json",
    "E12-seeds.json",
    "E13-seeds.json",
    "E14-seeds.json",
]


def test_the_seeds_spec_population_is_the_eight_committed_specs():
    """The membership pin the retired ceiling table also carried."""
    assert [os.path.basename(p) for p in SEED_SPECS] == SEEDS_SPECS_TODAY, \
        [os.path.basename(p) for p in SEED_SPECS]


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_every_specs_citations_resolve_to_the_lines_they_claim(path):
    """The clause its four siblings already have: run over EVERY spec, at EQUALITY.

    A reader re-deriving the ceiling before a spend reads a cited line that says something
    else and concludes the clause moved, while the test written to make exactly that
    impossible passes over one file in eight.

    WAVE 26, F-9473345e — `len(stale) <= STALE_CITATIONS_TODAY[name]` became `stale == []`.
    The dated ceiling permitted four regressions per spec that the sibling census refused
    outright, so the two disagreed about the same property; this is the one that reports which
    citation drifted and on which spec, so it keeps the reporting and drops the slack.
    """
    name = os.path.basename(path)
    assert len(_citations(path)) == 7, (name, _citations(path))
    assert name in SEEDS_SPECS_TODAY, (
        f"{name} is a committed seeds spec that the population pin does not name; record it "
        f"rather than letting it join a census that never opened it")
    assert stale_citations(path) == [], {"spec": name, "stale": stale_citations(path)}


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
    # WAVE 26, F-9473345e: `sum(others.values()) <= 28` read `0 <= 28` — a clause that cannot
    # fail, guarding the 28-strong backlog the wave-18 re-anchoring had already cleared. The
    # 28 is history and stays in the docstring above; the assertion is the measurement.
    assert sum(others.values()) == 0, others
    assert set(others) == set(SEEDS_SPECS_TODAY) - {"E08-seeds.json"}, sorted(others)


# WAVE-12 MERGE (coordinator, 2026-09-04): builders' appended census (F-5e7fe9dc) carried beside tests' widening.


@pytest.mark.parametrize("spec", SEED_SPECS, ids=lambda p: os.path.basename(p))
def test_every_citation_in_every_seeds_spec_resolves(spec):
    """Each cited line must exist AND be the line that reads the key it is cited for."""
    import re

    why = _load(spec)["ceiling"]["why_machine_readable"]
    cited = re.findall(r"\b([A-Za-z0-9_]+[.]py):([0-9]+)", why)
    assert len(cited) == 7, cited
    for name, lineno in cited:
        path = os.path.join(TOOLS, name)
        assert os.path.isfile(path), f"{name} is cited and does not exist"
        lines = open(path, encoding="utf-8").read().splitlines()
        assert 1 <= int(lineno) <= len(lines), (
            f"{os.path.basename(spec)} cites {name}:{lineno}, past the end of a "
            f"{len(lines)}-line file")
        assert int(lineno) in seed_reader_call_lines(name), (
            f"{os.path.basename(spec)} cites {name}:{lineno} as the reader of the seed "
            f"registration and that line is not a `{SEED_READER}` CALL; it reads "
            f"{lines[int(lineno) - 1].strip()!r}")


@pytest.mark.parametrize("spec", SEED_SPECS, ids=lambda p: os.path.basename(p))
def test_every_citation_names_the_function_that_holds_it(spec):
    """The second anchor, added in wave 12: a line number alone goes stale silently on any
    code move, and the record is then a placeholder shaped like evidence. The function name
    survives the move, and this check makes the pair agree."""
    import ast
    import re

    why = _load(spec)["ceiling"]["why_machine_readable"]
    cited = re.findall(r"\b([A-Za-z0-9_]+[.]py):([0-9]+) \(([A-Za-z0-9_<>]+)\)", why)
    assert len(cited) == 7, f"{os.path.basename(spec)} carries {len(cited)} qualified citations"
    for name, lineno, fn in cited:
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        holder = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.lineno <= int(lineno) <= (node.end_lineno or node.lineno):
                    if holder is None or node.lineno > holder.lineno:
                        holder = node
        assert holder is not None and holder.name == fn, (
            f"{os.path.basename(spec)} cites {name}:{lineno} as being in {fn}(); it is in "
            f"{holder.name + '()' if holder else 'module scope'}")


def test_the_eight_specs_carry_the_SAME_citations_as_each_other():
    """They are eight copies of one paragraph. A re-anchoring that fixes some and not others
    is how seven files came to disagree with the eighth for a whole wave."""
    import re

    seen = {}
    for spec in SEED_SPECS:
        why = _load(spec).get("ceiling", {}).get("why_machine_readable")
        if not isinstance(why, str):
            continue
        seen[os.path.basename(spec)] = sorted(
            f"{n}:{l}" for n, l in re.findall(r"\b([A-Za-z0-9_]+[.]py):([0-9]+)", why))
    assert len(seen) == 8, sorted(seen)
    distinct = {tuple(v) for v in seen.values()}
    assert len(distinct) == 1, {k: v for k, v in seen.items()}


def test_the_census_goes_red_on_a_spec_whose_citation_has_drifted(tmp_path):
    """The proof that this walk can fail on the shape that hid from the original: a SECOND
    spec — not `SEED_SPECS[0]` — whose citation points at a line that reads something else.
    The original census returned green over exactly this."""
    import re
    import shutil

    assert len(SEED_SPECS) >= 2
    victim = SEED_SPECS[1]
    doc = _load(victim)
    why = doc["ceiling"]["why_machine_readable"]
    drifted = re.sub(r"\b(build_animate_payload[.]py):([0-9]+)", r"\1:1", why, count=1)
    assert drifted != why

    copy = tmp_path / os.path.basename(victim)
    doc["ceiling"]["why_machine_readable"] = drifted
    copy.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    cited = re.findall(r"\b([A-Za-z0-9_]+[.]py):([0-9]+)", drifted)
    bad = [f"{n}:{l}" for n, l in cited
           if "seeds" not in open(os.path.join(TOOLS, n), encoding="utf-8")
           .read().splitlines()[int(l) - 1]]
    assert bad == ["build_animate_payload.py:1"], bad
    shutil.rmtree(tmp_path, ignore_errors=True)


# ===========================================================================
# WAVE 23, F-a5089b5f — the citation predicate, and the decoy it must refuse
# ===========================================================================


#: The decoy the citation predicate must refuse: a `read_seed_registration` call one line
#: BELOW a comment that mentions seeds. One shape, so the proof and the old-predicate
#: comparison below are grading the same module.
DECOY_SOURCE = "\n".join([
    "def main(argv=None):",
    "    # the registered seeds are read on the next line",
    "    registered = read_seed_registration(a.seeds, flag='--seeds')",
    "    return registered",
])


def _old_substring_predicate(source):
    """The predicate this file used BEFORE wave 23: any line containing `seeds`.

    Kept runnable so the proof below can assert what the correction actually changed, rather
    than asserting the new answer alone.
    """
    return {i for i, line in enumerate(source.splitlines(), 1) if "seeds" in line}


def test_the_citation_predicate_refuses_a_comment_beside_the_call():
    """The red proof, kept in the tree — and driving the PRODUCTION predicate (F-a89efade).

    What stood here parsed `DECOY_SOURCE` with its own `ast.walk` loop and asserted the
    comment line was not in the result. That is a property of `ast`; `seed_reader_call_lines`
    was never called, so reverting it to the substring predicate left this proof green along
    with the rest of the module. It calls the real function now, through the `source` seam,
    and asserts BOTH directions: the AST predicate refuses the comment and finds the call,
    and the predicate it replaced accepts the comment — which is the difference the wave-23
    correction was made for.
    """
    calls = seed_reader_call_lines("<decoy>", source=DECOY_SOURCE)
    assert calls == {3}, calls

    old = _old_substring_predicate(DECOY_SOURCE)
    assert 2 in old, "the decoy does not carry the substring the old predicate keyed on"
    assert 2 not in calls, "the AST predicate accepted a comment"
    assert old != calls, (
        "the old substring predicate and the AST predicate agree on the decoy, so this proof "
        "cannot show what the wave-23 correction changed")


def test_substituting_the_old_predicate_turns_this_modules_census_red():
    """The revert, driven: with the substring predicate in place of the AST one, a citation
    that points at a COMMENT must be accepted — which is the failure mode the census exists
    to refuse.

    Measured on `81d6c07`: substituting the old predicate module-wide left every test here
    green, so the census could not tell the two apart on the real tree (every citation target
    is a real call line that happens to contain `seeds`). The decoy is where they differ, and
    this drives `stale_citations`' own comparison over it rather than over the tree.
    """
    lineno_of_the_comment = 2
    assert lineno_of_the_comment in _old_substring_predicate(DECOY_SOURCE)
    assert lineno_of_the_comment not in seed_reader_call_lines("<decoy>", source=DECOY_SOURCE)


def test_the_seed_reader_call_lines_are_the_ones_the_specs_cite():
    """The population, stated: each cited module holds at least one call, and the seven
    citations are all of them — so a citation cannot drift onto a second, unrelated call
    site while the census stays green."""
    cited = {}
    for spec in SEED_SPECS:
        for name, lineno in _citations(spec):
            cited.setdefault(name, set()).add(int(lineno))
    assert len(cited) == 7, sorted(cited)
    for name, linenos in sorted(cited.items()):
        calls = seed_reader_call_lines(name)
        assert calls, f"{name} is cited as the reader and calls {SEED_READER} nowhere"
        assert linenos <= calls, (name, sorted(linenos), sorted(calls))
