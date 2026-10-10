"""Synthetic inputs shared by the test files: a one-zone tracker and a density ramp."""
from __future__ import annotations

from backend.alerts import AlertManager
from backend.config import Thresholds, Zone
from backend.predictor import ZoneTracker

FPS = 15.0
DT = 1.0 / FPS
THRESHOLDS = Thresholds()
SQUARE = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))


def one_zone() -> Zone:
    return Zone("z1", "Zone One", SQUARE)


def piecewise(points):
    """Density as a function of time from (t, density) corner points, linear in between."""
    def f(t: float) -> float:
        if t <= points[0][0]:
            return points[0][1]
        for (t0, d0), (t1, d1) in zip(points, points[1:]):
            if t <= t1:
                return d0 + (d1 - d0) * (t - t0) / (t1 - t0)
        return points[-1][1]
    return f


# 1 -> 6.5 people/m2 over 3 minutes, hold 7 minutes, then fall to 0.5 over 2 minutes.
RAMP = piecewise([(0, 1.0), (180, 6.5), (600, 6.5), (720, 0.5)])
RAMP_END_S = 760.0


def run(tracker: ZoneTracker, density_at, duration_s: float, alerts: AlertManager | None = None,
        t0: float = 0.0, count: int = 10):
    """Feeds one zone at 15 Hz. Yields (t, state, alerts raised by this frame)."""
    n = int(duration_s * FPS)
    for i in range(n + 1):
        t = t0 + i * DT
        states = tracker.update([count], [density_at(t - t0)], t)
        yield t, states[0], (alerts.update(states, t) if alerts else [])
