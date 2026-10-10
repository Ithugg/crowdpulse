"""The processing loop: newest frame -> people -> zones -> density/prediction -> alerts -> annotated JPEG."""
from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np

from .alerts import AlertManager
from .capture import Capture
from .config import Settings, Source
from .detector import PersonDetector
from .predictor import ZoneTracker
from .render import HeatmapRenderer, draw_boxes, encode_jpeg, resize_to_width
from .schemas import config_message, state_message
from .zones import ZoneCounter

log = logging.getLogger("crowdpulse.pipeline")


class ReplayCache:
    """Detections precomputed by scripts/precompute.py, replayed by frame index instead of running YOLO."""

    def __init__(self, path: Path):
        data = np.load(path)
        self._offsets, self._boxes = data["offsets"], data["boxes"]

    def boxes(self, frame_index: int) -> np.ndarray:
        if not 0 <= frame_index < len(self._offsets) - 1:
            return np.zeros((0, 5), dtype=np.float32)
        return self._boxes[self._offsets[frame_index]:self._offsets[frame_index + 1]]


class Pipeline(threading.Thread):
    """Runs in its own thread and reports through callbacks (called on this thread):
    on_config(config_msg), on_frame(state_msg, jpeg, alerts), on_error(text)."""

    def __init__(self, settings: Settings, on_config: Callable, on_frame: Callable, on_error: Callable):
        super().__init__(name="pipeline", daemon=True)
        self.settings = settings
        self._on_config, self._on_frame, self._on_error = on_config, on_frame, on_error
        self._commands: queue.Queue = queue.Queue()
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        self._overlay = {"boxes": True, "heatmap": True}
        self._latest: dict | None = None  # last state message + jpeg, for plan generation

        self._detector: PersonDetector | None = None
        self._capture: Capture | None = None
        self._source: Source | None = None
        self._replay: ReplayCache | None = None
        self._counter: ZoneCounter | None = None
        self._tracker: ZoneTracker | None = None
        self._alerts = AlertManager()
        self._heatmap = HeatmapRenderer()

    # ---- thread-safe controls -------------------------------------------------
    def set_source(self, source_id: str) -> None:
        self._commands.put(("source", source_id))

    def restart(self) -> None:
        self._commands.put(("restart", None))

    def set_overlay(self, boxes: bool | None = None, heatmap: bool | None = None) -> None:
        with self._lock:
            if boxes is not None:
                self._overlay["boxes"] = bool(boxes)
            if heatmap is not None:
                self._overlay["heatmap"] = bool(heatmap)

    def stop(self) -> None:
        self._stop_flag.set()

    def latest(self) -> dict | None:
        """{'state': last state message, 'jpeg': bytes, 'source': Source} or None before the first frame."""
        with self._lock:
            return self._latest

    # ---- loop -----------------------------------------------------------------
    def run(self) -> None:
        try:
            self._detector = PersonDetector(self.settings.detector)
            log.info("Detector ready on %s", self._detector.device)
        except Exception as exc:
            log.exception("Detector failed to load")
            self._on_error(f"Detector failed to load: {exc}")
            return
        self._open_first_available()

        seq, serial, loops, fps = 0, 0, 0, 0.0
        min_period = 1.0 / self.settings.max_fps
        while not self._stop_flag.is_set():
            tick = time.perf_counter()
            if self._handle_commands():
                serial, loops = 0, 0
            if self._capture is None:
                time.sleep(0.1)
                continue
            item = self._capture.read(serial)
            if item is None:
                continue
            frame, serial, index, frame_loops = item
            if frame_loops != loops:  # clip restarted from the top
                loops = frame_loops
                self._reset_tracking()

            h, w = frame.shape[:2]
            if self._counter is None or (self._counter.frame_w, self._counter.frame_h) != (w, h):
                self._counter = ZoneCounter(self._source.zones, w, h)

            t0 = time.perf_counter()
            boxes = self._replay.boxes(index) if self._replay else self._detector.detect(frame)
            inference_ms = (time.perf_counter() - t0) * 1000
            zone_idx = self._counter.assign(boxes)
            now = time.monotonic()
            states = self._tracker.update(self._counter.counts(zone_idx), now)
            alerts = self._alerts.update(states, now)

            with self._lock:
                overlay = dict(self._overlay)
            out, scale = resize_to_width(frame, self.settings.stream_width)
            if scale == 1.0:
                out = frame.copy()
            scaled = boxes.copy()
            scaled[:, :4] *= scale
            if overlay["heatmap"]:
                self._heatmap.draw(out, scaled)
            if overlay["boxes"]:
                draw_boxes(out, scaled, zone_idx)
            jpeg = encode_jpeg(out, self.settings.jpeg_quality)

            seq += 1
            elapsed = time.perf_counter() - tick
            fps = 1.0 / max(elapsed, min_period) if fps == 0 else 0.9 * fps + 0.1 / max(elapsed, min_period)
            state = state_message(
                seq=seq, source_id=self._source.id, fps=fps, inference_ms=inference_ms,
                mode="replay" if self._replay else "live", frame_w=out.shape[1], frame_h=out.shape[0],
                total_count=len(boxes), states=states, overlay=overlay,
            )
            with self._lock:
                self._latest = {"state": state, "jpeg": jpeg, "source": self._source}
            self._on_frame(state, jpeg, alerts)

            spare = min_period - (time.perf_counter() - tick)
            if spare > 0:
                time.sleep(spare)

        if self._capture:
            self._capture.close()

    # ---- helpers --------------------------------------------------------------
    def _handle_commands(self) -> bool:
        changed = False
        while True:
            try:
                kind, arg = self._commands.get_nowait()
            except queue.Empty:
                return changed
            if kind == "source":
                changed |= self._open(arg)
            elif kind == "restart" and self._source is not None:
                changed |= self._open(self._source.id)

    def _open_first_available(self) -> None:
        order = [self.settings.default_source] + [s for s in self.settings.sources if s != self.settings.default_source]
        for source_id in order:
            if self._open(source_id, report_errors=False):
                return
        self._on_error("No camera or video source could be opened. Check config/sources.yaml and the media/ folder.")

    def _open(self, source_id: str, report_errors: bool = True) -> bool:
        source = self.settings.sources.get(source_id)
        if source is None:
            self._on_error(f"Unknown source '{source_id}'")
            return False
        try:
            capture = Capture(source)
        except RuntimeError as exc:
            log.warning("%s", exc)
            if report_errors:
                self._on_error(f"{source.label} is not available")
            return False
        if self._capture:
            self._capture.close()
        self._capture, self._source = capture, source
        self._replay = None
        if source.replay_path and source.replay_path.exists():
            self._replay = ReplayCache(source.replay_path)
        self._counter = None
        self._reset_tracking()
        with self._lock:
            self._latest = None
        log.info("Source -> %s (%s)", source.id, "replay" if self._replay else "live")
        self._on_config(config_message(self.settings, source))
        return True

    def _reset_tracking(self) -> None:
        self._tracker = ZoneTracker(self._source.zones, self.settings.thresholds)
        self._alerts.reset()
        self._heatmap.reset()
