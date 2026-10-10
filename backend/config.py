"""Loads config/sources.yaml into typed settings shared by the scripts and the server."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "sources.yaml"

Point = tuple[float, float]


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    area_m2: float  # estimated floor area covered by the polygon (not calibrated)
    polygon: tuple[Point, ...]  # normalized 0-1 image coordinates


@dataclass(frozen=True)
class Source:
    id: str
    label: str
    kind: str  # "webcam" | "video"
    path: int | str  # camera index, or video path
    zones: tuple[Zone, ...]
    replay: str | None = None  # optional detection cache written by scripts/precompute.py

    @property
    def video_path(self) -> Path:
        p = Path(str(self.path))
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def replay_path(self) -> Path | None:
        if not self.replay:
            return None
        p = Path(self.replay)
        return p if p.is_absolute() else REPO_ROOT / p


@dataclass(frozen=True)
class Thresholds:
    warn: float = 2.5  # people/m2 where a zone turns yellow
    critical: float = 4.0  # people/m2 where a zone turns red


@dataclass(frozen=True)
class DetectorSettings:
    weights: str = "yolov8n.pt"
    imgsz: int = 640
    conf: float = 0.25


@dataclass(frozen=True)
class Settings:
    thresholds: Thresholds
    detector: DetectorSettings
    sources: dict[str, Source]
    default_source: str
    max_fps: float = 15.0
    stream_width: int = 960
    jpeg_quality: int = 70


def grid_zones(rows: int = 2, cols: int = 2, area_m2: float = 10.0) -> tuple[Zone, ...]:
    """Fallback zones for a source that has none configured yet."""
    zones = []
    for r in range(rows):
        for c in range(cols):
            x0, y0, x1, y1 = c / cols, r / rows, (c + 1) / cols, (r + 1) / rows
            letter = chr(ord("A") + r * cols + c)
            zones.append(Zone(f"zone_{letter.lower()}", f"Zone {letter}", area_m2,
                              ((x0, y0), (x1, y0), (x1, y1), (x0, y1))))
    return tuple(zones)


def _parse_zones(raw: list[dict] | None) -> tuple[Zone, ...]:
    if not raw:
        return grid_zones()
    return tuple(
        Zone(z["id"], z["name"], float(z["area_m2"]), tuple((float(x), float(y)) for x, y in z["polygon"]))
        for z in raw
    )


def load_settings(path: Path = CONFIG_PATH) -> Settings:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = {
        sid: Source(sid, s.get("label", sid), s.get("kind", "video"), s["path"],
                    _parse_zones(s.get("zones")), s.get("replay"))
        for sid, s in (raw.get("sources") or {}).items()
    }
    stream = raw.get("stream") or {}
    return Settings(
        thresholds=Thresholds(**(raw.get("thresholds") or {})),
        detector=DetectorSettings(**(raw.get("detector") or {})),
        sources=sources,
        default_source=raw.get("default_source") or next(iter(sources), ""),
        max_fps=float(stream.get("max_fps", 15.0)),
        stream_width=int(stream.get("width", 960)),
        jpeg_quality=int(stream.get("jpeg_quality", 70)),
    )


def resolve_source(settings: Settings, arg: str) -> Source:
    """A configured source id, a camera index ("0"), or a path to a video file."""
    if arg in settings.sources:
        return settings.sources[arg]
    if arg.isdigit():
        return Source(f"camera_{arg}", f"Camera {arg}", "webcam", int(arg), grid_zones(1, 3, 2.0))
    return Source(Path(arg).stem, Path(arg).stem, "video", arg, grid_zones())
