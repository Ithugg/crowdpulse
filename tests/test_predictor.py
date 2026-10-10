"""backend/predictor.py: ZoneTracker smoothing, level changes, exposure timer and forecast on synthetic ramps."""
import math

import pytest

from backend.config import Zone
from backend.predictor import DWELL_DOWN_S, DWELL_UP_S, SMOOTH_TAU_S, WARMUP_S, ZoneTracker
from crowd_helpers import DT, RAMP, RAMP_END_S, THRESHOLDS, one_zone, piecewise, run


def tracker(areas=None):
    return ZoneTracker((one_zone(),), THRESHOLDS, areas)


def frames(density_at, duration_s):
    """Rows of (t, level, density, above_safe_s, eta_s, eta_level, trend_per_min, history length)."""
    return [(t, s.level, s.density, s.above_safe_s, s.eta_s, s.eta_level, s.trend_per_min, len(s.history()))
            for t, s, _ in run(tracker(), density_at, duration_s)]


def distinct(seq):
    return [x for i, x in enumerate(seq) if i == 0 or x != seq[i - 1]]


# ---- levels on the ramp ---------------------------------------------------------------------------

def test_levels_should_be_reached_in_order_up_and_down_on_a_full_ramp():
    levels = distinct([f[1] for f in frames(RAMP, RAMP_END_S)])
    assert levels == ["normal", "busy", "caution", "danger", "critical", "danger", "caution", "busy", "normal"]


def test_zone_should_be_at_critical_while_density_is_held_at_six_and_a_half():
    held = [f for f in frames(RAMP, 500) if 300 <= f[0] <= 500]
    assert {f[1] for f in held} == {"critical"}


def test_level_should_not_rise_before_the_density_has_crossed_the_threshold():
    rows = frames(RAMP, 200)
    assert all(f[2] >= 4.0 for f in rows if f[1] in ("caution", "danger", "critical"))


# ---- warm-up and dwell ----------------------------------------------------------------------------

def test_level_should_not_change_during_the_warm_up_even_when_density_is_extreme():
    rows = frames(lambda t: 6.5, WARMUP_S + 5)
    assert all(f[1] == "normal" for f in rows if f[0] < WARMUP_S)


def test_level_should_jump_straight_to_critical_after_warm_up_and_dwell_when_density_stays_extreme():
    rows = frames(lambda t: 6.5, WARMUP_S + DWELL_UP_S + 1.0)
    assert rows[-1][1] == "critical"


def test_a_short_excursion_above_a_threshold_should_not_change_the_level():
    spike = piecewise([(0, 1.0), (10, 1.0), (10.01, 3.0), (12, 3.0), (12.01, 1.0), (30, 1.0)])
    assert {f[1] for f in frames(spike, 30)} == {"normal"}


def test_the_same_density_should_change_the_level_when_it_is_held():
    held = piecewise([(0, 1.0), (10, 1.0), (10.01, 3.0), (40, 3.0)])
    assert frames(held, 40)[-1][1] == "busy"


def test_stepping_down_should_wait_the_down_dwell_after_the_drop_below_the_threshold():
    drop = piecewise([(0, 4.5), (20, 4.5), (20.01, 1.0), (60, 1.0)])
    rows = frames(drop, 60)
    below_since = next(f[0] for f in rows if f[0] > 20 and f[2] < 3.6)
    stepped = next(f[0] for f in rows if f[0] > 20 and f[1] != "caution")
    assert stepped - below_since >= DWELL_DOWN_S - 2 * DT


def test_stepping_up_should_wait_at_least_the_up_dwell_after_crossing_the_threshold():
    rise = piecewise([(0, 1.0), (10, 1.0), (10.01, 6.0), (40, 6.0)])
    rows = frames(rise, 40)
    crossed = next(f[0] for f in rows if f[0] > 10 and f[2] >= 2.0)
    changed = next(f[0] for f in rows if f[0] > 10 and f[1] != "normal")
    assert changed - crossed >= DWELL_UP_S - 2 * DT


def test_zone_should_stay_at_caution_while_density_sits_just_under_the_safe_limit():
    """Hysteresis: 3.8 is below 4 but not clearly below, so a zone already at caution holds it."""
    sag = piecewise([(0, 4.5), (20, 4.5), (20.01, 3.8), (80, 3.8)])
    rows = frames(sag, 80)
    assert rows[-1][1] == "caution" and rows[-1][2] == pytest.approx(3.8, abs=0.05)


def test_zone_should_leave_caution_once_density_settles_clearly_below_the_safe_limit():
    settle = piecewise([(0, 4.5), (20, 4.5), (20.01, 3.4), (80, 3.4)])
    assert frames(settle, 80)[-1][1] == "busy"


def test_level_should_not_flap_when_density_oscillates_around_the_safe_limit():
    def wobble(t):
        return 4.5 if t < 20 else (3.8 if int(t) % 2 else 4.2)
    levels = distinct([f[1] for f in frames(wobble, 140) if f[0] > 20])
    assert levels == ["caution"]


def test_level_should_not_flap_when_density_swings_widely_around_the_safe_limit():
    def swing(t):
        return 4.5 if t < 20 else (3.0 if int(t / 3) % 2 else 5.0)
    levels = distinct([f[1] for f in frames(swing, 140) if f[0] > 25])
    assert len(levels) <= 2 and "busy" not in levels and "normal" not in levels


# ---- smoothing ------------------------------------------------------------------------------------

def test_first_update_should_take_the_raw_density_unsmoothed():
    assert tracker().update([3], [2.7], 100.0)[0].density == 2.7


@pytest.mark.parametrize("step", [DT, 0.2])
def test_smoothing_should_follow_the_time_constant_regardless_of_frame_rate(step):
    tr = tracker()
    t = 0.0
    tr.update([1], [1.0], t)
    while t < 5.0 - 1e-9:
        t += step
        state = tr.update([1], [5.0], t)[0]
    assert state.density == pytest.approx(5.0 - 4.0 * math.exp(-5.0 / SMOOTH_TAU_S), abs=0.01)


# ---- exposure timer -------------------------------------------------------------------------------

def test_above_safe_s_should_stay_zero_below_caution():
    assert {f[3] for f in frames(lambda t: 3.0, 60)} == {0.0}


def test_above_safe_s_should_count_up_in_real_seconds_once_the_zone_is_at_caution():
    rows = frames(lambda t: 4.5, 60)
    at_caution = next(f for f in rows if f[1] == "caution")
    assert rows[-1][3] == pytest.approx(rows[-1][0] - at_caution[0], abs=DT)
    assert rows[-1][3] > 50


def test_above_safe_s_should_count_at_danger_and_critical_too():
    rows = frames(lambda t: 6.5, 40)
    assert rows[-1][1] == "critical" and rows[-1][3] > 30


def test_above_safe_s_should_reset_to_zero_once_the_level_drops_below_caution():
    rows = frames(RAMP, RAMP_END_S)
    assert max(f[3] for f in rows) > 400
    assert all(f[3] == 0.0 for f in rows if f[1] in ("normal", "busy"))
    assert rows[-1][3] == 0.0


def test_above_safe_s_should_start_again_from_zero_on_a_second_excursion():
    twice = piecewise([(0, 1), (5, 5), (60, 5), (65, 1), (100, 1), (105, 5), (140, 5)])
    rows = frames(twice, 140)
    first_peak = max(f[3] for f in rows if f[0] < 90)
    assert first_peak > 40 and rows[-1][3] < first_peak and rows[-1][3] < 40


# ---- forecast -------------------------------------------------------------------------------------

def test_forecast_should_be_absent_until_thirty_seconds_of_history_exist():
    rows = frames(piecewise([(0, 3.0), (60, 4.8)]), 60)
    assert all(f[4] is None for f in rows if f[0] < 28)
    assert any(f[4] is not None for f in rows if f[0] > 40)


def test_forecast_should_appear_only_once_density_is_halfway_to_the_target_level():
    slow = piecewise([(0, 0.5), (250, 3.0)])  # rising steadily, but below 2/m2 (half of 4) for 150 s
    rows = frames(slow, 250)
    early = [f for f in rows if f[2] < 1.95]
    assert any(f[6] > 0.3 for f in early), "the trend itself is measured long before the forecast"
    assert all(f[4] is None for f in early)
    first = next(f for f in rows if f[4] is not None)
    assert first[2] == pytest.approx(2.0, abs=0.1) and first[5] == "caution"


def test_forecast_should_be_roughly_right_about_when_caution_is_reached():
    rows = frames(RAMP, 120)
    at_60 = next(f for f in rows if f[0] >= 60)
    reached = next(f[0] for f in rows if f[2] >= 4.0)
    assert at_60[5] == "caution"
    assert at_60[4] == pytest.approx(reached - at_60[0], rel=0.25)


def test_forecast_should_name_the_next_level_up_as_the_zone_climbs():
    seen = {(f[1], f[5]) for f in frames(RAMP, 175) if f[5]}
    assert {("busy", "caution"), ("caution", "danger"), ("danger", "critical")} <= seen


def test_forecast_should_be_absent_at_critical_because_there_is_no_higher_level():
    assert all(f[5] is None for f in frames(RAMP, 300) if f[1] == "critical")


def test_forecast_should_be_absent_when_density_is_flat():
    rows = frames(lambda t: 3.0, 120)
    assert all(f[4] is None and f[5] is None for f in rows)
    assert abs(rows[-1][6]) < 0.05


def test_forecast_should_be_absent_when_density_is_falling():
    rows = frames(piecewise([(0, 6.5), (100, 2.5)]), 100)
    assert all(f[4] is None for f in rows) and rows[-1][6] < 0


def test_forecast_should_be_absent_when_density_creeps_up_too_slowly_to_count_as_a_trend():
    creep = piecewise([(0, 3.0), (120, 3.0 + 0.002 * 120)])  # 0.12 people/m2 per minute
    assert all(f[4] is None for f in frames(creep, 120))


# ---- history --------------------------------------------------------------------------------------

def test_history_should_hold_about_one_sample_per_second():
    assert 28 <= frames(RAMP, 30)[-1][7] <= 31


def test_history_should_be_capped_at_one_minute():
    assert frames(RAMP, 200)[-1][7] <= 61


def test_history_should_run_oldest_first_and_end_near_the_current_density():
    state = None
    for _t, state, _ in run(tracker(), RAMP, 90):
        pass
    hist = state.history()
    assert hist == sorted(hist) and hist[-1] == pytest.approx(state.density, abs=0.1)


def test_history_should_be_empty_before_any_update():
    assert tracker().states[0].history() == []


# ---- bookkeeping ----------------------------------------------------------------------------------

def test_avg_density_should_be_count_over_area_when_the_area_is_known():
    assert tracker(areas=[20.0]).update([30], [2.0], 0.0)[0].avg_density == pytest.approx(1.5)


def test_avg_density_should_be_none_when_the_area_is_unknown():
    assert tracker().update([30], [2.0], 0.0)[0].avg_density is None


def test_set_areas_should_apply_to_later_updates():
    tr = tracker()
    tr.set_areas([10.0])
    assert tr.update([5], [1.0], 0.0)[0].avg_density == pytest.approx(0.5)


def test_zones_should_be_tracked_independently():
    zones = (one_zone(), Zone("z2", "Zone Two", one_zone().polygon))
    tr = ZoneTracker(zones, THRESHOLDS)
    for i in range(300):
        tr.update([3, 1], [6.5, 1.0], i * DT)
    assert [s.level for s in tr.states] == ["critical", "normal"]
    assert [s.count for s in tr.states] == [3, 1]
