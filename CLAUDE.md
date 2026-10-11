# CrowdPulse — project context for Claude

Two-person entry for **Hacklanta 2026** (theme: Music Festival), **Social Good track (Cox)**, side challenges (the maximum of three, chosen Saturday evening): Mercedes Best Application of Computer Vision, MLH Best Use of Gemini API, Photon Agents in iMessage (`hacklanta/`). Auth0 and GoDaddy are dropped. The team is Ismail El Ktiri El Idrissi and Abir Chowdhury; the owner you work with is Ismail (GitHub `Ithugg`), and you are the engineering help. In anything public, say that both worked on it and never say who did what (the owner's instruction, Saturday evening).

**Hard deadline: Sunday Oct 11, 9:00 AM ET. Submit on Devpost + Google Form by 8:00 AM.** Feature freeze Saturday 9 PM. Judging Sunday 9:30–11:30: 3-minute pitch + 2 minutes Q&A.

## Start here

**Read [docs/HANDOFF.md](docs/HANDOFF.md) before anything else.** It is the current state and the ordered list of what to do next. If the owner says "continue" (or anything like it), begin at its Step 1 and work down without asking what to do first. Work on the `revamp` branch.

@docs/HANDOFF.md

[docs/PLAN.md](docs/PLAN.md) is the longer history. Where it disagrees with the handoff, the handoff is right.

## What it is
Existing venue cameras → YOLOv8 people detection → per-zone density (people/m²) → trend prediction ("critical in X") → Gemini-written staff response plan → live ops dashboard. Everything runs locally in one process.

## Rules for working here
- **Protect the demo.** A small thing that works beats a big thing that is half done. Do not refactor working code on Saturday; fix, polish, verify.
- Keep it simple. Commit and push after every working step.
- Tell the owner exactly what to run.
- Do not build: multi-camera, model training, cloud deployment, mobile app.
- Never commit `.env`. Disclose every pretrained model, library, API and dataset in README + Devpost.
- **Real numbers only (owner's decision, Friday night).** Density and zone areas are measured from the video, never typed in or scaled to make an alert fire. Do not add multipliers, "demo thresholds" or tuned areas. If a clip reads Normal, that is the answer.
- Be honest in README, Devpost and pitch notes: state the calibration assumptions; replay mode exists and is labelled.

## Run
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1     # once: venv, pip, npm, build
powershell -ExecutionPolicy Bypass -File scripts\start.ps1     # server + dashboard at http://localhost:8000
.\scripts\py.ps1 scripts\m1_count.py --source 0 --bench 100    # inference speed on this machine
```
- The venv lives in `.venv/` unless the repo is inside OneDrive, then in `%USERPROFILE%\.venvs\crowdpulse` (`scripts/_venv.ps1` decides). Always run Python through `scripts\py.ps1` or `$VenvPython`.
- After editing anything in `frontend/`, run `npm run build` in `frontend/` (FastAPI serves `frontend/dist`). For live UI work: `npm run dev` in `frontend/` (port 5173, proxies `/ws` to 8000) with the Python server running.
- Restart the Python server after backend or `config/sources.yaml` changes.

## Architecture
```
capture thread (newest frame, clips loop at native speed)        backend/capture.py
  → YOLOv8 person boxes (or replay cache by frame index)         backend/detector.py, pipeline.py
  → camera height + tilt fitted from person heights (1.7 m)      backend/calibration.py
  → each person's floor position in metres → local density      backend/calibration.py, zones.py
  → zone = peak (p90) local density of the people inside it      backend/zones.py
  → EMA smoothing, 5 levels with hysteresis + dwell, exposure
    timer, 60 s linear fit → time to next level                  backend/predictor.py
  → overlap tracker → walking speed (m/s), direction, crowd
    pressure per zone; people crossing gate lines                backend/flow.py
  → alerts (level change, forecast, exposure, cleared)           backend/alerts.py
  → zone at caution or above → Gemini plan (10 s, cached fallback) backend/gemini_plan.py
  → privacy pixelation of heads, boxes, heatmap → JPEG           backend/render.py
drill source (key 7): scripted people on a virtual floor, seen by a
  virtual camera, fed in as boxes where the detector would be    backend/drill.py
FastAPI /ws: JSON text + binary JPEG, latest-frame-only per client  backend/main.py
React console: status line, annunciator, camera, zone board,
  strip chart, response, log, key bar + command line          frontend/src/
```
- **WebSocket contract**: `backend/schemas.py` is the source of truth, mirrored by `frontend/src/types.ts`. Server → client: `config` (on connect, source switch, calibration update), `state` (per frame, followed by one binary JPEG; zones carry density, level, forecast, exposure, speed, heading; plus `gates`), `alert`, `alert_update` (acknowledged / dispatched), `plan` (`generating` then `ready`), `report` (`generating` then `ready`), `error`. Client → server: `set_source`, `set_overlay` (boxes, heatmap, privacy, grid), `restart`, `request_plan`, `ack_alert`, `request_report`. Change both files together. On a drill, `config.drill` is true, `state.mode` is `drill`, and every `alert`, `plan` and `report` carries `drill: true`; `config.run` goes up each time any source is selected or reset, and a new run is a new session (clean log, plan and report), so `R` clears the log on every camera.
- **Drill** (`backend/drill.py`, source `drill` in `sources.yaml`, key `7`): the answer to "no clip reaches the action level". Scripted people stand on a virtual floor; a virtual camera (pose in `sources.yaml`) turns them into person boxes; from there the unchanged pipeline measures, levels, forecasts and alerts. `SCRIPTS` holds the density each zone is filled to over a 4-minute cycle: only the first zone alerts (busy 5 s, forecast 30 s, caution about 46 s, danger about 60 s, critical about 75 s, cleared about 3 min). The label is put on in code (`label_alerts`, `label_plan`, `label_report`, and the console's status line, annunciator and camera plate), never left to Gemini. A drill never touches a real camera's readings, and nothing from it may be shown as a real measurement.
- **Who may connect** (`trusted_origin` in `backend/main.py`): the WebSocket refuses a browser page whose Origin is not the address the server was reached at (localhost or a plain IP). Scripts send no Origin and are allowed. Without it any website open in the operator's browser could read the camera. Do not remove it to make a tool connect: send no Origin, or open the page from the server itself.
- **Session log** (`Session` in `backend/main.py`): alerts, staff response times, plans and peak readings for the current camera; reset on camera switch and on `R`; the only input to the incident report.
- **Automatic plans** (`plan_due` in `backend/main.py`): the first alert at caution or above gets a plan; after that one per zone per 60 seconds, except that a zone which climbs to a higher level gets a new plan at once. The console keeps the old plan up, tagged `REWRITING`, until the new one arrives. A plan that was overtaken while Gemini wrote it is dropped.
- **Flow and gates** need a fixed camera (`moving_camera: true` turns them off). Speed in m/s needs ground calibration. Gates are per-source lines in `sources.yaml` (`gates:`); crossing to the right-hand side of first → second point is "in".
- **Density levels** (local people/m², research-based, sources in `backend/zones.py` `LEVEL_INFO` and the README): Normal < 2, Busy 2–4, Caution 4–5 (4 = the "action level"; never call it a safe limit), Danger 5–6, Critical ≥ 6. Exposure alert after 6 min above 4.
- **Measurement**: `backend/calibration.py`. "ground" mode = camera fitted from whole-body detections (stored per clip in `sources.yaml` as `calibration: {cam_height_m, tilt_deg}`, or fitted live for a new source after ~300 whole-body samples). "size" mode = fallback when feet are not visible (webcam): distance from box width, shoulders ≈ 0.5 m. The only assumed number is the lens `hfov_deg` (default 60). `scripts/calibrate.py --source X` prints the fit and draws a 2 m grid on the floor to check it by eye.
- **Sliced detection**: `PersonDetector.detect_tiled` runs YOLO on overlapping tiles and merges the results; it finds 3–7× more people in packed scenes (23 → ~170 on the parade clip) but is far too slow for live CPU use, so it is only used by `scripts/precompute.py --tiles 4x3` to build replay caches.
- A source with `measure: size` never tries floor calibration (packed crowd or webcam, feet hidden).
- **Config**: `config/sources.yaml` holds sources, zone polygons (normalized 0–1, keep them on the floor), thresholds, detector settings. No zone sizes. A source with `replay: media/cache/<id>.npz` plays back precomputed detections (`scripts/precompute.py`) and shows a `REPLAY` badge.
- **Tuning knobs**: smoothing / dwell / forecast constants at the top of `backend/predictor.py`; hysteresis margin and peak percentile in `backend/zones.py`; kernel radius in `calibration.local_density`; forecast horizon and cooldown in `backend/alerts.py`.
- **Gemini**: `GEMINI_API_KEY` in `.env`. Model order: `GEMINI_MODEL` if set, then `gemini-flash-lite-latest`, `gemini-3.5-flash-lite`, `gemini-flash-latest` (6 s per attempt, 12 s in total). The lite models are first on purpose: about 1.5 s and dependable, where the full Flash models were overloaded when tested. Structured output via `response_schema=ResponsePlan`. The current frame is attached unless `GEMINI_SEND_FRAME=0`. Any failure falls back to `backend/fallback_plans.json` and the UI shows "Cached plan".

## Demo script (build everything around this)
The key-by-key script is [docs/RUNSHEET.md](docs/RUNSHEET.md). In short: problem hook → `1` live webcam on the judges → `5` then `G`, East Plaza with the measured 2 m floor grid → `3`, the street parade at Busy ("we do not scale it") → `7`, the labelled drill: forecast, action level, Gemini's plan by itself, acknowledge, dispatch, PA, critical, `P` → `I` incident report → close. `S` (sources) is for the questions.

With real numbers the densest clip reaches Busy (about 2 /m²) and nothing reaches Caution (4). The owner said yes to a labelled drill on Saturday 10 October, and it is built (see Drill above). Real readings are still never scaled.

## Conventions
- Python: type hints, small modules, short "why" comments only. TypeScript: function components, one stylesheet (`frontend/src/index.css`) with the colour tokens and component classes; follow [DESIGN.md](DESIGN.md) for any UI change.
- No CDN assets: the demo must work offline (only Gemini needs the network). The typefaces (B612, B612 Mono) are bundled.
- Files under 500 lines.
- Tests: `.\scripts\py.ps1 -m pytest tests -q -p no:cacheprovider` (needs `requirements-dev.txt`). Run them after any backend change.
