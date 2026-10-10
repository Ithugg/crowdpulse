# Devpost draft

Paste each section into the matching Devpost field. Read it once out loud first and change anything that does not sound like you.

**Name:** CrowdPulse

**Tagline:** Crowd-crush early warning from the cameras a venue already has, in real people per square metre.

**Track:** Social Good (Cox). **Side challenges (the maximum of three):** Mercedes: Best Application of Computer Vision; MLH: Best Use of Gemini API; Photon: Agents in iMessage.

**Why each one fits** (one line each, for the Devpost form and the Google Form):
- Social Good: crowd safety at festivals, stations and campus events, from cameras a venue already owns, with no new hardware and no identification of anyone.
- Computer vision: the camera works out its own height and tilt from the people in view, so density is measured in real people per square metre instead of a raw head count; people are followed between frames for walking speed, direction and gate counts. The person detector is a pretrained YOLOv8, used as published; the calibration, density and tracking are my own code.
- Gemini: it receives the measured numbers and the camera frame and returns a structured response plan and the incident report; a stored plan takes over if it cannot be reached.
- Photon: an agent in iMessage, built on Spectrum, that texts the staff on duty and takes their replies back into the control room.

## Inspiration

Ten people died at Astroworld in 2021. More than 150 died in Itaewon in 2022. Both happened in front of cameras.

Crowd scientists have known the numbers for decades. At about 4 people per square metre a control room should already be acting. At about 6, people can no longer keep their footing. When Dirk Helbing's group went back through the video of the 2006 Hajj disaster, the warning signs were visible more than 30 minutes before the crush.

So the information exists and the cameras exist. What is missing is something that reads the number off the picture and tells staff what to do. I wanted to see how far one person could get on that in a weekend.

## What it does

CrowdPulse takes a webcam or a video feed and turns it into a control-room console.

- It finds every person in the frame.
- It works out the scale of the scene by itself. People are about 1.7 m tall, so how tall they appear at each height in the picture gives the camera's height and tilt. On the plaza clip it finds a camera 8.4 m up, looking 33° down, and it can draw the floor as a grid of 2 m squares to prove it.
- From that it measures density in each zone in real people per square metre, how fast the crowd is walking in metres per second, which way it is moving, and how many people cross a gate line per minute.
- Each zone is rated against published crowd-safety levels (2, 4, 5 and 6 people/m²), with a forecast of when it will reach the next one.
- When a zone crosses the action level, Gemini gets the numbers and the camera frame and writes the response plan: who does what, in order, plus a PA announcement in English and Spanish that the console can read aloud. If the zone keeps climbing, the plan is rewritten for each new level, and the old one stays on screen until the new one arrives.
- The operator acknowledges the alert and dispatches staff. Response times are logged, and one key writes the incident report afterwards.
- The same alert reaches staff where they already are: a CrowdPulse agent in iMessage, built on Photon's Spectrum SDK, texts the people on duty the alert, Gemini's plan and every dispatch. They answer in plain words ("status", "plan", "ack", "on my way"), and "on my way" is logged on the console as the dispatch with its response time.
- Every head is blurred before the video is shown. It counts people. It does not identify them, and no video is stored.
- A drill mode shows what happens above the action level: a simulated crowd fills one zone past critical, the forecast and alerts fire, and Gemini writes the plan. It is labelled DRILL: SIMULATED READINGS on screen and on everything it produces.

## How I built it

Python does the work: OpenCV for capture, a pretrained YOLOv8 model for person detection, and my own code for calibration, local density, tracking, forecasting and alerts. FastAPI serves one WebSocket that carries the readings as JSON and the video as JPEG frames. The console is React and TypeScript, built to static files so the whole thing starts with one command and runs on a laptop with no GPU.

The density measure is the Gaussian-kernel local density from Helbing, Johansson and Al-Abideen's 2007 Hajj study, and a zone's reading is its local peak, because an average over a big area hides a dangerous pocket.

Gemini is called with structured output, so the plan always comes back as a headline, numbered actions with a role for each, and the two announcements. If the network is down, a stored plan appears instead and is labelled as such.

The iMessage agent is a small separate Node program built on Spectrum. It listens to the same WebSocket as the console and sends back the same commands the keyboard does, so if it or the network fails, the console carries on untouched.

The console is meant to look like control-room software: black, dense, keyboard-driven, and colour is used only for a safety state.

## Challenges

**Getting an honest square metre.** My first version had zone areas typed into a config file, and the densities were whatever I made them. I threw that out and wrote the self-calibration. It is the part I am proudest of and the part that took longest.

**Refusing to fake the demo.** With real measurements, none of my footage is dangerous. The densest clip, a festival street parade, reads about 2 people/m². It was tempting to scale the numbers until something turned red. I did not, and the console says "no zone above the action level" because that is the truth about those clips. To show what the product is for, I built a drill instead: scripted people on a virtual floor, seen by a virtual camera and run through the same measurement and alert code as the real cameras. It is a separate source, it never touches a real reading, and the word DRILL is on the screen, the log, the plan and the report, added in code so it does not depend on the AI remembering.

**Checking my own sources.** Two things in my notes turned out to be wrong when I went back to the papers: the UK Green Guide does not give 4/m² as a "safe limit" (its figure is 4.7 for standing areas), and I could not find a published "6-minute rule". Both are fixed in the app and the README.

**A laptop with no GPU.** Dense scenes are precomputed with a larger model and played back in sync with the clip, with a REPLAY badge on screen. The webcam and the lighter clips run live.

## What I learned

How crowd crushes actually happen: it is pressure and flow, not panic. Enough camera geometry to recover a floor plan from people's heights. And that writing down what can be wrong with your numbers makes them easier to believe.

## What is next

- A crowd-counting model built for packed scenes. Detectors miss people who are hidden behind others, so readings run low exactly when it matters most.
- Checking the gate counts and densities against hand-labelled ground truth.
- Entering each camera's real lens angle, which is the one thing the video cannot tell us.
- A trial at a real venue: a stadium concourse, a transit station on event night, a campus event.

## Built with

Python, FastAPI, OpenCV, Ultralytics YOLOv8 (pretrained COCO weights, not trained by me), PyTorch, Google Gemini API, Photon Spectrum (iMessage), Node.js, React, TypeScript, Vite, Tailwind CSS, B612 typeface.

## Disclosures (required)

- Pretrained model: Ultralytics YOLOv8 (`yolov8n`, `yolov8s`), used as published. No model was trained or fine-tuned.
- API: Google Gemini, for response plans and incident reports.
- SDK and service: Photon Spectrum (`spectrum-ts`, MIT) and Photon's hosted iMessage line, for the staff messages. The agent was started from Photon's project template.
- Footage: two Pexels clips (Pexels License) and three MOT20 sequences (CC BY-NC-SA 3.0). Sources are listed in `media/SOURCES.md`.
- Simulated data: the drill (source 7) is a scripted crowd on a virtual floor, not footage and not a measurement. It is labelled as a drill on screen and on everything it produces. Anything red or orange in the screenshots and the video is the drill.
- AI coding assistant: Claude Code (Anthropic) was used throughout development.
- Demo video: every picture of the product is the real console, recorded on the demo laptop. It was assembled with Claude Code from the open-source `/brag` recipe: captions instead of a voice, and a synthesised soundtrack. The iMessage text in it is drawn from the recorded alert and plan in the agent's own format, not filmed on a phone; the phone screenshot in the gallery is the real thing.
- All code in the repository was written during Hacklanta 2026.

## Instructions for judges

- To run it: Windows, Python 3.11 to 3.13 and Node.js 20 or newer, then the two commands under "Run it" in the README. No account or login is needed. Without a Gemini key it still runs and shows stored plans tagged `CACHED PLAN`.
- Key `7` starts the drill; the action level is reached about 46 seconds later. Key `S` lists every source and what can be wrong with the numbers.
- The iMessage agent cannot be texted by judges directly: Photon's line only answers phones that are on the project's Users list. It is shown in the demo video and live at the judging table. To run your own, follow "Staff messages in iMessage" in the README with a free Photon project.
- No test credentials are needed.

## Links to fill in

- Repository: https://github.com/Ithugg/crowdpulse
- Demo video (2 to 3 minutes, public): _add link_
- Screenshots to upload, all taken on the demo laptop at its real screen size, in `docs/screens/`:
  - `plaza-grid.png`: a real clip with the measured 2 m floor grid. Caption: "The camera calibrated itself from the people in view."
  - `parade-plan.png`: the densest real footage, reading Busy, with Gemini's readiness plan. Caption: "Real readings, never scaled."
  - `drill.png`: the drill at critical with Gemini's plan. Caption must say it is a drill: "Drill mode: a simulated crowd, labelled as one."
  - `drill-report.png`: the incident report from the drill. Same rule for the caption.
- The demo video file is `brag-output-2026-10-10-180601/brag.mp4` on the laptop (2 minutes 19 seconds, 86 MB, not in the repository). Its plan, with what is and is not real in it, is `brag-plan.md` in the same folder. A 22-second version is in `brag-output-2026-10-10-153310/`.
