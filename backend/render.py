"""Draws detection boxes, the density heatmap and (for the OpenCV preview) zone outlines."""
from __future__ import annotations

import cv2
import numpy as np

from .zones import GREEN, RED, YELLOW, anchor_points

# BGR
LEVEL_COLORS = {GREEN: (120, 200, 60), YELLOW: (40, 190, 250), RED: (70, 60, 240)}
BOX_COLOR = (235, 215, 150)
OUTSIDE_COLOR = (150, 150, 150)

HEATMAP_SCALE = 8  # heatmap is built at 1/8 resolution, then upsampled
HEATMAP_DECAY = 0.75  # temporal smoothing between frames


def draw_boxes(frame: np.ndarray, boxes: np.ndarray, zone_idx: np.ndarray | None = None) -> None:
    for i, (x1, y1, x2, y2, _conf) in enumerate(boxes):
        inside = zone_idx is None or zone_idx[i] >= 0
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                      BOX_COLOR if inside else OUTSIDE_COLOR, 1, cv2.LINE_AA)


class HeatmapRenderer:
    """Gaussian splat per person, smoothed over time and blended onto the frame as a colour overlay."""

    def __init__(self):
        self._acc: np.ndarray | None = None

    def reset(self) -> None:
        self._acc = None

    def draw(self, frame: np.ndarray, boxes: np.ndarray) -> None:
        h, w = frame.shape[:2]
        sh, sw = max(h // HEATMAP_SCALE, 1), max(w // HEATMAP_SCALE, 1)
        grid = np.zeros((sh, sw), dtype=np.float32)
        if len(boxes):
            pts = anchor_points(boxes)
            # Use the middle of each box rather than the feet so the glow sits on the person.
            ys = (boxes[:, 1] + boxes[:, 3]) / 2
            xs = np.clip(pts[:, 0] / HEATMAP_SCALE, 0, sw - 1).astype(np.int32)
            ys = np.clip(ys / HEATMAP_SCALE, 0, sh - 1).astype(np.int32)
            np.add.at(grid, (ys, xs), 1.0)
            # Blob size follows the typical person size, so it adapts to camera distance.
            sigma = max(float(np.median(boxes[:, 2] - boxes[:, 0])) / HEATMAP_SCALE * 0.6, 1.5)
            grid = cv2.GaussianBlur(grid, (0, 0), sigma) * (2 * np.pi * sigma * sigma)
        if self._acc is None or self._acc.shape != grid.shape:
            self._acc = grid
        else:
            self._acc = HEATMAP_DECAY * self._acc + (1 - HEATMAP_DECAY) * grid

        # ~1.0 where one person stands alone; saturates when several overlap.
        norm = np.clip(self._acc / 3.0, 0.0, 1.0)
        norm = cv2.resize(norm, (w, h), interpolation=cv2.INTER_LINEAR)
        colour = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
        alpha = (np.clip(norm * 1.6, 0.0, 0.6))[..., None]
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
