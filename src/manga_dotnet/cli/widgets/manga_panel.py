"""Manga info display panel — beautiful Rich panel for manga metadata."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from manga_dotnet.core.models import MangaInfo


def create_manga_panel(manga: MangaInfo) -> Panel:
    """Create a rich panel displaying manga information."""
    # Header with title and rating
    header = Text()
    header.append(manga.title, style="bold magenta")
    if manga.rating:
        header.append(f"  ⭐ {manga.rating}", style="bold yellow")

    # Info grid
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Key", style="dim")
    info_table.add_column("Value")

    info_table.add_row("Status", Text(manga.status, style="cyan"))
    info_table.add_row("Chapters", str(manga.chapter_count))
    info_table.add_row(
        "Authors",
        ", ".join(manga.authors) if manga.authors else "—",
    )
    info_table.add_row(
        "Artists",
        ", ".join(manga.artists) if manga.artists else "—",
    )
    if manga.year:
        info_table.add_row("Year", str(manga.year))
    if manga.country_of_origin:
        info_table.add_row("Country", manga.country_of_origin)
    if manga.hiatus == "Yes":
        info_table.add_row("Hiatus", Text("Yes", style="red"))

    # Genres
    genres = " · ".join(f"[cyan]{g}[/cyan]" for g in manga.genres)

    # Description (truncated)
    desc = manga.description
    if len(desc) > 300:
        desc = desc[:300] + "..."

    # Build content
    parts = [info_table]
    if genres:
        parts.append(Text(f"\nGenres: {genres}"))
    if desc:
        parts.append(Text(f"\n{desc}", style="dim"))

    content = Text()
    for part in parts:
        if isinstance(part, Table):
            # Render table to text
            from io import StringIO
            from rich.console import Console as RichConsole
            buf = StringIO()
            tmp = RichConsole(file=buf, force_terminal=True, width=80)
            tmp.print(part)
            content.append(buf.getvalue())
        else:
            content.append_text(part)

    return Panel(
        content,
        title=header,
        border_style="purple",
        padding=(1, 2),
    )
