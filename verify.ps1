<#
.SYNOPSIS
  One command that runs everything CI runs, plus the site build, and refuses on any leg.

.DESCRIPTION
  The legs are the same ones `.github/workflows/ci.yml` runs, in the same order and with
  the same meaning, so a green local run and a green CI run are the same claim:

    1. the test suite on the repo venv
    2. the test suite again under `-O` with PYTHONOPTIMIZE=1 — this leg is not a
       duplicate. A gate implemented as an `assert` is DELETED by the optimizer, and 87
       of facet's andons turned out to be removable by an environment variable. Running
       the suite a second time under `-O` is what proves this repo's gates raise.
    3. the package build — the wheel and sdist, `twine check` on the metadata, the wheel
       installed into a CLEAN venv and run from THAT install, and the launcher's own
       self-test. Added at v0.2.0, when this repo started publishing: a package that fails
       to build is a release that fails at the registry, and finding that out from a
       release job is finding it out too late to take back. The clean-install half was
       missing until it was enumerated against ci.yml — it is the leg whose whole point is
       catching a wheel that does not work, and it probes the function-local dependencies
       (`draw_body`, `draw_hand`, `mean_consecutive_frame_difference`) because `armature
       check` executes no function body and was green on a wheel that could not run.
    4. the site build: `npm ci`, then `npm audit --audit-level=high` — the dependency scan,
       also missing until it was enumerated — then `npm run build`, which is what GitHub
       Pages deploys.

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
  Skip leg 3. Useful when nothing packaging-related changed; it shells out to `build` and
  `twine`, which a bare checkout may not have installed.

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
    $NO_OUTCOME = 253
    $global:LASTEXITCODE = $null
    $code = $null
    $raised = $false
    try {
        & $Body
        $code = $global:LASTEXITCODE
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
# required, so `-NoSite` on a box with no npm is still a legitimate partial run.
$needed = @()
if (-not $NoPackage) { $needed += 'node' }
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
    Invoke-Leg -Name 'package build (wheel + sdist + twine + clean install + launcher)' -Body {
        Push-Location $repo
        try {
            & $python -m build
            if ($LASTEXITCODE -ne 0) { return }
            & $python -m twine check (Join-Path $repo 'dist\*')
            if ($LASTEXITCODE -ne 0) { return }

            # ci.yml's clean-room leg, mirrored. The wheel is installed into a venv that has
            # nothing else in it and the command is run from THAT install, never from the
            # checkout — a module missing from the wheel otherwise passes because the source
            # tree is sitting right there. The probe calls the three functions whose imports
            # are function-local (`draw_body` and `draw_hand` reach cv2 and matplotlib,
            # `mean_consecutive_frame_difference` reaches PIL): `armature check` executes no
            # function body, so it printed "all modules resolved" and exited 0 on a wheel
            # that raised ModuleNotFoundError on first call.
            $cleanroom = Join-Path ([System.IO.Path]::GetTempPath()) "armature-cleanroom-$([guid]::NewGuid().ToString('N').Substring(0,8))"
            $binDir = if ($IsWindows -eq $false) { 'bin' } else { 'Scripts' }
            $exe = if ($IsWindows -eq $false) { '' } else { '.exe' }
            try {
                & $python -m venv $cleanroom
                if ($LASTEXITCODE -ne 0) { return }
                $cleanPython = Join-Path $cleanroom "$binDir\python$exe"
                $cleanArmature = Join-Path $cleanroom "$binDir\armature$exe"
                $wheel = Get-ChildItem (Join-Path $repo 'dist') -Filter '*.whl' |
                    Sort-Object LastWriteTime | Select-Object -Last 1
                if (-not $wheel) {
                    Write-Host '  no wheel in dist/ after the build' -ForegroundColor Red
                    $global:LASTEXITCODE = 1
                    return
                }
                & $cleanPython -m pip install --quiet $wheel.FullName
                if ($LASTEXITCODE -ne 0) { return }
                & $cleanArmature check
                if ($LASTEXITCODE -ne 0) { return }
                & $cleanArmature modules --json > $null
                if ($LASTEXITCODE -ne 0) { return }

                $probe = Join-Path $cleanroom 'clean_room_probe.py'
                @'
import os, tempfile
import numpy as np
from armature_core import aapose, donor_gate, pngio

if "site-packages" not in aapose.__file__.replace("\\", "/"):
    raise SystemExit("clean-room probe imported the source tree: " + aapose.__file__)

canvas = aapose.blank_canvas(64, 64)
body = np.zeros((aapose.KEYPOINT_COUNT, 3)); body[:, :2] = 32.0; body[:, 2] = 1.0
aapose.draw_body(canvas, body)
hand = np.zeros((aapose.HAND_KEYPOINT_COUNT, 3)); hand[:, :2] = 32.0; hand[:, 2] = 1.0
aapose.draw_hand(canvas, hand)

frames = tempfile.mkdtemp()
paths = []
for i in range(2):
    p = os.path.join(frames, "%05d.png" % i)
    pngio.write_png(p, np.full((8, 8, 3), i * 40, dtype=np.uint8))
    paths.append(p)
donor_gate.mean_consecutive_frame_difference(paths)
print("clean room: draw_body, draw_hand and mean_consecutive_frame_difference all ran")
'@ | Set-Content -Path $probe -Encoding utf8
                & $cleanPython $probe
                if ($LASTEXITCODE -ne 0) { return }
            } finally {
                if (Test-Path $cleanroom) {
                    Remove-Item $cleanroom -Recurse -Force -ErrorAction SilentlyContinue
                }
            }

            Push-Location (Join-Path $repo 'npm')
            try { node bin\armature.mjs --node-selftest } finally { Pop-Location }
        } finally { Pop-Location }
    }
}

if ($NoSite) {
    Write-Host ''
    Write-Host '──────── site build — SKIPPED (-NoSite)' -ForegroundColor Yellow
} else {
    Invoke-Leg -Name 'site build (npm ci + audit + build)' -Body {
        Push-Location (Join-Path $repo 'site')
        try {
            npm ci
            if ($LASTEXITCODE -ne 0) { return }
            # ci.yml's dependency scan, verbatim. site/ is the repo's only dependency
            # manifest, so this is the whole scannable surface; `high` is the studio's
            # threshold. Missing locally until the legs were enumerated against ci.yml, which
            # meant a green local run could still be a lockfile CI then rejected.
            npm audit --audit-level=high
            if ($LASTEXITCODE -ne 0) { return }
            npm run build
        } finally { Pop-Location }
    }
}

Write-Host ''
Write-Host '════════ verify' -ForegroundColor Cyan
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
