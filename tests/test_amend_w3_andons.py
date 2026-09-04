"""The refusals added in the wave-3 core-solvers amend, run under `-O` and PYTHONOPTIMIZE.

CLAUDE.md: *gates raise; they never `assert`* - an `assert` is deleted by `-O` or
`PYTHONOPTIMIZE=1`, and 87 of facet's andons turned out to be removable by an environment
variable. The assembly and cascade andons already have that probe in their own files
(`test_assembly.py`, `test_cascade.py`); this covers the ones added elsewhere in the same
pass, in a file of its own so it is obvious which change they arrived with:

* `walk.gate_stance_frac_is_modelled` - the gait model represents `stance_frac == 0.5` and
  refuses the values whose flight and double-support phases it cannot describe (F-39789a9e),
  both where the value enters and inside `build_gait`, which is the tool that performs the
  step;
* `lift_solve.gate_round_trip` - the andon split out of `round_trip_report`, with no flag
  to disarm it, and the diagnostic refusing to be armed by keyword (F-95a5029e);
* `clipcompare.frame_fidelity`'s shape refusal - not an andon, but the same class of check
  and the same deletion risk (F-4c233305).

Each probe MUTATES the protected thing and requires the raise. A probe that ran on a happy
input would prove nothing about whether the check can fire.
"""

import json
import os
import subprocess
import sys
import textwrap

import pytest

from conftest import TOOLS

PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])          # the worktree's tools/
    sys.path.insert(0, sys.argv[2])          # the worktree's tests/, for the fixtures
    import numpy as np
    from armature_core import walk
    from armature_core import lift_solve as LS
    from armature_core import clipcompare as CC
    from test_lift_solve import synthetic_rest, observed_from, motion, LIMB_MOTION, DIAGONAL
    from test_walk import LANDMARKS, FACING_Y_SIGN, LEFT_X_SIGN

    asserts_active = False
    try:
        assert False
    except AssertionError:
        asserts_active = True

    def _performer():
        return walk.Performer(LANDMARKS, FACING_Y_SIGN, LEFT_X_SIGN)

    def _solve():
        rest = synthetic_rest()
        obs = observed_from(rest, motion(LIMB_MOTION))
        return rest, obs, LS.solve_frame(rest, obs)

    def stance_frac_constructor():
        walk.GaitParams(stance_frac=0.4)

    def stance_frac_mutated_after_construction():
        p = walk.GaitParams()
        p.stance_frac = 0.6
        walk.build_gait(_performer(), p)

    def round_trip_gate():
        rest, obs, solved = _solve()
        solved["local"]["elbow.L"] = LS.mat_mul(
            LS.axis_angle((0.0, 1.0, 0.0), 1e-3), solved["local"]["elbow.L"])
        LS.gate_round_trip(rest, obs, solved, DIAGONAL)

    def arming_the_diagnostic():
        rest, obs, solved = _solve()
        LS.round_trip_report(rest, obs, solved, DIAGONAL, raise_on_fail=True)

    def frame_fidelity_shape():
        a = np.zeros((4, 100), dtype=np.uint8)
        b = a.copy()
        b[1, 50] = 255
        CC.frame_fidelity(a, b)

    # "WalkError" -> "GaitGate" in wave 10 (F-0d621185): the stance-fraction andon now
    # raises a class that is a `GateFailure` as well as a `WalkError`, so the halt contract
    # records it as a gate firing at exit 2 instead of as an unhandled crash at exit 1. The
    # name is pinned rather than the base, exactly as this file's own comment demands —
    # accepting `WalkError` here would now accept the parent and stop proving which andon
    # pulled.
    CASES = {"stance_frac_constructor": (stance_frac_constructor, "GaitGate"),
             "stance_frac_mutated_after_construction":
                 (stance_frac_mutated_after_construction, "GaitGate"),
             "round_trip_gate": (round_trip_gate, "SolveGate"),
             # WAVE 12 (F-9fab7829): both of these were bare builtins, and the 21-tool
             # halt contract classifies on the `ArmatureError` family — so each was
             # recorded as "FAILED - an unhandled error" at exit 1 where the honest record
             # is "REFUSED" at exit 2. The NAME is pinned rather than the base, as this
             # file's comment above demands.
             "arming_the_diagnostic": (arming_the_diagnostic, "SolveError"),
             "frame_fidelity_shape": (frame_fidelity_shape, "ClipCompareError")}

    # WAVE 16 (F-a64f4f47): the MRO, not the spelling. See the note on the assertion below.
    out = {"optimize_flag": sys.flags.optimize, "asserts_active": asserts_active,
           "raised": {}, "mro": {}}
    for name, (fn, want) in CASES.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
            out["mro"][name] = []
        except BaseException as exc:
            mro = [c.__name__ for c in type(exc).__mro__]
            out["mro"][name] = mro
            out["raised"][name] = "RAISED" if want in mro else "WRONG_ERROR:" + mro[0]
    print("AMEND " + json.dumps(out))
    """
)


def _run(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"amend_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = ([sys.executable] + (["-O"] if flag else [])
           + [str(script), TOOLS, os.path.dirname(os.path.abspath(__file__))])
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    assert proc.returncode == 0, proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("AMEND ")]
    assert line, proc.stdout + proc.stderr
    return json.loads(line[-1][len("AMEND "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_every_refusal_added_in_this_amend_survives_optimization(tmp_path, flag, env_var,
                                                                 label):
    res = _run(tmp_path, flag=flag, env_var=env_var)
    assert set(res["raised"]) == {
        "stance_frac_constructor", "stance_frac_mutated_after_construction",
        "round_trip_gate", "arming_the_diagnostic", "frame_fidelity_shape"}
    for name, outcome in res["raised"].items():
        assert outcome == "RAISED", f"{label}/{name}: {outcome}"
    # WAVE 16, F-a64f4f47. This file's comment at :91-95 names family membership as the
    # reason a bare builtin here was recorded as a crash at exit 1 rather than a refusal at
    # exit 2 — and this file mentioned `ArmatureError` nowhere, so the property it calls
    # load-bearing was asserted for none of its five. The probe now transports the MRO, so
    # a subclass re-class that keeps the contract stays green and a departure from the
    # family goes red.
    for name, mro in res["mro"].items():
        assert "ArmatureError" in mro, (
            f"{label}/{name} raised {mro[0]}, outside the ArmatureError family: the 21-tool "
            f"halt contract records it as 'FAILED - an unhandled error' at exit 1 rather "
            f"than a refusal at exit 2. MRO: {mro}")


def test_the_optimization_actually_took_effect(tmp_path):
    """Otherwise the parametrisation above is three copies of the same run."""
    assert _run(tmp_path, flag=False)["asserts_active"] is True
    assert _run(tmp_path, flag=True)["asserts_active"] is False
    assert _run(tmp_path, env_var=True)["asserts_active"] is False


def test_none_of_the_touched_modules_uses_a_bare_assert():
    """Source-level, because `-O` deletes asserts and this repo has been bitten."""
    for name in ("assembly.py", "walk.py", "lift_solve.py", "glb.py", "channels.py",
                 "clipcompare.py", "binding.py", "startframe.py"):
        path = os.path.join(TOOLS, "armature_core", name)
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                assert not line.strip().startswith("assert "), f"{name}:{i} {line!r}"
