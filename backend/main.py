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
DIST_DIR = REPO_ROOT / "frontend" / "dist"


def dumps(message: dict) -> str:
    return json.dumps(message, separators=(",", ":"))


class Client:
    """Per-connection outbox: events are queued in order, video frames are latest-only."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.events: deque[str] = deque()
        self.frame: tuple[str, bytes] | None = None
        self.wake = asyncio.Event()


class Hub:
    def __init__(self):
        self.clients: set[Client] = set()
        self.config: str | None = None
        self.active_source: str | None = None
        self.backlog: deque[str] = deque(maxlen=40)  # recent alerts + plans for late joiners

    def publish_config(self, message: dict) -> None:
        self.config = dumps(message)
        if message["active_source"] != self.active_source:  # a calibration update keeps the same camera's alerts
            self.active_source = message["active_source"]
            self.backlog.clear()
        self._send_event(self.config)

    def publish_event(self, message: dict, remember: bool = True) -> None:
        text = dumps(message)
        if remember:
            self.backlog.append(text)
        self._send_event(text)

    def publish_frame(self, state: dict, jpeg: bytes) -> None:
        text = dumps(state)
        for client in self.clients:
            client.frame = (text, jpeg)  # overwrites any frame the client has not sent yet
            client.wake.set()

    def _send_event(self, text: str) -> None:
        for client in self.clients:
            client.events.append(text)
            client.wake.set()


hub = Hub()
plans = PlanGenerator()
plan_ids = itertools.count(1)
last_plan_at: dict[str, float] = {}
background_tasks: set[asyncio.Task] = set()
pipeline: Pipeline | None = None


def spawn(coro) -> None:
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def plan_context(latest: dict, zone_id: str) -> dict | None:
    """The situation summary sent to Gemini for one zone."""
    state, source, geometry = latest["state"], latest["source"], latest["geometry"]
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

    th = pipeline.settings.thresholds
    return {
        "camera": source.label,
        "density_scale_per_m2": {"busy": th.busy, "caution_safe_limit": th.caution, "danger": th.danger,
                                 "critical": th.critical},
        "measurement": ("local peak density on the ground plane, camera calibrated from the people in view"
                        if geometry.mode == "ground" else "local peak density, distance estimated from body size"),
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

    base = {"type": "plan", "id": f"p{next(plan_ids)}", "alert_id": alert_id, "zone_id": zone_id,
            "zone_name": context["zone"]["name"], "level": context["zone"]["level"], "ts": time.time()}
    hub.publish_event({**base, "status": "generating"}, remember=False)
    result = await plans.generate(context, latest["jpeg"])
    hub.publish_event({**base, "status": "ready", **result})
    log.info("Plan for %s ready (%s, %s ms)", zone_id, result["origin"], result["latency_ms"])


def on_frame(state: dict, jpeg: bytes, alerts: list[dict]) -> None:
    hub.publish_frame(state, jpeg)
    for alert in alerts:
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
    log.info("Gemini plans: %s", "enabled" if plans.enabled else "no GEMINI_API_KEY, using cached plans")
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
        pipeline.set_overlay(message.get("boxes"), message.get("heatmap"))
    elif kind == "restart":
        pipeline.restart()
    elif kind == "request_plan":
        spawn(make_plan(str(message.get("zone_id", "")), forced=True))


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    client = Client(ws)
    if hub.config:
        client.events.append(hub.config)
    client.events.extend(hub.backlog)
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


if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="dashboard")
else:
    @app.get("/")
    def no_frontend() -> dict:
        return {"message": "Dashboard not built yet. Run scripts\\setup.ps1, or use the Vite dev server."}


def main() -> None:
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")), log_level="warning")


if __name__ == "__main__":
    main()
