"""WebSocket message shapes. This file is the contract between the server and the dashboard;
frontend/src/types.ts mirrors it."""
from __future__ import annotations

import math
import time

from pydantic import BaseModel, Field

from .calibration import SceneGeometry
from .config import Settings, Source
from .predictor import ZoneState
from .zones import LEVEL_INFO, LEVEL_RANK, LEVELS


class PlanAction(BaseModel):
    role: str = Field(description="Staff role responsible, e.g. 'Stage manager' or 'Zone security lead'")
    instruction: str = Field(description="One imperative sentence the role can act on right now")


class ResponsePlan(BaseModel):
    """What Gemini returns (also the shape of the cached fallback plans)."""
    headline: str = Field(description="One-line summary of the response, under 10 words")
    actions: list[PlanAction] = Field(description="3 to 5 actions ordered by urgency")
    pa_announcement: str = Field(description="Calm public-address announcement for attendees, under 30 words")


def calibration_message(source: Source, geometry: SceneGeometry) -> dict:
    """How distances are being measured for this camera."""
    calib = geometry.calibration
    return {
        "mode": geometry.mode,  # "ground" = camera calibrated against the floor, "size" = from body size
        "cam_height_m": round(calib.cam_height_m, 1) if calib else None,
        "tilt_deg": round(math.degrees(calib.tilt_rad)) if calib else None,
        "hfov_deg": source.hfov_deg,
    }


def config_message(settings: Settings, source: Source, geometry: SceneGeometry,
                   areas_m2: list[float | None]) -> dict:
    steps = (0.0,) + settings.thresholds.steps
    return {
        "type": "config",
        "sources": [
            {"id": s.id, "label": s.label, "kind": s.kind,
             "available": s.kind == "webcam" or s.video_path.exists()}
            for s in settings.sources.values()
        ],
        "active_source": source.id,
        "levels": [
            {"id": level, "label": LEVEL_INFO[level][0], "min": steps[i],
             "what": LEVEL_INFO[level][1], "source": LEVEL_INFO[level][2]}
            for i, level in enumerate(LEVELS)
        ],
        "exposure_alert_s": settings.thresholds.exposure_alert_s,
        "calibration": calibration_message(source, geometry),
        "zones": [
            {"id": z.id, "name": z.name, "area_m2": area, "polygon": [list(p) for p in z.polygon]}
            for z, area in zip(source.zones, areas_m2)
        ],
    }


def zone_message(s: ZoneState) -> dict:
    return {
        "id": s.zone.id, "count": s.count, "density": round(s.density, 2),
        "avg_density": None if s.avg_density is None else round(s.avg_density, 2),
        "level": s.level, "trend_per_min": round(s.trend_per_min, 2),
        "eta_s": None if s.eta_s is None else round(s.eta_s), "eta_level": s.eta_level,
        "above_safe_s": round(s.above_safe_s),
        "history": s.history(),
    }


def state_message(*, seq: int, source_id: str, fps: float, inference_ms: float, mode: str,
                  frame_w: int, frame_h: int, total_count: int, states: list[ZoneState],
                  overlay: dict) -> dict:
    overall = max((s.level for s in states), key=LEVEL_RANK.get, default=LEVELS[0])
    return {
        "type": "state", "seq": seq, "ts": time.time(), "source_id": source_id,
        "fps": round(fps, 1), "inference_ms": round(inference_ms), "mode": mode,
        "frame": {"w": frame_w, "h": frame_h},
        "total_count": total_count, "overall_level": overall,
        "zones": [zone_message(s) for s in states],
        "overlay": overlay,
    }
