"""backend/alerts.py: AlertManager on the full density ramp, plus cooldown / exposure / reset on hand-built states."""
import pytest

from backend.config import Zone
from backend.alerts import PREDICTION_COOLDOWN_S, PREDICTION_HORIZON_S, AlertManager, format_eta
from backend.predictor import ZoneState, ZoneTracker
from crowd_helpers import RAMP, RAMP_END_S, THRESHOLDS, one_zone, run


def ramp_alerts():
    """[(t, alert)] raised while the tracker and manager run the 1 -> 6.5 -> 0.5 ramp."""
    manager, out = AlertManager(THRESHOLDS), []
    for t, _state, raised in run(ZoneTracker((one_zone(),), THRESHOLDS), RAMP, RAMP_END_S, manager):
        out += [(t, a) for a in raised]
    return out


def first(alerts, **match):
    """Time of the first alert whose fields match (and whose message contains `says`, if given)."""
    says = match.pop("says", "")
    return next(t for t, a in alerts if says in a["message"] and all(a[k] == v for k, v in match.items()))


def state(level="normal", density=1.0, eta_s=None, eta_level=None, above_safe_s=0.0):
    return ZoneState(one_zone(), count=5, density=density, level=level, eta_s=eta_s, eta_level=eta_level,
                     above_safe_s=above_safe_s)


def forecasts(manager, states, t):
    """Only the forecast alerts raised by this frame (a fresh busy zone also raises a level alert)."""
    return [a for a in manager.update(states, t) if a["kind"] == "prediction"]


# ---- the ramp -------------------------------------------------------------------------------------

def test_alerts_should_come_out_in_the_expected_order_on_the_ramp():
    alerts = ramp_alerts()
    order = [
        first(alerts, kind="level_change", level="busy"),
        first(alerts, kind="level_change", level="caution", says="reached"),
        first(alerts, kind="level_change", level="danger", says="reached"),
        first(alerts, kind="level_change", level="critical", says="reached"),
        first(alerts, kind="exposure"),
        first(alerts, kind="level_change", level="danger", says="easing"),
        first(alerts, kind="cleared"),
    ]
    assert order == sorted(order) and len(set(order)) == len(order)


def test_a_forecast_for_caution_should_arrive_before_the_zone_reaches_caution():
    alerts = ramp_alerts()
    forecast = first(alerts, kind="prediction", level="caution")
    assert forecast < first(alerts, kind="level_change", level="caution", says="reached") - 30


def test_the_forecast_and_the_busy_alert_should_both_come_before_caution():
    alerts = ramp_alerts()
    caution = first(alerts, kind="level_change", level="caution", says="reached")
    assert first(alerts, kind="prediction") < caution and first(alerts, kind="level_change", level="busy") < caution


def test_the_exposure_alert_should_fire_six_minutes_after_caution_was_reached():
    alerts = ramp_alerts()
    caution = first(alerts, kind="level_change", level="caution", says="reached")
    assert first(alerts, kind="exposure") - caution == pytest.approx(360, abs=1.0)


def test_each_upward_level_should_be_announced_exactly_once():
    alerts = [a for _, a in ramp_alerts()]
    for level in ("caution", "danger", "critical"):
        assert sum(a["kind"] == "level_change" and a["level"] == level and "reached" in a["message"]
                   for a in alerts) == 1


def test_the_whole_ramp_should_raise_exactly_one_exposure_one_cleared_and_two_easing_alerts():
    kinds = [a["kind"] for _, a in ramp_alerts()]
    messages = [a["message"] for _, a in ramp_alerts()]
    assert kinds.count("exposure") == 1 and kinds.count("cleared") == 1
    assert sum("easing to" in m for m in messages) == 2


def test_alert_ids_should_be_unique_and_every_alert_should_name_its_zone():
    alerts = [a for _, a in ramp_alerts()]
    assert len({a["id"] for a in alerts}) == len(alerts)
    assert {(a["zone_id"], a["zone_name"], a["type"]) for a in alerts} == {("z1", "Zone One", "alert")}


def test_the_cleared_alert_should_report_a_level_below_caution():
    cleared = [a for _, a in ramp_alerts() if a["kind"] == "cleared"]
    assert cleared[0]["level"] in ("busy", "normal") and cleared[0]["density"] < 4.0


def test_a_steady_normal_zone_should_raise_nothing():
    manager = AlertManager(THRESHOLDS)
    raised = [a for _t, _s, al in run(ZoneTracker((one_zone(),), THRESHOLDS), lambda t: 1.0, 120, manager)
              for a in al]
    assert raised == []


# ---- level_change details -------------------------------------------------------------------------

def test_a_jump_from_normal_to_critical_should_raise_one_reached_alert_for_critical():
    alerts = AlertManager(THRESHOLDS).update([state("critical", 6.4)], 0.0)
    assert [(a["kind"], a["level"]) for a in alerts] == [("level_change", "critical")]
    assert "reached CRITICAL" in alerts[0]["message"] and alerts[0]["density"] == 6.4


def test_dropping_from_normal_straight_to_busy_should_say_busy_and_not_cleared():
    alerts = AlertManager(THRESHOLDS).update([state("busy", 2.1)], 0.0)
    assert [(a["kind"], a["level"]) for a in alerts] == [("level_change", "busy")]


def test_returning_from_busy_to_normal_should_raise_nothing():
    manager = AlertManager(THRESHOLDS)
    manager.update([state("busy", 2.1)], 0.0)
    assert manager.update([state("normal", 1.5)], 10.0) == []


def test_the_same_level_on_consecutive_frames_should_not_repeat_the_alert():
    manager = AlertManager(THRESHOLDS)
    assert len(manager.update([state("caution", 4.1)], 0.0)) == 1
    assert manager.update([state("caution", 4.2)], 1.0) == []


# ---- forecast cooldown ----------------------------------------------------------------------------

def test_forecast_should_fire_once_and_then_hold_for_the_cooldown():
    manager = AlertManager(THRESHOLDS)
    s = state("busy", 3.0, eta_s=100.0, eta_level="caution")
    times = [0.0, 10.0, 30.0, PREDICTION_COOLDOWN_S - 0.1]
    assert [len(forecasts(manager, [s], t)) for t in times] == [1, 0, 0, 0]


def test_forecast_should_fire_again_once_the_cooldown_has_passed():
    manager = AlertManager(THRESHOLDS)
    s = state("busy", 3.0, eta_s=100.0, eta_level="caution")
    forecasts(manager, [s], 0.0)
    assert len(forecasts(manager, [s], PREDICTION_COOLDOWN_S)) == 1


def test_forecast_message_should_name_the_target_level_and_the_time():
    alert = forecasts(AlertManager(THRESHOLDS), [state("busy", 3.0, eta_s=70.0, eta_level="danger")], 0.0)[0]
    assert alert["level"] == "danger" and "Danger" in alert["message"] and "70 s" in alert["message"]


def test_forecast_beyond_the_horizon_should_be_ignored():
    s = state("busy", 3.0, eta_s=PREDICTION_HORIZON_S + 1, eta_level="caution")
    assert forecasts(AlertManager(THRESHOLDS), [s], 0.0) == []


def test_forecast_cooldown_should_be_kept_per_zone():
    manager = AlertManager(THRESHOLDS)
    other = ZoneState(Zone("z2", "Zone Two", one_zone().polygon), density=3.0, level="busy",
                      eta_s=50.0, eta_level="caution")
    a = state("busy", 3.0, eta_s=50.0, eta_level="caution")
    assert len(forecasts(manager, [a, other], 0.0)) == 2
    assert forecasts(manager, [a, other], 5.0) == []


@pytest.mark.parametrize("seconds, text", [(10, "10 s"), (4, "10 s"), (70, "70 s"), (89, "90 s"),
                                           (90, "2 min"), (150, "2 min"), (600, "10 min")])
def test_format_eta_should_round_to_ten_seconds_then_to_whole_minutes(seconds, text):
    assert format_eta(seconds) == text


# ---- exposure -------------------------------------------------------------------------------------

def test_exposure_should_not_fire_just_before_the_limit_and_fire_once_at_it():
    manager = AlertManager(THRESHOLDS)
    manager.update([state("caution", 4.5, above_safe_s=0.0)], 0.0)
    assert manager.update([state("caution", 4.5, above_safe_s=359.0)], 359.0) == []
    fired = manager.update([state("caution", 4.5, above_safe_s=360.0)], 360.0)
    assert [a["kind"] for a in fired] == ["exposure"] and "6 min" in fired[0]["message"]
    assert manager.update([state("caution", 4.5, above_safe_s=400.0)], 400.0) == []


def test_exposure_should_be_allowed_again_after_the_zone_drops_below_the_safe_limit():
    manager = AlertManager(THRESHOLDS)
    manager.update([state("caution", 4.5, above_safe_s=361.0)], 361.0)
    manager.update([state("busy", 3.0, above_safe_s=0.0)], 400.0)
    again = manager.update([state("caution", 4.5, above_safe_s=361.0)], 800.0)
    assert [a["kind"] for a in again if a["kind"] == "exposure"] == ["exposure"]


# ---- reset ----------------------------------------------------------------------------------------

def test_reset_should_let_a_level_alert_fire_again():
    manager = AlertManager(THRESHOLDS)
    assert len(manager.update([state("caution", 4.2)], 0.0)) == 1
    assert manager.update([state("caution", 4.2)], 1.0) == []
    manager.reset()
    assert [a["level"] for a in manager.update([state("caution", 4.2)], 2.0)] == ["caution"]


def test_reset_should_let_the_forecast_fire_without_waiting_for_the_cooldown():
    manager = AlertManager(THRESHOLDS)
    s = state("busy", 3.0, eta_s=100.0, eta_level="caution")
    forecasts(manager, [s], 0.0)
    manager.reset()
    assert len(forecasts(manager, [s], 1.0)) == 1


def test_reset_should_let_the_exposure_alert_fire_again():
    manager = AlertManager(THRESHOLDS)
    s = state("caution", 4.5, above_safe_s=400.0)
    manager.update([s], 0.0)
    manager.reset()
    assert "exposure" in [a["kind"] for a in manager.update([s], 1.0)]


def test_reset_should_not_reuse_alert_ids():
    manager = AlertManager(THRESHOLDS)
    first_id = manager.update([state("caution", 4.2)], 0.0)[0]["id"]
    manager.reset()
    assert manager.update([state("caution", 4.2)], 1.0)[0]["id"] != first_id
