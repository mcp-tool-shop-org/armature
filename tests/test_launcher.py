"""ARMATURE_PYTHON is a pin, and a pin the launcher walks past is worse than no pin.

`candidates()` returned `[...pinned, "python", "py", "python3"]` and `locate()` kept walking
that list until something imported the toolkit. Measured on this rig: with the pin on an
interpreter that could NOT import `armature_core` and a different one first on PATH that
could, `armature --version` printed `armature-studio 0.3.0` and exited 0 -- byte-identical to
the control run with the variable unset. The launcher's own failure message tells the user to
point at a specific interpreter with this variable, so the user gets the OTHER install's
version and behaviour with nothing on screen saying so: the repo's "success while doing
something else" class, in the one file whose entire job is choosing an interpreter.

`npm test` (`--node-selftest`) is the launcher's only coverage in CI and needs no Python, so
the substitution is asserted there too and driven from here.
"""

import os
import shutil
import subprocess

import pytest

from conftest import REPO

LAUNCHER = os.path.join(REPO, "npm", "bin", "armature.mjs")
NODE = shutil.which("node")
requires_node = pytest.mark.skipif(NODE is None, reason="the launcher is Node; none on PATH")


def _launch(args, **env):
    return subprocess.run(
        [NODE, LAUNCHER, *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**os.environ, **env},
    )


@requires_node
def test_the_pin_substitutes_for_the_search_order_rather_than_joining_it(tmp_path):
    """ARMATURE_PYTHON is a pin, and a pin the code walks past is worse than no pin.

    `candidates()` returned `[...pinned, "python", "py", "python3"]` and `locate()` kept
    walking until something imported the toolkit. Measured on this rig: with the pin on an
    interpreter that could not import `armature_core` and a different one first on PATH that
    could, `armature --version` printed the version and exited 0 -- byte-identical to the run
    with the variable unset. The launcher's own failure message tells the user to pin an
    interpreter with this variable, so honouring it is the difference between a pin and a
    decoration: the user gets the OTHER install's version and behaviour, silently.
    """
    pinned = str(tmp_path / "no-such-interpreter")
    got = _launch(["--version"], ARMATURE_PYTHON=pinned)
    assert got.returncode == 127, f"stdout: {got.stdout}\nstderr: {got.stderr}"
    assert pinned in got.stderr, (
        "the launcher failed without naming the interpreter it was pinned to, so the user "
        f"cannot tell the pin was even read:\n{got.stderr}"
    )


@requires_node
def test_the_selftest_covers_the_pin():
    """`npm test` is the launcher's only CI coverage; the pin has to be inside it."""
    got = _launch(["--node-selftest"])
    assert got.returncode == 0, got.stderr
    assert "ok" in got.stdout


@requires_node
def test_the_selftest_reports_the_pin_it_was_given(tmp_path):
    pinned = str(tmp_path / "pinned-python")
    got = _launch(["--node-selftest"], ARMATURE_PYTHON=pinned)
    assert got.returncode == 0, got.stderr
    assert pinned in got.stdout, (
        f"the selftest did not report the pin as the candidate list:\n{got.stdout}"
    )
    assert "python3" not in got.stdout, (
        f"the pin was joined to the PATH walk instead of replacing it:\n{got.stdout}"
    )
