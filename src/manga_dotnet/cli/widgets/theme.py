"""Color themes and styling for CLI Rich output."""

from __future__ import annotations

from rich.theme import Theme

CUSTOM_THEME = Theme({
    "info": "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "manga.title": "bold magenta",
    "manga.rating": "bold yellow",
    "manga.status": "bold cyan",
    "manga.chapters": "bold white",
    "progress.complete": "bold green",
    "progress.pending": "dim white",
})
