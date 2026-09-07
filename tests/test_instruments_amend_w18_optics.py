"""Wave-18 instruments amend, part 2 — the optics, the orbit angles, and the flag census.

F-cc1d17aa, and every sibling flag rule 2 makes it answer for. `--ortho-scale` is refused
at `render_turnaround`'s parser (S05) unless `math.isfinite(v) and v > 0.0`, under a
paragraph explaining that a non-finite span "still writes a well-formed, correctly-sized
RGBA PNG that no later check reports on". The two flags declared on the lines above it —
the ones `armature_core.turnaround.projection_plan` describes as what "composes the shot"
on the perspective path — got no clause at all, and `projection_plan` passes them through
as `float(lens_mm)` / `float(sensor_mm)` with no check either.

MEASURED on the repo venv from this worktree, `render_turnaround.solve_radius_for_height`
over a four-point cloud and eight azimuths:

| operand | measured on `6b984dd` |
|---|---|
| `--lens=nan` | RETURNS `radius=0.001` — the camera one millimetre from the subject, eight views, no refusal |
| `--lens=0.0` | bare `ZeroDivisionError` out of `armature_core.framing.project` |
| `--lens=inf` | `RenderTurnaroundGate` at the growth loop's 1.6e60 ceiling |
| `--lens=-50.0` | RETURNS the SAME radius as `+50.0`; a mirrored projection, silently |
| `--sensor=nan` | RETURNS `radius=0.001` |
| `--sensor=0.0` | `RenderTurnaroundGate` at the growth ceiling |
| `--sensor=inf` | RETURNS `radius=0.001` |
| `--sensor=-36.0` | RETURNS the same radius as `+36.0` |

The 0.001-metre case is the dangerous one: the eight views are the reference stack a paid
generation is conditioned on, and nothing downstream measures the lens.

Those eight rows are DATED to `6b984dd` and are not asserted anywhere below. core-solvers
is changing the very functions that produce them in this same wave (seams inbox SEAM 5:
`framing.half_fovs`, its `blender_scene` byte-twin and `projection_plan`'s perspective
branch now refuse a non-finite or non-positive `lens_mm`/`sensor_mm`), so a fixture pinning
them would be green here and red in the tree that ships. The clause words this file asserts
— `lens_mm_not_finite_and_positive`, `sensor_mm_not_finite_and_positive` — are theirs, by
their request in that seam, so one grep of a halt record finds the flag refusal and the
solver refusal under a single string. The two halves are complementary: this one refuses
before a Blender scene exists; theirs is inside the function performing the step.

**A CORRECTION to the finding, in place** (advisor rule 2, never a quiet deletion):
F-cc1d17aa states that "`lens=0.0`, `sensor=0.0` and `lens=inf` each raise a bare
`ZeroDivisionError`". Only `lens=0.0` does. `sensor=0.0` and `lens=inf` reach
`RenderTurnaroundGate` through the growth loop's own ceiling — an accident of a different
search, not a bound — and `sensor=inf` returns 0.001 silently, a THIRD silent case the
finding did not name. The measurements above are this file's, not the finding's.

**Rule 2 this wave — the fix's red proof runs against its SIBLINGS.** Every numeric flag
in both parsers is enumerated below BY DERIVATION from the parser's own AST, never from a
typed list, and each is bounded by name or measured out of scope:

* `render_turnaround` floats: `--lens`, `--sensor` (**bounded**, finite and positive),
  `--elevation`, `--azimuth-start`, `--sweep` (**bounded**, finite — an angle may be zero
  or negative), `--height-frac` (**bounded** in part 1), `--ortho-scale` (refused at the
  parser since S05, by its own older clause).
* `render_start_frame` floats: `--height-frac` (**bounded** in part 1). It has no lens or
  sensor flag — both are module constants there.
* Int flags — `--views`, `--fps`, `--frame`, `--width`, `--height`, `--floor`,
  `--shadow-layer` — are OUT OF SCOPE for this family BY MEASUREMENT, not by assertion:
  argparse refuses `nan`, `inf` and `-inf` for a `type=int` flag with a `SystemExit`
  (`test_argparse_takes_nan_for_a_float_flag_and_refuses_it_for_an_int_one`), so no
  non-finite value can enter through one. `--width`/`--height` are additionally bounded by
  `require_frame_size` (F-34a858f5, F-267361f5) and `--views` by `TA.orbit_azimuths`'
  below-1 refusal. What remains on the others is integral RANGE (`--fps=0`, `--frame=-1`,
  `--floor=7`) — a different family, posted to the wave-18 seams inbox rather than fixed
  under cover of this finding.

Fixtures, the `blender -b -P` argv preamble and the halt-record reader are imported from
`test_instruments_amend_w18` rather than copied.

Every fixture below was run once with its fix reverted and records `reverted-red` in its
own docstring.
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
from blender_stub import read_source                                    # noqa: E402
# ONE copy of the fixtures and the two harness helpers, not a second that can drift.
from test_instruments_amend_w18 import (CLOUD, _fn, _halt_record,       # noqa: E402,F401
                                        _parse, rsf, turn)

TOOLS = blender_stub.TOOLS


# ======================================================== the operands, pinned as measured
#
# DIAGNOSTICS of the defect, not of the fix: what the refusals below now stand in front of,
# and the reverted-red evidence in executable form.

# THE THREE OPERAND DIAGNOSTICS THAT WERE HERE ARE DELETED, and the deletion is the point.
# They asserted `solve_radius_for_height(lens=nan) == 0.001`, `lens=-50` returning the same
# radius as `+50`, and `lens=0.0` raising a bare `ZeroDivisionError` — the base-tree
# behaviour of `armature_core.framing`, which is core-solvers' file and which core-solvers
# is changing in THIS wave (seams inbox SEAM 5: `half_fovs` and its `blender_scene`
# byte-twin now refuse a non-finite or non-positive `lens_mm`/`sensor_mm`, and
# `projection_plan`'s perspective branch does too). A test that pins a defect while a
# sibling domain removes it is a landmine that goes off at the merge, and it would have
# gone off green-in-my-worktree, red-in-the-tree-that-ships. The measurements themselves are
# not lost: the table in this module's docstring carries all eight of them, dated to
# `6b984dd`, which is what evidence of a defect is for. What is tested below is the
# property that survives the merge — the flag never reaches the solver at all.


# ============================================ F-cc1d17aa — `--lens` / `--sensor`, at the parser
#
# Bounded beside the `--ortho-scale` clause, where `projection_plan` already says the two
# of them "compose the shot" on the perspective path. They are a focal length and a sensor
# width, so the predicate the ortho pin already uses — finite and strictly positive — is
# exactly right, and it is spelled through `armature_core.parts.require_finite`, the repo's
# ONE implementation of wave 10's rule 4, rather than as a fourth copy of `math.isfinite`.
#
# The refusal raises `RenderTurnaroundGate` rather than calling `ap.error`. That is
# deliberate and it is wave-18 rule 4: `parse_args` is called from inside `main`'s try, so
# a raised andon reaches the halt contract and prints `RENDER_TURNAROUND_HALT` with the
# gate id, the clause and the operand, where `ap.error`'s `SystemExit(2)` is re-raised
# untouched by the `__main__` block and prints an argparse usage message that no log
# reader can key on. `--ortho-scale`'s older clause still uses `ap.error`; moving it is a
# separate change to a shipped refusal and is posted to the inbox, not smuggled in here.


LENS_CLAUSE = "lens_mm_not_finite_and_positive"
SENSOR_CLAUSE = "sensor_mm_not_finite_and_positive"


@pytest.mark.parametrize("flag,bad,clause", [
    ("--lens", "nan", LENS_CLAUSE), ("--lens", "0", LENS_CLAUSE),
    ("--lens", "inf", LENS_CLAUSE), ("--lens", "-50", LENS_CLAUSE),
    ("--sensor", "nan", SENSOR_CLAUSE), ("--sensor", "0", SENSOR_CLAUSE),
    ("--sensor", "inf", SENSOR_CLAUSE), ("--sensor", "-36", SENSOR_CLAUSE),
])
def test_the_turnaround_refuses_optics_that_cannot_compose_a_shot(turn, flag, bad, clause):
    """RED on the operands the finding named, through the REAL parser. Reverted-red: yes —
    on the base tree every one of these parses and four of them reach a solved radius."""
    with pytest.raises(turn.RenderTurnaroundGate) as exc:
        _parse(turn, "--glb=x.glb", "--out=y", f"{flag}={bad}")
    ev = exc.value.evidence
    assert ev["flag"] == flag, ev
    assert ev["clause"] == clause, ev
    # RE-DERIVED wave 22, F-6381b9ff (branch-local): class id under "gate", the
    # declared id under "sub_gate" — one halt event, one gate id.
    assert ev["gate"] == "TURNAROUND", ev
    assert ev["sub_gate"] == "TURNAROUND_OPTICS", ev
    assert ev["andon"] == "RenderTurnaroundGate", ev
    assert ev["who"] == "render_turnaround", ev
    assert flag in str(exc.value)


def test_the_turnaround_default_optics_parse(turn):
    """The module's own 50 mm / 36 mm must survive its own bound."""
    a = _parse(turn, "--glb=x.glb", "--out=y")
    assert (a.lens, a.sensor) == (turn.LENS_MM, turn.SENSOR_MM)
    a = _parse(turn, "--glb=x.glb", "--out=y", "--lens=85", "--sensor=23.5")
    assert (a.lens, a.sensor) == (85.0, 23.5)


@pytest.mark.parametrize("flag,bad", [
    ("--elevation", "nan"), ("--elevation", "inf"),
    ("--azimuth-start", "nan"), ("--azimuth-start", "-inf"),
    ("--sweep", "nan"), ("--sweep", "inf"),
])
def test_the_orbit_angles_are_bounded_too(turn, flag, bad):
    """SIBLING ENUMERATION (wave-18 rule 2), proven red rather than listed. Measured on
    `6b984dd`: `TA.orbit_azimuths(8, nan, 360)` and `(8, 270, nan)` each return eight NaN
    azimuths with no refusal; `sweep=inf` returns `[nan, inf, inf, ...]`;
    `elevation=nan` drives `solve_radius_for_height` to the same `radius=0.001` a NaN lens
    does, and `elevation=inf` reaches a bare `ValueError` out of a projection helper. An
    angle may legitimately be zero or negative, so the clause is finiteness ONLY."""
    with pytest.raises(turn.RenderTurnaroundGate) as exc:
        _parse(turn, "--glb=x.glb", "--out=y", f"{flag}={bad}")
    ev = exc.value.evidence
    assert ev["flag"] == flag, ev
    assert ev["clause"] == "not_a_finite_angle", ev
    # RE-DERIVED wave 22, F-6381b9ff (branch-local).
    assert ev["gate"] == "TURNAROUND", ev
    assert ev["sub_gate"] == "TURNAROUND_ORBIT", ev


def test_a_negative_or_zero_orbit_angle_is_still_legal(turn):
    """Grade the bound only on what it should move: an elevation of 0 is the tool's own
    default and a negative azimuth start is an ordinary way to name a direction."""
    a = _parse(turn, "--glb=x.glb", "--out=y",
               "--elevation=0", "--azimuth-start=-90", "--sweep=-360")
    assert (a.elevation, a.azimuth_start, a.sweep) == (0.0, -90.0, -360.0)


# ==================================================== the sibling census, by derivation
#
# Rule 2's mechanical half: the list of flags is DERIVED from each parser's own AST, so a
# flag added later cannot quietly join the unbounded set.


def _float_flags(filename):
    """Every `--flag` declared `type=float` in the module's `parse_args`."""
    out = []
    for call in ast.walk(_fn(filename, "parse_args")):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "add_argument"):
            continue
        kw = {k.arg: k.value for k in call.keywords}
        t = kw.get("type")
        if isinstance(t, ast.Name) and t.id == "float":
            out += [a.value for a in call.args
                    if isinstance(a, ast.Constant) and str(a.value).startswith("--")]
    return sorted(out)


def _int_flags(filename):
    """Every `--flag` declared `type=int` in the module's `parse_args`."""
    out = []
    for call in ast.walk(_fn(filename, "parse_args")):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "add_argument"):
            continue
        kw = {k.arg: k.value for k in call.keywords}
        t = kw.get("type")
        if isinstance(t, ast.Name) and t.id == "int":
            out += [a.value for a in call.args
                    if isinstance(a, ast.Constant) and str(a.value).startswith("--")]
    return sorted(out)


def _loop_bindings(scope):
    """`{loop variable: [literal values]}` for every `for` over a literal table in `scope`.

    THE RESOLVED SHAPE, not the spelled one (wave-18 rule 1). `render_turnaround` bounds
    its five flags through two `for _flag, _value in (("--lens", a.lens), ...)` loops, so a
    census that only reads an `ast.Constant` in the first argument position sees a bare
    `ast.Name` there and reports five BOUNDED flags as unbounded — which is the same defect
    the wave-17 auditors found in the family census, where reading only `ast.Name` bases
    made the one dotted-base class invisible to every check that polices the family. This
    resolves the name back to the literals the loop actually binds to it.
    """
    out = {}
    for node in ast.walk(scope):
        if not isinstance(node, ast.For):
            continue
        targets = (node.target.elts if isinstance(node.target, ast.Tuple)
                   else [node.target])
        rows = node.iter.elts if isinstance(node.iter, (ast.Tuple, ast.List)) else []
        for pos, tgt in enumerate(targets):
            if not isinstance(tgt, ast.Name):
                continue
            vals = []
            for row in rows:
                cells = row.elts if isinstance(row, (ast.Tuple, ast.List)) else [row]
                if pos < len(cells) and isinstance(cells[pos], ast.Constant):
                    vals.append(cells[pos].value)
            if vals:
                out.setdefault(tgt.id, []).extend(vals)
    return out


def _bounded_flags(filename):
    """Every `--flag` a bounding helper is actually called on, spelled OR resolved.

    `require_finite` takes the name first; `require_shot_fraction` takes it first too. A
    literal in that position is read directly; an `ast.Name` is resolved through the
    enclosing `for` loop's literal table by `_loop_bindings`.
    """
    tree = ast.parse(read_source(filename))
    bindings = _loop_bindings(tree)
    names = set()
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call) or not call.args:
            continue
        fname = (call.func.attr if isinstance(call.func, ast.Attribute)
                 else getattr(call.func, "id", None))
        if fname not in ("require_finite", "require_shot_fraction"):
            continue
        first = call.args[0]
        if isinstance(first, ast.Constant):
            found = [first.value]
        elif isinstance(first, ast.Name):
            found = bindings.get(first.id, [])
        else:
            found = []
        names.update(v for v in found if str(v).startswith("--"))
    return names


def test_the_flag_census_resolves_a_loop_bound_name():
    """The census's own red proof, on a scratch tree. A census that could not resolve a
    loop-bound name would report `render_turnaround`'s five bounded flags as unbounded —
    and, read the other way round, would let a future flag hide inside a loop."""
    scope = ast.parse(
        'for _f, _v in (("--a", 1), ("--b", 2)):\n'
        '    parts.require_finite(_f, _v, G, {}, positive=True)\n')
    assert _loop_bindings(scope)["_f"] == ["--a", "--b"]
    assert _loop_bindings(ast.parse("for x in y:\n    pass\n")) == {}

def test_every_float_flag_in_both_parsers_is_bounded_by_name():
    """THE SIBLING SWEEP. `--ortho-scale` is the one exemption and it is not an exemption
    from being bounded — it carries its own parser refusal since S05 (asserted below), it
    is simply refused by a different clause. Reverted-red: yes — on the base tree the
    unbounded set is `{--azimuth-start, --elevation, --height-frac, --lens, --sensor,
    --sweep}` in `render_turnaround` and `{--height-frac}` in `render_start_frame`."""
    unbounded = {}
    for filename in ("render_start_frame.py", "render_turnaround.py"):
        gap = set(_float_flags(filename)) - _bounded_flags(filename) - {"--ortho-scale"}
        if gap:
            unbounded[filename] = sorted(gap)
    assert unbounded == {}, unbounded


def test_the_ortho_scale_pin_raises_the_andon_like_every_other_refusal(turn):
    """RE-DERIVED wave 22, F-0befca53 (branch-local). This test read:

        "The exemption above is a refusal, not a hole. It exits through argparse rather
        than through the andon — the inconsistency this file's F-cc1d17aa comment posts
        to the inbox rather than changing under cover of another finding."

    The inbox item was filed, approved and closed. MEASURED on `e8263a3` through
    `blender_stub.exit_code_of_main_block('render_turnaround.py')`: a typed
    `RenderTurnaroundGate` gives exit 2 AND a `RENDER_TURNAROUND_HALT` line carrying the
    gate id, the clause and the operand; `ap.error`'s `SystemExit(2)` gives exit 2 and
    stdout EMPTY. Same code, no record — on the two refusals guarding the number a whole
    roster's shared frame span stands on. Both clauses are typed raises now, and
    `test_the_instruments_domain_holds_no_ap_error_call_site` keeps the population closed.
    """
    for argv in (("--glb=x.glb", "--out=y", "--ortho", "--ortho-scale=nan"),
                 ("--glb=x.glb", "--out=y", "--ortho-scale=4.0")):
        with pytest.raises(turn.RenderTurnaroundGate) as exc:
            _parse(turn, *argv)
        ev = exc.value.evidence
        assert ev["flag"] == "--ortho-scale", ev
        assert ev["gate"] == turn.RenderTurnaroundGate.gate == "TURNAROUND", ev
        assert ev["clause"] in ("ortho_scale_not_finite_positive",
                                "ortho_scale_pinned_without_ortho"), ev


def test_argparse_takes_nan_for_a_float_flag_and_refuses_it_for_an_int_one():
    """WHY THE INT FLAGS ARE OUT OF SCOPE, measured rather than asserted. This is the
    whole reason the family is the float flags: `type=int` cannot carry a non-finite
    value, so `--views`, `--fps`, `--frame`, `--floor`, `--shadow-layer`, `--width` and
    `--height` are outside F-cc1d17aa's and F-f0c261c1's disease. Their integral RANGE is
    a different family (`--fps=0`, `--frame=-1`) and is posted to the seams inbox."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", type=float)
    ap.add_argument("--i", type=int)
    assert math.isnan(ap.parse_args(["--x=nan"]).x)
    assert math.isinf(ap.parse_args(["--x=inf"]).x)
    for token in ("nan", "inf", "-inf"):
        with pytest.raises(SystemExit):
            ap.parse_args([f"--i={token}"])


def test_the_int_flags_are_enumerated_so_the_next_one_cannot_hide():
    """The population, by derivation. If a numeric flag is ADDED to either parser this
    fails until someone decides which family it is in — which is the point of enumerating
    rather than listing."""
    # WAVE 34: `--end-frame` joins with `--set/--frames` multi-frame authoring.
    assert _int_flags("render_start_frame.py") == [
        "--end-frame", "--floor", "--fps", "--frame", "--height", "--shadow-layer",
        "--width"]
    assert _int_flags("render_turnaround.py") == [
        "--fps", "--height", "--views", "--width"]


def test_the_width_and_height_siblings_are_still_bounded_by_the_frame_gate():
    """The two int flags that ARE bounded stay bounded — the wave-12/14 fix this one sits
    beside must not be displaced by it."""
    # WAVE 37: render_start_frame's beauty mode re-bounds 704x2048 through a second
    # require_frame_size call; turnaround stays at one.
    expected = {"render_start_frame.py": 2, "render_turnaround.py": 1}
    for filename, n_expected in expected.items():
        fn = _fn(filename, "main")
        calls = [n for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "require_frame_size"]
        assert len(calls) == n_expected, (filename, [n.lineno for n in calls])


def test_the_lens_refusal_reaches_the_halt_line_intact(turn, capsys):
    """Read back verbatim from this worktree:

        RENDER_TURNAROUND_HALT {"tool": "render_turnaround",
          "outcome": "HALTED — a gate fired", "gate": "TURNAROUND",
          "error": "RenderTurnaroundGate",
          "message": "--lens=0.0 is not a finite positive number, ...",
          "evidence": {"gate": "TURNAROUND", "sub_gate": "TURNAROUND_OPTICS",
                       "andon": "RenderTurnaroundGate",
                       "who": "render_turnaround", "flag": "--lens",
                       "clause": "lens_mm_not_finite_and_positive", "--lens": 0.0}}

    The contrast this closes: on `6b984dd` the same command line printed
    `"outcome": "FAILED — an unhandled error", "error": "ZeroDivisionError",
    "gate": null, "evidence": null` at exit 1, from inside `armature_core.framing.project`,
    with the flag that caused it named nowhere in the record."""
    def raiser():
        _parse(turn, "--glb=x.glb", "--out=y", "--lens=0")

    code, escaped, rec = _halt_record("render_turnaround.py",
                                      "RENDER_TURNAROUND_HALT ", raiser, capsys)
    assert escaped is None, escaped
    assert code == 2, code
    assert rec["outcome"].startswith("HALTED"), rec
    assert rec["error"] == "RenderTurnaroundGate", rec
    assert rec["gate"] == "TURNAROUND", rec
    # RE-DERIVED wave 22, F-6381b9ff (branch-local).
    assert rec["evidence"]["gate"] == "TURNAROUND", rec
    assert rec["evidence"]["sub_gate"] == "TURNAROUND_OPTICS", rec
    assert rec["evidence"]["clause"] == LENS_CLAUSE, rec
    assert rec["evidence"]["flag"] == "--lens", rec


def test_the_optics_bound_survives_python_O(turn):
    """The `-O` leg in one test: every refusal added here is a `raise`, so it fires
    identically under `PYTHONOPTIMIZE=1`. (`ci.yml` runs the whole suite that way too.)"""
    with pytest.raises(turn.RenderTurnaroundGate, match="--sensor=nan") as one:
        _parse(turn, "--glb=x.glb", "--out=y", "--sensor=nan")
    assert one.value.evidence["clause"] == SENSOR_CLAUSE
    with pytest.raises(turn.RenderTurnaroundGate, match="--elevation=inf") as two:
        _parse(turn, "--glb=x.glb", "--out=y", "--elevation=inf")
    assert two.value.evidence["clause"] == "not_a_finite_angle"
