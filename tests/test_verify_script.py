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
    _code_only,
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


def _pwsh_capture_encoding():
    """Encoding for redirected pwsh stdout on this host (F-9071bbb4).

    Windows OEM (cp437 here) emits box-drawing U+2500 / U+2550 as single bytes 0xC4 / 0xCD.
    `encoding='utf-8', errors='replace'` turned those into U+FFFD and destroyed the Cyan
    rule banners every red probe reprints. cp1252 once raised inside the reader thread
    (measured 2026-09-04); OEM does not.
    """
    return "cp437" if os.name == "nt" else "utf-8"


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
        encoding=_pwsh_capture_encoding(),
    )
    recorded = {}
    for line in (proc.stdout or "").splitlines():
        if line.startswith("LEG|"):
            _, name, code = line.split("|", 2)
            recorded[name] = code.strip()
    assert recorded, f"the harness recorded nothing.\n{proc.stdout}\n{proc.stderr}"
    return recorded


OK = "& $PY -c 'raise SystemExit(0)'"
SEVEN = "& $PY -c 'raise SystemExit(7)'"
ABSENT = "armature-no-such-binary-8481819 --version"


@needs_pwsh
def test_captured_leg_banner_keeps_box_drawing_glyphs(tmp_path):
    """F-9071bbb4: OEM box-drawing survives capture as U+2500, never U+FFFD."""
    py = sys.executable.replace("\\", "/")
    script = (
        "$ErrorActionPreference = 'Continue'\n"
        "$results = [System.Collections.Generic.List[object]]::new()\n"
        f"$PY = '{py}'\n"
        f"{invoke_leg_source()}\n"
        "Invoke-Leg -Name 'tests' -Body { & $PY -c 'raise SystemExit(0)' }\n"
    )
    path = tmp_path / "banner_pin.ps1"
    path.write_text(script, encoding="utf-8")
    got = subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-File", str(path)],
        capture_output=True,
        text=True,
        encoding=_pwsh_capture_encoding(),
    )
    out = got.stdout or ""
    assert "\ufffd" not in out, f"replacement glyphs in capture:\n{out!r}"
    banner = next(
        (ln for ln in out.splitlines()
         if ln.lstrip()[:1] in ("\u2500", "\u2550") and "tests" in ln),
        None,
    )
    assert banner is not None, f"no box-drawing banner in:\n{out!r}"
    assert banner.lstrip()[0] in ("\u2500", "\u2550"), banner


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


def _clean_room_count(text):
    """ROOMS, not tokens: `python -m venv` is the node, in either language."""
    return len(re.findall(r"-m venv", text))


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


def test_the_two_implementations_of_the_packaging_leg_have_the_same_number_of_clean_rooms():
    """The parity guard keyed on the ROOMS, not on the presence of a token.

    WAVE 16, ci-packaging SEAM 3 + this domain's half of it. The three clauses above —
    `"-m venv" in clean`, `"-m venv" in VERIFY`, a regex for `armature check` — are each
    satisfied by ONE room, so the action grew a second one (the sdist room,
    `clean-room/action.yml:70-72`) and `verify.ps1` kept one, with the suite green.
    Measured by ci-packaging on `041027c` with `grep -c`: `-m venv` appears twice in the
    action and once in `verify.ps1`; `.tar.gz` three times in the action and NOT AT ALL in
    `verify.ps1`. A token-keyed guard cannot see either.

    RED ON THIS BRANCH, deliberately: `verify.ps1` here is still the base's one-room
    script. ci-packaging's `F-7f129472` adds the sdist room; this is the assertion that
    holds the two implementations together once it lands, and it names which side is short.
    """
    action, script = _clean_room_count(clean_room_script()), _clean_room_count(VERIFY)
    assert action == script == 2, (
        f"the clean-room leg has {action} rooms in .github/actions/clean-room/action.yml "
        f"and {script} in verify.ps1; wave 14 added the sdist room to one implementation "
        f"and not the other, and every clause keyed on the TOKEN `-m venv` was satisfied "
        f"by the room that was already there")


def test_both_implementations_install_the_sdist_and_then_run_it():
    """The sdist room's own clause — the one that was ABSENT, not merely uncounted.

    `twine check` reads METADATA and opens no archive, so an sdist that cannot be installed
    passes it. The room that catches that installs the `.tar.gz` with `--no-deps` and then
    runs the shim it provides. RED ON THIS BRANCH for `verify.ps1` (ci-packaging's
    `F-7f129472`); green for the action on both trees.
    """
    for impl, text in (("the clean-room action", clean_room_script()),
                       ("verify.ps1", VERIFY)):
        assert "--no-deps" in text and ".tar.gz" in text, (
            f"{impl} never installs the sdist; `twine check` reads METADATA and opens no "
            f"archive, so a broken sdist reaches PyPI with this leg green")
        assert re.search(r"armature[\"'\s]+modules", text), (
            f"{impl} installs the sdist and never runs it")


# -- WAVE 26, F-1ebf099e: the parity guard counts what the rooms DO ------------------------
#
# `test_the_two_implementations_of_the_packaging_leg_have_the_same_number_of_clean_rooms`
# above counts ROOMS (`-m venv`), and `test_both_implementations_install_the_sdist_and_then_
# _run_it` asserts both install an sdist. Neither covers a property on which the two
# implementations actually differ, and both differences are on the artifact the leg judges:
#
#   (1) `verify.ps1:233-236` EMPTIES `dist/` before building; the composite action never
#       clears it. `python -m build` does not clear `dist/` either.
#   (2) `verify.ps1:246-262` selects the wheel and the sdist BY NAME, derived from
#       `pyproject.toml` (`$distName-$version.tar.gz` / `-py3-none-any.whl`); the action
#       installs `dist/*.tar.gz` and `dist/*.whl` — a GLOB.
#
# A grep for `distName`, `Remove-Item` and `dist/*` across `tests/*.py` on `81d6c07` found no
# assertion on either. The consequence is the one `verify.ps1`'s own comment records as
# MEASURED on this rig: `E:\AI\armature\dist` held an `armature_studio-0.2.1` pair beside the
# 0.3.0 pair, and `twine check dist\*` issued its verdict over four files, two of them three
# weeks old. The leg whose whole point is that it runs what CI runs diverges on WHICH artifact
# it runs and on whether a stale one can be present — and the parity guard reported parity.
#
# The census below is keyed on WHAT EACH IMPLEMENTATION DOES per axis, not on a token count.


def clears_dist_before_building(text):
    """Does this implementation remove `dist/` BEFORE it builds? `(cleared, build_at)`.

    Both languages, because the two implementations are written in two: PowerShell's
    `Remove-Item ... dist` and bash's `rm -rf dist`. The ORDER is the property — a clear that
    runs after the build judges nothing — so both positions are returned rather than a bool.

    Comments stripped first, through `test_ci_workflows._code_only`. Measured while writing
    this: `verify.ps1` names `-m build` in TWO comments (`:128` and `:248`) above the line
    that runs it (`:302`), so a raw-text reader placed the build at offset 8417 and the clear
    at 17570 and reported the clear as coming second — a census reading prose as code, in the
    test written to catch exactly that.
    """
    text = _code_only(text)
    clear = None
    for match in re.finditer(r"(?im)^[^\S\r\n]*(?:Remove-Item[^\r\n]*?\bdist\b"
                             r"|rm\s+-rf\s+[\"']?dist)", text):
        clear = match.start() if clear is None else clear
    build = None
    for match in re.finditer(r"-m\s+build\b", text):
        build = match.start() if build is None else build
    return clear, build


def artifact_selection(text):
    """How this implementation NAMES the two artifacts it installs: `"glob"` or `"derived"`.

    `derived` means the name is computed from `pyproject.toml` (the distribution name and the
    version), so a stale sibling in `dist/` cannot be selected. `glob` means `dist/*.whl` /
    `dist/*.tar.gz`, which selects whatever is there.

    Comments are stripped through `test_ci_workflows._code_only` — the home for that
    predicate — because BOTH implementations discuss their own selection in prose beside it,
    and a census satisfied by prose is the shape this wave closed twice over.
    """
    text = _code_only(text)
    globbed = bool(re.search(r"dist[/\\]\*\.(?:whl|tar\.gz)", text))
    derived = bool(re.search(r"(?i)(?:distName|DIST_NAME)", text)
                   and re.search(r"(?i)(?:\$version|\$\{VERSION\}|\$VERSION)", text))
    if derived and not globbed:
        return "derived"
    if globbed and not derived:
        return "glob"
    return "both" if derived else "neither"


def _packaging_leg_implementations():
    """`{name: text}` for the two implementations of one leg. ONE population, both axes."""
    return {"the clean-room action": clean_room_script(), "verify.ps1": VERIFY}


#: The axes on which the two implementations of the packaging leg are MEASURED to disagree on
#: this branch, with the finding and the domain that closes each. Both are ci-packaging's
#: half, landing in this same wave (`wave-26/seams-inbox.md` SEAM 4 §2, which carries the
#: exact strings): `F-1d0f6c82` adds the `rm -rf dist` + emptiness check to the action, and
#: `F-2a90c1ee` replaces `dist/*.tar.gz` / `dist/*.whl` with names derived from
#: `pyproject.toml`. This table is NOT a ceiling: the assertions below require each listed
#: axis to still be OPEN, so the moment the action gains the property its row must be deleted
#: or this file goes red. It cannot rot into an exemption the way a dated count can.
AXES_LANDING_THIS_WAVE = {
    # WAVE-26 MERGE FIX-UP (coordinator, 2026-09-05): both rows this table carried on the tests branch
    # ("dist is cleared before the build", ci-packaging F-1d0f6c82; "the artifacts are selected by a
    # derived name", ci-packaging F-2a90c1ee) closed when the ci-packaging branch merged first, and the
    # test below named both for deletion, as designed. Empty means: every axis the parity census reads
    # is live on BOTH implementations. A future same-wave hand-off adds its row here and deletes it at
    # the merge that closes it.
}


def test_verify_clears_dist_before_it_builds_and_the_clear_comes_first():
    """Axis (1) on the implementation that carries it, unconditionally.

    An ordering, not a presence: a clear that runs after `-m build` deletes the thing the leg
    was about to judge, and a leg with no clear at all judges whatever the rig left behind.
    """
    clear, build = clears_dist_before_building(VERIFY)
    assert clear is not None, (
        "verify.ps1 no longer clears `dist/`; `python -m build` does not clear it either, so "
        "`twine check dist\\*` would range over artifacts this run did not build")
    assert build is not None, "verify.ps1 no longer builds anything"
    assert clear < build, (
        "verify.ps1 clears `dist/` AFTER building into it; the clear must come first or the "
        "leg judges nothing")


def test_verify_selects_its_artifacts_by_a_derived_name_not_a_glob():
    """Axis (2) on the implementation that carries it, unconditionally."""
    assert artifact_selection(VERIFY) == "derived", (
        "verify.ps1 stopped deriving the wheel and sdist names from pyproject.toml; a glob "
        "selects whatever version happens to be in `dist/`")


def test_the_two_implementations_of_the_packaging_leg_agree_on_every_axis():
    """The parity claim, keyed on what the rooms DO (F-1ebf099e).

    The pre-existing guard counted rooms; a leg with the same number of rooms can still build
    from a directory one implementation clears and the other does not, and install an
    artifact one selects by name and the other selects by glob. Those are the two axes on
    which they were measured to differ.

    Axes listed in `AXES_LANDING_THIS_WAVE` are exempted here and REQUIRED to still be open by
    the test below, so this is a hand-off with a deadline rather than an allowlist.
    """
    impls = _packaging_leg_implementations()
    disagreements = {}

    if "dist is cleared before the build" not in AXES_LANDING_THIS_WAVE:
        cleared = {name: clears_dist_before_building(text)[0] is not None
                   for name, text in impls.items()}
        if len(set(cleared.values())) > 1:
            disagreements["dist is cleared before the build"] = cleared

    if "the artifacts are selected by a derived name" not in AXES_LANDING_THIS_WAVE:
        selection = {name: artifact_selection(text) for name, text in impls.items()}
        if len(set(selection.values())) > 1:
            disagreements["the artifacts are selected by a derived name"] = selection

    assert disagreements == {}, (
        f"the two implementations of one leg differ on {sorted(disagreements)}: "
        f"{disagreements}. The leg's whole claim is that a green local run equals the green "
        f"CI run its DESCRIPTION equates it to.")


def test_every_axis_deferred_to_the_other_domain_is_still_actually_open():
    """The deadline on `AXES_LANDING_THIS_WAVE`, so it cannot become a permanent exemption.

    Each listed axis must name a finding id, and must still be MEASURABLY open on the action
    side. The moment ci-packaging's half lands — in this wave's merge — the row is false and
    this test says so, naming the axis to delete. That is the opposite of a dated ceiling,
    which goes quiet when the backlog it records is cleared (F-9473345e, one file over).
    """
    action = clean_room_script()
    for axis, reason in sorted(AXES_LANDING_THIS_WAVE.items()):
        assert re.search(r"F-[0-9a-f]{8}", reason), (axis, reason)

    still_open = {}
    if "dist is cleared before the build" in AXES_LANDING_THIS_WAVE:
        still_open["dist is cleared before the build"] = (
            clears_dist_before_building(action)[0] is None)
    if "the artifacts are selected by a derived name" in AXES_LANDING_THIS_WAVE:
        still_open["the artifacts are selected by a derived name"] = (
            artifact_selection(action) == "glob")

    closed = sorted(axis for axis, open_ in still_open.items() if not open_)
    assert closed == [], (
        f"{closed} is recorded in AXES_LANDING_THIS_WAVE as ci-packaging's outstanding half, "
        f"and the clean-room action already carries it. Delete the row: the parity census "
        f"above then arms on that axis, which is the point of the hand-off.")


def test_the_artifact_selection_axis_can_tell_a_glob_from_a_derived_name(tmp_path):
    """The red proof, on a scratch `dist/` holding TWO versions — the state
    `verify.ps1`'s own comment records as measured on this rig (a 0.2.1 pair beside the
    0.3.0 pair, `twine check dist\\*` ruling over four files).

    Both halves are driven through the production readers: `artifact_selection` must call the
    two spellings differently, and the difference must MATTER — a glob resolves both versions
    in that directory while a derived name resolves exactly the one this run built.
    """
    import glob as _glob

    dist = tmp_path / "dist"
    dist.mkdir()
    for name in ("armature_studio-0.2.1-py3-none-any.whl", "armature_studio-0.2.1.tar.gz",
                 "armature_studio-0.3.0-py3-none-any.whl", "armature_studio-0.3.0.tar.gz"):
        (dist / name).write_bytes(b"")

    globbed = sorted(os.path.basename(x) for x in _glob.glob(str(dist / "*.whl")))
    derived = sorted(os.path.basename(x) for x in
                     _glob.glob(str(dist / "armature_studio-0.3.0-py3-none-any.whl")))
    assert len(globbed) == 2, globbed
    assert derived == ["armature_studio-0.3.0-py3-none-any.whl"], derived

    assert artifact_selection('"$SDIST_ROOM/bin/python" -m pip install dist/*.tar.gz\n'
                              'pip install dist/*.whl') == "glob"
    assert artifact_selection('$distName = "armature_studio"\n'
                              '$sdist = "dist/$distName-$version.tar.gz"') == "derived"
    assert artifact_selection("python -m build") == "neither"


def test_the_dist_clear_axis_reads_both_languages_and_the_order():
    """The other red proof: the axis must see PowerShell's clear and bash's, and must fail a
    clear that runs after the build.

    Two implementations in two languages is why this axis is a function rather than a
    substring: a guard that only knew `Remove-Item` would report the bash side as never
    clearing, and a guard that ignored order would pass a leg that empties `dist/` after
    building into it.
    """
    ps_ok = 'Remove-Item -Recurse -Force dist\n& $python -m build\n'
    sh_ok = 'rm -rf dist\npython -m build\n'
    reversed_order = 'python -m build\nrm -rf dist\n'
    none_at_all = 'python -m build\ntwine check dist/*\n'

    for text in (ps_ok, sh_ok):
        clear, build = clears_dist_before_building(text)
        assert clear is not None and build is not None and clear < build, text

    clear, build = clears_dist_before_building(reversed_order)
    assert clear is not None and build is not None and clear > build, reversed_order

    clear, _build = clears_dist_before_building(none_at_all)
    assert clear is None, none_at_all


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
        # verify.ps1 prints box-drawing rules. cp1252 once raised inside the reader thread
        # (measured 2026-09-04, merged wave 6); utf-8+replace turned OEM 0xC4 into U+FFFD
        # (F-9071bbb4). Decode with the OEM page the redirected host actually emits.
        encoding=_pwsh_capture_encoding(),
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
        # A command, not a hashtable key. Wave 29's receipt writes
        # `node = $nodeReport` / `npm = $npmReport` after the last guard;
        # `^\s*node\s` counted those as invocations.
        found = {c for c in PREFLIGHT_COMMANDS
                 if re.search(r"^\s*" + c + r"\s+[^=\s]", body, re.M)}
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
        capture_output=True, text=True, encoding=_pwsh_capture_encoding(),
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
        "            & $python -m pip install 'build>=1.5,<2' 'twine>=7,<8' 'trove-classifiers>=2026.6.1.19,<2027'",
        "            git rev-parse HEAD\n"
        "            & $python -m pip install 'build>=1.5,<2' 'twine>=7,<8' 'trove-classifiers>=2026.6.1.19,<2027'",
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
        # BOTH spellings, the way `_scratch_verify` writes them: whether `Join-Path` on a POSIX
        # host leaves the child's backslashes alone (a file whose NAME contains them) or
        # normalises them to `/` (the nested path) depends on the pwsh build. MEASURED on the
        # first CI run of the swarm (2026-09-05, `6e83dbb`, ubuntu-latest): the script's ANDON
        # named `<root>/.venv/Scripts/python.exe` -- forward slashes -- while this test had
        # linked only the backslash spelling, so the interpreter line never printed. Two links
        # to one interpreter cost nothing and make the test read the script's behaviour rather
        # than assume one join semantics.
        nested = root / ".venv" / "Scripts"
        nested.mkdir(parents=True, exist_ok=True)
        os.symlink(sys.executable, nested / "python.exe")
        os.symlink(sys.executable, root / r".venv\Scripts\python.exe")
    got = _run_verify(root, "-NoSite", "-NoPackage")
    out = got.stdout or ""
    line = [ln for ln in out.splitlines() if "interpreter:" in ln]
    assert line, f"no interpreter line at all:\n{out}"
    expected = "%d.%d.%d" % sys.version_info[:3]
    assert expected in line[0], (
        f"the summary reports no readable version for a real interpreter: {line[0]!r}"
    )


# =========================================================================================
# WAVE 23 — ci-packaging's own contract for `verify.ps1` (SEAM 1).
# =========================================================================================


# -- F-da5e552b: the host this script is, declared -----------------------------------------
#
# `Invoke-Leg`'s outcome recording is PowerShell 7 only. `$PSNativeCommandUseErrorActionPreference`
# is inert before 7.3 and `catch [System.Management.Automation.NativeCommandExitException]`
# names a type Windows PowerShell 5.1 does not have — and nothing guarded the host:
# `grep -i requires verify.ps1` on `e8263a3` returned only the `[build-system].requires`
# prose, and neither of the two pre-flight ANDONs reads `$PSVersionTable`. Measured on this
# rig by driving both hosts: under pwsh 7.6.5 the type resolves and the preference variable
# exists; under Windows PowerShell 5.1.26100.9233 the script terminates with `Unable to find
# type [System.Management.Automation.NativeCommandExitException]` and
# `Get-Variable PSNativeCommandUseErrorActionPreference` returns nothing — so the rig's
# pre-tag gate died mid-run without printing the summary its DESCRIPTION promises.

#: The floor at which BOTH constructs `Invoke-Leg` uses exist and are non-experimental.
INVOKE_LEG_POWERSHELL_FLOOR = (7, 4)

WINDOWS_POWERSHELL = shutil.which("powershell")


def _requires_version():
    """The version `#requires -Version` names, or None."""
    match = re.search(r"(?m)^#requires\s+-Version\s+(\d+(?:\.\d+)*)\s*$", VERIFY)
    return tuple(int(p) for p in match.group(1).split(".")) if match else None


def test_verify_declares_the_powershell_its_own_leg_recorder_needs():
    """A `#requires` directive, at or above the version the constructs need."""
    declared = _requires_version()
    assert declared is not None, (
        "verify.ps1 carries no `#requires -Version`; its Invoke-Leg uses two PowerShell 7 "
        "constructs and Windows PowerShell 5.1 terminates on the first of them, mid-run, "
        "before the summary the DESCRIPTION promises is printed")
    assert declared >= INVOKE_LEG_POWERSHELL_FLOOR, (
        f"verify.ps1 requires PowerShell {declared} and Invoke-Leg needs "
        f"{INVOKE_LEG_POWERSHELL_FLOOR}: `$PSNativeCommandUseErrorActionPreference` is inert "
        "before 7.3 and the NativeCommandExitException type is 7-only")
    body = invoke_leg_source()
    assert "$PSNativeCommandUseErrorActionPreference" in body, (
        "the preference variable the requirement exists for is gone from Invoke-Leg; the "
        "floor above is now guarding nothing")
    assert "NativeCommandExitException" in body, (
        "the typed catch the requirement exists for is gone from Invoke-Leg")


def test_the_directive_is_the_first_thing_in_the_file():
    """A `#requires` below the first executable line is a halt that arrives too late."""
    lines = [line for line in VERIFY.splitlines() if line.strip()]
    assert lines and lines[0].lower().startswith("#requires"), (
        f"the first non-blank line of verify.ps1 is {lines[0]!r}")


def test_the_version_reader_goes_red_on_a_file_with_no_directive():
    """The mutation: the file as it stood on `e8263a3`, which named no host at all."""
    assert re.search(r"(?m)^#requires\s+-Version\s+(\d+(?:\.\d+)*)\s*$",
                     "<#\n.SYNOPSIS\n  x\n#>\nparam()\n") is None


@pytest.mark.skipif(
    WINDOWS_POWERSHELL is None,
    reason="no Windows PowerShell on this box to measure the 5.1 half against")
def test_the_constructs_the_directive_guards_are_absent_from_windows_powershell():
    """The measured operand, driven — not asserted from the version number.

    verify.ps1 itself is NOT run here: with the directive present a 5.1 host refuses it, and
    with the directive absent it would run the whole suite. The two constructs are probed
    directly instead, which is the mechanism the directive exists for.
    """
    probe = (
        "$t = [System.Management.Automation.NativeCommandExitException] "
        "-as [type]; "
        "$v = Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction "
        "SilentlyContinue; "
        "Write-Output ('MAJOR|' + $PSVersionTable.PSVersion.Major); "
        "Write-Output ('TYPE|' + [bool]$t); "
        "Write-Output ('PREF|' + [bool]$v)"
    )
    got = subprocess.run([WINDOWS_POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", probe],
                         capture_output=True, text=True)
    fields = dict(line.split("|", 1) for line in got.stdout.splitlines() if "|" in line)
    if fields.get("MAJOR", "") not in ("5", "4", "3"):
        pytest.skip(f"`powershell` here is major {fields.get('MAJOR')!r}, not Windows PowerShell")
    assert fields["TYPE"] == "False", (
        "Windows PowerShell resolves NativeCommandExitException on this box; the directive's "
        "operand has moved and its floor should be re-measured")
    assert fields["PREF"] == "False", (
        "Windows PowerShell carries $PSNativeCommandUseErrorActionPreference on this box")


# -- F-a7b2c2dc: leg 3 ESTABLISHES the cleared-`dist/` invariant ---------------------------
#
# The leg's stated invariant — "`dist/` CLEARED so every verdict below is about what this run
# built" — was never established. `Remove-Item ... -ErrorAction SilentlyContinue` suppresses
# its own failure (the explicit -EA overrides the `$ErrorActionPreference = 'Stop'` Invoke-Leg
# sets), and nothing between the clear and `twine check dist\*` asked whether the directory
# was empty. The two artifacts are selected BY NAME lower down, which protects the two clean
# rooms and not the two checks that range over `dist\*`. Re-measured on `e8263a3` under pwsh
# 7.6.5 with `$ErrorActionPreference = 'Stop'` and `$PSNativeCommandUseErrorActionPreference
# = $true` set: the suppressed Remove-Item raised no terminating error, left `$LASTEXITCODE`
# null, recorded one object in `$Error` that nothing reads, and the stale files remained.


def dist_clear_source():
    """`$dist = Join-Path $repo 'dist'` through the end of its `if (Test-Path $dist)` block."""
    start = VERIFY.index("$dist = Join-Path $repo 'dist'")
    open_brace = VERIFY.index("{", VERIFY.index("if (Test-Path $dist)", start))
    depth = 0
    for j in range(open_brace, len(VERIFY)):
        if VERIFY[j] == "{":
            depth += 1
        elif VERIFY[j] == "}":
            depth -= 1
            if depth == 0:
                return VERIFY[start : j + 1]
    raise AssertionError("the dist clear block is unbalanced")


def test_the_clear_is_followed_by_a_check_before_anything_ranges_over_dist():
    """Statically: the emptiness check sits between the clear and `twine check dist\\*`.

    WAVE 26, `F-1d0f6c82` — THE FIFTH PARITY AXIS. Wave 23 established this invariant in
    `verify.ps1` on the stated ground that `twine check dist\\*` and the classifier gate
    "can still issue their verdicts over an artifact this run did not build". The OTHER
    implementation of the same leg got neither half: a grep for a remove or a clean over
    `.github/actions/clean-room/action.yml` returned nothing, and this test lifted `VERIFY`
    alone — while the four axes beside it (rooms counted, sdist installed and run, two
    `pip freeze` lines, the toolchain specifiers) all pair the two texts. It now asserts the
    property of both, so the next hardening of one implementation cannot land in one of them
    again.
    """
    #: CODE ONLY. Both texts now DESCRIBE this invariant as well as running it, and a
    #: comment quoting `python -m build` would put the ordering assertions below on prose.
    action = _code_only(clean_room_script())
    assert re.search(r"(?m)^\s*rm -rf dist\s*$", action), (
        "the clean-room action never clears dist/ before building into it; `python -m build` "
        "does not clear it, and release.yml uploads the whole directory to the publish job")
    assert action.index("rm -rf dist") < action.index("-m build"), (
        "the action clears dist/ after building into it, which is the artifact the clear "
        "exists to protect")
    assert action.index("-m build") < action.index("twine check"), (
        "the action checks metadata before it builds")
    assert "ls -la dist/" in action, (
        "the action's clear is not followed by a refusal that LISTS what survived; an "
        "unchecked clear is the shape wave 23 replaced in the other implementation")

    block = dist_clear_source()
    assert "Remove-Item" in block, "the clear left the block this test lifts"
    assert "-ErrorAction SilentlyContinue" in block, (
        "the -EA flag was removed; a locked file is not a reason to halt BEFORE the check "
        "that would name it — the check, not the flag, is the fix")
    assert "Get-ChildItem" in block and "$global:LASTEXITCODE = 1" in block, (
        "nothing in the clear block asks whether dist/ is actually empty, so `twine check "
        "dist\\*` and the classifier gate can still range over a file this run did not build")
    twine = VERIFY.index("-m twine check")
    assert VERIFY.index("Get-ChildItem $dist -Force") < twine, (
        "the emptiness check runs after `twine check`, which is the verdict it exists to "
        "protect")


def _run_dist_clear(tmp_path):
    """Drive the lifted clear block with `$repo` pointed at a scratch tree."""
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        "$PSNativeCommandUseErrorActionPreference = $true\n"
        f"$repo = '{str(tmp_path).replace(chr(92), '/')}'\n"
        "$global:LASTEXITCODE = 0\n"
        "function Invoke-Body {\n" + dist_clear_source() + "\n}\n"
        "Invoke-Body\n"
        "Write-Output ('CODE|' + $global:LASTEXITCODE)\n"
    )
    path = tmp_path / "clear_harness.ps1"
    path.write_text(script, encoding="utf-8")
    proc = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-File", str(path)],
                          capture_output=True, text=True)
    code = None
    for line in proc.stdout.splitlines():
        if line.startswith("CODE|"):
            code = line.split("|", 1)[1].strip()
    return code, proc.stdout + proc.stderr


@needs_pwsh
def test_a_dist_that_clears_leaves_the_leg_running(tmp_path):
    """The direction the fix must not break: an empty dist/ is the normal case."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "armature_studio-0.0.1-py3-none-any.whl").write_bytes(b"stale")
    code, out = _run_dist_clear(tmp_path)
    assert code == "0", out
    assert "could not be cleared" not in out, out
    assert list(dist.iterdir()) == [], list(dist.iterdir())


@needs_pwsh
def test_leg_three_refuses_a_dist_it_could_not_clear(tmp_path):
    """The red proof: a stale artifact survives the clear and the leg proceeds anyway.

    The file is held open by another process, which is what makes `Remove-Item -Force` fail
    on Windows — the same shape as a half-written archive or an antivirus hold. Before this
    fix the block below recorded nothing and `twine check dist\\*` issued its verdict over
    the survivor.
    """
    dist = tmp_path / "dist"
    dist.mkdir()
    stale = dist / "armature_studio-0.0.1-py3-none-any.whl"
    stale.write_bytes(b"stale")
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import sys,time;f=open(sys.argv[1],'a');print('OPEN',flush=True);time.sleep(60)",
         str(stale)],
        stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "OPEN"
        code, out = _run_dist_clear(tmp_path)
    finally:
        holder.kill()
        holder.wait()
    if not stale.exists():
        pytest.skip("this filesystem removed a file held open by another process")
    assert code == "1", (
        f"a stale artifact survived the clear and the leg recorded {code!r}; every verdict "
        f"below it is then a claim about a file this run did not build.\n{out}")
    assert "could not be cleared" in out and stale.name in out, (
        f"the refusal does not name what remained.\n{out}")


# -- F-1c5dc527 / F-e3e6bdc8: the probe is one file, and the rooms say what they resolved ---


def _uncommented(text):
    """`verify.ps1` with its `#` comment lines blanked — comments quote the code they
    replaced, and a census over the raw text would read a correction record as live code."""
    return "\n".join("" if line.strip().startswith("#") else line
                      for line in text.splitlines())


def test_the_script_carries_no_platform_branch_its_own_interpreter_resolution_made_dead():
    """WAVE 26, `F-e70bd932` — six branches whose other arm could never be taken.

    `$binDir` / `$exe` were consumed at four constructed paths, every one of them with an
    embedded backslash, so the non-Windows arm would have built a `bin\\python` name no POSIX
    layout has; `$shimName` was the sixth site. None could run: the interpreter is resolved
    as a hard-coded `.venv\\Scripts\\python.exe` and the ANDON exits 2 when that exact path
    is absent, and `#requires -Version 7.4` under pwsh 7 makes `$IsWindows` true. Nothing
    reported a green it had not earned — a constructed path that does not exist raises inside
    `Invoke-Leg` — but the branches said this script runs on the Mac rig and the interpreter
    line said it does not.

    The rule is CONDITIONAL, not a ban: a platform branch may return the day the interpreter
    resolution has a POSIX arm, and this test says so by requiring the two together.
    """
    code = _uncommented(VERIFY)
    branches = [ln.strip() for ln in code.splitlines() if "$IsWindows" in ln]
    posix_interpreter = "bin/python" in code or "bin\\python'" in code
    if not posix_interpreter:
        assert branches == [], (
            "verify.ps1 branches on $IsWindows while resolving its interpreter at a "
            f"hard-coded Windows venv layout, so the other arm is unreachable: {branches}")
    assert "$exe" not in code, (
        "the `$exe` suffix is back; it exists only to serve the branch above")
    for embedded in (r'"$binDir\python$exe"', r'"$binDir\armature$exe"'):
        assert embedded not in VERIFY.replace("# ", "#"), (
            f"{embedded} builds a path segment by string interpolation with an embedded "
            "backslash; Join-Path is what the sibling npm room already uses")


def pin_report_source():
    """The summary block that resolves ci.yml's `==` specifiers, lifted by its own marker."""
    start = VERIFY.index("$pinReport = @(")
    end = VERIFY.index("foreach ($line in @($pinReport))")
    return VERIFY[start:VERIFY.index("\n", end) + 1]


def test_the_summary_states_which_build_of_the_pinned_suite_dependencies_it_ran():
    """WAVE 26, `F-9c05e7b3` — the THIRD runtime axis the summary said nothing about.

    The block reports the interpreter and node because a green local run is not a green CI
    run on those axes. Two suite dependencies are pinned with `==` for the same reason —
    their exact build decides a result — and pyproject records that the rig satisfies `cv2`
    from a DIFFERENT DISTRIBUTION than every CI install line names
    (`opencv-contrib-python` here, `opencv-python-headless` there). Re-measured on the repo
    venv 2026-09-05: `opencv-python-headless` and `opencv-python` both ABSENT. So the aapose
    golden-frame tests run against another rasterizer's distribution and the RUN did not say
    so. The specifiers are READ OUT OF ci.yml rather than written here, so a re-pin moves
    this report with it.
    """
    block = pin_report_source()
    assert "ci.yml" in block, (
        "the pin report no longer reads ci.yml's install line; a list written here would be "
        "a fourth copy of the dependency set the manifest already holds to CI's")
    assert "importlib.metadata" in block or "PackageNotFoundError" in block, (
        "the report does not resolve the installed version through importlib.metadata")
    assert "(absent)" in block, (
        "a distribution that is not installed must be reported as absent, never guessed at")
    assert "cv2" in block, (
        "the report does not name the distribution that actually provides cv2, which is the "
        "half pyproject says diverges between the rig and CI")
    assert "-m pip" in block, (
        "the report's marker for CI's install line changed; `pip` and `install` spelled "
        "together here would be read as an install line by the artifact-toolchain census")


@needs_pwsh
def test_the_pin_report_resolves_the_specifiers_and_names_the_cv2_provider(tmp_path):
    """Driven, not read: the block runs against the real ci.yml on the real venv.

    A static assertion alone would pass on a block that prints nothing. This one has to
    produce a row per `==` specifier ci.yml installs, and a row naming the distribution that
    answers `import cv2`.
    """
    script = (
        f"$repo = '{REPO.replace(chr(92), '/')}'\n"
        f"$python = '{sys.executable.replace(chr(92), '/')}'\n"
        + pin_report_source()
    )
    path = tmp_path / "pin_report.ps1"
    path.write_text(script, encoding="utf-8")
    got = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-File", str(path)],
                         capture_output=True, text=True,
                         encoding=_pwsh_capture_encoding())
    out = got.stdout or ""
    assert "pinned dependencies" in out, f"{out}\n{got.stderr}"
    rows = [ln.strip() for ln in out.splitlines() if "->" in ln or "provided by" in ln]
    assert any("opencv-python-headless==" in r for r in rows), rows
    assert any("matplotlib==" in r for r in rows), rows
    assert any(r.startswith("cv2 ") and "provided by" in r for r in rows), rows
    #: the measurement this block exists for, asserted as a PROPERTY rather than as a
    #: number: whatever provides cv2 here is named, and if it is not the distribution CI
    #: installs, the run says which one it is.
    provider = [r for r in rows if r.startswith("cv2 ")][0]
    assert "opencv" in provider, provider


@needs_pwsh
def test_a_statement_after_a_failing_native_command_does_not_run(tmp_path):
    """WAVE 26, `F-4f8a2d16` — the reachability claim, driven rather than reasoned.

    `Invoke-Leg` sets `$ErrorActionPreference = 'Stop'` and
    `$PSNativeCommandUseErrorActionPreference = $true`, which promote a native command's
    non-zero exit to a terminating error caught by the function — so every
    `if ($LASTEXITCODE -ne 0) { return }` guard in a leg body is unreachable, and the
    comment block above `Invoke-Leg` now says they are belt-and-braces rather than the
    mechanism. A future edit that removed the promotion would make that comment false and
    the guards load-bearing again, silently. This is what catches it.

    BOTH DIRECTIONS MEASURED at wave 26, by lifting this function and driving it twice with
    a body running a command that exits 7, then the guard, then a marker write, then a
    command that exits 0. As the function stands: recorded ExitCode 7, Raised False,
    Established True, and NEITHER the guard nor the marker ran. With the two preference
    lines stripped out: recorded ExitCode 0 -- a PASS on a leg whose first command exited 7
    -- and the guard AND the marker both ran. So the promotion is the mechanism, the guards
    are what would be left without it, and this fixture can tell the two apart.
    """
    marker = (tmp_path / "after.txt").as_posix()
    guard = (tmp_path / "guard.txt").as_posix()
    body = (f"{SEVEN}; "
            f"if ($LASTEXITCODE -ne 0) {{ Set-Content -Path '{guard}' -Value 'guard' }}; "
            f"Set-Content -Path '{marker}' -Value 'after'; {OK}")
    recorded = _run_legs(tmp_path, [("promotion", body)])
    assert recorded["promotion"] == "7", (
        "a leg whose first native command exited 7 and whose last exited 0 recorded "
        f"{recorded['promotion']!r}; the promotion that makes the guards redundant is gone, "
        "and the 21 `-ne 0` guards in the leg bodies are load-bearing again")
    assert not os.path.exists(guard), (
        "the guard after the failing command RAN; it is described in verify.ps1 as "
        "belt-and-braces, which is only true while the promotion stops the leg first")
    assert not os.path.exists(marker), (
        "a statement after a failing native command ran, so a leg no longer stops at the "
        "first command that failed")


def test_verify_runs_the_one_lazy_import_probe_file():
    """One text, two callers — and no here-string copy left behind."""
    assert "lazy_import_probe.py" in VERIFY, (
        "verify.ps1 no longer runs `.github/actions/clean-room/lazy_import_probe.py`; a "
        "here-string copy is a second implementation of one probe, and no census under "
        "`.github/` can see it")
    assert "aapose.blank_canvas" not in VERIFY, (
        "verify.ps1 carries an inline copy of the probe body again")
    assert "lazy_import_probe.py" in clean_room_script(), (
        "the clean-room action no longer runs the same file")


def test_both_clean_rooms_state_the_dependency_set_they_exercised():
    """`--quiet` removed the one line saying what pip resolved, in both implementations.

    The wheel room resolves the runtime set FRESH — the coordinator's wave-23 ruling, and a
    user's experience of `pip install armature-studio` — so what it resolved has to be
    readable, or a dependency-day break and a wheel defect are the same red on the step with
    no compensator.
    """
    for impl, text in (("the clean-room action", clean_room_script()),
                       ("verify.ps1", VERIFY)):
        quiet = [line.strip() for line in text.splitlines()
                 if "pip install" in line and not line.strip().startswith("#")
                 and ("--quiet" in line.split() or "-q" in line.split())
                 and ("dist" in line or "$wheelPath" in line or "$sdistPath" in line)]
        assert quiet == [], (
            f"{impl} silences the clean-room install: {quiet}")
        assert "pip freeze" in text, (
            f"{impl} never states the dependency set the probe ran against")
    def _freezes(text):
        # CODE lines only, in either language: `#` opens a comment in bash and in
        # PowerShell alike, and both files now DESCRIBE the report as well as running it.
        return [line.strip() for line in text.splitlines()
                if "pip freeze" in line and not line.strip().startswith("#")]

    assert len(_freezes(VERIFY)) == 2, (
        f"verify.ps1 reports {_freezes(VERIFY)} for its two clean-room installs")
    assert len(_freezes(clean_room_script())) == 2, (
        f"the clean-room action reports {_freezes(clean_room_script())} for its two rooms")
