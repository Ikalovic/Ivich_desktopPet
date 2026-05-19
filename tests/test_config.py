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


def test_load_project_config_parses_effects_without_breaking_character_names(tmp_path: Path) -> None:
    write_json(
        tmp_path / "assets/config/animation.json",
        {
            "character": {
                "idle": {"pattern": "assets/character/idle/idle_%02d.png"},
                "special": {
                    "peek": {"pattern": "assets/character/special/peek_%02d.png"},
                },
            },
            "effects": {
                "heart": {"pattern": "assets/effects/heart/heart_%02d.png"},
            },
        },
    )
    write_json(
        tmp_path / "assets/config/state.json",
        {
            "defaultState": "idle",
            "states": {
                "idle": {"animation": "idle", "canTransitionTo": ["peek"]},
                "peek": {"animation": "special.peek"},
            },
        },
    )
    write_json(tmp_path / "assets/config/settings.json", {"canvas": {}})

    config = load_project_config(tmp_path)

    assert sorted(config.animations) == ["effects.heart", "idle", "special.peek"]
    assert config.animations["idle"].pattern == "assets/character/idle/idle_%02d.png"
    assert config.animations["special.peek"].pattern == "assets/character/special/peek_%02d.png"
    assert config.animations["effects.heart"].pattern == "assets/effects/heart/heart_%02d.png"


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


@pytest.mark.parametrize(
    ("animation_config", "state_config", "expected_message"),
    [
        (
            {"character": {"idle": {"pattern": "assets/character/idle/idle_%02d.png", "fps": "fast"}}},
            {"defaultState": "idle", "states": {"idle": {"animation": "idle"}}},
            "animation",
        ),
        (
            {"character": {"idle": {"pattern": "assets/character/idle/idle_%02d.png"}}},
            {"defaultState": "idle", "states": {"idle": {"canTransitionTo": []}}},
            "state",
        ),
    ],
)
def test_load_project_config_wraps_wrong_shape_data_in_config_error(
    tmp_path: Path,
    animation_config: object,
    state_config: object,
    expected_message: str,
) -> None:
    write_json(tmp_path / "assets/config/animation.json", animation_config)
    write_json(tmp_path / "assets/config/state.json", state_config)
    write_json(tmp_path / "assets/config/settings.json", {"canvas": {"baseWidth": 512, "baseHeight": 512}})

    with pytest.raises(ConfigError, match=expected_message):
        load_project_config(tmp_path)
