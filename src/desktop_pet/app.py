from __future__ import annotations

import logging
from pathlib import Path
import sys

from desktop_pet.config import ConfigError, load_project_config
from desktop_pet.sprites import discover_frames
from desktop_pet.state import PetStateMachine


LOGGER = logging.getLogger(__name__)
_CONFIG_SENTINEL = Path("assets") / "config" / "animation.json"


class DesktopPetApp:
    def __init__(self, project_root: Path) -> None:
        from PySide6.QtCore import QTimer
        from desktop_pet.window import PetWindow, SpriteAnimator

        self.config = load_project_config(project_root)
        self.frames_by_animation = {
            name: discover_frames(project_root, animation)
            for name, animation in self.config.animations.items()
        }
        available_animations = {
            name for name, frames in self.frames_by_animation.items() if frames
        }
        self.state = PetStateMachine(self.config.states, available_animations)
        self.window = PetWindow(
            self.config.settings.base_width,
            self.config.settings.base_height,
        )
        self.animator = SpriteAnimator(self.window)
        self.animator.frame_changed.connect(self.window.set_frame)
        self._current_animation_name: str | None = None
        self.window.drag_started.connect(lambda: self.change_state("drag", force=True))
        self.window.drag_finished.connect(lambda: self.change_state("idle", force=True))
        self.window.clicked.connect(self.handle_click)

        self._sleep_timer = QTimer(self.window)
        self._sleep_timer.timeout.connect(lambda: self.change_state("sleep"))
        self._sleep_timer.start(120_000)

    def start(self) -> None:
        self.window.show()
        if not self.change_state(self.config.states.default_state, force=True):
            self.window.set_placeholder("Missing idle frames")

    def change_state(self, state_name: str, force: bool = False) -> bool:
        if force:
            self.state.force(state_name)
        else:
            self.state.transition_to(state_name)

        animation_name = self.state.current_animation
        animation = self.config.animations.get(animation_name)
        if animation is None:
            LOGGER.warning("Animation %s is not configured", animation_name)
            self._current_animation_name = None
            return False

        if not force and animation_name == self._current_animation_name:
            return True

        frames = self.frames_by_animation.get(animation_name, [])
        if not frames:
            LOGGER.warning(
                "Animation %s has no frames; falling back to idle",
                animation_name,
            )
            self._current_animation_name = None
            if state_name != self.config.states.default_state:
                return self.change_state(self.config.states.default_state, force=True)
            return False

        if self.animator.play(frames, animation):
            self._current_animation_name = animation_name
            return True

        self._current_animation_name = None
        LOGGER.warning("Animation %s could not be loaded", animation_name)
        if state_name != self.config.states.default_state:
            return self.change_state(self.config.states.default_state, force=True)
        return False

    def handle_click(self) -> None:
        self._sleep_timer.start(120_000)
        self.change_state("idle", force=True)


def find_project_root() -> Path:
    for start in (Path.cwd(), Path(__file__).resolve()):
        project_root = _find_project_root_from(start)
        if project_root is not None:
            return project_root
    return Path(__file__).resolve().parents[2]


def _find_project_root_from(start: Path) -> Path | None:
    candidate = start if start.is_dir() else start.parent
    for path in (candidate, *candidate.parents):
        if (path / _CONFIG_SENTINEL).is_file():
            return path
    return None


def main() -> int:
    from PySide6.QtWidgets import QApplication

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    qt_app = QApplication(sys.argv)
    try:
        pet = DesktopPetApp(find_project_root())
    except ConfigError as exc:
        LOGGER.error("%s", exc)
        return 1
    pet.start()
    return qt_app.exec()
