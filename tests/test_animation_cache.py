from pathlib import Path

from desktop_pet.animation_cache import FrameCache
from desktop_pet.config import AnimationConfig


class FakeFrame:
    def __init__(self, name: str) -> None:
        self.name = name
        self.mirrored = False

    def mirror(self) -> "FakeFrame":
        mirrored = FakeFrame(self.name)
        mirrored.mirrored = True
        return mirrored


def test_frame_cache_loads_same_animation_once() -> None:
    load_calls: list[Path] = []

    def load(path: Path) -> FakeFrame | None:
        load_calls.append(path)
        return FakeFrame(path.name)

    cache = FrameCache(load_frame=load)
    config = AnimationConfig("idle", "idle_%02d.png", 2, 8, True)
    paths = [Path("idle_01.png"), Path("idle_02.png")]

    assert cache.get(paths, config, mirror_horizontal=False)
    assert cache.get(paths, config, mirror_horizontal=False)

    assert load_calls == paths


def test_frame_cache_uses_separate_entries_for_mirrored_frames() -> None:
    load_calls: list[Path] = []

    def load(path: Path) -> FakeFrame | None:
        load_calls.append(path)
        return FakeFrame(path.name)

    cache = FrameCache(load_frame=load, mirror_frame=lambda frame: frame.mirror())
    config = AnimationConfig("walk", "walk_%02d.png", 1, 8, True)
    paths = [Path("walk_01.png")]

    normal = cache.get(paths, config, mirror_horizontal=False)
    mirrored = cache.get(paths, config, mirror_horizontal=True)

    assert load_calls == [Path("walk_01.png")]
    assert normal[0].mirrored is False
    assert mirrored[0].mirrored is True
