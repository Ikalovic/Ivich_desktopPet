import logging
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


def test_discover_frames_logs_first_missing_auto_frame(
    tmp_path: Path,
    caplog,
) -> None:
    make_frame(tmp_path / "assets/character/idle/idle_01.png")
    config = AnimationConfig("idle", "assets/character/idle/idle_%02d.png", 0, 8, True)

    with caplog.at_level(logging.INFO, logger="desktop_pet.sprites"):
        discover_frames(tmp_path, config)

    assert "idle_02.png" in caplog.text


def test_discover_frames_respects_explicit_frame_count(tmp_path: Path) -> None:
    make_frame(tmp_path / "assets/character/idle/idle_01.png")
    make_frame(tmp_path / "assets/character/idle/idle_02.png")
    config = AnimationConfig("idle", "assets/character/idle/idle_%02d.png", 2, 8, True)

    frames = discover_frames(tmp_path, config)

    assert [path.name for path in frames] == ["idle_01.png", "idle_02.png"]


def test_discover_frames_logs_missing_explicit_frame(tmp_path: Path, caplog) -> None:
    make_frame(tmp_path / "assets/character/idle/idle_01.png")
    config = AnimationConfig("idle", "assets/character/idle/idle_%02d.png", 2, 8, True)

    with caplog.at_level(logging.WARNING, logger="desktop_pet.sprites"):
        frames = discover_frames(tmp_path, config)

    assert [path.name for path in frames] == ["idle_01.png"]
    assert "idle_02.png" in caplog.text
