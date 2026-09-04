"""Wave 10, builders — the exit convention's SUCCESS direction, and the fps clause.

Two censuses live here, and both exist because the wave-8 versions keyed on the wrong node.

* **The exit convention.** `test_packaging.py` derives the 13 CPU spend/fetch tools and
  pins the two FAILURE codes (2 = a gate refused, 1 = this tool crashed) and the
  `<PREFIX>_HALT` sentinel. It never pinned SUCCESS, and three builders returned an
  artifact — a graph dict, or a `(graph, record)` tuple — from `main()` under
  `raise SystemExit(main())`, so CPython printed the object to stderr and exited **1** on a
  fully gated success. Measured 2026-09-04 as subprocesses: `BUILD_ASSEMBLY_OK`,
  `BUILD_CASCADE_OK` and `BUILD_R2V_OK` all printed with every gate line green, 9 KB of
  graph on stderr, exit code 1 — the code those files' own comments reserve for "this tool
  crashed".

* **The fps clause.** `build_cascade_payload`'s record states `CreateVideo`'s measured
  contract as "fps FLOAT (1-120, default 30)" and wrote `--fps` into the node with no
  clause. Measured as subprocesses on an 81-entry padded map: `--fps=0`, `--fps=-5` and
  `--fps=999` each built the graph, passed all five gates including Gate ROUTE, and printed
  `BUILD_CASCADE_OK`. A tool that records a generator constraint and does not enforce it is
  the shape CLAUDE.md's "generation frames must be generator-legal" rule exists to prevent.

**The walk both censuses use is NON-DESCENDING** (F-c236304b, corrected 2026-09-04 after
instruments measured the same class in the other direction). `ast.walk(main_node)` descends
into nested `def`s and attributes THEIR returns to `main`: on
`tools/make_skeleton_sheet.py` it reports `return body, bones` for `main` when those two
returns belong to the closure `render(...)` defined inside it, and that `main` in fact has
zero direct returns and exits 0. The walk here stops at every nested
`FunctionDef`/`AsyncFunctionDef`/`Lambda`/`ClassDef`, and
`test_the_return_walk_does_not_descend_into_a_nested_def` pins that property directly, so
the census is proven on its own walk and not only on its population.
"""

import ast
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

import build_assembly_payload as ASSEMBLY  # noqa: E402
import build_cascade_payload as CASCADE  # noqa: E402
from armature_core import assembly as AS  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402


# =======================================================================================
# the population, derived the way test_packaging derives it
# =======================================================================================

def _spend_and_fetch_tools():
    """Every `tools/build_*payload*.py`, `tools/fetch_*.py`, `canon_gate.py` and
    `gate_saved_graph.py` — the CPU-side tools that author a submission, gate one, or
    retrieve its output. The same derivation `test_packaging._spend_and_fetch_tools` uses;
    the two must agree, and `test_the_population_agrees_with_the_packaging_census` says so.
    """
    tools = os.path.join(REPO, "tools")
    return sorted(
        n for n in os.listdir(tools)
        if n.endswith(".py")
        and ((n.startswith("build_") and "payload" in n)
             or n.startswith("fetch_")
             or n in ("canon_gate.py", "gate_saved_graph.py")))


CPU_TOOLS = _spend_and_fetch_tools()

_NESTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def direct_returns(fn):
    """Every `return` that belongs to `fn` ITSELF — the walk does not descend into a
    nested `def`, `lambda` or `class`.

    This is the node the exit convention lives on: `raise SystemExit(main())` passes
    `main`'s own return value to `SystemExit`, and a closure's return is not `main`'s.
    """
    out = []

    def walk(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _NESTED):
                continue
            if isinstance(child, ast.Return):
                out.append(child)
            walk(child)

    walk(fn)
    return out


def _module(filename):
    path = os.path.join(REPO, "tools", filename)
    return ast.parse(open(path, encoding="utf-8").read()), path


def _toplevel_def(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _main_block(tree):
    for node in tree.body:
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"):
            return node
    return None


def halt_prefix(tree):
    """The tool's OWN sentinel stem, read out of its `__main__` block.

    `<STEM_UPPER>` is NOT this stem: `build_assembly_payload.py` prints
    `BUILD_ASSEMBLY_HALT`, `gate_saved_graph.py` prints `SAVED_ADMISSION_HALT`, and
    `fetch_t2v_run.py` prints `FETCH_T2V_HALT`. One AST read of this literal derives both
    directions of the convention from one node.
    """
    block = _main_block(tree)
    found = set()
    for node in ast.walk(block) if block is not None else ():
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and node.value.strip().endswith("_HALT"):
            found.add(node.value.strip()[:-len("_HALT")])
    return sorted(found)


def test_the_population_agrees_with_the_packaging_census():
    """Size AND membership. A new spend or fetch tool joins both censuses the day it
    lands, or this fails rather than skipping it."""
    assert CPU_TOOLS == [
        "build_animate_payload.py", "build_assembly_payload.py",
        "build_camera_i2v_payload.py", "build_cascade_payload.py",
        "build_i2v_payload.py", "build_lora_arm_payload.py", "build_payload.py",
        "build_r2v_payload.py", "build_t2v_payload.py", "canon_gate.py",
        "fetch_run.py", "fetch_t2v_run.py", "gate_saved_graph.py"], CPU_TOOLS
    assert len(CPU_TOOLS) == 13


# =======================================================================================
# census 1 — main() hands SystemExit an int, never an artifact
# =======================================================================================

#: The ONE derived exemption, named and dated. `canon_gate.main` ends
#: `return args.func(args)` — a dispatch to this module's own subcommand handlers. It is
#: exempt from the "int literal" form because the reason is checkable rather than asserted:
#: `test_canon_gates_dispatch_targets_all_return_int_literals` re-derives every `cmd_*` in
#: that module and requires each of THEM to return int literals. Entered 2026-09-04.
DISPATCH_EXEMPT = {"canon_gate.py"}


def test_the_exemption_set_is_a_subset_of_the_population():
    assert DISPATCH_EXEMPT <= set(CPU_TOOLS)


@pytest.mark.parametrize("filename", CPU_TOOLS)
def test_every_cpu_tool_main_returns_an_int_to_SystemExit(filename):
    """`raise SystemExit(<object>)` prints the object to stderr and exits 1. Three builders
    did exactly that on their success path while printing their green OK line."""
    tree, path = _module(filename)
    main = _toplevel_def(tree, "main")
    assert main is not None, f"{filename} has no module-level main()"
    forms = [(r.lineno, ast.unparse(r.value) if r.value is not None else "None")
             for r in direct_returns(main)]
    if filename in DISPATCH_EXEMPT:
        pytest.skip(f"{filename}: dispatch form, checked by its own test")
    bad = [f for f in forms if f[1] not in ("0", "1", "2", "None")]
    assert not bad, (
        f"{filename}: main() returns {bad} to `raise SystemExit(main())`; CPython prints a "
        f"non-int object to stderr and exits 1 — the code this file's own comment reserves "
        f"for 'this tool crashed'")


def test_canon_gates_dispatch_targets_all_return_int_literals():
    """The exemption's REASON, re-derived rather than asserted: every `cmd_*` handler in
    `canon_gate` returns an int literal, so `return args.func(args)` returns an int."""
    tree, _path = _module("canon_gate.py")
    handlers = [n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name.startswith("cmd_")]
    assert {h.name for h in handlers} == {"cmd_resolve", "cmd_coverage", "cmd_check",
                                          "cmd_spend"}
    for h in handlers:
        forms = [ast.unparse(r.value) if r.value is not None else "None"
                 for r in direct_returns(h)]
        assert forms, f"{h.name} returns nothing"
        assert all(f in ("0", "1", "2", "None") for f in forms), (h.name, forms)


def test_the_census_goes_RED_on_a_main_that_returns_an_artifact(tmp_path):
    """The mutation: a module whose `main` returns a graph. A census that cannot fail is
    the class this wave exists to close."""
    fake = tmp_path / "build_nothing_payload.py"
    fake.write_text("def main(argv=None):\n    wf = {}\n    return wf\n", encoding="utf-8")
    main = _toplevel_def(ast.parse(fake.read_text(encoding="utf-8")), "main")
    forms = [ast.unparse(r.value) for r in direct_returns(main)]
    assert forms == ["wf"]
    assert not all(f in ("0", "1", "2", "None") for f in forms)


def test_the_return_walk_does_not_descend_into_a_nested_def(tmp_path):
    """The walk itself, pinned. `ast.walk` reports a closure's returns as `main`'s — which
    is how three sites in `make_skeleton_sheet.py`, `lift_clip.py` and `measure_lift.py`
    were filed as defects on 2026-09-04 and then withdrawn. Measured on the real file:
    `make_skeleton_sheet.main` has ZERO direct returns and exits 0."""
    src = ("def main(argv=None):\n"
           "    def render(x):\n"
           "        return x, x\n"
           "    render(1)\n"
           "    return 0\n")
    main = _toplevel_def(ast.parse(src), "main")
    assert [ast.unparse(r.value) for r in direct_returns(main)] == ["0"]
    assert len([n for n in ast.walk(main) if isinstance(n, ast.Return)]) == 2

    tree, _p = _module("build_r2v_payload.py")
    real_main = _toplevel_def(tree, "main")
    assert [r.lineno for r in direct_returns(real_main)], (
        "build_r2v_payload.main must have a direct return of its own")


# =======================================================================================
# census 2 — the SUCCESS sentinel is the HALT sentinel's prefix with _OK
# =======================================================================================

@pytest.mark.parametrize("filename", CPU_TOOLS)
def test_every_cpu_tool_has_exactly_one_halt_prefix(filename):
    tree, _path = _module(filename)
    assert len(halt_prefix(tree)) == 1, (
        f"{filename}: the __main__ block must print exactly one <PREFIX>_HALT literal; "
        f"found {halt_prefix(tree)}")


@pytest.mark.parametrize("filename", CPU_TOOLS)
def test_every_cpu_tool_prints_its_own_prefix_with_OK_on_success(filename):
    """One success convention across the 13. Before this landed the tree spelled it four
    ways: `BUILD_PAYLOAD ` (no _OK), `FETCH_RUN ` (no _OK), `FETCH_OK ` (the wrong prefix),
    and no success line at all in `canon_gate.py` and `build_lora_arm_payload.py`."""
    tree, path = _module(filename)
    prefix = halt_prefix(tree)[0]
    src = open(path, encoding="utf-8").read()
    printed = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            for lit in ast.walk(node):
                if isinstance(lit, ast.Constant) and isinstance(lit.value, str) \
                        and f"{prefix}_OK" in lit.value:
                    printed.add(lit.value.strip().split()[0])
    assert f"{prefix}_OK" in printed, (
        f"{filename} prints no `{prefix}_OK ` line on its success path; a wrapper cannot "
        f"tell a completed build from a silent one, and the failure half of this "
        f"convention already agrees across all 13. Source has: "
        f"{[l for l in src.splitlines() if '_OK' in l][:3]}")


def test_the_success_census_goes_RED_on_a_tool_that_prints_the_wrong_prefix(tmp_path):
    """The mutation: `fetch_t2v_run`'s pre-fix shape — a HALT prefix of `FETCH_T2V` and a
    success line spelled `FETCH_OK`."""
    fake = tmp_path / "fetch_wrong.py"
    fake.write_text(
        'def main(argv=None):\n'
        '    print("FETCH_OK " + "x")\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    try:\n'
        '        raise SystemExit(main())\n'
        '    except BaseException:\n'
        '        print("FETCH_T2V_HALT " + "{}")\n', encoding="utf-8")
    tree = ast.parse(fake.read_text(encoding="utf-8"))
    assert halt_prefix(tree) == ["FETCH_T2V"]
    printed = {lit.value.strip().split()[0]
               for node in ast.walk(tree)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id == "print"
               for lit in ast.walk(node)
               if isinstance(lit, ast.Constant) and isinstance(lit.value, str)
               and "_OK" in lit.value}
    assert "FETCH_T2V_OK" not in printed and "FETCH_OK" in printed


# =======================================================================================
# the behavioural leg — the three builders whose success exited 1
# =======================================================================================

def _padded_map(path, n=9):
    """`n` defaults to 9 because Gate L's wan rules require a 4n+1 frame count: an 8-frame
    clip is refused by `route_gates.verify` before any of these clauses is reached."""
    path.write_text(json.dumps({f"{i:05d}.png": f"srv_{i:05d}_aaaa.png"
                                for i in range(n)}), encoding="utf-8")
    return path


def _run(tool, *args, cwd=None):
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "tools"))
    return subprocess.run([sys.executable, os.path.join(REPO, "tools", tool), *args],
                          capture_output=True, text=True, env=env, cwd=cwd or REPO)


@pytest.mark.parametrize("tool,prefix", [
    ("build_assembly_payload.py", "BUILD_ASSEMBLY"),
    ("build_cascade_payload.py", "BUILD_CASCADE"),
])
def test_a_successful_build_exits_0_with_its_OK_line_and_no_HALT(tmp_path, tool, prefix):
    """The direction no census pinned. Measured before the fix on an 81-entry padded map:
    both printed every gate line green and their `_OK` line on stdout, dumped ~9 KB of the
    graph dict to stderr, and exited **1**."""
    up = _padded_map(tmp_path / "uploads.json", 81)
    proc = _run(tool, f"--uploads={up}", f"--out={tmp_path / 'out'}")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len([ln for ln in proc.stdout.splitlines()
                if ln.startswith(f"{prefix}_OK ")]) == 1, proc.stdout
    assert f"{prefix}_HALT" not in proc.stdout
    assert "class_type" not in proc.stderr, (
        "the graph was printed to stderr by SystemExit(<object>)")


def test_the_r2v_spend_builder_exits_0_on_a_fully_gated_success(tmp_path):
    """The E13 hosted-tier spend builder. Same defect, on the arm that costs money."""
    proc = _run("build_r2v_payload.py", "--arm=A1", "--seed=2026081351",
                f"--seeds={os.path.join(REPO, 'specs', 'E13-seeds.json')}",
                f"--prompt-file={os.path.join(REPO, 'specs', 'E13-prompt.json')}",
                f"--refs={_refs_record(tmp_path)}", f"--out={tmp_path / 'fresh'}",
                "--subject=BLACKGUARD", "--no-canon")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len([ln for ln in proc.stdout.splitlines()
                if ln.startswith("BUILD_R2V_OK")]) == 1, proc.stdout
    assert "BUILD_R2V_HALT" not in proc.stdout
    assert "class_type" not in proc.stderr


def _refs_record(tmp_path):
    p = tmp_path / "refs.json"
    p.write_text(json.dumps({"views": [{"upload_name": f"{i:064x}.png"} for i in range(2)]}),
                 encoding="utf-8")
    return p


def test_the_in_process_callers_still_get_the_artifact(tmp_path):
    """`main()` returns an int; the graph is handed back through `build_and_write`, so the
    tests that read it did not have to be weakened to make the exit code right."""
    up = _padded_map(tmp_path / "u.json", 9)
    wf = ASSEMBLY.build_and_write([f"--uploads={up}", f"--out={tmp_path / 'a'}"])
    assert wf["401"]["class_type"] == "CreateVideo"
    assert ASSEMBLY.main([f"--uploads={up}", f"--out={tmp_path / 'a2'}"]) == 0

    wf2 = CASCADE.build_and_write([f"--uploads={up}", f"--out={tmp_path / 'c'}"])
    assert wf2[str(CASCADE.VIDEO_ID)]["class_type"] == "CreateVideo"
    assert CASCADE.main([f"--uploads={up}", f"--out={tmp_path / 'c2'}"]) == 0


# =======================================================================================
# the fps clause (F-29693a0e)
# =======================================================================================

def test_the_fps_family_is_the_builders_that_write_a_flag_into_CreateVideo():
    """The population, DERIVED: every `tools/build_*payload*.py` whose parser declares
    `--fps` AND whose module writes a `CreateVideo` node. Keyed on the parser's
    `add_argument` calls and on the emitted `class_type` literal — not on a typed list, and
    not on the docstring, which is where the two named in the finding were found."""
    family = []
    for name in CPU_TOOLS:
        tree, _p = _module(name)
        flags, creates = set(), False
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument" and node.args
                    and isinstance(node.args[0], ast.Constant)):
                flags.add(node.args[0].value)
            if isinstance(node, ast.Constant) and node.value == "CreateVideo":
                creates = True
        if "--fps" in flags and creates:
            family.append(name)
    assert family == ["build_animate_payload.py", "build_assembly_payload.py",
                      "build_camera_i2v_payload.py", "build_cascade_payload.py",
                      "build_i2v_payload.py"], family


@pytest.mark.parametrize("bad", [0.0, -5.0, 999.0, 0.5, 120.5, float("nan")])
def test_an_out_of_contract_fps_is_refused_by_the_shared_clause(bad):
    """`CreateVideo` takes fps as a FLOAT bounded 1..120 — the contract this tool's OWN
    record states and did not enforce. NaN is in here because `nan > 120` and `nan < 1` are
    both False, so a range test written the obvious way admits it in both directions."""
    with pytest.raises(RG.RouteGate, match="fps"):
        ASSEMBLY.gate_create_video_fps(bad)


@pytest.mark.parametrize("ok", [1, 16, 30.0, 120])
def test_a_contract_legal_fps_passes_and_records_the_contract(ok):
    ev = ASSEMBLY.gate_create_video_fps(ok)
    assert ev["gate"] == "ROUTE" and ev["fps"] == float(ok)
    assert "1-120" in ev["contract"]


@pytest.mark.parametrize("bad", ["0", "-5", "999"])
def test_the_cascade_builder_refuses_an_illegal_fps_before_it_builds(tmp_path, bad):
    """Measured as subprocesses before the fix: each of these built the graph, passed all
    five gates including Gate ROUTE, and printed BUILD_CASCADE_OK."""
    up = _padded_map(tmp_path / "u.json", 9)
    with pytest.raises(RG.RouteGate, match="fps"):
        CASCADE.build_and_write([f"--uploads={up}", f"--out={tmp_path / 'o'}",
                                 f"--fps={bad}"])
    assert not (tmp_path / "o").exists(), "a refused build leaves no run directory"


@pytest.mark.parametrize("bad", ["0", "-5", "999"])
def test_the_assembly_builder_carries_the_same_clause(tmp_path, bad):
    """The sibling site named in the finding, fixed from the SAME function — not a copy."""
    up = _padded_map(tmp_path / "u.json", 9)
    with pytest.raises(RG.RouteGate, match="fps"):
        ASSEMBLY.build_and_write([f"--uploads={up}", f"--out={tmp_path / 'o'}",
                                  f"--fps={bad}"])
    assert not (tmp_path / "o").exists()


def test_the_fps_clause_is_reached_through_build_not_only_through_main(tmp_path):
    """The gate lives inside the function that emits the node, so an in-process caller
    cannot route around it."""
    with pytest.raises(RG.RouteGate, match="fps"):
        ASSEMBLY.build(["a.png", "b.png"], fps=0)
    with pytest.raises(RG.RouteGate, match="fps"):
        CASCADE.build(["a.png", "b.png"], fps=999)


def test_a_legal_fps_still_builds_and_the_record_says_what_was_checked(tmp_path):
    """The mutation that must not fire it, plus the receipt: the record already claimed the
    1-120 contract in `node_contracts_measured` while nothing read it."""
    up = _padded_map(tmp_path / "u.json", 9)
    CASCADE.build_and_write([f"--uploads={up}", f"--out={tmp_path / 'o'}", "--fps=120"])
    rec = json.loads((tmp_path / "o" / "E13-cascade-payload-record.json")
                     .read_text(encoding="utf-8"))
    assert rec["fps"] == 120.0
    assert rec["gates"]["CREATE_VIDEO_fps"]["fps"] == 120.0


def test_the_group_clause_still_binds_so_the_fps_clause_did_not_replace_it(tmp_path):
    """`--group` was the bounded flag the finding contrasted `--fps` against. It stays
    bounded."""
    up = _padded_map(tmp_path / "u.json", 9)
    with pytest.raises(AS.AssemblyGate, match="group size must be at least"):
        CASCADE.build_and_write([f"--uploads={up}", f"--out={tmp_path / 'o'}", "--group=0"])
