"""GUI error handling — global exception handler for PyQt6 application."""

from __future__ import annotations

import logging
import traceback

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget

from manga_dotnet.core.exceptions import (
    APIError,
    ConnectionError,
    DiskSpaceError,
    DownloadError,
    ExportError,
    ImageDownloadError,
    MangaDotNetError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

logger = logging.getLogger(__name__)


def handle_gui_error(parent: QWidget | None, error: Exception) -> None:
    """Show a user-friendly error dialog for unhandled exceptions.

    Call this from the global exception hook or ``sys.excepthook``.
    """
    title, message, icon = _format_error(error)

    logger.error("Unhandled error: %s: %s", type(error).__name__, error)

    msgbox = QMessageBox(parent)
    msgbox.setWindowTitle(title)
    msgbox.setText(message)
    msgbox.setIcon(icon)
    msgbox.exec()


def _format_error(error: Exception) -> tuple[str, str, QMessageBox.Icon]:
    """Return (title, message, icon) for an exception."""
    if isinstance(error, RateLimitError):
        retry = f"Retry after {error.retry_after:.0f}s" if error.retry_after else "Wait a moment and try again."
        return (
            "Rate Limited",
            f"The server is limiting requests.\n\n{retry}",
            QMessageBox.Icon.Warning,
        )

    if isinstance(error, NotFoundError):
        return (
            "Not Found",
            "The requested manga or chapter was not found.\n\nCheck the ID and try again.",
            QMessageBox.Icon.Critical,
        )

    if isinstance(error, ImageDownloadError):
        return (
            "Image Download Failed",
            f"URL: {error.url}\n\nThis image will be skipped.",
            QMessageBox.Icon.Warning,
        )

    if isinstance(error, DiskSpaceError):
        return (
            "Insufficient Disk Space",
            "Not enough disk space to complete the download.\n\nFree up space and try again.",
            QMessageBox.Icon.Critical,
        )

    if isinstance(error, ExportError):
        return (
            "Export Failed",
            "Failed to create the export file.\n\nCheck write permissions and disk space.",
            QMessageBox.Icon.Critical,
        )

    if isinstance(error, ConnectionError):
        suggestion = getattr(error, "suggestion", None) or (
            "Check your internet connection and try again.\n"
            "The Cloudflare challenge may have failed."
        )
        return (
            "Connection Error",
            suggestion,
            QMessageBox.Icon.Critical,
        )

    if isinstance(error, ServerError):
        return (
            "Server Error",
            f"The MangaDotNet server returned an error ({error.status_code}).\n\nTry again in a few minutes.",
            QMessageBox.Icon.Critical,
        )

    if isinstance(error, APIError):
        detail = f" (HTTP {error.status_code})" if error.status_code else ""
        return (
            f"API Error{detail}",
            str(error),
            QMessageBox.Icon.Critical,
        )

    if isinstance(error, MangaDotNetError):
        suggestion = getattr(error, "suggestion", None)
        msg = str(error)
        if suggestion:
            msg += f"\n\nSuggestion: {suggestion}"
        return (
            type(error).__name__,
            msg,
            QMessageBox.Icon.Critical,
        )

    # Unexpected error
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    return (
        "Unexpected Error",
        f"{type(error).__name__}: {error}\n\n{''.join(tb[-3:])}",
        QMessageBox.Icon.Critical,
    )


class GlobalExceptionHandler:
    """Install a global exception hook for the PyQt6 application."""

    error_occurred = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        self._parent = parent
        self._install_hook()

    def _install_hook(self) -> None:
        import sys

        original_hook = sys.excepthook

        def _hook(exc_type, exc_value, exc_tb):
            if exc_type is KeyboardInterrupt:
                sys.exit(0)
            handle_gui_error(self._parent, exc_value)
            original_hook(exc_type, exc_value, exc_tb)

        sys.excepthook = _hook
