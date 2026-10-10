"""Check the automatic ground calibration for a source: camera height/tilt, real zone areas, and a
picture of a metre grid drawn on the floor (runs/<source>_grid.jpg). If the grid squares look like
squares lying on the floor, the calibration is right.

  python scripts/calibrate.py --source concourse
  python scripts/calibrate.py --source concourse --hfov 45 60 75     # how much does the lens assumption matter?
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.calibration import DEFAULT_HFOV_DEG, fit_calibration, local_density  # noqa: E402
from backend.capture import open_capture  # noqa: E402
from backend.config import REPO_ROOT, load_settings, resolve_source  # noqa: E402
from backend.detector import PersonDetector  # noqa: E402
from backend.zones import ZoneCounter, anchor_points  # noqa: E402


def collect(source, settings, seconds: float, stride: int):
    """Returns (list of per-frame box arrays, a sample frame)."""
    cap = open_capture(source)
    if not cap.isOpened():
        sys.exit(f"Could not open {source.path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cache = np.load(source.replay_path) if source.replay_path and source.replay_path.exists() else None
    detector = None if cache is not None else PersonDetector(settings.detector)
    frames, sample, i = [], None, -1
    while True:
        ok, frame = cap.read()
        if not ok or (i + 1) / fps > seconds:
            break
        i += 1
        if i % stride:
            continue
        sample = frame
        if cache is not None:
            off = cache["offsets"]
            frames.append(cache["boxes"][off[i]:off[i + 1]] if i < len(off) - 1 else np.zeros((0, 5), np.float32))
        else:
            frames.append(detector.detect(frame))
    cap.release()
    return frames, sample


def draw_grid(frame, calib, step_m: float = 2.0):
    """Draws ground lines every step_m metres by sampling the floor and marking where the grid cell changes."""
    h, w = frame.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w]
    ground = calib.to_ground(np.stack([xs.ravel(), ys.ravel()], axis=1)).reshape(h, w, 2)
    valid = np.isfinite(ground[..., 1]) & (ground[..., 1] < 40)
    cells = np.floor(np.nan_to_num(ground) / step_m)
    edge = np.zeros((h, w), bool)
    edge[:, 1:] |= cells[:, 1:, 0] != cells[:, :-1, 0]
    edge[1:, :] |= cells[1:, :, 1] != cells[:-1, :, 1]
    out = frame.copy()
    out[edge & valid] = (60, 220, 255)
    hy = int(calib.horizon_y)
    if 0 <= hy < h:
        cv2.line(out, (0, hy), (w, hy), (255, 120, 60), 2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--hfov", type=float, nargs="+", default=[DEFAULT_HFOV_DEG], help="horizontal field of view to assume")
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--stride", type=int, default=5)
    args = ap.parse_args()

    settings = load_settings()
    source = resolve_source(settings, args.source)
    frames, sample = collect(source, settings, args.seconds, args.stride)
    h, w = sample.shape[:2]
    boxes = np.concatenate(frames)
    print(f"{source.id}: {len(frames)} frames, {len(boxes)} boxes, frame {w}x{h}")

    counter = ZoneCounter(source.zones, w, h)
    for hfov in args.hfov:
        calib = fit_calibration(boxes, w, h, hfov)
        if calib is None:
            print(f"  hfov {hfov:.0f}: not enough whole-body detections to calibrate")
            continue
        print(f"  hfov {hfov:.0f} deg: camera {calib.cam_height_m:.1f} m high, looking {math.degrees(calib.tilt_rad):.0f} deg down, "
              f"horizon y={calib.horizon_y:.0f}px, fit error {calib.fit_error * 100:.0f}% over {calib.samples} people")
        print(f"    sources.yaml ->  calibration: {{cam_height_m: {calib.cam_height_m:.1f}, tilt_deg: {math.degrees(calib.tilt_rad):.1f}}}")
        visible = calib.mask_area_m2(np.ones((h, w), bool))
        peaks = []
        for fb in frames:
            rho = local_density(calib.to_ground(anchor_points(fb)))
            if len(rho):
                peaks.append((np.percentile(rho, 90), rho.max(), len(fb)))
        peaks = np.array(peaks)
        print(f"    visible floor {visible:.0f} m2 | people/frame {peaks[:, 2].mean():.0f} | average density "
              f"{peaks[:, 2].mean() / visible:.2f} p/m2 | local density p90 {peaks[:, 0].mean():.2f}, max {peaks[:, 1].mean():.2f} p/m2")
        for i, zone in enumerate(source.zones):
            area = calib.mask_area_m2(counter._mask == i + 1)
            mean_count = np.mean([np.count_nonzero(counter.assign(fb) == i) for fb in frames])
            print(f"    {zone.name:<20} {area:7.1f} m2   {mean_count:5.1f} people   {mean_count / max(area, 1e-6):.2f} p/m2 average")
        out = REPO_ROOT / "runs" / f"{source.id}_grid_{hfov:.0f}.jpg"
        out.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(out), draw_grid(sample, calib))
        print(f"    grid picture: {out}")


if __name__ == "__main__":
    main()
