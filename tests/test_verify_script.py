"""`verify.ps1` is the pre-push gate, so its own failure mode is the expensive one.

Two claims the script makes about itself, both measured false before this file existed:

1. **Every leg records the outcome it actually had.** `Invoke-Leg` read `$LASTEXITCODE`
   after `& $Body`. A PowerShell `CommandNotFoundException` does not set `$LASTEXITCODE`, so
   a leg whose native command is absent left the value from the PREVIOUS leg standing and was
   recorded as `ExitCode 0` = PASS. Replicated on the real function: a body running an
   interpreter that exits 0 followed by a non-existent binary reported `ExitCode 0`; a body
   whose ONLY statement was a non-existent binary also reported `ExitCode 0`. With node
   absent the launcher self-test never ran and its leg passed on twine's zero; with npm
   absent the site leg built nothing and passed on the leg before it. That is this repo's
   headline defect class -- a tool reporting success while doing nothing -- living inside the
   script that exists to prevent it.

2. **The legs are the ones CI runs.** The DESCRIPTION says a green local run and a green CI
   run are the same claim. Two of ci.yml's legs had no local counterpart: the clean-venv
   install-and-run (the leg whose whole point is catching a wheel that does not work) and the
   dependency scan. The commands compared here are read out of ci.yml, not typed in, so the
   two files cannot drift apart quietly.

The harness runs the REAL `Invoke-Leg`, lifted verbatim out of verify.ps1 -- a copy of the
function written here would prove something about the copy.
"""

import os
import re
import shutil
import subprocess
import sys

import pytest

from conftest import REPO

from test_ci_workflows import CI, run_script, step_containing

VERIFY_PATH = os.path.join(REPO, "verify.ps1")
with open(VERIFY_PATH, encoding="utf-8") as _fh:
    VERIFY = _fh.read()

PWSH = shutil.which("pwsh") or shutil.which("powershell")
needs_pwsh = pytest.mark.skipif(PWSH is None, reason="no PowerShell to run verify.ps1's own function with")


def invoke_leg_source():
    """`function Invoke-Leg { ... }` lifted verbatim, by brace depth."""
    start = VERIFY.index("function Invoke-Leg")
    depth, i = 0, VERIFY.index("{", start)
    for j in range(i, len(VERIFY)):
        if VERIFY[j] == "{":
            depth += 1
        elif VERIFY[j] == "}":
            depth -= 1
            if depth == 0:
                return VERIFY[start : j + 1]
    raise AssertionError("Invoke-Leg is unbalanced")


def _run_legs(tmp_path, legs):
    """Drive the real Invoke-Leg over `legs` (name -> body) and read back what it recorded."""
    py = sys.executable.replace("\\", "/")
    body = "\n".join(
        f"Invoke-Leg -Name '{name}' -Body {{ {code} }}" for name, code in legs
    )
    script = (
        "$ErrorActionPreference = 'Continue'\n"
        "$results = [System.Collections.Generic.List[object]]::new()\n"
        f"$PY = '{py}'\n"
        f"{invoke_leg_source()}\n"
        f"{body}\n"
        "foreach ($r in $results) { Write-Output (\"LEG|\" + $r.Leg + \"|\" + $r.ExitCode) }\n"
    )
    path = tmp_path / "leg_harness.ps1"
    path.write_text(script, encoding="utf-8")
    proc = subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-File", str(path)],
        capture_output=True,
        text=True,
    )
    recorded = {}
    for line in proc.stdout.splitlines():
        if line.startswith("LEG|"):
            _, name, code = line.split("|", 2)
            recorded[name] = code.strip()
    assert recorded, f"the harness recorded nothing.\n{proc.stdout}\n{proc.stderr}"
    return recorded


OK = "& $PY -c 'raise SystemExit(0)'"
SEVEN = "& $PY -c 'raise SystemExit(7)'"
ABSENT = "armature-no-such-binary-8481819 --version"


def _is_recorded_failure(code):
    """A leg failed only if it RECORDED a non-zero code.

    An empty field is `$LASTEXITCODE` left null -- the leg's outcome was never established,
    which is the ambiguity this whole file exists to remove, so it does not count as a
    failure here either.
    """
    return code not in ("", "0")


@needs_pwsh
def test_a_leg_whose_command_is_absent_is_recorded_as_a_failure(tmp_path):
    """The measured hole: a green leg standing on the previous leg's exit code."""
    recorded = _run_legs(tmp_path, [("prior-ok", OK), ("absent", ABSENT)])
    assert _is_recorded_failure(recorded["absent"]), (
        "a leg whose binary does not exist was not recorded as a failure; it carried the "
        f"previous leg's exit code: {recorded}"
    )


@needs_pwsh
def test_a_first_leg_whose_command_is_absent_is_recorded_as_a_failure(tmp_path):
    """Nothing ran before it, so the recorded code is whatever the shell had lying around."""
    recorded = _run_legs(tmp_path, [("absent-first", ABSENT)])
    assert _is_recorded_failure(recorded["absent-first"]), (
        f"a leg that never ran anything did not record an outcome at all: {recorded}"
    )


@needs_pwsh
def test_a_command_that_vanishes_MID_leg_is_not_recorded_as_the_previous_command_s_pass(tmp_path):
    """The outcome is per LEG, and a leg is many commands. Leg 3 is the exposed one.

    `$global:LASTEXITCODE = $null` is set once per leg, so `Established` answers only "did
    anything in this whole leg set an exit code". Measured on the real function before the
    fix: a leg whose body ran an interpreter that exits 0 and THEN an absent binary recorded
    ExitCode 0 / PASS / Established True, while a leg whose only statement was the absent
    binary recorded 253 / FAIL / Established False. The two existing fixtures cover the
    across-leg and first-command cases and neither reaches this one.

    Where it bites: after `& $python -m build` every remaining command in leg 3 runs on a
    CONSTRUCTED path (`$cleanPython`, `$cleanArmature`), and those paths being absent IS the
    defect that leg exists to catch — a wheel that installs but creates no console script
    makes `& $cleanArmature check` raise, and the catch then reads pip's zero.
    """
    recorded = _run_legs(tmp_path, [("ok-then-absent", f"{OK}; {ABSENT}")])
    assert _is_recorded_failure(recorded["ok-then-absent"]), (
        "a command that raised mid-leg was recorded as the PREVIOUS command's exit code; "
        f"the leg reports a pass on work that never ran: {recorded}"
    )


@needs_pwsh
def test_a_leg_that_raises_after_a_failing_command_still_reports_a_failure(tmp_path):
    """The other direction: the fix must not turn a recorded non-zero into something else.

    A leg that ran a command exiting 7 and then hit an absent binary is still a failure; what
    it may not be is a PASS. This pins that the mid-leg rule fires in the direction the
    invariant is not bounded and nowhere else.
    """
    recorded = _run_legs(tmp_path, [("seven-then-absent", f"{SEVEN}; {ABSENT}")])
    assert _is_recorded_failure(recorded["seven-then-absent"]), recorded


@needs_pwsh
def test_a_leg_of_several_commands_that_all_run_is_still_a_pass(tmp_path):
    """A gate that cannot pass is not a gate. Three real commands, one leg, one PASS."""
    recorded = _run_legs(tmp_path, [("all-ran", f"{OK}; {OK}; {OK}")])
    assert recorded["all-ran"] == "0", recorded


@needs_pwsh
def test_a_leg_that_runs_and_succeeds_is_still_a_pass(tmp_path):
    """The gate must fire on the absent binary without turning every green leg red."""
    recorded = _run_legs(tmp_path, [("ok", OK), ("seven", SEVEN), ("ok-again", OK)])
    assert recorded["ok"] == "0", recorded
    assert recorded["ok-again"] == "0", recorded
    assert recorded["seven"] == "7", recorded


@needs_pwsh
def test_a_leg_that_throws_before_running_anything_is_a_failure(tmp_path):
    """A body that raises a PowerShell error is not a body that passed."""
    recorded = _run_legs(tmp_path, [("prior-ok", OK), ("throws", "throw 'leg exploded'")])
    assert _is_recorded_failure(recorded["throws"]), recorded


# -- the parity claim ---------------------------------------------------------------------


def test_verify_runs_cis_dependency_scan():
    """Read out of ci.yml so the two cannot drift: the local site leg runs the same scan."""
    scan = run_script(step_containing(CI, "scan site dependencies")).strip()
    assert scan.startswith("npm audit"), f"ci.yml's scan step changed shape: {scan!r}"
    assert scan in VERIFY, (
        f"ci.yml runs {scan!r} and verify.ps1 does not; a green local run is then a weaker "
        "claim than the green CI run its DESCRIPTION equates it to"
    )


def test_verify_runs_the_package_from_a_clean_install_the_way_ci_does():
    """The leg whose whole point is catching a wheel that does not work."""
    clean = run_script(step_containing(CI, "run it from a clean install"))
    assert "-m venv" in clean, f"ci.yml's clean-room leg changed shape:\n{clean}"
    assert "-m venv" in VERIFY, (
        "verify.ps1 never installs the wheel it just built into a clean environment, so a "
        "wheel that cannot run passes locally and fails in CI"
    )
    assert re.search(r"armature[\"'\s]+check", VERIFY), (
        "verify.ps1 builds a wheel but never runs the installed command from it"
    )


def test_verify_describes_the_legs_it_actually_has():
    """The DESCRIPTION enumerates the legs; an enumerated leg that does not exist is a lie."""
    described = re.search(r"\.DESCRIPTION(.*?)\.PARAMETER", VERIFY, re.S)
    assert described, "verify.ps1 lost its DESCRIPTION block"
    text = described.group(1)
    for phrase in ("clean", "audit"):
        assert phrase in text.lower(), (
            f"the DESCRIPTION does not mention the {phrase!r} leg that the script now runs"
        )


# -- the pre-flight ANDONs ----------------------------------------------------------------
#
# Two halts run before any leg does: the missing interpreter, and the missing node/npm that
# legs 3 and 4 shell out to. Both fire correctly today and neither had a fixture -- in the
# script whose whole subject is a leg that reports success while doing nothing. An edit to the
# `$needed` list, or to the `-NoPackage`/`-NoSite` conditions that build it, disarms either one
# with the suite green. The mirror case is asserted too: the comment above the halt claims a
# `-NoSite -NoPackage` run on a box with no npm is still a legitimate partial run, and nothing
# pinned that either -- a halt that fired there would be a gate in the wrong direction.

NODE_BINARIES = ("node", "node.exe", "npm", "npm.cmd", "npm.exe", "npm.bat")


def _path_without_node():
    """PATH with every directory that carries node or npm removed, or None if that is not possible."""
    kept = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry.strip():
            continue
        try:
            names = set(os.listdir(entry))
        except OSError:
            kept.append(entry)
            continue
        if names.intersection(NODE_BINARIES):
            continue
        kept.append(entry)
    stripped = os.pathsep.join(kept)
    if shutil.which("node", path=stripped) or shutil.which("npm", path=stripped):
        return None
    return stripped


STRIPPED_PATH = _path_without_node()
needs_stripped_path = pytest.mark.skipif(
    STRIPPED_PATH is None,
    reason="node/npm could not be removed from PATH here, so the halt cannot be exercised",
)


def _scratch_verify(tmp_path, interpreter=True):
    r"""A copy of the real verify.ps1 with its own $PSScriptRoot, and optionally a dummy venv.

    The script is copied rather than re-implemented: a halt written here would prove something
    about the copy. `Join-Path` on a POSIX host leaves the backslashes in
    `.venv\Scripts\python.exe` alone, so the file the script will actually look for is created
    under both spellings and the fixture runs the same on either platform.
    """
    root = tmp_path / "repo"
    root.mkdir(exist_ok=True)
    shutil.copy2(VERIFY_PATH, root / "verify.ps1")
    if interpreter:
        nested = root / ".venv" / "Scripts"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "python.exe").write_bytes(b"")
        if os.name != "nt":
            (root / r".venv\Scripts\python.exe").write_bytes(b"")
    return root


def _run_verify(root, *args, path=None):
    env = dict(os.environ)
    if path is not None:
        env["PATH"] = path
        env.pop("Path", None)
    return subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-File", str(root / "verify.ps1"), *args],
        capture_output=True,
        text=True,
        # verify.ps1 prints box-drawing rules; decoded with the console's locale codec (cp1252
        # under PowerShell) a byte it cannot map raised inside the reader thread and the
        # CompletedProcess came back with stdout None (measured 2026-09-04, merged wave 6).
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(root),
    )


@needs_pwsh
def test_the_preflight_halts_when_the_interpreter_is_missing(tmp_path):
    """Leg 1 runs `& $python`; with no interpreter the halt must come first, and by name."""
    root = _scratch_verify(tmp_path, interpreter=False)
    got = _run_verify(root)
    assert got.returncode == 2, f"exit {got.returncode}\n{got.stdout}\n{got.stderr}"
    assert "ANDON: no interpreter at" in got.stdout, got.stdout + got.stderr


@needs_pwsh
@needs_stripped_path
def test_the_preflight_halts_when_node_and_npm_are_absent(tmp_path):
    """The mutation is the environment: remove what legs 3 and 4 shell out to.

    Without this halt the run discovers it three legs in — and `Invoke-Leg`'s own history is
    that an absent binary was recorded as the PREVIOUS leg's zero.
    """
    root = _scratch_verify(tmp_path)
    got = _run_verify(root, path=STRIPPED_PATH)
    assert got.returncode == 2, f"exit {got.returncode}\n{got.stdout}\n{got.stderr}"
    assert "ANDON: not on PATH" in got.stdout, got.stdout + got.stderr
    for name in ("node", "npm"):
        assert name in got.stdout, f"the halt did not name {name}:\n{got.stdout}"


@needs_pwsh
@needs_stripped_path
def test_a_deliberate_partial_run_does_not_halt_on_the_tools_it_skipped(tmp_path):
    """The other direction, which the halt's own comment claims and nothing pinned.

    Only the tools the SELECTED legs need are required, so `-NoSite -NoPackage` on a box with
    no npm is a legitimate partial run. A halt here would be a gate firing on an invariant it
    does not bound.
    """
    root = _scratch_verify(tmp_path)
    got = _run_verify(root, "-NoSite", "-NoPackage", path=STRIPPED_PATH)
    assert got.returncode != 2, (
        "a deliberate partial run halted on tools no selected leg shells out to:\n"
        f"{got.stdout}\n{got.stderr}"
    )
    assert "ANDON: not on PATH" not in got.stdout, got.stdout


@needs_pwsh
@needs_stripped_path
def test_the_halt_is_armed_by_the_legs_that_were_selected(tmp_path):
    """`-NoSite` alone still needs node: leg 3 runs the launcher self-test with it.

    This is the clause an edit to `$needed` deletes silently — the site leg is the obvious one,
    and the package leg's dependency on node is the one that goes missing.
    """
    root = _scratch_verify(tmp_path)
    got = _run_verify(root, "-NoSite", path=STRIPPED_PATH)
    assert got.returncode == 2, f"exit {got.returncode}\n{got.stdout}\n{got.stderr}"
    assert "node" in got.stdout, got.stdout
