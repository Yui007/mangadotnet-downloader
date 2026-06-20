"""GUI pages — open url, search, downloads, library, history, settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors
from ..widgets.search_widget import SearchBar, SearchResultsGrid

if TYPE_CHECKING:
    from manga_dotnet.core.config import Config


# ---------------------------------------------------------------------------
# Open URL page
# ---------------------------------------------------------------------------

from .open_url_page import OpenUrlPage  # noqa: E402

# ---------------------------------------------------------------------------
# Manga detail page
# ---------------------------------------------------------------------------

from .manga_detail_page import MangaDetailPage  # noqa: E402


# ---------------------------------------------------------------------------
# Search page — search bar + results + detail (stacked)
# ---------------------------------------------------------------------------

class SearchPage(QWidget):
    """Search page with results grid and manga detail view.

    Clicking a manga card switches to the detail view.
    The detail view has a back button to return to results.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stack: results grid ↔ manga detail
        self._stack = QStackedWidget()

        # Page 0: Search bar + results
        self._results_container = QWidget()
        rc_layout = QVBoxLayout(self._results_container)
        rc_layout.setContentsMargins(0, 0, 0, 0)
        rc_layout.setSpacing(0)

        self.search_bar = SearchBar()
        rc_layout.addWidget(self.search_bar)

        self.results_grid = SearchResultsGrid()
        rc_layout.addWidget(self.results_grid, stretch=1)

        self._stack.addWidget(self._results_container)

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

        back_btn = QPushButton("← Back to Search")
        back_btn.setStyleSheet(
            f"background: transparent; border: none; color: {Colors.PRIMARY}; "
            f"font-size: 13px; font-weight: bold; padding: 4px 8px;"
        )
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.show_results)
        back_layout.addWidget(back_btn)
        back_layout.addStretch()

        dc_layout.addWidget(back_bar)

        self.detail_page = MangaDetailPage()
        dc_layout.addWidget(self.detail_page, stretch=1)

        self._stack.addWidget(self._detail_container)

        layout.addWidget(self._stack)

        # Signals
        self.search_bar.search_triggered.connect(self._on_search)
        self.results_grid.manga_clicked.connect(self._on_manga_clicked)

        self._client = None

    def set_client(self, client) -> None:
        self._client = client
        self.detail_page.set_client(client)
        self.results_grid.set_client(client)

    def set_show_thumbnails(self, show: bool) -> None:
        """Toggle thumbnail display in search results."""
        self.results_grid.set_show_thumbnails(show)

    def set_default_language(self, lang: str) -> None:
        """Set the default language filter."""
        self.detail_page.set_default_language(lang)

    def set_default_format(self, fmt: str) -> None:
        """Set the default export format."""
        self.detail_page.set_default_format(fmt)

    def set_default_quality(self, quality: str) -> None:
        """Set the default quality."""
        self.detail_page.set_default_quality(quality)

    def set_delete_images(self, delete: bool) -> None:
        """Set the delete images after export checkbox."""
        self.detail_page.set_delete_images(delete)

    def set_thumbnail_size(self, size: int) -> None:
        """Set the thumbnail size in search results."""
        self.results_grid.set_thumbnail_size(size)

    def _on_search(self, query: str) -> None:
        if self._client is None:
            self.results_grid.show_error(
                "API client not ready. Please wait for Cloudflare…"
            )
            return
        self.results_grid.show_loading()
        from ..widgets.search_widget import _SearchWorker
        self._worker = _SearchWorker(self._client, query, parent=self)
        self._worker.results_ready.connect(self.results_grid.show_results)
        self._worker.error_occurred.connect(self.results_grid.show_error)
        self._worker.start()

    def _on_manga_clicked(self, manga_id: int) -> None:
        """Switch to detail view for the clicked manga."""
        if self._client:
            from .open_url_page import _MangaLoader
            self._detail_loader = _MangaLoader(self._client, manga_id, parent=self)
            self._detail_loader.loaded.connect(self.detail_page.update_info)
            self._detail_loader.start()
        self.detail_page.load_manga(manga_id)
        self._stack.setCurrentIndex(1)

    def show_detail(self, manga_id: int, title: str = "", cover_url: str = "") -> None:
        """Show detail page for a manga (used by OpenUrlPage)."""
        if self._client:
            from .open_url_page import _MangaLoader
            self._detail_loader = _MangaLoader(self._client, manga_id, parent=self)
            self._detail_loader.loaded.connect(self.detail_page.update_info)
            self._detail_loader.start()
        self.detail_page.load_manga(manga_id, title=title, cover_url=cover_url)
        self._stack.setCurrentIndex(1)

    def show_results(self) -> None:
        """Switch back to results view."""
        self._stack.setCurrentIndex(0)


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------

from .settings_page import SettingsPage  # noqa: E402

# ---------------------------------------------------------------------------
# Downloads page
# ---------------------------------------------------------------------------

from .downloads_page import DownloadsPage  # noqa: E402

# ---------------------------------------------------------------------------
# History page
# ---------------------------------------------------------------------------

from .history_page import HistoryPage  # noqa: E402
