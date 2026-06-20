"""Chapter selection table — interactive chapter list with Rich."""

from __future__ import annotations

from rich.table import Table

from manga_dotnet.core.models import Chapter


def create_chapter_table(
    chapters: list[Chapter],
    title: str = "Chapters",
    show_index: bool = True,
) -> Table:
    """Create a Rich table displaying chapters."""
    table = Table(
        title=title,
        show_header=True,
        header_style="bold purple",
        border_style="dim",
        padding=(0, 1),
    )

    if show_index:
        table.add_column("#", style="dim", width=4)
    table.add_column("Ch.", justify="right", style="bold", width=6)
    table.add_column("Title", max_width=40)
    table.add_column("Group", style="cyan", max_width=20)
    table.add_column("Pages", justify="right", style="dim")
    table.add_column("Source", width=3)

    for idx, ch in enumerate(chapters, 1):
        rows = []
        if show_index:
            rows.append(str(idx))
        rows.extend([
            str(ch.chapter_number),
            ch.display_title,
            ch.group_display,
            str(ch.page_count),
            ch.source_badge,
        ])
        table.add_row(*rows)

    return table
