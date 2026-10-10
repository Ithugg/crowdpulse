"""YOLOv8 person detector. Pretrained COCO weights, no training; runs on CPU unless CUDA is present."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .config import REPO_ROOT, DetectorSettings

PERSON_CLASS = 0


class PersonDetector:
    def __init__(self, settings: DetectorSettings | None = None, device: str | None = None):
        import torch
        from ultralytics import YOLO

        self.settings = settings or DetectorSettings()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(str(self._weights_path(self.settings.weights)))

    @staticmethod
    def _weights_path(weights: str) -> Path:
        # Bare names ("yolov8n.pt") live in models/ and are auto-downloaded there on first use.
        p = Path(weights)
        if p.is_absolute() or len(p.parts) > 1:
            return p if p.is_absolute() else REPO_ROOT / p
        (REPO_ROOT / "models").mkdir(exist_ok=True)
        return REPO_ROOT / "models" / weights

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """Returns an (N, 5) float32 array of [x1, y1, x2, y2, confidence] in frame pixels."""
        result = self.model.predict(
            frame, classes=[PERSON_CLASS], conf=self.settings.conf, imgsz=self.settings.imgsz,
            device=self.device, max_det=1000, verbose=False,
        )[0]
        if result.boxes is None or len(result.boxes) == 0:
            return np.zeros((0, 5), dtype=np.float32)
        boxes = result.boxes
        return np.concatenate(
            [boxes.xyxy.cpu().numpy(), boxes.conf.cpu().numpy()[:, None]], axis=1
        ).astype(np.float32)

    def detect_tiled(self, frame: np.ndarray, cols: int, rows: int, overlap: float = 0.25) -> np.ndarray:
        """Sliced inference for packed crowds: run the detector on overlapping tiles (so small, half-hidden
        people are seen at a usable size) plus once on the whole frame, then merge duplicates.
        Far too slow for live CPU use; scripts/precompute.py uses it to build replay caches."""
        import torch
        from torchvision.ops import nms

        h, w = frame.shape[:2]
        tile_w = int(w / (cols - (cols - 1) * overlap))
        tile_h = int(h / (rows - (rows - 1) * overlap))
        found = [self.detect(frame)]
        for r in range(rows):
            for c in range(cols):
                x0 = min(int(c * tile_w * (1 - overlap)), w - tile_w)
                y0 = min(int(r * tile_h * (1 - overlap)), h - tile_h)
                boxes = self.detect(frame[y0:y0 + tile_h, x0:x0 + tile_w])
                boxes[:, [0, 2]] += x0
                boxes[:, [1, 3]] += y0
                found.append(boxes)
        merged = torch.from_numpy(np.concatenate(found))
        if len(merged) == 0:
            return np.zeros((0, 5), dtype=np.float32)
        return merged[nms(merged[:, :4], merged[:, 4], 0.5)].numpy()
