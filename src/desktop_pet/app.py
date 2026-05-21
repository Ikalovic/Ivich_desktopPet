from __future__ import annotations

import logging
import random
from pathlib import Path
import sys

from desktop_pet.config import ConfigError, load_project_config
from desktop_pet.sprites import discover_frames
from desktop_pet.state import PetStateMachine
from desktop_pet.walk import WalkController


LOGGER = logging.getLogger(__name__)
_CONFIG_SENTINEL = Path("assets") / "config" / "animation.json"
_IDLE_SLEEP_MS = 120_000
_IDLE_TICK_MS = 1_000
_WALK_INTERVAL_MIN_MS = 30_000
_WALK_INTERVAL_MAX_MS = 90_000
_WALK_TICK_MS = 50


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
        self._current_animation_mirror_horizontal: bool | None = None
        self._rng = random.Random()
        self._idle_elapsed_ms = 0
        self.walk = WalkController()
        self.window.drag_started.connect(self._handle_drag_started)
        self.window.drag_finished.connect(lambda: self.change_state("idle", force=True))
        self.window.clicked.connect(self.handle_click)

        self._idle_tick_timer = QTimer(self.window)
        self._idle_tick_timer.timeout.connect(lambda: self._advance_idle_time(_IDLE_TICK_MS))
        self._idle_tick_timer.start(_IDLE_TICK_MS)

        self._walk_timer = QTimer(self.window)
        self._walk_timer.setSingleShot(True)
        self._walk_timer.timeout.connect(self.maybe_start_idle_walk)

        self._walk_motion_timer = QTimer(self.window)
        self._walk_motion_timer.timeout.connect(lambda: self.advance_walk(_WALK_TICK_MS))

    def start(self) -> None:
        self.window.show()
        if not self.change_state(self.config.states.default_state, force=True):
            self.window.set_placeholder("Missing idle frames")

    def change_state(self, state_name: str, force: bool = False, mirror_horizontal: bool = False) -> bool:
        if force:
            self.state.force(state_name)
        else:
            self.state.transition_to(state_name)

        played = self._play_animation(
            self.state.current_animation,
            force=force,
            fallback_state=state_name,
            mirror_horizontal=mirror_horizontal,
        )
        self._sync_state_timers()
        return played

    def maybe_start_idle_walk(self) -> bool:
        if self.state.current_state != self.config.states.default_state:
            return False
        if not self.walk.start_random_walk():
            self._schedule_walk_timer()
            return False

        if not self.change_state(
            "walk",
            force=True,
            mirror_horizontal=self.walk.mirror_horizontal,
        ):
            self.walk.stop()
            self._schedule_walk_timer()
            return False

        if self.state.current_state != "walk":
            self.walk.stop()
            self._schedule_walk_timer()
            return False

        self._start_walk_motion_timer()
        return True

    def advance_walk(self, elapsed_ms: int) -> None:
        if not self.walk.is_walking:
            return

        position = self.window.pos()
        size = self.window.size()
        screen = self.window.screen()
        if screen is None:
            return
        bounds = screen.availableGeometry()

        step = self.walk.step(
            x=position.x() - bounds.x(),
            y=position.y() - bounds.y(),
            pet_width=size.width(),
            pet_height=size.height(),
            bounds_width=bounds.width(),
            bounds_height=bounds.height(),
            elapsed_ms=elapsed_ms,
        )
        self.window.move(bounds.x() + step.x, bounds.y() + step.y)
        if step.is_walking:
            self._play_animation(
                step.animation_name,
                mirror_horizontal=step.mirror_horizontal,
                fallback_state="walk",
            )
            if self.state.current_state == "walk":
                return
            self.walk.stop()
            self._stop_walk_motion_timer()
            return

        self._stop_walk_motion_timer()
        self.walk.stop()
        self.change_state(self.config.states.default_state, force=True)

    def _play_animation(
        self,
        animation_name: str,
        *,
        force: bool = False,
        fallback_state: str | None = None,
        mirror_horizontal: bool = False,
    ) -> bool:
        animation = self.config.animations.get(animation_name)
        if animation is None:
            LOGGER.warning("Animation %s is not configured", animation_name)
            self._current_animation_name = None
            self._current_animation_mirror_horizontal = None
            return False

        if (
            not force
            and animation_name == self._current_animation_name
            and mirror_horizontal == self._current_animation_mirror_horizontal
        ):
            return True

        frames = self.frames_by_animation.get(animation_name, [])
        if not frames:
            LOGGER.warning(
                "Animation %s has no frames; falling back to idle",
                animation_name,
            )
            self._current_animation_name = None
            self._current_animation_mirror_horizontal = None
            if fallback_state is not None and fallback_state != self.config.states.default_state:
                return self.change_state(self.config.states.default_state, force=True)
            return False

        if self.animator.play(frames, animation, mirror_horizontal=mirror_horizontal):
            self._current_animation_name = animation_name
            self._current_animation_mirror_horizontal = mirror_horizontal
            return True

        self._current_animation_name = None
        self._current_animation_mirror_horizontal = None
        LOGGER.warning("Animation %s could not be loaded", animation_name)
        if fallback_state is not None and fallback_state != self.config.states.default_state:
            return self.change_state(self.config.states.default_state, force=True)
        return False

    def _sync_state_timers(self) -> None:
        if self.state.current_state == self.config.states.default_state:
            self._schedule_walk_timer()
            self._stop_walk_motion_timer()
            return

        self._stop_idle_timers()
        if self.state.current_state != "walk":
            self._stop_walk_motion_timer()

    def _schedule_walk_timer(self) -> None:
        walk_timer = getattr(self, "_walk_timer", None)
        if walk_timer is not None:
            walk_timer.start(
                self._rng.randint(_WALK_INTERVAL_MIN_MS, _WALK_INTERVAL_MAX_MS)
            )

    def _stop_idle_timers(self) -> None:
        walk_timer = getattr(self, "_walk_timer", None)
        if walk_timer is not None:
            walk_timer.stop()

    def _stop_walk_motion_timer(self) -> None:
        walk_motion_timer = getattr(self, "_walk_motion_timer", None)
        if walk_motion_timer is not None:
            walk_motion_timer.stop()

    def _start_walk_motion_timer(self) -> None:
        walk_motion_timer = getattr(self, "_walk_motion_timer", None)
        if walk_motion_timer is not None:
            walk_motion_timer.start(_WALK_TICK_MS)

    def _advance_idle_time(self, elapsed_ms: int) -> bool:
        if self.state.current_state != self.config.states.default_state:
            return False

        self._idle_elapsed_ms += max(0, elapsed_ms)
        if self._idle_elapsed_ms < _IDLE_SLEEP_MS:
            return False

        self._idle_elapsed_ms = 0
        return self.change_state("sleep")

    def _handle_drag_started(self) -> None:
        self._idle_elapsed_ms = 0
        self._stop_walk_motion_timer()
        self.walk.stop()
        self.change_state("drag", force=True)

    def handle_click(self) -> None:
        self._idle_elapsed_ms = 0
        self._stop_walk_motion_timer()
        self.walk.stop()
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
