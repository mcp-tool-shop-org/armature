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
"""

import ast
import glob
import json
import os
import sys

import pytest
from PIL import Image

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


def _dests_declared(tree):
    """Every argparse DEST this module's `add_argument` calls declare.

    The dest, not the spelling: `--frames-dir` is read as `a.frames_dir`, and an explicit
    `dest=` overrides both. Keyed on the PARSER, which is the node the defect lives on.
    """
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
                name = arg.value
                if name.startswith("--"):
                    dest = name[2:].replace("-", "_")
                    break
                if not name.startswith("-"):
                    dest = name.replace("-", "_")
                    break
        if dest:
            out.add(dest)
    return out


def _namespace_attrs_read(tree):
    """Every attribute read off an argparse namespace, per function.

    Scoped to the function that called `parse_args`, because a module-wide walk for
    `<name>.<attr>` also collects `a.shape` off a numpy array called `a` two functions
    away — a census keyed on the wrong node, which is the class this wave exists to close.
    """
    def scope_nodes(scope):
        """Every node of one scope, NOT descending into a nested function.

        Descending is what made the first draft read `a.shape` off a numpy array in a
        helper whose own `a` is a parameter, while the namespace binding lives in `main`.
        """
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


def _parser_census():
    """`{module: (path, declared dests, namespace attrs read)}` over every `tools/*.py`."""
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO, "tools", "*.py"))):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        out[os.path.basename(path)[:-3]] = (path, _dests_declared(tree),
                                            _namespace_attrs_read(tree))
    return out


PARSERS = _parser_census()

#: Derived population: every module that READS `sheet_plate` off its own argparse
#: namespace. The read is the node — `make_gate0_sheet` had the read and not the flag.
PLATE_SHEETS = {m: v[0] for m, v in PARSERS.items() if "sheet_plate" in v[2]}


def test_the_plate_parsing_population_is_the_one_this_file_claims():
    """Size AND membership, so a sixth sheet joins the census the day it lands."""
    assert set(PLATE_SHEETS) == {
        "make_gate0_sheet", "make_identity_sheet", "make_lift_sheet",
        "make_startframe_sheet", "make_thesis_sheet"}, sorted(PLATE_SHEETS)
    assert len(PLATE_SHEETS) == 5


@pytest.mark.parametrize("module", sorted(PLATE_SHEETS))
def test_every_flag_a_sheet_reads_is_a_flag_its_parser_declares(module):
    """The gate-0 regression, stated as a property of the parser.

    `--sheet-plate` was READ and never DECLARED, so every invocation died in `main` with
    an `AttributeError` naming no flag. Any other undeclared read is the same defect.
    """
    _path, declared, read = PARSERS[module]
    undeclared = sorted(f for f in read if f not in declared)
    assert undeclared == [], (
        f"{module} reads {undeclared} off its own argparse namespace and its parser "
        f"declares no such argument; every invocation dies in main()")
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
    declared, read = _dests_declared(tree), _namespace_attrs_read(tree)
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
