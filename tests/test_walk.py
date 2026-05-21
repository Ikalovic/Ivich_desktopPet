from __future__ import annotations

from desktop_pet.walk import WalkController, WalkSettings


class FixedRandom:
    def __init__(self, *, direction_index: int, speed: float, duration: int) -> None:
        self.direction_index = direction_index
        self.speed = speed
        self.duration = duration

    def randint(self, start: int, end: int) -> int:
        if start == 0 and end == 7:
            return self.direction_index
        return self.duration

    def uniform(self, start: float, end: float) -> float:
        return self.speed


def test_start_random_walk_can_choose_diagonal_direction() -> None:
    controller = WalkController(
        WalkSettings(min_speed_px_per_second=10.0, max_speed_px_per_second=10.0, min_duration_ms=3_000, max_duration_ms=3_000),
        rng=FixedRandom(direction_index=7, speed=10.0, duration=3_000),
    )

    assert controller.start_random_walk()

    step = controller.step(
        x=20,
        y=30,
        pet_width=50,
        pet_height=50,
        bounds_width=500,
        bounds_height=400,
        elapsed_ms=1_000,
    )

    assert step.x > 20
    assert step.y > 30
    assert step.animation_name == "walk"
    assert step.mirror_horizontal
    assert step.is_walking


def test_walk_step_returns_to_idle_when_duration_ends() -> None:
    controller = WalkController(
        WalkSettings(min_speed_px_per_second=10.0, max_speed_px_per_second=10.0, min_duration_ms=1_000, max_duration_ms=1_000),
        rng=FixedRandom(direction_index=0, speed=10.0, duration=1_000),
    )
    controller.start_random_walk()

    step = controller.step(
        x=20,
        y=30,
        pet_width=50,
        pet_height=50,
        bounds_width=500,
        bounds_height=400,
        elapsed_ms=1_000,
    )

    assert not step.is_walking
    assert step.animation_name == "idle"


def test_walk_step_mirrors_when_moving_left() -> None:
    controller = WalkController(
        WalkSettings(min_speed_px_per_second=10.0, max_speed_px_per_second=10.0, min_duration_ms=3_000, max_duration_ms=3_000),
        rng=FixedRandom(direction_index=3, speed=10.0, duration=3_000),
    )
    controller.start_random_walk()

    step = controller.step(
        x=20,
        y=30,
        pet_width=50,
        pet_height=50,
        bounds_width=500,
        bounds_height=400,
        elapsed_ms=1_000,
    )

    assert step.x < 20
    assert step.animation_name == "walk"
    assert not step.mirror_horizontal
