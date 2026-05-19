from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QLabel, QMenu, QWidget

from desktop_pet.config import AnimationConfig


LOGGER = logging.getLogger(__name__)


class SpriteAnimator(QWidget):
    frame_changed = Signal(QPixmap)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)
        self._frames: list[QPixmap] = []
        self._index = 0
        self._loop = True

    def play(self, frame_paths: list[Path], config: AnimationConfig) -> bool:
        pixmaps: list[QPixmap] = []
        for path in frame_paths:
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                LOGGER.warning("Animation %s could not load frame: %s", config.name, path)
            else:
                pixmaps.append(pixmap)
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
    drag_started = Signal()
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
        self._is_dragging = False

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
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._is_dragging = False
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
            if not self._is_dragging:
                distance = (current_pos - self._press_pos).manhattanLength()
                if distance <= self._DRAG_THRESHOLD_PX:
                    event.accept()
                    return
                self._is_dragging = True
                self.drag_started.emit()
            self.move(current_pos - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragging = self._is_dragging
            release_pos = event.globalPosition().toPoint()
            moved_too_far_for_click = (
                self._press_pos is not None
                and (release_pos - self._press_pos).manhattanLength() > self._DRAG_THRESHOLD_PX
            )
            self._drag_offset = None
            self._press_pos = None
            self._is_dragging = False
            if was_dragging:
                self.drag_finished.emit()
            elif not moved_too_far_for_click:
                self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        menu.exec(global_pos)
