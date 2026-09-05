#requires -Version 7.4
<#
.SYNOPSIS
  One command that runs everything CI runs, plus the site build, and refuses on any leg.

.NOTES
  THE HOST THIS SCRIPT IS, AND WAS NOT SAYING. `Invoke-Leg`'s outcome recording is PowerShell
  7 only: `$PSNativeCommandUseErrorActionPreference` is inert before 7.3, and
  `catch [System.Management.Automation.NativeCommandExitException]` names a type Windows
  PowerShell 5.1 does not have. Nothing guarded the host -- `grep -i requires verify.ps1` on
  `e8263a3` returned only the `[build-system].requires` prose, and neither of the two ANDONs
  below checks `$PSVersionTable`. Measured on this rig by driving both hosts: under pwsh
  7.6.5 the type resolves and the preference variable exists; under Windows PowerShell
  5.1.26100.9233 the script terminates with `Unable to find type
  [System.Management.Automation.NativeCommandExitException]` and
  `Get-Variable PSNativeCommandUseErrorActionPreference` returns nothing -- so the rig's
  pre-tag gate died mid-run without ever printing the summary the DESCRIPTION promises.
  `#requires -Version 7.4` above is the halt, and 7.4 is the version at which BOTH constructs
  exist and are non-experimental. It is deliberately a `#requires` and not a
  `$PSVersionTable` andon beside the other two: the directive refuses before a single line of
  this script runs, where an in-script check would be unreachable underneath it, and a check
  that cannot fail is not a check. `tests/test_verify_script.py` asserts the directive is
  here and names a version at or above the one `Invoke-Leg`'s constructs need.

.DESCRIPTION
  The legs are the same ones `.github/workflows/ci.yml` runs, in the same order and with
  the same meaning, so a green local run and a green CI run are the same claim ABOUT WHAT
  RAN. They are not the same claim about the two RUNTIMES those legs run on. The Python
  axis: every Python leg here uses `$repo\.venv\Scripts\python.exe`, whatever version the
  rig happens to hold, while ci.yml's `python-tests` job runs its own matrix and
  release.yml's gate runs one version -- none of them necessarily this one. The node axis,
  which moved into ci.yml in wave 12 and did not move here: leg 3's launcher self-test,
  `npm pack` and the clean install of the tarball run on whatever single node the rig has on
  PATH, while ci.yml's `launcher` job runs them across a 2-entry matrix -- node 18, the floor
  `npm/package.json` declares in `engines.node`, and node 22 -- for the stated reason that
  nothing ran 18. So an npm-9 install layout or an API level `bin/armature.mjs` uses can pass
  here and fail there. The summary block prints the resolved interpreter AND the resolved
  node and npm, so each run states which runtimes its claim was made on; a
  version-specific behaviour can still pass here and fail on a runner, and those lines are
  where to look first. The legs themselves:

    1. the test suite on the repo venv
    2. the test suite again under `-O` with PYTHONOPTIMIZE=1 — this leg is not a
       duplicate. A gate implemented as an `assert` is DELETED by the optimizer, and 87
       of facet's andons turned out to be removable by an environment variable. Running
       the suite a second time under `-O` is what proves this repo's gates raise.
    3. the package build — `build` and `twine` installed under the SAME constraints
       `.github/actions/clean-room/action.yml` installs them under (they are the tools that
       produce the artifact, and this leg used to build with whatever the repo venv held),
       then `dist/` CLEARED so every verdict below is about what this run built, then the
       wheel and sdist, `twine check` on the metadata, then TWO clean rooms in the action's
       own order — the sdist installed with `--no-deps` into its own venv and `armature
       modules --json` run from it (the archive has to BUILD, which installing a wheel never
       proves), then the wheel installed into a second CLEAN venv and run from THAT install —
       and the launcher's own self-test. Added at v0.2.0, when this repo started publishing: a package that fails
       to build is a release that fails at the registry, and finding that out from a
       release job is finding it out too late to take back. The clean-install half was
       missing until it was enumerated against ci.yml — it is the leg whose whole point is
       catching a wheel that does not work, and it probes the function-local dependencies
       (`draw_body`, `draw_hand`, `mean_consecutive_frame_difference`) because `armature
       check` executes no function body and was green on a wheel that could not run.
    4. the site build: `npm audit --package-lock-only --audit-level=high` — the dependency
       scan, also missing until it was enumerated, and running BEFORE the install because
       `npm ci` executes every lifecycle script in the tree it resolves — then `npm ci`,
       then `npm run build`, which is what GitHub Pages deploys.

  Every leg runs even if an earlier one fails, so one invocation reports the whole
  picture rather than the first thing to break. The exit code is 0 only if all legs pass,
  and a leg that could not establish an outcome at all counts as a failure, not a pass.
  That is recorded per COMMAND, not per leg: a command that vanishes part-way through a leg
  leaves an earlier command's zero in $LASTEXITCODE, and a leg is a claim about every
  command in it — so a leg whose body raised establishes no outcome and fails.

.PARAMETER NoSite
  Skip leg 4. Useful when only Python changed and node_modules is cold; the site leg is
  the slow one. A run with -NoSite is NOT a full verify and says so in its summary.

.PARAMETER NoPackage
  Skip leg 3. Useful when nothing packaging-related changed; it installs `build` and `twine`
  at CI's constraints into the repo venv, EMPTIES `dist/` and rebuilds, so it needs an index,
  it changes what that venv holds, and it does not preserve an artifact left there earlier. Note that the SUITE also builds an sdist (two tests in
  `tests/test_packaging.py` pin what the published archive carries), so `build` is needed by
  leg 1 as well — skipping this leg does not remove that requirement.

.EXAMPLE
  pwsh -NoProfile -File .\verify.ps1
  pwsh -NoProfile -File .\verify.ps1 -NoSite
#>
[CmdletBinding()]
param(
    [switch]$NoSite,
    [switch]$NoPackage
)

$ErrorActionPreference = 'Continue'
$repo = $PSScriptRoot
$python = Join-Path $repo '.venv\Scripts\python.exe'

$results = [System.Collections.Generic.List[object]]::new()

function Invoke-Leg {
    param(
        [string]$Name,
        [scriptblock]$Body
    )
    Write-Host ''
    Write-Host "──────── $Name" -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    # A leg's outcome is RECORDED, never inherited. PowerShell does not clear $LASTEXITCODE
    # between commands, and a CommandNotFoundException sets no exit code at all — so this
    # function used to write down the PREVIOUS leg's zero as this leg's pass. Measured on
    # this exact function: a body running an interpreter that exits 0 followed by a
    # non-existent binary reported ExitCode 0, and so did a body whose only statement was a
    # non-existent binary. Concretely, with node absent leg 3's launcher self-test never ran
    # and the leg passed on twine's zero; with npm absent leg 4 built nothing and passed on
    # leg 3's — and the script then printed "All legs passed." That is this repo's headline
    # defect class living inside the script that exists to prevent it.
    # tests/test_verify_script.py lifts this function out and drives it with an absent binary,
    # so everything it needs is defined INSIDE it — a function whose verdict depended on a
    # constant elsewhere in the file would be a function the test could only approximate.
    # A LEG IS MANY COMMANDS, AND THE OUTCOME WAS RECORDED PER LEG. `$LASTEXITCODE` is
    # cleared once here, so `Established` answered only "did ANYTHING in this whole leg set
    # an exit code" — and a command that vanished MID-leg left the previous command's zero
    # standing for the catch to read. Measured on this function: a body running an
    # interpreter that exits 0 and THEN an absent binary recorded ExitCode 0 / PASS /
    # Established True, while a body whose only statement was the absent binary recorded 253
    # / FAIL. Leg 3 is the exposed one: after `& $python -m build` every remaining command
    # runs on a CONSTRUCTED path ($cleanPython, $cleanArmature), and those paths being absent
    # IS the defect that leg exists to catch — a wheel that installs but creates no console
    # script makes `& $cleanArmature check` raise, the catch reads pip's zero, and the leg
    # reports PASS with `leg raised:` printed in red above a green summary line.
    #
    # So a RAISED body establishes no outcome, whatever $LASTEXITCODE currently holds. The
    # commands after the one that raised did not run, and a leg is a claim about all of them.
    #
    # AND A NON-ZERO EXIT MID-LEG IS NOT A RAISE. Measured at the wave-8 merge on this exact
    # function: a body running a command that exits 7 and THEN one that exits 0 recorded 0 /
    # PASS, because `$LASTEXITCODE` is whatever the LAST command left. The absent-binary
    # case above raises; a plain non-zero exit does not. So, inside the body, a native
    # command's non-zero exit is promoted to a terminating error (PowerShell 7.4+:
    # `$PSNativeCommandUseErrorActionPreference` with `$ErrorActionPreference = 'Stop'`),
    # caught here, and RECORDED as that command's own code — the leg stops at the first
    # command that failed, which is the claim a leg makes about all of its commands.
    $NO_OUTCOME = 253
    $global:LASTEXITCODE = $null
    $code = $null
    $raised = $false
    $ErrorActionPreference = 'Stop'
    $PSNativeCommandUseErrorActionPreference = $true
    try {
        & $Body
        $code = $global:LASTEXITCODE
    } catch [System.Management.Automation.NativeCommandExitException] {
        $code = $_.Exception.ExitCode
        Write-Host "  command exited $code : $($_.Exception.Message)" -ForegroundColor Red
    } catch {
        Write-Host "  leg raised: $($_.Exception.Message)" -ForegroundColor Red
        $raised = $true
    }
    $established = (-not $raised) -and ($null -ne $code)
    if (-not $established) { $code = $NO_OUTCOME }

    $sw.Stop()
    $script:results.Add([pscustomobject]@{
        Leg         = $Name
        ExitCode    = $code
        Outcome     = if ($code -eq 0) { 'PASS' } else { 'FAIL' }
        Established = $established
        Raised      = $raised
        Seconds     = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    })
}

if (-not (Test-Path $python)) {
    Write-Host "ANDON: no interpreter at $python" -ForegroundColor Red
    Write-Host "The suite runs on the repo venv. Create it, or point CI's python at this tree."
    exit 2
}

# The legs that shell out to node and npm halt up front rather than discovering it mid-run,
# the same way the missing interpreter does. Only the tools the SELECTED legs need are
# required, so `-NoSite -NoPackage` on a box with no npm is still a legitimate partial run.
#
# LEG 3 NEEDS BOTH, and asked for `node` alone until 2026-09-04. It gained the npm clean room
# in wave 10 -- `npm pack --silent` and `npm install --prefix $npmroom` below -- and this list
# did not move with it, while the guard that pins the clause asserted only that `node` was
# named. So `pwsh verify.ps1 -NoSite` on a box with node and no npm walked past the halt, ran
# both pytest legs and the whole pip-install / build / twine / clean-venv / wheel-probe
# sequence, and died at `npm pack` with a CommandNotFoundException -- recorded honestly as
# `FAIL (the leg established no outcome)`, but after paying the cost this halt exists to
# avoid. `tests/test_verify_script.py` now DERIVES the requirement instead of naming it: it
# reads the external commands each leg's body invokes out of PowerShell's own parser and
# holds this list to them under all four flag combinations, so a leg that starts shelling out
# to a third tool moves the requirement with it.
$needed = @()
if (-not $NoPackage) { $needed += @('node', 'npm') }
if (-not $NoSite) { $needed += @('node', 'npm') }
$absent = @($needed | Sort-Object -Unique | Where-Object {
    -not (Get-Command $_ -ErrorAction SilentlyContinue)
})
if ($absent.Count -gt 0) {
    Write-Host "ANDON: not on PATH: $($absent -join ', ')" -ForegroundColor Red
    Write-Host "The launcher self-test and the site build shell out to these. Install them, or"
    Write-Host "skip those legs deliberately with -NoPackage / -NoSite — a run that could not"
    Write-Host "start a leg is not a run that passed it."
    exit 2
}

Invoke-Leg -Name 'tests' -Body {
    & $python -m pytest $(Join-Path $repo 'tests') -q
}

Invoke-Leg -Name 'tests under -O (gates must still raise)' -Body {
    $prior = $env:PYTHONOPTIMIZE
    $env:PYTHONOPTIMIZE = '1'
    try { & $python -O -m pytest $(Join-Path $repo 'tests') -q }
    finally { $env:PYTHONOPTIMIZE = $prior }
}

if ($NoPackage) {
    Write-Host ''
    Write-Host '──────── package build — SKIPPED (-NoPackage)' -ForegroundColor Yellow
} else {
    Invoke-Leg -Name 'package build (wheel + sdist + twine + two clean installs + launcher)' -Body {
        Push-Location $repo
        try {
            # The toolchain CI pins, installed here for the same reason it is pinned there:
            # `build` and `twine` are what PRODUCE the artifact, and this leg built with
            # whatever the repo venv happened to hold. Measured 2026-09-04: the venv held
            # build 1.5.0 and twine 7.0.0 — inside CI's window, so the divergence was latent,
            # which is the state in which nobody notices it. A `pip install -U build` past 2.0
            # on the rig would make this leg select sdist contents differently from CI, and a
            # green local run would then assert something CI never ran — precisely the
            # equivalence the DESCRIPTION sells. The specifiers are read out of
            # `.github/actions/clean-room/action.yml` by
            # `tests/test_verify_script.py::test_verify_builds_the_artifact_with_the_toolchain_the_clean_room_action_pins`,
            # so raising either constraint there moves this line with it.
            # `trove-classifiers` joins them for the classifier gate below, under the
            # action's specifier character for character. It carries a CalVer-year ceiling
            # for the reason the action's comment records: it was written floor-only first,
            # and `test_every_tool_that_makes_or_moves_the_artifact_is_bounded_from_above`
            # named it here as well as in both workflows — a data set resolved fresh on the
            # day is no more verified than a tool resolved fresh on the day.
            & $python -m pip install --quiet 'build>=1.5,<2' 'twine>=7,<8' 'trove-classifiers>=2026.6.1.19,<2027'
            if ($LASTEXITCODE -ne 0) { return }

            # THE LEG JUDGES WHAT THIS RUN BUILT, AND NOTHING ELSE. `python -m build` does
            # not clear `dist/`, and neither did this leg: its only `Remove-Item` calls were
            # the two scratch rooms and the npm tarball. Measured on the main checkout
            # 2026-09-04, `E:\AI\armature\dist` held `armature_studio-0.2.1-py3-none-any.whl`
            # and `armature_studio-0.2.1.tar.gz` (mtime 2026-08-15) beside the 0.3.0 pair, so
            # `twine check dist\*` issued its verdict over FOUR files, two of them a version
            # published three weeks earlier -- a stale or half-written archive there turns the
            # leg red for a reason that has nothing to do with the commit, which is the flake
            # class `.github/actions/npm-clean-room/action.yml:42-49` calls "the bad kind". CI
            # reproduces neither half (fresh checkout, empty `dist/`), so the two
            # implementations of one leg behaved differently on the same command.
            #
            # AND THE INVARIANT IS ESTABLISHED, NOT ASSUMED. The clear below suppresses its
            # own failure: the explicit `-ErrorAction SilentlyContinue` overrides the
            # `$ErrorActionPreference = 'Stop'` `Invoke-Leg` sets, and nothing between the
            # clear and `twine check` asked whether the directory was actually empty. The two
            # artifacts are selected BY NAME below, which protects the two clean rooms -- but
            # `twine check dist\*` and the classifier gate both range over `dist\*` and would
            # still issue their verdicts over a file this run did not build. Measured on
            # `e8263a3` under pwsh 7.6.5 with `$ErrorActionPreference = 'Stop'` and
            # `$PSNativeCommandUseErrorActionPreference = $true` set: `Remove-Item
            # <held-open file> -Recurse -Force -ErrorAction SilentlyContinue` raised no
            # terminating error, left `$LASTEXITCODE` null, recorded one object in `$Error`
            # that nothing reads, and both stale files remained on disk. The flag stays -- a
            # locked file is not a reason to halt before the check that would name it -- and
            # the CHECK is the fix, in the by-name refusal's own shape.
            # `tests/test_verify_script.py::test_leg_three_refuses_a_dist_it_could_not_clear`
            # lifts this block out and drives it against a file another process holds open.
            $dist = Join-Path $repo 'dist'
            if (Test-Path $dist) {
                Remove-Item (Join-Path $dist '*') -Recurse -Force -ErrorAction SilentlyContinue
                $left = @(Get-ChildItem $dist -Force -ErrorAction SilentlyContinue)
                if ($left.Count -gt 0) {
                    Write-Host "  dist/ could not be cleared; $($left.Count) item(s) remain:" -ForegroundColor Red
                    $left | ForEach-Object { Write-Host "    $($_.Name)" -ForegroundColor Red }
                    Write-Host '  every verdict below is a claim about what THIS run built; refusing.' -ForegroundColor Red
                    $global:LASTEXITCODE = 1
                    return
                }
            }

            # The two filenames this run must produce, read out of the manifest rather than
            # globbed. The selection was `Get-ChildItem -Filter '*.whl' | Sort-Object
            # LastWriteTime | Select-Object -Last 1` -- the wheel the clean room installed and
            # probed was chosen BY TIMESTAMP and never compared against `project.version`.
            # Measured on a scratch dist holding two wheels, the newer mtime on the older
            # version: that expression returned `armature_studio-0.2.1-py3-none-any.whl`. The
            # version is read the way `release.yml`'s tag gate reads it, and the distribution
            # half is PEP 503/427 normalisation of `project.name`.
            $meta = & $python -c "import re,tomllib;p=tomllib.load(open('pyproject.toml','rb'))['project'];print(re.sub(r'[-_.]+','_',p['name']).lower());print(p['version'])"
            if ($LASTEXITCODE -ne 0) { return }
            $distName = $meta[0]
            $version = $meta[1]

            & $python -m build
            if ($LASTEXITCODE -ne 0) { return }
            & $python -m twine check (Join-Path $repo 'dist\*')
            if ($LASTEXITCODE -ne 0) { return }

            # Refused BY NAME when an expected artifact is absent -- the same shape as the
            # "no wheel in dist/ after the build" refusal this replaces, and now covering both
            # halves: a build that renames or drops either one halts here rather than falling
            # through to whatever the directory happens to hold.
            $wheelPath = Join-Path $dist "$distName-$version-py3-none-any.whl"
            $sdistPath = Join-Path $dist "$distName-$version.tar.gz"
            foreach ($expected in @($wheelPath, $sdistPath)) {
                if (-not (Test-Path $expected)) {
                    Write-Host "  the build produced no $(Split-Path $expected -Leaf); dist/ holds:" -ForegroundColor Red
                    Get-ChildItem $dist -ErrorAction SilentlyContinue |
                        ForEach-Object { Write-Host "    $($_.Name)" -ForegroundColor Red }
                    $global:LASTEXITCODE = 1
                    return
                }
            }

            # THE CLASSIFIER GATE, and it is the SAME FILE the release gate runs -- not a
            # second implementation of it. `twine check` two commands up validates metadata
            # STRUCTURE, not classifier MEMBERSHIP: measured 2026-09-04 on a `git archive`
            # copy of this tree with `Topic :: Scientific :: Image Processing` (the row PyPI
            # 400'd this project's first upload on) added back, the build produced both
            # artifacts with no warning and `twine check` printed PASSED for each and exited
            # 0. This script's DESCRIPTION equates a green local run to a green CI run; the
            # release gate calls `.github/actions/clean-room/classifier_gate.py` from its own
            # action and so does this line, so the equivalence is a shared text rather than a
            # claim. The sdist room three paragraphs down is in this script BECAUSE that
            # equivalence was once asserted over a leg the action had and this one did not.
            & $python (Join-Path $repo '.github/actions/clean-room/classifier_gate.py') $dist
            if ($LASTEXITCODE -ne 0) { return }

            $binDir = if ($IsWindows -eq $false) { 'bin' } else { 'Scripts' }
            $exe = if ($IsWindows -eq $false) { '' } else { '.exe' }

            # THE SDIST ROOM, mirroring `.github/actions/clean-room/action.yml:70-72` line for
            # line and in that action's order (sdist first, then the wheel). Wave 14 added it
            # there -- three artifacts leave this repository and the sdist was the one nothing
            # built from -- and this script, whose DESCRIPTION claims the legs are "the same
            # ones ci.yml runs, in the same order and with the same meaning", did not move
            # with it: `grep -n 'tar.gz' verify.ps1` returned 0 hits while leg 3's own name
            # already said "sdist". `pip install <sdist>` runs the backend under build
            # isolation, so it exercises `[build-system].requires` and MANIFEST.in the way a
            # downstream packager does, which installing a wheel cannot; its OWN venv, because
            # a wheel already present in the other room would satisfy the requirement without
            # the archive ever being opened. `--no-deps`, and `modules --json` rather than the
            # wheel room's full probe, for the action's stated reason: the question here is
            # whether the ARCHIVE builds and the command it installs runs, and the room below
            # already resolves and exercises the runtime dependency set.
            $sdistRoom = Join-Path ([System.IO.Path]::GetTempPath()) "armature-cleanroom-sdist-$([guid]::NewGuid().ToString('N').Substring(0,8))"
            try {
                & $python -m venv $sdistRoom
                if ($LASTEXITCODE -ne 0) { return }
                $sdistPython = Join-Path $sdistRoom "$binDir\python$exe"
                $sdistArmature = Join-Path $sdistRoom "$binDir\armature$exe"
                & $sdistPython -m pip install --no-deps $sdistPath
                if ($LASTEXITCODE -ne 0) { return }
                & $sdistPython -m pip freeze
                if ($LASTEXITCODE -ne 0) { return }
                if (-not (Test-Path $sdistArmature)) {
                    Write-Host "  the sdist install provides no armature command at $sdistArmature" -ForegroundColor Red
                    $global:LASTEXITCODE = 1
                    return
                }
                & $sdistArmature modules --json > $null
                if ($LASTEXITCODE -ne 0) { return }
            } finally {
                if (Test-Path $sdistRoom) {
                    Remove-Item $sdistRoom -Recurse -Force -ErrorAction SilentlyContinue
                }
            }

            # ci.yml's clean-room leg, mirrored. The wheel is installed into a venv that has
            # nothing else in it and the command is run from THAT install, never from the
            # checkout — a module missing from the wheel otherwise passes because the source
            # tree is sitting right there. The probe calls the three functions whose imports
            # are function-local (`draw_body` and `draw_hand` reach cv2 and matplotlib,
            # `mean_consecutive_frame_difference` reaches PIL): `armature check` executes no
            # function body, so it printed "all modules resolved" and exited 0 on a wheel
            # that raised ModuleNotFoundError on first call.
            $cleanroom = Join-Path ([System.IO.Path]::GetTempPath()) "armature-cleanroom-$([guid]::NewGuid().ToString('N').Substring(0,8))"
            try {
                & $python -m venv $cleanroom
                if ($LASTEXITCODE -ne 0) { return }
                $cleanPython = Join-Path $cleanroom "$binDir\python$exe"
                $cleanArmature = Join-Path $cleanroom "$binDir\armature$exe"
                # WHAT THIS ROOM RESOLVED, STATED -- `--quiet` used to remove the one line
                # that said. This install carries no `--no-deps`, so numpy, cv2, pillow and
                # matplotlib are resolved FRESH from the index at the unbounded specifiers
                # `pyproject.toml` declares (that is deliberate: it is a user's experience of
                # `pip install armature-studio`, and the thing this room exercises). Measured
                # on the rig 2026-09-04, `pip install --quiet` emitted nothing at all while
                # the same install without the flag printed `Successfully installed
                # armature-studio-0.3.0`. `pip freeze` states the whole resolved set, so a
                # dependency-day break and a wheel defect are two different reds rather than
                # one silent one. `.github/actions/clean-room/action.yml` carries the same
                # two lines.
                & $cleanPython -m pip install $wheelPath
                if ($LASTEXITCODE -ne 0) { return }
                & $cleanPython -m pip freeze
                if ($LASTEXITCODE -ne 0) { return }
                & $cleanArmature check
                if ($LASTEXITCODE -ne 0) { return }
                & $cleanArmature modules --json > $null
                if ($LASTEXITCODE -ne 0) { return }

                # THE PROBE IS THE SAME FILE THE RELEASE GATE RUNS, not a here-string
                # copy of it. It was a copy: `.github/actions/clean-room/action.yml`'s
                # heredoc and this here-string were two implementations of one probe, and
                # NO census could see this one -- `tests/test_ci_workflows.py`'s lazy-import
                # guard derives the leg from `_all_run_scripts()`, which walks `.github/`
                # only. Measured on `e8263a3` in a `git archive` scratch copy with
                # `aapose.draw_body`, `aapose.draw_hand` and
                # `donor_gate.mean_consecutive_frame_difference` replaced by `pass` inside
                # THIS here-string alone: `tests/test_verify_script.py` +
                # `tests/test_ci_workflows.py` = 256 passed. The two copies were still
                # code-identical at that point, so this is drift that had not happened yet
                # -- the classifier gate two paragraphs down was made a FILE for exactly
                # this reason, and the probe stayed duplicated. One text, two callers.
                $probe = Join-Path $repo '.github/actions/clean-room/lazy_import_probe.py'
                & $cleanPython $probe
                if ($LASTEXITCODE -ne 0) { return }
            } finally {
                if (Test-Path $cleanroom) {
                    Remove-Item $cleanroom -Recurse -Force -ErrorAction SilentlyContinue
                }
            }

            Push-Location (Join-Path $repo 'npm')
            try {
                node bin\armature.mjs --node-selftest
                if ($LASTEXITCODE -ne 0) { return }

                # ci.yml's npm clean room (`.github/actions/npm-clean-room`), mirrored — the
                # npm half of the leg above. The self-test on the line before runs the
                # launcher out of the CHECKOUT and consults neither `bin`, `files`, nor the
                # tarball; measured 2026-09-04 with the `bin` map pointed at a typo, that
                # self-test passed, `npm pack` passed, the install reported `added 1 package`,
                # and no `armature` command existed anywhere. The package is published
                # irreversibly, so the command it installs is what has to be run.
                Get-ChildItem -Path . -Filter '*.tgz' -ErrorAction SilentlyContinue |
                    Remove-Item -Force -ErrorAction SilentlyContinue
                npm pack --silent
                if ($LASTEXITCODE -ne 0) { return }
                $tarball = Get-ChildItem -Path . -Filter '*.tgz' |
                    Sort-Object LastWriteTime | Select-Object -Last 1
                if (-not $tarball) {
                    Write-Host '  npm pack produced no tarball' -ForegroundColor Red
                    $global:LASTEXITCODE = 1
                    return
                }
                $npmroom = Join-Path ([System.IO.Path]::GetTempPath()) "armature-npmroom-$([guid]::NewGuid().ToString('N').Substring(0,8))"
                try {
                    New-Item -ItemType Directory -Path $npmroom -Force | Out-Null
                    npm install --prefix $npmroom $tarball.FullName
                    if ($LASTEXITCODE -ne 0) { return }
                    $shimName = if ($IsWindows -eq $false) { 'armature' } else { 'armature.cmd' }
                    $shim = Join-Path $npmroom (Join-Path 'node_modules/.bin' $shimName)
                    if (-not (Test-Path $shim)) {
                        Write-Host "  the installed package provides no armature command at $shim" -ForegroundColor Red
                        Write-Host '  check bin/ and files/ in npm/package.json' -ForegroundColor Red
                        $global:LASTEXITCODE = 1
                        return
                    }
                    & $shim --node-selftest
                    if ($LASTEXITCODE -ne 0) { return }
                } finally {
                    if (Test-Path $npmroom) {
                        Remove-Item $npmroom -Recurse -Force -ErrorAction SilentlyContinue
                    }
                    Remove-Item $tarball.FullName -Force -ErrorAction SilentlyContinue
                }
            } finally { Pop-Location }
        } finally { Pop-Location }
    }
}

if ($NoSite) {
    Write-Host ''
    Write-Host '──────── site build — SKIPPED (-NoSite)' -ForegroundColor Yellow
} else {
    Invoke-Leg -Name 'site build (audit + npm ci + build)' -Body {
        Push-Location (Join-Path $repo 'site')
        try {
            # ci.yml's dependency scan, verbatim, and in ci.yml's order: BEFORE the
            # install. `npm ci` runs every lifecycle script in the resolved tree, so a scan
            # that follows it reports a compromised dependency that has already run — here,
            # on the rig. `--package-lock-only` reads the committed lockfile and needs no
            # node_modules. site/ is the repo's only dependency manifest, so this is the
            # whole scannable surface; `high` is the studio's threshold. Missing locally
            # until the legs were enumerated against ci.yml, which meant a green local run
            # could still be a lockfile CI then rejected.
            npm audit --package-lock-only --audit-level=high
            if ($LASTEXITCODE -ne 0) { return }
            npm ci
            if ($LASTEXITCODE -ne 0) { return }
            npm run build
        } finally { Pop-Location }
    }
}

Write-Host ''
Write-Host '════════ verify' -ForegroundColor Cyan

# WHICH INTERPRETER THE CLAIM WAS MADE ON. The DESCRIPTION equates a green run here with a
# green CI run; that holds for the legs and their order and NOT for the interpreter. Every
# Python leg above ran on the venv interpreter, whose version CI does not necessarily run --
# measured 2026-09-04, this rig's venv is a version above the top classifier pyproject
# declares, and ci.yml runs neither end of it here. So the run states it rather than leaving
# the reader to assume equivalence: a version-specific red on a runner is then one line away
# from being recognised as an interpreter difference instead of a change to debug.
#
# The version is only reported when it can be READ. `& $python --version` on a file that is
# not a working interpreter writes a message and leaves whatever `$LASTEXITCODE` already
# held, so the output is matched against the shape a version has rather than printed
# whatever came back -- a line that quoted an error message under the word "interpreter"
# would be a placeholder shaped like evidence.
$interpreter = "$python (version unreadable)"
try {
    $reported = (& $python --version 2>&1 | Out-String).Trim()
    if ($reported -match '^Python\s+\S+') { $interpreter = "$python -- $reported" }
} catch { }
Write-Host ("  interpreter: {0}" -f $interpreter)

# WHICH NODE THE CLAIM WAS MADE ON -- the SECOND runtime axis, and the one that moved without
# this block. Leg 3 runs `node bin\armature.mjs --node-selftest`, `npm pack --silent`,
# `npm install --prefix` and the installed shim; leg 4 runs `npm audit`, `npm ci` and
# `npm run build`. All of them use whatever single node is on PATH. ci.yml's `launcher` job
# runs the same two commands across `node-version: [18, 22]` BECAUSE `npm/package.json`
# declares `"node": ">=18"` and nothing ran 18 -- so a green run here is a claim about one
# node out of the two CI exercises, and the DESCRIPTION named only the Python axis. That is
# the reading error one tool over: "all legs passed" read as "CI will pass", the operator
# then debugging the change instead of the runtime.
#
# Read the same defensive way as the interpreter above: matched against the shape a version
# has, never echoed raw, because a line quoting an error message under the word "node" would
# be a placeholder shaped like evidence. When BOTH node-using legs were skipped, this says
# that rather than reporting a runtime nothing ran on.
$nodeReport = 'not exercised (-NoPackage and -NoSite)'
$npmReport = 'not exercised (-NoPackage and -NoSite)'
if (-not ($NoPackage -and $NoSite)) {
    $nodeReport = '(version unreadable)'
    try {
        $said = (& node --version 2>&1 | Out-String).Trim()
        if ($said -match '^v\d+\.\d+\.\d+') { $nodeReport = $Matches[0] }
    } catch { }
    $npmReport = '(version unreadable)'
    try {
        $said = (& npm --version 2>&1 | Out-String).Trim()
        if ($said -match '^\d+\.\d+\.\d+') { $npmReport = $Matches[0] }
    } catch { }
}
Write-Host ("  node:        {0}" -f $nodeReport)
Write-Host ("  npm:         {0}" -f $npmReport)
Write-Host '  (the legs and their order are ci.yml''s; the runtimes are this rig''s venv and PATH)'
Write-Host ''

foreach ($r in $results) {
    $verdict = if ($r.Outcome -eq 'PASS') {
        'PASS'
    } elseif ($r.Raised) {
        'FAIL (a command in the leg raised — the commands after it never ran, so the leg established no outcome)'
    } elseif (-not $r.Established) {
        'FAIL (the leg established no outcome — nothing it shells out to ran)'
    } else {
        "FAIL (exit $($r.ExitCode))"
    }
    $colour = if ($r.Outcome -eq 'PASS') { 'Green' } else { 'Red' }
    Write-Host ("  {0,-52} {1,7}s  {2}" -f $r.Leg, $r.Seconds, $verdict) -ForegroundColor $colour
}

$failed = @($results | Where-Object { $_.Outcome -ne 'PASS' })
if ($failed.Count -gt 0) {
    Write-Host ''
    Write-Host "REFUSED — $($failed.Count) leg(s) failed." -ForegroundColor Red
    exit 1
}

if ($NoSite -or $NoPackage) {
    $skipped = @()
    if ($NoPackage) { $skipped += 'the package build' }
    if ($NoSite) { $skipped += 'the site build' }
    Write-Host ''
    Write-Host "All run legs passed. NOT a full verify — $($skipped -join ' and ') was skipped." -ForegroundColor Yellow
    exit 0
}

Write-Host ''
Write-Host 'All legs passed.' -ForegroundColor Green
exit 0
