# Starts CrowdPulse: one process serving the dashboard + WebSocket at http://localhost:8000
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_venv.ps1"

if (-not (Test-Path $VenvPython)) { throw 'Not set up yet. Run scripts\setup.ps1 first.' }

$Frontend = Join-Path $RepoRoot 'frontend'
if (-not (Test-Path (Join-Path $Frontend 'dist\index.html'))) {
    Write-Host 'Building dashboard...'
    Push-Location $Frontend
    try {
        if (-not (Test-Path 'node_modules')) { npm install; if ($LASTEXITCODE -ne 0) { throw 'npm install failed' } }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'frontend build failed' }
    } finally { Pop-Location }
}

$Port = if ($env:PORT) { $env:PORT } else { '8000' }
if (-not $NoBrowser) {
    # Open the dashboard once the server has had a moment to load the model.
    Start-Job -ScriptBlock { param($p) Start-Sleep 4; Start-Process "http://localhost:$p" } -ArgumentList $Port | Out-Null
}

Write-Host "CrowdPulse running at http://localhost:$Port  (Ctrl+C to stop)"
Push-Location $RepoRoot
try { & $VenvPython -m backend.main } finally { Pop-Location }
