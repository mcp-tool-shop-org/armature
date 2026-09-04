"""Wave 8, instruments: the ONE halt contract every Blender-side tool answers to.

`tests/test_instrument_exits.py` (wave 6) asserts only `code not in (0, None)`. That
accepts a tool that returns 1 where the contract says 2, and it says nothing at all about
what the tool PRINTS — so a halt could name no gate, carry no evidence, and read to a
later session exactly like a crash. Three wave-7 findings are that gap:

* **F-7e64c103** — `preview_glb.py` had a bare module-level `main()`: no guard, no
  handler, no sentinel. `blender -b -P` exits **0** when the script's exception
  propagates, so every failure of that tool returned success. It was exempted from the
  wave-6 census by name, on a premise (`a library of preview helpers ... not invoked as a
  script`) that its own docstring line 3 contradicts.
* **F-1aee25e2** — `preview_walk.py`'s handler called `sys.exit(1)` unconditionally and
  printed neither `gate` nor `evidence`, in the one tool whose whole purpose is to be
  looked at before a credit is spent.
* **F-c3f86abc** — `rig_character.py`'s halt record hard-coded
  `"outcome": "HALTED — a gate fired"` with no branch, so a crash in the rigging code
  wrote a record asserting an andon fired.

THE CONTRACT, decided this wave and pinned here so the whole family answers to one shape:

    exit 2   the tool refused deliberately — `isinstance(exc, (GateFailure, ArmatureError))`
    exit 1   anything else: a crash

    stdout   exactly one line `<STEM>_HALT <json object>` where `<STEM>` is the module's
             basename upper-cased, carrying

                 tool      the module basename
                 outcome   HALTED — a gate fired          (a typed GateFailure)
                           REFUSED — the tool declined to proceed   (a bare ArmatureError)
                           FAILED — an unhandled error     (anything else)
                 gate      the andon id, or null
                 error     the exception class name
                 message   str(exc)
                 evidence  the gate's evidence dict, or null

The three outcomes are three states, not two: a bad `--mode=` value is a deliberate
refusal AND not a gate, and writing it either as "a gate fired" or as "an unhandled
error" is a false record. The five tools that also write `halt.json` (`rig_bake`,
`rig_character`, `rig_parts`, `rig_repair`, `rig_retopo`) carry the same fields there.

The population is DERIVED by walking `tools/` for `import bpy` (wave 8's census rule), and
the derivation takes the directory as an argument precisely so the red direction below can
point it at a tree that contains a defective member.
"""

import ast
import json
import os

import pytest

from blender_stub import TOOLS, blender_tools, exit_code_of_main_block, main_block

HALTED = "HALTED — a gate fired"
REFUSED = "REFUSED — the tool declined to proceed"
FAILED = "FAILED — an unhandled error"

#: The exact key set the sentinel carries. Asserted as a set so a tool cannot answer the
#: contract by printing a superset that a reader has to guess at.
SENTINEL_KEYS = {"tool", "outcome", "gate", "error", "message", "evidence"}


def blender_tools_in(directory):
    """Every `*.py` under `directory` that does `import bpy` — the wave-8 derivation.

    `blender_stub.blender_tools()` is this walk pinned to the repo's own `tools/`. This
    takes the directory so `test_the_derivation_catches_a_tool_that_does_not_answer`
    can run it over a tree carrying a member that fails the property.
    """
    names = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(directory, fn), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name == "bpy" for a in node.names):
                names.append(fn)
                break
    return names


#: Measured 2026-09-04 by the walk above over `tools/`. Written out so a new Blender tool
#: fails this file loudly rather than joining a census nobody re-read.
POPULATION = [
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py",
    "preview_walk.py", "probe_glb.py", "probe_subject.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py", "rig_bake.py", "rig_character.py",
    "rig_parts.py", "rig_repair.py", "rig_retopo.py",
]


def test_the_population_is_the_size_and_the_membership_it_was_measured_to_be():
    """SIZE and MEMBERSHIP, then the property — a census that quietly stopped
    enumerating would report green over everything it no longer reaches."""
    derived = blender_tools_in(TOOLS)
    assert len(derived) == 21, derived
    assert sorted(derived) == sorted(POPULATION), (
        sorted(set(derived) ^ set(POPULATION)))
    assert sorted(derived) == sorted(blender_tools()), "blender_stub disagrees with the walk"


def test_every_tool_in_the_population_has_a_main_guard():
    """There is no exemption. `preview_glb.py` was exempted by name for having no
    `__main__` block; it had none because it called `main()` unconditionally instead."""
    missing = [fn for fn in blender_tools_in(TOOLS) if main_block(fn) is None]
    assert missing == [], (
        f"{missing}: a Blender-side tool with no `__main__` handler. `blender -b -P` exits "
        f"0 when the script's exception propagates, so every failure returns success.")


def test_no_tool_calls_main_at_module_scope():
    """The other half of the same defect: a guard is not enough if `main()` is ALSO
    called bare, and a bare call is what made `preview_glb` unreachable to the census."""
    offenders = []
    for fn in blender_tools_in(TOOLS):
        with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "main"):
                offenders.append((fn, node.lineno))
    assert offenders == [], offenders


def _halt(filename, raiser, tmp_path, capsys):
    """Run the tool's handler with `main` replaced, and read back (code, sentinel)."""
    code, escaped = exit_code_of_main_block(
        filename, raiser=raiser,
        argv=["blender", "-b", "-P", filename, "--", "--glb=nope.glb",
              "--out=" + str(tmp_path / "out")])
    out = capsys.readouterr().out
    stem = filename[:-3].upper()
    lines = [ln for ln in out.splitlines() if ln.startswith(stem + "_HALT ")]
    return code, escaped, lines


def _assert_sentinel(filename, lines, *, outcome, gate, error, evidence):
    """The shape assertion, factored out so the red direction below can feed it a
    defective handler's output and watch it refuse."""
    if len(lines) != 1:
        raise AssertionError(
            f"{filename}: expected exactly one `{filename[:-3].upper()}_HALT ` line, got "
            f"{len(lines)}: {lines}")
    payload = json.loads(lines[0].split(" ", 1)[1])
    if set(payload) != SENTINEL_KEYS:
        raise AssertionError(f"{filename}: sentinel keys {sorted(payload)}")
    if payload["tool"] != filename[:-3]:
        raise AssertionError(f"{filename}: tool {payload['tool']!r}")
    if payload["outcome"] != outcome:
        raise AssertionError(f"{filename}: outcome {payload['outcome']!r}, want {outcome!r}")
    if payload["gate"] != gate:
        raise AssertionError(f"{filename}: gate {payload['gate']!r}, want {gate!r}")
    if payload["error"] != error:
        raise AssertionError(f"{filename}: error {payload['error']!r}, want {error!r}")
    if payload["evidence"] != evidence:
        raise AssertionError(f"{filename}: evidence {payload['evidence']!r}")
    return payload


@pytest.mark.parametrize("filename", POPULATION)
def test_a_typed_gate_exits_two_and_names_itself(filename, tmp_path, capsys):
    from armature_core.errors import GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    def raiser():
        raise _Gate("a gate fired", {"measured": 1})

    code, escaped, lines = _halt(filename, raiser, tmp_path, capsys)
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    assert code == 2, f"{filename}: exit {code!r}; a fired andon is 2"
    _assert_sentinel(filename, lines, outcome=HALTED, gate="PROBE", error="_Gate",
                     evidence={"measured": 1})


@pytest.mark.parametrize("filename", POPULATION)
def test_a_bare_refusal_exits_two_and_names_no_gate(filename, tmp_path, capsys):
    """An `ArmatureError` that is not a `GateFailure` is a deliberate refusal with no
    andon behind it — a bad `--mode=` value, a usage error. It is not a crash (exit 2),
    and it is not a gate (`gate` is null, and the outcome does not say one fired)."""
    from armature_core.errors import ArmatureError

    def raiser():
        raise ArmatureError("unknown --mode='wobble'; known: skeleton, full")

    code, escaped, lines = _halt(filename, raiser, tmp_path, capsys)
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler"
    assert code == 2, f"{filename}: exit {code!r}; a deliberate refusal is 2"
    _assert_sentinel(filename, lines, outcome=REFUSED, gate=None, error="ArmatureError",
                     evidence=None)


@pytest.mark.parametrize("filename", POPULATION)
def test_a_crash_exits_one_and_is_not_recorded_as_a_gate(filename, tmp_path, capsys):
    """F-c3f86abc's direction: the two records must DIFFER. A `ValueError` may not
    produce an outcome containing 'a gate fired'."""
    def raiser():
        raise ValueError("a bug, not a gate")

    code, escaped, lines = _halt(filename, raiser, tmp_path, capsys)
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler"
    assert code == 1, f"{filename}: exit {code!r}; a crash is 1"
    payload = _assert_sentinel(filename, lines, outcome=FAILED, gate=None,
                               error="ValueError", evidence=None)
    assert "gate fired" not in payload["outcome"]


#: The five tools that ALSO leave `halt.json` on disk, with an argv their own `parse_args`
#: accepts — the handler re-parses it to find out where to write. Derived below and pinned
#: against the derivation, so a sixth halt-file writer cannot join unnoticed.
HALT_FILE_ARGV = {
    "rig_bake.py": ["--retopo=nope.glb", "--source=nope.glb", "--max-deviation=0.1"],
    "rig_character.py": ["--glb=nope.glb"],
    "rig_parts.py": ["--glb=nope.glb"],
    "rig_repair.py": ["--glb=nope.glb"],
    "rig_retopo.py": ["--glb=nope.glb"],
}


def test_the_halt_file_writers_are_the_five_they_were_measured_to_be():
    """Derived from the tree: a tool whose `__main__` block writes `halt.json`."""
    derived = sorted(fn for fn in blender_tools_in(TOOLS)
                     if '"halt.json"' in open(os.path.join(TOOLS, fn),
                                              encoding="utf-8").read())
    assert derived == sorted(HALT_FILE_ARGV), derived


@pytest.mark.parametrize("filename", sorted(HALT_FILE_ARGV))
def test_the_halt_file_says_which_of_the_three_happened(filename, tmp_path, capsys):
    """The five tools that also leave a record on disk write the SAME outcome vocabulary.

    `rig_character._write_halt` hard-coded 'HALTED — a gate fired' for every exception it
    was handed; a crash in the rigging code wrote a record asserting an andon fired, next
    to a note explaining that gates after the one that fired are NOT YET RUN."""
    from armature_core.errors import ArmatureError, GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    seen = {}
    for label, exc in (("gate", _Gate("a gate fired", {"measured": 1})),
                       ("refusal", ArmatureError("unknown --mode='wobble'")),
                       ("crash", ValueError("a bug, not a gate"))):
        out = tmp_path / label
        code, escaped = exit_code_of_main_block(
            filename, raiser=(lambda e=exc: (_ for _ in ()).throw(e)),
            argv=(["blender", "-b", "-P", filename, "--", "--out=" + str(out)]
                  + HALT_FILE_ARGV[filename]))
        capsys.readouterr()
        assert escaped is None, (filename, label, escaped)
        with open(out / "halt.json", encoding="utf-8") as fh:
            seen[label] = json.load(fh)

    assert seen["gate"]["outcome"] == HALTED, seen["gate"]
    assert seen["gate"]["gate"] == "PROBE", seen["gate"]
    assert seen["refusal"]["outcome"] == REFUSED, seen["refusal"]
    assert seen["crash"]["outcome"] == FAILED, seen["crash"]
    assert "gate fired" not in seen["crash"]["outcome"]
    assert seen["crash"]["gate"] is None, seen["crash"]


def test_the_derivation_catches_a_tool_that_does_not_answer(tmp_path):
    """The RED direction for the population walk: a census that cannot fail is not a
    census. A tree carrying a tool with a bare `main()` and no guard must be enumerated
    by the derivation and must fail the property."""
    (tmp_path / "sneaky_tool.py").write_text(
        "import bpy\n\n\ndef main():\n    return 0\n\n\nmain()\n", encoding="utf-8")
    (tmp_path / "not_a_blender_tool.py").write_text("import os\n", encoding="utf-8")

    derived = blender_tools_in(str(tmp_path))
    assert derived == ["sneaky_tool.py"], derived

    tree = ast.parse((tmp_path / "sneaky_tool.py").read_text(encoding="utf-8"))
    guards = [n for n in tree.body
              if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
              and isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__"]
    bare = [n.lineno for n in tree.body
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Name) and n.value.func.id == "main"]
    assert guards == [] and bare == [8], (guards, bare)


def test_the_shape_assertion_refuses_a_defective_handlers_output():
    """The RED direction for the property: the exact line `preview_walk` used to print —
    no gate, no evidence, no outcome — must not pass."""
    old = ('PREVIEW_WALK_HALT {"error": "RuntimeError", "message": '
           '"the preview is not complete: 1 of 16 frames were never written"}')
    with pytest.raises(AssertionError):
        _assert_sentinel("preview_walk.py", [old], outcome=HALTED, gate="PREVIEW",
                         error="RuntimeError", evidence={"missing": ["00007.png"]})
