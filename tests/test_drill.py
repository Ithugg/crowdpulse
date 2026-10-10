"""backend/drill.py: the drill is a simulated camera whose people go through the real measurement,
level and alert code, and everything it produces is labelled as a drill."""
import numpy as np
import pytest

from backend.alerts import AlertManager
from backend.calibration import SceneGeometry, calibration_from_params
from backend.config import load_settings
from backend.drill import (CYCLE_S, SCRIPTS, DrillCapture, DrillScene, label_alerts, label_plan, label_report,
                           target_density)
from backend.predictor import ZoneTracker
from backend.schemas import config_message
from backend.zones import ZoneCounter
from camera_helpers import make_camera, project

SETTINGS = load_settings()
DRILL = SETTINGS.sources["drill"]
W, H = 960, 540


def camera():
    return calibration_from_params(W, H, DRILL.hfov_deg, DRILL.cam_height_m, DRILL.tilt_deg)


def counter_for(cam):
    return ZoneCounter(DRILL.zones, W, H, SceneGeometry(W, H, DRILL.hfov_deg, cam))


def run_drill(seconds, fps=5.0):
    """One drill on a fake clock through the real counter, tracker and alert manager.
    Returns (alerts with their script time, final states)."""
    cam = camera()
    scene, counter = DrillScene(DRILL, cam), counter_for(cam)
    tracker = ZoneTracker(DRILL.zones, SETTINGS.thresholds, counter.areas_m2)
    manager, raised = AlertManager(SETTINGS.thresholds), []
    for i in range(int(seconds * fps) + 1):
        t = i / fps
        _, counts, peaks, _, _ = counter.measure(scene.step(t))
        states = tracker.update(counts, peaks, t)
        alerts = manager.update(states, t)
        label_alerts(alerts)
        raised += [(t, a) for a in alerts]
    return raised, states


# ---- the virtual camera -----------------------------------------------------------------------------

def test_to_image_should_agree_with_an_independent_projection_of_feet_and_heads():
    cam = make_camera(9.0, 40.0, W, H)
    floor = np.array([[-4.0, 7.0], [0.0, 12.0], [5.0, 17.0]])
    for up in (0.0, 1.7):
        x, y = project(cam, floor[:, 0], floor[:, 1], up)
        assert cam.to_image(floor, up) == pytest.approx(np.stack([x, y], axis=1))


def test_to_image_should_be_undone_by_to_ground():
    cam = camera()
    floor = np.array([[-5.0, 6.5], [0.8, 11.4], [5.4, 17.4]])
    assert cam.to_ground(cam.to_image(floor)) == pytest.approx(floor)


def test_the_drill_source_should_be_a_calibrated_drill_that_is_always_offered():
    assert DRILL.is_drill and DRILL.available and DRILL.cam_height_m and DRILL.tilt_deg
    assert not any(s.is_drill for sid, s in SETTINGS.sources.items() if sid != "drill")


def test_a_drill_without_a_camera_pose_should_refuse_to_start():
    from dataclasses import replace
    with pytest.raises(RuntimeError):
        DrillCapture(replace(DRILL, cam_height_m=None, tilt_deg=None))


# ---- the scripted crowd -----------------------------------------------------------------------------

@pytest.mark.parametrize("t", [0.0, 46.0, 100.0, 170.0])
def test_everyone_in_the_drill_should_stand_inside_a_zone_and_inside_the_frame(t):
    cam = camera()
    scene = DrillScene(DRILL, cam)
    boxes = scene.step(t, limit=None)
    assert (counter_for(cam).assign(boxes) >= 0).all()
    assert boxes[:, 0].min() >= 0 and boxes[:, 2].max() <= W and boxes[:, 1].min() >= 0 and boxes[:, 3].max() <= H


@pytest.mark.parametrize("t", [0.0, 100.0])
def test_the_measured_reading_should_follow_the_script_when_the_crowd_is_measured_like_a_real_one(t):
    cam = camera()
    _, _, peaks, _, _ = counter_for(cam).measure(DrillScene(DRILL, cam).step(t, limit=None))
    for script, peak in zip(SCRIPTS, peaks):
        assert peak == pytest.approx(target_density(script, t), rel=0.2)


def test_the_script_should_end_each_cycle_where_it_began():
    for script in SCRIPTS:
        assert script[0][0] == 0 and script[-1][0] == CYCLE_S
        assert target_density(script, 0.0) == pytest.approx(script[0][1])
        assert target_density(script, CYCLE_S - 1e-6) == pytest.approx(script[0][1], abs=1e-4)


def test_the_drill_frame_should_be_a_colour_picture_of_the_stream_size_with_one_box_per_person():
    capture = DrillCapture(DRILL, W)
    frame, serial, _, _ = capture.read(0)
    assert frame.shape == (H, W, 3) and frame.dtype == np.uint8 and serial == 1
    assert capture.boxes(serial).shape[1] == 5 and len(capture.boxes(serial)) > 50


# ---- through the real level, forecast and alert logic -----------------------------------------------

def test_one_drill_cycle_should_forecast_then_climb_through_every_level_and_clear():
    raised, _ = run_drill(200.0)
    story = [(a["kind"], a["level"]) for _, a in raised]
    wanted = [("level_change", "busy"), ("prediction", "caution"), ("level_change", "caution"),
              ("level_change", "danger"), ("level_change", "critical"), ("cleared", "busy")]
    positions = [story.index(step) for step in wanted]
    assert positions == sorted(positions), story


def test_the_drill_should_reach_the_action_level_inside_the_first_minute():
    raised, _ = run_drill(60.0)
    reached = [t for t, a in raised if a["kind"] == "level_change" and a["level"] == "caution"]
    assert reached and 35.0 < reached[0] < 60.0


def test_only_the_first_zone_should_ever_raise_an_alert():
    raised, _ = run_drill(200.0)
    assert {a["zone_id"] for _, a in raised} == {DRILL.zones[0].id}


# ---- the labels -------------------------------------------------------------------------------------

def test_every_alert_from_a_drill_should_be_marked_and_say_drill_first():
    raised, _ = run_drill(60.0)
    assert raised and all(a["drill"] is True and a["message"].startswith("DRILL: ") for _, a in raised)


def test_a_drill_plan_and_report_should_be_labelled_whoever_wrote_them():
    plan = label_plan({"headline": "Hold the gates", "actions": []})
    report = label_report({"title": "Front Barrier exercise", "summary": "Density peaked at 6.5.", "timeline": []})
    assert plan["headline"] == "DRILL: Hold the gates"
    assert report["title"].startswith("DRILL: ") and report["summary"].startswith("This was a drill: every reading")
    assert report["summary"].endswith("Density peaked at 6.5.")


@pytest.mark.parametrize("written", ["Drill: Front Barrier critical density event", "DRILL - Front Barrier critical density event",
                                     "drill: Front Barrier critical density event"])
def test_a_label_gemini_wrote_itself_should_not_be_doubled(written):
    assert label_report({"title": written, "summary": "x"})["title"] == "DRILL: Front Barrier critical density event"
    assert label_plan({"headline": written})["headline"] == "DRILL: Front Barrier critical density event"


def test_a_headline_that_merely_starts_with_the_word_should_be_kept_whole():
    assert label_plan({"headline": "Drill staff on the barrier release"})["headline"] == "DRILL: Drill staff on the barrier release"


def test_config_message_should_flag_the_drill_and_turn_flow_off_for_it():
    cam = camera()
    msg = config_message(SETTINGS, DRILL, SceneGeometry(W, H, DRILL.hfov_deg, cam), counter_for(cam).areas_m2)
    assert msg["drill"] is True and msg["flow"] is False and msg["gates"] == []
    assert next(s for s in msg["sources"] if s["id"] == "drill")["available"] is True
    assert all(z["area_m2"] and z["capacity"] for z in msg["zones"])


def test_config_message_should_not_flag_a_real_camera_as_a_drill():
    source = next(s for s in SETTINGS.sources.values() if not s.is_drill)
    msg = config_message(SETTINGS, source, SceneGeometry(1280, 720, source.hfov_deg, None), [None] * len(source.zones))
    assert msg["drill"] is False and msg["run"] == 0


# ---- a drill started over is a new session ----------------------------------------------------------

def test_a_drill_started_over_should_begin_a_clean_session_but_the_same_run_should_keep_its_log():
    from backend import main

    hub = main.Hub()
    hub.publish_config({"type": "config", "active_source": "drill", "run": 1})
    hub.publish_event({"type": "alert", "id": "a1"})
    hub.session.frames = 99
    main.last_plan_at["drill:front_barrier"] = (1.0, "caution")

    hub.publish_config({"type": "config", "active_source": "drill", "run": 1})  # same run: nothing is lost
    assert len(hub.backlog) == 1 and hub.session.frames == 99 and main.last_plan_at

    hub.publish_config({"type": "config", "active_source": "drill", "run": 2})  # reset pressed: a new exercise
    assert len(hub.backlog) == 0 and hub.session.frames == 0 and not main.last_plan_at


def test_switching_between_real_cameras_should_still_start_a_new_session():
    from backend import main

    hub = main.Hub()
    hub.publish_config({"type": "config", "active_source": "plaza", "run": 0})
    hub.publish_event({"type": "alert", "id": "a1"})
    hub.publish_config({"type": "config", "active_source": "plaza", "run": 0})
    assert len(hub.backlog) == 1
    hub.publish_config({"type": "config", "active_source": "concourse", "run": 0})
    assert len(hub.backlog) == 0
