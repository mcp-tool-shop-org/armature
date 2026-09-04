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

from test_ci_workflows import (
    CI,
    _has_a_ceiling,
    _install_tokens,
    clean_room_script,
    npm_clean_room_script,
    run_script,
    step_containing,
)

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


# -- WAVE 8, F-b359d73d: the case verify.ps1's own comment names FIRST --------------------
#
# Both fixtures above place the missing binary as the ENTIRE body of a leg. verify.ps1's
# real legs are nothing like that: :137 builds, twine-checks, installs into a clean venv
# and runs the launcher self-test in ONE body; :217 runs npm ci, npm audit and npm run
# build in another. The shape the comment at verify.ps1:64-71 names first — a body that
# runs a command SUCCESSFULLY and then reaches an absent one — was driven by nothing.
#
# Measured 2026-09-04 with this file's own `_run_legs` and pwsh on this rig:
#   {'prior-ok': '0', 'absent': '253'}   the shape the old fixtures drive — caught
#   {'within': '0'}                      OK + '; ' + ABSENT inside one body — a PASS
#   {'within2': '0'}                     the same with a newline separator — a PASS
#   {'within3': '0'}                     SEVEN + '; ' + OK — a PASS over a failed command
#
# So with node or npm absent, the launcher self-test or the site build never runs, the leg
# records 0, and the script prints that all legs passed: the headline defect class living
# inside the script written to prevent it. `Invoke-Leg` recording per COMMAND rather than
# per LEG is the ci-packaging half of this; these are the fixtures that say so.


@needs_pwsh
@pytest.mark.parametrize("sep", ["; ", "\n"], ids=["semicolon", "newline"])
def test_an_absent_command_after_a_successful_one_still_fails_its_leg(tmp_path, sep):
    """The within-leg case. `$LASTEXITCODE` is left standing at the earlier command's 0
    because a `CommandNotFoundException` never sets it, and the leg reports the outcome of
    the half that ran rather than the half that did not."""
    recorded = _run_legs(tmp_path, [("within", OK + sep + ABSENT)])
    assert _is_recorded_failure(recorded["within"]), (
        "a leg whose SECOND command does not exist recorded the FIRST command's success: "
        f"{recorded}. verify.ps1:137 and :217 are multi-command bodies, so this is the "
        f"shape that actually ships"
    )


@needs_pwsh
def test_a_failed_command_is_not_erased_by_a_successful_one_after_it(tmp_path):
    """The other direction of the same defect, and the one no absent binary is needed for:
    a command that exits 7 followed by one that exits 0. The leg's recorded code is the
    LAST command's, so a real failure inside a body is overwritten by whatever tidying
    runs after it."""
    recorded = _run_legs(tmp_path, [("within3", SEVEN + "; " + OK)])
    assert _is_recorded_failure(recorded["within3"]), (
        f"a command that exited 7 was erased by the command after it: {recorded}"
    )


@needs_pwsh
def test_a_multi_command_leg_that_wholly_succeeds_is_still_a_pass(tmp_path):
    """The direction the fix must not break: three commands, all zero, one PASS. Without
    this, `Invoke-Leg` could satisfy the two tests above by failing every leg."""
    recorded = _run_legs(tmp_path, [("all-ok", "; ".join([OK, OK, OK]))])
    assert recorded["all-ok"] == "0", recorded


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
    # Read from wherever the leg lives: it moved into `.github/actions/clean-room` so
    # the release gate could run the SAME leg on the artifact it publishes.
    clean = clean_room_script()
    assert "-m venv" in clean, f"the clean-room leg changed shape:\n{clean}"
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
    # BOTH, and the second half is the one that was never written. Leg 3 gained the npm clean
    # room in wave 10 -- `npm pack --silent` and `npm install --prefix` -- and `$needed` did
    # not move with it, so this guard stayed green while `-NoSite` on a box with node and no
    # npm ran both pytest legs and the whole build / twine / clean-venv / wheel-probe sequence
    # before dying at `npm pack`. The requirement is derived rather than typed by
    # `test_the_preflight_requires_every_tool_the_selected_legs_shell_out_to` below; this
    # test is the end-to-end half, run against the real script with node and npm off PATH.
    for name in ("node", "npm"):
        assert name in got.stdout, f"the halt did not name {name}:\n{got.stdout}"


# -- the local site leg scans before it installs, the way CI does (F-a495cc98) -------------
#
# `npm ci` runs every lifecycle script in the resolved tree, so a scan that follows it
# reports a compromised dependency that has already had a shell — on the rig, in this leg.
# The DESCRIPTION equates a green local run with a green CI run, so the ORDER is part of the
# claim, not only the presence of the command.


def _site_leg():
    """The body of the `site build` leg, sliced out of the real script, comments dropped.

    The steps explain each other, so both commands appear in the prose above them; an
    ordering read off a comment would be an ordering read off an explanation.
    """
    head = VERIFY.index("Invoke-Leg -Name 'site build")
    start = VERIFY.index("-Body {", head)  # the leg NAME names both commands too
    kept = [line for line in VERIFY[start:].splitlines()
            if not line.lstrip().startswith("#")]
    return chr(10).join(kept)


def test_the_local_site_leg_scans_before_it_installs():
    leg = _site_leg()
    install, scan = leg.find("npm ci"), leg.find("npm audit")
    assert scan != -1, "the site leg no longer scans site/'s lockfile at all"
    assert scan < install, (
        f"verify.ps1 runs `npm ci` at offset {install} and `npm audit` at {scan} inside the "
        "site leg; the scan reports after every lifecycle script in the tree has run")


def test_the_local_scan_is_the_lockfile_only_form_ci_uses():
    """Read out of ci.yml so the two cannot drift: same command, same order, same claim."""
    scan = run_script(step_containing(CI, "scan site dependencies")).strip()
    assert "--package-lock-only" in scan, f"ci.yml's scan step changed shape: {scan!r}"
    assert scan in VERIFY, (
        f"ci.yml runs {scan!r} and verify.ps1 does not; a green local run is then a weaker "
        "claim than the green CI run its DESCRIPTION equates it to")


# -- the parity claim, at the level of the TOOL (wave 10, F-da6b0457) ----------------------
#
# The DESCRIPTION says "the legs are the same ones `.github/workflows/ci.yml` runs, in the
# same order and with the same meaning, so a green local run and a green CI run are the same
# claim". Leg 3 called `& $python -m build` and `& $python -m twine check` against whatever
# the repo venv happened to hold; the CI leg it mirrors installs `build>=1.5,<2` and
# `twine>=7,<8` first. Measured 2026-09-04: the repo venv holds build 1.5.0 and twine 7.0.0 —
# inside CI's window, so the divergence was latent rather than live, which is exactly the
# state in which nobody notices it.
#
# Neither existing check could see it. `toolchain_tokens()` walked `job_scripts()` over
# `workflow_files()` only, and the mirror test below asserted `-m venv` and `armature check`
# appear in both texts — the SHAPE of the leg, not the toolchain that produces the artifact
# it inspects. A `pip install -U build` past 2.0 on the rig would make the local leg select
# sdist contents differently from CI, and a green local run would then assert something CI
# never ran.
#
# THE NODE THIS CENSUS KEYS ON: the install tokens of the clean-room ACTION's own script,
# read at run time. Nothing is typed here, so raising either constraint in the action moves
# this requirement with it rather than leaving the local leg pinned to yesterday's window.


def clean_room_install_tokens():
    """The package specifiers `.github/actions/clean-room` installs before it builds."""
    return sorted(set(_install_tokens(clean_room_script())))


def _missing_from(text, tokens):
    return [token for token in tokens if token not in text]


def test_the_clean_room_pins_a_toolchain_this_check_can_compare():
    """The census's own premise: an empty token list would make the comparison vacuous."""
    tokens = clean_room_install_tokens()
    assert tokens, (
        "the clean-room action installs nothing this check can read; the comparison below "
        "would pass on any verify.ps1 at all")
    unbounded = [t for t in tokens if not _has_a_ceiling(t)]
    assert unbounded == [], (
        f"the clean-room action installs {unbounded} without an upper bound, so pinning "
        "verify.ps1 to it would pin it to nothing")


def test_verify_builds_the_artifact_with_the_toolchain_the_clean_room_action_pins():
    """The DESCRIPTION equates a green local run to a green CI run; the tools must match.

    What this looks like if wrong: `pip install -U build` on the rig takes the local leg past
    the constraint CI holds, sdist file selection changes underneath it, and the local run
    asserts a packaging outcome CI has never produced — while claiming to be the same claim.
    """
    missing = _missing_from(VERIFY, clean_room_install_tokens())
    assert missing == [], (
        f"verify.ps1 builds the package without installing {missing}, which "
        f".github/actions/clean-room/action.yml installs before it builds; the DESCRIPTION "
        "equates the two runs and the toolchain that PRODUCES the artifact is what differs")


def test_the_toolchain_parity_check_goes_red_on_the_leg_this_repo_had():
    """The mutation: leg 3 as it stood, building against whatever the venv held."""
    before = "& $python -m build\n& $python -m twine check (Join-Path $repo 'dist\\*')"
    assert _missing_from(before, clean_room_install_tokens()) == clean_room_install_tokens(), (
        "the pre-fix leg reads as installing the pinned toolchain; the check cannot fail")
    # And the near-miss that matters: the right tools at the WRONG constraint.
    forked = "& $python -m pip install 'build' 'twine'"
    assert _missing_from(forked, clean_room_install_tokens()), (
        "an unconstrained local install reads as matching CI's pinned one")


# -- the npm clean room, locally too (wave 10, F-3729edd4 family carry) --------------------
#
# The family is "places that run the npm package's launcher as coverage": ci.yml's `launcher`
# job, release.yml's `npm` job, and verify.ps1's leg 3. All three ran
# `node bin/armature.mjs --node-selftest` out of the CHECKOUT, which consults neither `bin`,
# nor `files`, nor the tarball — measured green on a `bin` map pointed at a typo, with no
# `armature` command existing anywhere after the install. ci.yml and release.yml now call
# `.github/actions/npm-clean-room`; this is the same leg in the script whose DESCRIPTION says
# a green local run and a green CI run are the same claim.


def _runs_the_npm_clean_room(text):
    """True when a text packs the npm package, installs the tarball into a scratch prefix,
    and invokes the shim npm created there.

    The bash action and the PowerShell script cannot share tokens verbatim, so what is
    compared is the three MECHANISMS, and the action is held to the same predicate below so
    a change of mechanism there fails here rather than drifting.
    """
    return (
        "npm pack" in text
        and re.search(r"npm\s+(install|i)\b[^\n]*--prefix", text) is not None
        and "node_modules/.bin" in text
        and "--node-selftest" in text
    )


def test_verify_runs_the_npm_package_from_a_clean_install_the_way_ci_does():
    """The third member of the family, in the file that claims parity with the other two."""
    assert _runs_the_npm_clean_room(npm_clean_room_script()), (
        "the CI leg this is mirrored from no longer matches the mechanisms compared here:\n"
        + npm_clean_room_script())
    assert _runs_the_npm_clean_room(VERIFY.replace("\\", "/")), (
        "verify.ps1 runs the launcher out of the checkout and never installs the package it "
        "would publish; a `bin` map that resolves to nothing passes locally")


def test_the_local_npm_clean_room_check_goes_red_on_the_leg_this_script_had():
    """The mutation: leg 3's npm step exactly as it stood, and two near-misses."""
    before = "Push-Location (Join-Path $repo 'npm')\ntry { node bin/armature.mjs --node-selftest } finally { Pop-Location }"
    assert not _runs_the_npm_clean_room(before), (
        "the checkout self-test reads as a clean install")
    assert not _runs_the_npm_clean_room("npm pack --silent\nnode bin/armature.mjs --node-selftest"), (
        "packing and then running the CHECKOUT reads as a clean install")
    assert not _runs_the_npm_clean_room(
        "npm pack --silent\nnpm install --prefix $npmroom $tarball.FullName"), (
        "installing without invoking the shim reads as a clean install; that is the exact "
        "state where npm reported `added 1 package` and made no bin directory")


# -- the pre-flight requires what the SELECTED legs shell out to (F-329a630d) --------------
#
# The halt's own comment says the legs that shell out to node and npm "halt up front rather
# than discovering it mid-run", and that "Only the tools the SELECTED legs need are required".
# Both clauses were held by a hand-written pair of lines and by one assertion that named
# `node`. Leg 3 gained the npm clean room in wave 10 -- `npm pack --silent` at verify.ps1:275
# and `npm install --prefix $npmroom` at :287 -- and the requirement list did not move with
# it. Measured by lifting the construction verbatim into pwsh and evaluating all four flag
# combinations: `(no flags)` -> node, npm; `-NoSite` -> node ONLY; `-NoPackage` -> node, npm;
# `-NoSite -NoPackage` -> (none).
#
# THE NODE THIS CENSUS KEYS ON: the external commands a leg's BODY invokes, read out of
# PowerShell's own parser -- every `CommandAst` under the leg's script block whose command
# name does not resolve to a cmdlet, function or alias. Not the two names `node` and `npm`:
# a leg that starts shelling out to a third tool has to move the requirement with it, and a
# census that knows the answer in advance cannot notice that. `& $python` resolves to no
# command name at all (the interpreter is a variable, and it has its own halt above).
#
# MEASURED AND NOT CHANGED (2026-09-04): the requirement is a SUPERSET under `-NoPackage`.
# Leg 4 invokes `npm` three times and `node` never, and line 150 asks for both. Requiring
# `node` for a leg that never names it is the mirror defect, but npm IS node -- no box has
# one without the other -- so the over-requirement cannot halt a run that would have worked,
# and this census asserts the direction that can: every tool a selected leg needs is
# required. The other direction is bounded by the two clauses below it.

import json


def _pwsh_json(script):
    """Run a PowerShell script and read the JSON on its stdout."""
    got = subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert got.returncode == 0, f"pwsh exited {got.returncode}\n{got.stdout}\n{got.stderr}"
    return json.loads(got.stdout)


_LEG_AST_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$path = '%s'
$ast = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$null)
$legs = $ast.FindAll({
    param($n)
    $n -is [System.Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'Invoke-Leg'
}, $true)
$out = New-Object System.Collections.ArrayList
foreach ($leg in $legs) {
    $elems = $leg.CommandElements
    $name = $null
    for ($i = 0; $i -lt $elems.Count; $i++) {
        if ($elems[$i] -is [System.Management.Automation.Language.CommandParameterAst] -and
            $elems[$i].ParameterName -eq 'Name' -and ($i + 1) -lt $elems.Count) {
            $name = $elems[$i + 1].Value
        }
    }
    $body = $elems | Where-Object {
        $_ -is [System.Management.Automation.Language.ScriptBlockExpressionAst]
    } | Select-Object -First 1
    $cmds = New-Object System.Collections.ArrayList
    if ($body) {
        foreach ($c in $body.FindAll({
            param($n) $n -is [System.Management.Automation.Language.CommandAst]
        }, $true)) {
            $cn = $c.GetCommandName()
            if (-not $cn) { continue }
            # An external is anything PowerShell does not provide ITSELF. Keyed that way and
            # not on `-eq 'Application'`: `Get-Command npm` resolves to `npm.ps1` on this rig
            # (CommandType ExternalScript), so an Application-only test read the site leg as
            # shelling out to nothing at all. A name that resolves to nothing is external too
            # -- that is precisely the state the halt exists for.
            $resolved = Get-Command $cn -ErrorAction SilentlyContinue
            $internal = @('Cmdlet', 'Function', 'Alias', 'Filter', 'Configuration')
            if ($resolved -and $internal -contains [string]$resolved.CommandType) { continue }
            [void]$cmds.Add($cn)
        }
    }
    $guard = $null
    $inElse = $false
    $node = $leg.Parent
    while ($null -ne $node) {
        if ($node -is [System.Management.Automation.Language.IfStatementAst]) {
            if ($node.Clauses[0].Item1.Extent.Text -match '\$(No\w+)') { $guard = $Matches[1] }
            if ($node.ElseClause -and
                $node.ElseClause.Extent.StartOffset -le $leg.Extent.StartOffset -and
                $node.ElseClause.Extent.EndOffset -ge $leg.Extent.EndOffset) { $inElse = $true }
            break
        }
        $node = $node.Parent
    }
    [void]$out.Add([pscustomobject]@{
        name = $name
        commands = @($cmds | Sort-Object -Unique)
        guard = $guard
        skipped_by_the_flag = $inElse
    })
}
ConvertTo-Json -InputObject @($out) -Depth 6
"""


def leg_externals(script_path=None):
    """(leg name -> {commands, guard, skipped_by_the_flag}) read out of PowerShell's parser."""
    script_path = VERIFY_PATH if script_path is None else script_path
    rows = _pwsh_json(_LEG_AST_SCRIPT % str(script_path).replace("'", "''"))
    return {row["name"]: row for row in rows}


def preflight_source(text=None):
    """The `$needed` construction, lifted verbatim between its two anchors.

    Lifted rather than re-typed for the same reason `Invoke-Leg` is: a requirement list
    written here would prove something about the copy. The end anchor is `$absent`, the
    statement that CONSUMES the list.
    """
    text = VERIFY if text is None else text
    start = text.index("$needed = @()")
    end = text.index("$absent = @(", start)
    return text[start:end]


def preflight_requirements(no_site, no_package, text=None):
    """What the real pre-flight would demand under one flag combination."""
    body = preflight_source(text).replace("'", "''")
    script = (
        f"$NoSite = ${str(bool(no_site)).lower()}; "
        f"$NoPackage = ${str(bool(no_package)).lower()}\n"
        f"{preflight_source(text)}\n"
        "ConvertTo-Json -InputObject @(@($needed) | Sort-Object -Unique) -Depth 3\n"
    )
    assert body  # the lift found something
    return set(_pwsh_json(script))


def _selected_legs(no_site, no_package, script_path=None):
    """The legs that RUN under one flag combination, by the guard each sits under."""
    flags = {"NoSite": bool(no_site), "NoPackage": bool(no_package)}
    out = {}
    for name, row in leg_externals(script_path).items():
        guard = row["guard"]
        if guard is None:
            out[name] = row
            continue
        held = flags.get(guard)
        assert held is not None, f"leg {name!r} is guarded by an unknown switch ${guard}"
        if row["skipped_by_the_flag"] != held:
            out[name] = row
    return out


COMBINATIONS = [(False, False), (True, False), (False, True), (True, True)]


@needs_pwsh
def test_the_leg_census_reads_the_real_script_and_finds_the_shell_outs():
    """Size and membership before the property: four legs, and the two that shell out.

    An empty command list on leg 3 or leg 4 would make every assertion below vacuous, which
    is the shape a census fails in without going red.
    """
    legs = leg_externals()
    assert len(legs) == 4, sorted(legs)
    package = [row for name, row in legs.items() if row["guard"] == "NoPackage"]
    site = [row for name, row in legs.items() if row["guard"] == "NoSite"]
    assert len(package) == 1 and len(site) == 1, sorted(
        (name, row["guard"]) for name, row in legs.items())
    assert set(package[0]["commands"]) == {"node", "npm"}, package[0]
    assert set(site[0]["commands"]) == {"npm"}, site[0]
    # The two pytest legs shell out to nothing: `& $python` is a variable, and the missing
    # interpreter has its own halt above this one.
    unguarded = [row for row in legs.values() if row["guard"] is None]
    assert len(unguarded) == 2 and all(row["commands"] == [] for row in unguarded), unguarded


@needs_pwsh
@pytest.mark.parametrize("no_site,no_package", COMBINATIONS)
def test_the_preflight_requires_every_tool_the_selected_legs_shell_out_to(no_site, no_package):
    """The invariant the halt claims, over all four flag combinations.

    The direction that costs: a tool a selected leg needs and the pre-flight does not require
    is a run that pays for both pytest legs and the whole build sequence before dying at the
    command, recorded honestly as `FAIL (the leg established no outcome)` -- after paying the
    cost the up-front halt exists to avoid, on a run the operator has to read backwards.
    """
    needed = preflight_requirements(no_site, no_package)
    selected = _selected_legs(no_site, no_package)
    for name, row in sorted(selected.items()):
        missing = sorted(set(row["commands"]) - needed)
        assert missing == [], (
            f"leg {name!r} runs under (-NoSite={no_site}, -NoPackage={no_package}) and shells "
            f"out to {missing}, which the pre-flight does not require: {sorted(needed)}"
        )


@needs_pwsh
def test_the_preflight_requires_nothing_no_leg_anywhere_shells_out_to():
    """The other direction, bounded: a required tool must be one SOME leg actually invokes.

    `$needed += 'git'` would otherwise halt a legitimate run on a tool this script never runs.
    """
    everything = set()
    for row in leg_externals().values():
        everything.update(row["commands"])
    for no_site, no_package in COMBINATIONS:
        stray = sorted(preflight_requirements(no_site, no_package) - everything)
        assert stray == [], (
            f"(-NoSite={no_site}, -NoPackage={no_package}) requires {stray}; no leg in this "
            f"script invokes them, and the legs invoke {sorted(everything)}"
        )


@needs_pwsh
def test_the_requirement_census_goes_red_on_a_third_tool_under_a_name_it_was_not_told(tmp_path):
    """The hidden spelling: a leg that starts shelling out to something not called node or npm.

    A census keyed on the two names in the list can only ever re-confirm the list. This drives
    the real derivation over a scratch copy of verify.ps1 whose package leg gains a `git`
    invocation, and asserts BOTH halves: the walk sees the new command, and the comparison
    goes red on it. Written with `git` because it is a real external the parser will classify
    as an Application on this rig and no line of verify.ps1 names.
    """
    mutated = VERIFY.replace(
        "            & $python -m pip install --quiet 'build>=1.5,<2' 'twine>=7,<8'",
        "            git rev-parse HEAD\n"
        "            & $python -m pip install --quiet 'build>=1.5,<2' 'twine>=7,<8'",
        1,
    )
    assert mutated != VERIFY, "the package leg no longer has the line this mutation hangs on"
    scratch = tmp_path / "verify.ps1"
    scratch.write_text(mutated, encoding="utf-8")

    legs = leg_externals(str(scratch))
    package = [row for row in legs.values() if row["guard"] == "NoPackage"]
    assert len(package) == 1 and "git" in package[0]["commands"], package

    selected = _selected_legs(False, False, str(scratch))
    needed = preflight_requirements(False, False, mutated)
    missing = sorted(
        {c for row in selected.values() for c in row["commands"]} - needed)
    assert missing == ["git"], (
        f"the derivation did not go red on a leg's new shell-out; missing={missing}, "
        f"needed={sorted(needed)}"
    )


# -- the interpreter the local claim is made on (F-857aa2fa) ------------------------------
#
# The DESCRIPTION's equivalence sentence -- "The legs are the same ones
# `.github/workflows/ci.yml` runs, in the same order and with the same meaning, so a green
# local run and a green CI run are the same claim" -- is true of the LEGS and false on the
# interpreter axis, and that axis moved in wave 10. verify.ps1 runs every Python leg on
# `$repo\.venv\Scripts\python.exe`; measured on this rig 2026-09-04 that interpreter is
# Python 3.14.5. ci.yml's `python-tests` job runs a two-entry matrix of ["3.11", "3.13"] and
# release.yml's release gate runs "3.13" -- so the interpreter the local claim is made on is
# one no CI job runs, and is above the top classifier pyproject declares. The rest of the
# equivalence is machine-held (the build/twine specifiers are read out of the clean-room
# action by this file), which is what makes the remaining gap worth naming.
#
# Two halves, because the finding has two: the prose must not sell an equivalence it does not
# have, and the RUN must state which interpreter it was made on. The second is the one a
# reader can act on -- a summary that names the interpreter turns "CI will be green" into a
# checkable claim.

DESCRIPTION = VERIFY[VERIFY.index(".DESCRIPTION"):VERIFY.index(".PARAMETER")]


def _paragraphs(text):
    """Blank-line-separated paragraphs, whitespace collapsed."""
    out, current = [], []
    for line in text.splitlines():
        if line.strip():
            current.append(line.strip())
        elif current:
            out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return out


def test_the_equivalence_claim_names_the_axis_it_does_not_hold_on():
    """The paragraph that sells the equivalence must name the interpreter.

    Keyed on the paragraph rather than on a sentence: the qualification is a clause about a
    different subject and reads as its own sentence, and a check that demanded both words in
    one sentence would be a check on punctuation.
    """
    claiming = [p for p in _paragraphs(DESCRIPTION) if "same claim" in p]
    assert len(claiming) == 1, [p[:80] for p in _paragraphs(DESCRIPTION)]
    assert "interpreter" in claiming[0].lower(), (
        "the DESCRIPTION equates a green local run with a green CI run and says nothing "
        "about the interpreter, which is the axis on which they are NOT the same claim: "
        f"{claiming[0]}"
    )


@needs_pwsh
def test_the_summary_states_which_interpreter_the_claim_was_made_on(tmp_path):
    """The run itself must say which interpreter it ran, honestly when it cannot read one.

    Driven on the scratch fixture, whose `.venv\\Scripts\\python.exe` is an empty file: the
    legs fail, which is the point -- the summary block prints for a failing run too, and the
    interpreter line has to be there for the operator reading a red run backwards. A version
    that cannot be read is reported as unreadable and never guessed at.
    """
    root = _scratch_verify(tmp_path)
    got = _run_verify(root, "-NoSite", "-NoPackage")
    out = got.stdout or ""
    assert "interpreter:" in out, (
        f"the summary does not say which interpreter the legs ran on:\n{out}"
    )
    line = [ln for ln in out.splitlines() if "interpreter:" in ln][0]
    assert ".venv" in line, f"the interpreter line does not name the interpreter: {line!r}"
    assert "unreadable" in line, (
        "the fixture's interpreter is an empty file, so no version can be read from it; the "
        f"line must say so rather than print something: {line!r}"
    )


@needs_pwsh
def test_the_interpreter_line_reports_a_version_it_can_read(tmp_path):
    """The other direction: given a real interpreter, the line carries its version.

    A line that always said "unreadable" would be a check that cannot fail, and this is the
    half the operator actually reads.
    """
    root = _scratch_verify(tmp_path, interpreter=False)
    if os.name == "nt":
        # A COPIED venv `python.exe` is not a working interpreter -- it resolves its prefix
        # from its own location and finds no `pyvenv.cfg`, so it reports nothing and this
        # test would have asserted "unreadable" in both directions. `venv --without-pip` is
        # a real interpreter at the path the script looks for, built from this one, and
        # needs no index.
        made = subprocess.run(
            [sys.executable, "-m", "venv", "--without-pip", str(root / ".venv")],
            capture_output=True, text=True,
        )
        assert made.returncode == 0, made.stdout + made.stderr
    else:
        # `Join-Path` leaves the backslashes alone on a POSIX host, so the script looks for a
        # file whose NAME contains them (the same shape `_scratch_verify` writes).
        os.symlink(sys.executable, root / r".venv\Scripts\python.exe")
    got = _run_verify(root, "-NoSite", "-NoPackage")
    out = got.stdout or ""
    line = [ln for ln in out.splitlines() if "interpreter:" in ln]
    assert line, f"no interpreter line at all:\n{out}"
    expected = "%d.%d.%d" % sys.version_info[:3]
    assert expected in line[0], (
        f"the summary reports no readable version for a real interpreter: {line[0]!r}"
    )
