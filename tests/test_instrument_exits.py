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

The population is derived (`blender_stub.blender_tools`, which walks the tree for
`import bpy`), never typed out, so a new Blender tool joins it the day it lands.
"""

import json

import pytest

from blender_stub import blender_tools, exit_code_of_main_block, main_block, read_source

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
RECORDED_BLENDER_TOOLS = [
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py",
    "preview_walk.py", "probe_glb.py", "probe_subject.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py", "rig_bake.py", "rig_character.py",
    "rig_parts.py", "rig_repair.py", "rig_retopo.py",
]

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


def _block_shape(filename):
    """`(uses_finally, writes_a_halt_record)` for one tool's `__main__` block.

    THE NODE: the `__main__` block's own statements. `writes_a_halt_record` is read off the
    module — `rig_character` writes through `_write_halt(...)`, which puts the `halt.json`
    literal one function away — so the discriminator asserted below is the `finally`, and
    the record write is checked to agree with it.
    """
    import ast

    tree = ast.parse(read_source(filename))
    block = next(n for n in tree.body
                 if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                 and getattr(n.test.left, "id", None) == "__name__")
    uses_finally = any(isinstance(n, ast.Try) and n.finalbody for n in ast.walk(block))
    writes_record = any(
        isinstance(n, ast.Constant) and isinstance(n.value, str) and "halt.json" in n.value
        for n in ast.walk(tree))
    return uses_finally, writes_record


def test_the_halt_record_writers_are_the_ones_the_contract_names():
    """The split this file's own prose used to state of all 21.

    Size and membership before the property: the five are DERIVED off the `finally` in each
    `__main__` block, and the halt-record write is asserted to agree with that derivation,
    so a sixth writer — or one of the five losing its `finally` — fails here rather than
    leaving the docstring describing a tree that no longer looks like it.
    """
    shapes = {f: _block_shape(f) for f in WITH_MAIN}
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
    assert with_finally == sorted(WITH_MAIN), {
        "delivers its sentinel and exit outside a `finally`":
            sorted(set(WITH_MAIN) - set(with_finally))}
    assert len(WITH_MAIN) - len(writes) == 16, (
        "16 tools print their sentinel and exit from the `finally` and write no halt record; "
        "the five that write one are the rig tools the contract names")


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


def test_the_population_is_the_whole_blender_side_of_the_repo():
    """A census that quietly stopped enumerating would report green over anything."""
    tools = blender_tools()
    assert len(tools) == 21, tools
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
    want_code = CONTRACT[kind][0]
    code, escaped = _run(filename, kind, tmp_path)
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    assert code == want_code, f"{filename} ({kind}): exit code {code!r}, contract says {want_code}"


@pytest.mark.parametrize("filename", WITH_MAIN)
def test_a_refusal_and_a_crash_do_not_answer_with_the_same_code(filename, tmp_path):
    """The divergence itself, stated separately from the two absolute codes: a regression
    that collapses every outcome to one number is invisible to a test that only asks for
    non-zero, and the whole point of the 2 is that it is NOT the 1."""
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

    return [("tuple_key", per_view), ("numpy_int_key", per_frame),
            ("circular", circular)]


EVIDENCE_SHAPES = _evidence_shapes()

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
