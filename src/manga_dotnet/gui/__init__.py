"""GUI interface — PyQt6 application with left sidebar navigation.

Launch with ``python -m manga_dotnet.gui.app`` or ``mdnet-gui``.
"""

from .main_window import MainWindow
from .sidebar import SidebarNav
from .themes import Colors, DARK_THEME_QSS

__all__ = ["MainWindow", "SidebarNav", "Colors", "DARK_THEME_QSS"]
