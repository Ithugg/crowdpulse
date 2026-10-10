"""Per-zone density smoothing, level tracking and a linear-trend estimate of time until critical."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from .config import Thresholds, Zone
from .zones import GREEN, RED, level_for

SMOOTH_TAU_S = 1.5  # EMA time constant: hides frame-to-frame detection flicker
SAMPLE_PERIOD_S = 0.5  # history resolution
WINDOW_S = 60.0  # how far back the trend looks
MIN_TREND_SPAN_S = 12.0  # need at least this much history before predicting
MIN_SLOPE_PER_S = 0.003  # ~0.18 p/m2 per minute; below this a zone counts as stable
MAX_ETA_S = 15 * 60


@dataclass
class ZoneState:
    zone: Zone
    count: int = 0
    density: float = 0.0  # smoothed people/m2
    level: str = GREEN
    trend_per_min: float = 0.0
    eta_critical_s: float | None = None
    samples: deque = field(default_factory=lambda: deque(maxlen=int(WINDOW_S / SAMPLE_PERIOD_S)))
    _last_t: float | None = None
    _last_sample_t: float = -math.inf

    def history(self) -> list[float]:
        """Last minute of density at 1 Hz, oldest first (for the dashboard sparkline)."""
        step = max(1, round(1.0 / SAMPLE_PERIOD_S))
        return [round(d, 2) for _, d in list(self.samples)[::-1][::step][::-1]]


class ZoneTracker:
    def __init__(self, zones: tuple[Zone, ...], thresholds: Thresholds):
        self.thresholds = thresholds
        self.states = [ZoneState(z) for z in zones]

    def update(self, counts: list[int], t: float) -> list[ZoneState]:
        """Feed the raw per-zone counts for a frame at time t (seconds, any monotonic clock)."""
        for state, count in zip(self.states, counts):
            raw = count / state.zone.area_m2
            if state._last_t is None:
                state.density = raw
            else:
                alpha = 1.0 - math.exp(-max(t - state._last_t, 0.0) / SMOOTH_TAU_S)
                state.density += alpha * (raw - state.density)
            state._last_t = t
            state.count = count
            state.level = level_for(state.density, self.thresholds, state.level)

            if t - state._last_sample_t >= SAMPLE_PERIOD_S:
                state.samples.append((t, state.density))
                state._last_sample_t = t
                self._predict(state)
        return self.states

    def _predict(self, state: ZoneState) -> None:
        state.trend_per_min, state.eta_critical_s = 0.0, None
        if len(state.samples) < 8:
            return
        ts = np.array([s[0] for s in state.samples])
        ds = np.array([s[1] for s in state.samples])
        if ts[-1] - ts[0] < MIN_TREND_SPAN_S:
            return
        slope, intercept = np.polyfit(ts - ts[0], ds, 1)
        state.trend_per_min = float(slope * 60.0)
        if state.level == RED or slope < MIN_SLOPE_PER_S:
            return
        fitted_now = slope * (ts[-1] - ts[0]) + intercept
        eta = (self.thresholds.critical - max(fitted_now, state.density)) / slope
        if 0 < eta <= MAX_ETA_S:
            state.eta_critical_s = float(eta)
