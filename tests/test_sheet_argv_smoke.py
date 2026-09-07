"""The five panels, driven the way an operator drives them: from `argv`.

**Why this file exists.** `make_gate0_sheet.main` read `a.sheet_plate` at line 250 and its
parser never declared `--sheet-plate`. Measured 2026-09-04 in this worktree on a synthetic
3-frame control/output pair with `--reference=none`: `AttributeError: 'Namespace' object has
no attribute 'sheet_plate'`, exit 1, before `os.makedirs` and before a tile was cut — on
EVERY invocation. There is no argument combination that reaches the sheet. The whole suite
was green because every gate-0 test exercised `G0.build`, never `G0.main`.

That is the shape no census in this repo could see: the plate census
(`test_sheet_pairing.py`) walks tile LOADERS (`_rgb` / `_load_rgb`) and the alpha law walks
composite helpers — neither keys on the node the defect lives on, which is the **argument
parser**. So this file keys on two nodes and says so:

* **the parser** — `ast`-walked `add_argument` calls per module, compared against the
  `parse_plate(a.sheet_plate, ...)` call sites in the same module. A flag that is READ and
  not DECLARED fails here; the population is derived from `tools/*.py`, never typed.
* **`main(argv)` itself** — each sheet is run end to end on a synthetic fixture and must
  return 0, print its success sentinel, and leave the file it named. The SUCCESS direction
  of the exit convention is pinned here, because a failure-only census cannot see a tool
  that dies on every invocation (wave-10 coordinator brief, rule 3).

The refusal direction is pinned beside it: a malformed `--sheet-plate` raises the sheet's
own typed error and leaves nothing on disk.

WAVE 12 — the parser node now covers every command-line tool, and the walk is ONE walk.
WAVE 16 — "every" finally means every: 36 -> 67 (F-beeab1d0, below).

* **F-1c9d39e2** — this file carried a SECOND implementation of "a flag that is read and
  never declared" which resolved no cross-module helper, no `set_defaults` and no
  `add_subparsers(dest=)`. Measured over every `tools/*.py`, it reported six correct
  modules as offenders while the sibling walk reported none, and nothing pinned the two
  against each other. Both are now `tests/_census_nodes`, and
  `test_the_two_walks_are_literally_the_same_function` asserts identity rather than
  agreement.
* **F-fae3fad4** — the undeclared-flag property was parametrized over the five plate sheets
  while `_parser_census()` had always walked the whole tree, so 31 command-line tools were
  policed by nothing here. It now runs over all of them. The end-to-end SUCCESS leg still
  covers 5; that gap is a counted category (`NO_SUCCESS_FIXTURE`) with a size that may only
  fall, and every CPython member gets the cheapest real-process argv exercise there is —
  `--help`, which constructs the parser for real and would die on a module that cannot be
  imported or a parser that cannot be built.
"""

import ast
import glob
import json
import os
import subprocess
import sys

import pytest
from PIL import Image

import _census_nodes as CN

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools"))

from conftest import TOOLS  # noqa: F401,E402

import make_gate0_sheet as G0  # noqa: E402
import make_identity_sheet as MIS  # noqa: E402
import make_lift_sheet as LS  # noqa: E402
import make_startframe_sheet as SFS  # noqa: E402
import make_thesis_sheet as TS  # noqa: E402
import sheet_compose as SC  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = (32, 24)


# ------------------------------------------------- node 1: the parser, not the tile loader


# WAVE 12, F-1c9d39e2 — the second walk is DELETED.
#
# This file used to carry its own `_dests_declared` + `_namespace_attrs_read` pair. Two
# independent implementations of "a flag that is read and never declared" lived in the
# suite, they disagreed by construction, and nothing pinned them against each other: this
# one resolved no cross-module helper, no `set_defaults` and no `add_subparsers(dest=)`,
# while `tests/test_sheet_pairing.py`'s resolved all three. Measured over all 78
# `tools/*.py` with both walks, this one reported undeclared flags on SIX modules that are
# correct — `build_payload`, `build_t2v_payload`, `build_r2v_payload` and
# `build_lora_arm_payload` (`subject`, `no_canon`, `canon_prompt`, declared by the shared
# `add_spend_flags` at tools/armature_core/canon.py:94), `canon_gate` (`cmd`, `func`, from
# `add_subparsers(dest=)` / `set_defaults(func=)`) and `render_turnaround`
# (`ortho_scale_text`, which the tool ASSIGNS onto the namespace itself). The only thing
# keeping those six off the board was that the property was parametrized over the five
# plate sheets while this file's docstring framed it as the general property — so the
# obvious next step, widening it, would have turned six correct modules red and invited an
# exemption list, converting a derived census into a typed one.
#
# There is now ONE walk, in `tests/_census_nodes.py`, and this file keeps only its own
# contribution: the end-to-end `main(argv)` leg. `test_the_two_walks_are_literally_the_same_
# function` below is the assertion that would have caught the divergence.
_dests_declared = CN.argparse_dests
_namespace_attrs_read = CN.namespace_reads


def _success_tokens(path):
    """The success sentinel(s) `main` PRINTS, read off the file by AST.

    One node — the `print` calls directly inside `main`, walked WITHOUT descending into a
    nested function — so the token this file pins per tool is the token that tool actually
    emits, rather than a string typed twice. An f-string's leading constant is its first
    word, which is where every sentinel in this repo lives.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    main = next((n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    if main is None:
        return set()

    stack, nodes = list(ast.iter_child_nodes(main)), []
    while stack:
        node = stack.pop()
        nodes.append(node)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))

    tokens = set()
    for node in nodes:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print" and node.args):
            continue
        first = node.args[0]
        # `print("TOKEN " + json.dumps(...))` is the other spelling in this family; the
        # leading constant is the left operand of the concatenation.
        while isinstance(first, ast.BinOp) and isinstance(first.op, ast.Add):
            first = first.left
        if isinstance(first, ast.JoinedStr) and first.values:
            first = first.values[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            word = first.value.strip().split()
            if word:
                tokens.add(word[0])
    return tokens


#: Every module tree in `tools/` (plus `armature_core/`, whose `add_spend_flags` declares
#: three of the flags four builders read), and the helper table resolved once.
TREES = CN.module_trees()
HELPERS = CN.flag_helpers(TREES)

#: The tool-keyed population, WITHOUT `armature_core` shadowing a basename. `module_trees`
#: is keyed by basename and `armature_core/lift_solve.py` claimed `lift_solve` there, so
#: `tools/lift_solve.py` — five declared flags, all five read — was walked as the solver,
#: which has no `main`, and reported "no command line" (F-beeab1d0).
TOOL_TREES = CN.tool_trees()


def _parser_census():
    """`{module: (path, declared dests, namespace attrs read)}` over every `tools/*.py`.

    ONE walk (F-1c9d39e2): `declared` resolves module-local AND imported flag helpers,
    `add_subparsers(dest=)` and `set_defaults(**)`; `read` is keyed on the tool's CLI BODY,
    so a builder whose argv parsing moved into `build_and_write(argv)` is still read
    (F-0e0709b2).
    """
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO, "tools", "*.py"))):
        mod = os.path.basename(path)[:-3]
        out[mod] = (path, CN.declared_flags(TOOL_TREES[mod], mod, HELPERS),
                    set(CN.namespace_reads(TOOL_TREES[mod])))
    return out


PARSERS = _parser_census()

#: Every `tools/*.py` with a command line — the census's OWN population, 67 on 2026-09-04,
#: derived and asserted in `tests/test_sheet_pairing.py`. The undeclared-flag property below
#: runs over all of it; until wave 12 it ran over the five plate sheets only.
#
# WAVE 16, F-beeab1d0: 36 -> 67. The census kept a module only when `namespace_reads` found
# `a = ap.parse_args(argv)` — an `ast.Attribute` call. 31 tools write `a = parse_args(argv)`
# instead (a module-level helper holds the parser), four of those return `vars(...)` and
# read their flags as subscripts, and one hands `_dispatch` to a shared runner. All 31 were
# outside the gate-0 property AND outside the `--help` smoke; `tools/build_i2v_payload.py`
# and all four renderers among them. The population is now asserted against the tools that
# call `add_argument(`, so a tool cannot leave the census by changing its idiom.
CLI_TOOLS = CN.parser_population(TOOL_TREES)

#: Derived population: every module that READS `sheet_plate` off its own argparse
#: namespace. The read is the node — `make_gate0_sheet` had the read and not the flag.
PLATE_SHEETS = {m: v[0] for m, v in PARSERS.items() if "sheet_plate" in v[2]}


def test_the_parser_population_is_every_tool_that_declares_an_argument():
    """The census's population, asserted against the thing the census is ABOUT.

    WAVE 16, F-beeab1d0. `CLI_TOOLS` was whatever `namespace_reads` happened to reach, and
    what it reached was one idiom: `a = ap.parse_args(argv)`. 31 of the 67 tools that call
    `add_argument(` factor their parser into a module-level helper and write
    `a = parse_args(argv)`; the walk could not see the bare `ast.Name` call, so they were
    outside the undeclared-flag property AND outside the `--help` smoke — three payload
    builders and all four renderers among them. A population derived from the idiom cannot
    notice a tool leaving it. This one is derived from `add_argument(`, which is what a
    parser IS, so a tool can only leave the census by ceasing to have a command line.
    """
    declared_one = CN.tools_calling_add_argument()
    assert sorted(CLI_TOOLS) == sorted(declared_one), {
        "declares a flag, census cannot see it": sorted(set(declared_one) - set(CLI_TOOLS)),
        "in the census, declares nothing": sorted(set(CLI_TOOLS) - set(declared_one)),
    }
    # WAVE 34: 67 -> 69. `build_submit_payload` and `build_uploads_payload` join; the
    # retarget spelling on `lift_solve` (`a = require_retarget_flags(parse_args())`) is
    # visible again via `_passthrough_arg0_names`, so it does not leave.
    # WAVE 35: 69 -> 70. `build_routes_payload` joins.
    assert len(CLI_TOOLS) == 70, len(CLI_TOOLS)


def test_the_solver_no_longer_shadows_the_tool_of_the_same_name():
    """`module_trees` is keyed by BASENAME and exactly one basename is claimed twice.

    Measured 2026-09-04: `armature_core/lift_solve.py` was parsed last and won the key, so
    every tool-keyed census walked the solver — which has no `main` — and reported
    `tools/lift_solve.py` as having no command line while it declares 5 flags and reads all
    5. Pinned by name so a second collision cannot land quietly.
    """
    assert CN.colliding_basenames() == ["lift_solve"], CN.colliding_basenames()
    assert CN.cli_body(TOOL_TREES["lift_solve"]) is not None
    assert CN.cli_body(CN.module_trees(include_core=False)["lift_solve"]) is not None
    # WAVE 34 retarget admits four more flags; the passthrough binding keeps them visible.
    assert set(CN.namespace_reads(TOOL_TREES["lift_solve"])) == {
        "bone_map", "fps", "glb", "licence_row", "manifest", "motion", "motion_out",
        "out", "retarget", "root_translation"}


def test_the_widened_walk_sees_a_flag_the_old_one_could_not_and_the_old_one_is_shown_blind():
    """RED on a member OUTSIDE the subset the old walk reached (wave-16 rule 2).

    The old walk bound a namespace only from an `ast.Attribute` call, so the renderer
    idiom was invisible to it. Both directions on the same source: the widened walk reports
    the undeclared read, and the pre-wave-16 binding is shown returning nothing at all — if
    it could see it, this comparison would be with itself.
    """
    def old_reads(tree):
        """The pre-wave-16 binding, verbatim: `ast.Attribute` calls only, one body."""
        body = CN.cli_body(tree)
        if body is None:
            return {}
        ns = set()
        for node in CN.walk_scope(body):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and node.value.func.attr in ("parse_args", "parse_known_args")):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        ns.add(target.id)
        out = {}
        for node in CN.walk_scope(body):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id in ns):
                out.setdefault(node.attr, node.lineno)
        return out

    src = (
        "import argparse\n"
        "def parse_args(argv=None):\n"
        "    ap = argparse.ArgumentParser()\n"
        "    ap.add_argument('--views', default='0,90')\n"
        "    return ap.parse_args(argv)\n"
        "def main(argv=None):\n"
        "    a = parse_args(argv)\n"
        "    return render(a.views, a.ortho_scale)\n")
    tree = ast.parse(src)
    helpers = CN.flag_helpers({"render_synthetic": tree})
    assert old_reads(tree) == {}, (
        "the pre-wave-16 binding must be blind to `a = parse_args(argv)`; if it sees it "
        "there is nothing to widen")
    assert set(CN.namespace_reads(tree)) == {"views", "ortho_scale"}
    assert sorted(CN.undeclared_flags(tree, "render_synthetic", helpers)) == ["ortho_scale"]

    # the dict spelling, which four Blender-side tools use: `vars(p.parse_args(argv))`
    dict_src = (
        "import argparse\n"
        "def parse_args(argv=None):\n"
        "    p = argparse.ArgumentParser()\n"
        "    p.add_argument('--glb', required=True)\n"
        "    return vars(p.parse_args(argv))\n"
        "def main(argv=None):\n"
        "    args = parse_args(argv)\n"
        "    return rig(args['glb'], args['fps'])\n")
    dtree = ast.parse(dict_src)
    dhelpers = CN.flag_helpers({"rig_synthetic": dtree})
    assert old_reads(dtree) == {}
    assert set(CN.namespace_reads(dtree)) == {"glb", "fps"}
    assert sorted(CN.undeclared_flags(dtree, "rig_synthetic", dhelpers)) == ["fps"]


def test_the_census_goes_red_on_a_REAL_renderer_given_an_undeclared_flag():
    """The same proof on a member of the population, not on a synthetic module.

    `render_turnaround` is one of the 31 the old walk could not see. Its source is read,
    one undeclared read is spliced into its CLI body, and the widened census must report
    exactly that flag — while the pre-wave-16 walk reports nothing, on the same bytes.
    """
    with open(os.path.join(REPO, "tools", "render_turnaround.py"), encoding="utf-8") as fh:
        src = fh.read()
    assert CN.undeclared_flags(ast.parse(src), "render_turnaround", HELPERS) == {}, (
        "baseline: the real renderer declares every flag it reads")
    marker = "def main():\n"
    assert src.count(marker) == 1, "the splice point moved; re-derive it"
    spliced = src.replace(marker, marker + "    _probe = a.no_such_flag\n", 1)
    assert sorted(CN.undeclared_flags(ast.parse(spliced), "render_turnaround",
                                      HELPERS)) == ["no_such_flag"]


def test_the_plate_parsing_population_is_the_one_this_file_claims():
    """Size AND membership, so a sixth sheet joins the census the day it lands."""
    assert set(PLATE_SHEETS) == {
        "make_gate0_sheet", "make_identity_sheet", "make_lift_sheet",
        "make_startframe_sheet", "make_thesis_sheet"}, sorted(PLATE_SHEETS)
    assert len(PLATE_SHEETS) == 5


def test_the_two_walks_are_literally_the_same_function():
    """F-1c9d39e2's own fix, asserted rather than trusted.

    The shape
    `tests/test_packaging.py::test_the_two_spend_and_fetch_censuses_are_literally_the_same_function`
    already uses for the two import scanners: not "these two walks agree today", but "there
    is one walk". A second implementation of a law drifts, and this pair had drifted into
    disagreeing about six modules.

    ⚠ RE-ANCHORED 2026-09-05 (wave 25): the citation was a bare line number in
    `test_packaging.py`, and teaching `_exit_convention` to read the one handler's prefix
    argument moved it onto a blank line. The number is dropped rather than re-measured —
    the symbol does not move.
    """
    import test_sheet_pairing as SP

    assert _dests_declared is CN.argparse_dests
    assert _namespace_attrs_read is CN.namespace_reads
    assert SP._argparse_dests is CN.argparse_dests
    assert SP.namespace_reads is CN.namespace_reads
    assert SP.declared_flags is CN.declared_flags


def test_the_deleted_walk_is_the_one_that_reported_six_correct_modules():
    """The measurement that justified the deletion, kept runnable.

    The old walk is reconstructed here — `add_argument` only, no helper resolution, no
    `set_defaults`, no `add_subparsers` — and shown to report exactly the six modules the
    finding names, none of which has a defect. A deletion nobody can re-derive is a claim.
    """
    def old_declared(tree):
        out = set()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"):
                continue
            dest = None
            for kw in node.keywords:
                if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                    dest = kw.value.value
            if dest is None:
                for arg in node.args:
                    if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                        continue
                    if arg.value.startswith("--"):
                        dest = arg.value[2:].replace("-", "_")
                        break
                    if not arg.value.startswith("-"):
                        dest = arg.value.replace("-", "_")
                        break
            if dest:
                out.add(dest)
        return out

    def old_read(tree):
        """The deleted READ walk, verbatim: every function scope that calls `parse_args`."""
        def scope_nodes(scope):
            stack, out = list(ast.iter_child_nodes(scope)), []
            while stack:
                node = stack.pop()
                out.append(node)
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                         ast.ClassDef, ast.Lambda)):
                    stack.extend(ast.iter_child_nodes(node))
            return out

        scopes = [tree] + [n for n in ast.walk(tree)
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        reads = set()
        for scope in scopes:
            nodes = scope_nodes(scope)
            namespaces = set()
            for node in nodes:
                if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Attribute)
                        and node.value.func.attr == "parse_args"):
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            namespaces.add(tgt.id)
            if not namespaces:
                continue
            for node in nodes:
                if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                        and node.value.id in namespaces):
                    reads.add(node.attr)
        return reads

    disagree = {}
    for mod, (_path, _dec, _read) in sorted(PARSERS.items()):
        tree = TOOL_TREES[mod]
        old = sorted(old_read(tree) - old_declared(tree))
        new = sorted(CN.undeclared_flags(tree, mod, HELPERS))
        if old != new:
            disagree[mod] = (old, new)
    assert disagree == {
        "build_lora_arm_payload": (["canon_prompt", "no_canon", "subject"], []),
        "build_payload": (["canon_prompt", "no_canon", "subject"], []),
        "build_r2v_payload": (["canon_prompt", "no_canon", "subject"], []),
        # WAVE 35: routes dispatcher — old walk saw subparser dests; CN.undeclared_flags
        # resolves them. Same shape as canon_gate's cmd/func.
        "build_routes_payload": (["cmd", "func"], []),
        "build_t2v_payload": (["canon_prompt", "no_canon", "subject"], []),
        "canon_gate": (["cmd", "func"], []),
        "render_turnaround": (["ortho_scale_text"], []),
    }, disagree


@pytest.mark.parametrize("module", sorted(CLI_TOOLS))
def test_every_flag_a_tool_reads_is_a_flag_its_parser_declares(module):
    """The gate-0 regression, stated as a property of the parser — over ALL 67 tools.

    `--sheet-plate` was READ and never DECLARED, so every invocation died in `main` with
    an `AttributeError` naming no flag. Any other undeclared read is the same defect.

    WAVE 12, F-fae3fad4: this property was parametrized over `PLATE_SHEETS` — the five
    modules that read `sheet_plate` — while `_parser_census()` had always walked every
    `tools/*.py`. The 31 other command-line tools were policed by nothing here. It could not
    be widened until the two walks became one (F-1c9d39e2), because the walk this file
    carried reported six correct modules as offenders.
    """
    _path, declared, read = PARSERS[module]
    undeclared = sorted(f for f in read if f not in declared)
    assert undeclared == [], (
        f"{module} reads {undeclared} off its own argparse namespace and its parser "
        f"declares no such argument; every invocation dies in main()")


@pytest.mark.parametrize("module", sorted(PLATE_SHEETS))
def test_every_plate_sheet_declares_the_plate_flag(module):
    """The narrower half that IS about the five: the flag itself."""
    _path, declared, _read = PARSERS[module]
    assert "sheet_plate" in declared, module


def test_the_parser_census_goes_red_on_a_call_site_with_no_flag(tmp_path):
    """The falsifiability fixture: the exact shape `make_gate0_sheet` shipped.

    Also pins the numpy false positive the first draft of this walk had: an `a.shape`
    read in a function that never called `parse_args` is not an argparse read.
    """
    src = (
        "import argparse\n"
        "def helper(a):\n"
        "    return a.shape, a.ndim\n"
        "def main(argv=None):\n"
        "    ap = argparse.ArgumentParser()\n"
        "    ap.add_argument('--out', required=True)\n"
        "    ap.add_argument('--frames-dir', required=True)\n"
        "    a = ap.parse_args(argv)\n"
        "    return parse_plate(a.sheet_plate, Exc, flag='--sheet-plate'), a.frames_dir\n")
    tree = ast.parse(src)
    declared, read = _dests_declared(tree), set(_namespace_attrs_read(tree))
    assert declared == {"out", "frames_dir"}
    assert read == {"sheet_plate", "frames_dir"}, read
    assert sorted(f for f in read if f not in declared) == ["sheet_plate"]


# ---------------------------------------- node 2: `main(argv)`, run end to end (rule 3)


def _clip(d, numbers, base=(20, 20, 24), digits=5):
    os.makedirs(d, exist_ok=True)
    for k, n in enumerate(numbers):
        Image.new("RGB", SIZE, (base[0] + 20 * k, base[1] + 7 * k, base[2])).save(
            os.path.join(d, f"{n:0{digits}d}.png"))
    return d


def _meta(path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"experiment": "E99", "arm": "A1"}, fh)
    return path


def _detection(path, frames):
    rows = [{"frame": n, "file": f"{n:05d}.png", "fired": False,
             "image": [], "visibility": []} for n in frames]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh)
    return path


def _gate0_argv(tmp, plate=None):
    out = str(tmp / "sheets" / "gate0.png")
    argv = [f"--run={_clip(str(tmp / 'ctl'), [0, 1, 2])}",
            f"--frames-dir={_clip(str(tmp / 'out'), [0, 1, 2])}",
            "--reference=none", f"--meta={_meta(str(tmp / 'meta.json'))}",
            f"--out={out}", "--frames=0,1,2"]
    if plate is not None:
        argv.append(f"--sheet-plate={plate}")
    return G0, argv, out, "GATE0_SHEET", SC.SheetPopulationError


def _identity_argv(tmp, plate=None):
    run = str(tmp / "run")
    _clip(os.path.join(run, "normal"), [0, 1, 2])
    ref = str(tmp / "ref.png")
    Image.new("RGB", SIZE, (60, 60, 60)).save(ref)
    out = str(tmp / "sheets" / "identity.png")
    argv = [f"--run={run}", f"--plates={ref}", f"--out={out}", "--frames=0,1",
            "--tile-height=24"]
    if plate is not None:
        argv.append(f"--sheet-plate={plate}")
    return MIS, argv, out, "IDENTITY_SHEET", MIS.IdentitySheetError


def _lift_argv(tmp, plate=None):
    src = _clip(str(tmp / "src"), [0, 1, 2])
    lif = _clip(str(tmp / "lif"), [0, 1, 2], base=(40, 30, 24))
    for d in (src, lif):
        Image.new("RGB", SIZE, (0, 0, 0)).save(os.path.join(d, "empty_plate.png"))
    out = str(tmp / "sheets" / "lift.png")
    argv = [f"--source={src}", f"--lifted={lif}",
            f"--detection={_detection(str(tmp / 'det.json'), [0, 1, 2])}",
            f"--out={out}", "--frames=0,1", "--tile-h=24", "--source-uncropped"]
    if plate is not None:
        argv.append(f"--sheet-plate={plate}")
    return LS, argv, out, "MAKE_LIFT_SHEET_OK", SC.SheetPopulationError


def _startframe_argv(tmp, plate=None):
    start = str(tmp / "start.png")
    Image.new("RGB", SIZE, (9, 9, 9)).save(start)
    out = str(tmp / "sheets" / "startframe.png")
    argv = [f"--start={start}", f"--frames={_clip(str(tmp / 'f'), [0, 1, 2])}",
            f"--meta={_meta(str(tmp / 'meta.json'))}", f"--out={out}", "--at=0,1",
            "--scale=0.5"]
    if plate is not None:
        argv.append(f"--sheet-plate={plate}")
    return SFS, argv, out, "STARTFRAME_SHEET", SC.SheetPopulationError


def _thesis_argv(tmp, plate=None):
    ctl = _clip(str(tmp / "ctl"), [0, 1, 2])
    arm = _clip(str(tmp / "arm"), [0, 1, 2], base=(40, 30, 24))
    out = str(tmp / "sheets" / "thesis.png")
    argv = [f"--control={ctl}", f"--arms=A1:{arm}", "--reference=none",
            f"--out={out}", "--frames=0,1", "--tile-height=24"]
    if plate is not None:
        argv.append(f"--sheet-plate={plate}")
    return TS, argv, out, "THESIS_SHEET", SC.SheetPopulationError


SHEETS = {
    "make_gate0_sheet": _gate0_argv,
    "make_identity_sheet": _identity_argv,
    "make_lift_sheet": _lift_argv,
    "make_startframe_sheet": _startframe_argv,
    "make_thesis_sheet": _thesis_argv,
}


def test_the_argv_smoke_population_is_the_plate_parsing_population():
    """The two nodes describe the same five tools; neither may drift from the other."""
    assert set(SHEETS) == set(PLATE_SHEETS)


# ------------------------------------ the gap with no success fixture, COUNTED not ignored
#
# WAVE 12, F-fae3fad4, rule 3. The end-to-end `main(argv)` leg covers 5 of the tools with
# a command line. That gap was invisible: the file's docstring frames `main(argv)` as one of
# its two nodes and says nothing about which tools it reaches. It is now a category with a
# size and a membership, so it can only shrink deliberately — and every member still gets
# the cheapest end-to-end argv exercise there is, `--help`, which builds the real parser in
# a real process and would have died on a parser that cannot be constructed at all.
#
# WAVE 16, F-beeab1d0: 31 -> 62, because the population went 36 -> 67. The ceiling is
# re-derived, never re-typed: `len(set(CN.parser_population(CN.tool_trees())) - set(SHEETS))`
# reads 62 on 2026-09-04 in this worktree.
#
# WAVE 34, F-fbe68663: the fifteen paid CLIs move into `tests/test_paid_argv_smoke.PAID`
# SUCCESS fixtures, so the gap shrinks 62 -> 47 deliberately. SHEETS stays the plate-sheet
# five; PAID is the sibling population. The two boundary payload tools that joined the
# CLI population the same wave (`build_submit_payload`, `build_uploads_payload`) carry
# dry-run SUCCESS fixtures too, so the gap stays at 47 rather than growing with them.
#
# WAVE 35, F-8c52638d: the seven measure_* CLIs move into
# `tests/test_measure_argv_smoke.MEASURE`, so the gap shrinks 47 -> 40.
# WAVE 35, F-f1f4cfaa: extended CPython sheets join EXTENDED_SHEETS (see below), shrinking
# further; blender_reach sheets join BLENDER_SHEET_SUCCESS under the stub.


import test_paid_argv_smoke as _PAID_SMOKE  # noqa: E402
import test_measure_argv_smoke as _MEASURE_SMOKE  # noqa: E402
import test_extended_sheet_argv_smoke as _EXT_SHEET_SMOKE  # noqa: E402

PAID_SUCCESS = set(_PAID_SMOKE.PAID)
MEASURE_SUCCESS = set(_MEASURE_SMOKE.MEASURE)
EXTENDED_SHEETS = set(_EXT_SHEET_SMOKE.EXTENDED_SHEETS)
BLENDER_SHEET_SUCCESS = set(_EXT_SHEET_SMOKE.BLENDER_SHEET_SUCCESS)
#: WAVE 35: owned routes dispatcher carries a list SUCCESS fixture below so the gap
#: does not grow when the tool joins CLI_TOOLS.
ROUTES_SUCCESS = {"build_routes_payload"}
NO_SUCCESS_FIXTURE = sorted(
    set(CLI_TOOLS) - set(SHEETS) - PAID_SUCCESS - MEASURE_SUCCESS
    - EXTENDED_SHEETS - BLENDER_SHEET_SUCCESS - ROUTES_SUCCESS)

#: The members of `CLI_TOOLS` that cannot be driven from a CPython process at all, keyed on
#: the BEHAVIOUR "runs under Blender" (`blender_stub.blender_reach`, wave 12 F-6b3040d1) and
#: not on a typed list: `make_test_armature` imports `bpy` at module scope, so `--help`
#: raises `ModuleNotFoundError` before argparse is reached. Their exit contract is asserted
#: in `tests/test_instrument_exits.py`, which drives their `__main__` handlers under the
#: Blender stub.
def _cpython_cli_tools():
    from blender_stub import blender_reach

    return sorted(m for m in CLI_TOOLS if not blender_reach(m + ".py"))


CPYTHON_CLI_TOOLS = _cpython_cli_tools()


def test_the_success_fixture_gap_is_counted_and_may_only_shrink():
    """29 of 70 after wave 35 routes SUCCESS (was 29 of 69 before routes joined CLI;
    measure + extended sheets had already shrunk the gap). A fixture added moves a tool
    out of this set; nothing may move the other way."""
    covered = (set(SHEETS) | PAID_SUCCESS | MEASURE_SUCCESS
               | EXTENDED_SHEETS | BLENDER_SHEET_SUCCESS | ROUTES_SUCCESS)
    assert set(NO_SUCCESS_FIXTURE) | covered == set(CLI_TOOLS)
    assert set(SHEETS) <= set(CLI_TOOLS), sorted(set(SHEETS) - set(CLI_TOOLS))
    assert PAID_SUCCESS <= set(CLI_TOOLS), sorted(PAID_SUCCESS - set(CLI_TOOLS))
    assert MEASURE_SUCCESS <= set(CLI_TOOLS), sorted(MEASURE_SUCCESS - set(CLI_TOOLS))
    assert EXTENDED_SHEETS <= set(CLI_TOOLS), sorted(EXTENDED_SHEETS - set(CLI_TOOLS))
    assert BLENDER_SHEET_SUCCESS <= set(CLI_TOOLS), sorted(
        BLENDER_SHEET_SUCCESS - set(CLI_TOOLS))
    assert ROUTES_SUCCESS <= set(CLI_TOOLS), sorted(ROUTES_SUCCESS - set(CLI_TOOLS))
    assert len(NO_SUCCESS_FIXTURE) <= 29, (
        f"{len(NO_SUCCESS_FIXTURE)} command-line tools have no end-to-end success fixture; "
        f"29 was the count after wave 35's measure + extended sheet + routes SUCCESS "
        f"fixtures and it may only fall: {NO_SUCCESS_FIXTURE}")
    assert len(PAID_SUCCESS) == 17, sorted(PAID_SUCCESS)
    assert len(MEASURE_SUCCESS) == 7, sorted(MEASURE_SUCCESS)
    assert len(EXTENDED_SHEETS) == 7, sorted(EXTENDED_SHEETS)
    assert len(BLENDER_SHEET_SUCCESS) == 4, sorted(BLENDER_SHEET_SUCCESS)
    assert len(ROUTES_SUCCESS) == 1, sorted(ROUTES_SUCCESS)


def test_build_routes_payload_list_is_a_success_fixture(capsys):
    """WAVE 35: routes dispatcher joins CLI_TOOLS with a real main(argv) SUCCESS path."""
    import build_routes_payload as BRP

    assert BRP.main(["list", "--live-only"]) == 0
    out = capsys.readouterr().out
    assert "ROUTES_LIST_OK " in out


def test_the_blender_side_of_the_cli_population_is_the_one_that_cannot_be_driven_here():
    """The exemption, keyed on its REASON and re-derived — never a typed list.

    WAVE 16: 1 -> 17, because the population that could reach this exemption at all went
    36 -> 67. Every one of the sixteen that joined is a Blender tool by
    `blender_reach` — `render_turnaround` and the three other renderers among them, which
    means their `--help` is still not driven in a real process. That is stated rather than
    hidden: their exit contract is asserted in `tests/test_instrument_exits.py`, under the
    stub, and the reason they are here is a property of the module, not a name on a list.
    """
    from blender_stub import blender_reach

    excluded = sorted(set(CLI_TOOLS) - set(CPYTHON_CLI_TOOLS))
    assert excluded == [
        "author_walk", "check_relift", "diagnose_bone_heat", "lift_solve",
        "make_binding_sheet", "make_parts_sheet", "make_rig_sheet", "make_skeleton_sheet",
        "make_test_armature", "preview_glb", "preview_walk", "render_performer",
        "render_start_frame", "render_turnaround", "rig_bake", "rig_repair",
        "rig_retopo"], excluded
    for module in excluded:
        assert blender_reach(module + ".py"), module
    # WAVE 34: 50 -> 52. The two boundary payload tools are CPython; blender side unchanged.
    # WAVE 35: 52 -> 53. build_routes_payload is CPython.
    assert len(CPYTHON_CLI_TOOLS) == 53, len(CPYTHON_CLI_TOOLS)


def _module_scope_imports_this_interpreter_cannot_resolve(module):
    """`{name}` a tool imports at MODULE SCOPE that this interpreter has no spec for.

    The second exemption from the `--help` smoke, derived the same way as the Blender one:
    keyed on the reason, never on a name. `tools/armature_index.py` imports `record_index`
    at module scope — a sibling working copy at `E:\\AI\\record-index`, not a dependency of
    this venv (`tests/test_record_index_binding.py` states the same fact and skips on the
    same condition). With it on `PYTHONPATH` the tool is driven like every other; without
    it, `--help` dies in the import and the skip says which module was missing.
    """
    import importlib.util

    path = os.path.join(REPO, "tools", module + ".py")
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    missing = set()
    for node in tree.body:
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split(".")[0]]
        for name in names:
            try:
                if importlib.util.find_spec(name) is None:
                    missing.add(name)
            except (ImportError, ValueError):
                missing.add(name)
    return missing


@pytest.mark.parametrize("module", CPYTHON_CLI_TOOLS)
def test_every_command_line_tool_builds_its_parser_in_a_real_process(module):
    """The weakest END-TO-END direction, run over all 50 rather than over five.

    `--help` is argparse's own path: the module is imported as `__main__`, the parser is
    constructed, every `add_argument` runs, and the process exits 0. It cannot see a flag
    that is read and never declared — the static property above is what sees that — but it
    does see a parser that cannot be built, a module-scope failure, and a tool whose
    `--help` exits non-zero, none of which any test reached for 31 of these tools.

    WAVE 16, F-beeab1d0: 35 -> 50 members. `tools/build_i2v_payload.py`,
    `tools/build_camera_i2v_payload.py`, `tools/build_animate_payload.py`,
    `tools/pack_pose_pack.py` and eleven more had never had their parser constructed by any
    test. The subprocess now CARRIES the caller's `PYTHONPATH` rather than replacing it, so
    a sibling working copy the operator has on the path is on the tool's path too.
    """
    missing = _module_scope_imports_this_interpreter_cannot_resolve(module)
    if missing:
        pytest.skip(f"tools/{module}.py imports {sorted(missing)} at module scope and this "
                    f"interpreter has no spec for it; put it on PYTHONPATH to drive --help")
    inherited = os.environ.get("PYTHONPATH", "")
    tools_path = os.path.join(REPO, "tools")
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", module + ".py"), "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(
            [tools_path] + ([inherited] if inherited else []))),
        cwd=os.path.join(REPO, "tools"))
    assert proc.returncode == 0, (
        f"tools/{module}.py --help exited {proc.returncode}:\n{proc.stdout}\n{proc.stderr}")
    assert "usage" in proc.stdout.lower(), proc.stdout[:400]


def test_each_sheet_prints_exactly_one_success_token_and_they_are_all_distinct():
    """Derived per tool from its own `main`. Two tools sharing a token make a caller that
    keys on it unable to say which one succeeded — the reason the shared `PANELS_OK` was
    retired from the bpy side this wave."""
    tokens = {name: _success_tokens(path) for name, path in PLATE_SHEETS.items()}
    for name, found in tokens.items():
        assert len(found) == 1, (name, sorted(found))
    flat = [next(iter(v)) for v in tokens.values()]
    assert len(set(flat)) == len(flat), sorted(flat)


@pytest.mark.parametrize("name", sorted(SHEETS))
def test_every_sheet_main_runs_end_to_end_from_argv(name, tmp_path, capsys):
    """SUCCESS direction: exit 0, the success sentinel, and the file it named on disk.

    `make_gate0_sheet` died here with `AttributeError: 'Namespace' object has no attribute
    'sheet_plate'` before this flag was declared — on every invocation, with the whole
    suite green.
    """
    mod, argv, out, sentinel, _exc = SHEETS[name](tmp_path)
    # The token is DERIVED from the tool's own source, not only typed here: exactly one
    # success sentinel per tool, and it is the one this test pins.
    derived = _success_tokens(PLATE_SHEETS[name])
    assert derived == {sentinel}, (name, sorted(derived))
    assert mod.main(argv) == 0, name
    assert sentinel in capsys.readouterr().out, name
    assert os.path.exists(out) and os.path.getsize(out) > 0, out


@pytest.mark.parametrize("name", sorted(SHEETS))
def test_every_sheet_main_takes_the_plate_from_argv(name, tmp_path, capsys):
    """The flag is not merely declared — the value reaches the line the tool prints."""
    mod, argv, out, _sentinel, _exc = SHEETS[name](tmp_path, plate="154,154,157")
    assert mod.main(argv) == 0, name
    assert "154, 154, 157" in capsys.readouterr().out.replace("[", "(").replace("]", ")")


@pytest.mark.parametrize("name", sorted(SHEETS))
def test_every_sheet_refuses_a_malformed_plate_and_writes_nothing(name, tmp_path):
    """REFUSAL direction, on the same flag: a typed error, and no file left behind."""
    mod, argv, out, _sentinel, exc = SHEETS[name](tmp_path, plate="nope")
    with pytest.raises(exc, match=r"--sheet-plate takes three 0-255 integers"):
        mod.main(argv)
    assert not os.path.exists(out)
