"""Runs the flow tracker over a video source without the server and prints walking speed per zone and
gate counts. A sanity check: people on a concourse should come out at roughly 1.0 to 1.5 m/s.

  python scripts/check_flow.py --source concourse
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.calibration import SceneGeometry, calibration_from_params  # noqa: E402
from backend.config import load_settings  # noqa: E402
from backend.detector import PersonDetector  # noqa: E402
from backend.flow import FlowTracker  # noqa: E402
from backend.zones import ZoneCounter  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--stride", type=int, default=2, help="process every Nth frame (2 is close to the live rate)")
    args = ap.parse_args()

    settings = load_settings()
    source = settings.sources[args.source]
    cap = cv2.VideoCapture(str(source.video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cache = np.load(source.replay_path) if source.replay_path and source.replay_path.exists() else None
    detector = None if cache is not None else PersonDetector(settings.detector)

    counter = flow = None
    i, last_print = -1, -1e9
    while True:
        ok, frame = cap.read()
        if not ok or (i + 1) / fps > args.seconds:
            break
        i += 1
        if i % args.stride:
            continue
        t = i / fps
        if counter is None:
            h, w = frame.shape[:2]
            calib = None
            if source.cam_height_m and source.tilt_deg is not None and source.measure != "size":
                calib = calibration_from_params(w, h, source.hfov_deg, source.cam_height_m, source.tilt_deg)
            counter = ZoneCounter(source.zones, w, h, SceneGeometry(w, h, source.hfov_deg, calib))
            flow = FlowTracker(len(source.zones), source.gates, w, h)
            print(f"{source.id}: measuring in {counter.geometry.mode} mode")
        if cache is not None:
            off = cache["offsets"]
            boxes = cache["boxes"][off[i]:off[i + 1]] if i < len(off) - 1 else np.zeros((0, 5), np.float32)
        else:
            boxes = detector.detect(frame)
        zone_idx, _counts, peaks, _rho, positions = counter.measure(boxes)
        ground = positions if counter.geometry.mode == "ground" else None
        flows, gates = flow.update(boxes, zone_idx, ground, peaks, t)
        if t - last_print >= 5.0:
            last_print = t
            cells = []
            for zone, f in zip(source.zones, flows):
                if f is None:
                    cells.append(f"{zone.name}: -")
                else:
                    heading = "standing" if f["heading_deg"] is None else f"{f['heading_deg']:>4} deg"
                    cells.append(f"{zone.name}: {f['speed_mps']:.2f} m/s {heading} align {f['alignment']:.2f} ({f['tracked']})")
            gate_text = "  ".join(f"[{g['id']} in {g['total_in']} out {g['total_out']} | {g['in_per_min']}/min in]" for g in gates)
            print(f"t={t:5.1f}s  " + " | ".join(cells) + ("  " + gate_text if gate_text else ""), flush=True)


if __name__ == "__main__":
    main()
