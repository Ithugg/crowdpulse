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
- Be honest in README, Devpost and pitch notes: zone areas are estimates tuned for the test clips; replay mode exists and is labelled.

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
  → bottom-centre of each box → zone polygon mask → counts       backend/zones.py
  → EMA-smoothed density, level with hysteresis, 60 s linear fit backend/predictor.py
  → alerts (level change, forecast, cleared)                     backend/alerts.py
  → red alert → Gemini plan (10 s budget, cached fallback)       backend/gemini_plan.py
  → boxes + heatmap drawn server-side → JPEG                     backend/render.py
FastAPI /ws: JSON text + binary JPEG, latest-frame-only per client  backend/main.py
React dashboard: canvas frame + SVG zones + cards + feed + plan  frontend/src/
```
- **WebSocket contract**: `backend/schemas.py` is the source of truth, mirrored by `frontend/src/types.ts`. Server → client: `config` (on connect and source switch), `state` (per frame, followed by one binary JPEG), `alert`, `plan` (`generating` then `ready`), `error`. Client → server: `set_source`, `set_overlay`, `restart`, `request_plan`. Change both files together.
- **Config**: `config/sources.yaml` holds sources, zone polygons (normalized 0–1), `area_m2` estimates, thresholds (warn 2.5, critical 4.0 p/m²), detector settings. A source with `replay: media/cache/<id>.npz` plays back precomputed detections (`scripts/precompute.py`) and shows a `REPLAY` badge.
- **Tuning knobs**: smoothing / trend constants at the top of `backend/predictor.py`; hysteresis margin in `backend/zones.py`; forecast horizon and cooldown in `backend/alerts.py`; heatmap look in `backend/render.py`.
- **Gemini**: `GEMINI_API_KEY` in `.env`. Model order: `GEMINI_MODEL` if set, then `gemini-flash-latest`, then `gemini-2.5-flash`. Structured output via `response_schema=ResponsePlan`. The current frame is attached unless `GEMINI_SEND_FRAME=0`. Any failure falls back to `backend/fallback_plans.json` and the UI shows "Cached plan".

## Demo script (build everything around this)
1. Problem hook: Astroworld, Itaewon (20 s).
2. Key `1`: live webcam on the judges; they are counted, zones react (webcam zones have small areas on purpose).
3. Key `2`: Gate 3 Concourse clip. Main Floor goes green → yellow → forecast alert → red within about 40 s, the plan appears.
4. Key `4`: Main Stage Field, the dense scene. Close with impact and future (stadiums, MARTA stations, campus events).

## Conventions
- Python: type hints, small modules, short "why" comments only. TypeScript: function components, Tailwind classes, colour tokens from `frontend/src/index.css`.
- System fonts only and no CDN assets: the demo must work offline (only Gemini needs the network).
- Files under 500 lines.
