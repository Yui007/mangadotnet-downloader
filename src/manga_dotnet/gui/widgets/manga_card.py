"""Manga card widget — clickable card with cover image, title, and metadata."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors

if TYPE_CHECKING:
    from manga_dotnet.api.client import MangaDotNetClient
    from manga_dotnet.core.models import MangaResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Card stylesheet
# ---------------------------------------------------------------------------

_CARD_QSS = f"""
QFrame#mangaCard {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px;
}}
QFrame#mangaCard:hover {{
    border-color: {Colors.PRIMARY}60;
    background-color: {Colors.BG_ELEVATED};
}}
"""


# ---------------------------------------------------------------------------
# Cover image loader (runs in a background thread, uses browser fetch)
# ---------------------------------------------------------------------------

class _CoverLoader(QThread):
    loaded = pyqtSignal(QPixmap)
    failed = pyqtSignal()

    def __init__(self, url: str, client: MangaDotNetClient | None = None, parent=None) -> None:
        super().__init__(parent)
        self._url = url
        self._client = client

    def run(self) -> None:
        try:
            # Try loading through the browser first (CF bypass)
            if self._client and self._client._driver:
                self._load_via_browser()
            else:
                self._load_via_httpx()
        except Exception:
            self.failed.emit()

    def _load_via_browser(self) -> None:
        """Load cover image through the browser's fetch() for CF bypass."""
        import base64
        script = f"""
        async function _fetchImg() {{
            const r = await fetch("{self._url}", {{
                credentials: 'include',
                headers: {{ 'x-requested-with': 'XMLHttpRequest' }}
            }});
            if (!r.ok) throw new Error("HTTP " + r.status);
            const buf = await r.arrayBuffer();
            const bytes = new Uint8Array(buf);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {{
                binary += String.fromCharCode(bytes[i]);
            }}
            return btoa(binary);
        }}
        return await _fetchImg();
        """
        b64 = self._client._driver.execute_script(script)
        data = base64.b64decode(b64)
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if not pixmap.isNull():
            self.loaded.emit(pixmap)
        else:
            self.failed.emit()

    def _load_via_httpx(self) -> None:
        """Fallback: load via httpx."""
        import httpx
        resp = httpx.get(self._url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        pixmap = QPixmap()
        pixmap.loadFromData(resp.content)
        if not pixmap.isNull():
            self.loaded.emit(pixmap)
        else:
            self.failed.emit()


# ---------------------------------------------------------------------------
# Manga card widget
# ---------------------------------------------------------------------------

class MangaCard(QFrame):
    """Clickable manga card with cover image, title, and metadata row.

    Emits ``clicked(int)`` with the manga ID when the card is pressed.
    """

    clicked = pyqtSignal(int)

    CARD_WIDTH = 200
    CARD_HEIGHT = 320
    COVER_WIDTH = 184
    COVER_HEIGHT = 240

    def __init__(self, manga: MangaResult, client: MangaDotNetClient | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manga_id = manga.id
        self._client = client
        self.setObjectName("mangaCard")
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setStyleSheet(_CARD_QSS)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._loader: _CoverLoader | None = None
        self._build_ui(manga)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, manga: MangaResult) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Cover image placeholder
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(self.COVER_WIDTH, self.COVER_HEIGHT)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet(
            f"background: {Colors.BG_DARK}; border-radius: 8px; font-size: 36px;"
        )
        self.cover_label.setText("📖")
        layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Title
        title_label = QLabel(manga.title)
        title_label.setWordWrap(True)
        title_label.setMaximumHeight(32)
        title_label.setStyleSheet(
            f"font-weight: bold; font-size: 12px; color: {Colors.TEXT};"
        )
        layout.addWidget(title_label)

        # Metadata row
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        if manga.rating is not None:
            rating_label = QLabel(f"⭐ {manga.rating:.0f}")
            rating_label.setStyleSheet(
                f"color: {Colors.WARNING}; font-size: 11px;"
            )
            meta_layout.addWidget(rating_label)

        if manga.status:
            status_label = QLabel(manga.status)
            status_label.setStyleSheet(
                f"color: {Colors.SECONDARY}; font-size: 11px;"
            )
            meta_layout.addWidget(status_label)

        if manga.chapter_count:
            ch_label = QLabel(f"{manga.chapter_count} ch")
            ch_label.setStyleSheet(
                f"color: {Colors.MUTED}; font-size: 11px;"
            )
            meta_layout.addWidget(ch_label)

        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # Load cover asynchronously
        if manga.photo:
            url = manga.cover_url
            self._loader = _CoverLoader(url, client=self._client, parent=self)
            self._loader.loaded.connect(self._on_cover_loaded)
            self._loader.start()

    # ------------------------------------------------------------------
    # Cover loading
    # ------------------------------------------------------------------

    def _on_cover_loaded(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            self.COVER_WIDTH,
            self.COVER_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cover_label.setPixmap(scaled)

    # ------------------------------------------------------------------
    # Click handling
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.manga_id)
        super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Stop the cover loader thread if running."""
        if self._loader and self._loader.isRunning():
            self._loader.quit()
            self._loader.wait(2000)
            self._loader = None


# ---------------------------------------------------------------------------
# Manga row widget — horizontal layout for search results
# ---------------------------------------------------------------------------

_ROW_QSS = f"""
QFrame#mangaRow {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px;
}}
QFrame#mangaRow:hover {{
    border-color: {Colors.PRIMARY}60;
    background-color: {Colors.BG_ELEVATED};
}}
"""


class MangaRow(QFrame):
    """Clickable horizontal manga row — cover on left, info on right.

    Emits ``clicked(int)`` with the manga ID when the row is pressed.
    """

    clicked = pyqtSignal(int)

    ROW_HEIGHT = 120
    COVER_WIDTH = 80
    COVER_HEIGHT = 110

    def __init__(self, manga: MangaResult, client: MangaDotNetClient | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manga_id = manga.id
        self._client = client
        self.setObjectName("mangaRow")
        self.setMinimumHeight(self.ROW_HEIGHT)
        self.setMaximumHeight(self.ROW_HEIGHT + 16)
        self.setStyleSheet(_ROW_QSS)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._loader: _CoverLoader | None = None
        self._build_ui(manga)

    def _build_ui(self, manga: MangaResult) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 14, 8)
        layout.setSpacing(14)

        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(self.COVER_WIDTH, self.COVER_HEIGHT)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet(
            f"background: {Colors.BG_DARK}; border-radius: 6px; font-size: 28px;"
        )
        self.cover_label.setText("📖")
        layout.addWidget(self.cover_label)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(3)

        # Title
        title_label = QLabel(manga.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {Colors.TEXT};"
        )
        info.addWidget(title_label)

        # Metadata row
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(12)

        if manga.rating is not None:
            rating_label = QLabel(f"⭐ {manga.rating:.0f}")
            rating_label.setStyleSheet(
                f"color: {Colors.WARNING}; font-size: 12px;"
            )
            meta_layout.addWidget(rating_label)

        if manga.status:
            status_label = QLabel(manga.status)
            status_label.setStyleSheet(
                f"color: {Colors.SECONDARY}; font-size: 12px;"
            )
            meta_layout.addWidget(status_label)

        if manga.chapter_count:
            ch_label = QLabel(f"{manga.chapter_count} chapters")
            ch_label.setStyleSheet(
                f"color: {Colors.MUTED}; font-size: 12px;"
            )
            meta_layout.addWidget(ch_label)

        meta_layout.addStretch()
        info.addLayout(meta_layout)

        # Genres (if available)
        if manga.genres:
            genres_text = " · ".join(manga.genres[:6])
            genres_label = QLabel(genres_text)
            genres_label.setStyleSheet(
                f"color: {Colors.MUTED}; font-size: 11px;"
            )
            genres_label.setWordWrap(True)
            info.addWidget(genres_label)

        # Description (truncated)
        if manga.description:
            desc_text = manga.description[:200]
            if len(manga.description) > 200:
                desc_text += "…"
            desc_label = QLabel(desc_text)
            desc_label.setStyleSheet(
                f"color: {Colors.MUTED}; font-size: 11px;"
            )
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(36)
            info.addWidget(desc_label)

        info.addStretch()
        layout.addLayout(info, stretch=1)

        # Load cover asynchronously
        if manga.photo:
            url = manga.cover_url
            self._loader = _CoverLoader(url, client=self._client, parent=self)
            self._loader.loaded.connect(self._on_cover_loaded)
            self._loader.start()

    def _on_cover_loaded(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            self.COVER_WIDTH,
            self.COVER_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cover_label.setPixmap(scaled)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.manga_id)
        super().mousePressEvent(event)

    def cleanup(self) -> None:
        """Stop the cover loader thread if running."""
        if self._loader and self._loader.isRunning():
            self._loader.quit()
            self._loader.wait(2000)
            self._loader = None
