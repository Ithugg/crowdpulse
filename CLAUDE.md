# CrowdPulse — project context for Claude

Solo entry for **Hacklanta 2026** (theme: Music Festival), **Social Good track (Cox)**, side challenges: Best Use of Gemini API, optionally Auth0 and GoDaddy Registry. The owner (Ismail, GitHub `Ithugg`) is one person; you are the engineering team.

**Hard deadline: Sunday Oct 11, 9:00 AM ET. Submit on Devpost + Google Form by 8:00 AM.** Feature freeze Saturday 9 PM. Judging Sunday 9:30–11:30: 3-minute pitch + 2 minutes Q&A.

Read [docs/PLAN.md](docs/PLAN.md) first: it holds the current status, what is verified, and the next steps.

## What it is
Existing venue cameras → YOLOv8 people detection → per-zone density (people/m²) → trend prediction ("critical in X") → Gemini-written staff response plan → live ops dashboard. Everything runs locally in one process.

## Rules for working here
- **Protect the demo.** A small thing that works beats a big thing that is half done. Do not refactor working code on Saturday; fix, polish, verify.
- Keep it simple. Commit and push after every working step.
- Tell the owner exactly what to run.
- Do not build: optical flow / surge detection, real camera calibration, multi-camera, model training, cloud deployment, mobile app.
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
  → alerts (level change, forecast, exposure, cleared)           backend/alerts.py
  → zone at caution or above → Gemini plan (10 s, cached fallback) backend/gemini_plan.py
  → boxes + heatmap (coloured by real density) → JPEG            backend/render.py
FastAPI /ws: JSON text + binary JPEG, latest-frame-only per client  backend/main.py
React dashboard: canvas frame + SVG zones + cards + feed + plan  frontend/src/
```
- **WebSocket contract**: `backend/schemas.py` is the source of truth, mirrored by `frontend/src/types.ts`. Server → client: `config` (on connect and source switch), `state` (per frame, followed by one binary JPEG), `alert`, `plan` (`generating` then `ready`), `error`. Client → server: `set_source`, `set_overlay`, `restart`, `request_plan`. Change both files together.
- **Density levels** (local people/m², research-based, sources in `backend/zones.py` `LEVEL_INFO` and the README): Normal < 2, Busy 2–4, Caution 4–5 (4 = safe limit), Danger 5–6, Critical ≥ 6. Exposure alert after 6 min above 4.
- **Measurement**: `backend/calibration.py`. "ground" mode = camera fitted from whole-body detections (stored per clip in `sources.yaml` as `calibration: {cam_height_m, tilt_deg}`, or fitted live for a new source after ~300 whole-body samples). "size" mode = fallback when feet are not visible (webcam): distance from box width, shoulders ≈ 0.5 m. The only assumed number is the lens `hfov_deg` (default 60). `scripts/calibrate.py --source X` prints the fit and draws a 2 m grid on the floor to check it by eye.
- **Sliced detection**: `PersonDetector.detect_tiled` runs YOLO on overlapping tiles and merges the results; it finds 3–7× more people in packed scenes (23 → ~170 on the parade clip) but is far too slow for live CPU use, so it is only used by `scripts/precompute.py --tiles 4x3` to build replay caches.
- A source with `measure: size` never tries floor calibration (packed crowd or webcam, feet hidden).
- **Config**: `config/sources.yaml` holds sources, zone polygons (normalized 0–1, keep them on the floor), thresholds, detector settings. No zone sizes. A source with `replay: media/cache/<id>.npz` plays back precomputed detections (`scripts/precompute.py`) and shows a `REPLAY` badge.
- **Tuning knobs**: smoothing / dwell / forecast constants at the top of `backend/predictor.py`; hysteresis margin and peak percentile in `backend/zones.py`; kernel radius in `calibration.local_density`; forecast horizon and cooldown in `backend/alerts.py`.
- **Gemini**: `GEMINI_API_KEY` in `.env`. Model order: `GEMINI_MODEL` if set, then `gemini-flash-latest`, then `gemini-2.5-flash`. Structured output via `response_schema=ResponsePlan`. The current frame is attached unless `GEMINI_SEND_FRAME=0`. Any failure falls back to `backend/fallback_plans.json` and the UI shows "Cached plan".

## Demo script (build everything around this)
1. Problem hook: Astroworld, Itaewon (20 s).
2. Key `1`: live webcam on the judges; they are counted live.
3. Key `2`: Festival Plaza (a real festival stage, audience, stalls). Point at "Auto-calibrated" and the measured zone areas: the system worked out the geometry by itself.
4. Key `3`: Festival Street Parade (Amsterdam Dance Event). The densest footage: 2–3 people/m² local peak, "Busy". Press `P` to show the Gemini response plan.
5. Keys `4`–`6` are the three MOT surveillance clips (station concourse, plaza, night square): backup material.
6. Close with impact and future (stadiums, MARTA stations, campus events).

**Open problem for the demo:** with real numbers, the densest clip reaches Busy (2–3 /m²) and nothing reaches Caution (4), so no automatic plan fires on its own. See "Showing an alert honestly" in docs/PLAN.md before changing anything.

## Conventions
- Python: type hints, small modules, short "why" comments only. TypeScript: function components, Tailwind classes, colour tokens from `frontend/src/index.css`.
- System fonts only and no CDN assets: the demo must work offline (only Gemini needs the network).
- Files under 500 lines.
