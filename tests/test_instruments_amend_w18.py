"""Wave-18 instruments amend, part 1 — `--height-frac`, bounded where it is read.

F-f0c261c1. The two tools whose renders CONDITION a paid generation take their framing
target as a bare `type=float` flag, and a float flag accepts the tokens `nan`, `inf` and
`-inf` from the command line (measured in the sibling module,
`test_argparse_takes_nan_for_a_float_flag_and_refuses_it_for_an_int_one`). A NaN fails
every comparison in BOTH directions, so it does not fire a bound — it walks past every
bound and lands on the verdict line.

MEASURED on the repo venv from this worktree, four-point cloud:
`framing.solve_camera(..., height_frac=nan, end_x_frac=0.5)` RETURNS `radius=40.0` — the
bisection ceiling — where `0.0`, `-0.5` and `inf` each raise `FramingError`. Everything
after that passes: `require_frame_size` has already ruled on width and height, the render
is a correctly-sized RGBA PNG, and `SF.gate_whole` reads a subject a handful of pixels
wide near the frame centre and returns its strongest verdict, "whole silhouette in frame;
smallest margin 206.1 px", over a figure occupying 0.1011 of the frame. The record then
publishes `height_frac_requested: NaN`. This is the residue of the `require_frame_size`
sweep (F-34a858f5, F-267361f5), which bounded `--width`/`--height` on both renderers and
never reached the framing fraction on either.

`render_turnaround` carries the same flag and gets the same clause. Its own solve happens
to refuse a NaN by growing to 1.6e60 and raising `RenderTurnaroundGate` — an accident of a
different search, not a bound, and green on `0.0` (returns 4.25e16), on `1.5` (returns
1.68) and on `inf` (returns 0.001).

The other half of this wave's instruments amend — F-cc1d17aa's `--lens` / `--sensor`
refusal, the orbit-angle siblings, and the derived census that walks every numeric flag in
both parsers — is in `test_instruments_amend_w18_optics.py`, which imports this module's
fixtures and helpers rather than copying them.

Every fixture below was run once with its fix reverted and records `reverted-red` in its
own docstring. Helpers in this file **raise**; they never `assert` outside a test body
(`test_gate_survives_optimize.py` polices that, and `ci.yml` runs an `-O` leg).
"""

import argparse
import ast
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blender_stub                                                     # noqa: E402
from blender_stub import load_tool, read_source                         # noqa: E402

from armature_core import framing, startframe as SF                     # noqa: E402

TOOLS = blender_stub.TOOLS

#: The four-point cloud every measurement in the module docstring was taken on. A
#: three-point cloud is degenerate under one of the eight azimuths and the fourth point is
#: what keeps the projected height non-zero all the way round.
CLOUD = [(0.0, 0.0, 0.0), (0.2, 0.0, 1.7), (-0.2, 0.1, 0.9), (0.0, -0.2, 1.2)]


@pytest.fixture(scope="module")
def rsf():
    return load_tool("render_start_frame.py")


@pytest.fixture(scope="module")
def turn():
    return load_tool("render_turnaround.py")


def _parse(mod, *args):
    """`parse_args` through the real parser, with the `blender -b -P ... --` preamble."""
    argv = sys.argv
    sys.argv = ["blender", "--"] + list(args)
    try:
        return mod.parse_args()
    finally:
        sys.argv = argv


def _fn(filename, name):
    """One top-level function's AST node, for a census that walks the shipped source."""
    tree = ast.parse(read_source(filename))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise LookupError(f"{filename} has no top-level function {name!r}")


# ======================================================== the operands, pinned as measured
#
# These are DIAGNOSTICS of the defect, not of the fix: they run against
# `armature_core` (another domain's files, untouched here) and they are what the two
# refusals below now stand in front of. They are the reverted-red evidence in executable
# form — each one is exactly what a user got on `6b984dd`.


def test_a_nan_height_frac_returns_a_camera_and_a_passing_gate_whole():
    """F-f0c261c1's operand, at the level below the flag. Nothing here is fixed by this
    wave: `framing.solve_camera` is core-solvers' file. This pins WHAT the bound stands in
    front of — a solve that returns the bisection ceiling and a Gate WHOLE that certifies
    it."""
    sol = framing.solve_camera(CLOUD, CLOUD, 270, 8, 50.0, 36.0, 832, 480,
                               height_frac=float("nan"), end_x_frac=0.5)
    assert sol["radius"] == 40.0, sol
    extent = SF.silhouette_extent(CLOUD, tuple(sol["target"]), float(sol["radius"]),
                                  270, 8, 50.0, 36.0, 832, 480)
    whole = SF.gate_whole(extent, 832, 480, 24)
    assert "whole silhouette in frame" in json.dumps(whole), whole
    assert whole["height_frac"] < 0.2, whole


@pytest.mark.parametrize("hf", [0.0, -0.5, float("inf")])
def test_the_other_out_of_band_height_fracs_do_raise_which_is_why_nan_is_the_finding(hf):
    """The contrast that makes the NaN a finding rather than a style note: every other
    unreachable request raises, and only the one that fails comparisons in both directions
    returns."""
    with pytest.raises(Exception):
        framing.solve_camera(CLOUD, CLOUD, 270, 8, 50.0, 36.0, 832, 480,
                             height_frac=hf, end_x_frac=0.5)


# ================================================ F-f0c261c1 — `--height-frac`, both tools
#
# THE OPERAND: the value `--height-frac` hands to a solver. THE POPULATION: both tools that
# carry the flag. `require_shot_fraction` is ONE implementation with two callers, the shape
# `require_frame_size` already has in this same file — parameterised only in what it says
# about ITSELF (`who`, the caller's gate class, the caller's gate id), never in what it
# checks.


@pytest.mark.parametrize("bad,clause", [
    (float("nan"), "not_a_finite_positive_fraction"),
    (float("inf"), "not_a_finite_positive_fraction"),
    (float("-inf"), "not_a_finite_positive_fraction"),
    (0.0, "not_a_finite_positive_fraction"),
    (-0.5, "not_a_finite_positive_fraction"),
    (1.5, "above_one"),
    (1e9, "above_one"),
])
def test_the_start_frame_refuses_a_height_frac_that_is_not_a_fraction(rsf, bad, clause):
    """RED on the operand the finding named. Reverted-red: yes — on the base tree
    `render_start_frame` has no `require_shot_fraction` at all and `main` passes
    `float(a.height_frac)` straight into `framing.solve_camera`."""
    with pytest.raises(rsf.RenderGate) as exc:
        rsf.require_shot_fraction("--height-frac", bad)
    ev = exc.value.evidence
    assert ev["clause"] == clause, ev
    assert ev["flag"] == "--height-frac"
    assert ev["who"] == "render_start_frame"
    # RE-DERIVED wave 22, F-6381b9ff (branch-local): the class id under "gate", the
    # caller's declared id under "sub_gate".
    assert ev["gate"] == rsf.RenderGate.gate == "STARTFRAME"
    assert ev["sub_gate"] == "STARTFRAME_FRACTION"
    assert ev["andon"] == "RenderGate"
    # The evidence carries the OPERAND, not just its name (wave-16 rule).
    assert repr(bad) in repr(ev["--height-frac"]) or ev["--height-frac"] == bad, ev
    assert "--height-frac" in str(exc.value)


@pytest.mark.parametrize("good", [0.90, 0.831, 1.0, 1e-6])
def test_the_band_edges_and_both_module_defaults_are_accepted(rsf, turn, good):
    """A bound that refuses its own tool's default is not a bound, it is a bug. `1.0` is
    the tightest legal fraction — the subject exactly filling the frame — and it is
    inside, not outside (the `require_finite` zero-is-legal correction of F-2a564189, one
    band over)."""
    assert rsf.require_shot_fraction("--height-frac", good) == float(good)
    assert rsf.require_shot_fraction("--height-frac", rsf.HEIGHT_FRAC) == rsf.HEIGHT_FRAC
    assert rsf.require_shot_fraction(
        "--height-frac", turn.HEIGHT_FRAC, who="render_turnaround",
        gate=turn.RenderTurnaroundGate, gate_id="TURNAROUND_FRACTION") == turn.HEIGHT_FRAC


@pytest.mark.parametrize("bad", [float("nan"), 0.0, -0.5, 1.5, float("inf")])
def test_the_turnaround_gets_the_same_clause_under_its_own_andon(turn, bad):
    """Parameterising the gate must not change what either caller raises. The turnaround's
    own solve happens to refuse a NaN by growing to 1.6e60 and raising at the growth
    ceiling — an accident of a different search, not a bound, and green on `0.0` (returns
    `4.25e16`) and on `1.5` (returns `1.68`) and on `inf` (returns `0.001`)."""
    with pytest.raises(turn.RenderTurnaroundGate) as exc:
        turn.require_shot_fraction("--height-frac", bad, who="render_turnaround",
                                   gate=turn.RenderTurnaroundGate,
                                   gate_id="TURNAROUND_FRACTION")
    ev = exc.value.evidence
    # RE-DERIVED wave 22, F-6381b9ff (branch-local).
    assert ev["gate"] == turn.RenderTurnaroundGate.gate == "TURNAROUND"
    assert ev["sub_gate"] == "TURNAROUND_FRACTION"
    assert ev["andon"] == "RenderTurnaroundGate"
    assert ev["who"] == "render_turnaround"


def test_there_is_one_require_shot_fraction_and_three_callers():
    """One implementation, imported — never a second copy. `armature_core.startframe` is
    where it belongs and is outside this domain's globs, so the lift is FILED, not done,
    exactly as `require_frame_size` is."""
    defs = []
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        defs += [(fn, n.name) for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name == "require_shot_fraction"]
    assert [d[0] for d in defs] == ["render_start_frame.py"], defs

    callers = sorted(
        fn for fn in os.listdir(TOOLS)
        if fn.endswith(".py")
        and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "require_shot_fraction"
                for n in ast.walk(ast.parse(read_source(fn)))))
    # RE-DERIVED wave 22, F-3990e197 (branch-local): `preview_walk` is the THIRD caller.
    # It is the third renderer that assigns `scene.render.resolution_x`, and its
    # `--scale` — declared "fraction of shot resolution" in its own help string — was
    # bounded nowhere: nan raised a bare ValueError, inf a bare OverflowError, and 0,
    # -0.5 and 1e6 raised nothing at all and were assigned.
    assert callers == ["preview_walk.py", "render_start_frame.py",
                       "render_turnaround.py"], callers


@pytest.mark.parametrize("filename", ["render_start_frame.py", "render_turnaround.py"])
def test_the_fraction_bound_runs_above_the_resolution_assignment(filename):
    """THE ORDERING CLAUSE F-34a858f5 earned. A check below the assignment refuses a scene
    that has already been set from the bad number, and — the half that matters here — a
    check below the SOLVE does not exist at all."""
    fn = _fn(filename, "main")
    checks = [n.lineno for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "require_shot_fraction"]
    assert len(checks) == 1, checks
    assigns = [n.lineno for n in ast.walk(fn)
               if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Attribute) and t.attr == "resolution_x"
                       for tgt in n.targets
                       for t in (tgt.elts if isinstance(tgt, ast.Tuple) else [tgt]))]
    assert assigns, f"{filename} no longer assigns scene.render.resolution_x"
    assert checks[0] < min(assigns), (checks, assigns)


@pytest.mark.parametrize("filename", ["render_start_frame.py", "render_turnaround.py"])
def test_no_unbounded_height_frac_survives_anywhere_in_main(filename):
    """THE RESOLVED SHAPE, not the spelled one (wave-18 rule 1). The bound is worth
    nothing if a second reader still takes `a.height_frac` straight off the namespace, so
    `main` may mention the attribute exactly ONCE — inside the bound call — and every
    later read is of the bound's return value. Reverted-red: yes; on the base tree `main`
    reads `a.height_frac` four times in `render_turnaround` and twice in
    `render_start_frame`."""
    fn = _fn(filename, "main")
    reads = [n for n in ast.walk(fn)
             if isinstance(n, ast.Attribute) and n.attr == "height_frac"
             and isinstance(n.value, ast.Name)]
    assert len(reads) == 1, [n.lineno for n in reads]
    bound = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "require_shot_fraction"]
    assert bound, f"{filename}'s main has no require_shot_fraction call"
    # CONTAINMENT, not line equality: the call spans four lines in `render_turnaround`, so
    # a line-number match would fail there for a reason that has nothing to do with the
    # property. The attribute must be a DESCENDANT of the bound call.
    inside = [n for n in ast.walk(bound[0]) if n is reads[0]]
    assert inside, (reads[0].lineno, bound[0].lineno)


# ========================================================= the halt line, READ (rule 4)


def _halt_record(filename, prefix, raiser, capsys):
    """Drive the tool's `__main__` with `main` replaced by a real refusal, and READ the
    record it prints. This is the only way to see what an operator actually gets.

    **A trap measured here, and posted to the wave-18 seams inbox for anyone else driving
    `exit_code_of_main_block` this wave.** `blender_stubbed`'s teardown POPS every
    `armature_core.*` module that was first imported under the stub (blender_stub.py:176)
    — deliberately, so a stub-bound module cannot leak into a later test. So a raiser that
    closes over a module loaded by an EARLIER `load_tool` raises an exception whose
    `GateFailure` is a different class object from the one the freshly re-loaded
    `__main__` block tests `isinstance` against, and a perfectly ordinary andon is
    reported as `"FAILED — an unhandled error"` at exit **1** instead of `"HALTED — a gate
    fired"` at exit **2**. Measured 2026-09-04 both ways: a standalone script that touches
    `armature_core` only through `load_tool` reads `(1, None)` on all four refusals below;
    this module imports `armature_core` at module scope, OUTSIDE any stub, so the package
    is in `blender_stubbed`'s `before` set, is never popped, and there is exactly one
    `GateFailure` — which is also the arrangement a real `blender -b -P` run has, one
    process and one import. That is why the assertions below read exit 2.
    """
    code, escaped = blender_stub.exit_code_of_main_block(filename, raiser=raiser)
    out = capsys.readouterr().out
    line = next((ln for ln in out.splitlines() if ln.startswith(prefix)), None)
    if line is None:
        raise AssertionError(f"no {prefix} line in:\n{out[-2000:]}")
    return code, escaped, json.loads(line[len(prefix):])


def test_the_height_frac_refusal_reaches_the_halt_line_intact(rsf, capsys):
    """Wave-18 rule 4, read back verbatim from this worktree:

        RENDER_START_FRAME_HALT {"tool": "render_start_frame",
          "outcome": "HALTED — a gate fired", "gate": "STARTFRAME",
          "error": "RenderGate", "message": "--height-frac=nan is not a finite positive
          number, so it cannot be compared against. ...",
          "evidence": {"gate": "STARTFRAME", "sub_gate": "STARTFRAME_FRACTION",
                       "andon": "RenderGate",
                       "who": "render_start_frame", "flag": "--height-frac",
                       "clause": "not_a_finite_positive_fraction",
                       "--height-frac": "nan"}}

    ⚠ TWO CLAIMS IN THIS DOCSTRING WERE OVERTURNED IN WAVE 22, and the corrections are
    kept in place with the measurements rather than deleted.

    (1) It read: "`\"gate\"` at the TOP level is the CLASS attribute `STARTFRAME`, while
    `evidence[\"gate\"]` is this refusal's own id — the shape `require_frame_size`
    established, and the reason a reader can tell which of the two STARTFRAME refusals
    fired." F-6381b9ff measured what that costs: ONE halt event printing TWO different
    gate ids, and `STARTFRAME_FRACTION` / `TURNAROUND_FRAME` / `TURNAROUND_FRACTION` /
    `TURNAROUND_OPTICS` / `TURNAROUND_ORBIT` declared by no `GateFailure` subclass at
    all, so a census enumerating gate ids from the family's `gate = "..."` literals
    reported zero sites for any of them. The repo had already closed this family twice
    in the builders domain (`tests/test_amend_w16_builders.py:815-823`, rule at :879-886:
    `ev["gate"] == type(exc).gate`). `evidence["gate"]` is now the class id and the
    refusal's own id is `evidence["sub_gate"]` — one event, one gate id, and a reader
    can still tell the two STARTFRAME refusals apart.

    (2) It read that the bare `NaN` token "is the halt contract's existing `json.dumps`
    behaviour, unchanged by this wave, and it is posted to the inbox rather than altered
    here." F-897a3329 closed it: the halt line is `json.dumps(..., allow_nan=False)` and
    `_halt_keysafe` writes a non-finite float as its `repr` string, so the record is
    strict JSON and the operand is still readable."""
    def raiser():
        rsf.require_shot_fraction("--height-frac", float("nan"))

    code, escaped, rec = _halt_record("render_start_frame.py",
                                      "RENDER_START_FRAME_HALT ", raiser, capsys)
    assert escaped is None, escaped
    assert code == 2, code
    assert rec["outcome"].startswith("HALTED"), rec
    assert rec["error"] == "RenderGate", rec
    # RE-DERIVED wave 22, F-6381b9ff (branch-local).
    assert rec["evidence"]["gate"] == "STARTFRAME", rec
    assert rec["evidence"]["sub_gate"] == "STARTFRAME_FRACTION", rec
    assert rec["evidence"]["clause"] == "not_a_finite_positive_fraction", rec
    assert rec["evidence"]["flag"] == "--height-frac", rec
    assert "--height-frac" in rec["evidence"], rec
    assert "--height-frac" in rec["message"], rec


# ============================================================ the shape of the refusals
#
# Gates raise; they never `assert`, and nothing here may be deleted by `-O`.


@pytest.mark.parametrize("filename", ["render_start_frame.py", "render_turnaround.py"])
def test_no_bound_added_this_wave_is_spelled_as_an_assert(filename):
    """`PYTHONOPTIMIZE=1` deletes every `assert`. A bound that an environment variable can
    delete is not a bound — the 87-gates lesson in CLAUDE.md."""
    tree = ast.parse(read_source(filename))
    for name in ("parse_args", "main", "require_shot_fraction"):
        try:
            fn = _fn(filename, name)
        except LookupError:
            continue
        asserts = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Assert)]
        assert asserts == [], (filename, name, asserts)
    assert isinstance(tree, ast.Module)


def test_the_fraction_bound_survives_python_O(rsf, turn):
    """The `-O` leg in one test: the refusal is a `raise`, so it fires identically under
    `PYTHONOPTIMIZE=1`. (`ci.yml` runs the whole suite that way as well.)"""
    with pytest.raises(rsf.RenderGate, match="--height-frac=nan") as one:
        rsf.require_shot_fraction("--height-frac", float("nan"))
    assert one.value.evidence["clause"] == "not_a_finite_positive_fraction"
    with pytest.raises(turn.RenderTurnaroundGate, match="--height-frac=1.5") as two:
        turn.require_shot_fraction("--height-frac", 1.5, who="render_turnaround",
                                   gate=turn.RenderTurnaroundGate,
                                   gate_id="TURNAROUND_FRACTION")
    assert two.value.evidence["clause"] == "above_one"
