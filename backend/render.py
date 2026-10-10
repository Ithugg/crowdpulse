"""Draws detection boxes, the density heatmap and (for the OpenCV preview) zone outlines."""
from __future__ import annotations

import cv2
import numpy as np

from .zones import BUSY, CAUTION, CRITICAL, DANGER, NORMAL

# BGR
LEVEL_COLORS = {NORMAL: (143, 208, 63), BUSY: (143, 208, 63), CAUTION: (59, 185, 246),
                DANGER: (61, 138, 255), CRITICAL: (97, 79, 255)}
BOX_COLOR = (235, 215, 150)
OUTSIDE_COLOR = (150, 150, 150)

HEATMAP_SCALE = 8  # heatmap is built at 1/8 resolution, then upsampled
HEATMAP_DECAY = 0.75  # temporal smoothing between frames


def draw_boxes(frame: np.ndarray, boxes: np.ndarray, zone_idx: np.ndarray | None = None) -> None:
    for i, (x1, y1, x2, y2, _conf) in enumerate(boxes):
        inside = zone_idx is None or zone_idx[i] >= 0
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                      BOX_COLOR if inside else OUTSIDE_COLOR, 1, cv2.LINE_AA)


def pixelate_heads(frame: np.ndarray, boxes: np.ndarray) -> None:
    """Privacy mode: pixelates the head region of every detected person so nobody can be identified."""
    h, w = frame.shape[:2]
    for x1, y1, x2, y2, _conf in boxes:
        bw, bh = x2 - x1, y2 - y1
        # Head height: about a fifth of a full-body box, about half of a head-and-shoulders box.
        head_h = max(min(0.6 * bw, 0.5 * bh), 0.15 * bh)
        xa, xb = int(max(x1 + 0.1 * bw, 0)), int(min(x2 - 0.1 * bw, w))
        ya, yb = int(max(y1, 0)), int(min(y1 + head_h, h))
        if xb - xa < 4 or yb - ya < 4:
            continue
        region = frame[ya:yb, xa:xb]
        small = cv2.resize(region, (4, 4), interpolation=cv2.INTER_AREA)
        frame[ya:yb, xa:xb] = cv2.resize(small, (xb - xa, yb - ya), interpolation=cv2.INTER_NEAREST)


def _density_colours() -> np.ndarray:
    """256-entry BGR lookup: green up to the safe limit, then yellow, orange, red at critical density."""
    stops = [(0.0, (143, 208, 63)), (0.55, (143, 208, 63)), (0.67, (59, 185, 246)),
             (0.83, (61, 138, 255)), (1.0, (97, 79, 255))]
    xs = np.array([s[0] for s in stops]) * 255
    lut = np.stack([np.interp(np.arange(256), xs, [s[1][c] for s in stops]) for c in range(3)], axis=1)
    return lut.astype(np.uint8)


class HeatmapRenderer:
    """Glow under each person, coloured by the real local density there (people/m2) on the same scale
    as the zone levels: green below the safe limit, red at critical. Smoothed over time."""

    def __init__(self):
        self._num: np.ndarray | None = None
        self._den: np.ndarray | None = None
        self._lut = _density_colours()

    def reset(self) -> None:
        self._num = self._den = None

    def draw(self, frame: np.ndarray, boxes: np.ndarray, densities: np.ndarray, critical: float) -> None:
        h, w = frame.shape[:2]
        sh, sw = max(h // HEATMAP_SCALE, 1), max(w // HEATMAP_SCALE, 1)
        num, den = np.zeros((sh, sw), dtype=np.float32), np.zeros((sh, sw), dtype=np.float32)
        if len(boxes):
            # Middle of each box rather than the feet, so the glow sits on the person.
            xs = np.clip((boxes[:, 0] + boxes[:, 2]) / 2 / HEATMAP_SCALE, 0, sw - 1).astype(np.int32)
            ys = np.clip((boxes[:, 1] + boxes[:, 3]) / 2 / HEATMAP_SCALE, 0, sh - 1).astype(np.int32)
            np.add.at(num, (ys, xs), np.clip(densities / critical, 0.0, 1.0))
            np.add.at(den, (ys, xs), 1.0)
            # Blob size follows the typical person size, so it adapts to camera distance.
            sigma = max(float(np.median(boxes[:, 2] - boxes[:, 0])) / HEATMAP_SCALE * 0.7, 1.5)
            peak = 2 * np.pi * sigma * sigma
            num, den = cv2.GaussianBlur(num, (0, 0), sigma) * peak, cv2.GaussianBlur(den, (0, 0), sigma) * peak
        if self._den is None or self._den.shape != den.shape:
            self._num, self._den = num, den
        else:
            self._num = HEATMAP_DECAY * self._num + (1 - HEATMAP_DECAY) * num
            self._den = HEATMAP_DECAY * self._den + (1 - HEATMAP_DECAY) * den

        value = cv2.resize(self._num / (self._den + 1e-3), (w, h), interpolation=cv2.INTER_LINEAR)
        presence = cv2.resize(np.clip(self._den, 0.0, 1.0), (w, h), interpolation=cv2.INTER_LINEAR)
        colour = self._lut[(np.clip(value, 0.0, 1.0) * 255).astype(np.uint8)]
        alpha = (presence * (0.14 + 0.46 * np.clip(value, 0.0, 1.0)))[..., None]
        np.copyto(frame, (frame * (1 - alpha) + colour * alpha).astype(np.uint8))


def draw_zones(frame: np.ndarray, polygons_px: list[np.ndarray], labels: list[str], levels: list[str]) -> None:
    """Zone outlines + labels. Only the OpenCV preview uses this; the dashboard draws zones in SVG."""
    overlay = frame.copy()
    for pts, level in zip(polygons_px, levels):
        cv2.fillPoly(overlay, [pts], LEVEL_COLORS[level])
    cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, dst=frame)
    for pts, label, level in zip(polygons_px, labels, levels):
        cv2.polylines(frame, [pts], True, LEVEL_COLORS[level], 2, cv2.LINE_AA)
        x, y = int(pts[:, 0].min()) + 8, int(pts[:, 1].min()) + 24
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x - 4, y - th - 6), (x + tw + 4, y + 6), (20, 20, 20), -1)
        cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, LEVEL_COLORS[level], 2, cv2.LINE_AA)


def encode_jpeg(frame: np.ndarray, quality: int = 70) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else b""


def resize_to_width(frame: np.ndarray, width: int) -> tuple[np.ndarray, float]:
    """Returns the resized frame and the scale factor applied (1.0 when already small enough)."""
    h, w = frame.shape[:2]
    if w <= width:
        return frame, 1.0
    scale = width / w
    return cv2.resize(frame, (width, int(round(h * scale))), interpolation=cv2.INTER_AREA), scale
