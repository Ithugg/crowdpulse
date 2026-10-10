"""backend/render.py: the privacy blur must cover the face however much of the person the frame shows,
and the density tint appears only where the crowd is at least busy."""
import numpy as np

from backend.render import HeatmapRenderer, pixelate_heads

W, H = 960, 540
CRITICAL = 6.0


def tinted(density):
    """Whether the heatmap changed a noise frame, for a tight group of people at one local density."""
    frame = np.random.default_rng(1).integers(0, 256, (H, W, 3), dtype=np.uint8)
    before = frame.copy()
    boxes = np.array([[400 + 30 * i, 200, 430 + 30 * i, 300, 0.9] for i in range(6)], dtype=np.float32)
    HeatmapRenderer().draw(frame, boxes, np.full(len(boxes), density), CRITICAL)
    return bool((frame != before).any())


def test_heatmap_should_leave_the_frame_untouched_when_the_crowd_is_below_busy():
    assert not tinted(1.2)


def test_heatmap_should_tint_the_frame_when_the_crowd_is_busy_or_denser():
    assert tinted(2.4)
    assert tinted(6.0)


def test_heatmap_should_leave_the_frame_untouched_when_nobody_is_in_view():
    frame = np.random.default_rng(1).integers(0, 256, (H, W, 3), dtype=np.uint8)
    before = frame.copy()
    HeatmapRenderer().draw(frame, np.zeros((0, 5), dtype=np.float32), np.zeros(0), CRITICAL)
    assert (frame == before).all()


def blurred_rows(box):
    """Rows of the frame the blur touched, for one box on a frame of random noise."""
    frame = np.random.default_rng(0).integers(0, 256, (H, W, 3), dtype=np.uint8)
    before = frame.copy()
    pixelate_heads(frame, np.array([box + [0.9]], dtype=np.float32))
    return np.flatnonzero((frame != before).any(axis=(1, 2)))


def test_pixelate_heads_should_blur_only_the_top_of_the_box_when_the_whole_body_is_in_view():
    rows = blurred_rows([400, 100, 480, 400])  # 80 wide, 300 tall, standing
    assert rows.min() == 100
    assert 140 <= rows.max() <= 170  # about a fifth of the height, never the torso


def test_pixelate_heads_should_blur_the_whole_box_when_a_face_close_to_the_lens_is_cut_off_by_the_frame():
    rows = blurred_rows([300, 350, 520, H])  # 220 wide, 190 tall, ends at the bottom edge
    assert rows.min() == 350
    assert rows.max() == H - 1


def test_pixelate_heads_should_keep_to_the_head_when_a_standing_person_is_cut_off_at_the_waist():
    rows = blurred_rows([400, 100, 600, H])  # 200 wide, 440 tall: head, chest and waist are visible
    assert rows.max() < 100 + 0.5 * 440


def test_pixelate_heads_should_blur_deeper_when_the_side_of_the_frame_hides_half_the_person():
    inside = blurred_rows([400, 100, 440, 400])
    at_edge = blurred_rows([0, 100, 40, 400])  # same box, but the frame's left edge cuts it
    assert at_edge.max() > inside.max()
