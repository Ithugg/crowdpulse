"""backend/calibration.py: camera fit, floor mapping, areas, usable boxes, local density, SceneGeometry.
The synthetic camera in camera_helpers.py projects people from first principles, independent of the backend."""
import math

import numpy as np
import pytest

from backend.calibration import (MIN_SAMPLES, SceneGeometry, fit_calibration, local_density, usable_boxes)
from camera_helpers import H, HFOV, W, make_camera, person_boxes, project, random_people


# ---- fit_calibration ------------------------------------------------------------------------------

@pytest.mark.parametrize("height, tilt, noise, seed", [
    (6.0, 25.0, 0.0, 1), (6.0, 25.0, 0.02, 2), (4.0, 15.0, 0.02, 3), (3.0, 10.0, 0.02, 4), (10.0, 40.0, 0.02, 5),
])
def test_fit_should_recover_camera_height_and_tilt_from_person_boxes(height, tilt, noise, seed):
    boxes = random_people(make_camera(height, tilt), 600, seed, noise, forward_range=(6.0, 35.0))
    fit = fit_calibration(boxes, W, H, HFOV)
    assert fit is not None
    assert fit.cam_height_m == pytest.approx(height, rel=0.10)
    assert math.degrees(fit.tilt_rad) == pytest.approx(tilt, abs=3.0)


def test_fit_should_report_a_small_error_and_the_sample_count_for_a_clean_fit():
    fit = fit_calibration(random_people(make_camera(), 400, seed=7), W, H)
    assert fit.fit_error < 0.05 and MIN_SAMPLES <= fit.samples <= 400


def test_fit_should_return_none_when_there_are_too_few_whole_body_boxes():
    assert fit_calibration(random_people(make_camera(), MIN_SAMPLES - 60, seed=1), W, H) is None


def test_fit_should_return_none_when_there_are_no_boxes():
    assert fit_calibration(np.zeros((0, 5)), W, H) is None


def test_fit_should_return_none_when_box_heights_do_not_follow_any_camera():
    rng = np.random.default_rng(3)
    n = 400
    feet, tall = rng.uniform(300, 700, n), rng.uniform(40, 300, n)  # height unrelated to where the feet are
    x = rng.uniform(100, 1100, n)
    boxes = np.stack([x, feet - tall, x + tall * 0.35, feet, np.full(n, 0.9)], axis=1)
    assert fit_calibration(boxes, W, H) is None


# ---- to_ground ------------------------------------------------------------------------------------

def test_to_ground_should_invert_the_projection_of_floor_points():
    cam = make_camera()
    side, fwd = np.array([-4.0, 0.0, 2.0, 7.5]), np.array([8.0, 12.0, 15.0, 25.0])
    px, py = project(cam, side, fwd)
    ground = cam.to_ground(np.stack([px, py], axis=1))
    assert np.allclose(ground[:, 0], side, atol=1e-6) and np.allclose(ground[:, 1], fwd, atol=1e-6)


def test_to_ground_should_put_the_image_centre_at_height_over_tan_tilt_in_front_of_the_camera():
    cam = make_camera(6.0, 25.0)
    assert cam.to_ground(np.array([[W / 2, H / 2]]))[0] == pytest.approx([0.0, 6.0 / math.tan(math.radians(25))])


def test_to_ground_should_put_lower_rows_closer_to_the_camera():
    cam = make_camera()
    forward = cam.to_ground(np.array([[W / 2, 300.0], [W / 2, 450.0], [W / 2, 650.0]]))[:, 1]
    assert forward[0] > forward[1] > forward[2] > 0


def test_to_ground_should_return_nan_above_the_horizon():
    cam = make_camera(6.0, 10.0)
    above, below = cam.horizon_y - 20, cam.horizon_y + 200
    out = cam.to_ground(np.array([[W / 2, above], [W / 2, below]]))
    assert np.isnan(out[0]).all() and np.isfinite(out[1]).all() and 0 < out[1, 1] < 40


def test_to_ground_should_put_points_right_of_centre_at_positive_sideways_metres():
    cam = make_camera()
    assert cam.to_ground(np.array([[W / 2 + 200, 500.0]]))[0, 0] > 0 > cam.to_ground(np.array([[W / 2 - 200, 500.0]]))[0, 0]


def test_horizon_should_sit_where_a_ray_parallel_to_the_floor_hits_the_image():
    cam = make_camera(6.0, 10.0)
    far_x, far_y = project(cam, 0.0, 1.0e6)
    assert cam.horizon_y == pytest.approx(float(far_y), abs=0.01)


# ---- row_area_m2 / mask_area_m2 -------------------------------------------------------------------

def test_row_area_should_be_zero_above_the_horizon_and_positive_below_it():
    cam = make_camera(6.0, 10.0)
    area = cam.row_area_m2()
    horizon = int(cam.horizon_y)
    assert np.all(area[: horizon + 1] == 0.0)  # rows beyond MAX_RANGE_M (just below it) are zero as well
    assert np.all(area[480:] > 0.0)


def test_row_area_should_grow_with_distance():
    area = make_camera().row_area_m2()
    assert area[300] > area[500] > area[700] > 0


def test_mask_area_should_match_the_analytic_floor_area_of_a_full_width_band():
    cam = make_camera()
    near_row, far_row = (int(round(float(project(cam, 0.0, f)[1]))) for f in (7.0, 12.0))
    mask = np.zeros((H, W), dtype=bool)
    mask[far_row:near_row + 1, :] = True
    sin, cos, hgt, f_px = math.sin(cam.tilt_rad), math.cos(cam.tilt_rad), cam.cam_height_m, cam.focal_px
    integral = lambda f: cos * f * f / 2 + hgt * sin * f  # noqa: E731  area = (W / f_px) * integral of depth dF
    expected = (W / f_px) * (integral(12.0) - integral(7.0))
    assert cam.mask_area_m2(mask) == pytest.approx(expected, rel=0.03)


def test_mask_area_should_be_none_when_the_mask_reaches_beyond_thirty_metres():
    assert make_camera().mask_area_m2(np.ones((H, W), dtype=bool)) is None


def test_mask_area_should_be_none_when_the_mask_reaches_above_the_horizon():
    cam = make_camera(6.0, 10.0)
    mask = np.zeros((H, W), dtype=bool)
    mask[:100, :] = True
    assert cam.mask_area_m2(mask) is None


def test_mask_area_should_be_positive_for_a_near_field_mask():
    mask = np.zeros((H, W), dtype=bool)
    mask[600:700, 200:1000] = True
    assert make_camera().mask_area_m2(mask) > 1.0


# ---- usable_boxes ---------------------------------------------------------------------------------

def test_usable_boxes_should_keep_a_whole_upright_confident_person():
    box = np.array([[500, 300, 560, 450, 0.9]])
    assert len(usable_boxes(box, W, H)) == 1


@pytest.mark.parametrize("box", [
    [0, 300, 60, 450, 0.9], [2, 300, 60, 450, 0.9],          # touches the left edge
    [500, 0, 560, 150, 0.9],                                   # touches the top edge
    [W - 40, 300, W - 1, 450, 0.9],                            # touches the right edge
    [500, 600, 560, H, 0.9], [500, 600, 560, H - 2, 0.9],      # touches the bottom edge
])
def test_usable_boxes_should_drop_boxes_touching_the_frame_edge(box):
    assert len(usable_boxes(np.array([box], dtype=float), W, H)) == 0


@pytest.mark.parametrize("box, why", [
    ([500, 300, 650, 450, 0.9], "square, not a standing person"),
    ([500, 300, 510, 450, 0.9], "far too thin"),
    ([500, 300, 560, 450, 0.2], "low confidence"),
])
def test_usable_boxes_should_drop_oddly_shaped_or_unsure_boxes(box, why):
    assert len(usable_boxes(np.array([box], dtype=float), W, H)) == 0, why


def test_usable_boxes_should_filter_a_mixed_batch_and_keep_only_the_good_ones():
    boxes = np.array([[500, 300, 560, 450, 0.9], [0, 300, 60, 450, 0.9], [700, 300, 760, 450, 0.8]])
    assert usable_boxes(boxes, W, H).tolist() == [[500, 300, 560, 450, 0.9], [700, 300, 760, 450, 0.8]]


def test_usable_boxes_should_cope_with_an_empty_input():
    assert len(usable_boxes(np.zeros((0, 5)), W, H)) == 0


# ---- local_density --------------------------------------------------------------------------------

def test_local_density_should_read_four_per_square_metre_inside_a_half_metre_grid():
    gx, gy = np.meshgrid(np.arange(21) * 0.5, np.arange(21) * 0.5)
    rho = local_density(np.stack([gx.ravel(), gy.ravel()], axis=1)).reshape(21, 21)
    assert rho[10, 10] == pytest.approx(4.0, rel=0.02) and rho[8:13, 8:13].min() > 3.9


def test_local_density_should_fall_off_at_the_edge_of_the_crowd():
    gx, gy = np.meshgrid(np.arange(21) * 0.5, np.arange(21) * 0.5)
    rho = local_density(np.stack([gx.ravel(), gy.ravel()], axis=1)).reshape(21, 21)
    assert rho[0, 0] < 0.5 * rho[10, 10]


def test_local_density_should_read_a_lone_person_as_one_over_pi():
    assert local_density(np.array([[3.0, 7.0]]))[0] == pytest.approx(1 / math.pi)


def test_local_density_should_not_count_people_far_apart_as_a_crowd():
    rho = local_density(np.array([[0.0, 0.0], [10.0, 0.0]]))
    assert rho == pytest.approx([1 / math.pi] * 2, abs=1e-6)


def test_local_density_should_return_an_empty_array_for_no_people():
    out = local_density(np.zeros((0, 2)))
    assert out.shape == (0,)


def test_local_density_should_ignore_people_whose_position_is_unknown():
    pts = np.array([[0.0, 0.0], [0.5, 0.0], [np.nan, np.nan]])
    rho = local_density(pts)
    assert np.isfinite(rho).all() and rho[0] == pytest.approx(local_density(pts[:2])[0])


def test_local_density_should_scale_with_the_kernel_radius_so_that_an_even_crowd_is_unchanged():
    gx, gy = np.meshgrid(np.arange(41) * 0.5, np.arange(41) * 0.5)
    pts = np.stack([gx.ravel(), gy.ravel()], axis=1)
    centre = 20 * 41 + 20
    assert local_density(pts, radius_m=2.0)[centre] == pytest.approx(4.0, rel=0.02)


# ---- SceneGeometry --------------------------------------------------------------------------------

def test_size_mode_should_be_used_when_there_is_no_calibration():
    assert SceneGeometry(W, H, HFOV, None).mode == "size"


def test_ground_mode_should_be_used_when_a_calibration_is_given():
    assert SceneGeometry(W, H, HFOV, make_camera()).mode == "ground"


def test_size_mode_should_place_a_wider_box_closer_than_a_narrow_one():
    wide, narrow = np.array([[600, 200, 700, 500, 0.9]]), np.array([[600, 200, 650, 500, 0.9]])
    geo = SceneGeometry(W, H, HFOV, None)
    assert geo.positions(wide)[0, 1] < geo.positions(narrow)[0, 1]


def test_size_mode_should_halve_the_distance_when_the_box_is_twice_as_wide():
    geo = SceneGeometry(W, H, HFOV, None)
    near, far = geo.positions(np.array([[0, 0, 100, 300, 0.9], [0, 0, 50, 300, 0.9]]))[:, 1]
    assert far == pytest.approx(2 * near)


def test_size_mode_should_follow_the_pinhole_law_for_half_metre_shoulders():
    geo = SceneGeometry(W, H, HFOV, None)
    focal = (W / 2) / math.tan(math.radians(HFOV / 2))
    assert geo.positions(np.array([[100, 0, 200, 300, 0.9]]))[0, 1] == pytest.approx(focal * 0.5 / 100)


def test_size_mode_should_put_boxes_right_of_centre_at_positive_sideways_metres():
    geo = SceneGeometry(W, H, HFOV, None)
    out = geo.positions(np.array([[900, 0, 1000, 300, 0.9], [300, 0, 400, 300, 0.9]]))
    assert out[0, 0] > 0 > out[1, 0]


def test_ground_mode_should_place_people_where_they_stand_on_the_floor():
    cam = make_camera()
    boxes = person_boxes(cam, [-3.0, 2.0], [10.0, 18.0])
    assert np.allclose(SceneGeometry(W, H, HFOV, cam).positions(boxes), [[-3.0, 10.0], [2.0, 18.0]], atol=1e-6)


def test_positions_should_be_an_empty_array_for_no_boxes_in_either_mode():
    for calibration in (None, make_camera()):
        assert SceneGeometry(W, H, HFOV, calibration).positions(np.zeros((0, 5))).shape == (0, 2)
