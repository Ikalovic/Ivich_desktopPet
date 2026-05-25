import json
from pathlib import Path

import pytest

from desktop_pet.config import ConfigError, load_project_config
from desktop_pet.sprites import discover_frames


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


def test_load_project_config_parses_walk_animation_and_state(tmp_path: Path) -> None:
    write_json(
        tmp_path / "assets/config/animation.json",
        {
            "character": {
                "idle": {"pattern": "assets/character/idle/idle_%02d.png"},
                "walk": {"pattern": "assets/character/walk/walk_left_%02d.png"},
            }
        },
    )
    write_json(
        tmp_path / "assets/config/state.json",
        {
            "defaultState": "idle",
            "states": {
                "idle": {"animation": "idle", "canTransitionTo": ["walk"]},
                "walk": {"animation": "walk", "canTransitionTo": ["idle"]},
            },
        },
    )
    write_json(tmp_path / "assets/config/settings.json", {"canvas": {}})

    config = load_project_config(tmp_path)

    assert config.animations["walk"].pattern == "assets/character/walk/walk_left_%02d.png"
    assert config.states.states["walk"].animation == "walk"


def test_project_walk_animation_config_matches_existing_assets() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = load_project_config(project_root)

    frames = discover_frames(project_root, config.animations["walk"])

    assert frames


def test_project_drag_still_animation_config_matches_existing_assets() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = load_project_config(project_root)

    assert config.states.states["drag_still"].animation == "drag_still"
    frames = discover_frames(project_root, config.animations["drag_still"])

    assert frames


def test_project_drag_animation_config_matches_left_drag_assets() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = load_project_config(project_root)

    assert config.animations["drag"].pattern == "assets/character/drag/drag_left_%02d.png"
    frames = discover_frames(project_root, config.animations["drag"])

    assert [path.name for path in frames] == [
        "drag_left_01.png",
        "drag_left_02.png",
        "drag_left_03.png",
        "drag_left_04.png",
        "drag_left_05.png",
        "drag_left_06.png",
        "drag_left_07.png",
        "drag_left_08.png",
    ]


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
