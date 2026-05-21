from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Protocol


class RandomSource(Protocol):
    def randint(self, start: int, end: int) -> int: ...

    def uniform(self, start: float, end: float) -> float: ...


@dataclass(frozen=True)
class WalkSettings:
    min_speed_px_per_second: float = 40.0
    max_speed_px_per_second: float = 90.0
    min_duration_ms: int = 3_000
    max_duration_ms: int = 8_000


@dataclass(frozen=True)
class WalkStep:
    x: int
    y: int
    animation_name: str
    mirror_horizontal: bool
    is_walking: bool


@dataclass
class _WalkPlan:
    velocity_x: float
    velocity_y: float
    remaining_ms: int


class WalkController:
    _DIRECTIONS: tuple[tuple[int, int], ...] = (
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    )

    def __init__(
        self,
        settings: WalkSettings | None = None,
        rng: RandomSource | None = None,
    ) -> None:
        self._settings = settings or WalkSettings()
        self._rng = rng or random.Random()
        self._plan: _WalkPlan | None = None

    @property
    def is_walking(self) -> bool:
        return self._plan is not None

    @property
    def remaining_ms(self) -> int:
        if self._plan is None:
            return 0
        return self._plan.remaining_ms

    @property
    def mirror_horizontal(self) -> bool:
        if self._plan is None:
            return False
        return self._plan.velocity_x > 0

    def start_random_walk(self) -> bool:
        if self._plan is not None:
            return False

        direction_index = self._rng.randint(0, len(self._DIRECTIONS) - 1)
        direction_x, direction_y = self._DIRECTIONS[direction_index]
        speed = self._rng.uniform(
            self._settings.min_speed_px_per_second,
            self._settings.max_speed_px_per_second,
        )
        duration_ms = self._rng.randint(
            self._settings.min_duration_ms,
            self._settings.max_duration_ms,
        )
        magnitude = math.hypot(direction_x, direction_y) or 1.0
        self._plan = _WalkPlan(
            velocity_x=(direction_x / magnitude) * speed,
            velocity_y=(direction_y / magnitude) * speed,
            remaining_ms=duration_ms,
        )
        return True

    def stop(self) -> None:
        self._plan = None

    def step(
        self,
        *,
        x: int,
        y: int,
        pet_width: int,
        pet_height: int,
        bounds_width: int,
        bounds_height: int,
        elapsed_ms: int,
    ) -> WalkStep:
        if self._plan is None:
            return WalkStep(
                x=x,
                y=y,
                animation_name="idle",
                mirror_horizontal=False,
                is_walking=False,
            )

        seconds = max(0, elapsed_ms) / 1000
        next_x = x + self._plan.velocity_x * seconds
        next_y = y + self._plan.velocity_y * seconds

        max_x = max(0, bounds_width - pet_width)
        max_y = max(0, bounds_height - pet_height)

        if next_x < 0:
            next_x = 0
            self._plan.velocity_x = abs(self._plan.velocity_x)
        elif next_x > max_x:
            next_x = max_x
            self._plan.velocity_x = -abs(self._plan.velocity_x)

        if next_y < 0:
            next_y = 0
            self._plan.velocity_y = abs(self._plan.velocity_y)
        elif next_y > max_y:
            next_y = max_y
            self._plan.velocity_y = -abs(self._plan.velocity_y)

        self._plan.remaining_ms -= max(0, elapsed_ms)
        mirror_horizontal = self._plan.velocity_x > 0
        if self._plan.remaining_ms <= 0:
            self._plan = None
            return WalkStep(
                x=round(next_x),
                y=round(next_y),
                animation_name="idle",
                mirror_horizontal=mirror_horizontal,
                is_walking=False,
            )

        return WalkStep(
            x=round(next_x),
            y=round(next_y),
            animation_name="walk",
            mirror_horizontal=mirror_horizontal,
            is_walking=True,
        )
