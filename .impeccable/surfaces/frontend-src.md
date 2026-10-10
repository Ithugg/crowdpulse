---
version: 1
slug: "frontend-src"
primary_target: "frontend/src"
related_targets: []
---

# Surface brief: the operations console (frontend/src)

Scope: the single screen of CrowdPulse. Visitor mode: Operate.

Audience and job: a control-room operator at a venue, at a desk for the whole event, deciding when to send stewards. Secondary this weekend: two judges watching a 3-minute demo on a laptop.

Content that must be present: live camera with measurement overlay; every zone's density, level, trend, people, capacity, flow and gate counts; forecast and time above the safe limit; alerts with acknowledge and dispatch; the Gemini response plan with English and Spanish PA text; the incident report; how the numbers are measured and their sources.

Constraints: real numbers only; offline apart from Gemini; steady on a CPU laptop; 1366×768 up to 1920×1080; keyboard-driven for the demo.

Unresolved: whether a labelled drill may be added so the alert states can be shown.

## Direction contract

THESIS: CrowdPulse is a terminal, not a dashboard. One black screen of keyed, tiled panels where each zone is a row of live measurements read like a market board, and the camera is one instrument among others. It refuses the category default: a top bar, a video, and a row of identical rounded metric cards.

OWN-WORLD: Bloomberg-terminal grammar translated for a venue control room. True black ground; gapless tiles divided by 1px hairlines; zero corner radius; no shadows; grey title strips; controls drawn as keycaps in inverse video. Warm-white ink, grey labels. Colour appears only for safety states (amber caution, orange danger, red critical, a small green lamp below the safe limit); cyan only for measurement drawn on the video. Selection is inverse video. Type is B612 and B612 Mono, the Airbus cockpit-display faces. Codes and states in capitals, prose in sentence case. State changes step; nothing fades.

STORY: the operator sees at a glance that every zone is below the safe limit, reads exact figures when they look closer, and when a zone crosses the limit the annunciator band takes over the screen with what happened and the keys to respond.

FIRST VIEWPORT: status line across the top (five-bar level mark, wordmark, camera code and name, readouts, clock). Below it a full-width annunciator band, quiet when normal. Then two columns. Left, about 60% wide: the camera with source tabs 1–6 in its title strip, and under it a 60-second strip chart of every zone against the threshold lines. Right: the zone board (rows with code, name, a 0–7 ruler ticked at 2, 4, 5, 6 with a pointer, the density numeral, and a detail line), then the response plan, then the event log. A key bar with a command line along the bottom. Primary action sits in the annunciator when alerting (ACK, DISPATCH, PLAN) and in the key bar otherwise.

SIGNATURE INTERACTION: the annunciator takeover with keyboard acknowledge, and the command line (C4, Z2, PLAN, REPORT, ACK, GRID). Motion grammar: two-frame steps only.

FORM: candidate 7 of 7 on the grounded list (Bloomberg Terminal), assigned by seed 0028c7e0; the amber base ink is translated to neutral because the brief reserves colour for safety states. Raised by the hand it beat: scale contrast as the only hierarchy device (type specimen); registration marks and a metric floor grid on the camera plate (design annual); short codes shared by overlay, board, log and commands (event catalog); stepped state changes (acetate manual); constant metric scale and a legend as a symbol table (orienteering map); focus on the alerting zone while the rest stay as context (transit diagram).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
