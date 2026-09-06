"""Every Blender-side tool's `__main__` handler exits with the code its outcome earns.

`blender -b -P script.py` exits **0** when the script's exception propagates: the repo has
measured that three times (`rig_character.py:1134`, `rig_parts.py:126`,
`author_walk.py:13`) and every gating tool's docstring repeats it. A halt that returns
success is not a halt — a shell chain or a CI step reading `$LASTEXITCODE` walks straight
past it.

Two defects of that class were routed into wave 6 and this file is the family census that
would have caught both, plus the eight siblings nobody had filed:

* `render_turnaround.py` (F-1fa79db9) — `if __name__ == "__main__": main()`, bare, in the
  one gating renderer that did not carry the handler its five siblings do. Gates ALPHA,
  TURN, WHOLE, CROP and every `RenderTurnaroundGate` halted Blender with status 0.
* `rig_character.py` (F-f5530688) — the handler re-parses `sys.argv` and re-hashes the GLB
  INSIDE its own `except` block, before `sys.exit`. A bad flag or a mistyped path raises
  there, the new exception leaves the whole `try` statement, and `sys.exit` never runs.

WAVE 8, F-ea5aaab8 — why `code not in (0, None)` is no longer the assertion.

All four directions asserted only that the code was non-zero, so the 2-vs-1 distinction
wave 6 created was pinned by nothing at all. Measured 2026-09-04 by driving
`blender_stub.exit_code_of_main_block` over all 20 handler-carrying tools with three
raisers: `preview_walk.py` returned **1** for a `GateFailure` and 1 for an `ArmatureError`
where the contract says 2, and `rig_bake`, `rig_character`, `rig_parts`, `rig_repair` and
`rig_retopo` all returned 1 for an `ArmatureError`. Every one of those passed all four
tests. The halt sentinel was unpinned in the same way: measured shapes included
`RIG_CHARACTER_HALT_RECORD_NOT_WRITTEN`, `rig_parts`' bare `ERROR {"gate": "n/a"}`, and
five tools whose `<TOOL>_HALT` line carried no `gate` key at all.

THE CONTRACT (one shape, agreed with the instruments domain 2026-09-04 and pinned here):

  exit code   `2` when the exception is a `GateFailure` OR a bare `ArmatureError`
              — a deliberate refusal — and `1` for anything else, which is a crash.
              Nothing else, ever: an operator or a workflow step that branches on 2 is
              asking "did this tool decide not to proceed?", and a crash answering 2 or a
              refusal answering 1 both give it the wrong answer.

  stdout      EXACTLY ONE line `<STEM>_HALT <json object>`, `<STEM>` being the module
              basename upper-cased. The object carries EXACTLY six keys: `tool`, `outcome`,
              `gate`, `error`, `message`, `evidence`.

  outcome     one of three literals, spaced em-dash included:
              "HALTED — a gate fired"                     (GateFailure)
              "REFUSED — the tool declined to proceed"    (ArmatureError, not GateFailure)
              "FAILED — an unhandled error"               (anything else)
              Three, not two, because a bad `--mode=` is a refusal and not a gate.

WAVE 10, F-6320c8e2 — this contract used to end the stdout clause with "printed from a
`finally` so it survives a failed `halt.json` write", stated of all 21, and it is a
property 16 of them do not have. Measured 2026-09-04 over every `__main__` block: five
tools (`rig_bake`, `rig_character`, `rig_parts`, `rig_repair`, `rig_retopo`) use a `finally`
and write a halt record; the other 16 print from a bare `except BaseException` block, use
no `finally`, and write no halt record at all — so there is no `halt.json` write for their
sentinel to survive and no `finally` protecting it. `sentinel_violations` reads the printed
line only and asserts nothing about the block's shape, so the discrepancy was invisible; a
maintainer reading this docstring would reason that any secondary failure in a handler still
yields a sentinel and an exit code, which F-7467e90d measures to be false for all 21.

So the contract is split, and the split is asserted rather than described:

  all 21     one sentinel line, six keys, three outcomes, the 2/2/1 codes, and `sys.exit`
             reached on every path (including an evidence dict the sentinel cannot
             serialise as written — see the F-7467e90d block below).

  the five   additionally write a halt RECORD, from a `finally` so it survives a failed
  writers    write of that record. Which five is derived, not typed:
             `test_the_halt_record_writers_are_the_ones_the_contract_names`. The halt-FILE
             half itself is asserted in `tests/test_instruments_amend_w8.py:214-267`.

WAVE 12, F-6b3040d1 — the population is keyed on BEHAVIOUR, not on the token `import bpy`.

`blender_stub.blender_tools()` derived its population from an `ast.Import` naming `bpy`.
`tools/stage_render.py` writes none: it reaches Blender through a lazily-instantiated
backend ("Imports bpy only when instantiated", stage_render.py:106) and a grep for
`import bpy` in it returns zero hits — so the walk returned 21 names, `stage_render` was
not among them, `test_amend_w10_builders.CPU_TOOLS` did not carry it either, and NO TEST IN
THIS REPO asserted its exit code or its halt sentinel. What sat outside: its documented
invocation is `blender -b -P tools/stage_render.py -- <args>` (README.md:181), its
`__main__` is a bare `sys.exit(main())`, and `main` catches `GateFailure` only — so a
`SpecError` (an `ArmatureError`, not a `GateFailure`) leaves `main` with a traceback, no
`STAGE_RENDER_HALT` line and no `sys.exit(2)`, which under `blender -b -P` is exit 0. That
is on the tool that writes the run directory, the per-frame manifest and the control frames
every downstream payload builder consumes.

`blender_tools()` now keys on the behaviour and returns 22. The handler itself is
instruments-measure's to write (F-f9251c74); until it lands, `stage_render` is counted in
its OWN category — `HALT_CONTRACT_PENDING` below, keyed on the objective property "prints
no `<STEM>_HALT` line anywhere", so the category empties itself the moment the handler
arrives rather than needing to be remembered.

The population is derived (`blender_stub.blender_tools`), never typed out, so a new Blender
tool joins it the day it lands.

WAVE 23, F-2f1b18c2 — THE SECOND POPULATION, and the derivation hazard it exposed.

Everything above is the Blender side. The 42 CPython instruments were in no equivalent
census, and that half holds the tools whose artifacts are UPLOADED. The second population
and its three properties are at the foot of this file; `blender_stub.halt_handler` derives
each member's halt PREFIX and ENTRY off its `__main__` block, and two hazards make that
derivation load-bearing rather than a formality:

* **The prefix is not the module stem**, for 20 of the 25 CPython tools that carry a
  handler. `build_animate_payload.py` prints `BUILD_ANIMATE_HALT`, `gate_saved_graph.py`
  prints `SAVED_ADMISSION_HALT`, `gate_b_frames.py` prints `GATE_B_HALT`,
  `project_pose_keypoints.py` prints `PROJECT_POSE_HALT`. `halt_contract_pending` keys on
  `<STEM>_HALT`, which is correct on the Blender side where every prefix IS the stem; the
  same predicate applied here reports 20 of 25 as carrying no handler at all.
* **The entry is not always `main`.** `composite_reference.py` is
  `run_tool_main(_cli, "COMPOSITE_REFERENCE")`. A driver that substitutes `main` runs the
  real `_cli`, which fails for its own reasons — measured here as a false exit 1 on a
  raiser that never ran, i.e. a census reporting a contract violation that does not exist.

Both are read off the block rather than assumed, which is what "keys on the resolved shape"
means for a population whose members disagree about their own spelling.
"""

import json
import os

import pytest

from blender_stub import (blender_tools, cpython_tools, exit_code_of_main_block,
                          halt_handler, main_block, read_source)

#: Re-derived 2026-09-04 and EMPTY (F-d5bd42b1). It held `preview_glb.py` under the
#: comment "a library of preview helpers with no `__main__` block; it is not invoked as a
#: script and so has no exit code to be wrong about". The file falsifies the second clause
#: on line 2 of its own docstring, which is the invocation
#: `blender -b --factory-startup -P preview_glb.py -- --glb <path> --out <dir> --name
#: <name>`, and its last line is a bare module-level `main()` with no `try`/`except` and no
#: `SystemExit` — so every failure propagates, and under `blender -b -P` that is exit 0.
#: The exemption's premise was false in the file that stated it, which is what an unchecked
#: exemption comment is worth. `preview_glb` gets the handler its 20 siblings carry (the
#: instruments wave-8 amend, "21 of 21"), so this set is empty and the population below is
#: the whole Blender side of the repo.
NO_MAIN_BLOCK = ()

WITH_MAIN = [f for f in blender_tools() if main_block(f) is not None]

#: Derived by `blender_tools()` on 2026-09-04. Equality, so a new Blender tool cannot join
#: the tree without joining this census in the same commit.
#: WAVE 12 (F-6b3040d1): `stage_render.py` JOINED when the population stopped keying on the
#: literal token `import bpy`. It is not new code; it was invisible.
RECORDED_BLENDER_TOOLS = [
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py",
    "preview_walk.py", "probe_glb.py", "probe_subject.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py", "rig_bake.py", "rig_character.py",
    "rig_parts.py", "rig_repair.py", "rig_retopo.py", "stage_render.py",
]


def halt_contract_pending(filename):
    """A reason string if this member prints no `<STEM>_HALT` line at all, else None.

    THE CATEGORY, not a skip flag (wave 12, rule 3: a walk that cannot judge a site reports
    it in its own category rather than `continue`ing past it). A member that carries no
    sentinel token anywhere in its source cannot be measured against a contract whose every
    clause reads that line; asserting the clauses one at a time would produce fourteen
    identical failures saying the same single thing.

    Keyed on the OBJECTIVE property — the `<STEM>_HALT` literal — so the category empties
    itself the moment the handler lands, and `test_the_pending_category_may_not_grow` fails
    if anything else falls into it.
    """
    stem = os.path.basename(filename)[:-3].upper()
    if f"{stem}_HALT" in read_source(filename):
        return None
    return (
        f"{filename} joined this census in wave 12 (F-6b3040d1) when the population stopped "
        f"keying on the literal token `import bpy` and started keying on the behaviour "
        f"'runs under Blender'. It prints no `{stem}_HALT` line anywhere: its `__main__` is "
        f"a bare `sys.exit(main())` and `main` catches `GateFailure` only, so a plain "
        f"`ArmatureError` escapes and `blender -b -P` exits 0. The handler is "
        f"instruments-measure's to write (F-f9251c74, wave 12); this file's half is the "
        f"population that makes it visible.")


#: RE-DERIVED 2026-09-04 (wave 14, F-49eb5adc) and EMPTY, the way `NO_MAIN_BLOCK` above
#: already is.
#:
#: What it held: `{"stage_render.py"}`, routed to instruments-measure as F-f9251c74 in wave
#: 12. That fix landed — `tools/stage_render.py` carries the `STAGE_RENDER_HALT` literal
#: `halt_contract_pending` keys on — so `[f for f in WITH_MAIN if halt_contract_pending(f)]`
#: is `[]`. The entry then did worse than say nothing: the test below asserted
#: `set([]) <= {"stage_render.py"}` and iterated `for name in sorted([])`, so the clause that
#: exists to prove "the reason is a real, readable one, not an empty string standing in for
#: evidence" examined a zero-length population and could not fire. A synthetic member is fed
#: to `halt_contract_pending` there now, because the real population no longer supplies one.
#:
#: Re-derive with the suite interpreter (tests/conftest.py module docstring):
#:     .venv/Scripts/python.exe -c "import sys;sys.path[:0]=['tests','tools'];\
#:     import test_instrument_exits as M;\
#:     print([f for f in M.WITH_MAIN if M.halt_contract_pending(f)])"
HALT_CONTRACT_PENDING = set()

GATE_OUTCOME = "HALTED \u2014 a gate fired"
REFUSAL_OUTCOME = "REFUSED \u2014 the tool declined to proceed"
CRASH_OUTCOME = "FAILED \u2014 an unhandled error"

SENTINEL_KEYS = {"tool", "outcome", "gate", "error", "message", "evidence"}

#: `(exit code, outcome literal, gate value)` per raiser kind. The gate value is
#: `getattr(exc, "gate", None)`, so a typed gate names itself and the other two are null.
CONTRACT = {
    "gate": (2, GATE_OUTCOME, "PROBE"),
    "refusal": (2, REFUSAL_OUTCOME, None),
    "crash": (1, CRASH_OUTCOME, None),
}


def _raiser(kind):
    from armature_core.errors import ArmatureError, GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    def gate():
        raise _Gate("a gate fired", {"measured": 1})

    def refusal():
        raise ArmatureError("a refusal, not a crash")

    def crash():
        raise ValueError("an ordinary mistake")

    return {"gate": gate, "refusal": refusal, "crash": crash}[kind]


def sentinel_violations(stem, stdout, kind, code):
    """Everything the contract says about one halt, as a list of failures.

    Written as a pure function of `(stem, stdout, kind, code)` so that the checker itself
    can be shown red against synthetic halts — a checker exercised only against the tools
    it polices reports a clean tree whenever it has quietly stopped looking.
    """
    want_code, want_outcome, want_gate = CONTRACT[kind]
    bad = []
    if code != want_code:
        bad.append(f"exit code {code!r}, contract says {want_code}")

    token = f"{stem}_HALT"
    lines = [l for l in stdout.splitlines() if l.split(" ", 1)[0] == token]
    if len(lines) != 1:
        near = [l for l in stdout.splitlines() if "HALT" in l or l.startswith("ERROR")]
        bad.append(f"{len(lines)} `{token} <json>` line(s) on stdout, want exactly 1; "
                   f"lines carrying HALT/ERROR: {near}")
        return bad

    payload = lines[0][len(token):].strip()
    try:
        rec = json.loads(payload)
    except ValueError as exc:
        bad.append(f"the sentinel's payload is not JSON ({exc}): {payload[:120]!r}")
        return bad
    if not isinstance(rec, dict):
        bad.append(f"the sentinel's payload is {type(rec).__name__}, not an object")
        return bad

    if set(rec) != SENTINEL_KEYS:
        bad.append(f"keys {sorted(rec)}, contract says {sorted(SENTINEL_KEYS)}")
    if rec.get("outcome") != want_outcome:
        bad.append(f"outcome {rec.get('outcome')!r}, contract says {want_outcome!r}")
    if rec.get("gate") != want_gate:
        bad.append(f"gate {rec.get('gate')!r}, contract says {want_gate!r}")
    if "tool" in rec and rec["tool"] != stem.lower():
        bad.append(f"tool {rec['tool']!r}, contract says {stem.lower()!r}")
    if "evidence" in rec and not isinstance(rec["evidence"], (dict, type(None))):
        bad.append(f"evidence is {type(rec['evidence']).__name__}, want an object or null")
    if kind == "gate" and rec.get("evidence") != {"measured": 1}:
        bad.append(f"evidence {rec.get('evidence')!r}; a fired gate carries the "
                   f"measurement that fired it")
    return bad


def _run(filename, kind, tmp_path, argv=None):
    argv = argv or ["blender", "-b", "-P", filename, "--", "--glb=nope.glb",
                    "--out=" + str(tmp_path / "out")]
    return exit_code_of_main_block(filename, raiser=_raiser(kind), argv=argv)


#: Derived 2026-09-04 (F-6320c8e2). The five tools whose `__main__` block uses a `finally`
#: and writes a halt RECORD; the other 16 print their sentinel from a bare
#: `except BaseException` and write no record at all.
RECORDED_HALT_RECORD_WRITERS = [
    "rig_bake.py", "rig_character.py", "rig_parts.py", "rig_repair.py", "rig_retopo.py",
]


HALT_RECORD = "halt.json"


def _called_tail(call):
    import ast

    try:
        return ast.unparse(call.func).split(".")[-1]
    except Exception:                                                   # noqa: BLE001
        return ""


def _is_halt_path(expr):
    """True when this expression BUILDS a path whose last component is `halt.json`.

    A string constant that merely mentions the filename in prose is not one: the last path
    component is compared, so `"writes halt.json beside the outputs"` is not a path and
    `os.path.join(_d, "halt.json")` is.
    """
    import ast
    import posixpath

    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return posixpath.basename(expr.value.replace("\\", "/")) == HALT_RECORD
    if isinstance(expr, ast.Call) and _called_tail(expr) == "join" and expr.args:
        return _is_halt_path(expr.args[-1])
    return False


def _writes_halt_record_in(node):
    """True when `node` OPENS a `halt.json` path for writing — the behaviour, not a spelling.

    WAVE 14, F-e4919c09. This used to be `any ast.Constant string containing "halt.json"`
    anywhere in the MODULE, under a docstring stating "THE NODE: the `__main__` block's own
    statements". The stated reason for widening past the block was real — `rig_character`
    writes through `_write_halt`, which puts the literal one function away — but the widening
    applied to all 22 members, so a module docstring or an unrelated reader NAMING the file
    read as a halt-record writer. No live defect the day it was found (only the five rig
    tools carried the literal at all) and a census keyed on a spelling in a wave whose rule
    was that censuses key on behaviour.

    THE NODE now: an `open(<path ending in halt.json>, <write mode>)` call, or a
    `Path(...).write_text/write_bytes` on such a path, resolving a name bound to the path one
    assignment back (`path = os.path.join(out_dir, "halt.json")` … `open(path, "w")` is
    `rig_character`'s shape).
    """
    import ast

    bound = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Assign) and _is_halt_path(sub.value):
            bound |= {t.id for t in sub.targets if isinstance(t, ast.Name)}
    for call in ast.walk(node):
        if not isinstance(call, ast.Call):
            continue
        tail = _called_tail(call)
        if tail in ("write_text", "write_bytes"):
            target = getattr(call.func, "value", None)
            if target is not None and (_is_halt_path(target)
                                       or (isinstance(target, ast.Name)
                                           and target.id in bound)):
                return True
            continue
        if tail != "open" or not call.args:
            continue
        mode = ""
        if len(call.args) > 1 and isinstance(call.args[1], ast.Constant):
            mode = str(call.args[1].value)
        for kw in call.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = str(kw.value.value)
        if not any(c in mode for c in "wax"):
            continue
        first = call.args[0]
        if _is_halt_path(first) or (isinstance(first, ast.Name) and first.id in bound):
            return True
    return False


def _block_shape(filename):
    """`(uses_finally, writes_a_halt_record)` for one tool's `__main__` block.

    THE NODE: the `__main__` block's own statements, plus ONE HOP into a module-local
    function the block calls — the same one-hop rule `_census_nodes.functions_that_refuse`
    uses, and the reason the original widened to the whole module by mistake.

    **WAVE 25 (F-40316edd): the hop reaches the ONE handler too.** `uses_finally` is the
    contract's DELIVERY guarantee — "the sentinel line and `sys.exit` come from a `finally`,
    on every path" — and a block that is `run_tool_main(main, "STAGE_RENDER")` carries that
    guarantee without carrying a `try` of its own, because `armature_core.parts.run_tool_main`
    delivers both from its own `finally`. Read as an absent `finally`, the tool that ADOPTED
    the home would fail this assertion on the commit that adopted it, which is the census
    keying on the spelling rather than the resolved shape (wave 18, rule 1).
    """
    import ast

    tree = ast.parse(read_source(filename))
    block = next(n for n in tree.body
                 if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                 and getattr(n.test.left, "id", None) == "__name__")
    uses_finally = any(isinstance(n, ast.Try) and n.finalbody for n in ast.walk(block))
    if not uses_finally:
        uses_finally = any(
            isinstance(n, ast.Call) and _called_tail(n) == "run_tool_main"
            for n in ast.walk(block))

    local = {fn.name: fn for fn in ast.walk(tree)
             if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))}
    writes_record = _writes_halt_record_in(block)
    if not writes_record:
        for call in ast.walk(block):
            if isinstance(call, ast.Call) and _called_tail(call) in local:
                if _writes_halt_record_in(local[_called_tail(call)]):
                    writes_record = True
                    break
    return uses_finally, writes_record


def test_the_halt_record_writers_are_the_ones_the_contract_names():
    """The split this file's own prose used to state of all 21.

    Size and membership before the property: the five are DERIVED off the `finally` in each
    `__main__` block, and the halt-record write is asserted to agree with that derivation,
    so a sixth writer — or one of the five losing its `finally` — fails here rather than
    leaving the docstring describing a tree that no longer looks like it.
    """
    held = [f for f in WITH_MAIN if not halt_contract_pending(f)]
    shapes = {f: _block_shape(f) for f in held}
    # WAVE-10 MERGE (coordinator, 2026-09-04): the `finally` stopped discriminating the moment instruments closed the
    # key-serialisation escape (F-13bd448d) — every one of the 21 handlers now delivers its
    # sentinel line and `sys.exit` from a `finally`, so THE NODE for "writes a halt record" is
    # the record write itself, and the `finally` is asserted of all 21 as the contract's
    # delivery guarantee.
    writes = sorted(f for f, (_, rec) in shapes.items() if rec)
    assert writes == RECORDED_HALT_RECORD_WRITERS, {
        "appeared": sorted(set(writes) - set(RECORDED_HALT_RECORD_WRITERS)),
        "vanished": sorted(set(RECORDED_HALT_RECORD_WRITERS) - set(writes)),
    }
    with_finally = sorted(f for f, (fin, _) in shapes.items() if fin)
    assert with_finally == sorted(held), {
        "delivers its sentinel and exit outside a `finally`":
            sorted(set(held) - set(with_finally))}
    # WAVE-12 MERGE (coordinator, 2026-09-04): `stage_render` joined the population (22) and writes no halt record.
    assert len(held) - len(writes) == 17, (
        "16 tools print their sentinel and exit from the `finally` and write no halt record; "
        "the five that write one are the rig tools the contract names")


def test_the_halt_record_half_of_the_walk_is_red_on_a_module_that_only_names_the_file():
    """Rule 3 on the half that had no red proof (wave 14, F-e4919c09).

    Three synthetic modules, all carrying the literal `halt.json`, and the walk must
    separate them:

    * a module whose ONLY mention is a docstring — a reader, not a writer;
    * a module that OPENS the path for writing inside the `__main__` block;
    * a module that opens it one hop away, through a module-local helper the block calls,
      which is `rig_character`'s real shape and the reason the original walk was widened to
      the whole module by mistake.

    Under the substring predicate this replaced, all three read as writers, so the census
    could not have told a docstring from a write.
    """
    import ast
    import textwrap

    def shape(src):
        tree = ast.parse(textwrap.dedent(src))
        block = next(n for n in tree.body
                     if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                     and getattr(n.test.left, "id", None) == "__name__")
        local = {fn.name: fn for fn in ast.walk(tree)
                 if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if _writes_halt_record_in(block):
            return True
        return any(_writes_halt_record_in(local[_called_tail(c)])
                   for c in ast.walk(block)
                   if isinstance(c, ast.Call) and _called_tail(c) in local)

    only_names_it = '''
        """This tool writes halt.json beside its outputs when a gate fires."""
        import os
        def main(argv=None):
            return 0
        if __name__ == "__main__":
            import sys
            sys.exit(main())
    '''
    writes_in_the_block = '''
        import json, os, sys
        def main(argv=None):
            return 0
        if __name__ == "__main__":
            try:
                sys.exit(main())
            except BaseException as exc:
                with open(os.path.join("out", "halt.json"), "w") as fh:
                    json.dump({}, fh)
                raise
    '''
    writes_one_hop_away = '''
        import json, os, sys
        def _write_halt(out_dir, exc):
            path = os.path.join(out_dir, "halt.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({}, fh)
        def main(argv=None):
            return 0
        if __name__ == "__main__":
            try:
                sys.exit(main())
            except BaseException as exc:
                _write_halt("out", exc)
                raise
    '''
    assert shape(only_names_it) is False, (
        "a module whose only `halt.json` is in a docstring reads as a halt-record writer; "
        "the census is keyed on a spelling, not on the write")
    assert shape(writes_in_the_block) is True
    assert shape(writes_one_hop_away) is True

    # …and the predicate this replaced, run beside them, or the comparison says nothing.
    def substring_keyed(src):
        return any(isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and "halt.json" in n.value
                   for n in ast.walk(ast.parse(textwrap.dedent(src))))

    assert substring_keyed(only_names_it) is True, (
        "the substring predicate did not see the docstring; there is no defect to compare "
        "against and this test proves nothing")

    # A write in the wrong MODE is not a halt record either.
    reads_it_back = '''
        import json, os, sys
        def main(argv=None):
            return 0
        if __name__ == "__main__":
            with open(os.path.join("out", "halt.json")) as fh:
                json.load(fh)
            sys.exit(main())
    '''
    assert shape(reads_it_back) is False, reads_it_back


def test_the_block_shape_walk_can_tell_the_two_shapes_apart():
    """Rule 3 on the walk itself: a `finally`-less block must not read as a writer."""
    import ast

    with_finally = ast.parse(
        'if __name__ == "__main__":\n'
        "    try:\n"
        "        main()\n"
        "    except BaseException:\n"
        "        pass\n"
        "    finally:\n"
        "        print('X_HALT {}')\n")
    without = ast.parse(
        'if __name__ == "__main__":\n'
        "    try:\n"
        "        main()\n"
        "    except BaseException:\n"
        "        print('X_HALT {}')\n")
    for tree, expected in ((with_finally, True), (without, False)):
        block = tree.body[0]
        got = any(isinstance(n, ast.Try) and n.finalbody for n in ast.walk(block))
        assert got is expected


def test_the_population_sees_the_two_spellings_the_import_token_cannot(tmp_path,
                                                                       monkeypatch):
    """RED on the shapes that hide from the name (wave 12, rule 2).

    Three synthetic modules: one whose `import bpy` lives inside a function (a lazy import
    — `stage_render`'s backend does exactly this one module away), one that never writes
    the token at all and only DOCUMENTS `blender -b -P`, and one that is plainly CPython.
    The token-keyed walk this population used to be — a module-level `ast.Import` naming
    `bpy` — is run beside it and must be blind to the first two, or the comparison this
    test makes says nothing.
    """
    import ast as _ast

    import blender_stub

    lazy = ("def render(scene):\n"
            "    import bpy\n"
            "    return bpy.context\n")
    documented = ('"""Run me as `blender -b -P tools/probe_documented.py -- --out x`."""\n'
                  "from armature_core import blender_scene\n"
                  "def main():\n"
                  "    return blender_scene.backend()\n")
    plain = ("import json\n"
             "def main():\n"
             "    return json.dumps({})\n")
    for name, src in (("probe_lazy.py", lazy), ("probe_documented.py", documented),
                      ("probe_plain.py", plain)):
        (tmp_path / name).write_text(src, encoding="utf-8")
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))

    def token_keyed(fn):
        """The pre-wave-12 walk, verbatim: a MODULE-LEVEL `import bpy`."""
        tree = _ast.parse(blender_stub.read_source(fn))
        return any(isinstance(n, _ast.Import) and any(a.name == "bpy" for a in n.names)
                   for n in tree.body)

    assert blender_stub.blender_tools() == ["probe_documented.py", "probe_lazy.py"], (
        blender_stub.blender_tools())
    assert blender_stub.blender_reach("probe_lazy.py") == {"import bpy"}
    assert blender_stub.blender_reach("probe_documented.py") == {
        "documented `blender -b -P`", "armature_core.blender_scene backend"}
    assert blender_stub.blender_reach("probe_plain.py") == set()
    assert not token_keyed("probe_lazy.py"), (
        "the token-keyed walk saw the lazy import; it cannot, and if it could this test "
        "would be comparing a walk with itself")
    assert not token_keyed("probe_documented.py")


def test_the_pending_category_is_named_dated_and_may_not_grow():
    """Rule 3: what the census cannot judge is COUNTED, in its own category.

    The category is derived from the objective property, not from the list: a member that
    stops printing its sentinel falls in here and fails, and a member that starts printing
    one falls out and the list entry becomes deletable.
    """
    derived = sorted(f for f in WITH_MAIN if halt_contract_pending(f))
    assert set(derived) <= HALT_CONTRACT_PENDING, {
        "prints no `<STEM>_HALT` line and is not named as pending":
            sorted(set(derived) - HALT_CONTRACT_PENDING)}
    # WAVE 14, F-49eb5adc: EQUALITY. The subset direction alone let `stage_render.py` sit here
    # for a wave after its handler landed, naming nothing — and an entry that names nothing
    # cannot be deleted by the commit that closes it, because nothing fails.
    assert HALT_CONTRACT_PENDING == set(derived), {
        "named as pending and no longer pending (delete these)":
            sorted(HALT_CONTRACT_PENDING - set(derived))}
    assert HALT_CONTRACT_PENDING <= set(blender_tools()), sorted(
        HALT_CONTRACT_PENDING - set(blender_tools()))


def test_the_pending_reason_is_readable_evidence_and_not_an_empty_string(tmp_path,
                                                                        monkeypatch):
    """The clause that used to run over an empty list (wave 14, F-49eb5adc).

    `for name in sorted(derived)` was a ZERO-ITERATION loop the moment `stage_render`'s
    handler landed, so the one thing this category asserts about its own reasons — that they
    are readable evidence — checked nothing. The real population no longer supplies a
    sentinel-less member, so a synthetic one is put through `halt_contract_pending` itself:
    the predicate is exercised on the shape it exists to recognise, and its answer is read.
    """
    import blender_stub

    module = tmp_path / "probe_no_sentinel.py"
    module.write_text(
        "import bpy\n"
        "def main(argv=None):\n"
        "    return 0\n"
        'if __name__ == "__main__":\n'
        "    import sys\n"
        "    sys.exit(main())\n", encoding="utf-8")
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))

    reason = halt_contract_pending("probe_no_sentinel.py")
    assert reason, (
        "a module carrying no `<STEM>_HALT` literal anywhere reads as NOT pending; the "
        "category cannot recognise the shape it exists to hold")
    assert "F-f9251c74" in reason and "PROBE_NO_SENTINEL_HALT" in reason, reason
    assert reason.strip() == reason and len(reason) > 80, reason

    # …and the other direction, or the check above says nothing about the predicate: the
    # same module WITH the sentinel must read as not pending.
    module.write_text(
        "import bpy\n"
        "def main(argv=None):\n"
        "    return 0\n"
        'if __name__ == "__main__":\n'
        "    import sys\n"
        "    try:\n"
        "        sys.exit(main())\n"
        "    finally:\n"
        "        print('PROBE_NO_SENTINEL_HALT {}')\n", encoding="utf-8")
    assert halt_contract_pending("probe_no_sentinel.py") is None


def test_the_population_is_the_whole_blender_side_of_the_repo():
    """A census that quietly stopped enumerating would report green over anything."""
    tools = blender_tools()
    assert len(tools) == 22, tools
    assert tools == RECORDED_BLENDER_TOOLS, {
        "appeared": sorted(set(tools) - set(RECORDED_BLENDER_TOOLS)),
        "vanished": sorted(set(RECORDED_BLENDER_TOOLS) - set(tools)),
    }
    assert set(NO_MAIN_BLOCK) <= set(tools)
    assert sorted(set(tools) - set(WITH_MAIN)) == sorted(NO_MAIN_BLOCK), (
        "a Blender tool has no `__main__` handler, so every failure inside it propagates "
        "and `blender -b -P` reports success")


@pytest.mark.parametrize("kind", sorted(CONTRACT))
@pytest.mark.parametrize("filename", WITH_MAIN)
def test_the_exit_code_is_the_one_the_outcome_earns(filename, kind, tmp_path):
    """2 for a deliberate refusal (a typed gate OR a bare `ArmatureError`), 1 for a crash.

    `code not in (0, None)` — what this asserted until wave 8 — is satisfied by every
    tool collapsing every outcome to 1, which is the state six of twenty were in.
    """
    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    want_code = CONTRACT[kind][0]
    code, escaped = _run(filename, kind, tmp_path)
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    assert code == want_code, f"{filename} ({kind}): exit code {code!r}, contract says {want_code}"


@pytest.mark.parametrize("filename", WITH_MAIN)
def test_a_refusal_and_a_crash_do_not_answer_with_the_same_code(filename, tmp_path):
    """The divergence itself, stated separately from the two absolute codes: a regression
    that collapses every outcome to one number is invisible to a test that only asks for
    non-zero, and the whole point of the 2 is that it is NOT the 1."""
    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    refusal, _ = _run(filename, "refusal", tmp_path)
    crash, _ = _run(filename, "crash", tmp_path)
    assert refusal != crash, (
        f"{filename}: a refusal and an unhandled error both exit {refusal!r}; a caller "
        f"branching on 2 reads a crash as a decision, or a decision as a crash")


@pytest.mark.parametrize("kind", sorted(CONTRACT))
@pytest.mark.parametrize("filename", WITH_MAIN)
def test_the_halt_sentinel_says_which_of_the_three_things_happened(filename, kind,
                                                                   tmp_path, capsys):
    """The receipt, not just the code. A halt whose sentinel omits `gate` cannot be read
    back to the andon that produced it, which is the state the evidence-id census in
    `test_gates.py` exists to end — and stdout is where an operator reads it."""
    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    code, escaped = _run(filename, kind, tmp_path)
    out = capsys.readouterr().out
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    stem = filename[:-3].upper()
    bad = sentinel_violations(stem, out, kind, code)
    assert not bad, f"{filename} ({kind}):\n  " + "\n  ".join(bad)


@pytest.mark.parametrize("filename", WITH_MAIN)
def test_an_unparseable_argv_still_exits_non_zero(filename, tmp_path):
    """F-f5530688's exact shape. `main` fails on a bad flag; the handler then re-parses the
    SAME argv to find out where to write `halt.json`, and fails again. Whatever the handler
    does about that, it may not let the second failure delete the exit code."""
    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    code, escaped = _run(filename, "refusal", tmp_path,
                         argv=["blender", "-b", "-P", filename, "--", "--not-a-flag=1"])
    assert escaped is None, (
        f"{filename}: {escaped!r} escaped the handler. A second failure inside the `except` "
        f"block leaves the whole `try` statement and `sys.exit` never runs")
    assert code == 2, f"{filename}: exit code {code!r}, contract says 2 for a refusal"


@pytest.mark.parametrize("filename", WITH_MAIN)
def test_a_missing_glb_does_not_delete_the_exit_code(filename, tmp_path):
    """The other half of F-f5530688: `sha256_file(_args['glb'])` inside the `except` block
    raises `FileNotFoundError` on a mistyped path."""
    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    code, escaped = _run(filename, "crash", tmp_path,
                         argv=["blender", "-b", "-P", filename, "--",
                               "--glb=E:/no/such/file/at/all.glb",
                               "--out=" + str(tmp_path / "out")])
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    assert code == 1, f"{filename}: exit code {code!r}, contract says 1 for a crash"


# ------------------------------------- the input that escapes: evidence the sentinel cannot
#                                        serialise (wave 10, F-7467e90d)
#
# THE NODE THIS KEYS ON: the handler's own `print("<STEM>_HALT " + json.dumps({...},
# default=str))` followed by `sys.exit(...)`. The three argv/glb directions above vary the
# ARGV; not one of them varies the EVIDENCE, and the evidence is what the handler
# serialises. `json.dumps(default=str)` consults `default=` for VALUES only, never for
# KEYS, so a non-str key raises inside the `except` block, the second exception leaves the
# whole `try`, `sys.exit` never runs, and `blender -b -P` exits 0 — exactly the E07 failure
# the contract exists to end, with the census green.
#
# Measured 2026-09-04 on cd2d941 by driving `exit_code_of_main_block` over all 21 WITH_MAIN
# tools with three evidence shapes: 21 of 21 returned `code=None` with
# `TypeError("keys must be str, int, float, bool or None, not tuple")`,
# `... not numpy.int64`, and `ValueError("Circular reference detected")` respectively.
# That includes the five `rig_*` tools whose `finally` guards the halt.json write — the
# guard wraps the FILE write, not the `print`.
#
# Tuple-keyed and numpy-keyed evidence are ORDINARY here: per-view and per-frame
# measurements are how this repo's andons describe what fired them.
#
# Instruments owns the fix and is landing it in place in all 21 handlers (SEAM 3,
# 2026-09-04): the sentinel is built key-safely and the print moves inside its own
# try/except/finally so `sys.exit(_code)` runs on every path. This census asserts the
# BEHAVIOUR — no escape, the contract code — never the helper's name or location.


def _numpy_key():
    numpy = pytest.importorskip("numpy")
    return numpy.int64(3)


class _KeyWhoseStrRaises:
    """A key the KEYSAFE WALK ITSELF cannot survive.

    WAVE 12, F-e47781f3. The three shapes above are all shapes `_halt_keysafe` HANDLES —
    the census drives the fix's own happy path. The class the fix's structure does not cover
    is an exception raised INSIDE the walk: in all 21 handlers the call `_halt_keysafe(
    _detail)` builds `_sentinel` OUTSIDE the `try:` that guards `json.dumps`, so anything
    the keysafe walk raises escapes before the fallback line and before the `finally`
    carrying `print` + `sys.exit`.

    Measured 2026-09-04 with `blender_stub.exit_code_of_main_block` over all 21 WITH_MAIN
    tools: this shape returned `(code=None, escaped=ReferenceError)` for 21 of 21 — no
    sentinel line, `sys.exit` never reached, which under `blender -b -P` is exit 0 on a
    fired andon. A deeply nested (non-circular) dict returned `(None, RecursionError)` for
    21 of 21 by the same door.

    The shape this proves is STRUCTURAL, not about `__str__`: the keysafe call must move
    INSIDE the guarded `try`. `_keysafe_is_guarded` below reads exactly that off the AST,
    and the behavioural direction runs against each tool as soon as it holds.
    """

    def __str__(self):
        raise ReferenceError("this key cannot be stringified")

    def __repr__(self):
        raise ReferenceError("this key cannot be reprised either")

    def __hash__(self):
        return 7


def _evidence_shapes():
    """`(label, build)` per evidence dict — each a shape this repo's andons produce."""
    def per_view():
        return {"per_view": {(0, 30): 1.0}, "note": "a tuple key is a view pair"}

    def per_frame():
        return {"per_frame": {_numpy_key(): 0.5}}

    def circular():
        ev = {"gate": "PROBE"}
        ev["self"] = ev
        return ev

    def key_str_raises():
        return {"per_view": {_KeyWhoseStrRaises(): 1.0}, "gate": "PROBE"}

    return [("tuple_key", per_view), ("numpy_int_key", per_frame),
            ("circular", circular), ("key_str_raises", key_str_raises)]


EVIDENCE_SHAPES = _evidence_shapes()


def _keysafe_is_guarded(filename):
    """True when the handler builds its sentinel INSIDE the try that guards `json.dumps`.

    THE NODE: the inner `ast.Try` whose `finalbody` prints the `<STEM>_HALT` line. If the
    `_halt_keysafe(...)` call sits in that try's BODY, an exception raised while building
    the line falls to the fallback and the `finally` still delivers a sentinel and an exit
    code. If it sits above the try — where all 21 handlers put it on 2026-09-04 — the walk's
    own failure escapes the whole handler.

    **WAVE 25 (F-40316edd): the property is the RESOLVED shape, not the local spelling.**
    A tool that hands its `__main__` to `armature_core.parts.run_tool_main` has no local
    `ast.Try` and no local `_halt_keysafe` call at all — and it is guarded, because the ONE
    handler builds its sentinel inside its own guarded `try` (`parts.py::run_tool_main`,
    "Everything below that can fail is inside the guard"). Keying on the spelling turned
    `stage_render` — the 22nd Blender-side tool and the first to adopt the home — from a
    member this check RAN against into one it SKIPPED, on the commit that fixed it. That is
    wave 18's first rule (a census keys on the resolved shape) failing in the direction that
    loses coverage, so the adoption is read as the guarantee it is.

    **WAVE 28 (instruments, F-814335e4): the delegation branch keys on a CALL, not on the
    name appearing anywhere in the file — and this one failed in the direction that INVENTS
    coverage.** The five handlers that gained `except SystemExit: raise` carry a comment
    naming `armature_core.parts.run_tool_main` as the CPython home those two lines are
    adopted from. The substring test read all five as delegating, so `_keysafe_is_guarded`
    returned True and the five `key_str_raises` cases stopped skipping and started PASSING —
    MEASURED on this branch with the shortcut removed, the AST half answers **False** for all
    five, which is the honest answer: they build their sentinel above the guarded `try`
    exactly as they did before, and the wave-12 move (F-e47781f3) has still not landed on
    them. A test that passes because a census misread a comment is worse than the documented
    skip it replaced, so the five skip again, with their own reason.
    """
    import ast

    src = read_source(filename)
    if any(isinstance(n, ast.Call)
           and (getattr(n.func, "attr", None) == "run_tool_main"
                or getattr(n.func, "id", None) == "run_tool_main")
           for n in ast.walk(ast.parse(src))):
        return True
    stem = os.path.basename(filename)[:-3].upper()
    tree = ast.parse(src)
    block = next((n for n in tree.body
                  if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                  and getattr(n.test.left, "id", None) == "__name__"), None)
    if block is None:
        return False
    for node in ast.walk(block):
        if not (isinstance(node, ast.Try) and node.finalbody):
            continue
        delivers = any(
            isinstance(c, ast.Constant) and isinstance(c.value, str)
            and c.value.strip().startswith(f"{stem}_HALT")
            for c in ast.walk(ast.Module(body=node.finalbody, type_ignores=[])))
        if not delivers:
            continue
        guarded = ast.Module(body=node.body, type_ignores=[])
        if any(isinstance(c, ast.Call) and getattr(c.func, "id", None) == "_halt_keysafe"
               for c in ast.walk(guarded)):
            return True
    return False


#: The shapes whose behavioural direction is gated on a structural property the tool must
#: carry first. Named, dated 2026-09-04, keyed on the property rather than on a list of
#: tools, so it self-closes: `key_str_raises` runs against a tool the moment
#: `_keysafe_is_guarded` is true of it. The move is instruments'/instruments-measure's
#: (wave 12: "`_halt_keysafe` construction inside the guarded region").
SHAPES_NEEDING_A_GUARDED_CONSTRUCTION = {"key_str_raises"}

#: The two shapes whose sentinel must still be WELL FORMED after the fix: a key that can be
#: stringified. `circular` is held to the exit-code half only — a cycle cannot be
#: stringified away, and the contract clause it exercises is "`sys.exit` runs on every
#: path", not "the JSON is complete".
SERIALISABLE_SHAPES = {"tuple_key", "numpy_int_key"}


def _evidence_raiser(build):
    from armature_core.errors import GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    def gate():
        raise _Gate("a gate fired", build())

    return gate


@pytest.mark.parametrize("label,build", EVIDENCE_SHAPES, ids=[s[0] for s in EVIDENCE_SHAPES])
@pytest.mark.parametrize("filename", WITH_MAIN)
def test_a_measurement_keyed_evidence_dict_does_not_escape_the_handler(
        filename, label, build, tmp_path, capsys):
    """The direction the halt census never asserted: an evidence dict the sentinel cannot
    serialise as written. `escaped is None` and the contract's code, for every tool."""
    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    if label in SHAPES_NEEDING_A_GUARDED_CONSTRUCTION and not _keysafe_is_guarded(filename):
        pytest.skip(
            f"{filename} builds its sentinel — `_halt_keysafe(_detail)` — ABOVE the `try` "
            f"that guards `json.dumps`, so an exception raised inside the keysafe walk "
            f"escapes before the fallback line and before the `finally` that carries the "
            f"print and `sys.exit`. Measured 2026-09-04: (code=None, "
            f"escaped=ReferenceError) for 21 of 21. Moving the construction inside the "
            f"guarded region is instruments'/instruments-measure's half (wave 12, "
            f"F-e47781f3); this direction runs against this tool the moment it lands.")
    code, escaped = exit_code_of_main_block(
        filename, raiser=_evidence_raiser(build),
        argv=["blender", "-b", "-P", filename, "--", "--glb=nope.glb",
              "--out=" + str(tmp_path / "out")])
    out = capsys.readouterr().out
    assert escaped is None, (
        f"{filename} ({label}): {escaped!r} escaped the handler, so `sys.exit` never ran "
        f"and `blender -b -P` reports success on a fired gate")
    assert code == 2, f"{filename} ({label}): exit code {code!r}, contract says 2 for a gate"
    if label in SERIALISABLE_SHAPES:
        stem = filename[:-3].upper()
        token = f"{stem}_HALT"
        lines = [l for l in out.splitlines() if l.split(" ", 1)[0] == token]
        assert len(lines) == 1, f"{filename} ({label}): {len(lines)} sentinel lines"
        rec = json.loads(lines[0][len(token):].strip())
        assert set(rec) == SENTINEL_KEYS, sorted(rec)
        assert rec["gate"] == "PROBE"
        assert isinstance(rec["evidence"], dict)
        assert all(isinstance(k, str) for k in rec["evidence"]), rec["evidence"]


def test_the_evidence_shapes_this_census_drives_are_the_ones_json_dumps_refuses():
    """The premise, measured here rather than asserted: `default=` is consulted for VALUES
    only. If a future Python applied it to keys, these fixtures would stop probing anything
    and this test says so instead of going quietly green."""
    for label, build in EVIDENCE_SHAPES:
        with pytest.raises((TypeError, ValueError)):
            json.dumps(build(), default=str)
    # …and the same dicts serialise once the keys are strings, so the shapes are not
    # unserialisable in principle — the KEY is the whole defect.
    for label, build in EVIDENCE_SHAPES:
        if label not in SERIALISABLE_SHAPES:
            continue
        ev = build()
        flat = {k: {str(kk): vv for kk, vv in v.items()} if isinstance(v, dict) else v
                for k, v in ev.items()}
        json.dumps(flat, default=str)


def test_the_guarded_construction_walk_tells_the_two_handler_shapes_apart(tmp_path,
                                                                          monkeypatch):
    """The red direction for `_keysafe_is_guarded`, on both spellings of the handler.

    A check that cannot fail is not a check: the walk is driven against a handler that
    builds its sentinel ABOVE the guarded `try` (the shape all 21 carry on 2026-09-04) and
    against one that builds it INSIDE, and must answer differently.
    """
    import blender_stub

    unguarded = (
        "import json, sys\n"
        "def _halt_keysafe(d):\n"
        "    return {str(k): v for k, v in d.items()}\n"
        "def main():\n"
        "    return 0\n"
        'if __name__ == "__main__":\n'
        "    try:\n"
        "        raise SystemExit(main())\n"
        "    except SystemExit:\n"
        "        raise\n"
        "    except BaseException as exc:\n"
        "        _code = 1\n"
        "        _sentinel = {'evidence': _halt_keysafe(getattr(exc, 'evidence', {}))}\n"
        "        try:\n"
        "            _line = json.dumps(_sentinel, default=str)\n"
        "        except BaseException:\n"
        "            _line = '{}'\n"
        "        finally:\n"
        "            print('PROBE_UNGUARDED_HALT ' + _line)\n"
        "            sys.exit(_code)\n")
    guarded = unguarded.replace(
        "        _sentinel = {'evidence': _halt_keysafe(getattr(exc, 'evidence', {}))}\n"
        "        try:\n"
        "            _line = json.dumps(_sentinel, default=str)\n",
        "        try:\n"
        "            _sentinel = {'evidence': _halt_keysafe(getattr(exc, 'evidence', {}))}\n"
        "            _line = json.dumps(_sentinel, default=str)\n"
    ).replace("PROBE_UNGUARDED_HALT", "PROBE_GUARDED_HALT")

    (tmp_path / "probe_unguarded.py").write_text(unguarded, encoding="utf-8")
    (tmp_path / "probe_guarded.py").write_text(guarded, encoding="utf-8")
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))

    assert _keysafe_is_guarded("probe_unguarded.py") is False, (
        "a sentinel built above the guarded `try` must not read as guarded; the walk "
        "cannot distinguish the shape it exists to find")
    assert _keysafe_is_guarded("probe_guarded.py") is True


def test_a_key_whose_str_raises_escapes_an_unguarded_handler_and_not_a_guarded_one(
        tmp_path, monkeypatch):
    """The BEHAVIOUR behind the structural claim, driven end to end on both shapes.

    This is the shape F-e47781f3 measured escaping 21 of 21 handlers. Proving it here — on
    synthetic modules this file owns — means the census's fourth direction is shown red
    without waiting on the sibling domain that moves the construction in the 21.
    """
    import blender_stub

    def handler(token, guarded):
        build = ("        _sentinel = {'evidence': _halt_keysafe(_detail)}\n"
                 "        try:\n"
                 "            _line = json.dumps(_sentinel, default=str)\n")
        if guarded:
            build = ("        try:\n"
                     "            _sentinel = {'evidence': _halt_keysafe(_detail)}\n"
                     "            _line = json.dumps(_sentinel, default=str)\n")
        # RECURSIVE, like the 21 real ones: the raising key is nested under `per_view`,
        # which is where this repo's andons put a per-measurement key.
        return (
            "import json, sys\n"
            "def _halt_keysafe(d):\n"
            "    if isinstance(d, dict):\n"
            "        return {str(k): _halt_keysafe(v) for k, v in d.items()}\n"
            "    return d\n"
            "def main():\n"
            "    return 0\n"
            'if __name__ == "__main__":\n'
            "    try:\n"
            "        raise SystemExit(main())\n"
            "    except SystemExit:\n"
            "        raise\n"
            "    except BaseException as exc:\n"
            "        _code = 2\n"
            "        _detail = getattr(exc, 'evidence', None) or {}\n"
            + build +
            "        except BaseException:\n"
            "            _line = json.dumps({'evidence': None})\n"
            "        finally:\n"
            f"            print('{token} ' + _line)\n"
            "            sys.exit(_code)\n")

    (tmp_path / "probe_open.py").write_text(handler("PROBE_OPEN_HALT", False),
                                            encoding="utf-8")
    (tmp_path / "probe_shut.py").write_text(handler("PROBE_SHUT_HALT", True),
                                            encoding="utf-8")
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))

    raiser = _evidence_raiser(dict(EVIDENCE_SHAPES)["key_str_raises"])
    argv = ["blender", "-b", "-P", "probe.py"]

    code, escaped = exit_code_of_main_block("probe_open.py", raiser=raiser, argv=argv)
    assert isinstance(escaped, ReferenceError), (code, escaped)
    assert code is None, (
        "the unguarded handler must lose its exit code; if it does not, this fixture is "
        "not reproducing the shape the census exists to catch")

    code, escaped = exit_code_of_main_block("probe_shut.py", raiser=raiser, argv=argv)
    assert escaped is None, escaped
    assert code == 2, code


# ------------------------------------------------------------- the checker, shown red
#
# Rule 3 of wave 8: a census proves it can fail. `sentinel_violations` is a pure function,
# so the mutations are halts rather than tools — each one a shape MEASURED in this tree on
# 2026-09-04, before the contract was one shape.

GOOD_GATE = ('AUTHOR_WALK_HALT {"tool": "author_walk", "outcome": '
             '"HALTED \u2014 a gate fired", "gate": "PROBE", "error": "_Gate", '
             '"message": "[PROBE] a gate fired", "evidence": {"measured": 1}}')


def test_the_sentinel_checker_accepts_the_contract_shape():
    assert sentinel_violations("AUTHOR_WALK", GOOD_GATE, "gate", 2) == []


@pytest.mark.parametrize("label,stem,stdout,kind,code,expect", [
    ("the code collapsed to 1, which is what six tools did for an ArmatureError",
     "RIG_BAKE", GOOD_GATE.replace("AUTHOR_WALK", "RIG_BAKE"), "gate", 1, "exit code 1"),
    ("no sentinel at all",
     "RIG_BAKE", "", "gate", 2, "0 `RIG_BAKE_HALT <json>` line(s)"),
    ("rig_parts' bare `ERROR {\"gate\": \"n/a\"}`",
     "RIG_PARTS", 'ERROR {"gate": "n/a"}', "crash", 1, "0 `RIG_PARTS_HALT <json>`"),
    ("rig_character's RIG_CHARACTER_HALT_RECORD_NOT_WRITTEN token",
     "RIG_CHARACTER", 'RIG_CHARACTER_HALT_RECORD_NOT_WRITTEN {"gate": null}', "crash", 1,
     "0 `RIG_CHARACTER_HALT <json>`"),
    ("the five tools whose halt line carried no `gate` key",
     "LIFT_SOLVE",
     'LIFT_SOLVE_HALT {"tool": "lift_solve", "outcome": "HALTED \u2014 a gate fired", '
     '"error": "_Gate", "message": "x", "evidence": {"measured": 1}}', "gate", 2, "keys"),
    ("a refusal wearing the gate outcome",
     "AUTHOR_WALK", GOOD_GATE, "refusal", 2, "outcome"),
    ("two sentinel lines, so a reader cannot tell which halt is the halt",
     "AUTHOR_WALK", GOOD_GATE + "\n" + GOOD_GATE, "gate", 2, "2 `AUTHOR_WALK_HALT"),
    ("a fired gate whose evidence went missing",
     "AUTHOR_WALK", GOOD_GATE.replace('{"measured": 1}', "null"), "gate", 2, "evidence"),
])
def test_the_sentinel_checker_names_each_shape_that_was_measured_here(
        label, stem, stdout, kind, code, expect):
    bad = sentinel_violations(stem, stdout, kind, code)
    assert bad, f"{label}: the checker saw nothing wrong"
    assert any(expect in b for b in bad), (label, bad)


# ============================================================================ wave-22 merge
#
# WAVE-22 MERGE (coordinator, 2026-09-05). Instruments' F-897a3329 made the 21 Blender-side
# handlers' halt lines strict JSON — `_halt_keysafe` writes a non-finite float as its `repr`
# and the sentinel is dumped with `allow_nan=False` — and its census
# (`tests/test_instruments_amend_w22.py::test_a_non_finite_operand_leaves_the_halt_line_strict_json`)
# runs over OWNED, which is those 21; `stage_render.py` is instruments-measure's, the 22nd
# copy of the same handler, and was posted to the inbox. The coordinator applied the same
# two-line change there at the merge, and this is the test that rides it: the one tool the
# census above does not drive, driven the same way.


def _strict_json(payload):
    """`json.loads` with `parse_constant` armed — what every parser but CPython's does."""
    def refuse(token):
        raise ValueError("not JSON: bare constant " + token)

    return json.loads(payload, parse_constant=refuse)


def test_stage_render_writes_a_non_finite_operand_as_strict_json(tmp_path, capsys):
    """RED on `41124a9`: the line carried the bare token `NaN`, which `json.loads` accepts
    and `parse_constant=<raise>` (JS `JSON.parse`, Go `encoding/json`, serde) rejects."""
    from armature_core.errors import GateFailure

    class _NaNGate(GateFailure):
        gate = "NAN_PROBE"

    def raiser():
        raise _NaNGate("a measurement that is not a number", {
            "clause": "measurement_not_finite",
            "floor": 0.00017320508075688773,
            "max_displacement": float("nan"),
            "span": float("inf"),
            "low": float("-inf"),
            "nested": [{"deep": float("nan")}],
        })

    code, escaped = exit_code_of_main_block(
        "stage_render.py", raiser=raiser,
        argv=["blender", "-b", "-P", "stage_render.py", "--", "--glb=nope.glb",
              "--out=" + str(tmp_path / "out")])
    assert escaped is None, escaped
    assert code == 2, code
    lines = [l for l in capsys.readouterr().out.splitlines()
             if l.startswith("STAGE_RENDER_HALT ")]
    assert len(lines) == 1, lines
    rec = _strict_json(lines[0][len("STAGE_RENDER_HALT "):])
    ev = rec["evidence"]
    assert ev["max_displacement"] == "nan", ev
    assert ev["span"] == "inf" and ev["low"] == "-inf", ev
    assert ev["nested"][0]["deep"] == "nan", ev
    assert ev["floor"] == 0.00017320508075688773, ev


# ===========================================================================
# WAVE 23, F-2f1b18c2 — THE SECOND POPULATION: the CPython instruments
# ===========================================================================
#
# Everything above is parametrized over `WITH_MAIN`, which is `blender_tools()` — the 22
# tools that run under Blender. The 42 CPython instruments were in no equivalent census,
# and that population contains the tools whose artifacts are UPLOADED. Measured on
# `e8263a3` as real subprocesses on `tools/pack_pose_pack.py`: `--frames=<missing dir>`
# exited 1 with a bare `FileNotFoundError` traceback; the ALPHA-LAW refusal exited 1 with
# an empty stdout; the `--fps=0` refusal, whose own message says the delay is "written into
# the animated image the run UPLOADS", exited 1 with an empty stdout. No halt line on any
# of them, and the evidence dict — carrying the clause — reached no printed line. Exit 1 is
# this repo's contract code for a CRASH, so a runner branching on 2 as "a gate decided"
# read a deliberate alpha-law refusal on the uploaded pose pack as an environment fault.
#
# Wave 22 closed the mechanism for eight of them (SEAM 1's `armature_core.parts.
# run_tool_main`) and `tests/test_instruments_measure_amend_w18.py` asserts exit 2 and the
# clause for `pack_pose_pack` specifically — its `proc.returncode != 0` is gone, replaced
# by `== 2` in `test_the_pack_refusal_reaches_the_operator_and_records_what_it_cannot_say`.
# What is added here is the CENSUS: the same three properties this file holds for the
# Blender side, over every CPython tool that carries a handler, so the next one cannot lose
# its handler quietly.
#
# THE DERIVATION IS NOT `<STEM>_HALT`. The prefix is not the module stem for 20 of the 25 —
# `build_animate_payload.py` prints `BUILD_ANIMATE_HALT`, `gate_saved_graph.py` prints
# `SAVED_ADMISSION_HALT` — and the entry is not always `main`
# (`composite_reference.py` is `run_tool_main(_cli, ...)`, and a driver that substitutes
# `main` runs the real `_cli` and measures the wrong thing). `blender_stub.halt_handler`
# reads both off the block; see its docstring.
#
# THE CONTRACT, and where it differs from the Blender one above. The exit codes are the
# same three (2 for a fired gate, 2 for a bare refusal, 1 for a crash) and the sentinel is
# still exactly one `<PREFIX>_HALT <json object>` line. The KEY SET is not: the eight tools
# on `run_tool_main` print the full six, and the 17 that still carry a local handler print
# three (`error`, `message`, `evidence`). So the floor is those three and the ceiling is the
# six — a handler may not invent a seventh key, and the six-key members are additionally
# held to the whole Blender contract by `sentinel_violations`, which is how a member that
# adopts the one handler gets the stronger check the day it does.

CPYTHON_WITH_HANDLER = [f for f in cpython_tools() if halt_handler(f)]


#: WAVE-25 CI FIX-UP (coordinator, 2026-09-06). `armature_index.py` (a wave-25 adopter of the one handler) imports the sibling
#: working copy `record_index` at module level — on the rig through PYTHONPATH, on ubuntu-latest not at all —
#: so every census below that RUNS its `__main__` read `ModuleNotFoundError` there (8 reds on the first CI run of
#: the wave-25 merge). The suite's standing idiom for that sibling is `tests/test_record_index_binding.py`'s
#: `importorskip` with a reason naming it; this table gives the census the same reason for the same member.
#: Keyed on the resolved shape (the module the tool imports), not on the tool's name alone.
SIBLING_REPO_IMPORTS = {"armature_index.py": "record_index"}


def _sibling_repo_absent(filename):
    """The skip reason when `filename` imports a sibling working copy this interpreter cannot see, else None."""
    import importlib.util
    module = SIBLING_REPO_IMPORTS.get(filename)
    if module is None or importlib.util.find_spec(module) is not None:
        return None
    return (f"{filename} imports `{module}`, a sibling working copy that is not a dependency of this venv "
            f"(PYTHONPATH=E:/AI/record-index on the rig; absent here) — the same skip "
            f"`tests/test_record_index_binding.py` records for the same reason")

#: DERIVED 2026-09-05 by `[f for f in cpython_tools() if halt_handler(f)]`. Equality, so a
#: CPython tool that loses its handler — or a new one that never gets one — fails HERE,
#: naming itself, rather than falling silently out of the three properties below.
RECORDED_CPYTHON_WITH_HANDLER = [
    "analyze_p3.py", "armature_index.py", "build_animate_payload.py",
    "build_assembly_payload.py", "build_camera_i2v_payload.py",
    "build_cascade_payload.py", "build_i2v_payload.py", "build_lora_arm_payload.py",
    "build_payload.py", "build_r2v_payload.py", "build_t2v_payload.py", "canon_gate.py",
    "compare_runs.py", "composite_reference.py", "encode_control.py",
    "extract_clip_frames.py", "fetch_run.py", "fetch_t2v_run.py", "fit_reference.py",
    "gate_b_frames.py", "gate_saved_graph.py", "invert_frames.py", "lift_clip.py",
    "make_ab_clip.py", "make_cast_sheet.py", "make_crop_strip.py", "make_e08_sheet.py",
    "make_e13_sheet.py", "make_gate0_sheet.py", "make_hole_survey.py",
    "make_identity_sheet.py", "make_lift_sheet.py", "make_overlay_sheet.py",
    "make_pick_sheet.py", "make_plate.py", "make_review_clip.py", "make_sheet.py",
    "make_shotset_sheet.py", "make_startframe_sheet.py", "make_thesis_sheet.py",
    "make_zoom_sheet.py", "measure_arm.py", "measure_cascade_clip.py",
    "measure_clip.py", "measure_floor.py", "measure_lift.py", "measure_smoothness.py",
    "measure_tracking.py", "pack_pose_pack.py", "project_pose_keypoints.py",
    "render_pose_sticks.py", "resample_motion.py", "rig_sheet_compose.py",
    "sheet_compose.py",
]

#: THE PENDING TABLE, dated, in `halt_contract_pending`'s shape rather than a skip flag:
#: the CPython tools with no halt handler at all. Each ended in a bare `main()`,
#: `sys.exit(main())` or `raise SystemExit(main())`, so a typed refusal reached the operator
#: as a stdlib traceback at exit 1 and the clause reached nothing.
#:
#: **IT IS EMPTY. MEASURED 2026-09-05 on the wave-25 instruments-measure branch** — 29
#: members on `580af47`, 0 here. The category was keyed on the objective property and not on
#: a list, which is what let it empty itself: all 29 were one domain's files and all 29 adopt
#: `armature_core.parts.run_tool_main` in the wave-25 amend (F-68f3fb4b), so the population
#: with a handler moves 25 -> 54 and every one of the 149 raises those files carry (124 with
#: an evidence dict) now reaches the operator as exit 2 with a `<PREFIX>_HALT` line rather
#: than as exit 1 with a traceback. Six of them keep a non-int return value and adopt the
#: handler through a `_cli` wrapper, the shape `composite_reference` took in wave 22:
#: `extract_clip_frames`, `make_cast_sheet`, `make_e13_sheet`, `make_shotset_sheet`,
#: `measure_cascade_clip`, `measure_floor`.
#:
#: An empty table is not a retired one: it stays here, and the assertion below stays an
#: equality, so a NEW tool that arrives without a handler fails here naming itself.
#: BRANCH-LOCAL: builders move the adopter set in the same wave; the coordinator re-measures
#: on the merged tree and never sums.
#:
#: Re-derive with the suite interpreter (tests/conftest.py module docstring):
#:     .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'tests');import blender_stub as B;
#:     print([f for f in B.cpython_tools() if not B.halt_handler(f)])"
CPYTHON_HALT_CONTRACT_PENDING = []

#: The three keys every CPython handler prints; the six above are the ceiling.
CPYTHON_SENTINEL_FLOOR = {"error", "message", "evidence"}


def test_the_two_populations_partition_the_tools_directory():
    """Neither census can quietly stop covering a file: every `tools/*.py` is in exactly
    one of them, and the CPython half splits into handler-carrying and pending."""
    every = sorted(f for f in os.listdir(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
        if f.endswith(".py"))
    assert sorted(blender_tools() + cpython_tools()) == every
    assert set(blender_tools()) & set(cpython_tools()) == set()
    assert sorted(CPYTHON_WITH_HANDLER
                  + [f for f in cpython_tools() if not halt_handler(f)]) == cpython_tools()


def test_the_cpython_handler_population_is_the_measured_one():
    assert CPYTHON_WITH_HANDLER == RECORDED_CPYTHON_WITH_HANDLER, {
        "appeared": sorted(set(CPYTHON_WITH_HANDLER) - set(RECORDED_CPYTHON_WITH_HANDLER)),
        "vanished": sorted(set(RECORDED_CPYTHON_WITH_HANDLER) - set(CPYTHON_WITH_HANDLER)),
    }


def test_the_cpython_pending_table_is_the_measured_one_and_may_not_grow():
    """The category, keyed on the objective property, so it empties itself when a handler
    lands — and says so when one is lost."""
    pending = [f for f in cpython_tools() if not halt_handler(f)]
    assert pending == CPYTHON_HALT_CONTRACT_PENDING, {
        "joined the pending table": sorted(set(pending)
                                           - set(CPYTHON_HALT_CONTRACT_PENDING)),
        "left it": sorted(set(CPYTHON_HALT_CONTRACT_PENDING) - set(pending)),
    }
    assert set(pending) & set(RECORDED_CPYTHON_WITH_HANDLER) == set()


def _run_cpython(filename, kind):
    """The tool's own `__main__` block with its ENTRY replaced by a raiser.

    The same instrument the Blender half uses, given the entry name the block actually
    calls — `composite_reference`'s is `_cli`.
    """
    handler = halt_handler(filename)
    return exit_code_of_main_block(filename, raiser=_raiser(kind),
                                   argv=["python", filename],
                                   main_name=handler["entry"])


@pytest.mark.parametrize("kind", sorted(CONTRACT))
@pytest.mark.parametrize("filename", CPYTHON_WITH_HANDLER)
def test_the_cpython_exit_code_is_the_one_the_outcome_earns(filename, kind, capsys):
    """2 for a deliberate refusal, 1 for a crash — the property the uploaded-artifact tools
    did not have, over every CPython tool that claims to have it."""
    reason = _sibling_repo_absent(filename)
    if reason:
        pytest.skip(reason)
    want_code = CONTRACT[kind][0]
    code, escaped = _run_cpython(filename, kind)
    capsys.readouterr()
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler"
    assert code == want_code, f"{filename} ({kind}): exit {code!r}, contract says {want_code}"


@pytest.mark.parametrize("filename", CPYTHON_WITH_HANDLER)
def test_a_cpython_refusal_and_crash_do_not_answer_with_the_same_code(filename, capsys):
    """The divergence itself. Every one of these collapsed to 1 before its handler landed,
    which is the state `code not in (0, None)` cannot see."""
    reason = _sibling_repo_absent(filename)
    if reason:
        pytest.skip(reason)
    refusal, _ = _run_cpython(filename, "refusal")
    crash, _ = _run_cpython(filename, "crash")
    capsys.readouterr()
    assert refusal != crash, (
        f"{filename}: a refusal and an unhandled error both exit {refusal!r}; a caller "
        f"branching on 2 reads a crash as a decision, or a decision as a crash")


@pytest.mark.parametrize("kind", sorted(CONTRACT))
@pytest.mark.parametrize("filename", CPYTHON_WITH_HANDLER)
def test_the_cpython_halt_line_carries_the_gate_and_its_measurement(filename, kind,
                                                                    capsys):
    """The receipt an operator keys on, READ.

    One line, its prefix derived from the block rather than guessed from the stem; a JSON
    object; the three keys every handler prints, no key outside the six the one handler
    prints; the error class named; and, for a fired gate, the measurement that fired it —
    which is the half that "reached nothing" on the uploaded pose pack.
    """
    reason = _sibling_repo_absent(filename)
    if reason:
        pytest.skip(reason)
    handler = halt_handler(filename)
    prefix = handler["prefix"]
    code, escaped = _run_cpython(filename, kind)
    out = capsys.readouterr().out
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler"

    token = f"{prefix}_HALT"
    lines = [l for l in out.splitlines() if l.split(" ", 1)[0] == token]
    assert len(lines) == 1, (
        f"{filename} ({kind}): {len(lines)} `{token} <json>` line(s), want exactly 1; "
        f"lines carrying HALT: {[l for l in out.splitlines() if 'HALT' in l]}")
    rec = json.loads(lines[0][len(token):].strip())
    assert isinstance(rec, dict), (filename, kind, type(rec).__name__)
    assert CPYTHON_SENTINEL_FLOOR <= set(rec), (filename, kind, sorted(rec))
    assert set(rec) <= SENTINEL_KEYS, (
        filename, kind, sorted(set(rec) - SENTINEL_KEYS),
        "a key outside the one handler's six")
    assert rec["error"] == {"gate": "_Gate", "refusal": "ArmatureError",
                            "crash": "ValueError"}[kind], (filename, kind, rec)
    if kind == "gate":
        assert rec["evidence"] == {"measured": 1}, (
            f"{filename}: a fired gate's halt line carries the measurement that fired it; "
            f"got {rec.get('evidence')!r}")
    if len(rec) == len(SENTINEL_KEYS):
        # a member on the ONE handler is held to the whole Blender contract as well
        assert not sentinel_violations(prefix, out, kind, code), \
            sentinel_violations(prefix, out, kind, code)


def test_the_one_handlers_adopters_are_derived_and_carry_the_six_key_record():
    """Which members print the six is READ off the tree, not typed: a tool adopts the one
    handler by importing `run_tool_main`, and that is the same set whose halt line carries
    `tool` / `outcome` / `gate`.

    WAVE 25 (builders, F-af838b99): 8 -> 21. The nine builders, both fetchers, `canon_gate`
    and `gate_saved_graph` each carried a LOCAL three-key handler — thirteen byte-alike
    copies of the job this home does — and a `NaN` in one evidence value put the bare token
    on `SAVED_ADMISSION_HALT`, measured as a real subprocess. They are the same 13 members
    `CPYTHON_WITH_HANDLER` already held (the population does not move; what moves is which
    handler they print through), so they join the six-key half of the contract here and the
    stronger `sentinel_violations` check the branch below applies to it.
    """
    adopters = sorted(f for f in CPYTHON_WITH_HANDLER
                      if "run_tool_main" in read_source(f))
    # WAVE-25 MERGE (coordinator, 2026-09-05): the list below is DERIVED on the merged tree by the expression above — builders
    # (21) and instruments-measure (37) each typed their branch-local reading; the merged tree is
    # read, never summed.
    assert adopters == [
        "analyze_p3.py", "armature_index.py", "build_animate_payload.py",
        "build_assembly_payload.py", "build_camera_i2v_payload.py", "build_cascade_payload.py",
        "build_i2v_payload.py", "build_lora_arm_payload.py", "build_payload.py",
        "build_r2v_payload.py", "build_t2v_payload.py", "canon_gate.py",
        "compare_runs.py", "composite_reference.py", "encode_control.py",
        "extract_clip_frames.py", "fetch_run.py", "fetch_t2v_run.py",
        "fit_reference.py", "gate_saved_graph.py", "invert_frames.py",
        "make_ab_clip.py", "make_cast_sheet.py", "make_crop_strip.py",
        "make_e08_sheet.py", "make_e13_sheet.py", "make_gate0_sheet.py",
        "make_hole_survey.py", "make_identity_sheet.py", "make_lift_sheet.py",
        "make_overlay_sheet.py", "make_pick_sheet.py", "make_plate.py",
        "make_review_clip.py", "make_sheet.py", "make_shotset_sheet.py",
        "make_startframe_sheet.py", "make_thesis_sheet.py", "make_zoom_sheet.py",
        "measure_arm.py", "measure_cascade_clip.py", "measure_clip.py",
        "measure_floor.py", "measure_smoothness.py", "measure_tracking.py",
        "pack_pose_pack.py", "render_pose_sticks.py", "resample_motion.py",
        "rig_sheet_compose.py", "sheet_compose.py",
    ], adopters
    skipped_for_a_sibling_repo = [f for f in adopters if _sibling_repo_absent(f)]
    for filename in adopters:
        if filename in skipped_for_a_sibling_repo:
            continue                       # see SIBLING_REPO_IMPORTS; the reason is recorded there
        import io as _io
        import contextlib as _contextlib

        buf = _io.StringIO()
        with _contextlib.redirect_stdout(buf), _contextlib.redirect_stderr(_io.StringIO()):
            _run_cpython(filename, "gate")
        prefix = halt_handler(filename)["prefix"]
        line = [l for l in buf.getvalue().splitlines()
                if l.split(" ", 1)[0] == f"{prefix}_HALT"]
        assert line, (filename, buf.getvalue()[-300:])
        assert set(json.loads(line[0][len(prefix) + 5:])) == SENTINEL_KEYS, filename


def test_the_cpython_derivation_reads_the_prefix_and_the_entry_off_the_block():
    """The red proof for the DERIVATION, which is where this census could go quietly wrong.

    A `<STEM>_HALT` predicate — correct on the Blender side, where every prefix is the stem
    — reports 20 of these 25 as having no handler; and a driver that assumes the entry is
    `main` runs `composite_reference`'s real `_cli`. Both are asserted here so a later
    simplification of `halt_handler` cannot pass by getting easier.

    **WAVE 25: the same five, out of 54 rather than 25, and the point is sharper for it.**
    The 29 tools that adopted the one handler this wave pass their prefix as a bare constant
    (`run_tool_main(main, "MAKE_PLATE")`), so the literal `MAKE_PLATE_HALT` appears nowhere in
    their source: a `<STEM>_HALT` grep now reports 47 of 54 as handler-less, and the two that
    JOINED the list did so by quoting their own halt token in a docstring, not by printing
    it — the predicate reads a substring, which is the whole point. Seven
    entries are no longer `main` — `composite_reference`'s `_cli` plus the six wave-25
    wrappers — which is the half a substituting driver gets wrong.
    """
    by_stem = [f for f in CPYTHON_WITH_HANDLER
               if f"{f[:-3].upper()}_HALT" in read_source(f)]
    # 5 -> 7 in wave 25, and NEITHER newcomer prints the token: `encode_control` and
    # `measure_tracking` each quote their own `<STEM>_HALT` line inside a DOCSTRING or a
    # comment recording what was measured on `580af47`. That is precisely why the predicate
    # is wrong — it reads a substring of the source, not the handler — and it is recorded
    # here rather than papered over, because a census whose red proof drifts toward the
    # thing it is proving wrong stops proving it.
    assert len(by_stem) == 7, sorted(by_stem)
    assert sorted(by_stem) == ["build_payload.py", "canon_gate.py", "encode_control.py",
                               "fetch_run.py", "lift_clip.py", "measure_lift.py",
                               "measure_tracking.py"], sorted(by_stem)
    assert len(CPYTHON_WITH_HANDLER) - len(by_stem) == 47, len(CPYTHON_WITH_HANDLER)
    # The entry is not always `main`, and it is seven tools now rather than one.
    assert sorted(f for f in CPYTHON_WITH_HANDLER
                  if halt_handler(f)["entry"] != "main") == [
        "composite_reference.py", "extract_clip_frames.py", "make_cast_sheet.py",
        "make_e13_sheet.py", "make_shotset_sheet.py", "measure_cascade_clip.py",
        "measure_floor.py"], sorted(f for f in CPYTHON_WITH_HANDLER
                                    if halt_handler(f)["entry"] != "main")
    assert halt_handler("composite_reference.py") == {"prefix": "COMPOSITE_REFERENCE",
                                                      "entry": "_cli"}
    assert halt_handler("measure_floor.py") == {"prefix": "MEASURE_FLOOR", "entry": "_cli"}
    assert halt_handler("gate_saved_graph.py")["prefix"] == "SAVED_ADMISSION"
    assert halt_handler("build_animate_payload.py")["prefix"] == "BUILD_ANIMATE"
