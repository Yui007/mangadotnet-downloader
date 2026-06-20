"""Library command — ``mdnet library``."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from manga_dotnet.cli.error_handler import handle_error

library_app = typer.Typer(invoke_without_command=True)


@library_app.callback(invoke_without_command=True)
def library_callback(
    ctx: typer.Context,
    output_dir: str = typer.Option(None, "--dir", "-d", help="Library directory"),
    stats: bool = typer.Option(False, "--stats", help="Show library statistics"),
    clear: bool = typer.Option(False, "--clear", help="Clear download history"),
) -> None:
    """📚 View local library and download history."""
    if ctx.invoked_subcommand is not None:
        return
    console = Console()

    try:
        from manga_dotnet.core.history import LibraryManager

        lib_dir = Path(output_dir) if output_dir else None
        manager = LibraryManager()

        if clear:
            manager.clear_history()
            console.print("[success]Download history cleared.[/success]")
            return

        if stats:
            _show_stats(console, manager, lib_dir)
            return

        # Default: show library contents
        entries = manager.scan_directory(lib_dir)

        if not entries:
            console.print("[dim]No manga found in library.[/dim]")
            console.print("[dim]Set output_dir in settings or use --dir[/dim]")
            return

        from manga_dotnet.utils.filesystem import format_size

        table = Table(title="📚 Local Library", show_header=True, header_style="bold purple")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold")
        table.add_column("Chapters", justify="right")
        table.add_column("Size", justify="right", style="dim")
        table.add_column("Last Downloaded", style="dim")

        for idx, entry in enumerate(entries, 1):
            table.add_row(
                str(idx),
                entry.title,
                str(entry.chapter_count),
                format_size(entry.total_size_bytes),
                entry.last_downloaded[:10] if entry.last_downloaded else "—",
            )

        console.print(table)

        total_size = sum(e.total_size_bytes for e in entries)
        console.print(f"\n[dim]{len(entries)} manga — {format_size(total_size)} total[/dim]")

        # Also show recent history
        history = manager.get_history(limit=5)
        if history:
            console.print()
            hist_table = Table(title="📋 Recent Downloads", show_header=True, header_style="bold green")
            hist_table.add_column("Title", style="bold")
            hist_table.add_column("Chapters")
            hist_table.add_column("Format")
            hist_table.add_column("Date", style="dim")
            hist_table.add_column("Status")

            for h in history:
                status_style = "green" if h.status == "success" else "yellow" if h.status == "partial" else "red"
                hist_table.add_row(
                    h.manga_title,
                    h.chapter_range,
                    h.export_format.upper(),
                    h.timestamp[:10],
                    f"[{status_style}]{h.status}[/{status_style}]",
                )
            console.print(hist_table)

    except (KeyboardInterrupt, typer.Exit):
        raise
    except Exception as e:
        handle_error(console, e)
        raise typer.Exit(1)


def _show_stats(console: Console, manager, lib_dir) -> None:
    """Display library statistics."""
    from manga_dotnet.utils.filesystem import format_size

    stats = manager.get_stats(lib_dir)

    from rich.panel import Panel

    console.print(Panel(
        f"[bold]Library Statistics[/bold]\n\n"
        f"  Manga:          {stats.total_manga}\n"
        f"  Total chapters: {stats.total_chapters}\n"
        f"  Total size:     {stats.total_size_display}\n"
        f"  Total downloads: {stats.total_downloads}\n"
        f"  Last download:  {stats.last_download[:10] if stats.last_download else 'Never'}",
        title="📊 Library Stats",
        border_style="purple",
    ))
