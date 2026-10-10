"""Drill mode: a simulated camera over a simulated crowd, for rehearsing the response to a build-up.

Nothing in the footage we have is dense enough to raise an alert, and readings from real video are
never scaled. A drill is the honest way to exercise the alert states: scripted people stand on a
virtual floor under a virtual camera, and their boxes go through the same measurement, level, forecast
and alert code as a real camera's. Everything a drill produces is labelled as one.
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from .calibration import PERSON_HEIGHT_M, SHOULDER_WIDTH_M, GroundCalibration, calibration_from_params
from .config import Source

DRILL_LABEL = "DRILL: SIMULATED READINGS"
CYCLE_S = 240.0  # the script repeats
# Density each zone is filled to (people/m2) over one cycle: (seconds, density) corners, straight lines
# between. The first zone fills past critical and is then relieved; the other two stay below busy, so
# every alert is about one place and a response plan has somewhere to send people. Any further zone
# copies the third. The board reads a little above these figures, because a zone's reading is its
# local peak, not its average.
SCRIPTS = (
    ((0, 2.4), (44, 3.9), (58, 4.8), (72, 5.75), (80, 6.2), (130, 6.2), (190, 2.4), (240, 2.4)),
    ((0, 1.2), (120, 1.35), (240, 1.2)),
    ((0, 0.7), (240, 0.7)),
)
EDGE_M = 0.15  # people keep this far inside a zone's edge, so their feet are never on the line
SWAY_M = 0.03  # how far a standing person shifts about
MAX_CHANGE_PER_FRAME = 4  # arrivals or departures per zone per frame

FLOOR = (40, 42, 44)  # BGR
FLOOR_LINE = (50, 52, 54)
CLOTHES = ((92, 78, 62), (70, 70, 74), (66, 88, 82), (64, 62, 96), (110, 104, 92), (98, 86, 58),
           (84, 84, 88), (58, 74, 104))
SKIN = ((150, 170, 205), (120, 150, 190), (90, 120, 165), (70, 95, 135))


def target_density(script: tuple, t: float) -> float:
    ts, ds = zip(*script)
    return float(np.interp(t % CYCLE_S, ts, ds))


def label_alerts(alerts: list[dict]) -> None:
    """Every log entry raised during a drill says so, wherever it is shown or reported later."""
    for alert in alerts:
        alert["drill"] = True
        alert["message"] = f"DRILL: {alert['message']}"


# The labels on a plan and a report are put on here, in code, whoever wrote the text (Gemini or the
# cached fallback): a drill must never depend on a language model remembering to say it is one.
def label_plan(plan: dict) -> dict:
    return {**plan, "headline": f"DRILL: {plan['headline']}"}


def label_report(report: dict) -> dict:
    return {**report, "title": f"DRILL: {report['title']}",
            "summary": f"This was a drill: every reading in this report was simulated. {report['summary']}"}


class DrillScene:
    """The scripted crowd: where everyone stands on the floor (metres), and what the camera sees of them."""

    def __init__(self, source: Source, calibration: GroundCalibration, seed: int = 7):
        self.calibration = calibration
        self._rng = np.random.default_rng(seed)
        self._scripts = [SCRIPTS[min(i, len(SCRIPTS) - 1)] for i in range(len(source.zones))]
        size = np.array([calibration.frame_w, calibration.frame_h], dtype=np.float64)
        # Each zone polygon in the config is a rectangle of floor seen in perspective: recover the rectangle.
        self._rects = []
        for zone in source.zones:
            ground = calibration.to_ground(np.array(zone.polygon) * size)
            self._rects.append((ground[:, 0].min(), ground[:, 0].max(), ground[:, 1].min(), ground[:, 1].max()))
        self._home = np.zeros((0, 2))  # where each person stands
        self._sway = np.zeros((0, 2))
        self._zone = np.zeros((0,), dtype=np.int32)
        self._look = np.zeros((0,), dtype=np.int32)
        self._floor = self._draw_floor()
        self.step(0.0, limit=None)

    # ---- the crowd ---------------------------------------------------------------
    def step(self, t: float, limit: int | None = MAX_CHANGE_PER_FRAME) -> np.ndarray:
        """Moves the crowd on to script time t and returns the camera's view of it as person boxes."""
        for i, (script, (x0, x1, z0, z1)) in enumerate(zip(self._scripts, self._rects)):
            want = round(target_density(script, t) * (x1 - x0) * (z1 - z0))
            change = want - int(np.count_nonzero(self._zone == i))
            if limit is not None:
                change = max(-limit, min(limit, change))
            for _ in range(change):
                self._arrive(i)
            for _ in range(-change):
                self._leave(i)
        # People shift their weight around the spot they stand on; nobody wanders off.
        self._sway = 0.92 * self._sway + self._rng.normal(0.0, SWAY_M * 0.39, self._sway.shape)
        return self.boxes()

    def _arrive(self, zone: int) -> None:
        """A newcomer takes the emptiest of a few random spots, the way people fill the gaps in a crowd."""
        x0, x1, z0, z1 = self._rects[zone]
        spots = np.stack([self._rng.uniform(x0 + EDGE_M, x1 - EDGE_M, 12),
                          self._rng.uniform(z0 + EDGE_M, z1 - EDGE_M, 12)], axis=1)
        there = self._home[self._zone == zone]
        best = 0
        if len(there):
            nearest = np.sqrt(((spots[:, None, :] - there[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
            best = int(np.argmax(nearest))
        self._home = np.vstack([self._home, spots[best]])
        self._sway = np.vstack([self._sway, np.zeros(2)])
        self._zone = np.append(self._zone, zone).astype(np.int32)
        self._look = np.append(self._look, self._rng.integers(0, 1 << 16)).astype(np.int32)

    def _leave(self, zone: int) -> None:
        """The most hemmed-in of a few random people goes, so a crowd that thins out stays evenly spread."""
        members = np.flatnonzero(self._zone == zone)
        if len(members) == 0:
            return
        there = self._home[members]
        picks = self._rng.choice(len(members), min(12, len(members)), replace=False)
        gaps = np.sqrt(((there[picks, None, :] - there[None, :, :]) ** 2).sum(axis=2))
        gaps[np.arange(len(picks)), picks] = np.inf  # not the distance to themselves
        keep = np.ones(len(self._zone), dtype=bool)
        keep[members[picks[int(np.argmin(gaps.min(axis=1)))]]] = False
        self._home, self._sway = self._home[keep], self._sway[keep]
        self._zone, self._look = self._zone[keep], self._look[keep]

    @property
    def positions(self) -> np.ndarray:
        return self._home + self._sway

    # ---- the camera --------------------------------------------------------------
    def boxes(self) -> np.ndarray:
        """[x1, y1, x2, y2, confidence] for each person: what a detector would report from this camera."""
        if len(self._home) == 0:
            return np.zeros((0, 5), dtype=np.float32)
        feet = self.calibration.to_image(self.positions)
        head = self.calibration.to_image(self.positions, PERSON_HEIGHT_M)
        half_w = (feet[:, 1] - head[:, 1]) * (SHOULDER_WIDTH_M / PERSON_HEIGHT_M) / 2
        return np.stack([feet[:, 0] - half_w, head[:, 1], feet[:, 0] + half_w, feet[:, 1],
                         np.full(len(feet), 0.9)], axis=1).astype(np.float32)

    def _draw_floor(self) -> np.ndarray:
        """An empty floor with a faint line every metre, so the picture reads as a floor seen from above."""
        calib = self.calibration
        floor = np.full((calib.frame_h, calib.frame_w, 3), FLOOR, dtype=np.uint8)
        near, far = 2.0, 40.0
        for x in range(-20, 21):
            a, b = calib.to_image(np.array([[x, near], [x, far]])).astype(int)
            cv2.line(floor, tuple(map(int, a)), tuple(map(int, b)), FLOOR_LINE, 1)
        for z in range(int(near), int(far) + 1):
            a, b = calib.to_image(np.array([[-30.0, z], [30.0, z]])).astype(int)
            cv2.line(floor, tuple(map(int, a)), tuple(map(int, b)), FLOOR_LINE, 1)
        return floor

    def render(self, boxes: np.ndarray) -> np.ndarray:
        """The frame the simulated camera would deliver: plain figures on the floor, furthest first."""
        frame = self._floor.copy()
        for i in np.argsort(self.positions[:, 1])[::-1]:
            x1, y1, x2, y2 = (int(v) for v in boxes[i, :4])
            head_r = max(2, int(0.075 * (y2 - y1)))
            inset = int(0.12 * (x2 - x1))
            look = int(self._look[i])
            cv2.rectangle(frame, (x1 + inset, y1 + 2 * head_r), (x2 - inset, y2), CLOTHES[look % len(CLOTHES)], -1)
            cv2.rectangle(frame, (x1 + inset, y1 + 2 * head_r), (x2 - inset, y2), FLOOR, 1)
            cv2.circle(frame, ((x1 + x2) // 2, y1 + head_r), head_r, SKIN[(look >> 4) % len(SKIN)], -1)
        return frame


class DrillCapture:
    """Stands in for both the camera and the detector on a drill source: `read` hands the pipeline a new
    frame of the scripted crowd, and `boxes` the people in it. Same calls as Capture and ReplayCache."""

    is_video = False

    def __init__(self, source: Source, frame_w: int = 960, fps: float = 15.0):
        if source.cam_height_m is None or source.tilt_deg is None:
            raise RuntimeError(f"{source.label} needs a calibration (camera height and tilt) in sources.yaml")
        self.source, self.fps = source, fps
        self.frame_w, self.frame_h = frame_w, frame_w * 9 // 16
        calibration = calibration_from_params(self.frame_w, self.frame_h, source.hfov_deg,
                                              source.cam_height_m, source.tilt_deg)
        self._scene = DrillScene(source, calibration)
        self._started = time.monotonic()
        self._serial = 0
        self._boxes = self._scene.boxes()

    def read(self, after_serial: int, timeout: float = 0.5):
        """(frame, serial, index, loops), like Capture.read. The pipeline's own frame-rate cap sets the pace."""
        elapsed = time.monotonic() - self._started
        self._boxes = self._scene.step(elapsed)
        self._serial += 1
        return self._scene.render(self._boxes), self._serial, self._serial, int(elapsed // CYCLE_S)

    def boxes(self, frame_index: int) -> np.ndarray:
        return self._boxes

    def close(self) -> None:
        pass
