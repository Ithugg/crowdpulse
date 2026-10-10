# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

A control-room operator at a concert, festival or stadium. They sit at a desk in the venue's operations room for the whole event, watching camera feeds and listening to staff radio, and they are responsible for telling zone staff what to do when a crowd starts to build. (Confirmed by the owner, 10 Oct 2026.)

Secondary audience, for one weekend only: two hackathon judges watching a 3-minute demo on a laptop from about a metre away.

## Product Purpose

CrowdPulse turns the cameras a venue already has into an early warning of crowd crush. It measures how densely people are packed in each zone, in real people per square metre, shows how that is changing and how the crowd is moving, and tells staff what to do before a zone becomes dangerous. Success is an operator who acts minutes earlier than they would have by watching the pictures alone.

## Positioning

The numbers are measurements, not impressions. The camera calibrates itself from the people in view (average height 1.7 m as the ruler), so density is in real people/m², walking speed is in real m/s, and each level on screen is a published crowd-safety threshold with its source. Nothing is typed in or scaled for effect.

## Operating Context

- An operations room: dim, several screens, radio traffic, long stretches where nothing happens and short stretches where seconds matter.
- Cameras are fixed, elevated and already installed. Zones are named places in the venue (a gate, a concourse, the area in front of a stage).
- When a zone crosses the safe limit the operator dispatches stewards by radio, may ask for a PA announcement, and later has to account for what happened in an incident log.
- The whole system runs on one laptop with no cloud dependency except the Gemini call for response plans, which has an offline fallback.

## Capabilities and Constraints

- Person detection (YOLOv8), automatic camera calibration, local density per zone, five research-based levels (Normal under 2, Busy 2–4, Caution 4–5, Danger 5–6, Critical 6 and above), forecast to the next level, time above the safe limit, walking speed and direction, gate inflow counts, safe capacity from measured floor area.
- Gemini writes the response plan (English and Spanish PA text, read aloud by the browser) and the incident report.
- Alerts can be acknowledged and marked dispatched; response times are recorded.
- Privacy mode pixelates every detected head; no video is stored.
- Real numbers only: the owner has ruled out tuned areas, multipliers and unlabelled simulated data.
- Must work offline and with system fonts only (no CDN assets); must hold a steady frame rate on a CPU-only laptop.
- Undecided: whether a clearly labelled drill (simulated incident) is allowed, so that the alert states can be demonstrated.

## Brand Commitments

- The name is CrowdPulse.
- The owner wants it to read as mission-critical operations software, with air traffic control displays, broadcast control rooms, the Bloomberg Terminal, emergency dispatch (CAD) systems and Formula 1 pit-wall telemetry as references, and explicitly not as a SaaS template: no purple or blue gradients, glass effects, emoji icons, uniformly rounded cards, giant hero headers or marketing copy.
- Colour is reserved for meaning: the safety states.
- Copy is operational and uses real units ("5.3 /m² · rising 0.4/min").

## Evidence on Hand

- Five working video sources in `media/` (two festival clips from Pexels, three MOT20 surveillance clips) and a live webcam source.
- Measured readings on those clips: 0.3 to about 2.8 people/m². Nothing in the footage reaches the 4/m² safe limit, so Caution, Danger and Critical have never appeared on screen with real data.
- Research sources for the thresholds: Fruin; G. K. Still; the UK Green Guide; Helbing, Johansson & Al-Abideen 2007; Helbing & Mukerji 2012.
- No customers, deployments, accuracy benchmarks or testimonials exist. Do not invent any.

## Product Principles

1. A reading is only worth showing if it is real and says how it was measured.
2. Quiet when things are normal; unmistakable when they are not.
3. Every alert comes with what to do next and who does it.
4. The operator must be able to trust it after hours of nothing happening.
5. Count people, never identify them.

## Accessibility & Inclusion

Safety states must not rely on colour alone (label and position carry them too). PA announcements are produced in English and Spanish.
