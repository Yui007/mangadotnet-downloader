"""Light theme — clean, bright palette."""

# Light theme colors
_BG_DARK = "#FFFFFF"
_BG_CARD = "#F6F8FA"
_BG_ELEVATED = "#EBEEF2"
_BORDER = "#D0D7DE"
_TEXT = "#1F2328"
_MUTED = "#656D76"
_PRIMARY = "#6C5CE7"
_SECONDARY = "#00CEC9"
_SUCCESS = "#00B894"
_WARNING = "#FDCB6E"
_ERROR = "#E17055"


def get_light_qss() -> str:
    """Return the complete light theme QSS stylesheet."""
    return f"""
/* ── Global ── */
QWidget {{
    background-color: {_BG_DARK};
    color: {_TEXT};
    font-family: "Segoe UI", "Segoe UI Variable", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}
QMainWindow {{
    background-color: {_BG_DARK};
}}

/* ── Menu Bar ── */
QMenuBar {{
    background-color: {_BG_CARD};
    border-bottom: 1px solid {_BORDER};
    padding: 2px 4px;
}}
QMenuBar::item:selected {{
    background-color: {_BG_ELEVATED};
}}
QMenu {{
    background-color: {_BG_CARD};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {_PRIMARY}20;
    color: {_PRIMARY};
}}

/* ── Status Bar ── */
QStatusBar {{
    background-color: {_BG_CARD};
    border-top: 1px solid {_BORDER};
    color: {_MUTED};
    font-size: 12px;
}}

/* ── Scroll Bars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_MUTED};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Group Boxes ── */
QGroupBox {{
    border: 1px solid {_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    color: {_TEXT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {_PRIMARY};
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {_BG_CARD};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    color: {_TEXT};
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {_BG_ELEVATED};
    border-color: {_PRIMARY}60;
}}
QPushButton:pressed {{
    background-color: {_PRIMARY}20;
}}
QPushButton:disabled {{
    color: {_MUTED};
    background-color: {_BG_DARK};
    border-color: {_BORDER};
}}
QPushButton#primaryButton {{
    background-color: {_PRIMARY};
    border: none;
    color: white;
    font-weight: bold;
}}
QPushButton#primaryButton:hover {{
    background-color: {_PRIMARY}CC;
}}
QPushButton#dangerButton {{
    border-color: {_ERROR};
    color: {_ERROR};
}}

/* ── Line Edits ── */
QLineEdit {{
    background-color: {_BG_CARD};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {_TEXT};
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {_PRIMARY};
}}
QLineEdit::placeholder {{
    color: {_MUTED};
}}

/* ── Spin / Combo ── */
QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {_BG_CARD};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    color: {_TEXT};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {_BG_CARD};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    selection-background-color: {_PRIMARY}20;
}}

/* ── Check Boxes ── */
QCheckBox {{
    spacing: 8px;
    color: {_TEXT};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {_BORDER};
    background-color: {_BG_CARD};
}}
QCheckBox::indicator:checked {{
    background-color: {_PRIMARY};
    border-color: {_PRIMARY};
}}

/* ── Progress Bars ── */
QProgressBar {{
    background-color: {_BG_CARD};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    text-align: center;
    color: {_TEXT};
    height: 20px;
}}
QProgressBar::chunk {{
    background-color: {_PRIMARY};
    border-radius: 3px;
}}

/* ── Labels ── */
QLabel#headingLabel {{
    font-size: 18px;
    font-weight: bold;
    color: {_TEXT};
}}
QLabel#mutedLabel {{
    color: {_MUTED};
    font-size: 12px;
}}
"""
