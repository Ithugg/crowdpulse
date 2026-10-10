"""Per-zone density smoothing, level tracking, exposure timing and a linear-trend forecast."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from .config import Thresholds, Zone
from .zones import CAUTION, LEVEL_RANK, LEVELS, NORMAL, level_for

SMOOTH_TAU_S = 2.5  # EMA time constant: hides frame-to-frame detection flicker
SAMPLE_PERIOD_S = 0.5  # history resolution
WINDOW_S = 60.0  # how far back the trend looks
MIN_TREND_SPAN_S = 30.0  # need at least this much history before forecasting
MIN_SLOPE_PER_S = 0.003  # ~0.18 p/m2 per minute; below this a zone counts as stable
MAX_ETA_S = 15 * 60
FORECAST_MIN_FRACTION = 0.5  # only forecast a level once density is at least half-way there
WARMUP_S = 3.0  # no level changes until a zone has this much data (first frames are noisy)
DWELL_UP_S = 1.5  # a higher level must hold this long before it is reported
DWELL_DOWN_S = 4.0  # stepping down takes longer, so a zone does not flap around a threshold


@dataclass
class ZoneState:
    zone: Zone
    count: int = 0  # people in the zone, smoothed like the density so the two describe the same moment
    density: float = 0.0  # smoothed peak local density, people/m2
    avg_density: float | None = None  # count / measured zone area, when the area is known
    area_m2: float | None = None
    level: str = NORMAL
    trend_per_min: float = 0.0
    eta_s: float | None = None  # forecast: seconds until the zone reaches eta_level
    eta_level: str | None = None
    above_safe_s: float = 0.0  # how long the zone has been at or above the action level (caution)
    samples: deque = field(default_factory=lambda: deque(maxlen=int(WINDOW_S / SAMPLE_PERIOD_S)))
    _count: float = 0.0
    _first_t: float | None = None
    _last_t: float | None = None
    _last_sample_t: float = -math.inf
    _pending: str | None = None  # level waiting out its dwell time
    _pending_t: float = 0.0
    _above_since: float | None = None

    def history(self) -> list[float]:
        """Last minute of density at 1 Hz, oldest first (for the dashboard sparkline)."""
        step = max(1, round(1.0 / SAMPLE_PERIOD_S))
        return [round(d, 2) for _, d in list(self.samples)[::-1][::step][::-1]]


class ZoneTracker:
    def __init__(self, zones: tuple[Zone, ...], thresholds: Thresholds, areas_m2: list[float | None] | None = None):
        self.thresholds = thresholds
        self.states = [ZoneState(z) for z in zones]
        self.set_areas(areas_m2 or [None] * len(zones))

    def set_areas(self, areas_m2: list[float | None]) -> None:
        for state, area in zip(self.states, areas_m2):
            state.area_m2 = area

    def update(self, counts: list[int], densities: list[float], t: float) -> list[ZoneState]:
        """Feed each zone's raw count and raw peak local density for a frame at time t (seconds, monotonic)."""
        for state, count, raw in zip(self.states, counts, densities):
            if state._last_t is None:
                state.density, state._count, state._first_t = raw, float(count), t
            else:
                alpha = 1.0 - math.exp(-max(t - state._last_t, 0.0) / SMOOTH_TAU_S)
                state.density += alpha * (raw - state.density)
                state._count += alpha * (count - state._count)
            state._last_t = t
            state.count = round(state._count)
            state.avg_density = count / state.area_m2 if state.area_m2 else None
            self._update_level(state, t)

            if LEVEL_RANK[state.level] >= LEVEL_RANK[CAUTION]:
                if state._above_since is None:
                    state._above_since = t
                state.above_safe_s = t - state._above_since
            else:
                state._above_since, state.above_safe_s = None, 0.0

            if t - state._last_sample_t >= SAMPLE_PERIOD_S:
                state.samples.append((t, state.density))
                state._last_sample_t = t
                self._predict(state)
        return self.states

    def _update_level(self, state: ZoneState, t: float) -> None:
        target = level_for(state.density, self.thresholds, state.level)
        if target == state.level or t - state._first_t < WARMUP_S:
            state._pending = None
            return
        if state._pending != target:
            state._pending, state._pending_t = target, t
        dwell = DWELL_UP_S if LEVEL_RANK[target] > LEVEL_RANK[state.level] else DWELL_DOWN_S
        if t - state._pending_t >= dwell:
            state.level, state._pending = target, None

    def _predict(self, state: ZoneState) -> None:
        """Straight-line fit over the recent history -> time until the next level from caution upwards."""
        state.trend_per_min, state.eta_s, state.eta_level = 0.0, None, None
        if len(state.samples) < 8:
            return
        ts = np.array([s[0] for s in state.samples])
        ds = np.array([s[1] for s in state.samples])
        if ts[-1] - ts[0] < MIN_TREND_SPAN_S:
            return
        slope, intercept = np.polyfit(ts - ts[0], ds, 1)
        state.trend_per_min = float(slope * 60.0)
        if slope < MIN_SLOPE_PER_S:
            return
        now = max(slope * (ts[-1] - ts[0]) + intercept, state.density)
        for level, step in zip(LEVELS[2:], self.thresholds.steps[1:]):  # caution, danger, critical
            if LEVEL_RANK[level] > LEVEL_RANK[state.level] and step > now:
                eta = (step - now) / slope
                # A straight line is only believable over a short reach: no forecast from far below the level.
                if eta <= MAX_ETA_S and now >= FORECAST_MIN_FRACTION * step:
                    state.eta_s, state.eta_level = float(eta), level
                return
