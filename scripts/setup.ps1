# One-time setup: Python venv + dependencies (+ frontend build once it exists).
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_venv.ps1"

function Assert-Ok($what) {
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)" }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python not found. Install Python 3.11-3.13 from python.org (tick "Add to PATH") and re-run.'
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating venv at $VenvDir"
    python -m venv $VenvDir
    Assert-Ok 'venv creation'
}

& $VenvPython -m pip install --upgrade pip
Assert-Ok 'pip upgrade'
& $VenvPython -m pip install -r (Join-Path $RepoRoot 'requirements.txt')
Assert-Ok 'pip install'

New-Item -ItemType Directory -Force (Join-Path $RepoRoot 'media'), (Join-Path $RepoRoot 'models'), (Join-Path $RepoRoot 'runs') | Out-Null

$Frontend = Join-Path $RepoRoot 'frontend'
if (Test-Path (Join-Path $Frontend 'package.json')) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node.js not found. Install Node 20+ and re-run.' }
    Push-Location $Frontend
    try {
        npm install
        Assert-Ok 'npm install'
        npm run build
        Assert-Ok 'frontend build'
    } finally { Pop-Location }
}

Write-Host ''
Write-Host "Setup done. Python: $VenvPython"
Write-Host 'Try:  .\scripts\py.ps1 scripts\m1_count.py --help'
