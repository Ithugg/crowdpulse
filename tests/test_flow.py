"""backend/flow.py: FlowTracker identity, zone walking speed / alignment, and gate-line counting.
People are synthetic boxes (30 x 80 px) that move along known paths; the ground positions are supplied
by the test, so a known speed in m/s can be checked."""
import numpy as np
import pytest

from backend.config import Gate
from backend.flow import MAX_SPEED_MPS, FlowTracker

FW, FH, FPS = 640, 480, 15.0
BOX_W, BOX_H = 30.0, 80.0


class Walker:
    """Feet start at pixel (x, y) and move at (vx, vy) px/s; on the ground they move at gv metres/s.
    `path(t) -> (x, y)` overrides the pixel motion (for jitter and gate tests)."""

    def __init__(self, x=100.0, y=300.0, vx=60.0, vy=0.0, gv=(1.2, 0.0), path=None):
        self.x, self.y, self.vx, self.vy, self.gv, self.path = x, y, vx, vy, gv, path

    def feet(self, t):
        return self.path(t) if self.path else (self.x + self.vx * t, self.y + self.vy * t)

    def box(self, t):
        x, y = self.feet(t)
        return [x - BOX_W / 2, y - BOX_H, x + BOX_W / 2, y, 0.9]

    def ground(self, t):
        return [self.gv[0] * t, self.gv[1] * t]


def feed(tracker, walkers, seconds, t0=0.0, zone=0, calibrated=True, density=1.0, skip=()):
    """Runs 15 fps; returns (flows, gates) of the last frame. `skip` = frame numbers with no detections."""
    out = None
    for i in range(int(seconds * FPS) + 1):
        t = t0 + i * (1.0 / FPS)
        ws = [] if i in skip else walkers
        boxes = np.array([w.box(t) for w in ws], dtype=np.float64).reshape(-1, 5)
        ground = np.array([w.ground(t) for w in ws], dtype=np.float64).reshape(-1, 2) if calibrated else None
        out = tracker.update(boxes, np.full(len(ws), zone, dtype=np.int32), ground, [density] * tracker.n_zones, t)
    return out


def tracker(n_zones=1, gates=()):
    return FlowTracker(n_zones, tuple(gates), FW, FH)


def group(n, **kw):
    return [Walker(x=100.0 + 60 * i, y=300.0, **kw) for i in range(n)]


def opposing(n_each=4):
    right = [Walker(x=100.0 + 60 * i, y=200.0, vx=60.0, gv=(1.2, 0.0)) for i in range(n_each)]
    left = [Walker(x=500.0 - 60 * i, y=360.0, vx=-60.0, gv=(-1.2, 0.0)) for i in range(n_each)]
    return right + left


# ---- identity -------------------------------------------------------------------------------------

def test_boxes_moving_steadily_should_keep_their_identity_from_frame_to_frame():
    tr = tracker()
    feed(tr, group(4), 0.5)
    ids = sorted(t.id for t in tr._tracks)  # white-box on purpose: the id is the identity
    feed(tr, group(4), 3.0, t0=0.5 + 1 / FPS)
    assert sorted(t.id for t in tr._tracks) == ids and len(ids) == 4


def test_steady_walkers_should_all_be_followed_long_enough_to_measure_a_speed():
    flows, _ = feed(tracker(), group(4), 3.0)
    assert flows[0]["tracked"] == 4


def test_a_short_gap_in_detections_should_not_lose_the_tracks():
    tr = tracker()
    flows, _ = feed(tr, group(4), 3.0, skip={20, 21, 22})
    assert flows[0] is not None and flows[0]["tracked"] == 4 and len(tr._tracks) == 4


# ---- zone speed -----------------------------------------------------------------------------------

def test_zone_speed_should_match_the_ground_speed_of_the_walkers():
    flows, _ = feed(tracker(), group(4, gv=(1.2, 0.0)), 3.0)
    assert flows[0]["speed_mps"] == pytest.approx(1.2, abs=0.05)


def test_zone_speed_should_use_the_length_of_a_diagonal_ground_velocity():
    flows, _ = feed(tracker(), group(4, vx=40.0, vy=40.0, gv=(0.6, 0.8)), 3.0)
    assert flows[0]["speed_mps"] == pytest.approx(1.0, abs=0.05)


def test_zone_speed_should_be_none_until_enough_history_exists():
    flows, _ = feed(tracker(), group(4), 0.4)
    assert flows == [None]


def test_zone_speed_should_be_none_with_fewer_than_three_tracked_people():
    flows, _ = feed(tracker(), group(2), 3.0)
    assert flows == [None]


def test_zone_speed_should_appear_with_exactly_three_tracked_people():
    flows, _ = feed(tracker(), group(3), 3.0)
    assert flows[0]["tracked"] == 3


def test_speeds_above_the_outlier_cap_should_be_ignored():
    walkers = group(3) + [Walker(x=400.0, y=300.0, vx=200.0, gv=(MAX_SPEED_MPS + 1.0, 0.0))]
    flows, _ = feed(tracker(), walkers, 2.0)
    assert flows[0]["tracked"] == 3 and flows[0]["speed_mps"] == pytest.approx(1.2, abs=0.05)


def test_a_zone_where_everyone_is_above_the_cap_should_have_no_flow():
    fast = group(4, vx=200.0, gv=(MAX_SPEED_MPS + 1.0, 0.0))
    assert feed(tracker(), fast, 2.0)[0] == [None]


def test_flow_should_be_none_when_the_camera_has_no_ground_calibration():
    assert feed(tracker(), group(4), 3.0, calibrated=False)[0] == [None]


def test_people_outside_every_zone_should_not_count_towards_a_zone():
    assert feed(tracker(), group(4), 3.0, zone=-1)[0] == [None]


def test_each_zone_should_get_its_own_flow():
    flows, _ = feed(tracker(n_zones=2), group(4), 3.0, zone=1)
    assert flows[0] is None and flows[1]["tracked"] == 4


# ---- direction and pressure -----------------------------------------------------------------------

def test_walkers_going_the_same_way_should_be_fully_aligned_with_a_heading():
    flow = feed(tracker(), group(4, vx=60.0), 3.0)[0][0]
    assert flow["alignment"] == pytest.approx(1.0, abs=0.02) and flow["heading_deg"] == 0


def test_walkers_going_down_the_screen_should_have_a_heading_of_ninety_degrees():
    flow = feed(tracker(), group(4, vx=0.0, vy=60.0, gv=(0.0, -1.2)), 3.0)[0][0]
    assert flow["heading_deg"] == 90


def test_two_groups_walking_in_opposite_directions_should_have_low_alignment_and_no_heading():
    flow = feed(tracker(), opposing(), 3.0)[0][0]
    assert flow["alignment"] < 0.15 and flow["heading_deg"] is None
    assert flow["speed_mps"] == pytest.approx(1.2, abs=0.05)


def test_pressure_should_be_near_zero_when_everyone_moves_alike_and_high_in_counter_flow():
    aligned = feed(tracker(), group(4), 3.0, density=5.0)[0][0]["pressure"]
    counter = feed(tracker(), opposing(), 3.0, density=5.0)[0][0]["pressure"]
    assert aligned < 0.01 and counter > 5.0


def test_a_standing_crowd_should_have_a_speed_near_zero_and_no_heading():
    flow = feed(tracker(), group(4, vx=0.0, gv=(0.0, 0.0)), 3.0)[0][0]
    assert flow["speed_mps"] < 0.05 and flow["heading_deg"] is None


# ---- gates ----------------------------------------------------------------------------------------

def gate(line=((0.0, 0.5), (1.0, 0.5))):
    return Gate("g1", "Gate 1", line, None)


def cross(x, y0, y1, seconds=4.0):
    """Feet walk in a straight line from y0 to y1 over `seconds` at pixel column x."""
    return Walker(path=lambda t: (x, y0 + (y1 - y0) * min(t / seconds, 1.0)))


def totals(stats):
    return stats[0]["total_in"], stats[0]["total_out"]


def test_a_person_walking_to_the_in_side_should_be_counted_once_as_in():
    _, stats = feed(tracker(gates=[gate()]), [cross(300, 180, 300)], 6.0)
    assert totals(stats) == (1, 0)


def test_a_person_walking_to_the_other_side_should_be_counted_once_as_out():
    _, stats = feed(tracker(gates=[gate()]), [cross(300, 300, 180)], 6.0)
    assert totals(stats) == (0, 1)


def test_the_in_side_should_be_the_right_hand_side_of_the_line_direction():
    reversed_line = gate(((1.0, 0.5), (0.0, 0.5)))  # right to left: "in" is now upward on screen
    _, stats = feed(tracker(gates=[reversed_line]), [cross(300, 300, 180)], 6.0)
    assert totals(stats) == (1, 0)


def test_a_person_standing_still_on_one_side_should_never_be_counted():
    _, stats = feed(tracker(gates=[gate()]), [cross(300, 200, 200)], 6.0)
    assert totals(stats) == (0, 0)


def test_a_box_that_jitters_on_the_line_should_not_be_counted():
    wobble = Walker(path=lambda t: (300.0, 240.0 + (3.0 if int(t * FPS) % 2 else -3.0)))
    _, stats = feed(tracker(gates=[gate()]), [wobble], 8.0)
    assert totals(stats) == (0, 0)


def test_a_person_who_jitters_on_the_line_and_then_walks_through_should_count_once():
    def path(t):
        if t < 3.0:
            return 300.0, 235.0 + (4.0 if int(t * FPS) % 2 else -4.0)
        return 300.0, 235.0 + 30.0 * (t - 3.0)
    _, stats = feed(tracker(gates=[gate()]), [Walker(path=path)], 8.0)
    assert totals(stats) == (1, 0)


def test_a_crossing_past_the_end_of_a_short_gate_should_not_be_counted():
    short = gate(((0.4, 0.5), (0.6, 0.5)))  # x from 256 to 384 px
    _, stats = feed(tracker(gates=[short]), [cross(100, 180, 300)], 6.0)
    assert totals(stats) == (0, 0)


def test_two_people_crossing_in_opposite_directions_should_be_counted_separately():
    _, stats = feed(tracker(gates=[gate()]), [cross(200, 180, 300), cross(450, 300, 180)], 6.0)
    assert totals(stats) == (1, 1)


def test_the_same_person_crossing_back_within_the_rearm_time_should_not_be_counted_twice():
    def there_and_back(t):
        steps = int(t * FPS)
        return 300.0, 200.0 + 20.0 * min(steps, 4) - 20.0 * max(0, min(steps - 4, 4))
    _, stats = feed(tracker(gates=[gate()]), [Walker(path=there_and_back)], 2.0)
    assert totals(stats) == (1, 0)


def test_the_per_minute_rate_should_be_the_crossings_over_the_elapsed_time():
    tr = tracker(gates=[gate()])
    feed(tr, [cross(300, 180, 300)], 6.0)                      # the crossing happens near t = 2.7 s
    _, stats = feed(tr, [], 30.0 - 6.0, t0=6.0 + 1 / FPS)
    assert stats[0]["in_per_min"] == pytest.approx(2.0, abs=0.1) and stats[0]["out_per_min"] == 0


def test_the_per_minute_rate_should_not_explode_in_the_first_seconds():
    _, stats = feed(tracker(gates=[gate()]), [cross(300, 180, 300)], 4.0)
    assert stats[0]["in_per_min"] == pytest.approx(6.0, abs=0.2)  # one person over the 10 s minimum window


def test_old_crossings_should_leave_the_rate_but_stay_in_the_totals():
    tr = tracker(gates=[gate()])
    feed(tr, [cross(300, 180, 300)], 6.0)
    _, stats = feed(tr, [], 5.0, t0=80.0)
    assert stats[0]["in_per_min"] == 0 and stats[0]["total_in"] == 1


def test_gate_stats_should_name_the_gate():
    _, stats = feed(tracker(gates=[gate()]), [], 1.0)
    assert stats[0]["id"] == "g1" and totals(stats) == (0, 0)
