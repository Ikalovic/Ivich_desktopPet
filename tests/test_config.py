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
