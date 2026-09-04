"""Every Blender-side tool's `__main__` handler must exit NON-ZERO when `main` raises.

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

The population is read off the files (`blender_stub.blender_tools`), never typed out, so a
new Blender tool joins it the day it lands — the shape `tests/test_gates.py`'s
`SHARED_GATE_IDS` uses to stop a population growing quietly.
"""

import pytest

from blender_stub import blender_tools, exit_code_of_main_block, main_block

#: EMPTY, re-derived 2026-09-04 (F-7e64c103): `preview_glb.py` now carries the handler,
#: so line 40's exemption assertion no longer holds with the old value. Exact codes and
#: sentinel shape: `tests/test_instruments_amend_w8.py`.
NO_MAIN_BLOCK = ()

WITH_MAIN = [f for f in blender_tools() if main_block(f) is not None]


def test_the_population_is_the_whole_blender_side_of_the_repo():
    """A census that quietly stopped enumerating would report green over anything."""
    tools = blender_tools()
    assert len(tools) >= 21, tools
    assert "render_turnaround.py" in tools and "rig_character.py" in tools
    assert sorted(set(tools) - set(WITH_MAIN)) == sorted(NO_MAIN_BLOCK)


@pytest.mark.parametrize("filename", WITH_MAIN)
def test_a_gate_failure_exits_non_zero(filename, tmp_path):
    """The andon path: a typed gate fires inside `main`."""
    from armature_core.errors import GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    def raiser():
        raise _Gate("a gate fired", {"measured": 1})

    code, escaped = exit_code_of_main_block(
        filename, raiser=raiser,
        argv=["blender", "-b", "-P", filename, "--", "--glb=nope.glb", "--out=" + str(tmp_path / "out")])
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    assert code not in (0, None), f"{filename}: exit code {code!r}"


@pytest.mark.parametrize("filename", WITH_MAIN)
def test_an_ordinary_error_exits_non_zero(filename, tmp_path):
    """The un-typed path. `rig_parts.py:556` records this one biting the file that
    documents it: the handler caught only `GateFailure`, so a plain `ValueError` walked
    out and Blender reported success."""
    def raiser():
        raise ValueError("an ordinary mistake")

    code, escaped = exit_code_of_main_block(
        filename, raiser=raiser,
        argv=["blender", "-b", "-P", filename, "--", "--glb=nope.glb", "--out=" + str(tmp_path / "out")])
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    assert code not in (0, None), f"{filename}: exit code {code!r}"


@pytest.mark.parametrize("filename", WITH_MAIN)
def test_an_unparseable_argv_still_exits_non_zero(filename, tmp_path):
    """F-f5530688's exact shape. `main` fails on a bad flag; the handler then re-parses the
    SAME argv to find out where to write `halt.json`, and fails again. Whatever the handler
    does about that, it may not let the second failure delete the exit code."""
    from armature_core.errors import ArmatureError

    def raiser():
        raise ArmatureError("unknown flag --not-a-flag")

    code, escaped = exit_code_of_main_block(
        filename, raiser=raiser,
        argv=["blender", "-b", "-P", filename, "--", "--not-a-flag=1"])
    assert escaped is None, (
        f"{filename}: {escaped!r} escaped the handler. A second failure inside the `except` "
        f"block leaves the whole `try` statement and `sys.exit` never runs")
    assert code not in (0, None), f"{filename}: exit code {code!r}"


@pytest.mark.parametrize("filename", WITH_MAIN)
def test_a_missing_glb_does_not_delete_the_exit_code(filename, tmp_path):
    """The other half of F-f5530688: `sha256_file(_args['glb'])` inside the `except` block
    raises `FileNotFoundError` on a mistyped path."""
    def raiser():
        raise RuntimeError("something went wrong after the args parsed")

    code, escaped = exit_code_of_main_block(
        filename, raiser=raiser,
        argv=["blender", "-b", "-P", filename, "--",
              "--glb=E:/no/such/file/at/all.glb",
              "--out=" + str(tmp_path / "out")])
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    assert code not in (0, None), f"{filename}: exit code {code!r}"
