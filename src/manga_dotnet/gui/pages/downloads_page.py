"""Downloads page — active downloads with progress + completed list."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors
from ..widgets.download_panel import DownloadItemWidget, CompletedItemWidget


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_DOWNLOADS_PAGE_QSS = f"""
QLabel#sectionTitle {{
    font-size: 15px;
    font-weight: bold;
    color: {Colors.TEXT};
    padding: 6px 0;
}}
QLabel#emptyState {{
    color: {Colors.MUTED};
    font-size: 15px;
    padding: 40px;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
"""


# ---------------------------------------------------------------------------
# Downloads page
# ---------------------------------------------------------------------------

class DownloadsPage(QWidget):
    """Downloads page showing active and completed downloads.

    This is a full-page version of the download panel, with more detail
    and scrollable content.
    """

    cancel_requested = pyqtSignal(int)
    pause_requested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_DOWNLOADS_PAGE_QSS)
        self._active_items: dict[int, DownloadItemWidget] = {}
        self._completed_count = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # Header
        header = QLabel("⬇️ Downloads")
        header.setObjectName("headingLabel")
        header.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {Colors.TEXT};"
        )
        layout.addWidget(header)

        # Main Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(24)

        # Active Section Container
        active_sec = QWidget()
        active_sec_layout = QVBoxLayout(active_sec)
        active_sec_layout.setContentsMargins(0, 0, 0, 0)
        active_sec_layout.setSpacing(8)

        self._active_title = QLabel("Active Downloads")
        self._active_title.setObjectName("sectionTitle")
        self._active_title.setStyleSheet(f"color: {Colors.PRIMARY};")
        active_sec_layout.addWidget(self._active_title)

        self._active_container = QWidget()
        self._active_layout = QVBoxLayout(self._active_container)
        self._active_layout.setContentsMargins(0, 0, 0, 0)
        self._active_layout.setSpacing(10)
        active_sec_layout.addWidget(self._active_container)

        self._empty_active = QLabel("No active downloads running")
        self._empty_active.setObjectName("emptyState")
        self._empty_active.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_sec_layout.addWidget(self._empty_active)

        scroll_layout.addWidget(active_sec)

        # Completed Section Container
        completed_sec = QWidget()
        completed_sec_layout = QVBoxLayout(completed_sec)
        completed_sec_layout.setContentsMargins(0, 0, 0, 0)
        completed_sec_layout.setSpacing(8)

        self._completed_title = QLabel("Completed Downloads")
        self._completed_title.setObjectName("sectionTitle")
        self._completed_title.setStyleSheet(f"color: {Colors.SUCCESS};")
        completed_sec_layout.addWidget(self._completed_title)

        self._completed_container = QWidget()
        self._completed_layout = QVBoxLayout(self._completed_container)
        self._completed_layout.setContentsMargins(0, 0, 0, 0)
        self._completed_layout.setSpacing(6)
        completed_sec_layout.addWidget(self._completed_container)

        self._empty_completed = QLabel("No completed downloads in this session")
        self._empty_completed.setObjectName("emptyState")
        self._empty_completed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        completed_sec_layout.addWidget(self._empty_completed)

        scroll_layout.addWidget(completed_sec)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_active_download(
        self, task_id: int, manga_title: str, chapter_range: str
    ) -> DownloadItemWidget:
        """Add a new active download."""
        self._empty_active.hide()

        item = DownloadItemWidget(task_id, manga_title, chapter_range)
        item.cancel_requested.connect(self._on_cancel)
        item.pause_requested.connect(self._on_pause)
        self._active_items[task_id] = item
        self._active_layout.addWidget(item)

        count = len(self._active_items)
        self._active_title.setText(f"Active Downloads ({count})")
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

    def complete_download(
        self,
        task_id: int,
        manga_title: str = "",
        chapter_range: str = "",
        fmt: str = "cbz",
    ) -> None:
        """Move a download from active to completed."""
        item = self._active_items.pop(task_id, None)
        if item:
            self._active_layout.removeWidget(item)
            item.deleteLater()

        # Add completed entry
        completed = CompletedItemWidget(
            manga_title, chapter_range, fmt, time_ago="just now"
        )
        self._completed_layout.insertWidget(0, completed)
        self._completed_count += 1

        self._completed_title.setText(f"Completed Downloads ({self._completed_count})")
        self._empty_completed.hide()

        # Update active section
        count = len(self._active_items)
        if count == 0:
            self._active_title.setText("Active Downloads")
            self._empty_active.show()
        else:
            self._active_title.setText(f"Active Downloads ({count})")

    def remove_download(self, task_id: int) -> None:
        """Remove an active download."""
        item = self._active_items.pop(task_id, None)
        if item:
            self._active_layout.removeWidget(item)
            item.deleteLater()

        count = len(self._active_items)
        if count == 0:
            self._active_title.setText("Active Downloads")
            self._empty_active.show()
        else:
            self._active_title.setText(f"Active Downloads ({count})")

    def set_download_paused(self, task_id: int, paused: bool) -> None:
        """Set an active download's paused state in the UI."""
        item = self._active_items.get(task_id)
        if item:
            item.set_paused(paused)

    def _on_cancel(self, task_id: int) -> None:
        self.cancel_requested.emit(task_id)

    def _on_pause(self, task_id: int) -> None:
        self.pause_requested.emit(task_id)
