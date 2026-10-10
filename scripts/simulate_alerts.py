"""Replays a counts CSV written by m1_count.py through the tracker + alert logic, to tune zone areas
and thresholds without watching the clip in real time.

  python scripts/simulate_alerts.py concourse                    # areas from config/sources.yaml
  python scripts/simulate_alerts.py concourse main_floor=3.6     # try a different area for one zone
"""
from __future__ import annotations

import csv
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.alerts import AlertManager  # noqa: E402
from backend.config import REPO_ROOT, load_settings  # noqa: E402
from backend.predictor import ZoneTracker  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    settings = load_settings()
    source = settings.sources[sys.argv[1]]
    overrides = dict(arg.split("=") for arg in sys.argv[2:])
    zones = tuple(replace(z, area_m2=float(overrides.get(z.id, z.area_m2))) for z in source.zones)
    tracker, alerts = ZoneTracker(zones, settings.thresholds), AlertManager()
    peak = {z.id: 0.0 for z in zones}
    with (REPO_ROOT / "runs" / f"{source.id}.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            t = float(row["t"])
            states = tracker.update([int(row[f"{z.id}_count"]) for z in zones], t)
            for s in states:
                peak[s.zone.id] = max(peak[s.zone.id], s.density)
            for a in alerts.update(states, t):
                print(f"  t={t:6.1f}s  {a['level']:<6} {a['kind']:<12} {a['message']}")
    print("  peak density: " + ", ".join(f"{z.name} {peak[z.id]:.1f}" for z in zones))


if __name__ == "__main__":
    main()
