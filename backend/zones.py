"""Assigns detections to named zones and measures crowd density in real units (people per m2)."""
from __future__ import annotations

import cv2
import numpy as np

from .calibration import SceneGeometry, local_density
from .config import Thresholds, Zone

NORMAL, BUSY, CAUTION, DANGER, CRITICAL = "normal", "busy", "caution", "danger", "critical"
LEVELS = (NORMAL, BUSY, CAUTION, DANGER, CRITICAL)
LEVEL_RANK = {level: i for i, level in enumerate(LEVELS)}

# What each level means and where the number comes from. Sent to the dashboard for its legend.
LEVEL_INFO = {
    NORMAL: ("Normal", "People move freely.", "Fruin, level-of-service scale"),
    BUSY: ("Busy", "Movement is restricted and people slow down. Monitor.", "Fruin; G. Keith Still"),
    CAUTION: ("Caution", "4/m² is the safe limit for a moving crowd. Congestion can build quickly and the "
                         "risk of stumbling rises.", "UK Green Guide; Still; Helbing & Mukerji (Love Parade)"),
    DANGER: ("Danger", "People are in constant physical contact and at risk if anyone pushes.", "G. Keith Still"),
    CRITICAL: ("Critical", "Hard to stay upright, surges can start, and flow drops by a factor of 3 or more.",
               "Still; Helbing, Johansson & Al-Abideen 2007 (Hajj study)"),
}

PEAK_PERCENTILE = 90  # a zone's density is its local peak, not its average: averages hide dangerous pockets


def anchor_points(boxes: np.ndarray) -> np.ndarray:
    """Ground position of each detection: bottom-centre of its box, as (N, 2) pixel coords."""
    if len(boxes) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    return np.stack([(boxes[:, 0] + boxes[:, 2]) / 2, boxes[:, 3]], axis=1)


class ZoneCounter:
    """Rasterises the zone polygons once per frame size, so assignment is a single mask lookup."""

    def __init__(self, zones: tuple[Zone, ...], frame_w: int, frame_h: int, geometry: SceneGeometry | None = None):
        self.zones = zones
        self.frame_w, self.frame_h = frame_w, frame_h
        self.geometry = geometry or SceneGeometry(frame_w, frame_h, 60.0, None)
        self.polygons_px = [
            np.array([[x * frame_w, y * frame_h] for x, y in z.polygon], dtype=np.int32) for z in zones
        ]
        self._mask = np.zeros((frame_h, frame_w), dtype=np.uint8)
        for i, pts in enumerate(self.polygons_px):
            cv2.fillPoly(self._mask, [pts], i + 1)
        # Real floor area of each zone, only known when the camera is calibrated against the ground.
        calib = self.geometry.calibration
        self.areas_m2: list[float | None] = [
            round(calib.mask_area_m2(self._mask == i + 1), 1) if calib else None for i in range(len(zones))
        ]

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

    def measure(self, boxes: np.ndarray) -> tuple[np.ndarray, list[int], list[float], np.ndarray]:
        """Returns (zone index per box, count per zone, peak local density per zone, local density per box)."""
        zone_idx = self.assign(boxes)
        rho = local_density(self.geometry.positions(boxes))
        peaks = []
        for i in range(len(self.zones)):
            inside = rho[zone_idx == i]
            peaks.append(float(np.percentile(inside, PEAK_PERCENTILE)) if len(inside) else 0.0)
        return zone_idx, self.counts(zone_idx), peaks, rho


def level_for(density: float, thresholds: Thresholds, previous: str = NORMAL, margin: float = 0.1) -> str:
    """Level for a density, with hysteresis: a zone steps down only once it is clearly below the threshold."""
    steps = thresholds.steps
    i = LEVEL_RANK[previous]
    while i < len(steps) and density >= steps[i]:
        i += 1
    while i > 0 and density < steps[i - 1] * (1 - margin):
        i -= 1
    return LEVELS[i]
