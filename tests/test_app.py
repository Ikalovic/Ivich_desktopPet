from pathlib import Path

from desktop_pet.app import DesktopPetApp, _find_project_root_from
from desktop_pet.config import AnimationConfig, StateConfig, StateConfigSet
from desktop_pet.state import PetStateMachine


class RecordingAnimator:
    def __init__(self, results: list[bool]) -> None:
        self.results = results
        self.calls: list[tuple[list[Path], AnimationConfig]] = []

    def play(self, frames: list[Path], animation: AnimationConfig) -> bool:
        self.calls.append((frames, animation))
        if self.results:
            return self.results.pop(0)
        return True


def make_app(animator: RecordingAnimator) -> DesktopPetApp:
    app = object.__new__(DesktopPetApp)
    idle = AnimationConfig("idle", "idle_%02d.png", 1, 8, True)
    drag = AnimationConfig("drag", "drag_%02d.png", 1, 8, True)
    app.config = type(
        "Config",
        (),
        {
            "animations": {"idle": idle, "drag": drag},
            "states": StateConfigSet(
                default_state="idle",
                states={
                    "idle": StateConfig("idle", "idle", ("drag",)),
                    "drag": StateConfig("drag", "drag", ("idle",)),
                },
            ),
        },
    )()
    app.frames_by_animation = {
        "idle": [Path("idle_01.png")],
        "drag": [Path("drag_01.png")],
    }
    app.state = PetStateMachine(app.config.states, {"idle", "drag"})
    app.animator = animator
    app._current_animation_name = None
    return app


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
