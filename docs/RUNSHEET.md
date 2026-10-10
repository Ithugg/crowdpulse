# Demo run-sheet (3 minutes + 2 minutes Q&A)

Everything is on the keyboard. Practise it twice with a timer; cut words, not steps.

## Before the judges arrive

1. Laptop on mains power, browser full screen (`F11`), zoom at 100%.
2. `powershell -ExecutionPolicy Bypass -File scripts\start.ps1`, wait for the console.
3. Press `2`, `3`, `4`, `5`, `7` once each so every source has been opened, then `1`.
4. Press `3`, then `P`. Check the tag in the Response strip says `GEMINI` and not `CACHED PLAN`. If it says cached, Gemini cannot be reached or is overloaded (it was for a minute on Saturday afternoon): carry on, the demo still works, but the stored plan can take up to 12 seconds to appear.
5. Press `1`. Point the laptop's camera at where the judges will stand.

## The three minutes

| Time | Key | What is on screen | What to say |
|---|---|---|---|
| 0:00 | – | Console, webcam | "Ten people died at Astroworld. More than 150 in Itaewon. Crowd scientists have published the danger levels for decades: at 4 people per square metre a control room should already be acting, and at 6 people cannot keep their footing. The cameras were already there. Nobody was watching the numbers." |
| 0:20 | `1` | Judges on camera, counted, faces blurred | "This is live. It is counting you. Faces are blurred by default: CrowdPulse counts people, it never identifies them." |
| 0:35 | `5` then `G` | East Plaza with the 2 m floor grid | "A real camera over a real plaza. Nobody measured this floor. The system used the people as a ruler, about 1.7 metres each, and worked out that the camera is 8.4 metres up, looking 33 degrees down. That grid is 2-metre squares. So this is real people per square metre." |
| 1:00 | `G`, `3` | Festival Street Parade, Parade Front reads Busy | "The densest real footage we have: about 2 per square metre. Busy, below the action level of 4. We do not scale a real reading to make something turn red." |
| 1:10 | `7` | The drill. `DRILL: SIMULATED READINGS` on the band and the picture, `SIMULATED` in the status line | "So this is a drill, and it says so, here and here. A scripted crowd on a virtual floor, measured by exactly the same code. Watch the front barrier fill." |
| 1:40 | – | Log: "projected to reach Caution in ~20 s" | "Thirty seconds in, it forecasts the action level from the trend, before it happens." |
| 1:56 | – | The band turns orange and flashes. A plan appears by itself, tag `GEMINI` | "Action level. The band flashes until someone answers. And Gemini has already written the plan: who does what, in order, and where to send people." |
| 2:05 | `A`, `D`, then the `PA EN` key | Log shows acknowledged, dispatched, with seconds. The announcement is spoken | "Acknowledge, dispatch: the response time is recorded. And the announcement, in English and Spanish." |
| 2:25 | – | The band is red: `CRITICAL`, above 6. The plan has rewritten itself at each level (the strip says `REWRITING` while the old one stays up) | "Six per square metre: people cannot keep their footing. Every time it climbed, the plan was rewritten for the new level, and staff never lost the old one while they waited." |
| 2:40 | `I` | Incident report, tagged `DRILL` | "Afterwards, one key writes the incident report from the log." `Esc`. |
| 2:50 | – | The console | "It runs on one laptop with the cameras a venue already owns. Stadiums, MARTA stations, campus events. At the Hajj in 2006 the warning was on video more than thirty minutes before the crush. CrowdPulse watches the numbers." |

The drill keeps its own time from the moment `7` is pressed: busy at 5 seconds, the forecast at 30, the action level at about 46, danger at about 60, critical at about 75. It holds there, eases from 2:10, clears at about 3:00 and repeats every 4 minutes. `R` starts it again with a clean log. A new plan is written by itself at the action level, at danger and at critical; the one on screen stays until the next arrives.

If the first minute runs long, drop the parade (`3`) and go from the plaza straight to `7`. The Science sheet (`S`, then `End` for "What can be wrong") is for the questions.

## If something goes wrong

| Problem | Do this |
|---|---|
| Webcam shows nothing | Skip it: press `5` and start from the plaza. Say "live camera works the same way". |
| Plan tag says `CACHED PLAN` | Say "Gemini could not be reached, so it used the stored plan; it never leaves the operator with nothing". |
| The plan is still "Writing the plan" | Gemini is slow. Keep talking: the stored plan appears within 12 seconds. |
| The drill is at the wrong point | Press `R`: it starts again with a clean log, 46 seconds from the action level. |
| No sound from the PA key | Read the announcement aloud yourself. (Spanish needs the Windows Spanish voice installed.) |
| A clip looks frozen | Press `R`. It restarts the camera and clears its log. |
| The page is blank | Refresh. If still blank, restart `scripts\start.ps1` (about 15 seconds). |

## Likely questions

- **"How do you know the square metres?"** The camera calibrates itself from the people in view, assuming an average height of 1.7 m and a 60° lens. On the test clips it predicts how tall people appear to within 6–9%. A real installation would enter each camera's lens once.
- **"Why is nothing red on the real cameras?"** Because nothing in this footage is dangerous, and we do not fake it. The densest clip reads about 2 people per square metre against an action level of 4. The red you saw was the drill.
- **"Is the drill real data?"** No, and it says so on the screen, the log, the plan and the report. It is a scripted crowd on a virtual floor under a virtual camera. What is real in it is everything after the camera: the density measure, the levels, the forecast, the alerts and Gemini's plan. It does not show how well a real packed crowd is detected: every simulated person is found, and a real detector misses people.
- **"Where do the levels come from?"** Press `S`: every level is a published threshold with its source. `End` shows what can be wrong with our numbers.
- **"Does it work in a packed crowd?"** The detector misses people who are hidden behind others, so it reads low exactly when it matters most. The next step is a crowd-counting model built for dense scenes.
- **"What about privacy?"** Heads are blurred before the video is shown, nothing is recorded, and no one is identified or tracked across cameras.
- **"What did you use?"** YOLOv8 (pretrained, not trained by us) for detection, the Gemini API for plans and reports, OpenCV, FastAPI, React. Levels from Fruin, G. Keith Still and Helbing's Hajj study; the UK Green Guide's own figure is 4.7 per square metre for standing areas.

## Checked on the demo laptop

Saturday 10 October, on battery, from a fresh clone.

- **Setup and tests** pass.
- **Frame rate.** Every clip holds the 15 fps cap (cameras 4 and 5, which run the detector live, at 14.8 fps with 43 to 48 ms per detection). The live camera runs at about 12 fps. Measured at the server; glance at `RATE` in the status line in the real browser.
- **Live camera with two real people.** Both counted, faces blurred, readings of 0.3 to 0.5 people/m². A face close to the lens used to be only half blurred; that is fixed.
- **Cameras 2 to 6** play; 2, 3 and 6 show `REPLAY`.
- **Gemini.** `P` on Parade Front returned a "Readiness plan" tagged `GEMINI` in about 4 seconds, and the incident report in under 2.
- **Gemini unreachable** (simulated): the cached plan is shown instead.
- **Screen.** Full screen on this laptop is 1536 × 864 (1920 × 1080 at 125% scaling). Nothing overflows. The Science sheet is longer than the screen, so `End` is in the script above.
- **`1` or `R` on the live camera** restarts it in about a second. It used to freeze the picture.
- **The drill** (`7`). Run on a real clock at 15 fps: busy at 5 s, forecast at 30 s, action level at 46 s with Gemini's plan 2 seconds later, danger at 60 s, critical at 75 s. `R` restarts it with a clean log. The labels, the report and the Science sheet were checked in screenshots at 1536 × 864.
- **A plan at every level.** Run on the laptop at 3:35 PM: Gemini's plan arrived by itself at the action level (3.7 s), at danger (1.4 s) and at critical (1.3 s), with the earlier one on screen until each arrived.
- **Stress.** 200 commands in 110 seconds (rapid camera switches, resets, overlay toggles, plan and report requests, malformed messages, a client that sends garbage and vanishes): no errors logged, and every source streamed afterwards. If a frame ever does fail, the console now says so and carries on instead of freezing.
- **Gemini under load.** For about a minute on Saturday afternoon it answered 503 and timed out; the stored plan appeared after 12 seconds, tagged `CACHED PLAN`, as designed.

## Not yet checked on the demo laptop

Do these before the first judge.

- **Mains power in the room.** Measured plugged in at 4:00 PM (Balanced plan), through the real console: live camera 13 to 15 fps, cameras 4 and 5 at 13 to 14, the replays and the drill at 15. On battery with anything else running it drops to 6 to 9. Plug in before the first judge, and do not run a second server.
- **The spoken announcement.** Nobody has heard it yet: press `PA EN` and `PA ES` once. Both keys should be enabled. English uses a voice installed in Windows. Spanish uses the browser's own online voice (US Spanish in Edge and in Chrome), so it needs the network; for Spanish with Wi-Fi off, install the Windows voice: Settings → Time & language → Speech → Add voices → Spanish.
- **Wi-Fi really off.** Press `P`: the tag should read `CACHED PLAN`. Note how long it takes.
- **Gate count** on camera `4`, against a count by eye for one minute.
- **Two run-throughs with a timer.** The script above was rewritten around the drill on Saturday afternoon and has not been spoken aloud yet. The timings in it are measured; the words are a draft.

## Wording to be careful with

Checked against the sources on 10 October:

- Say "action level" for 4/m², not "safe limit". Still gives 4/m² as the guidance figure for a moving queue; the UK Green Guide's figure is 4.7/m² for standing areas.
- The Hajj timing is solid: Helbing and colleagues report the crush began more than 30 minutes after stop-and-go waves set in and about 10 minutes after turbulence began.
- Do not attribute the 6-minute exposure timer to anyone. It is our setting.
