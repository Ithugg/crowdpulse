"""backend/zones.py: density levels with hysteresis, and assigning detections to rectangular zones."""
import numpy as np
import pytest

from backend.calibration import SceneGeometry
from backend.config import Thresholds, Zone
from backend.zones import CAUTION, BUSY, CRITICAL, DANGER, NORMAL, ZoneCounter, anchor_points, level_for
from camera_helpers import W, H, make_camera, person_boxes

T = Thresholds()


def rect(x0, y0, x1, y1):
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def box(x1, y1, x2, y2, conf=0.9):
    return [x1, y1, x2, y2, conf]


# ---- level_for: thresholds ------------------------------------------------------------------------

@pytest.mark.parametrize("density, expected", [
    (0.0, NORMAL), (1.99, NORMAL), (2.0, BUSY), (3.99, BUSY),
    (4.0, CAUTION), (4.99, CAUTION), (5.0, DANGER), (5.99, DANGER), (6.0, CRITICAL), (12.0, CRITICAL),
])
def test_level_for_should_switch_exactly_at_each_threshold_when_coming_from_normal(density, expected):
    assert level_for(density, T) == expected


def test_level_for_should_use_the_thresholds_it_is_given_when_they_are_not_the_defaults():
    custom = Thresholds(busy=1.0, caution=2.0, danger=3.0, critical=4.0)
    assert [level_for(d, custom) for d in (0.99, 1.0, 2.0, 3.0, 4.0)] == [NORMAL, BUSY, CAUTION, DANGER, CRITICAL]


# ---- level_for: hysteresis ------------------------------------------------------------------------

def test_level_for_should_stay_in_caution_when_density_dips_just_below_four():
    assert level_for(3.9, T, previous=CAUTION) == CAUTION


def test_level_for_should_stay_in_caution_until_density_is_clearly_below_four():
    assert level_for(3.61, T, previous=CAUTION) == CAUTION


def test_level_for_should_step_down_to_busy_when_density_is_clearly_below_four():
    assert level_for(3.59, T, previous=CAUTION) == BUSY


@pytest.mark.parametrize("previous, density, expected", [
    (BUSY, 1.9, BUSY), (BUSY, 1.7, NORMAL),
    (DANGER, 4.6, DANGER), (DANGER, 4.4, CAUTION),
    (CRITICAL, 5.5, CRITICAL), (CRITICAL, 5.3, DANGER),
])
def test_level_for_should_hold_a_level_inside_its_margin_and_leave_it_outside(previous, density, expected):
    assert level_for(density, T, previous=previous) == expected


def test_level_for_should_not_use_hysteresis_when_density_rises():
    assert level_for(4.0, T, previous=BUSY) == CAUTION


def test_level_for_should_use_the_margin_it_is_given():
    assert level_for(3.7, T, previous=CAUTION, margin=0.5) == CAUTION
    assert level_for(3.9, T, previous=CAUTION, margin=0.0) == BUSY


# ---- level_for: multi-level jumps -----------------------------------------------------------------

def test_level_for_should_jump_several_levels_up_when_density_leaps():
    assert level_for(7.0, T, previous=NORMAL) == CRITICAL
    assert level_for(4.5, T, previous=NORMAL) == CAUTION


def test_level_for_should_jump_several_levels_down_when_density_collapses():
    assert level_for(0.5, T, previous=CRITICAL) == NORMAL
    assert level_for(2.5, T, previous=CRITICAL) == BUSY


# ---- anchor_points / assign -----------------------------------------------------------------------

def test_anchor_points_should_be_the_bottom_centre_of_each_box():
    pts = anchor_points(np.array([box(10, 20, 30, 80)], dtype=np.float32))
    assert pts.tolist() == [[20.0, 80.0]]


def test_anchor_points_should_return_an_empty_array_when_there_are_no_boxes():
    assert anchor_points(np.zeros((0, 5))).shape == (0, 2)


@pytest.fixture
def two_zones():
    zones = (Zone("a", "A", rect(0.0, 0.0, 0.5, 1.0)), Zone("b", "B", rect(0.5, 0.0, 1.0, 0.5)))
    return ZoneCounter(zones, 100, 100)


def test_assign_should_return_the_zone_each_box_stands_in(two_zones):
    boxes = np.array([box(10, 10, 30, 60), box(60, 10, 80, 40)], dtype=np.float32)
    assert two_zones.assign(boxes).tolist() == [0, 1]


def test_assign_should_use_the_feet_not_the_centre_of_the_box(two_zones):
    tall = np.array([box(60, 5, 80, 90)], dtype=np.float32)  # head in zone B, feet below B (outside every zone)
    assert two_zones.assign(tall).tolist() == [-1]


def test_assign_should_give_minus_one_when_a_box_is_outside_every_zone(two_zones):
    outside = np.array([box(60, 60, 80, 90)], dtype=np.float32)  # lower-right quadrant has no zone
    assert two_zones.assign(outside).tolist() == [-1]


def test_assign_should_return_an_empty_int_array_when_there_are_no_boxes(two_zones):
    out = two_zones.assign(np.zeros((0, 5)))
    assert out.shape == (0,) and out.dtype == np.int32


def test_assign_should_clip_boxes_that_extend_past_the_frame(two_zones):
    off = np.array([box(-30, -10, -10, 50)], dtype=np.float32)  # clipped to the left edge, inside zone A
    assert two_zones.assign(off).tolist() == [0]


# ---- counts ---------------------------------------------------------------------------------------

def test_counts_should_count_boxes_per_zone_and_ignore_those_outside(two_zones):
    assert two_zones.counts(np.array([0, 0, 1, -1, -1, 0])) == [3, 1]


def test_counts_should_be_all_zero_when_there_are_no_boxes(two_zones):
    assert two_zones.counts(two_zones.assign(np.zeros((0, 5)))) == [0, 0]


# ---- measure --------------------------------------------------------------------------------------

def test_measure_should_report_zero_density_and_empty_arrays_when_there_are_no_boxes(two_zones):
    idx, counts, peaks, rho, pos = two_zones.measure(np.zeros((0, 5)))
    assert (len(idx), counts, peaks, len(rho), pos.shape) == (0, [0, 0], [0.0, 0.0], 0, (0, 2))


def test_measure_should_ignore_a_box_outside_every_zone_when_counting_and_taking_peaks(two_zones):
    boxes = np.array([box(60, 60, 80, 90)], dtype=np.float32)
    idx, counts, peaks, rho, _ = two_zones.measure(boxes)
    assert idx.tolist() == [-1] and counts == [0, 0] and peaks == [0.0, 0.0] and len(rho) == 1


def test_measure_should_read_a_lone_person_as_a_third_of_a_person_per_square_metre():
    cam = make_camera()
    zones = (Zone("a", "A", rect(0, 0, 1, 1)),)
    counter = ZoneCounter(zones, W, H, SceneGeometry(W, H, 60.0, cam))
    _, counts, peaks, _, _ = counter.measure(person_boxes(cam, 0.0, 14.0).astype(np.float32))
    assert counts == [1] and peaks[0] == pytest.approx(1 / np.pi, abs=1e-3)


def test_measure_should_find_the_packed_zone_denser_than_the_empty_one():
    cam = make_camera()
    left_half, right_half = Zone("l", "L", rect(0, 0, 0.5, 1)), Zone("r", "R", rect(0.5, 0, 1, 1))
    counter = ZoneCounter((left_half, right_half), W, H, SceneGeometry(W, H, 60.0, cam))
    gx, gz = np.meshgrid(np.arange(-5.0, -3.0, 0.5), np.arange(12.0, 14.0, 0.5))  # 0.5 m grid on the left
    boxes = person_boxes(cam, np.append(gx.ravel(), 8.0), np.append(gz.ravel(), 14.0)).astype(np.float32)
    _, counts, peaks, _, _ = counter.measure(boxes)
    assert counts == [16, 1]
    assert peaks[0] > 2.0 > peaks[1]


def test_zone_areas_should_be_unknown_without_a_ground_calibration(two_zones):
    assert two_zones.areas_m2 == [None, None]


def test_zone_areas_should_be_measured_in_square_metres_with_a_calibration():
    cam = make_camera()
    near = Zone("n", "Near", rect(0.0, 0.6, 1.0, 1.0))
    counter = ZoneCounter((near,), W, H, SceneGeometry(W, H, 60.0, cam))
    assert counter.areas_m2[0] is not None and counter.areas_m2[0] > 10.0


def test_zone_area_should_be_unknown_when_the_zone_reaches_beyond_thirty_metres():
    cam = make_camera()
    whole = Zone("w", "Whole frame", rect(0, 0, 1, 1))
    assert ZoneCounter((whole,), W, H, SceneGeometry(W, H, 60.0, cam)).areas_m2 == [None]
