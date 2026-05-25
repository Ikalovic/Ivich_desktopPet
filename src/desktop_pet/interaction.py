from __future__ import annotations

from collections import deque
from dataclasses import dataclass


def classify_drag_behavior(*, delta_x: int, delta_y: int, threshold_px: int) -> str:
    if abs(delta_x) + abs(delta_y) <= threshold_px:
        return "drag_still"
    if abs(delta_x) > abs(delta_y):
        return "drag"
    return "drag_still"


@dataclass(frozen=True)
class DragSample:
    delta_x: int
    delta_y: int
    timestamp_ms: int


@dataclass(frozen=True)
class DragBehavior:
    name: str
    mirror_horizontal: bool = False

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        if isinstance(other, DragBehavior):
            return (
                self.name == other.name
                and self.mirror_horizontal == other.mirror_horizontal
            )
        return NotImplemented


def should_emit_drag_behavior(
    *,
    current_name: str | None,
    current_mirror_horizontal: bool | None,
    next_behavior: DragBehavior,
) -> bool:
    return (
        next_behavior.name != current_name
        or next_behavior.mirror_horizontal != current_mirror_horizontal
    )


class DragBehaviorTracker:
    def __init__(
        self,
        *,
        window_ms: int,
        threshold_px: int,
        direction_margin_px: int,
    ) -> None:
        self._window_ms = max(1, window_ms)
        self._threshold_px = max(0, threshold_px)
        self._direction_margin_px = max(0, direction_margin_px)
        self._samples: deque[DragSample] = deque()

    def reset(self) -> None:
        self._samples.clear()

    def update(self, *, delta_x: int, delta_y: int, timestamp_ms: int) -> DragBehavior | None:
        self._samples.append(DragSample(delta_x, delta_y, timestamp_ms))
        cutoff_ms = timestamp_ms - self._window_ms
        while self._samples and self._samples[0].timestamp_ms < cutoff_ms:
            self._samples.popleft()

        window_delta_x = sum(sample.delta_x for sample in self._samples)
        window_delta_y = sum(sample.delta_y for sample in self._samples)
        if abs(window_delta_x) + abs(window_delta_y) <= self._threshold_px:
            return None
        if abs(window_delta_x) >= abs(window_delta_y) + self._direction_margin_px:
            return DragBehavior("drag", mirror_horizontal=window_delta_x > 0)
        return DragBehavior("drag_still")
