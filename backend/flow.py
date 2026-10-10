"""Crowd movement: follows people between frames to measure walking speed and direction per zone,
and counts people crossing gate lines.

Flow matters as much as density: in the crowd-disaster literature, flow dropping and velocities
becoming erratic come before a crush (Helbing, Johansson & Al-Abideen 2007). Speeds are in real
metres per second, which is only possible because the camera is calibrated against the floor.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from .config import Gate

MATCH_IOU = 0.25  # a detection continues a track when their boxes overlap at least this much
MAX_MISSED = 6  # frames a track survives without a detection
VELOCITY_WINDOW_S = 1.5  # speed is measured over this much of a person's recent path
MIN_VELOCITY_SPAN_S = 0.8
MAX_SPEED_MPS = 3.5  # faster than this is detector jitter, not a person
MIN_PEOPLE = 3  # a zone needs this many tracked people before a flow figure is shown
MOVING_MPS = 0.25  # below this a crowd counts as standing, and has no direction
SMOOTH_TAU_S = 2.0
GATE_WINDOW_S = 60.0
GATE_REARM_S = 2.0  # one person cannot be counted twice on a gate within this time


@dataclass
class Track:
    id: int
    box: np.ndarray
    path: deque = field(default_factory=lambda: deque(maxlen=64))  # (t, pixel xy, ground xy or None)
    missed: int = 0
    gate_side: dict = field(default_factory=dict)  # gate id -> which side of the line the person is on
    gate_time: dict = field(default_factory=dict)  # gate id -> when they last crossed it

    def velocity(self) -> tuple[np.ndarray, np.ndarray | None] | None:
        """(pixels/s, metres/s or None) over the recent path, or None when the path is too short."""
        now = self.path[-1][0]
        recent = [p for p in self.path if now - p[0] <= VELOCITY_WINDOW_S]
        if len(recent) < 6 or recent[-1][0] - recent[0][0] < MIN_VELOCITY_SPAN_S:
            return None
        head, tail = recent[:3], recent[-3:]  # average the ends so one jittery box does not set the speed
        dt = np.mean([p[0] for p in tail]) - np.mean([p[0] for p in head])
        px = (np.mean([p[1] for p in tail], axis=0) - np.mean([p[1] for p in head], axis=0)) / dt
        if recent[0][2] is None:
            return px, None
        ground = (np.mean([p[2] for p in tail], axis=0) - np.mean([p[2] for p in head], axis=0)) / dt
        return px, (ground if np.all(np.isfinite(ground)) else None)


def _iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-6)


@dataclass
class _GateCounter:
    gate: Gate
    a: np.ndarray  # line ends in pixels
    b: np.ndarray
    total_in: int = 0
    total_out: int = 0
    events: deque = field(default_factory=deque)  # (t, +1 in / -1 out)

    @property
    def length(self) -> float:
        return float(np.hypot(*(self.b - self.a))) + 1e-9

    def side(self, point: np.ndarray) -> float:
        """Signed area: positive on the "in" side. Divide by length for the distance to the line in pixels."""
        d, r = self.b - self.a, point - self.a
        return float(d[0] * r[1] - d[1] * r[0])

    def within(self, point: np.ndarray) -> bool:
        """True when the point lies alongside the segment, not past either end."""
        d = self.b - self.a
        s = float(np.dot(point - self.a, d) / (np.dot(d, d) + 1e-9))
        return 0.0 <= s <= 1.0


class FlowTracker:
    """One per camera source. Feed it every frame's detections; it returns flow per zone and gate counts."""

    def __init__(self, n_zones: int, gates: tuple[Gate, ...], frame_w: int, frame_h: int):
        self.n_zones = n_zones
        self._tracks: list[Track] = []
        self._next_id = 1
        self._started: float | None = None
        self._last_t: float | None = None
        self._smooth: list[dict | None] = [None] * n_zones
        size = np.array([frame_w, frame_h], dtype=np.float64)
        self._gates = [_GateCounter(g, np.array(g.line[0]) * size, np.array(g.line[1]) * size) for g in gates]

    def update(self, boxes: np.ndarray, zone_idx: np.ndarray, ground: np.ndarray | None,
               densities: list[float], t: float) -> tuple[list[dict | None], list[dict]]:
        """ground: (N, 2) metres per box, or None when the camera is not calibrated against the floor."""
        if self._started is None:
            self._started = t
        track_of_box = self._associate(boxes)
        anchors = np.stack([(boxes[:, 0] + boxes[:, 2]) / 2, boxes[:, 3]], axis=1) if len(boxes) else np.zeros((0, 2))

        per_zone: list[list] = [[] for _ in range(self.n_zones)]
        for i, track in enumerate(track_of_box):
            track.path.append((t, anchors[i], None if ground is None else ground[i]))
            self._check_gates(track, anchors[i], t)
            if zone_idx[i] >= 0 and (v := track.velocity()) is not None:
                per_zone[zone_idx[i]].append(v)

        dt = 0.0 if self._last_t is None else t - self._last_t
        self._last_t = t
        flows = [self._zone_flow(z, vs, densities[z], dt) for z, vs in enumerate(per_zone)]
        return flows, [self._gate_stats(g, t) for g in self._gates]

    # ---- tracking ----------------------------------------------------------------
    def _associate(self, boxes: np.ndarray) -> list[Track]:
        """Greedy matching by box overlap. Returns the track for each box, creating tracks as needed."""
        assigned: list[Track | None] = [None] * len(boxes)
        if self._tracks and len(boxes):
            iou = _iou_matrix(np.stack([tr.box for tr in self._tracks]), boxes[:, :4])
            used_tracks: set[int] = set()
            for flat in np.argsort(-iou, axis=None):
                ti, bi = divmod(int(flat), len(boxes))
                if iou[ti, bi] < MATCH_IOU:
                    break
                if ti in used_tracks or assigned[bi] is not None:
                    continue
                used_tracks.add(ti)
                assigned[bi] = self._tracks[ti]
        seen = {id(tr) for tr in assigned if tr is not None}
        survivors = []
        for tr in self._tracks:
            tr.missed = 0 if id(tr) in seen else tr.missed + 1
            if tr.missed <= MAX_MISSED:
                survivors.append(tr)
        for bi in range(len(boxes)):
            if assigned[bi] is None:
                assigned[bi] = Track(self._next_id, boxes[bi, :4])
                self._next_id += 1
                survivors.append(assigned[bi])
            assigned[bi].box = boxes[bi, :4]
        self._tracks = survivors
        return assigned  # type: ignore[return-value]

    # ---- zone flow ---------------------------------------------------------------
    def _zone_flow(self, zone: int, velocities: list, density: float, dt: float) -> dict | None:
        ground = [g for _px, g in velocities if g is not None and np.hypot(*g) <= MAX_SPEED_MPS]
        if len(ground) < MIN_PEOPLE:
            self._smooth[zone] = None
            return None
        g = np.array(ground)
        px = np.array([p for p, gr in velocities if gr is not None and np.hypot(*gr) <= MAX_SPEED_MPS])
        speeds = np.hypot(g[:, 0], g[:, 1])
        mean_vec = g.mean(axis=0)
        raw = {
            "speed": float(speeds.mean()),
            # 1 = everyone walking the same way, 0 = movement cancels out (counter-flow or milling about)
            "alignment": float(np.hypot(*mean_vec) / (speeds.mean() + 1e-6)),
            # Helbing's crowd pressure: local density x variance of velocity. Meaningful in dense crowds.
            "pressure": float(density * ((g - mean_vec) ** 2).sum(axis=1).mean()),
            "dir": px.mean(axis=0) / (np.hypot(*px.mean(axis=0)) + 1e-6),  # unit vector on screen
        }
        prev = self._smooth[zone]
        if prev is None:
            self._smooth[zone] = raw
        else:
            alpha = 1.0 - math.exp(-dt / SMOOTH_TAU_S)
            for key in raw:
                prev[key] = prev[key] + alpha * (raw[key] - prev[key])
        s = self._smooth[zone]
        moving = s["speed"] >= MOVING_MPS and s["alignment"] >= 0.3
        return {
            "speed_mps": round(s["speed"], 2),
            "alignment": round(min(s["alignment"], 1.0), 2),
            "pressure": round(s["pressure"], 3),
            "heading_deg": round(math.degrees(math.atan2(s["dir"][1], s["dir"][0]))) if moving else None,
            "tracked": len(ground),
        }

    # ---- gates -------------------------------------------------------------------
    def _check_gates(self, track: Track, anchor: np.ndarray, t: float) -> None:
        # A person only changes side once they are clearly past the line, so a box that jitters on
        # the line is not counted back and forth.
        margin = max(4.0, 0.08 * float(track.box[3] - track.box[1]))
        for g in self._gates:
            side = g.side(anchor) / g.length
            if abs(side) < margin:
                continue
            previous = track.gate_side.get(g.gate.id)
            track.gate_side[g.gate.id] = side
            if previous is None or (side > 0) == (previous > 0) or not g.within(anchor):
                continue
            if t - track.gate_time.get(g.gate.id, -1e9) < GATE_REARM_S:
                continue
            track.gate_time[g.gate.id] = t
            direction = 1 if side > 0 else -1  # crossing to the positive side of the line counts as "in"
            g.events.append((t, direction))
            if direction > 0:
                g.total_in += 1
            else:
                g.total_out += 1

    def _gate_stats(self, g: _GateCounter, t: float) -> dict:
        while g.events and t - g.events[0][0] > GATE_WINDOW_S:
            g.events.popleft()
        minutes = min(max(t - self._started, 10.0), GATE_WINDOW_S) / 60.0
        return {
            "id": g.gate.id,
            "in_per_min": round(sum(1 for _, d in g.events if d > 0) / minutes, 1),
            "out_per_min": round(sum(1 for _, d in g.events if d < 0) / minutes, 1),
            "total_in": g.total_in, "total_out": g.total_out,
        }
