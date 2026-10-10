# Dot-source this to get $RepoRoot, $VenvDir and $VenvPython.
# The venv is kept out of OneDrive-synced folders: syncing torch (~1 GB) causes file locks and slow installs.
$RepoRoot = Split-Path -Parent $PSScriptRoot
if ($env:CROWDPULSE_VENV) {
    $VenvDir = $env:CROWDPULSE_VENV
} elseif ($env:OneDrive -and $RepoRoot.StartsWith($env:OneDrive, [StringComparison]::OrdinalIgnoreCase)) {
    # Not %LOCALAPPDATA%: Microsoft Store Python silently redirects writes there into its app sandbox.
    $VenvDir = Join-Path $env:USERPROFILE '.venvs\crowdpulse'
} else {
    $VenvDir = Join-Path $RepoRoot '.venv'
}
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
