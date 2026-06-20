"""Manga detail page — beautiful manga info + chapter list with filtering."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors

if TYPE_CHECKING:
    from manga_dotnet.api.client import MangaDotNetClient
    from manga_dotnet.core.models import Chapter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_DETAIL_QSS = f"""
QFrame#mangaHeader {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    padding: 20px;
}}
QLabel#mangaTitle {{
    font-size: 24px;
    font-weight: bold;
    color: {Colors.TEXT};
}}
QLabel#mangaMeta {{
    font-size: 13px;
    color: {Colors.MUTED};
}}
QTableWidget#chapterTable {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    gridline-color: {Colors.BORDER};
    selection-background-color: {Colors.PRIMARY}30;
    font-size: 12px;
}}
QHeaderView::section {{
    background-color: {Colors.BG_CARD};
    color: {Colors.MUTED};
    border: none;
    border-bottom: 1px solid {Colors.BORDER};
    padding: 6px 8px;
    font-weight: bold;
    font-size: 11px;
}}
QPushButton#downloadBtn {{
    background-color: {Colors.PRIMARY};
    border: none;
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 10px 32px;
    border-radius: 8px;
}}
QPushButton#downloadBtn:hover {{
    background-color: {Colors.PRIMARY}CC;
}}
QPushButton#downloadBtn:disabled {{
    background-color: {Colors.MUTED};
}}
QPushButton#selectBtn {{
    background: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: bold;
    color: {Colors.TEXT};
}}
QPushButton#selectBtn:hover {{
    background-color: {Colors.PRIMARY}30;
    border-color: {Colors.PRIMARY};
    color: {Colors.PRIMARY};
}}
QPushButton#selectBtn:pressed {{
    background-color: {Colors.PRIMARY}50;
}}
QComboBox#filterCombo {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
    color: {Colors.TEXT};
    min-width: 100px;
}}
"""


# ---------------------------------------------------------------------------
# Cover image loader
# ---------------------------------------------------------------------------

class _CoverLoader(QThread):
    loaded = pyqtSignal(QPixmap)
    failed = pyqtSignal()

    def __init__(self, url: str, client=None, parent=None) -> None:
        super().__init__(parent)
        self._url = url
        self._client = client

    def run(self) -> None:
        try:
            if self._client and self._client._driver:
                self._load_via_browser()
            else:
                self._load_via_httpx()
        except Exception:
            self.failed.emit()

    def _load_via_browser(self):
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

    def _load_via_httpx(self):
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
# Background chapter loader — loads ALL chapters (not deduplicated)
# ---------------------------------------------------------------------------

class _ChapterLoader(QThread):
    loaded = pyqtSignal(list)  # Emits raw chapters list
    error = pyqtSignal(str)

    def __init__(self, client, manga_id: int, parent=None) -> None:
        super().__init__(parent)
        self._client = client
        self._manga_id = manga_id

    def run(self) -> None:
        try:
            from manga_dotnet.api.chapters import ChapterAPI
            api = ChapterAPI(self._client)
            chapters = api.get_chapters(self._manga_id)
            self.loaded.emit(chapters)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Background volume loader
# ---------------------------------------------------------------------------

class _VolumeLoader(QThread):
    loaded = pyqtSignal(list)  # Emits list of Volume objects
    error = pyqtSignal(str)

    def __init__(self, client, manga_id: int, parent=None) -> None:
        super().__init__(parent)
        self._client = client
        self._manga_id = manga_id

    def run(self) -> None:
        try:
            from manga_dotnet.api.volumes import VolumeAPI
            api = VolumeAPI(self._client)
            volumes = api.get_volumes(self._manga_id)
            self.loaded.emit(volumes)
        except Exception as e:
            logger.warning("Failed to load volumes: %s", e)
            self.loaded.emit([])  # Don't fail — volumes are optional


# ---------------------------------------------------------------------------
# Manga detail page
# ---------------------------------------------------------------------------

class MangaDetailPage(QWidget):
    """Full manga detail view with info header and filterable chapter table."""

    download_requested = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_DETAIL_QSS)
        self._client = None
        self._all_chapters: list[Chapter] = []
        self._filtered_chapters: list[Chapter] = []
        self._checkboxes: list[QCheckBox] = []
        self._items: list[tuple[str, object]] = []  # (type, item) pairs for selection
        self._cover_loader = None
        self._chapter_loader = None
        self._available_languages: list[str] = []
        self._available_groups: list[str] = []
        self._available_volumes: list = []
        self._filtered_volumes: list = []
        self._build_ui()

    def set_client(self, client) -> None:
        self._client = client

    def set_default_format(self, fmt: str) -> None:
        """Pre-select the default export format."""
        idx = self._format.findText(fmt)
        if idx >= 0:
            self._format.setCurrentIndex(idx)

    def set_default_language(self, lang: str) -> None:
        """Pre-select the default language filter."""
        idx = self._lang_combo.findText(lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)

    def set_default_quality(self, quality: str) -> None:
        """Pre-select the default quality."""
        idx = self._quality.findText(quality)
        if idx >= 0:
            self._quality.setCurrentIndex(idx)

    def set_delete_images(self, delete: bool) -> None:
        """Pre-set the delete images after export checkbox."""
        self._delete_cb.setChecked(delete)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        container = QWidget()
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(24, 20, 24, 20)
        self._main_layout.setSpacing(12)

        self._build_header()
        self._build_filters()
        self._build_chapter_table()
        self._build_download_bar()

        self._main_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self._scroll_area = scroll

        # Empty state
        self._empty_label = QLabel("Select a manga to view details")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: 16px; padding: 60px;")
        layout.addWidget(self._empty_label)
        scroll.hide()

    def _build_header(self) -> None:
        header = QFrame()
        header.setObjectName("mangaHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setSpacing(20)

        self._cover = QLabel()
        self._cover.setFixedSize(180, 250)
        self._cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover.setStyleSheet(f"background: {Colors.BG_DARK}; border-radius: 8px; font-size: 48px;")
        self._cover.setText("📖")
        h_layout.addWidget(self._cover)

        info = QVBoxLayout()
        info.setSpacing(6)

        self._title = QLabel("")
        self._title.setObjectName("mangaTitle")
        self._title.setWordWrap(True)
        info.addWidget(self._title)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(16)
        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {Colors.SECONDARY}; font-size: 13px; font-weight: bold;")
        meta_row.addWidget(self._status)
        self._rating = QLabel("")
        self._rating.setStyleSheet(f"color: {Colors.WARNING}; font-size: 13px;")
        meta_row.addWidget(self._rating)
        self._ch_count = QLabel("")
        self._ch_count.setStyleSheet(f"color: {Colors.MUTED}; font-size: 13px;")
        meta_row.addWidget(self._ch_count)
        meta_row.addStretch()
        info.addLayout(meta_row)

        self._authors = QLabel("")
        self._authors.setObjectName("mangaMeta")
        info.addWidget(self._authors)
        self._genres = QLabel("")
        self._genres.setObjectName("mangaMeta")
        self._genres.setWordWrap(True)
        info.addWidget(self._genres)
        self._desc = QLabel("")
        self._desc.setObjectName("mangaMeta")
        self._desc.setWordWrap(True)
        self._desc.setMaximumHeight(60)
        info.addWidget(self._desc)

        info.addStretch()
        h_layout.addLayout(info, stretch=1)
        self._main_layout.addWidget(header)

    def _build_filters(self) -> None:
        """Build language, group, and volume filter controls."""
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        lbl = QLabel("Filters:")
        lbl.setStyleSheet(f"color: {Colors.MUTED}; font-size: 12px; font-weight: bold;")
        filter_row.addWidget(lbl)

        # Language filter
        lang_lbl = QLabel("Language:")
        lang_lbl.setStyleSheet(f"color: {Colors.MUTED}; font-size: 11px;")
        filter_row.addWidget(lang_lbl)
        self._lang_combo = QComboBox()
        self._lang_combo.setObjectName("filterCombo")
        self._lang_combo.addItem("All")
        self._lang_combo.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self._lang_combo)

        # Group filter
        grp_lbl = QLabel("Group:")
        grp_lbl.setStyleSheet(f"color: {Colors.MUTED}; font-size: 11px;")
        filter_row.addWidget(grp_lbl)
        self._group_combo = QComboBox()
        self._group_combo.setObjectName("filterCombo")
        self._group_combo.addItem("All")
        self._group_combo.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self._group_combo)

        # Volume filter
        vol_lbl = QLabel("Volume:")
        vol_lbl.setStyleSheet(f"color: {Colors.MUTED}; font-size: 11px;")
        filter_row.addWidget(vol_lbl)
        self._vol_combo = QComboBox()
        self._vol_combo.setObjectName("filterCombo")
        self._vol_combo.addItem("All")
        self._vol_combo.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self._vol_combo)

        filter_row.addStretch()
        self._main_layout.addLayout(filter_row)

    def _build_chapter_table(self) -> None:
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        ch_label = QLabel("📖 Chapters")
        ch_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.TEXT};")
        ctrl.addWidget(ch_label)

        self._count_label = QLabel("0 chapters")
        self._count_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: 12px;")
        ctrl.addWidget(self._count_label)

        ctrl.addStretch()

        for text, callback in [
            ("All", self._select_all),
            ("None", self._select_none),
            ("Invert", self._select_invert),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("selectBtn")
            btn.clicked.connect(callback)
            ctrl.addWidget(btn)

        self._main_layout.addLayout(ctrl)

        self._table = QTableWidget()
        self._table.setObjectName("chapterTable")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["✓", "Ch.", "Vol.", "Title", "Group", "Pages", "Lang"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(0, 36)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._main_layout.addWidget(self._table)

    def _build_download_bar(self) -> None:
        bar = QHBoxLayout()
        bar.setSpacing(12)

        fmt_lbl = QLabel("Format:")
        fmt_lbl.setStyleSheet(f"color: {Colors.MUTED}; font-size: 12px;")
        bar.addWidget(fmt_lbl)
        self._format = QComboBox()
        self._format.addItems(["cbz", "zip", "pdf", "images", "folder"])
        self._format.setFixedWidth(80)
        bar.addWidget(self._format)

        qual_lbl = QLabel("Quality:")
        qual_lbl.setStyleSheet(f"color: {Colors.MUTED}; font-size: 12px;")
        bar.addWidget(qual_lbl)
        self._quality = QComboBox()
        self._quality.addItems(["original", "high", "medium", "low"])
        self._quality.setFixedWidth(80)
        bar.addWidget(self._quality)

        self._delete_cb = QCheckBox("Delete images after export")
        self._delete_cb.setStyleSheet(f"font-size: 11px; color: {Colors.MUTED};")
        bar.addWidget(self._delete_cb)

        bar.addStretch()

        self._dl_btn = QPushButton("⬇ Download Selected")
        self._dl_btn.setObjectName("downloadBtn")
        self._dl_btn.setEnabled(False)
        self._dl_btn.clicked.connect(self._on_download)
        bar.addWidget(self._dl_btn)

        self._main_layout.addLayout(bar)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_manga(self, manga_id: int, title: str = "", cover_url: str = "") -> None:
        self._manga_id = manga_id
        self._empty_label.hide()
        self._scroll_area.show()
        if title:
            self._title.setText(title)
        if self._client:
            self._count_label.setText("Loading chapters & volumes…")
            self._chapter_loader = _ChapterLoader(self._client, manga_id, parent=self)
            self._chapter_loader.loaded.connect(self._on_chapters_loaded)
            self._chapter_loader.error.connect(self._on_chapters_error)
            self._chapter_loader.start()

            # Also load volumes
            self._volume_loader = _VolumeLoader(self._client, manga_id, parent=self)
            self._volume_loader.loaded.connect(self._on_volumes_loaded)
            self._volume_loader.start()
        if cover_url:
            url = cover_url if cover_url.startswith("http") else f"https://mangadot.net{cover_url}"
            self._cover_loader = _CoverLoader(url, client=self._client, parent=self)
            self._cover_loader.loaded.connect(self._on_cover_loaded)
            self._cover_loader.start()

    def update_info(self, info) -> None:
        self._title.setText(info.title)
        self._status.setText(info.status or "")
        self._rating.setText(f"⭐ {info.rating:.0f}" if info.rating else "")
        self._ch_count.setText(f"{info.chapter_count} chapters" if info.chapter_count else "")
        if info.authors:
            self._authors.setText(f"Authors: {', '.join(info.authors)}")
        if info.genres:
            self._genres.setText(f"Genres: {' · '.join(info.genres[:8])}")
        if info.description:
            self._desc.setText(info.description[:400])
        if info.photo:
            url = info.photo if info.photo.startswith("http") else f"https://mangadot.net{info.photo}"
            self._cover_loader = _CoverLoader(url, client=self._client, parent=self)
            self._cover_loader.loaded.connect(self._on_cover_loaded)
            self._cover_loader.start()

    # ------------------------------------------------------------------
    # Chapter loading + filtering
    # ------------------------------------------------------------------

    def _on_chapters_loaded(self, chapters: list) -> None:
        self._all_chapters = chapters

        # Extract unique filter values from chapters
        self._available_languages = sorted(set(ch.language for ch in chapters if ch.language))
        self._available_groups = sorted(set(
            ch.group_display for ch in chapters if ch.group_display != "Unknown"
        ))

        # Note: volumes are loaded separately via _VolumeLoader

        # Populate filter combos
        self._lang_combo.blockSignals(True)
        self._group_combo.blockSignals(True)

        self._lang_combo.clear()
        self._lang_combo.addItem("All")
        self._lang_combo.addItems(self._available_languages)

        self._group_combo.clear()
        self._group_combo.addItem("All")
        self._group_combo.addItems(self._available_groups)

        self._lang_combo.blockSignals(False)
        self._group_combo.blockSignals(False)

        self._apply_filters()

    def _on_volumes_loaded(self, volumes: list) -> None:
        """Handle volumes loaded from API."""
        self._available_volumes = volumes

        # Update volume filter combo
        self._vol_combo.blockSignals(True)
        self._vol_combo.clear()
        self._vol_combo.addItem("None")  # Show chapters only
        self._vol_combo.addItem("All")   # Show all volumes
        for v in volumes:
            self._vol_combo.addItem(f"Vol. {v.volume_number:g} ({v.page_count} pages)")
        self._vol_combo.blockSignals(False)

        # Update count label
        ch_count = len(self._all_chapters)
        vol_count = len(volumes)
        parts = []
        if ch_count:
            parts.append(f"{ch_count} chapters")
        if vol_count:
            parts.append(f"{vol_count} volumes")
        self._count_label.setText(" / ".join(parts) if parts else "Loading…")

    def _on_chapters_error(self, error: str) -> None:
        self._count_label.setText(f"❌ {error}")

    def _apply_filters(self) -> None:
        """Apply language, group, and volume filters.

        Volume filter logic:
        - "None" → show chapters only
        - "All"  → show all volumes only
        - "Vol. X" → show only that volume
        """
        lang = self._lang_combo.currentText()
        group = self._group_combo.currentText()
        vol_text = self._vol_combo.currentText()

        # Filter chapters by language and group (always applied to chapters)
        filtered_chapters = list(self._all_chapters)
        if lang != "All":
            filtered_chapters = [ch for ch in filtered_chapters if ch.language == lang]
        if group != "All":
            filtered_chapters = [ch for ch in filtered_chapters if ch.group_display == group]

        # Determine what to show based on volume filter
        if vol_text == "None":
            # Show chapters only
            self._filtered_volumes = []
        elif vol_text == "All":
            # Show all volumes only (no chapters)
            self._filtered_volumes = list(self._available_volumes)
            filtered_chapters = []
        elif vol_text.startswith("Vol. "):
            # Show the selected volume row + its chapters
            try:
                vol_num_str = vol_text.split(" ", 1)[1].split(" ")[0]
                vol_num = float(vol_num_str)
                filtered_chapters = [ch for ch in filtered_chapters if ch.volume_number == vol_num]
                # Also show the volume itself as a selectable row
                self._filtered_volumes = [
                    v for v in self._available_volumes if v.volume_number == vol_num
                ]
            except (ValueError, IndexError):
                self._filtered_volumes = []
        else:
            # Default: chapters only
            self._filtered_volumes = []

        self._filtered_chapters = sorted(filtered_chapters, key=lambda c: c.sort_key)
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate table with chapters AND volumes (when "All" selected)."""
        items = []

        # Add volumes first (they appear at the top)
        for vol in self._filtered_volumes:
            items.append(("volume", vol))

        # Then add chapters
        for ch in self._filtered_chapters:
            items.append(("chapter", ch))

        self._checkboxes.clear()
        self._items = items  # Store for get_selected_items()
        self._table.setRowCount(len(items))

        for row, (item_type, item) in enumerate(items):
            cb = QCheckBox()
            cb.setChecked(True)
            self._checkboxes.append(cb)

            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(cb)
            self._table.setCellWidget(row, 0, cell)

            if item_type == "volume":
                # Volume row
                values = [
                    f"Vol. {item.volume_number:g}",
                    f"Vol. {item.volume_number:g}",
                    f"Volume {item.volume_number:g}",
                    item.group_name or "Unknown",
                    str(item.page_count),
                    "en",
                ]
            else:
                # Chapter row
                values = [
                    f"{item.chapter_number:g}",
                    f"{item.volume_number:g}" if item.volume_number else "—",
                    item.display_title,
                    item.group_display,
                    str(item.page_count),
                    item.language,
                ]

            for col, value in enumerate(values, start=1):
                item_widget = QTableWidgetItem(value)
                item_widget.setFlags(item_widget.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if item_type == "volume":
                    # Store volume data in the chapter number column
                    item_widget.setData(Qt.ItemDataRole.UserRole, ("volume", item))
                else:
                    item_widget.setData(Qt.ItemDataRole.UserRole, ("chapter", item))
                self._table.setItem(row, col, item_widget)

        # Update count
        vol_count = len(self._filtered_volumes)
        ch_count = len(self._filtered_chapters)
        total = vol_count + ch_count
        parts = []
        if vol_count:
            parts.append(f"{vol_count} volumes")
        if ch_count:
            parts.append(f"{ch_count} chapters")
        self._count_label.setText(f"{total} items" if not parts else " / ".join(parts))
        self._dl_btn.setEnabled(total > 0)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _select_all(self):
        for cb in self._checkboxes:
            cb.setChecked(True)

    def _select_none(self):
        for cb in self._checkboxes:
            cb.setChecked(False)

    def _select_invert(self):
        for cb in self._checkboxes:
            cb.setChecked(not cb.isChecked())

    def get_selected_items(self) -> list[tuple[str, object]]:
        """Get all selected items (chapters and volumes) as (type, item) pairs."""
        return [
            (item_type, item)
            for (item_type, item), cb in zip(self._items, self._checkboxes)
            if cb.isChecked()
        ]

    def get_selected_chapters(self) -> list:
        """Get only selected chapters (convenience method)."""
        return [item for t, item in self.get_selected_items() if t == "chapter"]

    def get_selected_volumes(self) -> list:
        """Get only selected volumes."""
        return [item for t, item in self.get_selected_items() if t == "volume"]

    # ------------------------------------------------------------------
    # Cover + download
    # ------------------------------------------------------------------

    def _on_cover_loaded(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            180, 250,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._cover.setPixmap(scaled)

    def _on_download(self) -> None:
        selected_chapters = self.get_selected_chapters()
        selected_volumes = self.get_selected_volumes()
        if not selected_chapters and not selected_volumes:
            return
        self.download_requested.emit({
            "manga_id": self._manga_id,
            "manga_title": self._title.text(),
            "chapters": selected_chapters,
            "volumes": selected_volumes,
            "format": self._format.currentText(),
            "quality": self._quality.currentText(),
            "delete_images": self._delete_cb.isChecked(),
        })
