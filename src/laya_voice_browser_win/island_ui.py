"""Windows 11 Fluent Floating Island Overlay ("Dynamic Island for Windows").

Built with PySide6 for hardware-accelerated, transparent, floating glassmorphism UI.
Displays:
1. Animated glowing microphone and waveform audio visualizer
2. Live streaming speech transcript
3. Execution action status pill
4. Confirmation and candidate disambiguation badges
"""

from __future__ import annotations

import logging
import math
import sys
import threading
from typing import Any

logger = logging.getLogger(__name__)

try:
    from PySide6.QtCore import QObject, QPoint, QPropertyAnimation, QRect, QSize, Qt, QTimer, Signal
    from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
    from PySide6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QVBoxLayout,
        QWidget,
    )
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


class IslandSignals(QObject):
    update_status = Signal(str, str)  # status_text, state ("listening", "thinking", "executing", "confirm", "idle")
    update_transcript = Signal(str)
    update_action = Signal(str)
    update_audio_level = Signal(float)
    show_island = Signal()
    hide_island = Signal()


class WaveformWidget(QWidget):
    """Animated micro-waveform bars pulsing to user voice input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 24)
        self.level = 0.2
        self.phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def set_level(self, level: float):
        self.level = max(0.1, min(1.0, level))

    def _tick(self):
        self.phase += 0.2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        num_bars = 4
        spacing = 4
        bar_w = 4
        max_h = 18
        mid_y = self.height() / 2

        for i in range(num_bars):
            # Dynamic height with phase variation
            sin_mod = math.sin(self.phase + i * 0.9)
            h = max(4.0, (self.level * max_h) * (0.6 + 0.4 * sin_mod))
            x = i * (bar_w + spacing) + 8
            y = mid_y - h / 2

            gradient = QLinearGradient(x, y, x, y + h)
            gradient.setColorAt(0.0, QColor(99, 102, 241))  # Indigo
            gradient.setColorAt(1.0, QColor(56, 189, 248))  # Cyan

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRect(int(x), int(y), bar_w, int(h)), 2, 2)


class DynamicIslandWindow(QWidget):
    """The floating top-center notch window on Windows."""

    def __init__(self, signals: IslandSignals):
        super().__init__()
        self.signals = signals
        self._init_window()
        self._init_ui()
        self._connect_signals()

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(520)
        self.setFixedHeight(54)
        self._reposition()

    def _reposition(self):
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = (geom.width() - self.width()) // 2
            y = 16  # Top offset
            self.move(x, y)

    def _init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(18, 8, 18, 8)
        self.layout.setSpacing(12)

        # Waveform
        self.waveform = WaveformWidget(self)
        self.layout.addWidget(self.waveform)

        # Status badge
        self.status_badge = QLabel("Listening", self)
        self.status_badge.setStyleSheet(
            "background: rgba(99, 102, 241, 0.25); color: #818cf8; font-weight: 600; "
            "font-size: 11px; padding: 3px 8px; border-radius: 8px;"
        )
        self.layout.addWidget(self.status_badge)

        # Live Transcript
        self.transcript_label = QLabel("Say a command…", self)
        self.transcript_label.setStyleSheet(
            "color: #f3f4f6; font-size: 13px; font-weight: 500;"
        )
        self.transcript_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.layout.addWidget(self.transcript_label, 1)

        # Action preview pill
        self.action_label = QLabel("", self)
        self.action_label.setStyleSheet(
            "background: rgba(34, 197, 94, 0.2); color: #4ade80; font-weight: 600; "
            "font-size: 11px; padding: 3px 8px; border-radius: 8px;"
        )
        self.action_label.setVisible(False)
        self.layout.addWidget(self.action_label)

    def _connect_signals(self):
        self.signals.update_status.connect(self._on_update_status)
        self.signals.update_transcript.connect(self._on_update_transcript)
        self.signals.update_action.connect(self._on_update_action)
        self.signals.update_audio_level.connect(self.waveform.set_level)
        self.signals.show_island.connect(self.show)
        self.signals.hide_island.connect(self.hide)

    def _on_update_status(self, text: str, state: str):
        self.status_badge.setText(text)
        colors = {
            "listening": ("rgba(99, 102, 241, 0.25)", "#818cf8"),
            "thinking": ("rgba(234, 179, 8, 0.25)", "#fde047"),
            "executing": ("rgba(34, 197, 94, 0.25)", "#4ade80"),
            "confirm": ("rgba(239, 68, 68, 0.25)", "#f87171"),
            "idle": ("rgba(156, 163, 175, 0.25)", "#9ca3af"),
        }
        bg, fg = colors.get(state, colors["listening"])
        self.status_badge.setStyleSheet(
            f"background: {bg}; color: {fg}; font-weight: 600; font-size: 11px; padding: 3px 8px; border-radius: 8px;"
        )

    def _on_update_transcript(self, text: str):
        display = text if text else "Listening…"
        if len(display) > 55:
            display = display[:52] + "…"
        self.transcript_label.setText(display)

    def _on_update_action(self, action_summary: str):
        if action_summary:
            self.action_label.setText(action_summary)
            self.action_label.setVisible(True)
        else:
            self.action_label.setVisible(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Glassmorphic Dark Container
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(1, 1, -1, -1), 22, 22)

        # Gradient background
        bg_gradient = QLinearGradient(0, 0, 0, rect.height())
        bg_gradient.setColorAt(0.0, QColor(18, 18, 24, 235))
        bg_gradient.setColorAt(1.0, QColor(10, 10, 15, 245))

        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1.2))
        painter.drawPath(path)


class IslandApp:
    """Thread-safe UI coordinator that can be driven from the controller."""

    def __init__(self):
        self._app: QApplication | None = None
        self._window: DynamicIslandWindow | None = None
        self._signals: IslandSignals | None = None
        self._thread: threading.Thread | None = None
        self._ready_event = threading.Event()

    def start(self):
        if not QT_AVAILABLE:
            logger.warning("PySide6 not available; floating island UI disabled")
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=3.0)

    def _run(self):
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        self._app = app
        self._signals = IslandSignals()
        self._window = DynamicIslandWindow(self._signals)
        self._window.show()
        self._ready_event.set()
        app.exec()

    def set_status(self, text: str, state: str = "listening"):
        if self._signals:
            self._signals.update_status.emit(text, state)

    def set_transcript(self, text: str):
        if self._signals:
            self._signals.update_transcript.emit(text)

    def set_action(self, action_summary: str):
        if self._signals:
            self._signals.update_action.emit(action_summary)

    def set_audio_level(self, level: float):
        if self._signals:
            self._signals.update_audio_level.emit(level)

    def show(self):
        if self._signals:
            self._signals.show_island.emit()

    def hide(self):
        if self._signals:
            self._signals.hide_island.emit()
