---
name: CrowdPulse
description: Operations console for crowd density. A terminal, not a dashboard.
colors:
  ink: "#e9e4d6"
  ok: "#35b877"
  caution: "#ffb000"
  danger: "#ff6b00"
  critical: "#ff3030"
  measure: "#56c8f0"
  ground: "#000000"
  lift: "#0d0d0c"
  strip: "#161614"
  rule: "#2c2b27"
  rule-strong: "#4b4940"
  label: "#a39e8d"
  faint: "#7a7667"
typography:
  numeral-lead:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tabular-nums"
  numeral:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tabular-nums"
  alert:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.04em"
  wordmark:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 700
    letterSpacing: "0.1em"
  sheet-title:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.3
  headline:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: 1.3
  prose:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.4
  body:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
  name:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.05em"
  label:
    fontFamily: "B612, Bahnschrift, DIN Alternate, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    letterSpacing: "0.06em"
  code:
    fontFamily: "B612 Mono, Cascadia Mono, Consolas, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: "16px"
    letterSpacing: "0"
rounded:
  none: "0"
spacing:
  hairline: "1px"
  keycap-pad: "4px"
  key-gap: "6px"
  strip-pad: "8px"
  body-pad: "10px"
  cell-pad: "12px"
  band-gap: "16px"
components:
  statusline:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    height: "34px"
    padding: "0 12px"
  annunciator:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.label}"
    typography: "{typography.body}"
    height: "40px"
    padding: "0 12px"
  annunciator-alert:
    backgroundColor: "{colors.critical}"
    textColor: "{colors.ground}"
    typography: "{typography.alert}"
    height: "40px"
    padding: "0 12px"
  tile:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
  strip:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.label}"
    typography: "{typography.label}"
    height: "24px"
    padding: "0 8px"
  tag:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
    typography: "{typography.code}"
    rounded: "{rounded.none}"
    padding: "0 4px"
  tag-hollow:
    backgroundColor: "transparent"
    textColor: "{colors.label}"
    typography: "{typography.code}"
    padding: "0 4px"
  tag-alerting:
    backgroundColor: "{colors.caution}"
    textColor: "{colors.ground}"
    typography: "{typography.code}"
    padding: "0 4px"
  key:
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    height: "20px"
  keycap:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
    typography: "{typography.code}"
    rounded: "{rounded.none}"
    padding: "0 4px"
  keycap-hover:
    backgroundColor: "#ffffff"
    textColor: "{colors.ground}"
  keycap-active:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ground}"
  keycap-off:
    backgroundColor: "transparent"
    textColor: "{colors.label}"
  keycap-disabled:
    backgroundColor: "{colors.rule-strong}"
    textColor: "{colors.ground}"
  tab:
    textColor: "{colors.label}"
    typography: "{typography.label}"
    padding: "0 9px"
  tab-hover:
    textColor: "{colors.ink}"
  tab-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
    typography: "{typography.label}"
    padding: "0 9px"
  tab-disabled:
    textColor: "{colors.rule-strong}"
  lamp:
    backgroundColor: "{colors.ok}"
    rounded: "{rounded.none}"
    size: "8px"
  block:
    backgroundColor: "rgb(0 0 0 / 0.8)"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: "1px 5px 2px"
  block-alerting:
    backgroundColor: "{colors.critical}"
    textColor: "{colors.ground}"
  block-gate:
    backgroundColor: "rgb(0 0 0 / 0.8)"
    textColor: "{colors.measure}"
  zone-row:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    padding: "7px 10px 6px 8px"
  zone-row-selected:
    backgroundColor: "{colors.lift}"
    textColor: "{colors.ink}"
    padding: "7px 10px 6px 8px"
  ruler:
    backgroundColor: "{colors.rule-strong}"
    textColor: "{colors.label}"
    typography: "{typography.label}"
    height: "21px"
  keybar:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.ink}"
    height: "28px"
    padding: "0 8px"
  command-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.code}"
    padding: "0 0 0 12px"
  sheet:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    typography: "{typography.prose}"
    rounded: "{rounded.none}"
    width: "min(720px, calc(100vw - 32px))"
  sheet-foot:
    backgroundColor: "{colors.strip}"
    padding: "6px 10px"
---

# Design System: CrowdPulse

Recorded from the shipped console (`frontend/src/index.css` and `frontend/src/components/*.tsx`) on 10 Oct 2026. Every value below appears in that stylesheet. Tokens are Tailwind v4 `@theme` custom properties (`--color-*`, `--font-*`); spacing, sizes and heights are literals in the component classes.

## Overview

**Creative North Star: "A terminal, not a dashboard"**

CrowdPulse is a terminal, not a dashboard. One true-black screen of gapless tiles divided by 1px hairlines, read like a market board by an operator who sits in front of it for a whole event. There is no radius, no cast shadow, no gradient and no card: a tile is a rectangle of ground with a grey title strip, and the camera is one instrument among the others.

Hierarchy comes from scale and from inverse video, never from colour. Ink is a warm white; labels are grey. Colour is held back for the safety levels, so that when a zone crosses the action level the amber, orange or red on screen is the only colour there is. Cyan is the one other hue, and it belongs to measurement drawn on the video. Every control is a keycap plus a word, because the console is driven from the keyboard.

State changes step. Lamps blink in two hard frames, the annunciator band flips between colour-on-black and black-on-colour, and the ruler pointer jumps in steps. Nothing fades, eases or slides.

**Key Characteristics:**
- True black ground, gapless tiles, 1px hairlines.
- Zero radius, no cast shadows, no gradients.
- Colour means a safety level; cyan means a measurement on the video.
- Selection and emphasis are inverse video.
- Controls are keycaps; every action has a key and a command word.
- Codes and states in capitals, prose in sentence case.
- Stepped motion only.

## Colors

Eight warm neutrals from black to off-white carry the whole interface; five hues are reserved for meaning.

### Primary
- **Ink** (`ink` #e9e4d6): all primary text and numerals, and the fill of everything in inverse video: solid tags, keycaps, the selected camera tab, the focus ring, the text selection, the typing cursor, the selected trace line.

### Secondary
The safety signals. Each is set by one `data-level` attribute, which defines `--lv` (text and pointer colour) and `--lamp` (lamp and fill colour) for everything inside it.
- **Caution amber** (`caution` #ffb000): density from the action level up to danger.
- **Danger orange** (`danger` #ff6b00): the danger level.
- **Critical red** (`critical` #ff3030): the critical level.
- **OK green** (`ok` #35b877): lamps only, an 8px square meaning "below the action level". Never text, never a fill larger than a lamp.

At normal and busy, `--lv` is ink: figures and state words stay neutral and only the lamp is green. From caution upward the state word, the numeral, the ruler pointer, the row's tag, the zone outline and its 16% fill on the video, the trace line and the annunciator band all take the level colour. Level colour as a background always carries black text.

### Tertiary
- **Measure cyan** (`measure` #56c8f0): measurement drawn on the video and its echo on the board: gate lines (1.5px, dashed 6 5), gate blocks (cyan text, 1px cyan outline), the gate name in a zone's detail line, and the floor grid the server draws into the frame.

### Neutral
- **Ground** (`ground` #000000): the screen, every tile, sheets, and text on any ink or level-colour fill.
- **Lift** (`lift` #0d0d0c): background of the selected zone row. The only tonal step above ground inside a tile.
- **Strip** (`strip` #161614): title strips, the key bar, sheet footers.
- **Rule** (`rule` #2c2b27): hairlines between tiles, rows, cells and table lines.
- **Rule strong** (`rule-strong` #4b4940): outlines of hollow tags and off keycaps, the ruler base and minor ticks, chart axes, the sheet border, scrollbar thumb, disabled tabs and disabled keycaps.
- **Label** (`label` #a39e8d): secondary text: strip text, units, detail lines, axis labels, timestamps, off toggles, placeholder.
- **Faint** (`faint` #7a7667): status-line field labels, step numbers, unlit bars of the level mark, unselected trace lines, disabled key words.

Two translucent blacks sit over imagery: `rgb(0 0 0 / 0.8)` behind blocks and the in-view readout on the video, and `rgb(0 0 0 / 0.72)` as the sheet backdrop.

### Named Rules
**The Reserved Colour Rule.** Hue is a safety state. Amber, orange and red appear only when a zone is at caution, danger or critical; green appears only as a lamp. The one exception is a fault in the console itself (lost link, camera error, rejected command), which is shown in amber. No hue is used for branding, decoration, categories or emphasis.

**The Measurement Cyan Rule.** Cyan marks something measured and drawn on the video, and the board's reference to it. It is never a link, a selection or an accent.

**The Inverse Video Rule.** Selected, pressed-on and primary are shown by swapping ink and ground, not by adding a colour.

**The Not Colour Alone Rule.** Every level also has a word (NORMAL, CAUTION, DANGER, CRITICAL), a position on the ruler and a numeral size. The legend shows non-alerting levels as hollow squares.

## Typography

**Display and body font:** B612 (fallback Bahnschrift, DIN Alternate, system-ui, sans-serif), weights 400 and 700.
**Code font:** B612 Mono (fallback Cascadia Mono, Consolas, ui-monospace, monospace), weights 400 and 700.

**Character:** the Airbus cockpit-display faces, built for small sizes on dark screens. Both are bundled with the app (`@fontsource/b612`, `@fontsource/b612-mono`), so the console renders the same with no network.

### Hierarchy
- **Numeral lead** (700, 34px, line-height 1, tabular): the density figure of a zone at danger or critical; the selected zone's figure only while no zone is that serious.
- **Numeral** (700, 22px, line-height 1, tabular): every other zone's density figure.
- **Alert** (700, 18px, 0.04em): the annunciator band while alerting.
- **Wordmark** (700, 17px, 0.1em, capitals): CROWDPULSE in the status line.
- **Sheet title** (700, 15px, 1.3): the heading of a sheet.
- **Headline** (700, 14px, 1.3): the headline of a response plan.
- **Prose** (400, 12.5px, 1.4; 1.5 in sheets, max 68ch): plan steps, PA text, sheet paragraphs and tables.
- **Body** (400, 12px, 1.4): the base size. **Name** is the same size at 700, 0.05em, capitals, for zone and camera names.
- **Label** (400 or 700, 11px, 0.06em, capitals): strips, keys, tabs, state words, field labels, table headers. The same 11px without capitals or tracking carries units, detail lines, axis labels and timestamps.
- **Code** (B612 Mono 700, 11px, line-height 16px, no tracking): tags, keycaps, the command line (0.04em there), step numbers.

### Named Rules
**The Scale Is Hierarchy Rule.** The largest thing on the board is the most serious zone's figure. Size is earned by severity or selection, not by position.

**The Capitals Rule.** Codes, names, states and key words are capitals; anything a person reads as a sentence is sentence case. A strip's explanatory phrase ("last 60 s, people/m²") is sentence case with no tracking.

**The Tabular Rule.** Every number that changes uses tabular figures.

## Layout

One screen, no page scroll at 1024px and above. The frame is a four-row grid: status line (34px), annunciator (40px), tiles (the remaining height), key bar (28px).

The tiles are two columns, `minmax(0, 1.55fr)` and `minmax(400px, 1fr)`. Left: camera, then the strip chart. Right: zone board, response, log. Tiles are packed with a 1px gap over a rule-coloured parent, so the gap is the hairline; a tile has no border, margin or padding of its own. Each tile opens with a 24px strip.

Spacing is tight and literal: 4px inside keycaps and tags, 6px between a keycap and its word, 8px strip and row insets, 9px 10px tile body, 12px status-line cells, 14px between keys in the key bar, 16px between items in the annunciator and in a sheet's footer. Rows are divided by a 1px rule, never by space.

Fixed tracks: zone row `26px / 1fr / 92px` with an 8px column gap; strip chart `1fr / 104px`; plan steps `18px / 1fr`; log row `auto / 8px / 1fr / auto`, minimum 24px high.

Below 1024px the console becomes one scrolling column: the tiles stack, the status line, annunciator and key bar wrap to their content height, video blocks collapse to their code unless selected, scrolling tiles cap at 50vh and the strip chart keeps 150px.

## Elevation & Depth

Flat. There are no cast shadows, no blur and no gradients anywhere. Depth is tonal and takes three steps only: ground, lift (selected row), strip (title strips and bars). A sheet is separated from the console by a 1px rule-strong border and a 72% black backdrop that starts below the annunciator, so an alert is never dimmed.

### Named Rules
**The Hairline Rule.** Things are separated by a 1px line or by nothing. Structural lines between tiles and rows are real borders or the 1px grid gap; outlines around a small object (hollow tag, off keycap, video block, hollow legend square) are drawn with `box-shadow: inset 0 0 0 1px` so they add no size. That inset line is the only use of `box-shadow`.

## Shapes

Every corner is square (radius 0): tiles, tags, keycaps, lamps, blocks, sheets, the cursor. Lamps and legend swatches are 8px squares, not dots. SVG strokes use square caps. The only non-rectangular forms are the ruler pointer (a downward triangle, 8px wide, 7px tall), the level mark (five rising bars) and the registration marks: 12px L-shaped corners, 1px ink at 70% opacity, inset 6px at each corner of the camera plate.

## Components

### Strip
The title bar of a tile or sheet. 24px high, strip background, 0 8px padding, 10px gap. Title in ink 700 capitals; everything else label colour, 11px, 0.06em, capitals. Trailing controls are pushed right. The camera's strip has no padding and holds the tabs.

### Tag
A short code (Z1, C4, LIVE, GEMINI) in mono 700 11px, 16px line, 0 4px padding.
- **Solid:** ink background, black text. The selected thing.
- **Hollow:** transparent, label text, 1px rule-strong inset line. Everything else.
- **Alerting:** in a zone row at caution or above, the tag fills with the level colour, black text.

### Key
Every control is a keycap plus a word. 20px high, 6px gap, word in 11px 0.06em capitals. The keycap is mono 700 11px, minimum 16px wide, 0 4px padding, ink background, black text.
- **Hover:** keycap #ffffff. **Active:** keycap label grey.
- **Toggle off** (`aria-pressed="false"`): word in label grey, keycap hollow with a 1px rule-strong inset line.
- **Disabled:** word faint, keycap rule-strong.
- **On the alerting annunciator:** word inherits the band's text colour and the keycap is the inverse of the band.
- The letter on the keycap is the real keyboard shortcut. A keycap may hold a small filled SVG (play, stop) instead of a letter.

### Tab
Camera source selector inside the strip. 0 9px padding, a mono 700 number followed by the name in 11px capitals, label grey. Hover: ink. Selected: inverse video (ink background, black 700 text). Disabled: rule-strong. Tabs fill the strip's height and scroll horizontally without a scrollbar.

### Lamp
An 8px square filled with `--lamp`: green at normal and busy, the level colour above. At danger and critical inside a zone's state it blinks between opacity 1 and 0.25, once a second, in two steps.

### Block
A label pinned to the video. 11px tabular, 1.35 line, 1px 5px 2px padding, 80% black backing, 1px rule-strong inset line, positioned at the top-left of its zone with a 3px margin. Code and name in ink, units in label grey.
- **Selected:** the line becomes ink.
- **Alerting:** fills with the level colour, black 700 text, no line.
- **Gate:** cyan text and cyan line, centred on the gate line.
- The in-view readout is the same backing without a line, 6px from the plate's bottom-right.

On the video itself, a zone outline is 1px ink at 45% opacity, 1.5px at full opacity when selected, and 2px in the level colour with a 16% fill when alerting.

### Zone row
One zone as a full-width button: tag, then name with the state (lamp plus word) at the right, the ruler, a one-line detail in label grey 11px; then the density numeral and its unit. Padding 7px 10px 6px 8px, 1px rule below.
- **Selected:** lift background, solid tag, detail line wraps to show everything, numeral at 34px unless another zone is at danger or critical.
- **Alerting:** state word 700 in the level colour, numeral in the level colour, tag filled; the phrase that explains the alert is 700 in the level colour.

### Ruler
A 21px scale from 0 to 7 people/m². 1px rule-strong base line; a 1px tick at every unit (5px high), taller (8px) and label grey at each level boundary, with the boundary value beneath in 11px tabular. A 2px band in each alerting level's colour runs under the base at 50% opacity, 100% when the row is selected or alerting. The pointer is a triangle in `--lv` at the reading.

### Annunciator
The full-width band under the status line. 40px, 0 12px padding, 16px gap, capitals, 0.04em.
- **Quiet:** black, label grey text, a green lamp, the highest reading.
- **Alerting:** the band fills with the level colour, black 700 text at 18px, with the keys to respond at the right.
- **Unacknowledged:** flips between colour-on-black and black-on-colour once a second, in two steps, until acknowledged.

### Sheet
A modal document (incident report, science). Width min(720px, 100vw - 32px), max-height min(84vh, 760px), ground background, 1px rule-strong border. A strip on top, a scrolling body (9px 10px), a strip-coloured footer of keys aligned right. Headings: 15px 700, then 11px 700 capitals in label grey with 14px above. Tables use 1px rules above each row and 11px capital headers.

### Key bar and command line
The 28px bar at the bottom: strip background, 1px rule above, toggles as keys with 14px between them. The command line takes the remaining width behind a 1px rule: a `/` prompt and an input in B612 Mono, capitals, 0.04em, no box and no background. The placeholder is sentence case in label grey.

### Trace
The strip chart. 1px rule-strong axes, 1px rule gridlines at the half and full width, level lines dashed (alerting levels in their colour at 60%, dashed 6 4; others rule-strong, dashed 2 4). Zone lines are 1px faint, 2px ink when selected, the level colour when alerting. A 104px list of code and value sits at the right behind a 1px rule-strong line.

### Motion
- Lamp blink, annunciator flip and typing cursor: `1s steps(2, jump-none) infinite`.
- Ruler pointer: `left 0.4s steps(4)`.
- No other transition or animation exists. `prefers-reduced-motion: reduce` removes all of them.

### Focus
`:focus-visible` is a 2px ink outline offset -2px, drawn inside the element so it never spills over a hairline.

## Do's and Don'ts

### Do:
- **Do** build new surfaces from tiles: ground background, a 24px strip, 1px hairlines, no gap wider than 1px between panels.
- **Do** give every action a keycap and a command word, and show the key on the control.
- **Do** show selection with inverse video (ink background, black text) or the lift background.
- **Do** set anything at caution or above by putting `data-level` on its container and reading `--lv` and `--lamp`.
- **Do** put black text on any level-colour or ink fill.
- **Do** use tabular figures for every live number and give each one its unit.
- **Do** step state changes with `steps()`; two frames for blinks.
- **Do** draw small outlines with the 1px inset line so the object keeps its size.

### Don't:
- **Don't** round a corner. Lamps and swatches are squares.
- **Don't** add a cast shadow, blur, glass effect or gradient.
- **Don't** use amber, orange, red or green for anything but a safety level, or cyan for anything but a measurement on the video.
- **Don't** add a brand or accent colour; ink in inverse video is the accent.
- **Don't** separate panels with space or wrap content in cards.
- **Don't** fade, ease or slide anything.
- **Don't** set a figure larger than 22px unless its zone is selected or at danger or critical.
- **Don't** load a font or any asset from the network.
