"""Milestone 1: count people per zone on a webcam or video file.

Shows an OpenCV window with boxes + zones, prints a table every second and logs a CSV to runs/.

  python scripts/m1_count.py --source 0                     # webcam
  python scripts/m1_count.py --source media/MOT20-02.mp4    # any video file
  python scripts/m1_count.py --source main_stage            # a source id from config/sources.yaml
  python scripts/m1_count.py --source 0 --bench 100         # inference speed only
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import replace
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.calibration import SceneGeometry, calibration_from_params  # noqa: E402
from backend.capture import open_capture  # noqa: E402
from backend.config import REPO_ROOT, load_settings, resolve_source  # noqa: E402
from backend.detector import PersonDetector  # noqa: E402
from backend.predictor import ZoneTracker  # noqa: E402
from backend.render import HeatmapRenderer, draw_boxes, draw_zones  # noqa: E402
from backend.zones import ZoneCounter  # noqa: E402


def bench(detector: PersonDetector, cap: cv2.VideoCapture, n: int) -> None:
    ok, frame = cap.read()
    if not ok:
        sys.exit("Could not read a frame to benchmark with.")
    detector.detect(frame)  # warm-up
    times = []
    for _ in range(n):
        ok, nxt = cap.read()
        frame = nxt if ok else frame
        t0 = time.perf_counter()
        boxes = detector.detect(frame)
        times.append(time.perf_counter() - t0)
    times.sort()
    median = times[len(times) // 2]
    print(f"device={detector.device} weights={detector.settings.weights} imgsz={detector.settings.imgsz} "
          f"frame={frame.shape[1]}x{frame.shape[0]} people={len(boxes)}")
    print(f"inference: median {median * 1000:.1f} ms  ->  {1 / median:.1f} FPS  "
          f"(p90 {times[int(len(times) * 0.9)] * 1000:.1f} ms)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="0", help="camera index, video path, or source id from config/sources.yaml")
    ap.add_argument("--weights", help="override detector weights, e.g. yolov8s.pt")
    ap.add_argument("--imgsz", type=int, help="override inference size, e.g. 960")
    ap.add_argument("--conf", type=float, help="override confidence threshold")
    ap.add_argument("--stride", type=int, default=1, help="process every Nth frame")
    ap.add_argument("--max-seconds", type=float, help="stop after this many seconds of video")
    ap.add_argument("--no-window", action="store_true", help="run headless (console + CSV only)")
    ap.add_argument("--heatmap", action="store_true", help="draw the density heatmap too")
    ap.add_argument("--snapshot-every", type=float, help="save an annotated JPG every N seconds to runs/<source>/")
    ap.add_argument("--bench", type=int, metavar="N", help="time N inferences and exit")
    args = ap.parse_args()

    settings = load_settings()
    source = resolve_source(settings, args.source)
    overrides = {k: v for k, v in (("weights", args.weights), ("imgsz", args.imgsz), ("conf", args.conf)) if v}
    detector = PersonDetector(replace(settings.detector, **overrides))

    cap = open_capture(source)
    if not cap.isOpened():
        sys.exit(f"Could not open source '{args.source}' ({source.path}).")
    if args.bench:
        bench(detector, cap, args.bench)
        return

    is_video = source.kind == "video"
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    runs = REPO_ROOT / "runs"
    snap_dir = runs / source.id
    runs.mkdir(exist_ok=True)
    if args.snapshot_every:
        snap_dir.mkdir(exist_ok=True)

    counter = tracker = None
    heatmap = HeatmapRenderer()
    csv_path = runs / f"{source.id}.csv"
    frame_i, processed, last_print, last_snap, started = -1, 0, -1e9, -1e9, time.perf_counter()

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_i += 1
            if frame_i % args.stride:
                continue
            t = frame_i / video_fps if is_video else time.perf_counter() - started
            if args.max_seconds and t > args.max_seconds:
                break

            if counter is None:
                h, w = frame.shape[:2]
                # Stored calibration if the source has one, otherwise distance from body size.
                calib = None
                if source.cam_height_m and source.tilt_deg is not None:
                    calib = calibration_from_params(w, h, source.hfov_deg, source.cam_height_m, source.tilt_deg)
                counter = ZoneCounter(source.zones, w, h, SceneGeometry(w, h, source.hfov_deg, calib))
                tracker = ZoneTracker(source.zones, settings.thresholds, counter.areas_m2)
                print(f"distance measurement: {counter.geometry.mode}", flush=True)
                writer.writerow(["t", "total"] + [f"{z.id}_{k}" for z in source.zones for k in ("count", "density")])

            boxes = detector.detect(frame)
            zone_idx, counts, peaks, densities, _positions = counter.measure(boxes)
            states = tracker.update(counts, peaks, t)
            processed += 1
            # density column = raw peak local density for this frame (scripts/simulate_alerts.py replays it)
            writer.writerow([f"{t:.2f}", len(boxes)] + [v for c, p in zip(counts, peaks) for v in (c, f"{p:.3f}")])

            if t - last_print >= 1.0:
                last_print = t
                fps = processed / (time.perf_counter() - started)
                cells = []
                for s in states:
                    eta = f" -> {s.eta_level} in {s.eta_s:.0f}s" if s.eta_s else ""
                    cells.append(f"{s.zone.name} {s.count:>3} ({s.density:.2f} p/m2 {s.level}{eta})")
                print(f"t={t:6.1f}s fps={fps:5.1f} total={len(boxes):>3} | " + " | ".join(cells), flush=True)

            want_snap = args.snapshot_every and t - last_snap >= args.snapshot_every
            if want_snap or not args.no_window:
                if args.heatmap:
                    heatmap.draw(frame, boxes, densities, settings.thresholds.critical)
                draw_boxes(frame, boxes, zone_idx)
                draw_zones(frame, counter.polygons_px,
                           [f"{s.zone.name}: {s.count} | {s.density:.1f} p/m2" for s in states],
                           [s.level for s in states])
            if want_snap:
                last_snap = t
                cv2.imwrite(str(snap_dir / f"t{int(t):04d}.jpg"), frame)
            if not args.no_window:
                cv2.imshow("CrowdPulse - M1 (q to quit)", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
