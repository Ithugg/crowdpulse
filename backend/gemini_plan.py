"""Generates a staff response plan with the Gemini API, falling back to a cached plan if it fails."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from .schemas import ResponsePlan

log = logging.getLogger("crowdpulse.gemini")

FALLBACK_PATH = Path(__file__).with_name("fallback_plans.json")
DEFAULT_MODELS = ("gemini-flash-latest", "gemini-2.5-flash")
TIMEOUT_S = 10.0

SYSTEM_INSTRUCTION = """\
You are the decision-support assistant inside CrowdPulse, a crowd-safety dashboard used by venue \
operations staff at concerts and festivals. A camera zone has reached a dangerous crowd density or \
is about to. Write the immediate response plan for on-site staff.

Rules:
- 3 to 5 actions, ordered by urgency. Each is addressed to ONE role (for example: Control room, \
Stage manager, Zone security lead, Gate staff, Medical team) and is a single imperative sentence \
of at most 22 words that can be carried out in the next two minutes.
- Use the zone names you are given. When another zone has spare capacity, direct people there by name.
- Stop inflow before moving people. Never tell staff to push into, compress or rush the crowd.
- Above 4 people/m2 movement becomes restricted; above 5 to 6 the risk of crowd crush is severe. \
Match the urgency of the plan to the numbers.
- The PA announcement speaks to attendees: calm, specific about what to do, at most 30 words.
- If a camera frame is attached, use what you can see (where people are packed, where there is \
open space) to make the plan specific. Do not describe individuals.
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
        """Returns the plan fields plus origin ('gemini' | 'cached'), model and latency_ms."""
        started = time.perf_counter()
        if self.enabled:
            deadline = started + TIMEOUT_S
            for model in self.models:
                remaining = deadline - time.perf_counter()
                if remaining <= 0.5:
                    break
                try:
                    plan = await asyncio.wait_for(self._call(model, context, frame_jpeg), remaining)
                    return {**plan.model_dump(), "origin": "gemini", "model": model,
                            "latency_ms": round((time.perf_counter() - started) * 1000)}
                except Exception as exc:  # network, quota, unknown model, bad JSON: try the next, then fall back
                    log.warning("Gemini call failed (%s): %s", model, exc)
        return {**self._fallback(context), "origin": "cached", "model": None,
                "latency_ms": round((time.perf_counter() - started) * 1000)}

    async def _call(self, model: str, context: dict, frame_jpeg: bytes | None) -> ResponsePlan:
        from google import genai
        from google.genai import types

        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        parts = [types.Part.from_text(text="Live situation (JSON):\n" + json.dumps(context, indent=2))]
        if frame_jpeg and self.send_frame:
            parts.append(types.Part.from_bytes(data=frame_jpeg, mime_type="image/jpeg"))
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ResponsePlan,
                temperature=0.4,
            ),
        )
        if isinstance(response.parsed, ResponsePlan):
            return response.parsed
        return ResponsePlan.model_validate_json(response.text)

    def _fallback(self, context: dict) -> dict:
        zone = context["zone"]
        template = self._fallbacks["red" if zone["level"] == "red" else "yellow"]
        others = sorted(context.get("other_zones", []), key=lambda z: z["density_per_m2"])
        names = {"zone": zone["name"], "relief": others[0]["name"] if others else "the nearest open area"}
        return {
            "headline": template["headline"].format(**names),
            "actions": [{"role": a["role"], "instruction": a["instruction"].format(**names)}
                        for a in template["actions"]],
            "pa_announcement": template["pa_announcement"].format(**names),
        }
