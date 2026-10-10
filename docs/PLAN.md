# CrowdPulse — plan and status

Deadline: **Sunday Oct 11, 9:00 AM ET** (submit by 8:00). Feature freeze: **Saturday 9:00 PM**.

## Status (updated Friday night, end of session 1 on the desktop)

Written and verified on the dev desktop (Ryzen 7 7700X, CPU inference, no real webcam):

- [x] YOLOv8n person detection, about 49 FPS on that CPU at 640 px (`scripts/m1_count.py --bench`)
- [x] **Automatic camera calibration** from the people in view (height 1.7 m as the ruler). Fit error 6–9% on all three clips; a 2 m grid drawn on the concourse floor looks right by eye (`scripts/calibrate.py`)
- [x] **Real local density** (people/m², Helbing 2007 kernel, R = 1 m), zone value = local peak (p90); zone floor areas measured, not typed in
- [x] **Research-based levels**: Normal < 2, Busy 2–4, Caution 4–5, Danger 5–6, Critical ≥ 6, with sources in the legend and tooltips
- [x] Exposure timer per zone and an alert after 6 minutes above 4/m² (code path written; never triggered, see below)
- [x] Forecast to the next level (only once a zone is at least half-way there)
- [x] FastAPI WebSocket: JSON + binary JPEG at 15 FPS, source switching, overlay toggles
- [x] React dashboard: video + SVG zones, zone cards with scale gauge and trend line, legend, alert feed, plan panel, demo keys
- [x] Response plans with cached fallback (`P` to force; automatic from Caution upwards)
- [x] Heatmap coloured by real local density on the same scale
- [x] Replay mode: Main Stage Field plays back detections precomputed with yolov8s at 1280 px (`media/cache/main_field.npz`, in git)
- [x] `scripts/setup.ps1` tested from a fresh clone of the GitHub repo (before the calibration change; re-run it on the laptop)
- [x] Gemini code path exercised with a dummy key: the request reaches the API, is rejected, and the cached plan is shown after about 1.4 s

**Measured on the test clips (real numbers):**

| Clip | Camera (fitted) | Local peak density | Level |
|---|---|---|---|
| Gate 3 Concourse | 5.0 m high, 19° down | 0.4 – 1.0 /m² | Normal |
| East Plaza | 8.4 m high, 33° down | 0.6 – 1.3 /m² | Normal |
| Main Stage Field | 8.1 m high, 38° down | 0.6 – 1.4 /m² | Normal |

**Not verified yet (do these first on the laptop):**

- [ ] **Real webcam.** The desktop has none (only a DroidCam placeholder). Code path is `source: webcam`, `path: 0`. The webcam will run in "size" mode (distance from body width), which has never seen a real person. Check the numbers look sane: three people shoulder to shoulder at 1.5 m should read under 1 /m².
- [ ] **Real Gemini call.** No API key was available. Put the key in `.env`, start the server, press `P`, and confirm the badge says "Gemini" rather than "Cached plan". If the model name is rejected, set `GEMINI_MODEL` in `.env` (the server log prints the error).
- [ ] **Laptop CPU speed.** Run `.\scripts\py.ps1 scripts\m1_count.py --source 0 --bench 100`.
  - 10 FPS or more: nothing to do.
  - Less: export a faster model with `.\scripts\py.ps1 -c "from ultralytics import YOLO; YOLO('models/yolov8n.pt').export(format='openvino')"` (add `openvino` to pip first), then set `detector.weights` to the exported folder. Otherwise lower `detector.imgsz` to 480, or precompute replay caches for the clips.
- [ ] **Levels above Busy have never been seen on the dashboard**, because no footage reaches them. The logic itself was checked with a synthetic ramp fed straight into `ZoneTracker` + `AlertManager` (1 → 6.5 /m² over 3 minutes, hold, fall): forecast "Caution in ~70 s" came 67 s before Caution, then Danger, Critical, the 6-minute exposure alert, easing and cleared all fired in order. What is untested is how the Caution / Danger / Critical colours, the pulsing card and the automatic Gemini plan look in the browser.

## Showing an alert honestly (the main open problem)

The owner chose **real numbers only**: no multipliers, no tuned areas. The consequence is that all three clips sit at Normal and nothing fires by itself during the pitch. Options that stay honest, best first:

1. **Find genuinely dense footage.** Front-of-stage festival crowds do reach 4+ people/m². YOLO will undercount them badly (people hide each other), so this needs option 2 to read correctly.
2. **Add a pretrained crowd-counting density-map model** (already on the nice-to-have list) for packed scenes, and use its density map in place of YOLO positions when YOLO coverage is poor. Pretrained only; disclose it.
3. **Pitch it as it is**: "this footage is safe, and the system correctly says so; here is the scale it is measured against, and here is the plan it writes when I ask for one" (`P`). Show the exposure/alert logic with the ramp script above if a judge asks.
4. Ask the owner again about a clearly labelled drill mode. They declined it on Friday; do not add it without asking.

## Laptop setup (Saturday morning)

1. Install Git, Python 3.11–3.13 (python.org, tick "Add to PATH") and Node.js 20+.
2. `git clone https://github.com/Ithugg/crowdpulse.git C:\dev\crowdpulse` — **outside OneDrive**, so `node_modules` is not synced.
3. Copy the clips into `C:\dev\crowdpulse\media\`: `MOT20-02.mp4`, `MOT20-03.mp4`, `MOT20-05.mp4` (from the desktop's `Documents\Hacklanta\media\` folder via OneDrive or USB). Backup: `scripts\fetch_media.ps1` (needs ffmpeg).
4. `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`
5. Copy `.env.example` to `.env` and paste the Gemini key.
6. `powershell -ExecutionPolicy Bypass -File scripts\start.ps1`
7. Work through the "Not verified yet" list above.

## Remaining work, in priority order

1. The unverified items above.
2. Decide how the pitch shows an alert (section above) and do it.
3. Festival-flavoured footage: elevated, well-lit festival or concert crowd clips (Pexels, Pixabay, Mixkit). Add as sources with zones named for a festival (Front Stage, Gate 3, Food Court), run `scripts/calibrate.py --source <id>` and paste the `calibration:` line it prints into `config/sources.yaml`.
4. UI polish pass at the laptop's real screen size. Check the plan panel is readable from a metre away.
5. Two full run-throughs of the demo script (see CLAUDE.md), including one with Wi-Fi off.
6. Nice-to-haves, only if everything above is solid: bigger density chart per zone → Auth0 staff login → GoDaddy Registry domain. Crowd pressure from optical flow (density × variance of speed, Helbing 2007) is a stretch goal the owner's research notes mention; it was on the original do-not-build list, so ask before starting it.
7. Saturday 9 PM: freeze, tag `v1.0-demo`. Then record the 2–3 minute video, finish README, write Devpost, rehearse the pitch.

## Schedule (ET)

| When | What | Done when |
|---|---|---|
| Sat 7:30–8:30 AM | Laptop setup, webcam, Gemini key, benchmark | Unverified items ticked |
| Sat 8:30–11:30 | Dense festival footage, crowd-counting decision, calibration | The pitch has an honest way to show an alert |
| Sat 11:30–1:00 PM | UI polish | Looks right on the laptop screen |
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

- The lens field of view is assumed (60°). Going from 45° to 75° changes local density by roughly ±10–15% and zone areas by ±30% or more. Set `hfov_deg` per source if the camera is known.
- Zone area is the floor area of the polygon out to 40 m, so a polygon drawn over a wall or kiosk overstates it. Keep polygons on walkable floor.
- YOLOv8 finds roughly half the people in the Main Stage Field clip even with the larger replay model, so its density reads low. The roadmap answer is a density-map crowd-counting model.
- The forecast is a straight-line fit over the last 30–60 s. It needs 30 s of data and only speaks once a zone is at least half-way to the next level.
- The dev desktop exposes a DroidCam virtual camera as camera 0, which shows a placeholder image. That is not a bug.

## Pitch line (owner's)

"Crowd scientists have known the danger thresholds for decades: 4 people per square metre is the safe limit, 6 is when surges begin. At the Hajj in 2006, the warning signs were visible on video 30 minutes before people died. Nobody was watching the numbers. CrowdPulse watches the numbers."

Q&A on square metres: the camera calibrates itself from the people in view (average height 1.7 m), assuming a 60° lens; a real deployment would enter each camera's lens once.

## Judging criteria (keep in view)

1. Fits the track: Cox Social Good, "build for the people and places that get overlooked: access, safety, mobility, and the everyday systems communities run on."
2. How polished is the demo?
3. How effective is the presentation?
4. Clear, compelling use case?
