"""Turns zone state changes into alert events for the dashboard feed."""
from __future__ import annotations

import itertools
import time

from .predictor import ZoneState
from .zones import GREEN, LEVEL_RANK, RED, YELLOW

PREDICTION_HORIZON_S = 5 * 60  # only warn about a projected critical when it is this close
PREDICTION_COOLDOWN_S = 45


def format_eta(seconds: float) -> str:
    if seconds < 90:
        return f"{max(10, round(seconds / 10) * 10)} s"
    return f"{round(seconds / 60)} min"


class AlertManager:
    def __init__(self):
        self._ids = itertools.count(1)
        self._levels: dict[str, str] = {}
        self._last_prediction: dict[str, float] = {}

    def reset(self) -> None:
        """Forget zone levels (source switched or the clip looped) so alerts can fire again."""
        self._levels.clear()
        self._last_prediction.clear()

    def update(self, states: list[ZoneState], t: float) -> list[dict]:
        """t is the pipeline's monotonic clock; returns the alerts raised by this frame."""
        alerts = []
        for s in states:
            zid, name = s.zone.id, s.zone.name
            previous = self._levels.get(zid, GREEN)
            if s.level != previous:
                self._levels[zid] = s.level
                rising = LEVEL_RANK[s.level] > LEVEL_RANK[previous]
                if s.level == RED:
                    alerts.append(self._alert(s, "level_change", RED,
                                              f"{name} reached CRITICAL density ({s.density:.1f} p/m²)"))
                elif s.level == YELLOW and rising:
                    alerts.append(self._alert(s, "level_change", YELLOW,
                                              f"{name} density elevated ({s.density:.1f} p/m²)"))
                elif s.level == YELLOW:
                    alerts.append(self._alert(s, "level_change", YELLOW,
                                              f"{name} easing, still elevated ({s.density:.1f} p/m²)"))
                else:
                    alerts.append(self._alert(s, "cleared", GREEN, f"{name} back to normal"))

            eta = s.eta_critical_s
            if eta is not None and eta <= PREDICTION_HORIZON_S and s.level != RED:
                if t - self._last_prediction.get(zid, -1e9) >= PREDICTION_COOLDOWN_S:
                    self._last_prediction[zid] = t
                    alerts.append(self._alert(s, "prediction", YELLOW,
                                              f"{name} projected to reach critical in ~{format_eta(eta)}"))
        return alerts

    def _alert(self, s: ZoneState, kind: str, level: str, message: str) -> dict:
        return {
            "type": "alert", "id": f"a{next(self._ids)}", "ts": time.time(),
            "zone_id": s.zone.id, "zone_name": s.zone.name,
            "kind": kind, "level": level, "density": round(s.density, 2), "message": message,
        }
