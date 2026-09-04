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
    assert "node" in got.stdout, got.stdout


# -------------- the halt names every tool the SELECTED legs shell out to (F-7d109c56) -----
#
# The clause above is narrow on purpose and it is NOT the census. `"node" in got.stdout` is
# satisfied by the clause that is still there and cannot see the one that went missing — and
# the one that went missing is npm, not node. Measured 2026-09-04 by copying the real
# `verify.ps1` into a scratch root and running it under pwsh with this file's own
# `STRIPPED_PATH`: `verify.ps1 -NoSite` exits 2 and prints `ANDON: not on PATH: node`, while
# leg 3 — the leg `-NoSite` KEEPS — runs `npm pack --silent` (verify.ps1:275) and
# `npm install --prefix $npmroom $tarball` (:288) as the npm clean room it mirrors from
# ci.yml. On a box with node and no npm, `verify.ps1 -NoSite` passes the pre-flight and then
# discovers npm mid-leg: exactly the failure the block's own comment says it exists to
# prevent ("halt up front rather than discovering it mid-run", :145-147), with the leg's
# recorded outcome depending on how PowerShell reports the missing command rather than on an
# andon — the same family as the recorded headline defect at verify.ps1:79-81.
#
# The `$needed` line itself is ci-packaging's (F-329a630d). This block is APPENDED and the
# clause above is left byte-for-byte as it was, so both land without touching the same lines
# (their SEAM 2, 2026-09-04).

#: The native commands the pre-flight can require, and nothing else. Two, because the halt
#: block's own text names two ("The launcher self-test and the site build shell out to
#: these"); a third would need its own row here and in `$needed`.
PREFLIGHT_COMMANDS = ("node", "npm")


def legs_and_their_commands():
    """`{skip flag: {commands that leg shells out to}}` — read off verify.ps1, not typed.

    THE NODE: the COMMANDS a leg invokes, sliced out of the leg's own body, against the flag
    that skips that leg. The slice is each `if ($NoX) { ... } else { Invoke-Leg ... }` block,
    from the guard to the next top-level `if ($No`, with comment lines dropped — the steps
    explain each other, so both commands appear in the prose above them and an inventory read
    off a comment would be an inventory read off an explanation.
    """
    guards = [(m.start(), m.group(1))
              for m in re.finditer(r"^if \(\$(No[A-Za-z]+)\) \{", VERIFY, re.M)]
    out = {}
    for i, (start, flag) in enumerate(guards):
        end = guards[i + 1][0] if i + 1 < len(guards) else len(VERIFY)
        body = chr(10).join(line for line in VERIFY[start:end].splitlines()
                            if not line.lstrip().startswith("#"))
        found = {c for c in PREFLIGHT_COMMANDS
                 if re.search(r"^\s*" + c + r"\s", body, re.M)}
        if found:
            out["-" + flag] = found
    return out


def test_the_leg_command_inventory_is_the_one_measured_on_this_script():
    """Size and membership before the property: the derivation is shown to have found the
    two legs that shell out, and what each shells out to."""
    inventory = legs_and_their_commands()
    assert inventory == {
        "-NoPackage": {"node", "npm"},
        "-NoSite": {"npm"},
    }, inventory


#: Measured 2026-09-04: `verify.ps1 -NoSite` prints `ANDON: not on PATH: node` and does not
#: name npm, while the leg it keeps runs `npm pack` and `npm install`. The `$needed` line
#: (verify.ps1:148-150) is ci-packaging's to correct this wave; a SUBSET assertion, so the
#: entry becomes deletable rather than red the moment it lands.
PREFLIGHT_GAP_TODAY = {"-NoSite": {"npm"}}


@needs_pwsh
@needs_stripped_path
@pytest.mark.parametrize("skipped", ["-NoSite", "-NoPackage"])
def test_the_halt_names_every_tool_the_selected_legs_shell_out_to(skipped, tmp_path):
    """DERIVED, not typed: whatever the KEPT legs invoke must appear in the ANDON line."""
    inventory = legs_and_their_commands()
    wanted = set().union(*(cmds for flag, cmds in inventory.items() if flag != skipped))
    assert wanted, (skipped, inventory)

    root = _scratch_verify(tmp_path)
    got = _run_verify(root, skipped, path=STRIPPED_PATH)
    assert got.returncode == 2, f"exit {got.returncode}\n{got.stdout}\n{got.stderr}"
    assert "ANDON: not on PATH" in got.stdout, got.stdout + got.stderr
    known_gap = PREFLIGHT_GAP_TODAY.get(skipped, set())
    missing = sorted(c for c in wanted if c not in got.stdout and c not in known_gap)
    assert missing == [], (
        f"`verify.ps1 {skipped}` keeps a leg that shells out to {sorted(missing)} and the "
        f"pre-flight halt does not name it:\n{got.stdout}\n"
        f"the kept legs invoke {sorted(wanted)}; verify.ps1's `$needed` (:148-150) is what "
        f"decides, and it is ci-packaging's to correct")


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
