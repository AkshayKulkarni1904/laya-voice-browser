"""Windows System Tray Icon for LayaBrowse."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

try:
    from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
    from PySide6.QtWidgets import QMenu, QSystemTrayIcon
    QT_TRAY_AVAILABLE = True
except ImportError:
    QT_TRAY_AVAILABLE = False


def _create_tray_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw vibrant rounded hexagon/spark badge
    painter.setBrush(QColor(99, 102, 241))
    painter.setPen(QColor(255, 255, 255, 200))
    painter.drawRoundedRect(4, 4, 24, 24, 6, 6)

    # Draw letter 'L'
    painter.setPen(QColor(255, 255, 255))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(12)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, "L")  # AlignCenter
    painter.end()

    return QIcon(pixmap)


class WindowsTrayManager:
    """Manages the Windows notification area tray icon and its context menu."""

    def __init__(
        self,
        *,
        on_toggle_voice: Callable[[], None] | None = None,
        on_open_browser: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ):
        self.on_toggle_voice = on_toggle_voice
        self.on_open_browser = on_open_browser
        self.on_quit = on_quit
        self.tray_icon: QSystemTrayIcon | None = None

    def setup(self, parent_widget=None):
        if not QT_TRAY_AVAILABLE or not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("System tray is not available on this environment")
            return

        icon = _create_tray_icon()
        self.tray_icon = QSystemTrayIcon(icon, parent_widget)
        self.tray_icon.setToolTip("LayaBrowse Windows: Voice-control Edge and Chrome")

        menu = QMenu(parent_widget)
        
        # Actions
        toggle_act = QAction("🎙️ Toggle Listening (Double-Tap Ctrl)", menu)
        if self.on_toggle_voice:
            toggle_act.triggered.connect(self.on_toggle_voice)
        menu.addAction(toggle_act)

        open_browser_act = QAction("🌐 Open Browser Window", menu)
        if self.on_open_browser:
            open_browser_act.triggered.connect(self.on_open_browser)
        menu.addAction(open_browser_act)

        menu.addSeparator()

        quit_act = QAction("❌ Quit LayaBrowse", menu)
        if self.on_quit:
            quit_act.triggered.connect(self.on_quit)
        menu.addAction(quit_act)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
