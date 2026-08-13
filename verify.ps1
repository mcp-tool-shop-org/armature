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
    3. the site build (`npm ci` + `npm run build`), which is what GitHub Pages deploys

  Every leg runs even if an earlier one fails, so one invocation reports the whole
  picture rather than the first thing to break. The exit code is 0 only if all legs pass.

.PARAMETER NoSite
  Skip leg 3. Useful when only Python changed and node_modules is cold; the site leg is
  the slow one. A run with -NoSite is NOT a full verify and says so in its summary.

.EXAMPLE
  pwsh -NoProfile -File .\verify.ps1
  pwsh -NoProfile -File .\verify.ps1 -NoSite
#>
[CmdletBinding()]
param(
    [switch]$NoSite
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
    & $Body
    $code = $LASTEXITCODE
    $sw.Stop()
    $script:results.Add([pscustomobject]@{
        Leg      = $Name
        ExitCode = $code
        Seconds  = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    })
}

if (-not (Test-Path $python)) {
    Write-Host "ANDON: no interpreter at $python" -ForegroundColor Red
    Write-Host "The suite runs on the repo venv. Create it, or point CI's python at this tree."
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

if ($NoSite) {
    Write-Host ''
    Write-Host '──────── site build — SKIPPED (-NoSite)' -ForegroundColor Yellow
} else {
    Invoke-Leg -Name 'site build' -Body {
        Push-Location (Join-Path $repo 'site')
        try {
            npm ci
            if ($LASTEXITCODE -ne 0) { return }
            npm run build
        } finally { Pop-Location }
    }
}

Write-Host ''
Write-Host '════════ verify' -ForegroundColor Cyan
foreach ($r in $results) {
    $verdict = if ($r.ExitCode -eq 0) { 'PASS' } else { "FAIL (exit $($r.ExitCode))" }
    $colour = if ($r.ExitCode -eq 0) { 'Green' } else { 'Red' }
    Write-Host ("  {0,-40} {1,7}s  {2}" -f $r.Leg, $r.Seconds, $verdict) -ForegroundColor $colour
}

$failed = @($results | Where-Object { $_.ExitCode -ne 0 })
if ($failed.Count -gt 0) {
    Write-Host ''
    Write-Host "REFUSED — $($failed.Count) leg(s) failed." -ForegroundColor Red
    exit 1
}

if ($NoSite) {
    Write-Host ''
    Write-Host 'All run legs passed. NOT a full verify — the site build was skipped.' -ForegroundColor Yellow
    exit 0
}

Write-Host ''
Write-Host 'All legs passed.' -ForegroundColor Green
exit 0
