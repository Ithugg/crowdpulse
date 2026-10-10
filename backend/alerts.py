"""Turns zone state changes into alert events for the dashboard feed."""
from __future__ import annotations

import itertools
import time

from .config import Thresholds
from .predictor import ZoneState
from .zones import BUSY, CAUTION, LEVEL_INFO, LEVEL_RANK, NORMAL

PREDICTION_HORIZON_S = 10 * 60  # only warn about a projected level when it is this close
PREDICTION_COOLDOWN_S = 45


def format_eta(seconds: float) -> str:
    if seconds < 90:
        return f"{max(10, round(seconds / 10) * 10)} s"
    return f"{round(seconds / 60)} min"


class AlertManager:
    def __init__(self, thresholds: Thresholds):
        self.thresholds = thresholds
        self._ids = itertools.count(1)
        self._levels: dict[str, str] = {}
        self._last_prediction: dict[str, float] = {}
        self._exposure_alerted: set[str] = set()

    def reset(self) -> None:
        """Forget zone levels (source switched or the clip looped) so alerts can fire again."""
        self._levels.clear()
        self._last_prediction.clear()
        self._exposure_alerted.clear()

    def update(self, states: list[ZoneState], t: float) -> list[dict]:
        """t is the pipeline's monotonic clock; returns the alerts raised by this frame."""
        alerts = []
        for s in states:
            zid, name = s.zone.id, s.zone.name
            previous = self._levels.get(zid, NORMAL)
            if s.level != previous:
                self._levels[zid] = s.level
                was_alerting = LEVEL_RANK[previous] >= LEVEL_RANK[CAUTION]
                label = LEVEL_INFO[s.level][0].upper()
                if LEVEL_RANK[s.level] >= LEVEL_RANK[CAUTION]:
                    verb = "reached" if LEVEL_RANK[s.level] > LEVEL_RANK[previous] else "easing to"
                    alerts.append(self._alert(s, "level_change", s.level,
                                              f"{name} {verb} {label} ({s.density:.1f} people/m²)"))
                elif was_alerting:
                    alerts.append(self._alert(s, "cleared", s.level,
                                              f"{name} back below the action level ({s.density:.1f} people/m²)"))
                elif s.level == BUSY and previous == NORMAL:
                    alerts.append(self._alert(s, "level_change", BUSY,
                                              f"{name} is getting busy ({s.density:.1f} people/m²)"))

            if s.eta_s is not None and s.eta_s <= PREDICTION_HORIZON_S:
                if t - self._last_prediction.get(zid, -1e9) >= PREDICTION_COOLDOWN_S:
                    self._last_prediction[zid] = t
                    target = LEVEL_INFO[s.eta_level][0]
                    alerts.append(self._alert(s, "prediction", s.eta_level,
                                              f"{name} projected to reach {target} in ~{format_eta(s.eta_s)}"))

            if s.above_safe_s >= self.thresholds.exposure_alert_s and zid not in self._exposure_alerted:
                self._exposure_alerted.add(zid)
                minutes = round(self.thresholds.exposure_alert_s / 60)
                alerts.append(self._alert(s, "exposure", s.level,
                                          f"{name} has stayed above {self.thresholds.caution:g}/m² for {minutes} min"))
            elif s.above_safe_s == 0:
                self._exposure_alerted.discard(zid)
        return alerts

    def _alert(self, s: ZoneState, kind: str, level: str, message: str) -> dict:
        return {
            "type": "alert", "id": f"a{next(self._ids)}", "ts": time.time(),
            "zone_id": s.zone.id, "zone_name": s.zone.name,
            "kind": kind, "level": level, "density": round(s.density, 2), "message": message,
        }
