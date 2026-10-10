"""backend/pipeline.py and backend/main.py: every opening of a source is a new session, a zone that
climbs gets a new plan, and a plan that was overtaken while Gemini wrote it is never shown."""
import asyncio

import pytest

from backend import main
from backend.config import load_settings
from backend.main import PLAN_COOLDOWN_S, plan_due
from backend.pipeline import Pipeline

SETTINGS = load_settings()


def opened(*source_ids):
    """Opens sources on a pipeline that has no detector and no thread; returns it and the configs it sent."""
    configs = []
    pipeline = Pipeline(SETTINGS, on_config=configs.append, on_frame=lambda *a: None, on_error=lambda text: None)
    for source_id in source_ids:
        assert pipeline._open(source_id)
    return pipeline, configs


# ---- every opening of a source is a new session -------------------------------------------------------

def test_opening_the_drill_should_announce_a_drill_with_no_flow_and_supply_its_own_people():
    pipeline, configs = opened("drill")
    assert configs[-1]["drill"] is True and configs[-1]["flow"] is False and pipeline._mode() == "drill"
    assert pipeline._flow is None and pipeline._replay is pipeline._capture


def test_selecting_the_same_source_again_should_start_a_new_run():
    _, configs = opened("drill", "drill", "plaza", "plaza")
    assert [c["active_source"] for c in configs] == ["drill", "drill", "plaza", "plaza"]
    assert [c["run"] for c in configs] == [1, 2, 3, 4]


def test_a_replayed_clip_should_report_replay_and_a_live_clip_live():
    pipeline, _ = opened("parade_street")
    assert pipeline._mode() == "replay"
    pipeline._open("plaza")
    assert pipeline._mode() == "live"


def test_a_drill_whose_zone_is_off_the_floor_should_be_refused_not_crash():
    from dataclasses import replace
    from backend.config import Zone
    sky = Zone("sky", "Sky", ((0.1, 0.0), (0.9, 0.0), (0.9, 0.02), (0.1, 0.02)))
    bad = replace(SETTINGS.sources["drill"], tilt_deg=5.0, zones=(sky,))  # looking almost level: the top is sky
    errors = []
    pipeline = Pipeline(replace(SETTINGS, sources={"drill": bad}), on_config=lambda m: None,
                        on_frame=lambda *a: None, on_error=errors.append)
    assert pipeline._open("drill") is False and errors == ["Drill is not available"]


# ---- when a level change gets a plan by itself ----------------------------------------------------------

def test_a_zone_with_no_plan_yet_should_get_one():
    assert plan_due(None, 100.0, "caution")


def test_a_zone_should_not_get_a_second_plan_for_the_same_level_inside_the_cooldown():
    assert not plan_due((100.0, "caution"), 100.0 + PLAN_COOLDOWN_S - 1, "caution")
    assert plan_due((100.0, "caution"), 100.0 + PLAN_COOLDOWN_S, "caution")


@pytest.mark.parametrize("planned_for, now_at", [("caution", "danger"), ("caution", "critical"), ("danger", "critical")])
def test_a_zone_that_climbs_should_get_a_new_plan_at_once(planned_for, now_at):
    assert plan_due((100.0, planned_for), 101.0, now_at)


def test_a_zone_that_eases_should_keep_its_plan_inside_the_cooldown():
    assert not plan_due((100.0, "critical"), 110.0, "danger")


# ---- a plan overtaken while it was being written ----------------------------------------------------------

class FakePipeline:
    """Just enough of the pipeline for make_plan: one zone at a level."""

    def __init__(self, level):
        self.settings = SETTINGS
        self.level = level

    def latest(self):
        source = SETTINGS.sources["drill"]
        zones = [{"id": z.id, "count": 100, "density": 4.2, "level": self.level, "trend_per_min": 1.0,
                  "eta_s": None, "eta_level": None, "above_safe_s": 3} for z in source.zones]
        return {"state": {"zones": zones, "total_count": 300}, "jpeg": b"", "source": source, "geometry": None}


def run_plans(monkeypatch, script):
    """Runs `script` against a fresh hub with a slow fake Gemini. Returns the plan messages published as ready."""
    hub = main.Hub()
    hub.publish_config({"type": "config", "active_source": "drill", "run": 1})
    fake = FakePipeline("caution")
    release = {}

    async def slow_generate(context, frame):
        gate = release.setdefault(context["zone"]["level"], asyncio.Event())
        await gate.wait()
        return {"headline": f"Plan at {context['zone']['level']}", "actions": [], "pa_announcement": "",
                "pa_announcement_es": "", "origin": "cached", "model": None, "latency_ms": 1}

    monkeypatch.setattr(main, "hub", hub)
    monkeypatch.setattr(main, "pipeline", fake)
    monkeypatch.setattr(main.plans, "generate", slow_generate)
    main.last_plan_at.clear()
    main.newest_plan.clear()
    asyncio.run(script(hub, fake, release))
    return [m for m in hub.backlog if m["type"] == "plan" and m["status"] == "ready"]


def test_a_plan_should_be_dropped_when_the_drill_is_reset_while_it_is_being_written(monkeypatch):
    async def script(hub, fake, release):
        task = asyncio.create_task(main.make_plan("front_barrier", "a1"))
        await asyncio.sleep(0)
        hub.publish_config({"type": "config", "active_source": "drill", "run": 2})  # R pressed
        release["caution"].set()
        await task

    assert run_plans(monkeypatch, script) == []


def test_only_the_newest_plan_should_be_shown_when_a_zone_climbs_while_one_is_being_written(monkeypatch):
    async def script(hub, fake, release):
        first = asyncio.create_task(main.make_plan("front_barrier", "a1"))
        await asyncio.sleep(0)
        fake.level = "critical"
        second = asyncio.create_task(main.make_plan("front_barrier", "a2"))
        await asyncio.sleep(0)
        release["critical"].set()  # the newer plan is ready first
        await second
        release["caution"].set()   # then the older one finishes
        await first

    ready = run_plans(monkeypatch, script)
    assert [p["headline"] for p in ready] == ["DRILL: Plan at critical"]


# ---- who may open the console's socket ----------------------------------------------------------------

@pytest.mark.parametrize("origin, host", [
    (None, "localhost:8000"),                               # a script or tool: no browser, no Origin
    ("http://localhost:8000", "localhost:8000"),            # the console
    ("http://127.0.0.1:8000", "127.0.0.1:8000"),
    ("http://localhost:5173", "localhost:8000"),            # the Vite dev server proxying to the backend
    ("http://192.168.1.20:8000", "192.168.1.20:8000"),      # served on the venue network by address
    ("http://[::1]:8000", "[::1]:8000"),
])
def test_the_console_and_scripts_should_be_allowed_to_open_the_socket(origin, host):
    assert main.trusted_origin(origin, host)


@pytest.mark.parametrize("origin, host", [
    ("https://example.com", "localhost:8000"),              # any other site open in the operator's browser
    ("http://localhost.example.com", "localhost:8000"),
    ("http://127.0.0.1:8000", "localhost:8000"),            # not the address the page was served from
    ("http://rebind.example.com:8000", "rebind.example.com:8000"),  # a hostile name pointed at this machine
    ("null", "localhost:8000"),                             # a sandboxed page or a local file
])
def test_another_web_page_should_not_be_allowed_to_open_the_socket(origin, host):
    assert not main.trusted_origin(origin, host)


# ---- one bad frame must not stop the console ------------------------------------------------------------

def test_the_pipeline_should_report_an_unexpected_error_and_carry_on_with_the_next_frame():
    import threading

    frames, errors, enough = [], [], threading.Event()

    def on_frame(state, jpeg, alerts):
        frames.append(state)
        if len(frames) >= 3:
            enough.set()

    pipeline = Pipeline(SETTINGS, on_config=lambda m: None, on_frame=on_frame, on_error=errors.append)
    assert pipeline._open("drill")
    real_measure, calls = pipeline._counter.measure, {"n": 0}

    def flaky_measure(boxes):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ZeroDivisionError("a frame the code did not expect")
        return real_measure(boxes)

    pipeline._counter.measure = flaky_measure
    pipeline._stop_flag.wait = lambda seconds: None  # do not sit out the pause in a test
    worker = threading.Thread(target=lambda: [pipeline._loop_guarded()], daemon=True)
    worker.start()
    assert enough.wait(20), "no frames after the error"
    pipeline.stop()
    assert len(errors) == 1 and "ZeroDivisionError" in errors[0]
    assert frames[-1]["mode"] == "drill"
