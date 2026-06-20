"""Search results display — table for search output."""

from __future__ import annotations

from rich.table import Table

from manga_dotnet.core.models import MangaResult


def create_search_table(
    results: list[MangaResult],
    query: str,
) -> Table:
    """Create a Rich table displaying search results."""
    table = Table(
        title=f'🔍 Search Results — "{query}"',
        show_header=True,
        header_style="bold purple",
        border_style="dim",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold")
    table.add_column("Status", style="cyan")
    table.add_column("Rating", style="yellow")
    table.add_column("Chapters", justify="right")
    table.add_column("Genres", style="dim")

    for idx, manga in enumerate(results, 1):
        rating = f"⭐ {manga.rating}" if manga.rating else "—"
        genres = " · ".join(manga.genres[:3])
        if len(manga.genres) > 3:
            genres += " ..."

        table.add_row(
            str(idx),
            manga.title,
            manga.status,
            rating,
            str(manga.chapter_count),
            genres,
        )

    return table
