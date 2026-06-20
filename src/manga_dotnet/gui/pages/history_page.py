"""History page — past download log with modern card-based UI.

Features:
    - Thumbnail cover images loaded asynchronously
    - Sleek card layout with status indicators and format badges
    - Stats summary bar (total downloads, formats breakdown)
    - Per-entry actions: open containing folder, remove from history
    - Relative timestamps ("2 hours ago", "Yesterday", etc.)
    - Smooth hover animations via QSS
    - Empty state with illustration-style placeholder
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors

if TYPE_CHECKING:
    from manga_dotnet.api.client import MangaDotNetClient
    from manga_dotnet.core.history import HistoryEntry as HistoryEntryData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_HISTORY_QSS = f"""
/* ── Page background ── */
QWidget#historyPage {{
    background-color: {Colors.BG_DARK};
}}

/* ── Stats bar ── */
QFrame#statsBar {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    padding: 12px 20px;
}}
QLabel#statsLabel {{
    color: {Colors.MUTED};
    font-size: 12px;
}}
QLabel#statsValue {{
    color: {Colors.TEXT};
    font-size: 18px;
    font-weight: bold;
}}
QLabel#statsSub {{
    color: {Colors.MUTED};
    font-size: 11px;
}}

/* ── History card ── */
QFrame#historyCard {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    padding: 0px;
}}
QFrame#historyCard:hover {{
    border-color: {Colors.PRIMARY}50;
    background-color: {Colors.BG_ELEVATED};
}}

/* ── Thumbnail ── */
QLabel#historyThumb {{
    background-color: {Colors.BG_DARK};
    border-radius: 8px;
    color: {Colors.MUTED};
    font-size: 28px;
}}

/* ── Text labels ── */
QLabel#historyTitle {{
    color: {Colors.TEXT};
    font-size: 14px;
    font-weight: bold;
}}
QLabel#historyMeta {{
    color: {Colors.MUTED};
    font-size: 11px;
}}
QLabel#historyTime {{
    color: {Colors.MUTED};
    font-size: 11px;
}}
QLabel#historyPath {{
    color: {Colors.MUTED};
    font-size: 10px;
}}

/* ── Status dot ── */
QLabel#statusDot {{
    font-size: 10px;
}}

/* ── Format badge ── */
QLabel#formatBadge {{
    background-color: {Colors.PRIMARY}20;
    color: {Colors.PRIMARY};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QLabel#formatBadgeCbz {{
    background-color: {Colors.SUCCESS}20;
    color: {Colors.SUCCESS};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QLabel#formatBadgePdf {{
    background-color: {Colors.ERROR}20;
    color: {Colors.ERROR};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QLabel#formatBadgeZip {{
    background-color: {Colors.WARNING}20;
    color: {Colors.WARNING};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QLabel#formatBadgeImg {{
    background-color: {Colors.SECONDARY}20;
    color: {Colors.SECONDARY};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}

/* ── Action buttons ── */
QToolButton#actionBtn {{
    background: transparent;
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    color: {Colors.MUTED};
    font-size: 13px;
}}
QToolButton#actionBtn:hover {{
    background-color: {Colors.BG_ELEVATED};
    border-color: {Colors.PRIMARY}60;
    color: {Colors.TEXT};
}}
QToolButton#actionBtnDanger {{
    background: transparent;
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    color: {Colors.MUTED};
    font-size: 13px;
}}
QToolButton#actionBtnDanger:hover {{
    background-color: {Colors.ERROR}20;
    border-color: {Colors.ERROR}60;
    color: {Colors.ERROR};
}}

/* ── Empty state ── */
QLabel#emptyIcon {{
    color: {Colors.BORDER};
    font-size: 64px;
}}
QLabel#emptyTitle {{
    color: {Colors.TEXT};
    font-size: 18px;
    font-weight: bold;
}}
QLabel#emptySub {{
    color: {Colors.MUTED};
    font-size: 13px;
}}

/* ── Scroll area ── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _relative_timestamp(iso_ts: str) -> str:
    """Convert an ISO timestamp to a human-readable relative string."""
    if not iso_ts:
        return "Unknown"
    try:
        # Parse ISO format
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        now = datetime.now(tz=dt.tzinfo) if dt.tzinfo else datetime.now()
        delta = now - dt
        seconds = abs(delta.total_seconds())
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            m = int(seconds / 60)
            return f"{m} min ago" if m == 1 else f"{m} mins ago"
        if seconds < 86400:
            h = int(seconds / 3600)
            return f"{h} hr ago" if h == 1 else f"{h} hrs ago"
        if seconds < 172800:
            return "Yesterday"
        if seconds == 172800:
            return "2 days ago"
        if seconds < 604800:
            d = int(seconds / 86400)
            return f"{d} days ago"
        if seconds < 2592000:
            w = int(seconds / 604800)
            return f"{w} week ago" if w == 1 else f"{w} weeks ago"
        # Fall back to date
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso_ts[:10] if len(iso_ts) >= 10 else iso_ts


def _format_badge_style(fmt: str) -> str:
    """Return the QSS object-name for the format badge."""
    fmt_lower = fmt.lower()
    if fmt_lower == "cbz":
        return "formatBadgeCbz"
    if fmt_lower == "pdf":
        return "formatBadgePdf"
    if fmt_lower == "zip":
        return "formatBadgeZip"
    if fmt_lower in ("images", "folder", "img"):
        return "formatBadgeImg"
    return "formatBadge"


def _status_info(status: str) -> tuple[str, str]:
    """Return (dot_emoji, color) for a status string."""
    if status == "success":
        return ("●", Colors.SUCCESS)
    if status == "partial":
        return ("●", Colors.WARNING)
    if status == "failed":
        return ("●", Colors.ERROR)
    return ("●", Colors.MUTED)


# ---------------------------------------------------------------------------
# Thumbnail loader (reuses browser-based fetch for CF bypass)
# ---------------------------------------------------------------------------

class _ThumbLoader(QWidget):
    """Load a thumbnail pixmap via httpx (no thread — uses signals/slots)."""

    loaded = pyqtSignal(QPixmap)
    failed = pyqtSignal()

    def __init__(self, url: str, client: MangaDotNetClient | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url
        self._client = client
        # Use a zero-shot timer to load after the widget is shown
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._load)

    def _load(self) -> None:
        try:
            if self._client and getattr(self._client, "_driver", None):
                self._load_via_browser()
            else:
                self._load_via_httpx()
        except Exception:
            self.failed.emit()

    def _load_via_browser(self) -> None:
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
# History card widget
# ---------------------------------------------------------------------------

class HistoryCard(QFrame):
    """A single history entry displayed as a sleek horizontal card.

    Layout:
        ┌──────────────────────────────────────────────────────────┐
        │ ┌────────┐  Title — Chapter Range    [badge]  ● status  │
        │ │        │  12 chapters · 240 pages · PDF               │
        │ │ Thumb  │  📁 /path/to/file.cbz                         │
        │ │        │                              2 hrs ago  [🗑] │
        │ └────────┘                                              │
        └──────────────────────────────────────────────────────────┘
    """

    delete_requested = pyqtSignal(str)  # composite key: "manga_id|chapter_range|timestamp"
    open_requested = pyqtSignal(str)    # output_path

    THUMB_W = 80
    THUMB_H = 110

    def __init__(
        self,
        entry: HistoryEntryData,
        client: MangaDotNetClient | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._entry = entry
        self._client = client
        self.setObjectName("historyCard")
        self._build_ui(entry)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, entry: HistoryEntryData) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(14)

        # ── Thumbnail ──
        self._thumb = QLabel()
        self._thumb.setObjectName("historyThumb")
        self._thumb.setFixedSize(self.THUMB_W, self.THUMB_H)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setStyleSheet(
            f"background: {Colors.BG_DARK}; border-radius: 8px; font-size: 28px;"
        )
        self._thumb.setText("📖")
        main_layout.addWidget(self._thumb)

        # ── Center: title + meta + path ──
        info = QVBoxLayout()
        info.setSpacing(3)
        info.setContentsMargins(0, 4, 0, 4)

        # Title
        title_text = f"{entry.manga_title}  —  {entry.chapter_range}"
        title_label = QLabel(title_text)
        title_label.setObjectName("historyTitle")
        title_label.setWordWrap(False)
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info.addWidget(title_label)

        # Meta line: chapters · pages · format · errors
        meta_parts: list[str] = []
        if entry.chapters_downloaded:
            meta_parts.append(f"{entry.chapters_downloaded} chapter{'s' if entry.chapters_downloaded != 1 else ''}")
        if entry.total_pages:
            meta_parts.append(f"{entry.total_pages} page{'s' if entry.total_pages != 1 else ''}")
        if entry.export_format:
            meta_parts.append(entry.export_format.upper())
        if entry.errors:
            meta_parts.append(f"{len(entry.errors)} error{'s' if len(entry.errors) != 1 else ''}")

        if meta_parts:
            meta_label = QLabel("  ·  ".join(meta_parts))
            meta_label.setObjectName("historyMeta")
            info.addWidget(meta_label)

        # Output path (truncated)
        if entry.output_path:
            path_str = entry.output_path
            if len(path_str) > 70:
                path_str = "..." + path_str[-67:]
            path_label = QLabel(f"📁 {path_str}")
            path_label.setObjectName("historyPath")
            path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            path_label.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
            info.addWidget(path_label)

        info.addStretch()
        main_layout.addLayout(info, stretch=1)

        # ── Right column: badge + status + time + actions ──
        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        right_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # Badge + status row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        badge_row.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Format badge
        badge = QLabel(entry.export_format.upper())
        badge.setObjectName(_format_badge_style(entry.export_format))
        badge_row.addWidget(badge)

        # Status dot
        dot, color = _status_info(entry.status)
        status_label = QLabel(dot)
        status_label.setObjectName("statusDot")
        status_label.setStyleSheet(f"color: {color}; font-size: 10px;")
        status_label.setToolTip(entry.status.capitalize())
        badge_row.addWidget(status_label)

        right_col.addLayout(badge_row)

        # Relative timestamp
        time_label = QLabel(_relative_timestamp(entry.timestamp))
        time_label.setObjectName("historyTime")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(time_label)

        # Action buttons row
        actions = QHBoxLayout()
        actions.setSpacing(4)
        actions.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Open folder button
        if entry.output_path:
            open_btn = QToolButton()
            open_btn.setObjectName("actionBtn")
            open_btn.setText("📂")
            open_btn.setToolTip("Open containing folder")
            open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            open_btn.clicked.connect(lambda: self.open_requested.emit(entry.output_path))
            actions.addWidget(open_btn)

        # Delete button
        del_btn = QToolButton()
        del_btn.setObjectName("actionBtnDanger")
        del_btn.setText("🗑")
        del_btn.setToolTip("Remove from history")
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.clicked.connect(
            lambda: self.delete_requested.emit(
                f"{entry.manga_id}|{entry.chapter_range}|{entry.timestamp}"
            )
        )
        actions.addWidget(del_btn)

        right_col.addLayout(actions)
        right_col.addStretch()
        main_layout.addLayout(right_col)

    # ------------------------------------------------------------------
    # Thumbnail loading
    # ------------------------------------------------------------------

    def load_thumbnail(self, url: str) -> None:
        """Start loading a thumbnail from *url*."""
        self._thumb_loader = _ThumbLoader(url, client=self._client, parent=self)
        self._thumb_loader.loaded.connect(self._on_thumb_loaded)
        self._thumb_loader.failed.connect(self._on_thumb_failed)

    def _on_thumb_loaded(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            self.THUMB_W,
            self.THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._thumb.setPixmap(scaled)
        self._thumb.setStyleSheet("background: transparent; border-radius: 8px;")

    def _on_thumb_failed(self) -> None:
        pass  # Keep the default 📖 placeholder


# ---------------------------------------------------------------------------
# Stats bar
# ---------------------------------------------------------------------------

class _StatsBar(QFrame):
    """Summary statistics bar shown above the history list."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statsBar")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(24)

        # Total downloads
        self._total_value = QLabel("0")
        self._total_value.setObjectName("statsValue")
        self._total_label = QLabel("Total Downloads")
        self._total_label.setObjectName("statsSub")
        total_col = QVBoxLayout()
        total_col.addWidget(self._total_value, alignment=Qt.AlignmentFlag.AlignCenter)
        total_col.addWidget(self._total_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(total_col)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {Colors.BORDER};")
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        # Success count
        self._success_value = QLabel("0")
        self._success_value.setObjectName("statsValue")
        self._success_value.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 18px; font-weight: bold;")
        self._success_label = QLabel("Successful")
        self._success_label.setObjectName("statsSub")
        success_col = QVBoxLayout()
        success_col.addWidget(self._success_value, alignment=Qt.AlignmentFlag.AlignCenter)
        success_col.addWidget(self._success_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(success_col)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"color: {Colors.BORDER};")
        sep2.setFixedWidth(1)
        layout.addWidget(sep2)

        # Failed count
        self._failed_value = QLabel("0")
        self._failed_value.setObjectName("statsValue")
        self._failed_value.setStyleSheet(f"color: {Colors.ERROR}; font-size: 18px; font-weight: bold;")
        self._failed_label = QLabel("Failed")
        self._failed_label.setObjectName("statsSub")
        failed_col = QVBoxLayout()
        failed_col.addWidget(self._failed_value, alignment=Qt.AlignmentFlag.AlignCenter)
        failed_col.addWidget(self._failed_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(failed_col)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet(f"color: {Colors.BORDER};")
        sep3.setFixedWidth(1)
        layout.addWidget(sep3)

        # Format breakdown
        self._formats_value = QLabel("—")
        self._formats_value.setObjectName("statsValue")
        self._formats_value.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 18px; font-weight: bold;")
        self._formats_label = QLabel("Formats")
        self._formats_label.setObjectName("statsSub")
        fmt_col = QVBoxLayout()
        fmt_col.addWidget(self._formats_value, alignment=Qt.AlignmentFlag.AlignCenter)
        fmt_col.addWidget(self._formats_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(fmt_col)

        layout.addStretch()

    def update_stats(self, entries: list[HistoryEntryData]) -> None:
        """Refresh stats from the given entries."""
        total = len(entries)
        success = sum(1 for e in entries if e.status == "success")
        failed = sum(1 for e in entries if e.status == "failed")

        # Format breakdown
        fmt_counts: dict[str, int] = {}
        for e in entries:
            fmt_counts[e.export_format] = fmt_counts.get(e.export_format, 0) + 1
        fmt_str = " · ".join(f"{k.upper()}: {v}" for k, v in sorted(fmt_counts.items())) or "—"

        self._total_value.setText(str(total))
        self._success_value.setText(str(success))
        self._failed_value.setText(str(failed))
        self._formats_value.setText(fmt_str)


# ---------------------------------------------------------------------------
# History page
# ---------------------------------------------------------------------------

class HistoryPage(QWidget):
    """History page showing past downloads in a modern card-based layout.

    Features:
        - Stats summary bar at top
        - Thumbnail cover images per entry
        - Format badges with color coding
        - Relative timestamps
        - Per-entry actions (open folder, delete)
        - Empty state with styled placeholder
    """

    delete_entry_requested = pyqtSignal(str)  # composite key — connected by MainWindow

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPage")
        self.setStyleSheet(_HISTORY_QSS)
        self._cards: list[HistoryCard] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # ── Header ──
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title = QLabel("History")
        title.setObjectName("headingLabel")
        title.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {Colors.TEXT};"
        )
        header_row.addWidget(title)
        header_row.addStretch()

        layout.addLayout(header_row)

        # ── Stats bar ──
        self._stats_bar = _StatsBar()
        layout.addWidget(self._stats_bar)

        # ── Scroll area for cards ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("border: none; background: transparent;")

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()  # Push cards to top
        self._scroll.setWidget(self._cards_container)
        layout.addWidget(self._scroll, stretch=1)

        # ── Empty state ──
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_icon = QLabel("📋")
        empty_icon.setObjectName("emptyIcon")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("No Download History")
        empty_title.setObjectName("emptyTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_sub = QLabel("Your completed downloads will appear here.\nStart downloading some manga!")
        empty_sub.setObjectName("emptySub")
        empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_sub.setWordWrap(True)
        empty_layout.addWidget(empty_sub)

        layout.addWidget(self._empty_widget)

        # Show empty state initially
        self._scroll.hide()
        self._empty_widget.show()
        self._stats_bar.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_entry(
        self,
        manga_title: str,
        chapter_range: str,
        export_format: str,
        timestamp: str = "",
        status: str = "success",
        manga_id: int = 0,
        chapters_downloaded: int = 0,
        total_pages: int = 0,
        output_path: str = "",
        cover_url: str = "",
        errors: list[str] | None = None,
        client: MangaDotNetClient | None = None,
    ) -> None:
        """Add a history entry card.

        This is the primary method called by MainWindow to populate history.
        The parameters match the HistoryEntry dataclass fields.
        """
        from manga_dotnet.core.history import HistoryEntry as HistoryEntryData

        entry = HistoryEntryData(
            manga_id=manga_id,
            manga_title=manga_title,
            chapter_range=chapter_range,
            export_format=export_format,
            timestamp=timestamp,
            chapters_downloaded=chapters_downloaded,
            total_pages=total_pages,
            output_path=output_path,
            cover_url=cover_url,
            status=status,
            errors=errors or [],
        )
        self._add_card(entry, client=client, cover_url=cover_url)

    def _add_card(
        self,
        entry: HistoryEntryData,
        client: MangaDotNetClient | None = None,
        cover_url: str = "",
    ) -> None:
        """Internal: create and insert a HistoryCard."""
        card = HistoryCard(entry, client=client, parent=self._cards_container)
        card.delete_requested.connect(self._on_delete_requested)
        card.open_requested.connect(self._on_open_requested)

        # Insert before the stretch
        insert_idx = self._cards_layout.count() - 1
        self._cards_layout.insertWidget(insert_idx, card)
        self._cards.append(card)

        # Load thumbnail if cover URL is available
        if cover_url:
            card.load_thumbnail(cover_url)

        # Update visibility
        self._empty_widget.hide()
        self._scroll.show()
        self._stats_bar.show()

        # Refresh stats
        self._refresh_stats()

    def clear(self) -> None:
        """Clear all history entries."""
        for card in self._cards:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._empty_widget.show()
        self._scroll.hide()
        self._stats_bar.hide()

    def get_entries(self) -> list[HistoryEntryData]:
        """Return the current list of history entries from cards."""
        return [card._entry for card in self._cards]

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_delete_requested(self, key: str) -> None:
        """Handle delete button on a card."""
        self.delete_entry_requested.emit(key)

    def _on_open_requested(self, output_path: str) -> None:
        """Handle open folder button on a card."""
        path = Path(output_path)
        if path.is_file():
            path = path.parent
        if path.exists():
            import subprocess
            import sys
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])

    def _refresh_stats(self) -> None:
        """Recompute and display stats."""
        entries = self.get_entries()
        self._stats_bar.update_stats(entries)
