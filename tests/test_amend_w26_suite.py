"""WAVE 26 — the suite's own censuses: ONE home per walk, and a red proof that can fail.

Three findings in this wave are the same defect at three scales, and none of them had a
census that would have named it:

* **F-f893634d** — a call-site walk implemented twice, byte for byte, on top of a primitive
  (`_census_nodes.called_name`) that already had a home. `test_alpha_law._calls` and
  `test_render_visibility._call_lines` had identical 1359-character body dumps. They could
  not disagree while identical; they could the moment one was edited, and neither file's
  population pin would have said so, because each pins only its own walk's output.
* **F-1843d5f2** — `parser_population` derived twice: `_census_nodes.parser_population`,
  consumed by `test_sheet_argv_smoke` as `CLI_TOOLS`, and an identical local copy in
  `test_sheet_pairing`, whose five immediate neighbours WERE aliased. Both returned 67 and
  the same members; `test_sheet_pairing.parser_population is _census_nodes.parser_population`
  was False, so a correction to the membership rule could land in one and not the other.
* **F-a89efade** — eight red proofs whose names say `goes_red` / `would_catch` / `can_fail`,
  that parse a scratch tree with their OWN copy of the predicate and call no production
  helper at all. Each asserts a property of `ast`, not of the walk it is named for.
  Measured on `81d6c07` for the seeds-spec one: substituting the pre-wave-23 substring
  predicate for `test_seeds_specs.seed_reader_call_lines` in process left every test in that
  module green, the red proof included.

The three censuses below are derived over `tests/**`, so the next copy joins them on the day
it lands rather than waiting for an audit to sweep the tree again. All three assert EMPTY —
no allowlist, because the eight offenders they were written for are closed in this commit.
"""

import ast
import glob
import os
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import _census_nodes as CN  # noqa: E402


def _test_module_paths():
    """Every `tests/*.py`, `_census_nodes.py` and `conftest.py` included."""
    return sorted(glob.glob(os.path.join(TESTS_DIR, "*.py")))


_PARSED = {}


def _parse(path):
    """Parsed once per session. Three censuses in this file walk every `tests/*.py`, and the
    suite is 160 modules; re-parsing per census cost ~30s on this rig."""
    if path not in _PARSED:
        with open(path, encoding="utf-8") as fh:
            _PARSED[path] = ast.parse(fh.read())
    return _PARSED[path]


def _uses_the_ast_module(node):
    """The function reaches for `ast.<something>` — i.e. it walks a tree itself."""
    return any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
               and n.value.id == "ast"
               for n in ast.walk(node))


def _body_without_docstring(node):
    body = node.body
    if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return body


# =========================================================================================
# (a) F-f893634d / F-1843d5f2 — no two test modules define the same AST walk
# =========================================================================================


def duplicated_ast_walks():
    """`[[ (file, name, line), ... ]]` — groups of module-level AST walks that are IDENTICAL
    across two or more files.

    The comparison is `ast.dump` of the body with any docstring dropped, so two functions
    that differ only in their prose are the same walk. Same-file duplicates are not reported:
    a file that defines one walk twice is a different (and much louder) problem, and this
    census is about the drift that crosses a file boundary with nothing to hold the two ends
    together.
    """
    groups = {}
    for path in _test_module_paths():
        tree = _parse(path)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _uses_the_ast_module(node):
                continue
            body = _body_without_docstring(node)
            if not body:
                continue
            key = ast.dump(ast.Module(body=body, type_ignores=[]))
            groups.setdefault(key, []).append(
                (os.path.basename(path), node.name, node.lineno))
    return [members for members in groups.values()
            if len({f for f, _n, _l in members}) > 1]


def test_the_duplicate_walk_census_has_a_population_worth_measuring():
    """Size before the property. A census over an empty set reports green.

    Measured on the wave-26 branch: 481 module-level functions under `tests/` reach for the
    `ast` module, and every one of their bodies is distinct.
    """
    population = [1 for path in _test_module_paths() for node in _parse(path).body
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and _uses_the_ast_module(node)]
    assert len(population) >= 400, len(population)


def test_no_two_test_modules_define_the_same_ast_walk():
    """F-f893634d's fix, asserted rather than described.

    Four copies were retired in this commit: `test_alpha_law._calls` and
    `test_render_visibility._call_lines` (both now `_census_nodes.call_lines`),
    `test_refusal_clauses.called_name_of` (now `_census_nodes.called_name`), and the
    `_fn_source` pair in `test_instruments_amend_w14` / `_w16` (now `blender_stub.fn_source`).
    """
    dupes = duplicated_ast_walks()
    assert dupes == [], (
        "the same AST walk is defined in more than one test module; give it ONE home in "
        "`tests/_census_nodes.py` (or `tests/blender_stub.py` for a Blender-side helper) and "
        "alias it at both sites:\n  "
        + "\n  ".join(repr(group) for group in dupes))


def test_the_duplicate_walk_census_can_see_a_duplicate():
    """The red direction, driving `duplicated_ast_walks`' own grouping over a scratch pair.

    Written the way this wave requires of every red proof: the production grouping is the
    thing under test, not `ast.dump`. Two spellings of the same walk under different names
    in different files must group; a third that differs by one clause must not.
    """
    same = ("def a(tree):\n"
            "    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)]\n")
    renamed = ("def b(tree):\n"
               "    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)]\n")
    different = ("def c(tree):\n"
                 "    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]\n")

    def key(src):
        node = ast.parse(src).body[0]
        assert _uses_the_ast_module(node), src
        return ast.dump(ast.Module(body=_body_without_docstring(node), type_ignores=[]))

    assert key(same) == key(renamed), "the grouping is keyed on the NAME, not on the walk"
    assert key(same) != key(different), "the grouping cannot tell two walks apart"


# =========================================================================================
# (b) F-1843d5f2 / F-f893634d — the aliases are the same OBJECT, not merely equal
# =========================================================================================


def test_the_call_site_walk_has_one_home():
    """`is`, not `==`: the shape `test_canon_spend` already uses for `cli_body`.

    "These two walks agree today" is what the tree said before F-e63ce880; "there is one
    walk" is what it says now.
    """
    import test_alpha_law as AL
    import test_render_visibility as RV

    assert AL._calls is CN.call_lines
    assert RV._call_lines is CN.call_lines


def test_the_cli_tool_population_has_one_home():
    """F-1843d5f2: `test_sheet_pairing` re-inlined `parser_population` while its five
    immediate neighbours were aliased, and `RECORDED_PARSER_POPULATION` — equality-pinned at
    67 — pinned only the local copy."""
    import test_sheet_argv_smoke as SAS
    import test_sheet_pairing as SP

    assert SP.parser_population is CN.parser_population
    assert SAS.CLI_TOOLS == CN.parser_population()
    # WAVE 34: 67 -> 69 (submit + uploads).
    assert len(SAS.CLI_TOOLS) == 69, len(SAS.CLI_TOOLS)


def test_the_callee_name_and_fn_source_helpers_have_one_home():
    """The other two pairs retired in this commit."""
    import blender_stub
    import test_instruments_amend_w14 as W14
    import test_instruments_amend_w16 as W16
    import test_refusal_clauses as RC

    assert RC.called_name_of is CN.called_name
    assert W14._fn_source is blender_stub.fn_source
    assert W16._fn_source is blender_stub.fn_source


# =========================================================================================
# (c) F-a89efade — every red proof drives the predicate it is named for
# =========================================================================================

#: The three markers the finding names, quoted from it: a test whose name says one of these
#: is claiming to prove that some census CAN fail.
RED_PROOF_MARKERS = ("goes_red", "would_catch", "can_fail")

#: Module aliases whose calls are the standard library or a third-party test dependency, not
#: this repo's production code. A red proof that calls only these is still proving a property
#: of somebody else's library.
NOT_PRODUCTION = {
    "ast", "os", "sys", "re", "json", "glob", "io", "math", "shutil", "subprocess",
    "hashlib", "copy", "textwrap", "itertools", "collections", "pathlib", "time",
    "importlib", "inspect", "types", "tempfile", "random", "struct", "base64", "csv",
    "pytest", "np", "numpy", "cv2", "Image", "PIL", "yaml", "difflib", "warnings",
}


def _module_scope(tree):
    """`(names this module defines or imports by name, module aliases it imports)`."""
    helpers, aliases = set(), set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("test_"):
                helpers.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    helpers.add(target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                aliases.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                helpers.add(alias.asname or alias.name)
    return helpers, aliases


def _production_calls(fn, helpers, aliases):
    """Calls this test makes into code the repo owns — a module-level helper of its own file,
    or an attribute call on an imported alias that is not a library."""
    out = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in helpers:
            out.add(func.id)
        elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
              and func.value.id in (aliases | helpers)
              and func.value.id not in NOT_PRODUCTION):
            out.add(f"{func.value.id}.{func.attr}")
    return sorted(out)


def red_proofs():
    """`[(file, name, line, builds_its_own_walk, production calls)]` over `tests/**`."""
    rows = []
    for path in _test_module_paths():
        tree = _parse(path)
        helpers, aliases = _module_scope(tree)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            if not any(marker in node.name for marker in RED_PROOF_MARKERS):
                continue
            builds = any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and isinstance(c.func.value, ast.Name) and c.func.value.id == "ast"
                and c.func.attr in ("parse", "walk")
                for c in ast.walk(node))
            rows.append((os.path.basename(path), node.name, node.lineno, builds,
                         _production_calls(node, helpers, aliases)))
    return rows


def test_the_red_proof_census_has_a_population_worth_measuring():
    """Size before the property: 74 tests in this suite name themselves red proofs."""
    rows = red_proofs()
    assert len(rows) >= 70, len(rows)
    assert any(builds for _f, _n, _l, builds, _p in rows), (
        "no red proof parses a scratch tree at all; the property below has no subject")


def test_every_red_proof_that_walks_a_scratch_tree_drives_the_real_predicate():
    """F-a89efade: a red proof that re-implements the predicate cannot be reverted red.

    The eight this was written for, all closed in this commit by giving each production walk
    a `source` seam and calling it: `test_seeds_specs.py` (the citation predicate, the one
    the finding measured), `test_gate_survives_optimize.py` (the helper-assert scan, whose
    FILE SELECTION was the unproven half — F-66b07477), `test_landmarks.py`,
    `test_make_rig_sheet.py` x2, `test_parts.py`, `test_render_visibility.py` and
    `test_sheet_sides.py`.

    `test_sheet_argv_smoke.py::test_the_census_goes_red_on_a_REAL_renderer_given_an_undeclared_flag`
    is deliberately NOT in the offender set: it parses a scratch source and hands it to
    `CN.undeclared_flags`, which is exactly the shape required here.
    """
    offenders = [(f, n, line) for f, n, line, builds, production in red_proofs()
                 if builds and not production]
    assert offenders == [], (
        "these tests name themselves red proofs, parse a scratch tree, and call no walk this "
        "repo owns — so they assert a property of `ast` and would stay green if the census "
        "they are named for were loosened:\n  "
        + "\n  ".join(f"{f}:{line} {n}" for f, n, line in offenders))


@pytest.mark.parametrize("marker", RED_PROOF_MARKERS)
def test_each_red_proof_marker_still_names_tests_in_this_suite(marker):
    """The markers are the finding's own three words; if one stops matching anything, the
    census silently narrows and this says so rather than reporting green over a smaller set."""
    named = [n for _f, n, _l, _b, _p in red_proofs() if marker in n]
    assert named, f"no test in tests/ is named with the red-proof marker {marker!r} any more"


# =========================================================================================
# (d) F-dfdbcff1 — the SHA-pinning law has one home in `test_ci_workflows.py`
# =========================================================================================


def test_the_action_pinning_law_is_asserted_in_exactly_one_place():
    """Two near-identically named censuses asserted the same 40-hex clause over the same
    population in the same file, with the same failure messages, and the membership pins were
    doubled beside them. Doubled parametrization inflates the count of a law with ONE subject
    and leaves it ambiguous which census a future edit is meant to keep in step with.
    """
    tree = _parse(os.path.join(TESTS_DIR, "test_ci_workflows.py"))
    holders = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if any(marker in node.name for marker in RED_PROOF_MARKERS):
            continue          # the law's red direction quotes the same regex, by design
        if any(isinstance(n, ast.Constant) and n.value == r"[0-9a-f]{40}"
               for n in ast.walk(node)):
            holders.append(node.name)
    assert holders == ["test_every_action_is_pinned_to_a_commit_and_says_which_version"], holders
    # And the red direction that quotes the regex is still there, so the exclusion above is
    # not quietly hiding the law's only remaining home.
    red = [n.name for n in tree.body
           if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
           and any(m in n.name for m in RED_PROOF_MARKERS)
           and any(isinstance(c, ast.Constant) and c.value == r"[0-9a-f]{40}"
                   for c in ast.walk(n))]
    assert red == ["test_the_pinning_check_goes_red_on_a_moving_major_tag"], red
