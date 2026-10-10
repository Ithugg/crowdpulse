# CrowdPulse — plan and status

Deadline: **Sunday Oct 11, 9:00 AM ET** (submit by 8:00). Feature freeze: **Saturday 9:00 PM**.

## Status (updated Friday night, end of session 1 on the desktop)

Written and verified on the dev desktop (Ryzen 7 7700X, CPU inference, no webcam):

- [x] YOLOv8n person detection, about 49 FPS on that CPU at 640 px (`scripts/m1_count.py --bench`)
- [x] Zone counting, density, smoothing, green/yellow/red with hysteresis + dwell time
- [x] Linear-trend forecast ("critical in ~20 s")
- [x] Alert feed logic (elevated, critical, forecast, cleared)
- [x] FastAPI WebSocket: JSON + binary JPEG at 15 FPS, source switching, overlay toggles
- [x] React dashboard: video + SVG zones, zone cards with sparklines, alert feed, plan panel, demo keys
- [x] Response plans with cached fallback (auto on red, `P` to force)
- [x] Heatmap overlay
- [x] Full arc on the Gate 3 Concourse clip seen in the browser: yellow at ~12 s, forecast at ~30 s, red at ~38 s, plan appears
- [x] Replay mode: Main Stage Field plays back detections precomputed with yolov8s at 1280 px (`media/cache/main_field.npz`, in git)
- [x] `scripts/setup.ps1` tested from a fresh clone of the GitHub repo
- [x] Gemini code path exercised with a dummy key: the request reaches the API, is rejected, and the cached plan is shown after about 1.4 s

**Not verified yet (do these first on the laptop):**

- [ ] **Real webcam.** The desktop has none. Code path is `source: webcam`, `path: 0` in `config/sources.yaml`. If the laptop has several cameras, try `path: 1`.
- [ ] **Real Gemini call.** No API key was available. Put the key in `.env`, start the server, press `P`, and confirm the badge says "Gemini" rather than "Cached plan". If the model name is rejected, set `GEMINI_MODEL` in `.env` (the server log prints the error).
- [ ] **Laptop CPU speed.** Run `.\scripts\py.ps1 scripts\m1_count.py --source 0 --bench 100`.
  - 10 FPS or more: nothing to do.
  - Less: export a faster model with `.\scripts\py.ps1 -c "from ultralytics import YOLO; YOLO('models/yolov8n.pt').export(format='openvino')"` (add `openvino` to pip first), then set `detector.weights` to the exported folder. Otherwise lower `detector.imgsz` to 480, or precompute replay caches for the clips.
- [ ] Webcam zone areas: tune `area_m2` for the three webcam zones so 2–3 people in one zone turn it yellow or red at the judging table.

## Laptop setup (Saturday morning)

1. Install Git, Python 3.11–3.13 (python.org, tick "Add to PATH") and Node.js 20+.
2. `git clone https://github.com/Ithugg/crowdpulse.git C:\dev\crowdpulse` — **outside OneDrive**, so `node_modules` is not synced.
3. Copy the clips into `C:\dev\crowdpulse\media\`: `MOT20-02.mp4`, `MOT20-03.mp4`, `MOT20-05.mp4` (from the desktop's `media\` folder via OneDrive or USB). Backup: `scripts\fetch_media.ps1` (needs ffmpeg).
4. `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`
5. Copy `.env.example` to `.env` and paste the Gemini key.
6. `powershell -ExecutionPolicy Bypass -File scripts\start.ps1`
7. Work through the "Not verified yet" list above.

## Remaining work, in priority order

1. The four unverified items above.
2. Festival-flavoured footage: find one or two elevated, well-lit festival or concert crowd clips (Pexels, Pixabay, Mixkit), add them as sources with zones named for a festival (Front Stage, Gate 3, Food Court), calibrate with `scripts/m1_count.py` and `scripts/simulate_alerts.py`. The MOT clips work but are a train station and a street, not a festival.
3. UI polish pass at the laptop's real screen size. Check the plan panel is readable from a metre away.
4. Two full run-throughs of the demo script (see CLAUDE.md), including one with Wi-Fi off.
5. Nice-to-haves, strictly in this order and only if everything above is solid: bigger density chart per zone → Auth0 staff login → GoDaddy Registry domain.
6. Saturday 9 PM: freeze, tag `v1.0-demo`. Then record the 2–3 minute video, finish README, write Devpost, rehearse the pitch.

## Schedule (ET)

| When | What | Done when |
|---|---|---|
| Sat 7:30–8:30 AM | Laptop setup, webcam, Gemini key, benchmark | All four unverified items ticked |
| Sat 8:30–11:00 | Festival footage + calibration | Demo script runs on festival clips |
| Sat 11:00–1:00 PM | UI polish, webcam zone tuning | Looks right on the laptop screen |
| Sat 1:30–5:00 | Run-throughs, bug fixes, offline test. **Core complete, tag `v0.1-core`** | Two clean runs |
| Sat 5:30–9:00 | Nice-to-haves in order. **Freeze at 9:00, tag `v1.0-demo`** | |
| Sat 9:00–10:00 | Record demo video, upload public | Link opens in a private window |
| Sat 10:00–11:15 | README final, Devpost write-up | Devpost saved with everything |
| Sat 11:15–11:45 | Pitch script, two timed rehearsals | Under 3:00 |
| Sat 11:45 PM–6:15 AM | Sleep | |
| Sun 6:30–7:15 | Cold boot, one command, full demo twice | |
| Sun 7:15–8:00 | Final Devpost + Google Form. **Submitted by 8:00** | |

Cut order if behind: nice-to-haves → festival footage (fall back to the MOT clips) → polish. Never cut: webcam check, Gemini check, run-throughs.

## Known rough edges

- The forecast is a straight-line fit over the last 30–60 s. It needs 30 s of data before it speaks, and it is approximate.
- `area_m2` values for the test clips are tuned for `yolov8n` at 640 px. Changing the detector, the input size or the footage means re-tuning them (`scripts/simulate_alerts.py <source> zone_id=area` replays a logged run in a second).
- The dev desktop exposes a DroidCam virtual camera as camera 0, which shows a placeholder image. That is not a bug.
- YOLOv8 finds roughly a third to a half of the people in the dense Main Stage Field clip even with the larger replay model. Say so if a judge asks; the roadmap answer is a density-map crowd-counting model.

## Judging criteria (keep in view)

1. Fits the track: Cox Social Good, "build for the people and places that get overlooked: access, safety, mobility, and the everyday systems communities run on."
2. How polished is the demo?
3. How effective is the presentation?
4. Clear, compelling use case?
