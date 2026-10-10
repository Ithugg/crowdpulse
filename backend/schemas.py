"""WebSocket message shapes. This file is the contract between the server and the dashboard;
frontend/src/types.ts mirrors it."""
from __future__ import annotations

import time

from pydantic import BaseModel, Field

from .config import Settings, Source
from .predictor import ZoneState
from .zones import LEVEL_RANK


class PlanAction(BaseModel):
    role: str = Field(description="Staff role responsible, e.g. 'Stage manager' or 'Zone security lead'")
    instruction: str = Field(description="One imperative sentence the role can act on right now")


class ResponsePlan(BaseModel):
    """What Gemini returns (also the shape of the cached fallback plans)."""
    headline: str = Field(description="One-line summary of the response, under 10 words")
    actions: list[PlanAction] = Field(description="3 to 5 actions ordered by urgency")
    pa_announcement: str = Field(description="Calm public-address announcement for attendees, under 30 words")


def config_message(settings: Settings, source: Source) -> dict:
    return {
        "type": "config",
        "sources": [
            {"id": s.id, "label": s.label, "kind": s.kind,
             "available": s.kind == "webcam" or s.video_path.exists()}
            for s in settings.sources.values()
        ],
        "active_source": source.id,
        "thresholds": {"warn": settings.thresholds.warn, "critical": settings.thresholds.critical},
        "zones": [
            {"id": z.id, "name": z.name, "area_m2": z.area_m2, "polygon": [list(p) for p in z.polygon]}
            for z in source.zones
        ],
    }


def zone_message(s: ZoneState) -> dict:
    return {
        "id": s.zone.id, "count": s.count, "density": round(s.density, 2), "level": s.level,
        "trend_per_min": round(s.trend_per_min, 2),
        "eta_critical_s": None if s.eta_critical_s is None else round(s.eta_critical_s),
        "history": s.history(),
    }


def state_message(*, seq: int, source_id: str, fps: float, inference_ms: float, mode: str,
                  frame_w: int, frame_h: int, total_count: int, states: list[ZoneState],
                  overlay: dict) -> dict:
    overall = max((s.level for s in states), key=LEVEL_RANK.get, default="green")
    return {
        "type": "state", "seq": seq, "ts": time.time(), "source_id": source_id,
        "fps": round(fps, 1), "inference_ms": round(inference_ms), "mode": mode,
        "frame": {"w": frame_w, "h": frame_h},
        "total_count": total_count, "overall_level": overall,
        "zones": [zone_message(s) for s in states],
        "overlay": overlay,
    }
