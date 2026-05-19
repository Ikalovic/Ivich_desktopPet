# Python Qt Desktop Pet Design

## Goal

Build a Windows-first desktop pet MVP in Python with PySide6. The pet displays PNG sequence animations from the existing `assets/` tree, appears as a transparent always-on-top desktop window, supports drag movement, click feedback, simple state changes, and right-click exit.

## Scope

In scope for the MVP:

- PySide6 desktop app for Windows-first use.
- Transparent, frameless, always-on-top pet window.
- PNG sequence playback for character states.
- Left-drag movement.
- Left-click feedback.
- Right-click menu with Exit.
- `idle`, `walk`, `sleep`, and `drag` state support.
- Automatic frame discovery when `frames` is `0` in `assets/config/animation.json`.
- Non-GUI tests for configuration loading, frame scanning, and state transitions.

Out of scope for the MVP:

- System tray integration.
- Start-on-boot.
- Audio.
- AI behavior.
- Complex pathfinding.
- Packaging into an installer.
- Cross-platform polishing beyond keeping the code reasonably portable.

## Architecture

The application uses a small modular PySide6 architecture:

- `main.py` starts `QApplication`, loads configuration, creates the pet window, and enters the event loop.
- `PetWindow` owns the Qt window behavior: transparent frameless display, always-on-top flag, current pixmap rendering, mouse drag handling, click handling, and right-click menu.
- `SpriteAnimator` loads and caches PNG frames, advances frames by fps using a Qt timer, supports loop and non-loop animations, and emits the current frame to the window.
- `ConfigLoader` reads `assets/config/animation.json`, `assets/config/state.json`, and `assets/config/settings.json`, then resolves project-relative paths.
- `PetStateMachine` validates state transitions and chooses the animation for each state.

The modules are intentionally small so later features such as tray menu, audio, and more behaviors can be added without rewriting the animation core.

## Resources

The project keeps the existing asset layout:

- `assets/character/idle/idle_01.png`
- `assets/character/walk/walk_01.png`
- `assets/character/sleep/sleep_01.png`
- `assets/character/drag/drag_01.png`

Animation metadata continues to live in `assets/config/animation.json`. Each animation entry uses:

- `pattern`: project-relative printf-style path such as `assets/character/idle/idle_%02d.png`
- `frames`: explicit frame count, or `0` for automatic discovery
- `fps`: playback speed
- `loop`: whether playback repeats

When `frames` is `0`, frame discovery starts at frame `01` and increments until the next expected file is missing. This makes naming gaps visible; for example, `idle_01.png` plus `idle_03.png` without `idle_02.png` resolves to a one-frame animation and should log the missing sequence point during development.

`assets/config/settings.json` supplies the base canvas size. The initial MVP uses `baseWidth` and `baseHeight` as the window size, with the current assets expected to be transparent 512 x 512 PNGs anchored bottom-center.

## State And Interaction

The default state is `idle`, which loops the idle PNG sequence.

User interaction:

- Left mouse press and movement enters `drag`.
- During drag, the window follows the mouse cursor.
- Left mouse release returns to `idle`.
- Left mouse click triggers click feedback. If an expression or feedback animation exists, it may be shown briefly; otherwise the pet remains in `idle`.
- Right mouse click opens a context menu with `Exit`.

Automatic behavior:

- After a configurable idle period, the pet may enter `sleep` if sleep frames exist.
- Click or drag wakes the pet back to `idle`.
- `walk` is supported as a state and animation, but MVP movement can be timer-driven or manually triggered later; complex pathfinding is not part of this spec.

## Error Handling

Startup should fail with a clear message if required JSON config files are missing or malformed.

Animation errors are handled per state:

- If a non-idle state has no usable PNG frames, that state is unavailable and transitions to it fall back to `idle`.
- If `idle` has no usable PNG frames, the app shows a simple debug placeholder window and logs that the idle resource is missing.
- If a specific image fails to load, the loader skips that image and records its path in the log.

The app should prefer explicit, actionable errors over silent failure.

## Testing

Automated tests focus on logic that does not require a GUI event loop:

- Loading valid config files.
- Rejecting malformed config files with clear exceptions.
- Discovering PNG frames from `pattern` when `frames` is `0`.
- Respecting explicit `frames` when configured.
- Falling back to `idle` when a requested state has no usable animation.
- Validating allowed and disallowed state transitions from `state.json`.

Manual verification covers Qt behavior:

- The app opens a transparent, frameless, always-on-top window.
- Idle frames loop visibly.
- The pet can be dragged with the left mouse button.
- Releasing drag returns to idle.
- Right-click menu exits the application.

## Acceptance Criteria

The MVP is complete when:

- Running the app starts a PySide6 desktop pet window on Windows.
- Existing `assets/character/idle/idle_*.png` frames play as a loop.
- Adding more sequential PNG frames automatically affects playback without editing `frames`.
- Drag and right-click exit work.
- Missing optional state resources do not crash the app.
- Non-GUI tests pass for config loading, frame scanning, and state-machine behavior.
