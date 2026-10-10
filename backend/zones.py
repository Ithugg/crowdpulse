"""Assigns detections to named zones and turns counts into density (people per m2)."""
from __future__ import annotations

import cv2
import numpy as np

from .config import Thresholds, Zone

GREEN, YELLOW, RED = "green", "yellow", "red"
LEVEL_RANK = {GREEN: 0, YELLOW: 1, RED: 2}


def anchor_points(boxes: np.ndarray) -> np.ndarray:
    """Ground position of each detection: bottom-centre of its box, as (N, 2) pixel coords."""
    if len(boxes) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    return np.stack([(boxes[:, 0] + boxes[:, 2]) / 2, boxes[:, 3]], axis=1)


class ZoneCounter:
    """Rasterises the zone polygons once per frame size, so assignment is a single mask lookup."""

    def __init__(self, zones: tuple[Zone, ...], frame_w: int, frame_h: int):
        self.zones = zones
        self.frame_w, self.frame_h = frame_w, frame_h
        self.polygons_px = [
            np.array([[x * frame_w, y * frame_h] for x, y in z.polygon], dtype=np.int32) for z in zones
        ]
        self._mask = np.zeros((frame_h, frame_w), dtype=np.uint8)
        for i, pts in enumerate(self.polygons_px):
            cv2.fillPoly(self._mask, [pts], i + 1)

    def assign(self, boxes: np.ndarray) -> np.ndarray:
        """Zone index for each box, or -1 when it falls outside every zone."""
        if len(boxes) == 0:
            return np.zeros((0,), dtype=np.int32)
        pts = anchor_points(boxes)
        xs = np.clip(pts[:, 0], 0, self.frame_w - 1).astype(np.int32)
        ys = np.clip(pts[:, 1], 0, self.frame_h - 1).astype(np.int32)
        return self._mask[ys, xs].astype(np.int32) - 1

    def counts(self, zone_idx: np.ndarray) -> list[int]:
        return [int(np.count_nonzero(zone_idx == i)) for i in range(len(self.zones))]


def level_for(density: float, thresholds: Thresholds, previous: str = GREEN, margin: float = 0.1) -> str:
    """Green/yellow/red with hysteresis: a zone steps down only once it is clearly below the threshold."""
    warn, critical = thresholds.warn, thresholds.critical
    if previous == RED:
        critical *= 1 - margin
    if previous in (YELLOW, RED):
        warn *= 1 - margin
    if density >= critical:
        return RED
    if density >= warn:
        return YELLOW
    return GREEN
