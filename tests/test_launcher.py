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

import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import REPO

LAUNCHER = os.path.join(REPO, "npm", "bin", "armature.mjs")
NODE = shutil.which("node")
requires_node = pytest.mark.skipif(
    NODE is None,
    reason="the launcher is node; none on PATH — install node or put it on PATH")

def _launch(args, **env):
    return subprocess.run(
        [NODE, LAUNCHER, *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        timeout=30,
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


# -- the diagnosis after the probe succeeded ----------------------------------------------
#
# `locate()` returns `{ exe, pre }` on success and `{ exe: null, pre: null, sawInterpreter }`
# on failure -- only the FAILURE shape carries `sawInterpreter`. The spawn-error handler hands
# the SUCCESS object to `fail()`, which branches on `found.sawInterpreter`: absent reads as
# false, so a user whose interpreter `locate()` had just probed successfully -- it imported
# `armature_core` -- is told "No Python interpreter was found on PATH." and to
# `pip install armature-studio`. Reinstalling the toolkit changes nothing, because the toolkit
# was never the problem: the branch fires when the SPAWN fails after a successful probe
# (EACCES/EPERM from an AV or policy hook, the interpreter renamed or unmounted between the
# two calls, EMFILE). The file's own comments name this exact misdiagnosis twice as the thing
# they exist to prevent.

HEAD_MARKER = "const argv = process.argv.slice(2);"


def launcher_head():
    """Everything above the module's first side effect, lifted verbatim.

    Nothing below the marker can be imported without running the launcher, so the functions
    under test are lifted rather than re-declared -- a copy written here would prove something
    about the copy.
    """
    with open(LAUNCHER, encoding="utf-8") as fh:
        source = fh.read()
    assert HEAD_MARKER in source, "the launcher no longer has the head this test lifts"
    return source[: source.index(HEAD_MARKER)]


def _drive_head(tmp_path, driver, **env):
    """Run `driver` with the launcher's real head in scope."""
    module = tmp_path / "head.mjs"
    module.write_text(launcher_head() + "\n" + driver, encoding="utf-8")
    return subprocess.run(
        [NODE, str(module)],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        timeout=30,
    )


def _real_success_shape_env(tmp_path):
    """Pin the launcher at an interpreter that CAN import the toolkit, so `locate()` succeeds.

    The shape under test is `locate()`'s own return value, never one fabricated here: the
    whole defect is that the success shape and the failure shape differ in a key `fail()`
    reads.
    """
    return {
        "ARMATURE_PYTHON": sys.executable,
        "PYTHONPATH": os.path.join(REPO, "tools"),
    }


@requires_node
def test_locate_reports_the_same_facts_on_success_as_on_failure(tmp_path):
    """`sawInterpreter` is absent from the success shape, and `fail()` reads it as false."""
    got = _drive_head(
        tmp_path,
        'const found = locate();\n'
        'process.stdout.write(JSON.stringify({ exe: found.exe, saw: found.sawInterpreter }));\n',
        **_real_success_shape_env(tmp_path),
    )
    assert got.returncode == 0, f"stdout: {got.stdout}\nstderr: {got.stderr}"
    payload = json.loads(got.stdout)
    assert payload["exe"], (
        "the pinned interpreter could not import armature_core, so this test never reached "
        f"locate()'s success path: {got.stdout} {got.stderr}"
    )
    assert payload.get("saw") is True, (
        "locate() found an interpreter and returned an object that does not say so; any "
        f"caller reading `sawInterpreter` off it concludes PATH was empty: {payload}"
    )


@requires_node
def test_a_spawn_that_fails_after_a_successful_probe_does_not_blame_path(tmp_path):
    """The measured misdiagnosis: exit 127 and `pip install armature-studio`, on a good install.

    Driven with the object `locate()` actually returns on success, and the kind of error
    `child.on("error")` actually carries.
    """
    got = _drive_head(
        tmp_path,
        'const found = locate();\n'
        'if (!found.exe) { process.stderr.write("probe did not succeed"); process.exit(3); }\n'
        'const err = new Error("spawn EACCES"); err.code = "EACCES";\n'
        'fail(found, err);\n',
        **_real_success_shape_env(tmp_path),
    )
    assert got.returncode == 127, f"stdout: {got.stdout}\nstderr: {got.stderr}"
    # Both of `fail()`'s "we never got an interpreter" phrasings are wrong here — the pinned
    # one and the unpinned one. locate() ran this interpreter and imported the toolkit with it.
    for lie in ("No Python interpreter was found on PATH", "which this shell could not run"):
        assert lie not in got.stderr, (
            "the launcher told a user whose interpreter it had just probed successfully — it "
            f"imported armature_core with it — that {lie!r}:\n{got.stderr}"
        )
    assert "EACCES" in got.stderr, (
        f"the failure does not carry the error that actually stopped the run:\n{got.stderr}"
    )
    assert sys.executable.replace("\\", "/") in got.stderr.replace("\\", "/"), (
        f"the failure does not name the interpreter it could not start:\n{got.stderr}"
    )


@requires_node
def test_the_not_found_message_still_fires_when_nothing_was_found(tmp_path):
    """The other half: a real empty-PATH failure must keep saying so.

    A fix that made every failure say "could not start" would trade one misdiagnosis for
    another.
    """
    got = _drive_head(
        tmp_path,
        'const found = locate();\n'
        'fail(found);\n',
        ARMATURE_PYTHON=str(tmp_path / "no-such-interpreter"),
    )
    assert got.returncode == 127, got.stdout + got.stderr
    assert "could not run" in got.stderr or "not importable" in got.stderr, got.stderr
    assert str(tmp_path / "no-such-interpreter") in got.stderr, got.stderr


# -- a killed child is not a crash (F-46fe7537) -------------------------------------------
#
# `child.on("exit", (code, signal) => process.exit(signal ? 1 : code ?? 0))` collapsed every
# signal death of the Python child into exit 1. The comment on the line above states the
# contract it keeps -- "inherit the child's exit code, so a gate that raises in Python still
# fails the shell that called this launcher" -- and that half worked. What was lost is the
# distinction the rest of this repo spends effort on: 2 is a refusal, 1 is a crash
# (`tests/test_packaging.py` pins that convention on the CPU tools), and a child killed by
# SIGKILL -- the realistic case being the OOM killer during a frame or GLB pass -- arrived at
# the caller as 1, byte-identical to an ordinary Python traceback. A wrapper that retries a
# crash and halts on a kill cannot tell them apart, so an OOM-killed run is retried into the
# same wall and nothing on the caller's side names the signal.
#
# 128 + N is the shell convention, and it is what a caller already knows how to read.

SIGNAL_MAP_MARKER = "function exitCodeFor("


@requires_node
def test_a_signal_death_is_reported_as_the_shell_convention_and_not_as_a_crash(tmp_path):
    """The mapping, driven through the launcher's own function rather than a copy of it."""
    got = _drive_head(
        tmp_path,
        'const out = {};\n'
        'for (const s of ["SIGKILL", "SIGTERM", "SIGINT"]) out[s] = exitCodeFor(null, s);\n'
        'out.clean = exitCodeFor(0, null);\n'
        'out.refusal = exitCodeFor(2, null);\n'
        'out.crash = exitCodeFor(1, null);\n'
        'out.no_code_at_all = exitCodeFor(null, null);\n'
        'process.stdout.write(JSON.stringify(out));\n',
    )
    assert got.returncode == 0, f"stdout: {got.stdout}\nstderr: {got.stderr}"
    payload = json.loads(got.stdout)
    assert payload["SIGKILL"] == 137, payload
    assert payload["SIGTERM"] == 143, payload
    assert payload["SIGINT"] == 130, payload
    # The half that must NOT move: the launcher's stated contract is that the child's exit
    # code reaches the caller, and 2-is-a-refusal is what the CPU tools' convention rests on.
    assert payload["clean"] == 0 and payload["refusal"] == 2 and payload["crash"] == 1, payload
    assert payload["no_code_at_all"] == 0, payload
    assert payload["SIGKILL"] != payload["crash"], (
        "a killed child and a crashed one still arrive at the caller as the same number"
    )


@requires_node
def test_the_selftest_pins_the_signal_mapping_without_a_child():
    """`npm test` is the launcher's only coverage in CI, and it has no Python to kill.

    So the mapping is asserted there, the same way the ARMATURE_PYTHON pin is: a run that
    honours the convention and a run that collapses every signal into 1 are indistinguishable
    from outside unless something asserts the mapping itself.
    """
    got = _launch(["--node-selftest"])
    assert got.returncode == 0, got.stderr
    assert "SIGKILL=137" in got.stdout, (
        f"the selftest does not report the signal mapping it checks:\n{got.stdout}"
    )


@requires_node
def test_the_selftest_goes_red_on_the_collapsing_handler_this_launcher_had(tmp_path):
    """The mutation: the pre-fix expression, run through the real selftest.

    A selftest that passed on both shapes would be a check that cannot fail, and this is the
    only coverage the launcher has in CI.
    """
    with open(LAUNCHER, encoding="utf-8") as fh:
        source = fh.read()
    assert SIGNAL_MAP_MARKER in source, "the launcher no longer has the function this mutates"
    mutated = source.replace(
        "  const number = signal ? constants.signals[signal] : undefined;\n"
        "  if (signal) return number ? 128 + number : 1;\n",
        "  if (signal) return 1;\n",
        1,
    )
    assert mutated != source, "the mutation did not apply; the mapping was rewritten"
    scratch = tmp_path / "collapsed.mjs"
    scratch.write_text(mutated, encoding="utf-8")
    got = subprocess.run(
        [NODE, str(scratch), "--node-selftest"],
        cwd=REPO, capture_output=True, text=True, env={**os.environ},
        timeout=30,
    )
    assert got.returncode != 0, (
        "the selftest passed on a launcher that collapses every signal death into exit 1:\n"
        f"{got.stdout}\n{got.stderr}"
    )


needs_posix_signals = pytest.mark.skipif(
    os.name == "nt",
    reason="a process cannot terminate itself BY SIGNAL on Windows, so no child of this "
           "launcher can be made to die by one here; CI runs this leg on ubuntu",
)


@requires_node
@needs_posix_signals
def test_a_child_killed_by_a_signal_reaches_the_caller_as_that_signal(tmp_path):
    """End to end, through the real handler: a child that dies by SIGKILL, and the caller.

    The mapping test above drives the function; this drives the `child.on("exit")` path the
    function exists for, on a real spawned interpreter. The fake toolkit is what makes the
    probe succeed and gives `-m armature_core.cli` something to run.
    """
    fake = tmp_path / "site"
    package = fake / "armature_core"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli.py").write_text(
        "import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n", encoding="utf-8"
    )
    got = _launch(
        ["anything"],
        ARMATURE_PYTHON=sys.executable,
        PYTHONPATH=str(fake),
    )
    assert got.returncode == 137, (
        "a child killed by SIGKILL did not reach the caller as 128+9; a wrapper cannot tell "
        f"it from an ordinary traceback: exit {got.returncode}\n{got.stdout}\n{got.stderr}"
    )
    assert "SIGKILL" in got.stderr, (
        f"nothing on the caller's side names the signal that ended the run:\n{got.stderr}"
    )
