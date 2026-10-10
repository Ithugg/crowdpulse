"""Replays a CSV written by m1_count.py through the level, forecast and alert logic, so timing constants
can be tuned in a second instead of watching the clip in real time.

  python scripts/m1_count.py --source concourse --no-window --stride 2
  python scripts/simulate_alerts.py concourse
"""
from __future__ import annotations

import csv
import sys
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
    zones = source.zones
    tracker, alerts = ZoneTracker(zones, settings.thresholds), AlertManager(settings.thresholds)
    peak = {z.id: 0.0 for z in zones}
    with (REPO_ROOT / "runs" / f"{source.id}.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            t = float(row["t"])
            states = tracker.update([int(row[f"{z.id}_count"]) for z in zones],
                                    [float(row[f"{z.id}_density"]) for z in zones], t)
            for s in states:
                peak[s.zone.id] = max(peak[s.zone.id], s.density)
            for a in alerts.update(states, t):
                print(f"  t={t:6.1f}s  {a['level']:<8} {a['kind']:<12} {a['message']}")
    print("  highest smoothed density: " + ", ".join(f"{z.name} {peak[z.id]:.2f}" for z in zones))


if __name__ == "__main__":
    main()
