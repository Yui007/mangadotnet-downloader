"""Left sidebar navigation — icon + text tabs with collapse support."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .themes import Colors

# ---------------------------------------------------------------------------
# Sidebar stylesheet
# ---------------------------------------------------------------------------

_SIDEBAR_QSS = f"""
QWidget#sidebar {{
    background-color: {Colors.BG_CARD};
    border-right: 1px solid {Colors.BORDER};
}}
QPushButton.navButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    text-align: left;
    font-size: 13px;
    color: {Colors.MUTED};
}}
QPushButton.navButton:hover {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT};
}}
QPushButton.navButton:checked {{
    background-color: {Colors.PRIMARY}20;
    color: {Colors.PRIMARY};
    border-left: 3px solid {Colors.PRIMARY};
}}
QPushButton.collapseBtn {{
    background: transparent;
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px;
    font-size: 12px;
    color: {Colors.MUTED};
}}
QPushButton.collapseBtn:hover {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT};
}}
"""


# ---------------------------------------------------------------------------
# Sidebar navigation widget
# ---------------------------------------------------------------------------

class SidebarNav(QWidget):
    """Left sidebar with icon + text navigation tabs.

    Emits ``page_changed(int)`` when a tab is clicked, carrying the page index.
    """

    page_changed = pyqtSignal(int)

    TABS: list[tuple[str, str]] = [
        ("🔗", "Open URL"),
        ("🔍", "Search"),
        ("⬇️", "Downloads"),
        ("📋", "History"),
        ("⚙️", "Settings"),
    ]

    EXPANDED_WIDTH = 180
    COLLAPSED_WIDTH = 72

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.setStyleSheet(_SIDEBAR_QSS)

        self._active_index = 0
        self._buttons: list[QPushButton] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        # App logo
        logo = QLabel("📚")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 24px; padding: 12px;")
        layout.addWidget(logo)

        layout.addSpacing(8)

        # Navigation buttons
        for idx, (icon, text) in enumerate(self.TABS):
            btn = QPushButton(f"  {icon}  {text}")
            btn.setProperty("class", "navButton")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked, i=idx: self._on_tab_clicked(i))
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Collapse toggle
        self._collapse_btn = QPushButton("◀")
        self._collapse_btn.setProperty("class", "collapseBtn")
        self._collapse_btn.setFixedSize(36, 36)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.clicked.connect(self._toggle_collapse)
        layout.addWidget(self._collapse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    # ------------------------------------------------------------------
    # Tab handling
    # ------------------------------------------------------------------

    def _on_tab_clicked(self, index: int) -> None:
        """Update active state and emit page_changed."""
        self._buttons[self._active_index].setChecked(False)
        self._active_index = index
        self._buttons[index].setChecked(True)
        self.page_changed.emit(index)

    def set_current_index(self, index: int) -> None:
        """Programmatically switch the active tab."""
        if 0 <= index < len(self._buttons) and index != self._active_index:
            self._on_tab_clicked(index)

    # ------------------------------------------------------------------
    # Collapse / expand
    # ------------------------------------------------------------------

    def _toggle_collapse(self) -> None:
        if self.width() > self.COLLAPSED_WIDTH:
            self._collapse()
        else:
            self._expand()

    def _collapse(self) -> None:
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        for btn in self._buttons:
            # Show icon only (first token after leading spaces)
            full_text = btn.text()
            icon = full_text.strip().split()[0] if full_text.strip() else ""
            btn.setText(f"  {icon}  ")
        self._collapse_btn.setText("▶")

    def _expand(self) -> None:
        self.setFixedWidth(self.EXPANDED_WIDTH)
        for idx, (icon, text) in enumerate(self.TABS):
            self._buttons[idx].setText(f"  {icon}  {text}")
        self._collapse_btn.setText("◀")
