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

    def update(self, *, delta_x: int, delta_y: int, timestamp_ms: int) -> str | None:
        self._samples.append(DragSample(delta_x, delta_y, timestamp_ms))
        cutoff_ms = timestamp_ms - self._window_ms
        while self._samples and self._samples[0].timestamp_ms < cutoff_ms:
            self._samples.popleft()

        window_delta_x = sum(sample.delta_x for sample in self._samples)
        window_delta_y = sum(sample.delta_y for sample in self._samples)
        if abs(window_delta_x) + abs(window_delta_y) <= self._threshold_px:
            return None
        if abs(window_delta_x) >= abs(window_delta_y) + self._direction_margin_px:
            return "drag"
        return "drag_still"
