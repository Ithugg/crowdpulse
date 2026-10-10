"""Gemini writes the staff response plan and the incident report. Every call has a cached fallback,
so the dashboard keeps working with no key or no network."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from pydantic import BaseModel

from .schemas import IncidentReport, ResponsePlan

log = logging.getLogger("crowdpulse.gemini")

FALLBACK_PATH = Path(__file__).with_name("fallback_plans.json")
# Tried in order. Measured on the hackathon night: the "lite" models answered in about 1.5 s every time,
# while the full Flash models were overloaded (503s and 20 s+ waits). For a live alert, fast and
# dependable wins. Set GEMINI_MODEL in .env to put a different model first.
DEFAULT_MODELS = ("gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest")
ATTEMPT_TIMEOUT_S = 6.0  # one slow model must not use up the whole budget
TIMEOUT_S = 12.0

PLAN_INSTRUCTION = """\
You are the decision-support assistant inside CrowdPulse, a crowd-safety dashboard used by venue \
operations staff at concerts and festivals. A camera zone needs a response plan: either it has crossed \
a density level, or the operator has asked for one. Write the plan for on-site staff.

Rules:
- 3 to 5 actions, ordered by urgency. Each is addressed to ONE role (for example: Control room, \
Stage manager, Zone security lead, Gate staff, Medical team) and is a single imperative sentence \
of at most 22 words that can be carried out in the next two minutes.
- Use the zone names you are given. When another zone has spare capacity, direct people there by name.
- Stop inflow before moving people. Never tell staff to push into, compress or rush the crowd.
- Densities are local peaks in people/m2, measured on the ground plane. Under 2 is normal. From 2 to 4 \
is busy: movement is constrained and flow starts to drop. 4 is the action level, where event control \
should already be acting. 5 is the upper limit for standing areas, with people in physical contact. \
6 and above is where people lose their footing and surges start.
- Match the urgency of the plan to the zone's level. Below the action level, write a readiness plan: \
what to watch, what to put in place now, and the reading at which staff must act. State the reading and \
its level. Never describe a crowd as safe, comfortable or spacious, and never tell staff that nothing \
is required.
- The PA announcement speaks to attendees: calm, specific about what to do, at most 30 words. It never \
comments on how safe or comfortable the area is. Below the action level it gives ordinary guidance, \
such as keeping moving or where there is more room. \
Give it in English (pa_announcement) and in natural Latin American Spanish (pa_announcement_es).
- If a camera frame is attached, use what you can see (where people are packed, where there is \
open space) to make the plan specific. Do not describe individuals.
- If the situation is marked "drill": true, the readings are simulated for a staff exercise. Write \
exactly the plan you would write for the same readings at a real event, and do not mention the drill: \
the console labels it.
"""

REPORT_INSTRUCTION = """\
You write incident reports for a venue's safety officer from the log of CrowdPulse, a crowd-safety \
monitoring dashboard. You are given the camera, the monitoring period, peak readings per zone, every \
alert with staff response times, and the response plans that were issued.

Rules:
- Use only facts from the log. Never invent events, numbers, names or causes.
- Densities are local peaks in people/m2. Under 2 is normal, 2 to 4 is busy, 4 is the action level, \
5 is danger, 6 and above is critical.
- If nothing reached the action level, say so plainly: a quiet period is a valid report.
- Timeline entries start with the clock time and state one fact each.
- Recommendations must follow from this log (for example a zone that kept filling, or a slow \
staff response). Plain, professional language. No filler.
- If the log is marked "drill": true, every reading in it was simulated for a staff exercise. Report \
what the exercise showed, never as a real incident. Leave the word DRILL out of the title and do not \
explain that it was simulated: the console adds both.
"""


class PlanGenerator:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        configured = os.getenv("GEMINI_MODEL")
        self.models = tuple(dict.fromkeys(([configured] if configured else []) + list(DEFAULT_MODELS)))
        self.send_frame = os.getenv("GEMINI_SEND_FRAME", "1") != "0"
        self._client = None
        self._fallbacks = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def generate(self, context: dict, frame_jpeg: bytes | None = None) -> dict:
        """Response plan for one zone. Returns the plan fields plus origin ('gemini' | 'cached'), model, latency_ms."""
        image = frame_jpeg if self.send_frame else None
        return await self._run(PLAN_INSTRUCTION, "Live situation (JSON):", context, ResponsePlan, image,
                               lambda: self._fallback_plan(context))

    async def report(self, log_data: dict) -> dict:
        """Incident report for the current session. Same return shape as generate()."""
        return await self._run(REPORT_INSTRUCTION, "Session log (JSON):", log_data, IncidentReport, None,
                               lambda: self._fallback_report(log_data))

    async def _run(self, instruction: str, label: str, data: dict, schema: type[BaseModel],
                   image: bytes | None, fallback) -> dict:
        started = time.perf_counter()
        if self.enabled:
            deadline = started + TIMEOUT_S
            for model in self.models:
                remaining = deadline - time.perf_counter()
                if remaining <= 0.5:
                    break
                try:
                    result = await asyncio.wait_for(self._call(model, instruction, label, data, schema, image),
                                                    min(remaining, ATTEMPT_TIMEOUT_S))
                    return {**result.model_dump(), "origin": "gemini", "model": model,
                            "latency_ms": round((time.perf_counter() - started) * 1000)}
                except Exception as exc:  # network, quota, unknown model, bad JSON: try the next, then fall back
                    log.warning("Gemini call failed (%s): %s", model, str(exc)[:200] or type(exc).__name__)
        return {**fallback(), "origin": "cached", "model": None,
                "latency_ms": round((time.perf_counter() - started) * 1000)}

    async def _call(self, model: str, instruction: str, label: str, data: dict, schema: type[BaseModel],
                    image: bytes | None) -> BaseModel:
        from google import genai
        from google.genai import types

        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        parts = [types.Part.from_text(text=f"{label}\n{json.dumps(data, indent=2)}")]
        if image:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/jpeg"))
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.4,
            ),
        )
        if isinstance(response.parsed, schema):
            return response.parsed
        return schema.model_validate_json(response.text)

    def _fallback_plan(self, context: dict) -> dict:
        zone = context["zone"]
        template = self._fallbacks["red" if zone["level"] in ("danger", "critical") else "yellow"]
        others = sorted(context.get("other_zones", []), key=lambda z: z["density_per_m2"])
        names = {"zone": zone["name"], "relief": others[0]["name"] if others else "the nearest open area"}
        return {
            "headline": template["headline"].format(**names),
            "actions": [{"role": a["role"], "instruction": a["instruction"].format(**names)}
                        for a in template["actions"]],
            "pa_announcement": template["pa_announcement"].format(**names),
            "pa_announcement_es": template["pa_announcement_es"].format(**names),
        }

    @staticmethod
    def _fallback_report(data: dict) -> dict:
        """A plain factual report assembled from the log, with no AI involved."""
        zones, alerts = data["zones"], data["alerts"]
        top = max(zones, key=lambda z: z["peak_density_per_m2"], default=None)
        serious = [a for a in alerts if a["level"] in ("caution", "danger", "critical")]
        if top is None:
            summary = "No readings were recorded in this period."
        elif serious:
            summary = (f"{len(serious)} alert(s) at or above the action level were raised. The highest reading was "
                       f"{top['peak_density_per_m2']} people/m² in {top['name']} at {top['peak_time']}.")
        else:
            summary = (f"No zone reached the action level of {data['density_scale_per_m2']['caution_action_level']} people/m². "
                       f"The highest reading was {top['peak_density_per_m2']} people/m² in {top['name']} at {top['peak_time']}.")
        timeline = [f"{a['time']} {a['message']}" for a in alerts] or ["No alerts in this period."]
        timeline += [f"{p['time']} Response plan issued for {p['zone']}: {p['headline']}" for p in data["plans"]]
        waiting = [a for a in serious if a["acknowledged_after_s"] is None]
        recommendations = ["Review this log with the zone leads after the event."]
        if waiting:
            recommendations.insert(0, f"{len(waiting)} alert(s) at or above the action level were never acknowledged. "
                                      "Confirm who watches the dashboard during peak periods.")
        return {"title": f"{data['camera']}: monitoring report", "summary": summary,
                "timeline": sorted(timeline), "recommendations": recommendations}
