# Python Qt Desktop Pet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-first PySide6 desktop pet that plays PNG sequence frames, supports drag movement, simple state changes, click feedback, and right-click exit.

**Architecture:** Use a small `src/desktop_pet/` package. Keep non-GUI logic in testable modules (`config.py`, `sprites.py`, `state.py`) and isolate Qt behavior in `window.py` and `app.py`.

**Tech Stack:** Python 3.11+, PySide6, pytest, pathlib, dataclasses, JSON config files under `assets/config/`.

---

## File Structure

- Create `pyproject.toml`: project metadata, runtime dependency on PySide6, test dependency on pytest.
- Create `src/desktop_pet/__init__.py`: package marker and version.
- Create `src/desktop_pet/config.py`: typed config models and JSON loading.
- Create `src/desktop_pet/sprites.py`: PNG frame discovery and animation metadata.
- Create `src/desktop_pet/state.py`: state-machine transition and fallback logic.
- Create `src/desktop_pet/app.py`: app factory that wires config, state, animator, and window.
- Create `src/desktop_pet/window.py`: PySide6 transparent always-on-top pet window and frame animator.
- Create `src/desktop_pet/__main__.py`: `python -m desktop_pet` entry point.
- Create `tests/test_config.py`: config loading tests.
- Create `tests/test_sprites.py`: sequence frame discovery tests.
- Create `tests/test_state.py`: state transition and fallback tests.

## Task 1: Project Metadata And Package Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/desktop_pet/__init__.py`
- Create: `src/desktop_pet/__main__.py`

- [ ] **Step 1: Create project metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "desktop-pet"
version = "0.1.0"
description = "A Windows-first PySide6 desktop pet that plays PNG sequence animations."
readme = "assets/README.md"
requires-python = ">=3.11"
dependencies = [
  "PySide6>=6.7",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
]

[project.scripts]
desktop-pet = "desktop_pet.app:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create the package marker**

Create `src/desktop_pet/__init__.py`:

```python
"""Desktop pet application package."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create the module entry point**

Create `src/desktop_pet/__main__.py`:

```python
from desktop_pet.app import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verify package metadata can be parsed**

Run:

```bash
python -m pip install -e ".[dev]"
python -m pytest --collect-only
```

Expected: installation succeeds, pytest reports collected tests or no tests yet without import errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/desktop_pet/__init__.py src/desktop_pet/__main__.py
git commit -m "chore: add python package skeleton"
```

## Task 2: Configuration Loading

**Files:**
- Create: `src/desktop_pet/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_config.py`:

```python
import json
from pathlib import Path

import pytest

from desktop_pet.config import ConfigError, load_project_config


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_load_project_config_reads_all_config_files(tmp_path: Path) -> None:
    write_json(
        tmp_path / "assets/config/animation.json",
        {"character": {"idle": {"pattern": "assets/character/idle/idle_%02d.png", "frames": 0, "fps": 8, "loop": True}}},
    )
    write_json(
        tmp_path / "assets/config/state.json",
        {"defaultState": "idle", "states": {"idle": {"animation": "idle", "canTransitionTo": ["drag"]}}},
    )
    write_json(
        tmp_path / "assets/config/settings.json",
        {"canvas": {"baseWidth": 512, "baseHeight": 512, "anchor": "bottom-center"}},
    )

    config = load_project_config(tmp_path)

    assert config.project_root == tmp_path
    assert config.animations["idle"].pattern == "assets/character/idle/idle_%02d.png"
    assert config.animations["idle"].fps == 8
    assert config.states.default_state == "idle"
    assert config.settings.base_width == 512
    assert config.settings.base_height == 512


def test_load_project_config_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="animation.json"):
        load_project_config(tmp_path)


def test_load_project_config_reports_malformed_json(tmp_path: Path) -> None:
    config_dir = tmp_path / "assets/config"
    config_dir.mkdir(parents=True)
    (config_dir / "animation.json").write_text("{bad json", encoding="utf-8")
    write_json(config_dir / "state.json", {"defaultState": "idle", "states": {}})
    write_json(config_dir / "settings.json", {"canvas": {"baseWidth": 512, "baseHeight": 512}})

    with pytest.raises(ConfigError, match="animation.json"):
        load_project_config(tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_config.py -q
```

Expected: FAIL because `desktop_pet.config` does not exist.

- [ ] **Step 3: Implement config loading**

Create `src/desktop_pet/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


class ConfigError(RuntimeError):
    """Raised when required project configuration cannot be loaded."""


@dataclass(frozen=True)
class AnimationConfig:
    name: str
    pattern: str
    frames: int
    fps: int
    loop: bool


@dataclass(frozen=True)
class StateConfig:
    name: str
    animation: str
    can_transition_to: tuple[str, ...]


@dataclass(frozen=True)
class StateConfigSet:
    default_state: str
    states: dict[str, StateConfig]


@dataclass(frozen=True)
class SettingsConfig:
    base_width: int
    base_height: int
    anchor: str


@dataclass(frozen=True)
class ProjectConfig:
    project_root: Path
    animations: dict[str, AnimationConfig]
    states: StateConfigSet
    settings: SettingsConfig


def load_project_config(project_root: Path) -> ProjectConfig:
    config_dir = project_root / "assets" / "config"
    animation_data = _read_json(config_dir / "animation.json")
    state_data = _read_json(config_dir / "state.json")
    settings_data = _read_json(config_dir / "settings.json")
    return ProjectConfig(
        project_root=project_root,
        animations=_parse_animations(animation_data),
        states=_parse_states(state_data),
        settings=_parse_settings(settings_data),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Missing required config file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Malformed JSON in config file: {path}: {exc}") from exc


def _parse_animations(data: dict[str, Any]) -> dict[str, AnimationConfig]:
    animations: dict[str, AnimationConfig] = {}

    def collect(prefix: str, node: dict[str, Any]) -> None:
        for key, value in node.items():
            name = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict) and "pattern" in value:
                animations[name] = AnimationConfig(
                    name=name,
                    pattern=str(value["pattern"]),
                    frames=int(value.get("frames", 0)),
                    fps=int(value.get("fps", 8)),
                    loop=bool(value.get("loop", True)),
                )
            elif isinstance(value, dict):
                collect(name, value)

    collect("", data.get("character", {}))
    return animations


def _parse_states(data: dict[str, Any]) -> StateConfigSet:
    states = {
        name: StateConfig(
            name=name,
            animation=str(value["animation"]),
            can_transition_to=tuple(value.get("canTransitionTo", ())),
        )
        for name, value in data.get("states", {}).items()
    }
    return StateConfigSet(default_state=str(data.get("defaultState", "idle")), states=states)


def _parse_settings(data: dict[str, Any]) -> SettingsConfig:
    canvas = data.get("canvas", {})
    return SettingsConfig(
        base_width=int(canvas.get("baseWidth", 512)),
        base_height=int(canvas.get("baseHeight", 512)),
        anchor=str(canvas.get("anchor", "bottom-center")),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/desktop_pet/config.py tests/test_config.py
git commit -m "feat: load desktop pet configuration"
```

## Task 3: PNG Sequence Discovery

**Files:**
- Create: `src/desktop_pet/sprites.py`
- Create: `tests/test_sprites.py`

- [ ] **Step 1: Write failing sprite tests**

Create `tests/test_sprites.py`:

```python
from pathlib import Path

from desktop_pet.config import AnimationConfig
from desktop_pet.sprites import discover_frames


def make_frame(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not-a-real-png-for-discovery-tests")


def test_discover_frames_scans_contiguous_frames_when_count_is_zero(tmp_path: Path) -> None:
    make_frame(tmp_path / "assets/character/idle/idle_01.png")
    make_frame(tmp_path / "assets/character/idle/idle_02.png")
    make_frame(tmp_path / "assets/character/idle/idle_03.png")
    config = AnimationConfig("idle", "assets/character/idle/idle_%02d.png", 0, 8, True)

    frames = discover_frames(tmp_path, config)

    assert [path.name for path in frames] == ["idle_01.png", "idle_02.png", "idle_03.png"]


def test_discover_frames_stops_at_first_gap(tmp_path: Path) -> None:
    make_frame(tmp_path / "assets/character/idle/idle_01.png")
    make_frame(tmp_path / "assets/character/idle/idle_03.png")
    config = AnimationConfig("idle", "assets/character/idle/idle_%02d.png", 0, 8, True)

    frames = discover_frames(tmp_path, config)

    assert [path.name for path in frames] == ["idle_01.png"]


def test_discover_frames_respects_explicit_frame_count(tmp_path: Path) -> None:
    make_frame(tmp_path / "assets/character/idle/idle_01.png")
    make_frame(tmp_path / "assets/character/idle/idle_02.png")
    config = AnimationConfig("idle", "assets/character/idle/idle_%02d.png", 2, 8, True)

    frames = discover_frames(tmp_path, config)

    assert [path.name for path in frames] == ["idle_01.png", "idle_02.png"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_sprites.py -q
```

Expected: FAIL because `desktop_pet.sprites` does not exist.

- [ ] **Step 3: Implement frame discovery**

Create `src/desktop_pet/sprites.py`:

```python
from __future__ import annotations

from pathlib import Path

from desktop_pet.config import AnimationConfig


def discover_frames(project_root: Path, config: AnimationConfig) -> list[Path]:
    if config.frames > 0:
        return [
            path
            for index in range(1, config.frames + 1)
            if (path := _frame_path(project_root, config.pattern, index)).exists()
        ]

    frames: list[Path] = []
    index = 1
    while True:
        path = _frame_path(project_root, config.pattern, index)
        if not path.exists():
            break
        frames.append(path)
        index += 1
    return frames


def _frame_path(project_root: Path, pattern: str, index: int) -> Path:
    return project_root / (pattern % index)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_sprites.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/desktop_pet/sprites.py tests/test_sprites.py
git commit -m "feat: discover png animation frames"
```

## Task 4: State Machine

**Files:**
- Create: `src/desktop_pet/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing state tests**

Create `tests/test_state.py`:

```python
from desktop_pet.config import StateConfig, StateConfigSet
from desktop_pet.state import PetStateMachine


def make_states() -> StateConfigSet:
    return StateConfigSet(
        default_state="idle",
        states={
            "idle": StateConfig("idle", "idle", ("drag", "sleep")),
            "drag": StateConfig("drag", "drag", ("idle",)),
            "sleep": StateConfig("sleep", "sleep", ("idle",)),
        },
    )


def test_state_machine_starts_in_default_state() -> None:
    machine = PetStateMachine(make_states(), available_animations={"idle"})

    assert machine.current_state == "idle"
    assert machine.current_animation == "idle"


def test_state_machine_allows_configured_transition() -> None:
    machine = PetStateMachine(make_states(), available_animations={"idle", "drag"})

    assert machine.transition_to("drag") == "drag"
    assert machine.current_state == "drag"
    assert machine.current_animation == "drag"


def test_state_machine_rejects_unconfigured_transition() -> None:
    machine = PetStateMachine(make_states(), available_animations={"idle", "drag", "sleep"})

    assert machine.transition_to("sleep") == "sleep"
    assert machine.transition_to("drag") == "sleep"
    assert machine.current_state == "sleep"


def test_state_machine_falls_back_to_idle_when_animation_missing() -> None:
    machine = PetStateMachine(make_states(), available_animations={"idle"})

    assert machine.transition_to("drag") == "idle"
    assert machine.current_state == "idle"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_state.py -q
```

Expected: FAIL because `desktop_pet.state` does not exist.

- [ ] **Step 3: Implement state machine**

Create `src/desktop_pet/state.py`:

```python
from __future__ import annotations

from desktop_pet.config import StateConfigSet


class PetStateMachine:
    def __init__(self, states: StateConfigSet, available_animations: set[str]) -> None:
        self._states = states
        self._available_animations = available_animations
        self.current_state = states.default_state
        self.current_animation = self._animation_for(self.current_state)

    def transition_to(self, target_state: str) -> str:
        current = self._states.states.get(self.current_state)
        if current is None or target_state not in current.can_transition_to:
            return self.current_state
        animation = self._animation_for(target_state)
        if animation not in self._available_animations:
            self.current_state = self._states.default_state
            self.current_animation = self._animation_for(self.current_state)
            return self.current_state
        self.current_state = target_state
        self.current_animation = animation
        return self.current_state

    def force(self, target_state: str) -> str:
        animation = self._animation_for(target_state)
        if animation not in self._available_animations:
            target_state = self._states.default_state
            animation = self._animation_for(target_state)
        self.current_state = target_state
        self.current_animation = animation
        return self.current_state

    def _animation_for(self, state_name: str) -> str:
        state = self._states.states.get(state_name)
        if state is None:
            return self._states.default_state
        return state.animation
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_state.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/desktop_pet/state.py tests/test_state.py
git commit -m "feat: add pet state machine"
```

## Task 5: PySide6 Window And Animator

**Files:**
- Create: `src/desktop_pet/window.py`

- [ ] **Step 1: Implement Qt window and frame animator**

Create `src/desktop_pet/window.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QMouseEvent, QPixmap
from PySide6.QtWidgets import QLabel, QMenu, QWidget

from desktop_pet.config import AnimationConfig


class SpriteAnimator(QWidget):
    frame_changed = Signal(QPixmap)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)
        self._frames: list[QPixmap] = []
        self._index = 0
        self._loop = True

    def play(self, frame_paths: list[Path], config: AnimationConfig) -> bool:
        pixmaps = [pixmap for path in frame_paths if not (pixmap := QPixmap(str(path))).isNull()]
        if not pixmaps:
            return False
        self._frames = pixmaps
        self._index = 0
        self._loop = config.loop
        interval_ms = max(1, int(1000 / max(1, config.fps)))
        self.frame_changed.emit(self._frames[self._index])
        self._timer.start(interval_ms)
        return True

    def stop(self) -> None:
        self._timer.stop()

    def _next_frame(self) -> None:
        if not self._frames:
            return
        self._index += 1
        if self._index >= len(self._frames):
            if not self._loop:
                self._index = len(self._frames) - 1
                self._timer.stop()
            else:
                self._index = 0
        self.frame_changed.emit(self._frames[self._index])


class PetWindow(QWidget):
    drag_started = Signal()
    drag_finished = Signal()
    clicked = Signal()

    def __init__(self, width: int, height: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setGeometry(0, 0, width, height)
        self._drag_offset: QPoint | None = None
        self._press_pos: QPoint | None = None

        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

    def set_frame(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)

    def set_placeholder(self, text: str) -> None:
        self._label.setText(text)
        self._label.setStyleSheet("color: #334155; background: rgba(255, 255, 255, 180); border: 1px solid #94a3b8;")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.drag_started.emit()
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            release_pos = event.globalPosition().toPoint()
            was_click = self._press_pos is not None and (release_pos - self._press_pos).manhattanLength() < 5
            self._drag_offset = None
            self._press_pos = None
            if was_click:
                self.clicked.emit()
            else:
                self.drag_finished.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)
        menu.exec(global_pos)
```

- [ ] **Step 2: Manually inspect imports**

Run:

```bash
python -m compileall src/desktop_pet/window.py
```

Expected: command exits with code 0.

- [ ] **Step 3: Commit**

```bash
git add src/desktop_pet/window.py
git commit -m "feat: add qt pet window"
```

## Task 6: Wire The Application

**Files:**
- Create: `src/desktop_pet/app.py`
- Modify: `src/desktop_pet/window.py`

- [ ] **Step 1: Implement application wiring**

Create `src/desktop_pet/app.py`:

```python
from __future__ import annotations

import logging
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop_pet.config import AnimationConfig, ConfigError, load_project_config
from desktop_pet.sprites import discover_frames
from desktop_pet.state import PetStateMachine
from desktop_pet.window import PetWindow, SpriteAnimator


LOGGER = logging.getLogger(__name__)


class DesktopPetApp:
    def __init__(self, project_root: Path) -> None:
        self.config = load_project_config(project_root)
        self.frames_by_animation = {
            name: discover_frames(project_root, animation)
            for name, animation in self.config.animations.items()
        }
        available = {name for name, frames in self.frames_by_animation.items() if frames}
        self.state = PetStateMachine(self.config.states, available)
        self.window = PetWindow(self.config.settings.base_width, self.config.settings.base_height)
        self.animator = SpriteAnimator(self.window)
        self.animator.frame_changed.connect(self.window.set_frame)
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
        state = self.state.force(state_name) if force else self.state.transition_to(state_name)
        animation_name = self.state.current_animation
        animation = self.config.animations.get(animation_name)
        if animation is None:
            LOGGER.warning("Animation %s is not configured", animation_name)
            return False
        frames = self.frames_by_animation.get(animation_name, [])
        if not frames:
            LOGGER.warning("Animation %s has no frames; falling back to idle", animation_name)
            if state_name != self.config.states.default_state:
                return self.change_state(self.config.states.default_state, force=True)
            return False
        return self.animator.play(frames, animation)

    def handle_click(self) -> None:
        self._sleep_timer.start(120_000)
        self.change_state("idle", force=True)


def find_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    qt_app = QApplication(sys.argv)
    try:
        pet = DesktopPetApp(find_project_root())
    except ConfigError as exc:
        LOGGER.error("%s", exc)
        return 1
    pet.start()
    return qt_app.exec()
```

- [ ] **Step 2: Run non-GUI tests and compile app module**

Run:

```bash
python -m pytest -q
python -m compileall src/desktop_pet
```

Expected: tests pass and compileall exits with code 0.

- [ ] **Step 3: Manual GUI smoke test**

Run:

```bash
python -m desktop_pet
```

Expected: a 512 x 512 transparent always-on-top window appears, idle frames loop, left drag moves the pet, right-click shows `退出`.

- [ ] **Step 4: Commit**

```bash
git add src/desktop_pet/app.py
git commit -m "feat: wire desktop pet application"
```

## Task 7: Documentation And Run Instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Add README**

Create `README.md`:

```markdown
# Ivich Desktop Pet

Windows-first Python/PySide6 desktop pet using PNG sequence frames.

## Setup

```bash
python -m pip install -e ".[dev]"
```

## Run

```bash
python -m desktop_pet
```

## Test

```bash
python -m pytest -q
```

## Assets

Character animations are loaded from `assets/character/<state>/<state>_NN.png`.
Animation speed and looping are configured in `assets/config/animation.json`.
When `frames` is `0`, the app scans sequential files from `01` until the first missing frame.
```

- [ ] **Step 2: Verify docs render as plain Markdown**

Run:

```bash
sed -n '1,160p' README.md
```

Expected: README shows setup, run, test, and asset sections.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add run instructions"
```

## Task 8: Final Verification

**Files:**
- No file changes expected.

- [ ] **Step 1: Run full automated verification**

Run:

```bash
python -m pytest -q
python -m compileall src/desktop_pet
```

Expected: all tests pass and compileall exits with code 0.

- [ ] **Step 2: Run manual GUI verification**

Run:

```bash
python -m desktop_pet
```

Expected: the desktop pet opens, loops idle frames, drags with left mouse, returns to idle after drag, and exits from the right-click menu.

- [ ] **Step 3: Check Git status**

Run:

```bash
git status --short --branch
```

Expected: branch is clean after all commits.
