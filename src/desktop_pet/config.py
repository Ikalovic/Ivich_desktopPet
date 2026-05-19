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
    try:
        return ProjectConfig(
            project_root=project_root,
            animations=_parse_animations(animation_data),
            states=_parse_states(state_data),
            settings=_parse_settings(settings_data),
        )
    except ConfigError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid project configuration: {exc}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Missing required config file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Malformed JSON in config file: {path}: {exc}") from exc


def _parse_animations(data: dict[str, Any]) -> dict[str, AnimationConfig]:
    if not isinstance(data, dict):
        raise ConfigError("Invalid animation config: expected object")

    animations: dict[str, AnimationConfig] = {}

    def collect(prefix: str, node: dict[str, Any]) -> None:
        for key, value in node.items():
            name = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict) and "pattern" in value:
                try:
                    animations[name] = AnimationConfig(
                        name=name,
                        pattern=str(value["pattern"]),
                        frames=int(value.get("frames", 0)),
                        fps=int(value.get("fps", 8)),
                        loop=bool(value.get("loop", True)),
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise ConfigError(f"Invalid animation config for {name}: {exc}") from exc
            elif isinstance(value, dict):
                collect(name, value)
            else:
                raise ConfigError(f"Invalid animation config for {name}: expected object")

    for section_name, section_data in data.items():
        if not isinstance(section_data, dict):
            raise ConfigError(f"Invalid animation config for {section_name}: expected object")
        prefix = "" if section_name == "character" else section_name
        collect(prefix, section_data)
    return animations


def _parse_states(data: dict[str, Any]) -> StateConfigSet:
    if not isinstance(data, dict):
        raise ConfigError("Invalid state config: expected object")

    raw_states = data.get("states", {})
    if not isinstance(raw_states, dict):
        raise ConfigError("Invalid state config: states must be an object")

    states: dict[str, StateConfig] = {}
    for name, value in raw_states.items():
        if not isinstance(value, dict):
            raise ConfigError(f"Invalid state config for {name}: expected object")
        if "animation" not in value:
            raise ConfigError(f"Invalid state config for {name}: missing animation")
        transitions = value.get("canTransitionTo", ())
        if not isinstance(transitions, (list, tuple)):
            raise ConfigError(f"Invalid state config for {name}: canTransitionTo must be a list")
        states[name] = StateConfig(
            name=name,
            animation=str(value["animation"]),
            can_transition_to=tuple(str(transition) for transition in transitions),
        )
    return StateConfigSet(default_state=str(data.get("defaultState", "idle")), states=states)


def _parse_settings(data: dict[str, Any]) -> SettingsConfig:
    if not isinstance(data, dict):
        raise ConfigError("Invalid settings config: expected object")

    canvas = data.get("canvas", {})
    if not isinstance(canvas, dict):
        raise ConfigError("Invalid settings config: canvas must be an object")
    return SettingsConfig(
        base_width=int(canvas.get("baseWidth", 512)),
        base_height=int(canvas.get("baseHeight", 512)),
        anchor=str(canvas.get("anchor", "bottom-center")),
    )
