param(
    [string]$EnvPython = (Join-Path $env:LOCALAPPDATA 'kaiwu-original\Scripts\python.exe'),
    [string]$WorkDir = (Join-Path $env:TEMP ('apmcm_repro_original_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))),
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$code = Join-Path $repo 'code'
$data = Join-Path $repo 'date'

if (-not (Test-Path -LiteralPath $EnvPython)) {
    throw "Environment python not found: $EnvPython"
}
if (-not (Test-Path -LiteralPath $code)) {
    throw "code directory not found: $code"
}
if (-not (Test-Path -LiteralPath $data)) {
    throw "date directory not found: $data (official CSVs are required)"
}
if ((Test-Path -LiteralPath $WorkDir) -and -not $Force) {
    throw "Work directory already exists: $WorkDir. Use -Force or pass a new -WorkDir."
}

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
Copy-Item -LiteralPath $code -Destination (Join-Path $WorkDir 'code') -Recurse -Force
Copy-Item -LiteralPath $data -Destination (Join-Path $WorkDir 'date') -Recurse -Force
foreach ($sub in 'results', 'models', 'figures') {
    New-Item -ItemType Directory -Path (Join-Path $WorkDir $sub) -Force | Out-Null
}

$log = Join-Path $WorkDir 'run.log'
$started = Get-Date
Push-Location $WorkDir
try {
    & $EnvPython 'code\run_all.py' 2>&1 | Tee-Object -FilePath $log
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($exitCode -ne 0) {
    throw "run_all.py failed with exit code $exitCode. See $log"
}

$elapsed = (Get-Date) - $started
Write-Host ""
Write-Host "Run finished in $([math]::Round($elapsed.TotalSeconds, 1)) s"
Write-Host "Work directory: $WorkDir"
Write-Host "Repository results were not modified. Compare, do not copy back."
Write-Host "SHA256 of key outputs:"
$targets = @(
    'results\final_answers.json',
    'results\FINAL_ANSWERS.md',
    'results\run_all.log',
    'results\submission_q1_holdout.csv',
    'results\submission_q2_top20.csv',
    'results\submission_q3_top20.csv',
    'code\predictions\pool_q2_phys.csv',
    'code\predictions\pool_q3_phys.csv'
)
foreach ($t in $targets) {
    $p = Join-Path $WorkDir $t
    if (Test-Path -LiteralPath $p) {
        $h = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()
        Write-Host ("  {0}  {1}" -f $h, $t)
    } else {
        Write-Host ("  MISSING  {0}" -f $t)
    }
}
