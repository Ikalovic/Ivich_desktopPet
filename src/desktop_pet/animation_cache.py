from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Generic, TypeVar

from desktop_pet.config import AnimationConfig


FrameT = TypeVar("FrameT")


class FrameCache(Generic[FrameT]):
    def __init__(
        self,
        *,
        load_frame: Callable[[Path], FrameT | None],
        mirror_frame: Callable[[FrameT], FrameT] | None = None,
    ) -> None:
        self._load_frame = load_frame
        self._mirror_frame = mirror_frame
        self._source_frames_by_name: dict[str, list[FrameT]] = {}
        self._frames_by_key: dict[tuple[str, bool], list[FrameT]] = {}

    def get(
        self,
        frame_paths: list[Path],
        config: AnimationConfig,
        *,
        mirror_horizontal: bool,
    ) -> list[FrameT]:
        key = (config.name, mirror_horizontal)
        frames = self._frames_by_key.get(key)
        if frames is not None:
            return frames

        source_frames = self._source_frames_by_name.get(config.name)
        if source_frames is None:
            source_frames = self._load_source_frames(frame_paths)
            if source_frames:
                self._source_frames_by_name[config.name] = source_frames

        if not source_frames:
            return []

        if not mirror_horizontal:
            self._frames_by_key[key] = source_frames
            return source_frames

        if self._mirror_frame is None:
            self._frames_by_key[key] = source_frames
            return source_frames

        mirrored_frames = [self._mirror_frame(frame) for frame in source_frames]
        self._frames_by_key[key] = mirrored_frames
        return mirrored_frames

    def _load_source_frames(self, frame_paths: list[Path]) -> list[FrameT]:
        loaded_frames: list[FrameT] = []
        for path in frame_paths:
            frame = self._load_frame(path)
            if frame is None:
                continue
            loaded_frames.append(frame)
        return loaded_frames
