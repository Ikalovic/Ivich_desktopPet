from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QMouseEvent, QPixmap
from PySide6.QtWidgets import QLabel, QMenu, QWidget

from desktop_pet.config import AnimationConfig


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
        pixmaps = [pixmap for path in frame_paths if not (pixmap := QPixmap(str(path))).isNull()]
        if not pixmaps:
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

    def __init__(self, width: int, height: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setGeometry(0, 0, width, height)
        self._drag_offset: QPoint | None = None
        self._press_pos: QPoint | None = None

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
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.drag_started.emit()
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            release_pos = event.globalPosition().toPoint()
            was_click = (
                self._press_pos is not None
                and (release_pos - self._press_pos).manhattanLength() < 5
            )
            self._drag_offset = None
            self._press_pos = None
            if was_click:
                self.clicked.emit()
            else:
                self.drag_finished.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)
        menu.exec(global_pos)
