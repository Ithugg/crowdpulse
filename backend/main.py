"""FastAPI server: one WebSocket (/ws) carrying JSON state/events + binary JPEG frames, plus the built dashboard.

Run with:  python -m backend.main      (or scripts\\start.ps1)
"""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
import time
from collections import deque
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from .config import REPO_ROOT, load_settings
from .gemini_plan import PlanGenerator
from .pipeline import Pipeline

load_dotenv(REPO_ROOT / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("crowdpulse.server")

PLAN_COOLDOWN_S = 60  # per zone, for automatically triggered plans
PLAN_LEVELS = ("caution", "danger", "critical")
ALERT_STATUSES = ("acknowledged", "dispatched")
DIST_DIR = REPO_ROOT / "frontend" / "dist"


def dumps(message: dict) -> str:
    return json.dumps(message, separators=(",", ":"))


def clock(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


class Client:
    """Per-connection outbox: events are queued in order, video frames are latest-only."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.events: deque[str] = deque()
        self.frame: tuple[str, bytes] | None = None
        self.wake = asyncio.Event()


class Session:
    """What has happened on the current camera since it was selected. Feeds the incident report."""

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.started = time.time()
        self.alerts: dict[str, dict] = {}
        self.plans: list[dict] = []
        self.peaks: dict[str, dict] = {}  # zone id -> highest reading seen
        self.frames = 0

    def observe(self, state: dict) -> None:
        self.frames += 1
        if self.frames < 45:  # the first seconds on a camera are unsmoothed; do not record them as a peak
            return
        for zone in state["zones"]:
            best = self.peaks.get(zone["id"])
            if best is None or zone["density"] > best["density"]:
                self.peaks[zone["id"]] = {"density": zone["density"], "count": zone["count"], "ts": state["ts"]}


class Hub:
    def __init__(self):
        self.clients: set[Client] = set()
        self.config: dict | None = None
        self.backlog: deque[dict] = deque(maxlen=40)  # recent alerts + plans for late joiners
        self.session = Session()

    def publish_config(self, message: dict) -> None:
        # A calibration update keeps the same camera's alerts; a different camera starts a new session.
        if self.config is None or message["active_source"] != self.config["active_source"]:
            self.backlog.clear()
            self.session.reset()
        self.config = message
        self._send(message)

    def publish_event(self, message: dict, remember: bool = True) -> None:
        if remember:
            self.backlog.append(message)
        self._send(message)

    def publish_frame(self, state: dict, jpeg: bytes) -> None:
        text = dumps(state)
        for client in self.clients:
            client.frame = (text, jpeg)  # overwrites any frame the client has not sent yet
            client.wake.set()

    def _send(self, message: dict) -> None:
        text = dumps(message)
        for client in self.clients:
            client.events.append(text)
            client.wake.set()


hub = Hub()
plans = PlanGenerator()
ids = itertools.count(1)
last_plan_at: dict[str, float] = {}
background_tasks: set[asyncio.Task] = set()
pipeline: Pipeline | None = None


def spawn(coro) -> None:
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def density_scale() -> dict:
    th = pipeline.settings.thresholds
    return {"busy": th.busy, "caution_safe_limit": th.caution, "danger": th.danger, "critical": th.critical}


def measurement_note(latest: dict) -> str:
    if latest["geometry"].mode == "ground":
        return "local peak density on the ground plane, camera calibrated from the people in view"
    return "local peak density, distance estimated from body size"


def plan_context(latest: dict, zone_id: str) -> dict | None:
    """The situation summary sent to Gemini for one zone."""
    state, source = latest["state"], latest["source"]
    zones = {z.id: z for z in source.zones}
    live = {z["id"]: z for z in state["zones"]}
    if zone_id not in zones or zone_id not in live:
        return None

    def describe(zid: str) -> dict:
        s = live[zid]
        return {"name": zones[zid].name, "people_counted": s["count"],
                "density_per_m2": s["density"], "level": s["level"],
                "trend_per_min": s["trend_per_min"],
                "forecast": None if s["eta_s"] is None else {"reaches": s["eta_level"], "in_seconds": s["eta_s"]},
                "seconds_above_safe_limit": s["above_safe_s"]}

    return {
        "camera": source.label,
        "density_scale_per_m2": density_scale(),
        "measurement": measurement_note(latest),
        "zone": describe(zone_id),
        "other_zones": [describe(zid) for zid in zones if zid != zone_id],
        "total_people_in_view": state["total_count"],
    }


async def make_plan(zone_id: str, alert_id: str | None = None, forced: bool = False) -> None:
    latest = pipeline.latest() if pipeline else None
    context = plan_context(latest, zone_id) if latest else None
    if context is None:
        return
    key = f"{latest['source'].id}:{zone_id}"
    now = time.monotonic()
    if not forced and now - last_plan_at.get(key, -1e9) < PLAN_COOLDOWN_S:
        return
    last_plan_at[key] = now

    base = {"type": "plan", "id": f"p{next(ids)}", "alert_id": alert_id, "zone_id": zone_id,
            "zone_name": context["zone"]["name"], "level": context["zone"]["level"], "ts": time.time()}
    hub.publish_event({**base, "status": "generating"}, remember=False)
    result = await plans.generate(context, latest["jpeg"])
    plan = {**base, "status": "ready", **result}
    hub.session.plans.append(plan)
    hub.publish_event(plan)
    log.info("Plan for %s ready (%s, %s ms)", zone_id, result["origin"], result["latency_ms"])


def report_log(latest: dict) -> dict:
    """Everything the incident report is allowed to draw on."""
    session, source = hub.session, latest["source"]
    names = {z.id: z.name for z in source.zones}
    return {
        "camera": source.label,
        "period": {"from": clock(session.started), "to": clock(time.time())},
        "density_scale_per_m2": density_scale(),
        "measurement": measurement_note(latest),
        "zones": [{"name": names.get(zid, zid), "peak_density_per_m2": p["density"],
                   "people_at_peak": p["count"], "peak_time": clock(p["ts"])}
                  for zid, p in session.peaks.items()],
        "alerts": [{"time": clock(a["ts"]), "zone": a["zone_name"], "kind": a["kind"], "level": a["level"],
                    "message": a["message"], "acknowledged_after_s": a.get("ack_s"),
                    "staff_dispatched_after_s": a.get("dispatch_s")}
                   for a in session.alerts.values()],
        "plans": [{"time": clock(p["ts"]), "zone": p["zone_name"], "headline": p["headline"],
                   "written_by": p["origin"]} for p in session.plans],
    }


async def make_report() -> None:
    latest = pipeline.latest() if pipeline else None
    if latest is None:
        return
    data = report_log(latest)
    base = {"type": "report", "id": f"r{next(ids)}", "ts": time.time(), "camera": data["camera"],
            "period": data["period"], "zones": data["zones"]}
    hub.publish_event({**base, "status": "generating"}, remember=False)
    result = await plans.report(data)
    hub.publish_event({**base, "status": "ready", **result}, remember=False)
    log.info("Incident report ready (%s, %s ms)", result["origin"], result["latency_ms"])


def acknowledge(alert_id: str, status: str) -> None:
    """Staff marked an alert as acknowledged or dispatched: record how long the response took."""
    alert = hub.session.alerts.get(alert_id)
    if alert is None or status not in ALERT_STATUSES:
        return
    elapsed = round(time.time() - alert["ts"])
    alert.setdefault("ack_s", elapsed)  # dispatching also counts as acknowledging
    if status == "dispatched":
        alert.setdefault("dispatch_s", elapsed)
    alert["status"] = "dispatched" if "dispatch_s" in alert else "acknowledged"
    hub.publish_event({"type": "alert_update", "id": alert_id, "status": alert["status"],
                       "ack_s": alert["ack_s"], "dispatch_s": alert.get("dispatch_s")}, remember=False)


def on_frame(state: dict, jpeg: bytes, alerts: list[dict]) -> None:
    hub.session.observe(state)
    hub.publish_frame(state, jpeg)
    for alert in alerts:
        hub.session.alerts[alert["id"]] = alert  # the same dict sits in the backlog, so status updates reach late joiners
        hub.publish_event(alert)
        # Staff need instructions as soon as a zone crosses the safe limit (the per-zone cooldown stops repeats).
        if alert["kind"] in ("level_change", "exposure") and alert["level"] in PLAN_LEVELS:
            spawn(make_plan(alert["zone_id"], alert["id"]))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global pipeline
    loop = asyncio.get_running_loop()
    pipeline = Pipeline(
        load_settings(),
        on_config=lambda msg: loop.call_soon_threadsafe(hub.publish_config, msg),
        on_frame=lambda *args: loop.call_soon_threadsafe(on_frame, *args),
        on_error=lambda text: loop.call_soon_threadsafe(
            hub.publish_event, {"type": "error", "ts": time.time(), "message": text}, False),
    )
    pipeline.start()
    log.info("Gemini: %s", "enabled" if plans.enabled else "no GEMINI_API_KEY, using cached plans and reports")
    yield
    pipeline.stop()


app = FastAPI(title="CrowdPulse", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    latest = pipeline.latest() if pipeline else None
    return {
        "ok": True, "gemini": plans.enabled, "clients": len(hub.clients),
        "source": latest["source"].id if latest else None,
        "fps": latest["state"]["fps"] if latest else None,
    }


async def sender(client: Client) -> None:
    while True:
        await client.wake.wait()
        client.wake.clear()
        while client.events:
            await client.ws.send_text(client.events.popleft())
        if client.frame:
            state, jpeg = client.frame
            client.frame = None
            await client.ws.send_text(state)
            await client.ws.send_bytes(jpeg)


def handle_command(message: dict) -> None:
    kind = message.get("type")
    if kind == "set_source":
        pipeline.set_source(str(message.get("source_id", "")))
    elif kind == "set_overlay":
        pipeline.set_overlay(message.get("boxes"), message.get("heatmap"), message.get("privacy"),
                             message.get("grid"))
    elif kind == "restart":
        pipeline.restart()
    elif kind == "request_plan":
        spawn(make_plan(str(message.get("zone_id", "")), forced=True))
    elif kind == "ack_alert":
        acknowledge(str(message.get("alert_id", "")), str(message.get("status", "")))
    elif kind == "request_report":
        spawn(make_report())


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    client = Client(ws)
    if hub.config:
        client.events.append(dumps(hub.config))
    client.events.extend(dumps(message) for message in hub.backlog)
    client.wake.set()
    hub.clients.add(client)
    send_task = asyncio.create_task(sender(client))
    try:
        while True:
            message = await ws.receive_json()
            if isinstance(message, dict):
                handle_command(message)
    except (WebSocketDisconnect, RuntimeError, ValueError):
        pass
    finally:
        hub.clients.discard(client)
        send_task.cancel()


class DashboardFiles(StaticFiles):
    """The built dashboard. index.html must never be cached, or a rebuilt UI keeps showing the old one."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if not path.startswith("assets/"):
            response.headers["Cache-Control"] = "no-store"
        return response


if DIST_DIR.exists():
    app.mount("/", DashboardFiles(directory=DIST_DIR, html=True), name="dashboard")
else:
    @app.get("/")
    def no_frontend() -> dict:
        return {"message": "Dashboard not built yet. Run scripts\\setup.ps1, or use the Vite dev server."}


def main() -> None:
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")), log_level="warning")


if __name__ == "__main__":
    main()
