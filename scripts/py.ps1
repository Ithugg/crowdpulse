# Runs the project's venv Python from the repo root:  .\scripts\py.ps1 scripts\m1_count.py --source 0
. "$PSScriptRoot\_venv.ps1"
if (-not (Test-Path $VenvPython)) { throw 'venv missing. Run scripts\setup.ps1 first.' }
Push-Location $RepoRoot
try { & $VenvPython @args } finally { Pop-Location }
exit $LASTEXITCODE
