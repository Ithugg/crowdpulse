# CrowdPulse: submission record

Hacklanta 2026 (theme: Music Festival). Written Saturday 10 October 2026, in the evening, as a backup of everything that went into the submission and everything needed on Sunday. The same text is in the repository as `docs/SUBMISSION.md`.

## At a glance

| Item | Value |
|---|---|
| Project | CrowdPulse |
| Tagline | Crowd-crush early warning from the cameras a venue already has, in real people per square metre. |
| Team | Ismail El Ktiri El Idrissi and Abir Chowdhury |
| Repository (public) | https://github.com/Ithugg/crowdpulse |
| Release | Tag `v1.0-demo`; branches `revamp` and `main` are the same commit |
| Devpost | https://hacklanta.devpost.com/ : the owner reports it is submitted |
| Demo video | File on the laptop: `C:\dev\crowdpulse\brag-output-2026-10-10-180601\brag.mp4` (2 min 19 s). YouTube link: write it here |
| Google Form | Not yet filled in when this was written. The link is posted in the Hacklanta Discord |
| Tests | 349 pass |

## Deadlines (Eastern Time)

- Sunday 11 October, 9:00 AM: hacking ends. Devpost and the Google Form must both be in. No exceptions.
- Sunday 9:30 to 11:30 AM: judging expo, Student Center East State Ballroom. 3 minutes to pitch, 2 minutes of questions, two judges per table.
- Sunday 12:45 PM: closing ceremony, same room.
- All links (video, repository) must stay accessible throughout judging. Do not delete or re-upload the video, and do not rename the repository or the GitHub account.

## Tracks entered

One main track and the maximum of three side challenges.

- **Main track: Social Good (Cox).** Crowd safety at festivals, stations and campus events, from cameras a venue already owns, with no new hardware and no identification of anyone.
- **Mercedes: Best Application of Computer Vision.** The camera works out its own height and tilt from the people in view, so density is measured in real people per square metre instead of a raw head count; people are followed between frames for walking speed, direction and gate counts. The person detector is a pretrained YOLOv8, used as published; the calibration, density and tracking are our own code.
- **MLH: Best Use of Gemini API.** Gemini receives the measured numbers and the camera frame and returns a structured response plan and the incident report; a stored plan takes over if it cannot be reached.
- **Photon: Agents in iMessage.** An agent in iMessage, built on Photon's Spectrum SDK, that texts the staff on duty and takes their replies back into the control room.

Devpost's prize list only offers the MLH prizes, so only Gemini could be ticked there. Social Good, Mercedes and Photon have to be named on the Google Form. If the form has no place for them, ask an organiser.

## What was entered on Devpost

**Project name:** CrowdPulse

**Elevator pitch:** Crowd-crush early warning from the cameras a venue already has, in real people per square metre.

**About the project:** the full text is in the section "Devpost draft" further on (Inspiration, What it does, How we built it, Challenges, What we learned, What is next, Tracks, Disclosures, Instructions for judges). Two pieces were written after that draft and should also be in the description:

The problem and who it serves:

> Dangerous crowd density builds slowly and in plain sight, but nobody in the control room has a number for it: a camera wall shows pictures, not people per square metre. CrowdPulse is for the operator in an event control room and the safety officer they report to, and through them for the stewards on the ground, who get the alert and the plan on their phones. The people it protects are everyone in the crowd: at festivals, stadium concourses, transit stations on event nights and campus events. It needs no new hardware, only the cameras a venue already owns.

The video disclosure line:

> Demo video: every picture of the product is the real console, recorded on the demo laptop. It was assembled with Claude Code from the open-source `/brag` recipe: captions instead of a voice, and a synthesised soundtrack. The iMessage text in it is drawn from the recorded alert and plan in the agent's own format, not filmed on a phone; the phone screenshot in the gallery is the real thing.

**Built with (tags):** python, fastapi, opencv, yolov8, pytorch, gemini, photon, spectrum, node.js, react, typescript, vite, tailwindcss

**Try it out link:** https://github.com/Ithugg/crowdpulse

**Image gallery** (files in `docs\screens\`):

| File | Caption |
|---|---|
| `drill.png` | Drill mode: a simulated crowd, labelled as one, at critical with Gemini's plan. |
| `plaza-grid.png` | The camera calibrated itself from the people in view. The grid is 2 m squares. |
| `parade-plan.png` | The densest real footage reads Busy. Real readings, never scaled. |
| `drill-report.png` | The incident report from the drill, written from the alert log. |
| Phone screenshot | The CrowdPulse agent in iMessage, during a drill. |

**Additional info page:**

- Upload a file: none.
- Sponsor / special prizes: [MLH] Best Use of Gemini API.
- Universities or schools: entered by the owner.
- GoDaddy domain names: N/A.
- AI tools used: Anthropic (Claude Code, the coding assistant) and Gemini.
- Gemini project number: entered by the owner from Google AI Studio. It is the number made only of digits, not the project ID that starts with `gen-lang-client-`, and never the API key.

Feedback about technology:

> Gemini API: structured output (response_schema) meant every response plan came back in the same shape, so no parsing code was needed. The flash-lite models answered in about 1.5 seconds and were dependable; the full Flash models were overloaded and timed out several times on Saturday, so we put the lite models first and kept a stored fallback plan.
>
> Photon Spectrum: once it was set up, sending and receiving iMessages worked first time, and opening a chat from a phone number was one call. Setup on Windows was rough: the project template's cloud setup failed with "spawn npx ENOENT", and the starter did not load its own .env file, so we had to fill in the credentials by hand and add the loading ourselves.

Did you implement a generative AI model or API:

> Yes. CrowdPulse calls the Gemini API in two places. When a zone reaches the action level (4 people per square metre), Gemini receives the measured readings (density, level, trend, walking speed) together with the current camera frame, with heads blurred, and returns a structured response plan: a headline, numbered actions each assigned to a staff role, and a PA announcement in English and Spanish. The plan is rewritten when the zone climbs to a higher level. After the incident, Gemini turns the session's alert log, peak readings and staff response times into an incident report. We used it because a control-room operator under pressure needs specific instructions, not just a number, and because structured output guarantees the plan always arrives in the same shape. If Gemini cannot be reached within 12 seconds, a stored plan is shown instead and labelled as cached. Gemini does not measure anything: the density, levels, forecasts and alerts are computed locally by our own code.

## The Hacklanta checklist, item by item

| Required | Where it is |
|---|---|
| Project title and description | Devpost name, tagline and "What it does" |
| The problem and who it serves | "Inspiration" and the paragraph above |
| Team roster (max 4) | Devpost team section |
| Main track and side challenges | "Tracks" in the write-up, and the Google Form |
| Public GitHub repo with a useful README | https://github.com/Ithugg/crowdpulse |
| Working demo link or clear run instructions | README "Run it", and "Instructions for judges" |
| Short demo video of the project in action | The YouTube link, set to Public |
| Technologies, APIs, datasets, sponsor tools | "Built with" tags and "Disclosures" |
| Disclosure of anything made before Hacklanta | "Disclosures": nothing was |
| Test credentials or special instructions | "Instructions for judges": none needed |

## Still to do

1. Fill in the Google Form as soon as its link appears in Discord. Without it the project is not considered.
2. Check the Devpost page in a private browser window: the status is submitted (not draft), the video plays, the GitHub link opens.
3. Rehearse the three-minute pitch aloud twice with a timer. It is the section "Demo run-sheet" further on. It has never been spoken aloud.
4. Read the "Likely questions" in the run-sheet.
5. Press the `PA EN` key once to hear that the announcement is spoken.

## Sunday morning: starting everything

Laptop on mains power. Phone charged.

Start the console (it opens at http://localhost:8000):

```
powershell -ExecutionPolicy Bypass -File C:\dev\crowdpulse\scripts\start.ps1
```

Then, in a second terminal, start the iMessage agent and wait for "On duty from the start":

```
cd C:\dev\crowdpulse\hacklanta
npm run start
```

Then check, in this order:

1. Browser full screen (`F11`), zoom 100%.
2. Press `2`, `3`, `4`, `5`, `7` once each so every source has been opened.
3. Press `3`, then `P`: the Response strip should say `GEMINI`, not `CACHED PLAN`.
4. Text "status" to the CrowdPulse line: the agent should answer with the readings.
5. Press `1` and point the camera at where the judges will stand.

The agent needs the network and the console. If it fails, the console is unaffected: skip the phone beat.

## The keys

| Key | What it does |
|---|---|
| `1` | Live webcam |
| `2` to `6` | The recorded clips (2, 3 and 6 are replays, tagged `REPLAY`) |
| `7` | The drill: simulated crowd, labelled `DRILL: SIMULATED READINGS` |
| `G` | The measured 2 m floor grid |
| `B`, `H`, `V` | Boxes, heat tint, privacy blur (on by default) |
| `P` | Ask Gemini for a plan now |
| `A`, `D` | Acknowledge the alert; mark staff dispatched (texts the phone on duty) |
| `I` | Incident report |
| `S` | Sources and what can be wrong with the numbers |
| `R` | Restart the current camera with a clean log |

The drill's clock, from the moment `7` is pressed: busy at 5 seconds, forecast at 30, action level (Caution) at about 46, danger at about 60, critical at about 75, cleared at about 3 minutes, repeating every 4 minutes.

## The iMessage agent in one paragraph

A small Node program in `hacklanta\`, built on Photon's Spectrum SDK. It listens to the console's WebSocket and to iMessage. The phone listed in `hacklanta\.env.local` (not in the repository) is on duty from the start; anyone else on the Photon project's Users list goes on duty by texting the line once. It texts every alert from the action level up, forecasts, "cleared", each plan Gemini writes, and every dispatch with the plan. Replies it understands: "status", "plan", "ack", "on my way", "off duty". "ack" and "on my way" are logged on the console with the response time. It cannot place phone calls. The credentials are in `hacklanta\.env`, which is never committed.

## What is real and what is simulated

- Every reading from a camera or a clip is measured. Nothing is scaled, and there are no demo thresholds. The densest real clip reads about 2 people per square metre: Busy, below the action level of 4.
- Anything orange or red, in the console, the screenshots or the video, is the drill: scripted people on a virtual floor, seen by a virtual camera, measured by the same code. It is labelled on the screen, the log, the plan, the report and the texts.
- The detector under-reads packed crowds: in a real festival clip it found about 80 of several hundred people. The honest next step is a crowd-counting model built for dense scenes.
- 4 people per square metre is called the action level, never a safe limit. The 6-minute exposure timer is our own setting, not a published rule.
- The person detector is pretrained (YOLOv8) and was not trained by us.

## Where everything is

| Path | What |
|---|---|
| `C:\dev\crowdpulse` | The project on the demo laptop |
| `docs\RUNSHEET.md` | The three-minute pitch, key by key, with fallbacks and likely questions |
| `docs\DEVPOST.md` | The Devpost text |
| `docs\VIDEO.md` | The video script and how to record |
| `docs\HANDOFF.md` | Running notes on the state of the project |
| `docs\screens\` | Screenshots |
| `brag-output-2026-10-10-180601\brag.mp4` | The demo video (not in the repository) |
| `hacklanta\` | The iMessage agent |
| `.env`, `hacklanta\.env`, `hacklanta\.env.local` | The Gemini key, the Photon credentials and the on-duty phone. Never committed, never shared |
