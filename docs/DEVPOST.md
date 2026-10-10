# Devpost draft

Paste each section into the matching Devpost field. Read it once out loud first and change anything that does not sound like you.

**Name:** CrowdPulse

**Tagline:** Crowd-crush early warning from the cameras a venue already has, in real people per square metre.

**Track:** Social Good (Cox). **Side challenge:** Best Use of Gemini API.

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
- When a zone crosses the action level, Gemini gets the numbers and the camera frame and writes the response plan: who does what, in order, plus a PA announcement in English and Spanish that the console can read aloud.
- The operator acknowledges the alert and dispatches staff. Response times are logged, and one key writes the incident report afterwards.
- Every head is blurred before the video is shown. It counts people. It does not identify them, and no video is stored.

## How I built it

Python does the work: OpenCV for capture, a pretrained YOLOv8 model for person detection, and my own code for calibration, local density, tracking, forecasting and alerts. FastAPI serves one WebSocket that carries the readings as JSON and the video as JPEG frames. The console is React and TypeScript, built to static files so the whole thing starts with one command and runs on a laptop with no GPU.

The density measure is the Gaussian-kernel local density from Helbing, Johansson and Al-Abideen's 2007 Hajj study, and a zone's reading is its local peak, because an average over a big area hides a dangerous pocket.

Gemini is called with structured output, so the plan always comes back as a headline, numbered actions with a role for each, and the two announcements. If the network is down, a stored plan appears instead and is labelled as such.

The console is meant to look like control-room software: black, dense, keyboard-driven, and colour is used only for a safety state.

## Challenges

**Getting an honest square metre.** My first version had zone areas typed into a config file, and the densities were whatever I made them. I threw that out and wrote the self-calibration. It is the part I am proudest of and the part that took longest.

**Refusing to fake the demo.** With real measurements, none of my footage is dangerous. The densest clip, a festival street parade, reads about 2 people/m². It was tempting to scale the numbers until something turned red. I did not, and the console says "no zone above the action level" because that is the truth about those clips.

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

Python, FastAPI, OpenCV, Ultralytics YOLOv8 (pretrained COCO weights, not trained by me), PyTorch, Google Gemini API, React, TypeScript, Vite, Tailwind CSS, B612 typeface.

## Disclosures (required)

- Pretrained model: Ultralytics YOLOv8 (`yolov8n`, `yolov8s`), used as published. No model was trained or fine-tuned.
- API: Google Gemini, for response plans and incident reports.
- Footage: two Pexels clips (Pexels License) and three MOT20 sequences (CC BY-NC-SA 3.0). Sources are listed in `media/SOURCES.md`.
- AI coding assistant: Claude Code (Anthropic) was used throughout development.
- All code in the repository was written during Hacklanta 2026.

## Links to fill in

- Repository: https://github.com/Ithugg/crowdpulse
- Demo video (2 to 3 minutes, public): _add link_
