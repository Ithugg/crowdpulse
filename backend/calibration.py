"""Estimates real ground area from the video itself, using the people in view as a ruler.

A standing adult is about 1.7 m tall. How tall people appear at each height in the image tells us how
high the camera is and how steeply it looks down. With those two numbers every pixel on the floor maps
to a position in metres, which gives the real area of a zone and real distances between people.

Assumptions (stated in the README): flat ground, upright camera (no roll), average person height
1.7 m, and a lens field of view that is configured per source (default 60 degrees horizontal).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

PERSON_HEIGHT_M = 1.7
DEFAULT_HFOV_DEG = 60.0
MAX_RANGE_M = 40.0  # floor further away than this is ignored (too few pixels to trust)
AREA_TRUST_RANGE_M = 30.0  # zone areas are only reported when the whole zone is nearer than this
MIN_SAMPLES = 150
MAX_FIT_ERROR = 0.20  # median relative error in predicted person height; above this the fit is rejected
SHOULDER_WIDTH_M = 0.5


def focal_px(frame_w: int, hfov_deg: float) -> float:
    return (frame_w / 2) / math.tan(math.radians(hfov_deg) / 2)


@dataclass(frozen=True)
class GroundCalibration:
    frame_w: int
    frame_h: int
    focal_px: float
    tilt_rad: float  # how far the camera looks down from horizontal
    cam_height_m: float
    fit_error: float  # median relative error of predicted vs observed person height
    samples: int

    @property
    def horizon_y(self) -> float:
        return self.frame_h / 2 - self.focal_px * math.tan(self.tilt_rad)

    def to_ground(self, points_px: np.ndarray) -> np.ndarray:
        """Image points (N, 2) standing on the floor -> (N, 2) metres: [sideways, forward]. NaN above the horizon."""
        pts = np.asarray(points_px, dtype=np.float64).reshape(-1, 2)
        forward, depth = _ground_distance(pts[:, 1], self.frame_h, self.focal_px, self.tilt_rad, self.cam_height_m)
        sideways = (pts[:, 0] - self.frame_w / 2) * depth / self.focal_px
        return np.stack([sideways, forward], axis=1)

    def row_area_m2(self) -> np.ndarray:
        """Ground area covered by ONE pixel in each image row (frame_h,). Zero above the horizon or out of range."""
        ys = np.arange(self.frame_h, dtype=np.float64)
        forward, depth = _ground_distance(ys, self.frame_h, self.focal_px, self.tilt_rad, self.cam_height_m)
        metres_per_px_sideways = depth / self.focal_px
        metres_per_px_forward = np.abs(np.gradient(forward))
        area = metres_per_px_sideways * metres_per_px_forward
        area[~np.isfinite(area) | (forward > MAX_RANGE_M)] = 0.0
        return area

    def mask_area_m2(self, mask: np.ndarray) -> float | None:
        """Real floor area of the pixels set in a boolean (frame_h, frame_w) mask.

        None when part of the mask is further than AREA_TRUST_RANGE_M (or above the horizon): out
        there one pixel covers so much floor that a small error in the lens assumption changes the
        answer several-fold, so no number is better than a wrong one."""
        rows = mask.sum(axis=1)
        forward, _ = _ground_distance(np.arange(self.frame_h), self.frame_h, self.focal_px, self.tilt_rad,
                                      self.cam_height_m)
        used = rows > 0
        if not used.any() or not np.all(np.isfinite(forward[used])) or forward[used].max() > AREA_TRUST_RANGE_M:
            return None
        return float((rows * self.row_area_m2()).sum())


def _ground_distance(ys, frame_h, focal, tilt, cam_height):
    """For image rows ys: (horizontal distance along the floor, depth along the optical axis). NaN above the horizon."""
    t = (np.asarray(ys, dtype=np.float64) - frame_h / 2) / focal
    denom = math.sin(tilt) + t * math.cos(tilt)
    with np.errstate(divide="ignore", invalid="ignore"):
        forward = cam_height * (math.cos(tilt) - t * math.sin(tilt)) / denom
    forward = np.where(denom > 1e-4, forward, np.nan)
    depth = forward * math.cos(tilt) + cam_height * math.sin(tilt)
    return forward, depth


def usable_boxes(boxes: np.ndarray, frame_w: int, frame_h: int) -> np.ndarray:
    """Whole, upright people only: boxes cut off by the frame edge or oddly shaped would skew the fit."""
    if len(boxes) == 0:
        return boxes
    w, h = boxes[:, 2] - boxes[:, 0], boxes[:, 3] - boxes[:, 1]
    edge = 4
    inside = (boxes[:, 0] > edge) & (boxes[:, 1] > edge) & (boxes[:, 2] < frame_w - edge) & (boxes[:, 3] < frame_h - edge)
    shape = (h / np.maximum(w, 1) > 1.4) & (h / np.maximum(w, 1) < 5.0)
    return boxes[inside & shape & (boxes[:, 4] >= 0.35)]


def _fit_loss(foot_y, height, frame_h, focal, tilts, cam_heights):
    """Median relative error of predicted person height for every (tilt, camera height) pair."""
    t = ((foot_y - frame_h / 2) / focal)[None, None, :]
    tilts, cam_heights = tilts[:, None, None], cam_heights[None, :, None]
    sin, cos = np.sin(tilts), np.cos(tilts)
    denom = sin + t * cos
    # Exact pinhole model: where would the head of a 1.7 m person appear if their feet are at this row?
    with np.errstate(divide="ignore", invalid="ignore"):
        forward = cam_heights * (cos - t * sin) / denom
        head = cam_heights - PERSON_HEIGHT_M
        head_t = (-forward * sin + head * cos) / (forward * cos + head * sin)
        error = np.abs(np.log((t - head_t) * focal / height[None, None, :]))
    error = np.where((denom > 1e-4) & np.isfinite(error), np.minimum(error, 1.0), 1.0)
    return np.median(error, axis=2)


def fit_calibration(boxes: np.ndarray, frame_w: int, frame_h: int,
                    hfov_deg: float = DEFAULT_HFOV_DEG) -> GroundCalibration | None:
    """Fits camera height and tilt to many person boxes ([x1, y1, x2, y2, conf]) gathered over time.
    Returns None when there are too few whole-body detections or the fit is poor."""
    boxes = usable_boxes(boxes, frame_w, frame_h)
    if len(boxes) < MIN_SAMPLES:
        return None
    if len(boxes) > 1500:
        boxes = boxes[np.random.default_rng(0).choice(len(boxes), 1500, replace=False)]
    foot_y, height = boxes[:, 3].astype(np.float64), (boxes[:, 3] - boxes[:, 1]).astype(np.float64)
    focal = focal_px(frame_w, hfov_deg)

    # Coarse search, then refine around the best cell.
    tilts, cam_heights = np.radians(np.arange(2.0, 88.0, 2.0)), np.geomspace(1.2, 40.0, 60)
    loss = _fit_loss(foot_y, height, frame_h, focal, tilts, cam_heights)
    ti, hi = np.unravel_index(np.argmin(loss), loss.shape)
    tilts = np.clip(tilts[ti] + np.radians(np.arange(-2.0, 2.01, 0.25)), np.radians(1.0), np.radians(89.0))
    cam_heights = cam_heights[hi] * np.geomspace(0.92, 1.08, 17)
    loss = _fit_loss(foot_y, height, frame_h, focal, tilts, cam_heights)
    ti, hi = np.unravel_index(np.argmin(loss), loss.shape)
    if loss[ti, hi] > MAX_FIT_ERROR:
        return None
    return GroundCalibration(frame_w, frame_h, focal, float(tilts[ti]), float(cam_heights[hi]),
                             float(loss[ti, hi]), len(boxes))


def calibration_from_params(frame_w: int, frame_h: int, hfov_deg: float, cam_height_m: float,
                            tilt_deg: float) -> GroundCalibration:
    """A calibration stored in config/sources.yaml (written by scripts/calibrate.py)."""
    return GroundCalibration(frame_w, frame_h, focal_px(frame_w, hfov_deg), math.radians(tilt_deg),
                             cam_height_m, 0.0, 0)


class SceneGeometry:
    """Where each detected person stands, in metres, so density can be measured in real units.

    mode "ground": the camera calibration maps each person's feet onto the floor (accurate).
    mode "size":   fallback when feet are not visible (a webcam at table height): distance is taken
                   from apparent body width, assuming shoulders are about 0.5 m wide.
    """

    def __init__(self, frame_w: int, frame_h: int, hfov_deg: float, calibration: GroundCalibration | None):
        self.frame_w, self.frame_h = frame_w, frame_h
        self.focal = focal_px(frame_w, hfov_deg)
        self.calibration = calibration
        self.mode = "ground" if calibration else "size"

    def positions(self, boxes: np.ndarray) -> np.ndarray:
        """(N, 2) metres [sideways, forward] for each box."""
        if len(boxes) == 0:
            return np.zeros((0, 2), dtype=np.float64)
        centre_x = (boxes[:, 0] + boxes[:, 2]) / 2
        if self.calibration:
            return self.calibration.to_ground(np.stack([centre_x, boxes[:, 3]], axis=1))
        width = np.maximum(boxes[:, 2] - boxes[:, 0], 1.0).astype(np.float64)
        forward = self.focal * SHOULDER_WIDTH_M / width
        return np.stack([(centre_x - self.frame_w / 2) * forward / self.focal, forward], axis=1)


def local_density(ground_xy: np.ndarray, radius_m: float = 1.0) -> np.ndarray:
    """Local crowd density (people/m2) at each person's position.

    Gaussian-kernel local density as used by Helbing, Johansson & Al-Abideen (2007):
    rho(r) = sum_j exp(-|r_j - r|^2 / R^2) / (pi R^2). For an evenly spread crowd it equals the true
    density; a small group standing together does not look like a packed crowd.
    """
    if len(ground_xy) == 0:
        return np.zeros((0,), dtype=np.float64)
    diff = ground_xy[:, None, :] - ground_xy[None, :, :]
    dist2 = np.nan_to_num((diff ** 2).sum(axis=2), nan=np.inf)
    return np.exp(-dist2 / radius_m ** 2).sum(axis=1) / (math.pi * radius_m ** 2)
