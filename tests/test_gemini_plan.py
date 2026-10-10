"""backend/gemini_plan.py with no API key: the cached plan and report must still be complete and valid.
Nothing here touches the network (the key is removed from the environment before every test)."""
import asyncio
import json
import re
import string
from pathlib import Path

import pytest

from backend.gemini_plan import DEFAULT_MODELS, PlanGenerator
from backend.schemas import IncidentReport, ResponsePlan

FALLBACKS = json.loads((Path(__file__).resolve().parent.parent / "backend" / "fallback_plans.json").read_text("utf-8"))


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL", "GEMINI_SEND_FRAME"):
        monkeypatch.delenv(name, raising=False)


def plan_for(level="caution", name="Main Floor", others=None, **extra):
    context = {"zone": {"id": "main", "name": name, "level": level, "density_per_m2": 4.4}}
    if others is not None:
        context["other_zones"] = others
    return asyncio.run(PlanGenerator().generate({**context, **extra}))


def strings(plan):
    return [plan["headline"], plan["pa_announcement"], plan["pa_announcement_es"]] + \
           [a[k] for a in plan["actions"] for k in ("role", "instruction")]


OTHERS = [{"name": "Ticket Hall", "density_per_m2": 3.1}, {"name": "East Corridor", "density_per_m2": 0.4},
          {"name": "Gate Entry", "density_per_m2": 1.8}]


# ---- generator state ------------------------------------------------------------------------------

def test_generator_should_be_disabled_when_no_key_is_set():
    assert PlanGenerator().enabled is False


def test_generator_should_be_enabled_by_either_key_variable(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-key-for-the-test")
    assert PlanGenerator().enabled is True


def test_a_configured_model_should_be_tried_first_without_duplicating_the_defaults(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", DEFAULT_MODELS[1])
    models = PlanGenerator().models
    assert models[0] == DEFAULT_MODELS[1] and sorted(models) == sorted(DEFAULT_MODELS)


# ---- cached plan ----------------------------------------------------------------------------------

@pytest.mark.parametrize("level", ["caution", "danger", "critical"])
def test_cached_plan_should_report_its_origin_and_validate_as_a_response_plan(level):
    plan = plan_for(level, others=OTHERS)
    assert plan["origin"] == "cached" and plan["model"] is None and plan["latency_ms"] >= 0
    parsed = ResponsePlan(**plan)
    assert parsed.headline and parsed.pa_announcement and parsed.pa_announcement_es


@pytest.mark.parametrize("level", ["caution", "danger", "critical"])
def test_cached_plan_should_have_three_to_five_actions_each_with_a_role_and_an_instruction(level):
    actions = ResponsePlan(**plan_for(level, others=OTHERS)).actions
    assert 3 <= len(actions) <= 5 and all(a.role.strip() and a.instruction.strip() for a in actions)


def test_cached_plan_should_put_the_zone_name_in_the_headline_and_leave_no_placeholders():
    plan = plan_for("caution", name="Gate 3 Entry", others=OTHERS)
    assert "Gate 3 Entry" in plan["headline"]
    assert not any(re.search(r"[{}]", s) for s in strings(plan))


def test_cached_plan_should_direct_people_to_the_least_crowded_other_zone():
    plan = plan_for("danger", others=OTHERS)
    assert "East Corridor" in " ".join(strings(plan)) and "Ticket Hall" not in " ".join(strings(plan))


def test_cached_plan_should_fall_back_to_a_generic_relief_area_when_there_are_no_other_zones():
    for others in (None, []):
        plan = plan_for("danger", others=others)
        assert "the nearest open area" in " ".join(strings(plan))


@pytest.mark.parametrize("level", ["danger", "critical"])
def test_danger_and_critical_should_use_the_urgent_template(level):
    plan = plan_for(level, name="Zone X", others=OTHERS)
    assert plan["headline"] == FALLBACKS["red"]["headline"].format(zone="Zone X", relief="East Corridor")
    assert [a["role"] for a in plan["actions"]] == [a["role"] for a in FALLBACKS["red"]["actions"]]


def test_caution_should_use_the_milder_template_not_the_urgent_one():
    plan = plan_for("caution", name="Zone X", others=OTHERS)
    assert plan["headline"] == FALLBACKS["yellow"]["headline"].format(zone="Zone X", relief="East Corridor")
    assert len(plan["actions"]) == len(FALLBACKS["yellow"]["actions"])


def test_urgent_plan_should_tell_staff_to_stop_inflow_first():
    plan = plan_for("critical", others=OTHERS)
    assert "stop" in plan["actions"][0]["instruction"].lower()


def test_cached_plan_should_carry_a_spanish_announcement_that_differs_from_the_english_one():
    plan = plan_for("danger", others=OTHERS)
    assert plan["pa_announcement_es"] != plan["pa_announcement"] and "East Corridor" in plan["pa_announcement_es"]


def test_cached_plan_should_ignore_a_camera_frame_when_there_is_no_key():
    generator = PlanGenerator()
    context = {"zone": {"name": "Z", "level": "caution"}}
    plan = asyncio.run(generator.generate(context, frame_jpeg=b"\xff\xd8\xff\xd9"))
    assert plan["origin"] == "cached"


def test_fallback_templates_should_only_use_the_zone_and_relief_placeholders():
    for template in (FALLBACKS["red"], FALLBACKS["yellow"]):
        texts = [template["headline"], template["pa_announcement"], template["pa_announcement_es"]]
        texts += [a["instruction"] for a in template["actions"]]
        fields = {name for t in texts for _, name, _, _ in string.Formatter().parse(t) if name}
        assert fields <= {"zone", "relief"}


# ---- cached report --------------------------------------------------------------------------------

def log(zones=None, alerts=None, plans=None, camera="Gate 3 Concourse"):
    return {"camera": camera, "density_scale_per_m2": {"caution_action_level": 4.0},
            "zones": zones if zones is not None else [
                {"name": "Main Floor", "peak_density_per_m2": 1.2, "peak_time": "10:04:10"},
                {"name": "Ticket Hall", "peak_density_per_m2": 0.8, "peak_time": "10:03:00"}],
            "alerts": alerts or [], "plans": plans or []}


def report_for(data):
    return asyncio.run(PlanGenerator().report(data))


def alert(level="danger", time="10:05:00", message="Main Floor reached DANGER", ack=None):
    return {"level": level, "time": time, "message": message, "acknowledged_after_s": ack}


def test_cached_report_should_validate_as_an_incident_report_and_say_where_it_came_from():
    result = report_for(log())
    assert result["origin"] == "cached" and result["model"] is None
    parsed = IncidentReport(**result)
    assert parsed.title and parsed.summary and parsed.timeline and parsed.recommendations


def test_a_quiet_report_should_say_that_nothing_reached_the_safe_limit_and_name_the_peak():
    result = report_for(log())
    assert "No zone reached the action level of 4.0" in result["summary"]
    assert "1.2" in result["summary"] and "Main Floor" in result["summary"] and "10:04:10" in result["summary"]
    assert result["timeline"] == ["No alerts in this period."]


def test_a_report_with_serious_alerts_should_count_them_in_the_summary():
    alerts = [alert("caution", "10:01:00", "A reached CAUTION", 12), alert("danger", "10:02:00", "A reached DANGER", 5),
              alert("busy", "10:00:30", "A is getting busy")]
    assert "2 alert(s) at or above the action level" in report_for(log(alerts=alerts))["summary"]


def test_a_report_should_warn_about_serious_alerts_that_were_never_acknowledged_and_put_that_first():
    result = report_for(log(alerts=[alert(ack=None), alert("caution", "10:06:00", "B reached CAUTION", 9)]))
    assert "1 alert(s)" in result["recommendations"][0] and "never acknowledged" in result["recommendations"][0]
    assert len(result["recommendations"]) == 2


def test_a_report_should_not_warn_when_every_serious_alert_was_acknowledged():
    result = report_for(log(alerts=[alert(ack=7)]))
    assert not any("never acknowledged" in r for r in result["recommendations"])


def test_the_timeline_should_be_in_clock_order_and_include_the_plans_issued():
    alerts = [alert("danger", "10:09:00", "late"), alert("caution", "10:01:00", "early")]
    plans = [{"time": "10:05:00", "zone": "Main Floor", "headline": "Relieve pressure"}]
    timeline = report_for(log(alerts=alerts, plans=plans))["timeline"]
    assert timeline == sorted(timeline) and len(timeline) == 3
    assert "Response plan issued for Main Floor: Relieve pressure" in timeline[1]


def test_a_report_with_no_zone_readings_should_say_so_without_failing():
    result = report_for(log(zones=[]))
    assert result["summary"] == "No readings were recorded in this period."
    IncidentReport(**result)


def test_the_report_title_should_name_the_camera():
    assert report_for(log(camera="East Plaza"))["title"].startswith("East Plaza")
