"""Dark theme (default) — GitHub Dark inspired palette."""

from ..themes import Colors


def get_dark_qss() -> str:
    """Return the complete dark theme QSS stylesheet."""
    return f"""
/* ── Global ── */
QWidget {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT};
    font-family: "Segoe UI", "Segoe UI Variable", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {Colors.BG_DARK};
}}

/* ── Menu Bar ── */
QMenuBar {{
    background-color: {Colors.BG_CARD};
    border-bottom: 1px solid {Colors.BORDER};
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT};
}}
QMenu {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {Colors.PRIMARY}30;
    color: {Colors.PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background: {Colors.BORDER};
    margin: 4px 8px;
}}

/* ── Status Bar ── */
QStatusBar {{
    background-color: {Colors.BG_CARD};
    border-top: 1px solid {Colors.BORDER};
    color: {Colors.MUTED};
    font-size: 12px;
}}

/* ── Scroll Bars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {Colors.BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {Colors.MUTED};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {Colors.BORDER};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {Colors.MUTED};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Group Boxes ── */
QGroupBox {{
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    color: {Colors.TEXT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {Colors.PRIMARY};
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    color: {Colors.TEXT};
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {Colors.BG_ELEVATED};
    border-color: {Colors.PRIMARY}60;
}}
QPushButton:pressed {{
    background-color: {Colors.PRIMARY}30;
}}
QPushButton:disabled {{
    color: {Colors.MUTED};
    background-color: {Colors.BG_DARK};
    border-color: {Colors.BORDER};
}}
QPushButton:checked {{
    background-color: {Colors.PRIMARY}20;
    border-color: {Colors.PRIMARY};
    color: {Colors.PRIMARY};
}}
QPushButton#primaryButton {{
    background-color: {Colors.PRIMARY};
    border: none;
    color: white;
    font-weight: bold;
}}
QPushButton#primaryButton:hover {{
    background-color: {Colors.PRIMARY}CC;
}}
QPushButton#primaryButton:pressed {{
    background-color: {Colors.PRIMARY}99;
}}
QPushButton#dangerButton {{
    border-color: {Colors.ERROR};
    color: {Colors.ERROR};
}}
QPushButton#dangerButton:hover {{
    background-color: {Colors.ERROR}20;
}}

/* ── Line Edits ── */
QLineEdit {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {Colors.TEXT};
    font-size: 13px;
    selection-background-color: {Colors.PRIMARY}60;
}}
QLineEdit:focus {{
    border-color: {Colors.PRIMARY};
}}
QLineEdit::placeholder {{
    color: {Colors.MUTED};
}}

/* ── Spin Boxes ── */
QSpinBox, QDoubleSpinBox {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    color: {Colors.TEXT};
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {Colors.PRIMARY};
}}

/* ── Combo Boxes ── */
QComboBox {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    color: {Colors.TEXT};
    min-width: 100px;
}}
QComboBox:hover {{
    border-color: {Colors.PRIMARY}60;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    selection-background-color: {Colors.PRIMARY}30;
    selection-color: {Colors.PRIMARY};
    padding: 4px;
}}

/* ── Check Boxes ── */
QCheckBox {{
    spacing: 8px;
    color: {Colors.TEXT};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {Colors.BORDER};
    background-color: {Colors.BG_CARD};
}}
QCheckBox::indicator:hover {{
    border-color: {Colors.PRIMARY}80;
}}
QCheckBox::indicator:checked {{
    background-color: {Colors.PRIMARY};
    border-color: {Colors.PRIMARY};
}}

/* ── Labels ── */
QLabel {{
    color: {Colors.TEXT};
}}
QLabel#headingLabel {{
    font-size: 18px;
    font-weight: bold;
    color: {Colors.TEXT};
}}
QLabel#mutedLabel {{
    color: {Colors.MUTED};
    font-size: 12px;
}}

/* ── Cards ── */
QFrame#card {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px;
}}
QFrame#card:hover {{
    border-color: {Colors.PRIMARY}60;
}}

/* ── Progress Bars ── */
QProgressBar {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    text-align: center;
    color: {Colors.TEXT};
    height: 20px;
}}
QProgressBar::chunk {{
    background-color: {Colors.PRIMARY};
    border-radius: 3px;
}}

/* ── Tab Widget ── */
QTabWidget::pane {{
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    background-color: transparent;
}}
QTabBar::tab {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {Colors.MUTED};
}}
QTabBar::tab:selected {{
    background-color: {Colors.PRIMARY}20;
    color: {Colors.PRIMARY};
    border-bottom-color: {Colors.PRIMARY};
}}

/* ── Tooltips ── */
QToolTip {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    color: {Colors.TEXT};
    font-size: 12px;
}}
"""
