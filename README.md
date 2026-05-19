# Ivich Desktop Pet

Windows-first Python/PySide6 desktop pet using PNG sequence frames.

## Setup

```bash
python -m pip install -e ".[dev]"
```

## Run

```bash
desktop-pet
```

Alternatively, run the package module directly:

```bash
python -m desktop_pet
```

## Test

```bash
python -m pytest -q
```

## Assets

Animation assets are loaded from each animation's `pattern` in `assets/config/animation.json`,
such as `assets/character/idle/idle_%02d.png` and nested character or effects patterns.
Animation speed and looping are configured in `assets/config/animation.json`.
When `frames` is `0`, the app scans sequential files from `01` until the first missing frame.
