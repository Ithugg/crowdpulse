# CrowdPulse

**Real-time crowd-safety early warning from the cameras a venue already has.**

Crowd crushes build up over minutes, but staff usually see them too late. Ten people died at Astroworld (Houston, 2021) and more than 150 in Itaewon (Seoul, 2022). Crowd scientists have known the danger thresholds for decades: 4 people per square metre is the safe limit for a moving crowd, and around 6 is where surges begin. In the 2006 Hajj disaster the warning signs were visible on video about 30 minutes before people died (Helbing et al. 2007). Nobody was watching the numbers. CrowdPulse watches the numbers.

Built solo at **Hacklanta 2026** (theme: Music Festival) for the **Social Good track (Cox)**.

## What it does

1. **Counts people** in a live webcam or video feed with YOLOv8.
2. **Calibrates the camera by itself.** The people in view act as a ruler (average height 1.7 m). From how tall people appear at each height in the image, CrowdPulse works out the camera's height and tilt, and so the real floor position of every person. No tape measure, no typed-in areas.
3. **Measures local density in people per m²** for each named zone, using the Gaussian-kernel local density from crowd-disaster research (Helbing, Johansson & Al-Abideen 2007). A zone's reading is its local peak, because averages hide dangerous pockets.
4. **Rates every zone on a research-based scale** (below), with a timer for how long it has been above the safe limit.
5. **Forecasts** when a zone will reach the next level from its trend over the last minute.
6. **Writes a response plan with Gemini** when a zone crosses the safe limit: who does what, in order, plus a PA announcement. The camera frame is sent along with the numbers.
7. Shows it all on a **live operations dashboard**: video with detection boxes and a density heatmap, zone cards, an alert feed and the response plan.

### Density scale

| Local density (people/m²) | Level | What happens | Source |
|---|---|---|---|
| under 2 | Normal | People move freely | Fruin, level-of-service scale |
| 2 – 4 | Busy | Movement restricted, people slow down | Fruin; G. Keith Still |
| 4 – 5 | Caution | 4/m² is the safe limit for a moving crowd; congestion builds quickly | UK Green Guide; Still; Helbing & Mukerji (Love Parade) |
| 5 – 6 | Danger | Constant physical contact, at risk if anyone pushes | Still |
| 6 and above | Critical | Hard to stay upright, surges start, flow drops 3× or more | Still; Helbing et al. 2007 |

A zone that stays above 4/m² for more than 6 minutes raises an exposure alert (Still).

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
.\scripts\py.ps1 scripts\m1_count.py --source 0 --bench 100        # inference speed on this machine
.\scripts\py.ps1 scripts\calibrate.py --source concourse           # camera fit + a metre grid drawn on the floor
.\scripts\py.ps1 scripts\precompute.py --source main_field --weights yolov8s.pt --imgsz 1280
```

## How it works

```
webcam / video ─► capture thread (always the newest frame)
                    └► YOLOv8 person detection
                         └► camera calibration from person heights ─► each person's position in metres
                              └► local density per person ─► peak per zone ─► level (with hysteresis)
                                   └► linear trend over 60 s ─► time until the next level
                                        └► alerts ─► Gemini response plan (cached fallback)
FastAPI ── one WebSocket: JSON state + binary JPEG frames ──► React dashboard
```

- **Backend** (`backend/`): Python, FastAPI, OpenCV, Ultralytics YOLOv8. Everything runs locally in one process.
- **Frontend** (`frontend/`): React + Vite + Tailwind, built to static files and served by FastAPI.
- **Config** (`config/sources.yaml`): camera sources, zone polygons, thresholds. There are no zone sizes in it; areas are measured.
- The WebSocket message format is defined in [backend/schemas.py](backend/schemas.py) and mirrored in [frontend/src/types.ts](frontend/src/types.ts).

## Honest limitations

- **The numbers on screen are real measurements, not tuned for effect.** Most bundled clips show ordinary crowds and read 0.3–1.5 people/m² ("Normal"). The packed street-parade clip reads 2–3 people/m² ("Busy"). Nothing in the bundled footage reaches the 4/m² safe limit, and the dashboard says so.
- **Calibration has stated assumptions**: flat ground, an upright camera, an average person height of 1.7 m, and a lens field of view of 60° unless set per camera. On the test clips the fit predicts person height to within 6–9%. Changing the assumed lens from 45° to 75° moves the local density reading by roughly ±10–15% and the zone areas by ±30% or more.
- **When feet are not visible** (a webcam at table height), the floor cannot be calibrated. Distance is then taken from apparent body width (shoulders about 0.5 m) and the dashboard says so.
- **YOLOv8 undercounts packed crowds** because people hide each other, which makes it read low exactly when it matters most. A density-map crowd-counting model is the next step for crush-level scenes.
- A source can run in **replay mode** (badge shows `REPLAY`): detections computed offline are played back in sync with the clip, so a CPU-only laptop can show a dense scene smoothly. The offline pass uses a larger model and, for packed crowds, sliced detection (the frame is cut into overlapping tiles so small, half-hidden people are found): 23 people become about 170 on the street-parade clip.
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
| Two [Pexels](https://www.pexels.com/) clips (Pexels License): a festival plaza and the Amsterdam Dance Event street parade | Festival footage, see [media/SOURCES.md](media/SOURCES.md) |
| [MOT17 / MOT20](https://motchallenge.net/) sequence previews (CC BY-NC-SA 3.0) | Surveillance-style test footage, see [media/SOURCES.md](media/SOURCES.md) |
| Claude Code (Anthropic) | AI coding assistant used throughout development |

Research the thresholds and density measure are based on:

- J. J. Fruin, *Pedestrian Planning and Design* (level-of-service scale)
- G. K. Still, *Crowd Dynamics*, PhD thesis, University of Warwick
- Sports Grounds Safety Authority, *Guide to Safety at Sports Grounds* ("Green Guide")
- D. Helbing, A. Johansson, H. Z. Al-Abideen, "The Dynamics of Crowd Disasters: An Empirical Study", *Physical Review E* 75, 2007
- D. Helbing, P. Mukerji, "Crowd Disasters as Systemic Failures: Analysis of the Love Parade Disaster", *EPJ Data Science* 1, 2012

## Project layout

```
backend/    detector, calibration, zones, predictor, alerts, Gemini plans, pipeline, FastAPI server
frontend/   React dashboard
config/     sources.yaml (cameras, zones, thresholds)
scripts/    setup, start, m1_count (OpenCV preview + benchmark), calibrate, precompute, simulate_alerts
media/      demo clips (not in git) + SOURCES.md
docs/       plan and status
```
