"""Search widget — search bar + scrollable grid of manga cards."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors
from .manga_card import MangaCard, MangaRow

if TYPE_CHECKING:
    from manga_dotnet.api.client import MangaDotNetClient
    from manga_dotnet.core.models import MangaResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search bar
# ---------------------------------------------------------------------------

_SEARCH_BAR_QSS = f"""
QFrame#searchBar {{
    background-color: {Colors.BG_CARD};
    border-bottom: 1px solid {Colors.BORDER};
    padding: 8px 16px;
}}
QLineEdit#searchInput {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    color: {Colors.TEXT};
}}
QLineEdit#searchInput:focus {{
    border-color: {Colors.PRIMARY};
}}
"""


class SearchBar(QWidget):
    """Persistent search bar with icon and input field."""

    search_triggered = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("searchBar")
        self.setStyleSheet(_SEARCH_BAR_QSS)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        icon = QLabel("🔍")
        icon.setStyleSheet("font-size: 16px;")
        layout.addWidget(icon)

        self.input = QLineEdit()
        self.input.setObjectName("searchInput")
        self.input.setPlaceholderText("Search manga…")
        self.input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.input, stretch=1)

    def _on_submit(self) -> None:
        query = self.input.text().strip()
        if query:
            self.search_triggered.emit(query)


# ---------------------------------------------------------------------------
# Background search thread
# ---------------------------------------------------------------------------

class _SearchWorker(QThread):
    """Run search in a background thread to avoid blocking the UI."""

    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        client: MangaDotNetClient,
        query: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._query = query

    def run(self) -> None:
        try:
            from manga_dotnet.api.search import SearchAPI

            api = SearchAPI(self._client)
            results = api.search(self._query)
            self.results_ready.emit(results)
        except Exception as e:
            logger.error("Search failed: %s", e)
            self.error_occurred.emit(str(e))


# ---------------------------------------------------------------------------
# Results grid
# ---------------------------------------------------------------------------

_RESULTS_QSS = f"""
QScrollArea#resultsScroll {{
    border: none;
    background-color: transparent;
}}
QFrame#resultsContainer {{
    background-color: transparent;
}}
QLabel#emptyState {{
    color: {Colors.MUTED};
    font-size: 16px;
}}
QLabel#errorState {{
    color: {Colors.ERROR};
    font-size: 14px;
}}
QLabel#loadingState {{
    color: {Colors.MUTED};
    font-size: 14px;
}}
"""


class SearchResultsGrid(QWidget):
    """Scrollable grid that displays manga cards from search results."""

    manga_clicked = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_RESULTS_QSS)
        self._cards: list[MangaCard] = []
        self._client = None
        self._show_thumbnails = True
        self._thumbnail_size = 80
        self._build_ui()

    def set_client(self, client) -> None:
        """Set the API client for cover image loading."""
        self._client = client

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setObjectName("resultsScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # Container widget inside scroll
        self._container = QWidget()
        self._container.setObjectName("resultsContainer")

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        # State labels (shown/hidden as needed)
        self._empty_label = self._make_state_label(
            "🔍", "Search for manga to get started", "emptyState"
        )
        self._loading_label = self._make_state_label(
            "⏳", "Searching…", "loadingState"
        )
        self._error_label = self._make_state_label("", "", "errorState")
        layout.addWidget(self._empty_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._loading_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._error_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._show_empty()

    def _make_state_label(self, icon: str, text: str, object_name: str) -> QLabel:
        label = QLabel(f"{icon}\n{text}" if icon else text)
        label.setObjectName(object_name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.hide()
        return label

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _show_empty(self) -> None:
        self._empty_label.show()
        self._loading_label.hide()
        self._error_label.hide()
        self._scroll.hide()

    def _show_loading(self) -> None:
        self._empty_label.hide()
        self._loading_label.show()
        self._error_label.hide()
        self._scroll.hide()

    def _show_error(self, message: str) -> None:
        self._error_label.setText(f"❌ {message}")
        self._empty_label.hide()
        self._loading_label.hide()
        self._error_label.show()
        self._scroll.hide()

    def _show_results(self) -> None:
        self._empty_label.hide()
        self._loading_label.hide()
        self._error_label.hide()
        self._scroll.show()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_loading(self) -> None:
        """Show loading state."""
        self._show_loading()

    def show_results(self, results: list[MangaResult]) -> None:
        """Display search results as full-width horizontal rows."""
        self._clear_cards()

        if not results:
            self._empty_label.setText("🔍\nNo results found")
            self._show_empty()
            return

        # Create a fresh vertical layout on the container
        old_layout = self._container.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        v_layout = QVBoxLayout(self._container)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(8)

        for manga in results:
            row = MangaRow(manga, client=self._client)
            row.clicked.connect(self.manga_clicked.emit)
            self._cards.append(row)
            v_layout.addWidget(row)

        v_layout.addStretch()
        self._show_results()

    def show_error(self, message: str) -> None:
        """Show error state."""
        self._show_error(message)

    def show_empty(self, message: str = "🔍\nSearch for manga to get started") -> None:
        """Show empty state with custom message."""
        self._empty_label.setText(message)
        self._show_empty()

    def _clear_cards(self) -> None:
        """Remove all cards from the grid."""
        for card in self._cards:
            card.cleanup()
            card.deleteLater()
        self._cards.clear()

        # Remove any stale widgets from container layout
        layout = self._container.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def set_show_thumbnails(self, show: bool) -> None:
        """Toggle thumbnail visibility on all current manga rows."""
        self._show_thumbnails = show
        for card in self._cards:
            if hasattr(card, "cover_label"):
                card.cover_label.setVisible(show)
            if hasattr(card, "setMinimumHeight"):
                card.setMinimumHeight(60 if not show else 120)
                card.setMaximumHeight(80 if not show else 136)

    def set_thumbnail_size(self, size: int) -> None:
        """Update thumbnail size (store for next search)."""
        self._thumbnail_size = size
