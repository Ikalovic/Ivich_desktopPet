from pathlib import Path

from desktop_pet.app import DesktopPetApp, _find_project_root_from
from desktop_pet.config import AnimationConfig, StateConfig, StateConfigSet
from desktop_pet.state import PetStateMachine
from desktop_pet.walk import WalkStep


class RecordingAnimator:
    def __init__(self, results: list[bool]) -> None:
        self.results = results
        self.calls: list[tuple[list[Path], AnimationConfig, bool]] = []

    def play(self, frames: list[Path], animation: AnimationConfig, *, mirror_horizontal: bool = False) -> bool:
        self.calls.append((frames, animation, mirror_horizontal))
        if self.results:
            return self.results.pop(0)
        return True


def make_app(animator: RecordingAnimator) -> DesktopPetApp:
    app = object.__new__(DesktopPetApp)
    idle = AnimationConfig("idle", "idle_%02d.png", 1, 8, True)
    drag = AnimationConfig("drag", "drag_%02d.png", 1, 8, True)
    drag_still = AnimationConfig("drag_still", "drag_still_%02d.png", 1, 8, True)
    sleep = AnimationConfig("sleep", "sleep_%02d.png", 1, 8, True)
    walk = AnimationConfig("walk", "walk_%02d.png", 1, 8, True)
    app.config = type(
        "Config",
        (),
        {
            "animations": {
                "idle": idle,
                "drag": drag,
                "drag_still": drag_still,
                "sleep": sleep,
                "walk": walk,
            },
            "states": StateConfigSet(
                default_state="idle",
                states={
                    "idle": StateConfig("idle", "idle", ("drag", "drag_still", "sleep", "walk")),
                    "drag": StateConfig("drag", "drag", ("idle",)),
                    "drag_still": StateConfig("drag_still", "drag_still", ("idle",)),
                    "sleep": StateConfig("sleep", "sleep", ("idle",)),
                    "walk": StateConfig("walk", "walk", ("idle",)),
                },
            ),
        },
    )()
    app.frames_by_animation = {
        "idle": [Path("idle_01.png")],
        "drag": [Path("drag_01.png")],
        "drag_still": [Path("drag_still_01.png")],
        "sleep": [Path("sleep_01.png")],
        "walk": [Path("walk_01.png")],
    }
    app.state = PetStateMachine(app.config.states, {"idle", "drag", "drag_still", "sleep", "walk"})
    app.animator = animator
    app._current_animation_name = None
    return app


class StartingWalk:
    mirror_horizontal = True

    def start_random_walk(self) -> bool:
        return True


class StaticWalk:
    animation_name = "walk"

    def __init__(self, step: WalkStep) -> None:
        self.step_result = step
        self.calls: list[dict[str, int]] = []
        self.mirror_horizontal = step.mirror_horizontal

    @property
    def is_walking(self) -> bool:
        return True

    def start_random_walk(self) -> bool:
        return True

    def stop(self) -> None:
        return None

    def step(self, **kwargs: int) -> WalkStep:
        self.calls.append(kwargs)
        return self.step_result


class FakePoint:
    def __init__(self, x: int, y: int) -> None:
        self._x = x
        self._y = y

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y


class FakeSize:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class FakeGeometry:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self._x = x
        self._y = y
        self._width = width
        self._height = height

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class FakeScreen:
    def __init__(self, geometry: FakeGeometry) -> None:
        self._geometry = geometry

    def availableGeometry(self) -> FakeGeometry:
        return self._geometry


class FakeWindow:
    def __init__(self) -> None:
        self.moves: list[tuple[int, int]] = []

    def pos(self) -> FakePoint:
        return FakePoint(120, 80)

    def size(self) -> FakeSize:
        return FakeSize(50, 40)

    def screen(self) -> FakeScreen:
        return FakeScreen(FakeGeometry(100, 50, 800, 600))

    def move(self, x: int, y: int) -> None:
        self.moves.append((x, y))


def test_find_project_root_from_walks_up_to_assets_config(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    nested = project_root / "src" / "desktop_pet"
    (project_root / "assets" / "config").mkdir(parents=True)
    (project_root / "assets" / "config" / "animation.json").write_text(
        "{}",
        encoding="utf-8",
    )
    nested.mkdir(parents=True)

    assert _find_project_root_from(nested) == project_root


def test_change_state_falls_back_when_non_default_animation_cannot_play() -> None:
    animator = RecordingAnimator([False, True])
    app = make_app(animator)

    assert app.change_state("drag", force=True)

    assert app.state.current_state == "idle"
    assert [call[1].name for call in animator.calls] == ["drag", "idle"]
    assert app._current_animation_name == "idle"


def test_change_state_returns_false_when_default_animation_cannot_play() -> None:
    animator = RecordingAnimator([False])
    app = make_app(animator)

    assert not app.change_state("idle", force=True)

    assert app.state.current_state == "idle"
    assert [call[1].name for call in animator.calls] == ["idle"]
    assert app._current_animation_name is None


def test_change_state_skips_restart_for_same_animation_without_force() -> None:
    animator = RecordingAnimator([])
    app = make_app(animator)

    assert app.change_state("idle", force=True)
    assert app.change_state("idle")

    assert [call[1].name for call in animator.calls] == ["idle"]
    assert app._current_animation_name == "idle"


def test_play_animation_restarts_when_mirror_changes() -> None:
    animator = RecordingAnimator([])
    app = make_app(animator)

    assert app._play_animation("walk", force=True, mirror_horizontal=False)
    assert app._play_animation("walk", mirror_horizontal=True)

    assert [call[1].name for call in animator.calls] == ["walk", "walk"]
    assert [call[2] for call in animator.calls] == [False, True]


def test_idle_walk_starts_walk_state_and_uses_walk_animation() -> None:
    animator = RecordingAnimator([])
    app = make_app(animator)
    app.walk = StartingWalk()

    assert app.change_state("idle", force=True)

    app.maybe_start_idle_walk()

    assert app.state.current_state == "walk"
    assert [call[1].name for call in animator.calls] == ["idle", "walk"]
    assert [call[2] for call in animator.calls] == [False, True]
    assert app._current_animation_name == "walk"


def test_walk_step_moves_window_relative_to_screen_and_uses_mirror_flag() -> None:
    animator = RecordingAnimator([])
    app = make_app(animator)
    app.window = FakeWindow()
    app.walk = StaticWalk(WalkStep(x=25, y=45, animation_name="walk", mirror_horizontal=True, is_walking=True))

    app.advance_walk(100)

    assert app.walk.calls == [
        {
            "x": 20,
            "y": 30,
            "pet_width": 50,
            "pet_height": 40,
            "bounds_width": 800,
            "bounds_height": 600,
            "elapsed_ms": 100,
        }
    ]
    assert app.window.moves == [(125, 95)]
    assert [call[1].name for call in animator.calls] == ["walk"]
    assert [call[2] for call in animator.calls] == [True]


def test_walk_step_returns_to_idle_when_random_duration_ends() -> None:
    animator = RecordingAnimator([])
    app = make_app(animator)
    app.window = FakeWindow()
    app.walk = StaticWalk(WalkStep(x=25, y=45, animation_name="idle", mirror_horizontal=False, is_walking=False))

    app.advance_walk(100)

    assert app.state.current_state == "idle"
    assert [call[1].name for call in animator.calls] == ["idle"]


def test_handle_drag_still_started_switches_to_drag_still() -> None:
    animator = RecordingAnimator([])
    app = make_app(animator)
    app._idle_elapsed_ms = 100
    app._stop_walk_motion_timer = lambda: None
    app.walk = type("StaticWalker", (), {"stop": lambda self: None})()

    app.handle_drag_still_started()

    assert app.state.current_state == "drag_still"
    assert [call[1].name for call in animator.calls] == ["drag_still"]


def test_idle_time_accumulates_across_walk_before_sleep() -> None:
    animator = RecordingAnimator([])
    app = make_app(animator)
    app._idle_elapsed_ms = 60_000

    app.change_state("walk", force=True)
    app._advance_idle_time(10_000)

    assert app._idle_elapsed_ms == 60_000
    assert app.state.current_state == "walk"

    app.change_state("idle", force=True)
    app._advance_idle_time(60_000)

    assert app.state.current_state == "sleep"
    assert app._idle_elapsed_ms == 0
