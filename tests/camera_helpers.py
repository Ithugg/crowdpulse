"""A synthetic pinhole camera, written from the geometry (not from the backend's code), so the
calibration tests compare the backend against an independent projection."""
from __future__ import annotations

import math

import numpy as np

from backend.calibration import GroundCalibration, calibration_from_params

W, H = 1280, 720
HFOV = 60.0
CAM_HEIGHT = 6.0
TILT_DEG = 25.0
PERSON_M = 1.7


def make_camera(cam_height: float = CAM_HEIGHT, tilt_deg: float = TILT_DEG, w: int = W, h: int = H,
                hfov: float = HFOV) -> GroundCalibration:
    return calibration_from_params(w, h, hfov, cam_height, tilt_deg)


def project(cam: GroundCalibration, sideways, forward, up=0.0):
    """Pixel (x, y) of points `forward` metres ahead along the floor, `sideways` metres to the right and
    `up` metres above the floor. The camera is cam_height_m up, looking `tilt` below horizontal."""
    sideways, forward, up = (np.asarray(v, dtype=np.float64) for v in (sideways, forward, up))
    sin, cos = math.sin(cam.tilt_rad), math.cos(cam.tilt_rad)
    drop = cam.cam_height_m - up                      # how far the point is below the camera
    depth = forward * cos + drop * sin                # distance along the optical axis
    below_axis = -forward * sin + drop * cos          # offset towards the bottom of the image
    return cam.frame_w / 2 + cam.focal_px * sideways / depth, cam.frame_h / 2 + cam.focal_px * below_axis / depth


def person_boxes(cam: GroundCalibration, sideways, forward, conf: float = 0.9,
                 width_ratio: float = 0.35) -> np.ndarray:
    """[x1, y1, x2, y2, conf] of 1.7 m tall people standing at the given floor positions."""
    sideways, forward = np.atleast_1d(sideways).astype(np.float64), np.atleast_1d(forward).astype(np.float64)
    fx, fy = project(cam, sideways, forward, 0.0)
    _, hy = project(cam, sideways, forward, PERSON_M)
    half_w = (fy - hy) * width_ratio / 2
    return np.stack([fx - half_w, hy, fx + half_w, fy, np.full(len(fx), conf)], axis=1)


def random_people(cam: GroundCalibration, n: int, seed: int = 1, noise: float = 0.0,
                  forward_range=(8.0, 30.0), side_range=(-8.0, 8.0)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    boxes = person_boxes(cam, rng.uniform(*side_range, n), rng.uniform(*forward_range, n))
    if noise:
        boxes[:, :4] *= 1.0 + rng.normal(0.0, noise, (n, 4))
    return boxes
