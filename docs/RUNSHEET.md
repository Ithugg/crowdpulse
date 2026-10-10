# Demo run-sheet (3 minutes + 2 minutes Q&A)

Everything is on the keyboard. Practise it twice with a timer; cut words, not steps.

## Before the judges arrive

1. Laptop on mains power, browser full screen (`F11`), zoom at 100%.
2. `powershell -ExecutionPolicy Bypass -File scripts\start.ps1`, wait for the console.
3. Press `2`, `3`, `4`, `5` once each so every clip has been opened, then `1`.
4. Press `3`, then `P`. Check the tag in the Response strip says `GEMINI` and not `CACHED PLAN`. If it says cached, the Wi-Fi is down: carry on, the demo still works.
5. Press `R` to clear the log, then `1`. Point the laptop's camera at where the judges will stand.

## The three minutes

| Time | Key | What is on screen | What to say |
|---|---|---|---|
| 0:00 | – | Console, webcam | "Ten people died at Astroworld. More than 150 in Itaewon. Crowd scientists have published the danger levels for decades: at 4 people per square metre a control room should already be acting, and at 6 people cannot keep their footing. The cameras were already there. Nobody was watching the numbers." |
| 0:25 | `1` | Judges on camera, counted, faces blurred | "This is live. It is counting you. Faces are blurred by default: CrowdPulse counts people, it never identifies them." |
| 0:45 | `5` then `G` | East Plaza with the 2 m floor grid | "A real camera over a real plaza. Nobody measured this floor. The system used the people as a ruler, about 1.7 metres each, and worked out that the camera is 8.4 metres up, looking 33 degrees down. That grid is 2-metre squares. So this number is real people per square metre, and that is real walking speed." |
| 1:15 | `G`, `3` | Festival Street Parade, Parade Front reads Busy | "A festival street parade, the densest footage we have. About 2 people per square metre: busy, below the action level of 4, and the system says so. It has logged it." Point at the Log. |
| 1:35 | `A`, `D` | Log shows acknowledged, dispatched, with seconds | "The operator acknowledges and dispatches staff. Response time is recorded." |
| 1:45 | `P` | Response plan appears, tag `GEMINI`, headline "Readiness plan…" | "Gemini gets the numbers and the camera frame and writes the plan: who does what, in order. This zone is below the action level, so it is a readiness plan: what to watch, and the reading at which staff must act. And the PA announcement in English and Spanish." Press the `PA EN` key so it speaks. |
| 2:10 | `I` | Incident report | "After the event, one key writes the incident report from the log." `Esc`. |
| 2:25 | `S` | Science sheet | "Every level on this screen is a published threshold with its source. And this is what can be wrong with our numbers." `Esc`. |
| 2:40 | `3` | Back on the console | "It runs on one laptop with the cameras a venue already owns. Stadiums, MARTA stations, campus events. At the Hajj in 2006 the warning was on video more than thirty minutes before the crush. CrowdPulse watches the numbers." |

## If something goes wrong

| Problem | Do this |
|---|---|
| Webcam shows nothing | Skip it: press `5` and start from the plaza. Say "live camera works the same way". |
| Plan tag says `CACHED PLAN` | Say "the venue Wi-Fi is down, so it used the stored plan; it never leaves the operator with nothing". |
| No sound from the PA key | Read the announcement aloud yourself. (Spanish needs the Windows Spanish voice installed.) |
| A clip looks frozen | Press `R`. |
| The page is blank | Refresh. If still blank, restart `scripts\start.ps1` (about 15 seconds). |

## Likely questions

- **"How do you know the square metres?"** The camera calibrates itself from the people in view, assuming an average height of 1.7 m and a 60° lens. On the test clips it predicts how tall people appear to within 6–9%. A real installation would enter each camera's lens once.
- **"Why is nothing red?"** Because nothing in this footage is dangerous, and we do not fake it. The densest clip reads about 2 people per square metre against an action level of 4.
- **"Does it work in a packed crowd?"** The detector misses people who are hidden behind others, so it reads low exactly when it matters most. The next step is a crowd-counting model built for dense scenes.
- **"What about privacy?"** Heads are blurred before the video is shown, nothing is recorded, and no one is identified or tracked across cameras.
- **"What did you use?"** YOLOv8 (pretrained, not trained by us) for detection, the Gemini API for plans and reports, OpenCV, FastAPI, React. Levels from Fruin, G. Keith Still and Helbing's Hajj study; the UK Green Guide's own figure is 4.7 per square metre for standing areas.

## Not yet checked on the demo laptop

The webcam with real people, the laptop's frame rate, and the spoken announcement. Do all three before the first judge.

## Wording to be careful with

Checked against the sources on 10 October:

- Say "action level" for 4/m², not "safe limit". Still gives 4/m² as the guidance figure for a moving queue; the UK Green Guide's figure is 4.7/m² for standing areas.
- The Hajj timing is solid: Helbing and colleagues report the crush began more than 30 minutes after stop-and-go waves set in and about 10 minutes after turbulence began.
- Do not attribute the 6-minute exposure timer to anyone. It is our setting.
