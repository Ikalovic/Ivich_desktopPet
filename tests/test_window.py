from desktop_pet.interaction import (
    DragBehaviorTracker,
    classify_drag_behavior,
)


def test_classify_drag_behavior_prefers_horizontal_drag() -> None:
    assert classify_drag_behavior(delta_x=12, delta_y=3, threshold_px=5) == "drag"


def test_classify_drag_behavior_uses_drag_still_for_vertical_drag() -> None:
    assert classify_drag_behavior(delta_x=2, delta_y=12, threshold_px=5) == "drag_still"


def test_classify_drag_behavior_uses_drag_still_for_small_movement() -> None:
    assert classify_drag_behavior(delta_x=2, delta_y=1, threshold_px=5) == "drag_still"


def test_drag_behavior_tracker_uses_recent_time_window() -> None:
    tracker = DragBehaviorTracker(window_ms=150, threshold_px=5, direction_margin_px=3)

    assert tracker.update(delta_x=0, delta_y=12, timestamp_ms=0) == "drag_still"
    assert tracker.update(delta_x=20, delta_y=0, timestamp_ms=200) == "drag"


def test_drag_behavior_tracker_requires_horizontal_advantage_margin() -> None:
    tracker = DragBehaviorTracker(window_ms=150, threshold_px=5, direction_margin_px=3)

    assert tracker.update(delta_x=8, delta_y=6, timestamp_ms=0) == "drag_still"


def test_drag_behavior_tracker_ignores_subthreshold_recent_motion() -> None:
    tracker = DragBehaviorTracker(window_ms=150, threshold_px=5, direction_margin_px=3)

    assert tracker.update(delta_x=2, delta_y=1, timestamp_ms=0) is None
