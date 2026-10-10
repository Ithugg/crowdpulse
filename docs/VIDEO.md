# Demo video: script and how to record it

About 2 minutes 20 seconds. The rules ask for 2 to 3 minutes, public link. The timing is fixed by the drill: it reaches the action level 46 seconds after `7` and critical at 75 seconds, so the keys below are placed around that.

## Before recording

1. Laptop on mains power. Console running (`scripts\start.ps1`), browser full screen (`F11`), zoom 100%.
2. iMessage agent running in a second terminal: `cd C:\dev\crowdpulse\hacklanta; npm run start`. Wait for "On duty from the start".
3. Press `5` (East Plaza). Make sure the floor grid is off (`G` toggles it).
4. **Do not press `1` while recording.** The recorder is using the webcam for your face; the console cannot have it at the same time.
5. Phone unlocked, Messages open on the CrowdPulse line, within reach. Turn on Do Not Disturb on the laptop.
6. Press `3`, then `P`, and check the Response strip says `GEMINI`, not `CACHED PLAN`. Then `5` again.

## The script

| Time | Key | Say |
|---|---|---|
| 0:00 | – | "Ten people died at Astroworld. More than 150 in Itaewon. Both happened in front of cameras. Crowd scientists know the numbers: at 4 people per square metre staff should already be acting. At 6, people cannot keep their footing. This is CrowdPulse. It reads that number off the cameras a venue already has." |
| 0:22 | `G` | "A real camera over a real plaza. Nobody measured this floor. CrowdPulse used the people as a ruler and worked out that the camera is 8.4 metres up, looking 33 degrees down. That grid is 2-metre squares, so this is real people per square metre. And every head is blurred: it counts people, it never identifies them." |
| 0:45 | `G`, then `7` | "None of the real footage is dangerous, and a real reading is never scaled to make it turn red. So this is a drill, and it says so on the screen: a simulated crowd, measured by the same code. Watch the front barrier fill. Each zone is rated against published safety levels, with a forecast from the trend." |
| 1:15 | – | (The log shows "projected to reach Caution".) "There. It forecasts the action level before it happens." |
| 1:31 | – | (The band turns orange and flashes; a plan appears; the phone buzzes.) "Action level. The band flashes until someone answers, and Gemini has already written the plan: who does what, in order, with an announcement in English and Spanish." |
| 1:42 | `A`, `D` | "Acknowledge. Dispatch." Hold the phone up to the camera. "And dispatch does not stay in this room. The CrowdPulse agent lives in iMessage: it has just texted the steward on duty, with the plan. They can reply 'status' or 'on my way', and the response time is logged." |
| 2:00 | – | (The band is red: `CRITICAL`.) "Six per square metre. The plan rewrote itself at each level." |
| 2:07 | `I` | "Afterwards, one key writes the incident report from the log." Then `Esc`. |
| 2:13 | – | "One laptop, the cameras you already own, and no video leaves the building. CrowdPulse watches the numbers." |

If you are late pressing `7`, everything after it moves by the same amount: the forecast is 30 seconds after `7`, the action level 46, critical 75. If a take goes wrong, press `R` on the drill for a clean log, then `5`, and start again.

## Recording with your face in the corner (Clipchamp, already on Windows 11)

1. Start menu, open **Clipchamp**, sign in with a Microsoft account, **Create a new video**.
2. Left side: **Record & create**, then **Screen and camera**. Allow the camera and the microphone.
3. Press the red record button, choose **Entire screen**, then **Share**.
4. Switch to the console (`Alt+Tab`), and do the script.
5. Switch back, **Stop sharing**, then **Save and edit**. The screen and your face arrive as two layers: drag the face to a corner and shrink it so it does not cover the alert band at the top, the `DRILL` label or the plan.
6. Trim the start and the end, then **Export** at 1080p.
7. Upload to YouTube with visibility **Public**. Open the link in a private window to check it plays, then paste it into Devpost.

If Clipchamp will not record, `Win+Alt+R` (Xbox Game Bar) records the browser window with your voice but without your face. The rules do not require a face.
