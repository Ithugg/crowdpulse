# Handoff: read this first, then carry on

Written Saturday 10 October 2026, about 11:00 AM ET, by the Claude session on the owner's desktop.
You are a new Claude session on the owner's **laptop** (Windows, no NVIDIA GPU). That laptop is the demo machine. Nothing was left half-done: everything is committed and pushed.

If the owner just says "continue", start at **Step 1** and work down. Do not ask what to do first.

## Update from the laptop: Saturday 10 October, 1:45 PM ET

Step 1 is done, most of Step 2 is done, and **drill mode is built** (the owner said go at about 12:40 PM). The repository is at `C:\dev\crowdpulse` on the laptop and the Gemini key is in its `.env`.

- **Drill mode** is source `drill`, key `7`: `backend/drill.py`, described in `CLAUDE.md` under "Drill". It was run on a real clock at 15 fps and checked in true-size screenshots. Known limits, none of them fixed on purpose:
  - The plan on screen stays the one written at the action level while the zone climbs to danger and critical (automatic plans have a 60-second cooldown per zone). `P` rewrites it. Rewriting automatically on escalation would blank the plan while Gemini writes, so it was left alone.
  - The exposure alert (6 minutes above 4/m²) never fires in a drill: the zone is above the action level for about two minutes per cycle. The timer is visible; the setting was not shortened.
  - The run-sheet's script was rewritten around the drill and has not been rehearsed.
- **Gemini was overloaded for about a minute at 1:30 PM** (a 503, then timeouts). The stored plan appeared after 12 seconds, as designed. Check it again before the video and before judging.
- **The owner may be using the console on port 8000 while you test.** To check something without fighting over the camera keys, start a second server: `$env:PORT = '8001'; .\scripts\py.ps1 -m backend.main`, and stop it afterwards.
- Setup, the tests (321 now) and the console all work on the laptop. The results are in `docs/RUNSHEET.md` under "Checked on the demo laptop".
- Three things were broken on the laptop and are fixed:
  1. The privacy blur left half a face showing when someone stood close to the webcam (`pixelate_heads` in `backend/render.py`).
  2. The heat tint did its full-size work on every frame even with nothing to tint, which held the live clips to 6 to 8 fps. They now hold 15 (`HeatmapRenderer.draw`; the frames it draws are unchanged, pixel for pixel).
  3. Pressing `1` or `R` on the live camera opened the webcam a second time and froze the picture (`Pipeline._open`).
- Left in Step 2, all of which need the owner in person: plug in and look at `RATE`; hear `PA EN` (Windows has no Spanish voice installed); Wi-Fi really off; the gate count by eye; two timed run-throughs.
- Step 3: drill mode was answered yes and is done. **Merge, the extras (± band, PDF report) and Auth0 / GoDaddy have no answer yet**: do not merge or start them without one.
- `C:\dev\brag` is a clone of github.com/latent-spaces/brag (a launch-video skill) that the owner asked for. Nothing from it is installed or used.
- Throwaway check scripts from this session are in `runs\` (gitignored): `tour.py` opens every camera and prints its rate and readings, `plan_check.py` asks Gemini for a plan and a report, `drill_sim.py` runs a drill cycle on a fake clock and prints its alerts, `drill_live.py` runs it on the server, `shot_multi.py` takes timed true-size screenshots while pressing keys.

## Where things stand

- **Deadlines (ET):** feature freeze **Saturday 9:00 PM**; submit Devpost and the Google Form by **Sunday 8:00 AM** (hard deadline 9:00); judging Sunday 9:30 to 11:30, a 3-minute pitch and 2 minutes of questions.
- **Branch:** all current work is on **`revamp`**, which is also the repository's default branch, so a plain clone lands on it. `main` is the older look (tag `v0.1-core`) and is kept as a fallback. Do not merge into `main` until the owner says "merge".
- **The product works end to end** on the desktop: camera or clip, person detection, self-calibrated density in people/m², levels, forecast, walking speed, gate counts, Gemini response plan with English and Spanish announcements, acknowledge and dispatch with response times, incident report, privacy blur. 321 tests pass.
- **The console was redesigned** this morning as control-room software (black, dense, keyboard-driven). It went through two design reviews and is recorded in `DESIGN.md`. The owner has seen screenshots but has not yet said "merge".
- **Nothing has been run on the laptop yet.** That is your first job.

## How the owner wants you to work

- You are the whole engineering team. Keep it simple, protect the demo, commit and push after every working step.
- Tell the owner exactly what to run, in a copyable block.
- After each step: screenshots and a three-line summary. No long recaps.
- If something is a bad idea or will not fit in the time, say so directly.
- Decisions that belong to the owner wait for the owner (they are listed in Step 3). Everything else: just do it.

## Step 1: get it running on the laptop

Needs Git, Python 3.11 to 3.13 and Node.js 20 or newer. Check with `python --version; node --version; git --version` and tell the owner what to install if one is missing (python.org installer with "Add to PATH" ticked; nodejs.org LTS).

```powershell
git clone https://github.com/Ithugg/crowdpulse.git C:\dev\crowdpulse
cd C:\dev\crowdpulse
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
.\scripts\py.ps1 -m pip install -r requirements-dev.txt
.\scripts\py.ps1 -m pytest tests -q -p no:cacheprovider
```

- Clone **outside OneDrive** (for example `C:\dev\crowdpulse`), or `node_modules` gets synced.
- Expect `321 passed`.
- The five demo clips are in the repository (`media/`), and the detector weights download themselves on first run (needs internet once).
- **The Gemini key is not in the repository and must never be.** Run `Copy-Item .env.example .env`, then ask the owner to open it (`notepad .env`) and paste the key after `GEMINI_API_KEY=` themselves. Never print, echo, log or commit the key. Without a key the app still runs and shows plans tagged `CACHED PLAN`.

Then start it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

The console opens at http://localhost:8000.

## Step 2: check what could only be checked on this laptop

Do these in order and report each result. Fix what breaks before moving on.

1. **Speed.** `.\scripts\py.ps1 scripts\m1_count.py --source 0 --bench 100`. The live stream is capped at 15 fps; anything from about 10 inference fps up is fine. If it is slower, lower `detector.imgsz` in `config/sources.yaml` from 640 to 480 and measure again. Clips 2, 3 and 6 are replayed from caches and do not depend on this.
2. **Webcam** (key `1`). It has never seen a real person: the desktop has no camera. Check that people are found, heads are blurred, and the reading is believable. The webcam uses "body size" scale (feet are out of frame). If one person close to the lens reads absurdly high, tell the owner and look at `SceneGeometry` in `backend/calibration.py`; do not paper over it with a multiplier.
3. **Every camera** (keys `2` to `6`) plays, and 2, 3 and 6 show the `REPLAY` tag.
4. **Gemini.** Key `3`, wait for Parade Front to read Busy, then `P`. The Response strip should say `GEMINI` with a time, and the headline should start "Readiness plan".
5. **Spoken announcement.** Press the `PA EN` key: it should speak. Spanish only plays if Windows has a Spanish voice (Settings → Time & language → Speech → Add voices). Nobody has heard either yet.
6. **Screen size.** Look at the console at the laptop's real resolution, full screen (`F11`), zoom 100%. Nothing should overflow. `scripts\shot.py` saves true-size screenshots (usage is in its header).
7. **Wi-Fi off.** Press `P` again: the tag should read `CACHED PLAN`, and the rest of the console should carry on.
8. **Gate count.** On camera `4`, count people crossing the dashed line for one minute by eye and compare with the board. It has never been checked.
9. **Run-sheet.** Go through `docs/RUNSHEET.md` twice with a timer.

Update the "Not yet checked on the demo laptop" section of `docs/RUNSHEET.md` as you go.

## Step 3: decisions waiting for the owner

Ask these together, once, as soon as Step 1 works. Carry on with Step 2 while waiting.

1. **Merge?** "Have you looked at the new console? Say 'merge' and `revamp` becomes `main`."
2. **Drill mode: answered yes on Saturday at about 12:40 PM, and built** (see the update at the top). The original question, for the record: With real measurements no clip gets above Busy (about 2 people/m² against an action level of 4), so the red alert state, the automatic plan and the exposure timer never appear in the demo. On Friday the owner refused any scaling of the numbers, and that stands. A drill is different: a scripted density ramp fed into the real level, forecast and alert logic, with **DRILL: SIMULATED READINGS** on screen the whole time and on every log entry. The owner has not answered. Do not build it without a yes. If yes, it is about two hours: a `drill` source that bypasses the camera, a permanent label in the annunciator and status line, log and report entries marked as drill, and a line in the README. The ramp already exists in `tests/crowd_helpers.py`.
3. **Extras before the freeze** (pick any, or none):
   - A ± band next to each density reading, from the lens assumption (small; about an hour).
   - A bird's-eye floor view with a 1 m² grid (half a day; probably too big now).
   - An accuracy check against MOT20 ground truth (needs a large download, which needs the owner's OK; skip unless there is spare time).
   - Incident report as a PDF (about an hour; the text version already saves).
4. **Auth0 login and a GoDaddy domain** for the side challenges: not started. Only if everything else is done.

My recommendation: drill mode first, because it is the only way judges see what the product is for; then the ± band; skip the rest.

## Step 4: what is left for the submission

In this order. The owner does the recording and the form; you prepare everything around them.

1. Finish Steps 1 to 3 and whatever the owner picks.
2. **Saturday 9:00 PM: freeze.** Merge if the owner has said so, then `git tag v1.0-demo` and push the tag. After that, bug fixes only.
3. **Demo video**, 2 to 3 minutes, public link. The script is `docs/RUNSHEET.md`. Check the link opens in a private window.
4. **Devpost.** The draft is `docs/DEVPOST.md`. The owner should read it aloud once and change what does not sound like them. Add the video link and screenshots from `docs/screens/`.
5. **Google Form** and Devpost submitted by Sunday 8:00 AM.
6. Two timed pitch rehearsals. Sunday 6:30 AM: cold boot, one command, the full demo twice, once with Wi-Fi off.

## Decided: do not reopen

- **Real numbers only.** No tuned areas, multipliers, demo thresholds or unlabelled simulated data. If a clip reads Normal, that is the answer.
- The main user is a **control-room operator**; the judges are a second audience for one weekend.
- 4 people/m² is called the **action level**, never a "safe limit". The 6-minute exposure timer is our own setting, not a published rule. The citations were checked on Saturday morning (`docs/PLAN.md`, "Citations checked").
- No pretrained weights from sources nobody has vetted. Any file download needs the owner's OK first, with the filename, source and size.
- Privacy blur is on by default.
- Every pretrained model, library, API and dataset is disclosed in the README and on Devpost. Claude Code is disclosed as the coding assistant.
- The name is CrowdPulse.

## Traps I already fell into

- **Microsoft Store Python** moves a venv created under `%LOCALAPPDATA%` into its own sandbox and cannot reliably read files under `%LOCALAPPDATA%\Temp`. Always use `scripts\py.ps1`, and keep any throwaway script in `runs\` (gitignored), not in a temp folder.
- **Bash heredocs** mangle quotes and backslashes here. To patch files, use the edit tools, or write a small Python script into `runs\` and run it.
- **PowerShell and `localhost`:** `Invoke-RestMethod http://localhost:8000/...` can time out because it tries IPv6 first. Use `http://127.0.0.1:8000/api/health`. The browser is fine with `localhost`.
- **Restart the server after any backend or config change.** To free the port:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force }
  ```
- **After any frontend change** run `npm run build` in `frontend\`, then refresh the page. `npx tsc --noEmit -p tsconfig.json` is the type check (the build does not run it).
- **Overlay keys are server-wide.** `G`, `B`, `H` and `V` change what every open page sees and stay set until pressed again.
- **A webcam that "opens" but sends nothing** (a virtual camera such as DroidCam) is handled: the server falls back to the first clip.
- **The parade clip is 8.6 seconds long, loops, and the camera moves in it.** The trace shows a wave with that period. That is the clip, not a bug.
- **Looking at the alert states.** Copy `config\sources.yaml` to `runs\qa_sources.yaml`, lower the thresholds there (for example busy 0.5, caution 1.0, danger 1.6, critical 2.2, `exposure_alert_s: 20`), and start a second server:
  ```powershell
  $env:CROWDPULSE_CONFIG = 'runs\qa_sources.yaml'; $env:PORT = '8001'; .\scripts\py.ps1 -m backend.main
  ```
  This is for checking styling only. Never show its output as a real reading, and label any screenshot from it as a test render.
- **Gemini:** the lite models are tried first on purpose (about 2 seconds and dependable; the full Flash models were overloaded and timing out). Below the action level the plan is a "readiness plan" by instruction, and the model is told never to call a crowd safe.
- **CSS:** do not name a colour token `base` (it collides with Tailwind's `text-base`). Numbers are set in B612 with tabular figures, because B612 Mono leaves a gap after the decimal point.
- The design skills and review agents used on the desktop may not be installed on the laptop. For any UI change, `DESIGN.md` is the reference: no radius, no shadows, colour only for a safety state, state changes step instead of fading.

## Where things are

| Path | What |
|---|---|
| `CLAUDE.md` | Project rules, architecture, WebSocket contract |
| `docs/HANDOFF.md` | This file: current state and what to do next |
| `docs/RUNSHEET.md` | The 3-minute demo, key by key, with fallbacks and likely questions |
| `docs/DEVPOST.md` | Devpost draft |
| `docs/PLAN.md` | Longer history and background. Where it disagrees with this file, this file is right |
| `DESIGN.md`, `PRODUCT.md` | The console's design system and who it is for |
| `config/sources.yaml` | Cameras, zone polygons, thresholds |
| `backend/` | detector, calibration, zones, predictor, flow, alerts, Gemini, pipeline, server |
| `frontend/src/` | The console (React, TypeScript, one stylesheet: `index.css`) |
| `tests/` | 321 tests for the measurement, forecast, alert, fallback, privacy-blur and drill logic |
| `scripts/` | setup, start, `py.ps1`, benchmark, calibrate, precompute, `shot.py` |
| `media/` | The five clips and their replay caches; `SOURCES.md` has the licences |
