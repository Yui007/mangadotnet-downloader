"""History command — ``mdnet history``."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from manga_dotnet.cli.error_handler import handle_error

history_app = typer.Typer(invoke_without_command=True)


@history_app.callback(invoke_without_command=True)
def history_callback(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", "-l", help="Max entries to show"),
    clear: bool = typer.Option(False, "--clear", help="Clear all history"),
) -> None:
    """📋 View download history."""
    if ctx.invoked_subcommand is not None:
        return
    console = Console()

    try:
        from manga_dotnet.core.history import LibraryManager

        manager = LibraryManager()

        if clear:
            manager.clear_history()
            console.print("[success]Download history cleared.[/success]")
            return

        history = manager.get_history(limit=limit)

        if not history:
            console.print("[dim]No download history found.[/dim]")
            console.print("[dim]Downloads will be recorded automatically.[/dim]")
            return

        table = Table(
            title="📋 Download History",
            show_header=True,
            header_style="bold purple",
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold")
        table.add_column("Chapters")
        table.add_column("Format")
        table.add_column("Pages", justify="right")
        table.add_column("Date", style="dim")
        table.add_column("Status")

        for idx, entry in enumerate(history, 1):
            status_style = (
                "green" if entry.status == "success"
                else "yellow" if entry.status == "partial"
                else "red"
            )
            table.add_row(
                str(idx),
                entry.manga_title,
                entry.chapter_range,
                entry.export_format.upper(),
                str(entry.total_pages) if entry.total_pages else "—",
                entry.timestamp[:10],
                f"[{status_style}]{entry.status}[/{status_style}]",
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(history)} of {len(manager.get_history(9999))} entries[/dim]")

    except (KeyboardInterrupt, typer.Exit):
        raise
    except Exception as e:
        handle_error(console, e)
        raise typer.Exit(1)
