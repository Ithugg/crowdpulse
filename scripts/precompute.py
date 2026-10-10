"""Precompute detections for a video source so the server can replay them instead of running YOLO live.

Use this for clips that are too dense or too slow for live CPU inference on the demo laptop. A bigger
model / input size can be used here because it does not have to run in real time.

  python scripts/precompute.py --source main_field --weights yolov8s.pt --imgsz 1280

Writes media/cache/<source>.npz. Enable it by adding `replay: media/cache/<source>.npz` to that source
in config/sources.yaml. The dashboard then shows a REPLAY badge instead of LIVE for that source.
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import REPO_ROOT, load_settings  # noqa: E402
from backend.detector import PersonDetector  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="video source id from config/sources.yaml")
    ap.add_argument("--weights", help="e.g. yolov8s.pt (default: the configured detector)")
    ap.add_argument("--imgsz", type=int, help="e.g. 1280 (default: the configured detector)")
    ap.add_argument("--conf", type=float)
    args = ap.parse_args()

    settings = load_settings()
    source = settings.sources.get(args.source)
    if source is None or source.kind != "video":
        sys.exit(f"'{args.source}' is not a video source in config/sources.yaml")
    overrides = {k: v for k, v in (("weights", args.weights), ("imgsz", args.imgsz), ("conf", args.conf)) if v}
    detector = PersonDetector(replace(settings.detector, **overrides))

    cap = cv2.VideoCapture(str(source.video_path))
    if not cap.isOpened():
        sys.exit(f"Could not open {source.video_path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    per_frame, offsets, started = [], [0], time.perf_counter()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        boxes = detector.detect(frame)
        per_frame.append(boxes)
        offsets.append(offsets[-1] + len(boxes))
        if len(per_frame) % 100 == 0:
            rate = len(per_frame) / (time.perf_counter() - started)
            print(f"{len(per_frame)}/{total} frames  {rate:.1f} fps  people in last frame: {len(boxes)}", flush=True)
    cap.release()

    out = REPO_ROOT / "media" / "cache" / f"{source.id}.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out, offsets=np.array(offsets, dtype=np.int64),
        boxes=np.concatenate(per_frame) if per_frame else np.zeros((0, 5), dtype=np.float32),
    )
    mean = offsets[-1] / max(len(per_frame), 1)
    print(f"Wrote {out} ({len(per_frame)} frames, {mean:.0f} people per frame on average)")
    print(f"Enable it in config/sources.yaml:  replay: media/cache/{source.id}.npz")


if __name__ == "__main__":
    main()
