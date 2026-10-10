# Backup way to get the demo clips: downloads them from motchallenge.net and converts them exactly as on
# the dev machine (720p H.264, burned-in sequence labels masked). Needs ffmpeg on PATH
# (winget install Gyan.FFmpeg). Copying the media\ folder from the dev machine is faster if you can.
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\fetch_media.ps1
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_venv.ps1"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw 'ffmpeg not found. Install it with: winget install Gyan.FFmpeg' }

$Media = Join-Path $RepoRoot 'media'
$Raw = Join-Path $Media 'raw'
New-Item -ItemType Directory -Force $Raw | Out-Null

foreach ($name in 'MOT20-02', 'MOT20-03', 'MOT20-05') {
    $out = Join-Path $Media "$name.mp4"
    if (Test-Path $out) { Write-Host "$name.mp4 already present"; continue }
    $webm = Join-Path $Raw "$name-raw.webm"
    Write-Host "Downloading $name..."
    curl.exe -sL -o $webm "https://motchallenge.net/sequenceVideos/$name-raw.webm"
    if ($LASTEXITCODE -ne 0) { throw "download of $name failed" }
    ffmpeg -v error -y -i $webm -an -vf 'scale=-2:720,delogo=x=20:y=10:w=205:h=76,delogo=x=20:y=640:w=390:h=70' `
        -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p $out
    if ($LASTEXITCODE -ne 0) { throw "conversion of $name failed" }
    Write-Host "  -> $out"
}
Write-Host 'Done.'
