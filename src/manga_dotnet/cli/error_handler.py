"""CLI error handling — user-friendly error display with suggestions."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

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


def handle_error(console: Console, error: Exception) -> None:
    """Display an error with a user-friendly message and suggestion.

    Call this in CLI command ``except`` blocks to show rich-formatted
    error panels instead of raw tracebacks.
    """
    if isinstance(error, RateLimitError):
        retry_msg = (
            f"Retry after {error.retry_after:.0f}s"
            if error.retry_after
            else "Wait a moment and try again."
        )
        console.print(Panel(
            f"[yellow]Rate Limited[/yellow]\n\n"
            f"The server is limiting requests.\n{retry_msg}",
            title="⚠️ Too Many Requests",
            border_style="yellow",
        ))

    elif isinstance(error, NotFoundError):
        console.print(Panel(
            f"[red]Not Found[/red]\n\n"
            f"The requested manga or chapter was not found.\n"
            f"Check the ID and try again.",
            title="🔍 Not Found",
            border_style="red",
        ))

    elif isinstance(error, ImageDownloadError):
        console.print(Panel(
            f"[red]Image Download Failed[/red]\n\n"
            f"URL: {error.url}\n"
            f"Reason: {error}\n\n"
            f"[dim]This image will be skipped.[/dim]",
            title="❌ Image Error",
            border_style="red",
        ))

    elif isinstance(error, DiskSpaceError):
        console.print(Panel(
            f"[red]Insufficient Disk Space[/red]\n\n"
            f"Not enough disk space to complete the download.\n"
            f"Free up space and try again.",
            title="💾 Disk Full",
            border_style="red",
        ))

    elif isinstance(error, ExportError):
        console.print(Panel(
            f"[red]Export Failed[/red]\n\n"
            f"Failed to create the export file.\n"
            f"Check write permissions and available disk space.",
            title="📦 Export Error",
            border_style="red",
        ))

    elif isinstance(error, ConnectionError):
        suggestion = getattr(error, "suggestion", None) or (
            "Check your internet connection and try again.\n"
            "If the problem persists, the Cloudflare challenge may have failed.\n"
            "Try running the command again."
        )
        console.print(Panel(
            f"[red]Connection Error[/red]\n\n"
            f"{suggestion}",
            title="🌐 Connection Failed",
            border_style="red",
        ))

    elif isinstance(error, ServerError):
        console.print(Panel(
            f"[red]Server Error ({error.status_code})[/red]\n\n"
            f"The MangaDotNet server is experiencing issues.\n"
            f"Try again in a few minutes.",
            title="🔧 Server Error",
            border_style="red",
        ))

    elif isinstance(error, APIError):
        detail = f" (HTTP {error.status_code})" if error.status_code else ""
        console.print(Panel(
            f"[red]API Error{detail}[/red]\n\n"
            f"{error}",
            title="❌ API Error",
            border_style="red",
        ))

    elif isinstance(error, DownloadError):
        console.print(Panel(
            f"[red]Download Error[/red]\n\n"
            f"{error}",
            title="⬇️ Download Failed",
            border_style="red",
        ))

    elif isinstance(error, MangaDotNetError):
        suggestion = getattr(error, "suggestion", None)
        msg = f"{error}"
        if suggestion:
            msg += f"\n\n[dim]Suggestion: {suggestion}[/dim]"
        console.print(Panel(
            f"[red]{type(error).__name__}[/red]\n\n{msg}",
            title="❌ Error",
            border_style="red",
        ))

    else:
        # Unexpected error — show the full repr
        console.print(Panel(
            f"[red]{type(error).__name__}: {error}[/red]",
            title="❌ Unexpected Error",
            border_style="red",
        ))
