from __future__ import annotations

import logging
from pathlib import Path

from desktop_pet.config import AnimationConfig


LOGGER = logging.getLogger(__name__)


def discover_frames(project_root: Path, config: AnimationConfig) -> list[Path]:
    if config.frames > 0:
        frames: list[Path] = []
        for index in range(1, config.frames + 1):
            path = _frame_path(project_root, config.pattern, index)
            if path.exists():
                frames.append(path)
            else:
                LOGGER.warning("Animation %s missing frame: %s", config.name, path)
        return frames

    frames: list[Path] = []
    index = 1
    while True:
        path = _frame_path(project_root, config.pattern, index)
        if not path.exists():
            LOGGER.info("Animation %s stopped at missing frame: %s", config.name, path)
            break
        frames.append(path)
        index += 1
    return frames


def _frame_path(project_root: Path, pattern: str, index: int) -> Path:
    return project_root / (pattern % index)
