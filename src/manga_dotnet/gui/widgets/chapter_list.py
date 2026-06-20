"""Chapter list widget — table with checkboxes, selection controls, and download trigger."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors

if TYPE_CHECKING:
    from manga_dotnet.core.models import Chapter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_CHAPTER_LIST_QSS = f"""
QFrame#chapterListFrame {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
}}
QTableWidget#chapterTable {{
    background-color: {Colors.BG_DARK};
    border: none;
    gridline-color: {Colors.BORDER};
    selection-background-color: {Colors.PRIMARY}30;
    selection-color: {Colors.TEXT};
    font-size: 12px;
}}
QTableWidget#chapterTable::item {{
    padding: 4px 8px;
}}
QTableWidget#chapterTable::item:selected {{
    background-color: {Colors.PRIMARY}20;
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
QCheckBox#chapterCheckbox::indicator {{
    width: 16px;
    height: 16px;
}}
"""


# ---------------------------------------------------------------------------
# Chapter list widget
# ---------------------------------------------------------------------------

class ChapterListWidget(QWidget):
    """Display chapters in a table with checkboxes for multi-select.

    Features:
    - Checkbox per chapter row
    - Select All / None / Invert buttons
    - Range selector input
    - Format and quality dropdowns
    - Download Selected button
    """

    download_requested = pyqtSignal(dict)  # Emits {chapters, format, quality, delete_images}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chapterListFrame")
        self.setStyleSheet(_CHAPTER_LIST_QSS)

        self._chapters: list[Chapter] = []
        self._checkboxes: list[QCheckBox] = []

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)

        title = QLabel("📖 Chapters")
        title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Colors.TEXT};")
        header.addWidget(title)

        self._count_label = QLabel("0 chapters")
        self._count_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: 12px;")
        header.addWidget(self._count_label)

        header.addStretch()
        layout.addLayout(header)

        # Selection controls
        controls = QHBoxLayout()
        controls.setContentsMargins(12, 4, 12, 4)
        controls.setSpacing(8)

        self._select_all_btn = self._make_control_btn("All", self._select_all)
        self._select_none_btn = self._make_control_btn("None", self._select_none)
        self._select_invert_btn = self._make_control_btn("Invert", self._select_invert)
        controls.addWidget(self._select_all_btn)
        controls.addWidget(self._select_none_btn)
        controls.addWidget(self._select_invert_btn)

        controls.addSpacing(12)

        range_label = QLabel("Range:")
        range_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: 12px;")
        controls.addWidget(range_label)

        self._range_input = QLineEdit()
        self._range_input.setPlaceholderText("e.g. 1-10, 15, 20-30")
        self._range_input.setFixedWidth(180)
        self._range_input.setStyleSheet(
            f"background: {Colors.BG_CARD}; border: 1px solid {Colors.BORDER}; "
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._range_input.returnPressed.connect(self._apply_range)
        controls.addWidget(self._range_input)

        range_btn = self._make_control_btn("Apply", self._apply_range)
        controls.addWidget(range_btn)

        controls.addStretch()

        # Format selector
        fmt_label = QLabel("Format:")
        fmt_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: 12px;")
        controls.addWidget(fmt_label)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["cbz", "zip", "pdf", "images", "folder"])
        self._format_combo.setFixedWidth(80)
        controls.addWidget(self._format_combo)

        # Quality selector
        qual_label = QLabel("Quality:")
        qual_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: 12px;")
        controls.addWidget(qual_label)

        self._quality_combo = QComboBox()
        self._quality_combo.addItems(["original", "high", "medium", "low"])
        self._quality_combo.setFixedWidth(80)
        controls.addWidget(self._quality_combo)

        layout.addLayout(controls)

        # Table
        self._table = QTableWidget()
        self._table.setObjectName("chapterTable")
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["✓", "Ch.", "Title", "Group", "Pages", "Lang"]
        )
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(0, 36)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table, stretch=1)

        # Delete images checkbox + Download button
        footer = QHBoxLayout()
        footer.setContentsMargins(12, 8, 12, 8)

        self._delete_checkbox = QCheckBox("Delete images after export")
        self._delete_checkbox.setStyleSheet(f"font-size: 12px; color: {Colors.MUTED};")
        footer.addWidget(self._delete_checkbox)

        footer.addStretch()

        self._download_btn = QPushButton("⬇ Download Selected")
        self._download_btn.setObjectName("primaryButton")
        self._download_btn.clicked.connect(self._on_download)
        footer.addWidget(self._download_btn)

        layout.addLayout(footer)

    def _make_control_btn(self, text: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setStyleSheet(
            f"background: {Colors.BG_CARD}; border: 1px solid {Colors.BORDER}; "
            f"border-radius: 4px; padding: 2px 10px; font-size: 11px; color: {Colors.MUTED};"
        )
        btn.clicked.connect(callback)
        return btn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_chapters(self, chapters: list[Chapter]) -> None:
        """Populate the table with chapters."""
        self._chapters = chapters
        self._checkboxes.clear()
        self._table.setRowCount(len(chapters))

        for row, ch in enumerate(chapters):
            # Checkbox
            cb = QCheckBox()
            cb.setObjectName("chapterCheckbox")
            cb.setChecked(True)  # Default: all selected
            self._checkboxes.append(cb)

            # Wrap checkbox in a cell widget for centering
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.addWidget(cb)
            self._table.setCellWidget(row, 0, cell)

            # Chapter number
            ch_item = QTableWidgetItem(f"{ch.chapter_number:g}")
            ch_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ch_item.setFlags(ch_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, ch_item)

            # Title
            title_item = QTableWidgetItem(ch.display_title)
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 2, title_item)

            # Group
            group_item = QTableWidgetItem(ch.group_display)
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 3, group_item)

            # Pages
            pages_item = QTableWidgetItem(str(ch.page_count))
            pages_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pages_item.setFlags(pages_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 4, pages_item)

            # Language
            lang_item = QTableWidgetItem(ch.language)
            lang_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            lang_item.setFlags(lang_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 5, lang_item)

        self._count_label.setText(f"{len(chapters)} chapters")

    def get_selected_chapters(self) -> list[Chapter]:
        """Return the list of chapters whose checkboxes are checked."""
        return [
            ch for ch, cb in zip(self._chapters, self._checkboxes)
            if cb.isChecked()
        ]

    def clear(self) -> None:
        """Clear the table."""
        self._chapters.clear()
        self._checkboxes.clear()
        self._table.setRowCount(0)
        self._count_label.setText("0 chapters")

    # ------------------------------------------------------------------
    # Selection controls
    # ------------------------------------------------------------------

    def _select_all(self) -> None:
        for cb in self._checkboxes:
            cb.setChecked(True)

    def _select_none(self) -> None:
        for cb in self._checkboxes:
            cb.setChecked(False)

    def _select_invert(self) -> None:
        for cb in self._checkboxes:
            cb.setChecked(not cb.isChecked())

    def _apply_range(self) -> None:
        """Select chapters matching a range string like '1-10, 15, 20-30'."""
        text = self._range_input.text().strip()
        if not text:
            return

        # Parse range string
        selected_numbers: set[float] = set()
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    start_val = float(start.strip())
                    end_val = float(end.strip())
                    for n in range(int(start_val), int(end_val) + 1):
                        selected_numbers.add(float(n))
                except ValueError:
                    continue
            else:
                try:
                    selected_numbers.add(float(part))
                except ValueError:
                    continue

        # Apply selection
        for cb, ch in zip(self._checkboxes, self._chapters):
            cb.setChecked(ch.chapter_number in selected_numbers)

    # ------------------------------------------------------------------
    # Download trigger
    # ------------------------------------------------------------------

    def _on_download(self) -> None:
        selected = self.get_selected_chapters()
        if not selected:
            return

        self.download_requested.emit({
            "chapters": selected,
            "format": self._format_combo.currentText(),
            "quality": self._quality_combo.currentText(),
            "delete_images": self._delete_checkbox.isChecked(),
        })
