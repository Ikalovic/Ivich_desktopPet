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
