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
