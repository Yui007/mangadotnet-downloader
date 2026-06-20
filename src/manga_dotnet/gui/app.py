"""GUI application entry point.

Launch with::

    python -m manga_dotnet.gui.app

Or via the ``mdnet-gui`` console script (defined in pyproject.toml).
"""

from __future__ import annotations

import sys


def main() -> None:
    """Launch the MangaDotNet Downloader GUI."""
    from PyQt6.QtWidgets import QApplication

    from .error_handler import GlobalExceptionHandler
    from .main_window import MainWindow
    from .themes import DARK_THEME_QSS

    app = QApplication(sys.argv)
    app.setApplicationName("MangaDotNet Downloader")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")  # Consistent cross-platform base

    # Install global exception handler
    exception_handler = GlobalExceptionHandler()

    window = MainWindow()
    exception_handler._parent = window
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
