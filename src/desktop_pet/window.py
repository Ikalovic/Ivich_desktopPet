from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QPoint, QElapsedTimer, QTimer, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap, QTransform
from PySide6.QtWidgets import QLabel, QMenu, QWidget

from desktop_pet.animation_cache import FrameCache
from desktop_pet.config import AnimationConfig
from desktop_pet.interaction import (
    DragBehaviorTracker,
    classify_drag_behavior,
    should_emit_drag_behavior,
)


LOGGER = logging.getLogger(__name__)
_DRAG_DIRECTION_WINDOW_MS = 150
_DRAG_DIRECTION_MARGIN_PX = 3


class SpriteAnimator(QWidget):
    frame_changed = Signal(QPixmap)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)
        self._frames: list[QPixmap] = []
        self._frame_cache: FrameCache[QPixmap] = FrameCache(
            load_frame=self._load_pixmap,
            mirror_frame=self._mirror_pixmap,
        )
        self._index = 0
        self._loop = True

    def play(
        self,
        frame_paths: list[Path],
        config: AnimationConfig,
        *,
        mirror_horizontal: bool = False,
    ) -> bool:
        pixmaps = self._frame_cache.get(
            frame_paths,
            config,
            mirror_horizontal=mirror_horizontal,
        )
        if not pixmaps:
            self.stop()
            self._frames = []
            self._index = 0
            return False
        self._frames = pixmaps
        self._index = 0
        self._loop = config.loop
        interval_ms = max(1, int(1000 / max(1, config.fps)))
        self.frame_changed.emit(self._frames[self._index])
        self._timer.start(interval_ms)
        return True

    def stop(self) -> None:
        self._timer.stop()

    def _load_pixmap(self, path: Path) -> QPixmap | None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            LOGGER.warning("Could not load frame: %s", path)
            return None
        return pixmap

    def _mirror_pixmap(self, pixmap: QPixmap) -> QPixmap:
        return pixmap.transformed(QTransform().scale(-1, 1))

    def _next_frame(self) -> None:
        if not self._frames:
            return
        self._index += 1
        if self._index >= len(self._frames):
            if not self._loop:
                self._index = len(self._frames) - 1
                self._timer.stop()
            else:
                self._index = 0
        self.frame_changed.emit(self._frames[self._index])


class PetWindow(QWidget):
    drag_started = Signal(bool)
    drag_still_requested = Signal()
    drag_finished = Signal()
    clicked = Signal()

    _DRAG_THRESHOLD_PX = 5

    def __init__(self, width: int, height: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setGeometry(0, 0, width, height)
        self._drag_offset: QPoint | None = None
        self._press_pos: QPoint | None = None
        self._last_drag_pos: QPoint | None = None
        self._is_dragging = False
        self._drag_behavior: str | None = None
        self._drag_mirror_horizontal: bool | None = None
        self._drag_clock = QElapsedTimer()
        self._drag_tracker = DragBehaviorTracker(
            window_ms=_DRAG_DIRECTION_WINDOW_MS,
            threshold_px=self._DRAG_THRESHOLD_PX,
            direction_margin_px=_DRAG_DIRECTION_MARGIN_PX,
        )

        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

    def set_frame(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)

    def set_placeholder(self, text: str) -> None:
        self._label.setText(text)
        self._label.setStyleSheet(
            "color: #334155; background: rgba(255, 255, 255, 180); border: 1px solid #94a3b8;"
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._last_drag_pos = self._press_pos
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._is_dragging = False
            self._drag_behavior = None
            self._drag_mirror_horizontal = None
            self._drag_tracker.reset()
            self._drag_clock.start()
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._press_pos is not None
            and self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            current_pos = event.globalPosition().toPoint()
            total_delta = current_pos - self._press_pos
            if not self._is_dragging and total_delta.manhattanLength() <= self._DRAG_THRESHOLD_PX:
                event.accept()
                return
            if not self._is_dragging:
                self._is_dragging = True

            step_delta = current_pos - (self._last_drag_pos or self._press_pos)
            self._last_drag_pos = current_pos
            next_behavior = self._drag_tracker.update(
                delta_x=step_delta.x(),
                delta_y=step_delta.y(),
                timestamp_ms=self._drag_clock.elapsed(),
            )
            if next_behavior is not None and should_emit_drag_behavior(
                current_name=self._drag_behavior,
                current_mirror_horizontal=self._drag_mirror_horizontal,
                next_behavior=next_behavior,
            ):
                self._drag_behavior = next_behavior.name
                self._drag_mirror_horizontal = next_behavior.mirror_horizontal
                if next_behavior.name == "drag":
                    self.drag_started.emit(next_behavior.mirror_horizontal)
                else:
                    self.drag_still_requested.emit()
            self.move(current_pos - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragging = self._is_dragging
            release_pos = event.globalPosition().toPoint()
            drag_behavior = "drag_still"
            if self._press_pos is not None:
                delta = release_pos - self._press_pos
                drag_behavior = classify_drag_behavior(
                    delta_x=delta.x(),
                    delta_y=delta.y(),
                    threshold_px=self._DRAG_THRESHOLD_PX,
                )
            self._drag_offset = None
            self._press_pos = None
            self._last_drag_pos = None
            self._is_dragging = False
            self._drag_behavior = None
            self._drag_mirror_horizontal = None
            self._drag_tracker.reset()
            if was_dragging:
                self.drag_finished.emit()
            elif drag_behavior == "drag_still":
                self.drag_still_requested.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        menu.exec(global_pos)
