"""Background frame reader. Always exposes the newest frame so slow inference never causes lag."""
from __future__ import annotations

import sys
import threading
import time

import cv2
import numpy as np

from .config import Source


def open_capture(source: Source) -> cv2.VideoCapture:
    if source.kind == "webcam":
        # DirectShow opens far faster than the default backend on Windows.
        cap = cv2.VideoCapture(int(source.path), cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        return cap
    return cv2.VideoCapture(str(source.video_path))


class Capture:
    """Video files play at their native speed and loop; webcams deliver frames as they arrive."""

    def __init__(self, source: Source):
        self.source = source
        self.is_video = source.kind == "video"
        self._cap = open_capture(source)
        if not self._cap.isOpened():
            self._cap.release()
            raise RuntimeError(f"Could not open {source.label} ({source.path})")
        # A camera can "open" yet deliver nothing (no device, or in use by another app): prove it with one frame.
        ok, first = self._cap.read()
        if not ok:
            self._cap.release()
            raise RuntimeError(f"{source.label} opened but returned no frames ({source.path})")
        self.fps = (self._cap.get(cv2.CAP_PROP_FPS) or 25.0) if self.is_video else 30.0
        self.frame_h, self.frame_w = first.shape[:2]
        self._cond = threading.Condition()
        self._frame: np.ndarray | None = first
        self._serial = 1  # increments with every new frame
        self._index = 0  # frame index inside the video file
        self._loops = 0
        self._stop = False
        self._thread = threading.Thread(target=self._run, name=f"capture-{source.id}", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        period = 1.0 / self.fps
        next_t = time.perf_counter()
        failures = 0
        index = 0
        while not self._stop:
            ok, frame = self._cap.read()
            if not ok:
                failures += 1
                if self.is_video and failures < 3:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    index = -1
                    with self._cond:
                        self._loops += 1
                else:
                    time.sleep(0.05)
                continue
            failures = 0
            index += 1
            with self._cond:
                self._frame, self._index = frame, index
                self._serial += 1
                self._cond.notify_all()
            if self.is_video:
                next_t += period
                delay = next_t - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                elif delay < -0.5:  # fell behind (e.g. laptop woke from sleep): resync instead of racing
                    next_t = time.perf_counter()

    def read(self, after_serial: int, timeout: float = 0.5):
        """Blocks until a frame newer than after_serial exists. Returns (frame, serial, index, loops) or None."""
        with self._cond:
            if not self._cond.wait_for(lambda: self._serial > after_serial, timeout):
                return None
            return self._frame, self._serial, self._index, self._loops

    def close(self) -> None:
        self._stop = True
        self._thread.join(timeout=2.0)
        self._cap.release()
