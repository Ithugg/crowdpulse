"""backend/config.py and backend/schemas.py: the real config/sources.yaml is valid, and every message the
server sends can be serialised as strict JSON (no NaN) in the awkward cases (unknown areas, no flow)."""
import json
from pathlib import Path

import numpy as np
import pytest

from backend.calibration import SceneGeometry, calibration_from_params
from backend.config import CONFIG_PATH, load_settings, resolve_source
from backend.predictor import ZoneTracker
from backend.schemas import calibration_message, config_message, state_message, zone_message
from backend.zones import LEVELS, ZoneCounter
from camera_helpers import make_camera, person_boxes
from crowd_helpers import DT, RAMP, THRESHOLDS, one_zone, run

MINIMAL = Path(__file__).resolve().parent / "data" / "minimal_sources.yaml"
SETTINGS = load_settings()
SOURCES = list(SETTINGS.sources.values())


def strict(message):
    """Round-trips through strict JSON: raises on NaN / Infinity or anything not serialisable."""
    return json.loads(json.dumps(message, allow_nan=False))


def geometry_for(source, frame_w=1280, frame_h=720):
    calibrated = source.cam_height_m is not None and source.tilt_deg is not None
    calib = calibration_from_params(frame_w, frame_h, source.hfov_deg, source.cam_height_m, source.tilt_deg) \
        if calibrated else None
    return SceneGeometry(frame_w, frame_h, source.hfov_deg, calib)


def polygon_area(points):
    x, y = np.array(points).T
    return abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))) / 2


# ---- the real config/sources.yaml -----------------------------------------------------------------

def test_the_real_config_file_should_exist_and_define_sources():
    assert CONFIG_PATH.exists() and len(SOURCES) >= 1


def test_the_default_source_should_be_one_of_the_configured_sources():
    assert SETTINGS.default_source in SETTINGS.sources


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_every_source_should_have_at_least_one_zone_with_a_unique_id(source):
    ids = [z.id for z in source.zones]
    assert len(ids) >= 1 and len(set(ids)) == len(ids)


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_every_zone_polygon_should_be_a_real_shape_inside_the_unit_square(source):
    for zone in source.zones:
        assert len(zone.polygon) >= 3
        assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in zone.polygon), zone.id
        assert polygon_area(zone.polygon) > 0.001, zone.id


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_every_gate_should_reference_an_existing_zone_and_lie_inside_the_frame(source):
    zone_ids = {z.id for z in source.zones}
    for gate in source.gates:
        assert gate.zone in zone_ids, f"gate {gate.id} feeds unknown zone {gate.zone}"
        assert len(gate.line) == 2 and all(0.0 <= v <= 1.0 for p in gate.line for v in p)
        assert gate.line[0] != gate.line[1]


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_a_moving_camera_should_not_declare_gates(source):
    assert not (source.moving_camera and source.gates)


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_stored_calibration_should_have_both_numbers_and_sensible_values_or_neither(source):
    assert (source.cam_height_m is None) == (source.tilt_deg is None)
    if source.cam_height_m is not None:
        assert 1.0 < source.cam_height_m < 60.0 and 0.0 < source.tilt_deg < 90.0


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_every_source_should_have_a_known_kind_and_measure_mode_and_a_sane_lens(source):
    assert source.kind in ("webcam", "video", "drill") and source.measure in ("auto", "size")
    assert 20.0 < source.hfov_deg < 150.0


def test_the_thresholds_should_be_strictly_increasing_from_zero():
    steps = SETTINGS.thresholds.steps
    assert 0 < steps[0] < steps[1] < steps[2] < steps[3]
    assert SETTINGS.thresholds.exposure_alert_s > 0


def test_the_thresholds_should_match_the_documented_research_levels():
    assert SETTINGS.thresholds.steps == (2.0, 4.0, 5.0, 6.0) and SETTINGS.thresholds.exposure_alert_s == 360


def test_the_stream_and_detector_settings_should_be_usable_numbers():
    assert SETTINGS.max_fps > 0 and SETTINGS.stream_width > 0 and 1 <= SETTINGS.jpeg_quality <= 100
    assert 0.0 < SETTINGS.detector.conf < 1.0 and SETTINGS.detector.imgsz > 0


# ---- load_settings defaults and helpers -----------------------------------------------------------

def test_a_source_without_zones_should_get_four_grid_zones_covering_the_frame():
    zones = load_settings(MINIMAL).sources["lobby"].zones
    assert [z.id for z in zones] == ["zone_a", "zone_b", "zone_c", "zone_d"]
    assert sum(polygon_area(z.polygon) for z in zones) == pytest.approx(1.0)


def test_missing_sections_should_fall_back_to_the_default_thresholds_and_the_first_source():
    settings = load_settings(MINIMAL)
    assert settings.thresholds.steps == (2.0, 4.0, 5.0, 6.0) and settings.default_source == "lobby"
    assert settings.sources["lobby"].kind == "video" and settings.sources["lobby"].hfov_deg == 60.0


def test_explicit_source_fields_should_be_parsed_with_their_types():
    stage = load_settings(MINIMAL).sources["stage"]
    assert (stage.hfov_deg, stage.cam_height_m, stage.tilt_deg, stage.moving_camera) == (75.0, 4.5, 20, True)
    assert stage.gates[0].zone == "front" and stage.gates[0].line == ((0.1, 0.5), (0.9, 0.5))


def test_resolve_source_should_accept_a_configured_id_a_camera_index_or_a_file_path():
    assert resolve_source(SETTINGS, SOURCES[0].id) is SOURCES[0]
    cam = resolve_source(SETTINGS, "2")
    assert (cam.kind, cam.path, len(cam.zones)) == ("webcam", 2, 3)
    assert resolve_source(SETTINGS, "some/dir/clip.mp4").id == "clip"


# ---- config_message -------------------------------------------------------------------------------

def message_for(source, areas=None, geometry=None):
    areas = areas if areas is not None else [None] * len(source.zones)
    return config_message(SETTINGS, source, geometry or geometry_for(source), areas)


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_config_message_should_serialise_as_strict_json_when_every_area_is_unknown(source):
    assert strict(message_for(source))["type"] == "config"


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_config_message_should_serialise_as_strict_json_with_measured_areas(source):
    areas = [round(10.0 + 7.5 * i, 1) for i in range(len(source.zones))]
    assert strict(message_for(source, areas))["zones"][0]["area_m2"] == 10.0


def test_config_message_should_serialise_when_only_some_zone_areas_are_known():
    source = next(s for s in SOURCES if len(s.zones) >= 3)
    areas = [25.0, None] + [None] * (len(source.zones) - 2)
    zones = strict(message_for(source, areas))["zones"]
    assert (zones[0]["area_m2"], zones[0]["capacity"], zones[1]["area_m2"], zones[1]["capacity"]) == (25.0, 100, None, None)


def test_config_message_should_list_all_five_levels_with_their_starting_densities():
    levels = strict(message_for(SOURCES[0]))["levels"]
    assert [l["id"] for l in levels] == list(LEVELS) and [l["min"] for l in levels] == [0.0, 2.0, 4.0, 5.0, 6.0]
    assert all(l["label"] and l["what"] and l["source"] for l in levels)


def test_config_message_should_list_every_source_and_mark_the_webcam_available():
    msg = strict(message_for(SOURCES[0]))
    assert [s["id"] for s in msg["sources"]] == list(SETTINGS.sources)
    assert all(isinstance(s["available"], bool) for s in msg["sources"])
    assert all(s["available"] for s in msg["sources"] if s["kind"] == "webcam")


def test_config_message_should_include_gates_and_flow_for_a_fixed_camera():
    source = next(s for s in SOURCES if s.gates and not s.moving_camera)
    msg = strict(message_for(source))
    assert msg["flow"] is True and [g["id"] for g in msg["gates"]] == [g.id for g in source.gates]
    assert msg["gates"][0]["zone_id"] == source.gates[0].zone


def test_config_message_should_drop_gates_and_flow_for_a_moving_camera():
    source = next(s for s in SOURCES if s.moving_camera)
    msg = strict(message_for(source))
    assert msg["flow"] is False and msg["gates"] == []


def test_calibration_message_should_describe_ground_and_size_modes():
    ground = calibration_message(SOURCES[0], SceneGeometry(1280, 720, 60.0, make_camera(6.04, 25.2)))
    size = calibration_message(SOURCES[0], SceneGeometry(1280, 720, 60.0, None))
    assert (ground["mode"], ground["cam_height_m"], ground["tilt_deg"]) == ("ground", 6.0, 25)
    assert (size["mode"], size["cam_height_m"], size["tilt_deg"]) == ("size", None, None)


# ---- state_message --------------------------------------------------------------------------------

def states_after(density_at, seconds, zones=1, areas=None):
    tracker = ZoneTracker(tuple(one_zone() for _ in range(zones)), THRESHOLDS, areas)
    last = None
    for i in range(int(seconds / DT) + 1):
        last = tracker.update([7] * zones, [density_at(i * DT)] * zones, i * DT)
    return last


def build(states, **kw):
    base = dict(seq=1, source_id="concourse", fps=14.96, inference_ms=21.4, mode="ground", frame_w=1280,
                frame_h=720, total_count=len(states) * 7, states=states, overlay={"boxes": True})
    return state_message(**{**base, **kw})


def test_state_message_should_serialise_with_unknown_areas_and_no_flows():
    msg = strict(build(states_after(lambda t: 2.5, 10)))
    zone = msg["zones"][0]
    assert zone["avg_density"] is None and msg["gates"] == []
    assert zone["speed_mps"] is None and zone["heading_deg"] is None and zone["pressure"] is None


def test_state_message_should_serialise_with_known_areas_and_flows():
    states = states_after(lambda t: 2.5, 10, zones=2, areas=[30.0, 12.5])
    flows = [None, {"speed_mps": 1.2, "alignment": 0.9, "pressure": 0.1, "heading_deg": None, "tracked": 5}]
    msg = strict(build(states, flows=flows, gates=[{"id": "g", "in_per_min": 2.0, "out_per_min": 0.0,
                                                    "total_in": 3, "total_out": 0}]))
    assert msg["zones"][0]["avg_density"] == pytest.approx(7 / 30.0, abs=0.01)
    assert msg["zones"][0]["speed_mps"] is None and msg["zones"][1]["speed_mps"] == 1.2


def test_state_message_should_report_the_worst_zone_as_the_overall_level():
    states = states_after(lambda t: 6.5, 10, zones=2)
    states[0].level, states[1].level = "busy", "danger"
    assert build(states)["overall_level"] == "danger"


def test_state_message_should_report_normal_when_there_are_no_zones():
    assert strict(build([]))["overall_level"] == "normal"


def test_state_message_should_carry_the_forecast_and_exposure_fields_as_plain_numbers():
    tracker = ZoneTracker((one_zone(),), THRESHOLDS)
    for _ in run(tracker, RAMP, 150):
        pass
    zone = strict(build(tracker.states))["zones"][0]
    assert isinstance(zone["eta_s"], int) and zone["eta_level"] in LEVELS and isinstance(zone["above_safe_s"], int)
    assert zone["history"] and all(isinstance(v, float) for v in zone["history"])


def test_zone_message_should_use_none_for_every_flow_field_when_there_is_no_flow():
    zone = zone_message(states_after(lambda t: 1.0, 5)[0])
    assert [zone[k] for k in ("speed_mps", "heading_deg", "alignment", "pressure")] == [None] * 4


def test_state_message_should_stay_finite_when_a_person_is_above_the_horizon():
    """A box whose feet are above the horizon has no floor position (NaN); it must not leak into the message."""
    cam = make_camera(6.0, 10.0)
    zones = (one_zone(),)
    counter = ZoneCounter(zones, 1280, 720, SceneGeometry(1280, 720, 60.0, cam))
    sky = np.array([[600.0, 20.0, 640.0, int(cam.horizon_y) - 30.0, 0.9]], dtype=np.float32)
    boxes = np.concatenate([person_boxes(cam, [0.0, 0.5], [12.0, 12.0]).astype(np.float32), sky])
    _, counts, peaks, _, _ = counter.measure(boxes)
    tracker = ZoneTracker(zones, THRESHOLDS, counter.areas_m2)
    states = tracker.update(counts, peaks, 0.0)
    assert np.isfinite(peaks).all()
    strict(build(states, total_count=len(boxes)))
