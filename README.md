# CrowdPulse

**Real-time crowd-safety early warning from the cameras a venue already has.**

Crowd crushes build up over minutes, but staff usually see them too late. Ten people died at Astroworld (Houston, 2021) and more than 150 in Itaewon (Seoul, 2022). In both, dangerous density built up while cameras were pointed straight at it. CrowdPulse turns that footage into numbers staff can act on: how many people are in each zone, how dense it is, how fast it is rising, how long until it becomes dangerous, and what to do about it.

Built solo at **Hacklanta 2026** (theme: Music Festival) for the **Social Good track (Cox)**.

## What it does

1. **Counts people** in a live webcam or video feed with YOLOv8.
2. **Measures density per zone** (people per m²) for named zones such as "Gate 3 Entry" or "Main Floor", and colours each zone green, yellow or red.
3. **Predicts** when a zone will reach critical density from its trend over the last minute ("Main Floor critical in ~40 s").
4. **Writes a response plan with Gemini** the moment a zone turns red: who does what, in order, plus a PA announcement. The camera frame is sent along with the numbers, so the plan can refer to what is visible.
5. Shows it all on a **live operations dashboard**: video with detection boxes and a density heatmap, zone cards, an alert feed and the response plan.

## Run it (Windows)

You need **Python 3.11–3.13**, **Node.js 20+** and **Git**.

```powershell
git clone https://github.com/Ithugg/crowdpulse.git
cd crowdpulse
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Add the demo clips to `media/` (see [media/SOURCES.md](media/SOURCES.md), or run `scripts\fetch_media.ps1`, which needs ffmpeg). Then, for AI response plans, copy `.env.example` to `.env` and paste a free Gemini API key from <https://aistudio.google.com/apikey>. Without a key the app still runs and shows pre-written plans marked "Cached plan".

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

The dashboard opens at <http://localhost:8000>. No test credentials are needed.

### Demo controls

| Key | Action |
|---|---|
| `1` – `9` | Switch camera source instantly (webcam or a clip) |
| `R` | Restart the current clip |
| `P` | Generate a response plan for the densest zone |
| `B` / `H` | Toggle detection boxes / heatmap |

### Useful scripts

```powershell
.\scripts\py.ps1 scripts\m1_count.py --source 0                    # webcam in a plain OpenCV window
.\scripts\py.ps1 scripts\m1_count.py --source 0 --bench 100        # inference speed on this machine
.\scripts\py.ps1 scripts\precompute.py --source main_field --weights yolov8s.pt --imgsz 1280
```

## How it works

```
webcam / video ─► capture thread (always the newest frame)
                    └► YOLOv8 person detection
                         └► zone assignment ─► density = people / estimated m²
                              └► smoothing + green/yellow/red with hysteresis
                                   └► linear trend over 60 s ─► time until critical
                                        └► alerts ─► Gemini response plan (cached fallback)
FastAPI ── one WebSocket: JSON state + binary JPEG frames ──► React dashboard
```

- **Backend** (`backend/`): Python, FastAPI, OpenCV, Ultralytics YOLOv8. Everything runs locally in one process.
- **Frontend** (`frontend/`): React + Vite + Tailwind, built to static files and served by FastAPI.
- **Config** (`config/sources.yaml`): camera sources, zone polygons, estimated zone areas and thresholds.
- The WebSocket message format is defined in [backend/schemas.py](backend/schemas.py) and mirrored in [frontend/src/types.ts](frontend/src/types.ts).

## Honest limitations

- **Zone areas are estimates typed into a config file**, not a camera calibration. For the bundled test clips the areas are tuned so that each clip exercises every alert level; the test footage shows ordinary crowds, not real crush conditions. A real deployment would calibrate each camera once.
- **YOLOv8 undercounts very dense crowds** because people hide each other. A density-map crowd-counting model is the next step for packed scenes.
- A source can run in **replay mode** (badge shows `REPLAY`): detections computed offline with a larger model are played back in sync with the clip, so a CPU-only laptop can show a dense scene smoothly. The webcam and the other clips run live.
- CrowdPulse is a hackathon prototype for decision support. It is not a certified life-safety system.

## Technologies and disclosures

Everything in this repository was written during Hacklanta 2026. Pretrained models, libraries, APIs and data used:

| What | Use |
|---|---|
| [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) (AGPL-3.0), pretrained COCO weights `yolov8n` / `yolov8s` | Person detection. No model was trained or fine-tuned. |
| [Google Gemini API](https://ai.google.dev/) via `google-genai` | Response plans (structured JSON output, multimodal: metrics + camera frame) |
| OpenCV, NumPy, PyTorch | Video capture, drawing, heatmap, inference runtime |
| FastAPI, Uvicorn | Server and WebSocket |
| React, Vite, Tailwind CSS | Dashboard |
| [MOT17 / MOT20](https://motchallenge.net/) sequence previews (CC BY-NC-SA 3.0) | Test footage, see [media/SOURCES.md](media/SOURCES.md) |
| Claude Code (Anthropic) | AI coding assistant used throughout development |

## Project layout

```
backend/    detector, zones, predictor, alerts, Gemini plans, pipeline, FastAPI server
frontend/   React dashboard
config/     sources.yaml (cameras, zones, thresholds)
scripts/    setup, start, m1_count (OpenCV preview + benchmark), precompute (replay cache)
media/      demo clips (not in git) + SOURCES.md
docs/       plan and status
```
