"""Download panel — collapsible bottom panel showing active and completed downloads."""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_DOWNLOAD_PANEL_QSS = f"""
QFrame#downloadPanel {{
    background-color: {Colors.BG_CARD};
    border-top: 1px solid {Colors.BORDER};
}}
QFrame#downloadItem {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 4px;
}}
QFrame#downloadItem:hover {{
    border-color: {Colors.PRIMARY}aa;
    background-color: {Colors.BG_ELEVATED};
}}
QFrame#completedItem {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 4px;
}}
QFrame#completedItem:hover {{
    border-color: {Colors.SUCCESS}aa;
    background-color: {Colors.BG_ELEVATED};
}}
"""


# ---------------------------------------------------------------------------
# Single download item (active)
# ---------------------------------------------------------------------------

class DownloadItemWidget(QFrame):
    """A single active download with progress bar and controls."""

    cancel_requested = pyqtSignal(int)  # Emits task_id
    pause_requested = pyqtSignal(int)   # Emits task_id

    def __init__(
        self,
        task_id: int,
        manga_title: str,
        chapter_range: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.task_id = task_id
        self.setObjectName("downloadItem")
        self._paused = False
        self._build_ui(manga_title, chapter_range)

    def _build_ui(self, title: str, chapters: str) -> None:
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header Row: Icon, Title & Format, Spacer, Percentage
        header = QHBoxLayout()
        header.setSpacing(8)

        self._title_label = QLabel(f"📖  {title} — {chapters}")
        self._title_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.TEXT};")
        header.addWidget(self._title_label)

        header.addStretch()

        self._pct_label = QLabel("0%")
        self._pct_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.PRIMARY};")
        header.addWidget(self._pct_label)

        layout.addLayout(header)

        # Progress Bar Row
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)  # We show percentage in label
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.PRIMARY};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self._progress_bar)

        # Bottom Row: Stats on the left, Control buttons on the right
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self._stats_label = QLabel("Waiting to start…")
        self._stats_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: 11px;")
        bottom.addWidget(self._stats_label)

        bottom.addStretch()

        self._pause_btn = QPushButton("⏸")
        self._pause_btn.setFixedSize(26, 26)
        self._pause_btn.setToolTip("Pause")
        self._pause_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                color: {Colors.TEXT};
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_ELEVATED};
                border-color: {Colors.PRIMARY};
            }}
        """)
        self._pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pause_btn.clicked.connect(lambda: self.pause_requested.emit(self.task_id))
        bottom.addWidget(self._pause_btn)

        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setFixedSize(26, 26)
        self._cancel_btn.setObjectName("dangerButton")
        self._cancel_btn.setToolTip("Cancel")
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                color: {Colors.ERROR};
            }}
            QPushButton:hover {{
                background-color: {Colors.ERROR}20;
                border-color: {Colors.ERROR};
            }}
        """)
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self.task_id))
        bottom.addWidget(self._cancel_btn)

        layout.addLayout(bottom)

    # ------------------------------------------------------------------
    # Public update methods
    # ------------------------------------------------------------------

    def update_progress(
        self,
        percent: int,
        speed: str = "",
        elapsed: str = "",
        pages: str = "",
    ) -> None:
        self._progress_bar.setValue(percent)
        self._pct_label.setText(f"{percent}%")
        parts = []
        if speed:
            parts.append(f"⬇ {speed}")
        if elapsed:
            parts.append(f"⏱ {elapsed}")
        if pages:
            parts.append(f"📦 {pages}")
        
        status_text = "  |  ".join(parts) if parts else "Downloading…"
        if self._paused:
            status_text = f"⏸ Paused  |  {status_text}"
        self._stats_label.setText(status_text)

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            self._pause_btn.setText("▶")
            self._pause_btn.setToolTip("Resume")
            self._progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {Colors.BG_DARK};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {Colors.MUTED};
                    border-radius: 3px;
                }}
            """)
            self._pct_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.MUTED};")
            # Update stats label to prefix Paused
            current = self._stats_label.text()
            if not current.startswith("⏸ Paused"):
                self._stats_label.setText(f"⏸ Paused  |  {current}")
        else:
            self._pause_btn.setText("⏸")
            self._pause_btn.setToolTip("Pause")
            self._progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {Colors.BG_DARK};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {Colors.PRIMARY};
                    border-radius: 3px;
                }}
            """)
            self._pct_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.PRIMARY};")
            # Remove Paused prefix from stats label
            current = self._stats_label.text()
            if current.startswith("⏸ Paused  |  "):
                self._stats_label.setText(current[13:])

    def set_completed(self) -> None:
        self._progress_bar.setValue(100)
        self._pct_label.setText("100%")
        self._pct_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.SUCCESS};")
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.SUCCESS};
                border-radius: 3px;
            }}
        """)
        self._stats_label.setText("✅ Completed")
        self._stats_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px; font-weight: bold;")
        self._pause_btn.hide()
        self._cancel_btn.hide()

    def set_error(self, message: str) -> None:
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.ERROR};
                border-radius: 3px;
            }}
        """)
        self._pct_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.ERROR};")
        self._stats_label.setText(f"❌ {message}")
        self._stats_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px; font-weight: bold;")
        self._pause_btn.hide()
        self._cancel_btn.setText("🗑")


# ---------------------------------------------------------------------------
# Completed download item (history row)
# ---------------------------------------------------------------------------

class CompletedItemWidget(QFrame):
    """A single completed download entry."""

    def __init__(
        self,
        manga_title: str,
        chapter_range: str,
        format: str,
        time_ago: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("completedItem")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Success checkmark and info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(6)
        
        icon = QLabel("✅")
        info_layout.addWidget(icon)
        
        label = QLabel(f"{manga_title} — {chapter_range}")
        label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {Colors.TEXT};")
        info_layout.addWidget(label)
        
        layout.addLayout(info_layout)
        layout.addStretch()

        # Format badge
        badge = QLabel(format.upper())
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.SUCCESS}20;
                color: {Colors.SUCCESS};
                border: 1px solid {Colors.SUCCESS}50;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(badge)

        if time_ago:
            time_label = QLabel(time_ago)
            time_label.setStyleSheet(f"font-size: 11px; color: {Colors.MUTED};")
            layout.addWidget(time_label)


# ---------------------------------------------------------------------------
# Download panel (collapsible)
# ---------------------------------------------------------------------------

class DownloadPanel(QWidget):
    """Collapsible bottom panel showing active downloads and recent completions."""

    cancel_requested = pyqtSignal(int)
    pause_requested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("downloadPanel")
        self.setStyleSheet(_DOWNLOAD_PANEL_QSS)
        self.setMinimumHeight(40)
        self.setMaximumHeight(300)
        self._expanded = True

        self._active_items: dict[int, DownloadItemWidget] = {}
        self._completed_count = 0

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar (always visible)
        header = QHBoxLayout()
        header.setContentsMargins(12, 6, 12, 6)

        self._title_label = QLabel("⬇️ Downloads")
        self._title_label.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {Colors.MUTED};"
        )
        header.addWidget(self._title_label)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"font-size: 12px; color: {Colors.MUTED};")
        header.addWidget(self._status_label)

        header.addStretch()

        self._toggle_btn = QPushButton("▼")
        self._toggle_btn.setFixedSize(28, 28)
        self._toggle_btn.setStyleSheet(
            f"background: transparent; border: none; color: {Colors.MUTED}; font-size: 14px;"
        )
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)
        header.addWidget(self._toggle_btn)

        layout.addLayout(header)

        # Content area (scrollable)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 0, 8, 4)
        self._content_layout.setSpacing(4)

        # Active section
        self._active_label = QLabel("Active")
        self._active_label.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {Colors.PRIMARY}; padding: 2px;"
        )
        self._content_layout.addWidget(self._active_label)

        self._active_container = QWidget()
        self._active_layout = QVBoxLayout(self._active_container)
        self._active_layout.setContentsMargins(0, 0, 0, 0)
        self._active_layout.setSpacing(4)
        self._content_layout.addWidget(self._active_container)

        # Completed section
        self._completed_label = QLabel("Completed")
        self._completed_label.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {Colors.SUCCESS}; padding: 2px;"
        )
        self._content_layout.addWidget(self._completed_label)

        self._completed_container = QWidget()
        self._completed_layout = QVBoxLayout(self._completed_container)
        self._completed_layout.setContentsMargins(0, 0, 0, 0)
        self._completed_layout.setSpacing(2)
        self._content_layout.addWidget(self._completed_container)

        self._content_layout.addStretch()

        layout.addWidget(self._content)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._toggle_btn.setText("▼" if self._expanded else "▶")

        if self._expanded:
            self.setMinimumHeight(120)
        else:
            self.setMinimumHeight(40)
            self.setMaximumHeight(40)

    def add_active_download(
        self, task_id: int, manga_title: str, chapter_range: str
    ) -> DownloadItemWidget:
        """Add a new active download item."""
        item = DownloadItemWidget(task_id, manga_title, chapter_range)
        item.cancel_requested.connect(self._on_cancel)
        item.pause_requested.connect(self._on_pause)
        self._active_items[task_id] = item
        self._active_layout.addWidget(item)
        self._update_status()
        self._active_label.show()
        self._active_container.show()
        return item

    def update_download_progress(
        self,
        task_id: int,
        percent: int,
        speed: str = "",
        elapsed: str = "",
        pages: str = "",
    ) -> None:
        """Update progress for an active download."""
        item = self._active_items.get(task_id)
        if item:
            item.update_progress(percent, speed, elapsed, pages)

    def complete_download(self, task_id: int, manga_title: str = "", chapter_range: str = "", fmt: str = "cbz") -> None:
        """Move a download from active to completed."""
        item = self._active_items.pop(task_id, None)
        if item:
            self._active_layout.removeWidget(item)
            item.deleteLater()

        completed = CompletedItemWidget(
            manga_title, chapter_range, fmt, time_ago="just now"
        )
        self._completed_layout.insertWidget(0, completed)
        self._completed_count += 1
        self._update_status()

    def remove_download(self, task_id: int) -> None:
        """Remove an active download."""
        item = self._active_items.pop(task_id, None)
        if item:
            self._active_layout.removeWidget(item)
            item.deleteLater()
        self._update_status()

    def set_download_paused(self, task_id: int, paused: bool) -> None:
        """Set an active download's paused state in the UI."""
        item = self._active_items.get(task_id)
        if item:
            item.set_paused(paused)

    def _update_status(self) -> None:
        active = len(self._active_items)
        if active > 0:
            self._status_label.setText(f"{active} active")
            self._active_label.show()
            self._active_container.show()
        else:
            self._status_label.setText("No active downloads")
            self._active_label.hide()
            self._active_container.hide()

        self._completed_label.setVisible(self._completed_count > 0)
        self._completed_container.setVisible(self._completed_count > 0)

    def _on_cancel(self, task_id: int) -> None:
        logger.info("Cancel requested for task %d", task_id)
        self.cancel_requested.emit(task_id)

    def _on_pause(self, task_id: int) -> None:
        logger.info("Pause requested for task %d", task_id)
        self.pause_requested.emit(task_id)
