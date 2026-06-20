"""Open URL page — paste a manga URL to view its info and chapters."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors
from .manga_detail_page import MangaDetailPage

if TYPE_CHECKING:
    from manga_dotnet.api.client import MangaDotNetClient


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

_MANGADOT_URL_RE = re.compile(
    r"mangadot\.net/(?:manga/)?(\d+)",
    re.IGNORECASE,
)


def extract_manga_id(url: str) -> int | None:
    url = url.strip()
    if url.isdigit():
        return int(url)
    match = _MANGADOT_URL_RE.search(url)
    if match:
        return int(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Background manga loader
# ---------------------------------------------------------------------------

class _MangaLoader(QThread):
    loaded = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, client, manga_id: int, parent=None) -> None:
        super().__init__(parent)
        self._client = client
        self._manga_id = manga_id

    def run(self) -> None:
        try:
            from manga_dotnet.api.manga import MangaAPI
            api = MangaAPI(self._client)
            info = api.get_info(self._manga_id)
            self.loaded.emit(info)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Open URL page
# ---------------------------------------------------------------------------

_OPEN_URL_QSS = f"""
QLineEdit#urlInput {{
    background-color: {Colors.BG_CARD};
    border: 2px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 15px;
    color: {Colors.TEXT};
}}
QLineEdit#urlInput:focus {{
    border-color: {Colors.PRIMARY};
}}
QPushButton#openBtn {{
    background-color: {Colors.PRIMARY};
    border: none;
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 12px 32px;
    border-radius: 8px;
}}
QPushButton#openBtn:hover {{
    background-color: {Colors.PRIMARY}CC;
}}
"""


class OpenUrlPage(QWidget):
    """Page where users paste a manga URL to view its details and chapters."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_OPEN_URL_QSS)
        self._client = None
        self._loader = None
        self._build_ui()

    def set_client(self, client) -> None:
        self._client = client
        self._detail.set_client(client)

    def set_default_format(self, fmt: str) -> None:
        """Pre-select the default export format."""
        self._detail.set_default_format(fmt)

    def set_default_language(self, lang: str) -> None:
        """Pre-select the default language filter."""
        self._detail.set_default_language(lang)

    def set_default_quality(self, quality: str) -> None:
        """Pre-select the default quality."""
        self._detail.set_default_quality(quality)

    def set_delete_images(self, delete: bool) -> None:
        """Pre-set the delete images after export checkbox."""
        self._detail.set_delete_images(delete)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stack: input form ↔ manga detail
        self._stack = __import__("PyQt6.QtWidgets", fromlist=["QStackedWidget"]).QStackedWidget()

        # Page 0: URL input
        input_page = QWidget()
        ip_layout = QVBoxLayout(input_page)
        ip_layout.setContentsMargins(40, 60, 40, 40)
        ip_layout.setSpacing(20)

        header = QLabel("🔗 Open Manga URL")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {Colors.TEXT};")
        ip_layout.addWidget(header)

        subtitle = QLabel("Paste a MangaDotNet URL or enter a manga ID")
        subtitle.setStyleSheet(f"font-size: 14px; color: {Colors.MUTED};")
        ip_layout.addWidget(subtitle)

        ip_layout.addSpacing(20)

        # Input row
        row = QHBoxLayout()
        row.setSpacing(12)

        self._url_input = QLineEdit()
        self._url_input.setObjectName("urlInput")
        self._url_input.setPlaceholderText("https://mangadot.net/manga/166  or  just 166")
        self._url_input.returnPressed.connect(self._on_open)
        row.addWidget(self._url_input, stretch=1)

        self._open_btn = QPushButton("Open")
        self._open_btn.setObjectName("openBtn")
        self._open_btn.setFixedWidth(100)
        self._open_btn.clicked.connect(self._on_open)
        row.addWidget(self._open_btn)

        ip_layout.addLayout(row)

        self._status = QLabel("")
        self._status.setStyleSheet(f"font-size: 13px; color: {Colors.MUTED};")
        ip_layout.addWidget(self._status)

        ip_layout.addStretch()
        self._stack.addWidget(input_page)

        # Page 1: Manga detail with back button
        self._detail_container = QWidget()
        dc_layout = QVBoxLayout(self._detail_container)
        dc_layout.setContentsMargins(0, 0, 0, 0)
        dc_layout.setSpacing(0)

        # Back button bar
        back_bar = QWidget()
        back_bar.setStyleSheet(f"background: {Colors.BG_CARD}; border-bottom: 1px solid {Colors.BORDER}; padding: 4px;")
        back_layout = QHBoxLayout(back_bar)
        back_layout.setContentsMargins(8, 4, 8, 4)

        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet(
            f"background: transparent; border: none; color: {Colors.PRIMARY}; "
            f"font-size: 13px; font-weight: bold; padding: 4px 8px;"
        )
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self._go_back)
        back_layout.addWidget(back_btn)
        back_layout.addStretch()

        dc_layout.addWidget(back_bar)

        self._detail = MangaDetailPage()
        dc_layout.addWidget(self._detail, stretch=1)

        self._stack.addWidget(self._detail_container)

        layout.addWidget(self._stack)

    def _on_open(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            self._status.setText("Please enter a URL or manga ID")
            return

        manga_id = extract_manga_id(url)
        if manga_id is None:
            self._status.setText("❌ Could not extract manga ID from that URL")
            return

        if self._client is None:
            self._status.setText("API client not ready — waiting for Cloudflare…")
            return

        self._status.setText(f"⏳ Loading manga {manga_id}…")
        self._open_btn.setEnabled(False)

        self._loader = _MangaLoader(self._client, manga_id, parent=self)
        self._loader.loaded.connect(self._on_loaded)
        self._loader.error.connect(self._on_error)
        self._loader.start()

    def _on_loaded(self, info) -> None:
        self._open_btn.setEnabled(True)
        self._status.setText("")
        self._detail.update_info(info)
        self._detail.load_manga(info.id, title=info.title)
        self._stack.setCurrentIndex(1)

    def _go_back(self) -> None:
        """Return to the URL input page."""
        self._stack.setCurrentIndex(0)

    def _on_error(self, error: str) -> None:
        self._open_btn.setEnabled(True)
        self._status.setText(f"❌ {error}")
