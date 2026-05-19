# Ivich Desktop Pet

Windows-first Python/PySide6 desktop pet using PNG sequence frames.

## Setup

```bash
python -m pip install -e ".[dev]"
```

## Run

```bash
python -m desktop_pet
```

## Test

```bash
python -m pytest -q
```

## Assets

Character animations are loaded from `assets/character/<state>/<state>_NN.png`.
Animation speed and looping are configured in `assets/config/animation.json`.
When `frames` is `0`, the app scans sequential files from `01` until the first missing frame.
