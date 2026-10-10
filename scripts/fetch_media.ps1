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

# The burned-in frame counter and sequence label sit at different places per clip (after scaling to 720p).
$Masks = @{
    'MOT20-02' = 'delogo=x=20:y=10:w=205:h=76,delogo=x=20:y=640:w=390:h=70'
    'MOT20-03' = 'delogo=x=30:y=12:w=225:h=84,delogo=x=30:y=628:w=455:h=72'
    'MOT20-05' = 'delogo=x=20:y=10:w=205:h=76,delogo=x=20:y=640:w=390:h=70'
}

foreach ($name in 'MOT20-02', 'MOT20-03', 'MOT20-05') {
    $out = Join-Path $Media "$name.mp4"
    if (Test-Path $out) { Write-Host "$name.mp4 already present"; continue }
    $webm = Join-Path $Raw "$name-raw.webm"
    Write-Host "Downloading $name..."
    curl.exe -sL -o $webm "https://motchallenge.net/sequenceVideos/$name-raw.webm"
    if ($LASTEXITCODE -ne 0) { throw "download of $name failed" }
    ffmpeg -v error -y -i $webm -an -vf "scale=-2:720,$($Masks[$name])" `
        -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p $out
    if ($LASTEXITCODE -ne 0) { throw "conversion of $name failed" }
    Write-Host "  -> $out"
}
# Festival parade clip (Pexels, already an MP4: no conversion needed)
$ade = Join-Path $Media 'ade_street.mp4'
if (-not (Test-Path $ade)) {
    Write-Host 'Downloading ade_street...'
    curl.exe -sL -A 'Mozilla/5.0' -o $ade 'https://videos.pexels.com/video-files/19300221/19300221-hd_1920_1080_25fps.mp4'
    if ($LASTEXITCODE -ne 0) { throw 'download of ade_street failed' }
}
# Festival plaza clip (Pexels): converted to 720p / 25 fps so the frame count matches the replay cache
$plaza = Join-Path $Media 'festival_plaza.mp4'
if (-not (Test-Path $plaza)) {
    Write-Host 'Downloading festival_plaza...'
    $src = Join-Path $Raw 'festival_plaza_src.mp4'
    curl.exe -sL -A 'Mozilla/5.0' -o $src 'https://videos.pexels.com/video-files/28834188/12490396_1920_1080_60fps.mp4'
    if ($LASTEXITCODE -ne 0) { throw 'download of festival_plaza failed' }
    ffmpeg -nostdin -v error -y -i $src -an -vf 'scale=-2:720,fps=25' -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p $plaza
    if ($LASTEXITCODE -ne 0) { throw 'conversion of festival_plaza failed' }
}
Write-Host 'Done.'
