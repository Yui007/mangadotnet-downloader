"""Update checker command — ``mdnet updates``."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from manga_dotnet.cli.error_handler import handle_error

updates_app = typer.Typer(invoke_without_command=True)


@updates_app.callback(invoke_without_command=True)
def updates_callback(
    ctx: typer.Context,
    output_dir: str = typer.Option(None, "--dir", "-d", help="Library directory"),
    manga_id: int = typer.Option(None, "--manga-id", "-m", help="Check single manga"),
) -> None:
    """🔄 Check for new chapters in library manga."""
    if ctx.invoked_subcommand is not None:
        return
    console = Console()

    try:
        from manga_dotnet.core.history import LibraryManager
        from manga_dotnet.core.updates import UpdateChecker

        lib_dir = Path(output_dir) if output_dir else None
        manager = LibraryManager()

        if manga_id:
            # Check single manga
            with console.status(f"[bold purple]Checking manga {manga_id}..."):
                checker = UpdateChecker()
                new_chapters = checker.check_single(manga_id)

            if not new_chapters:
                console.print(f"[dim]No new chapters for manga {manga_id}.[/dim]")
                return

            console.print(f"[success]Found {len(new_chapters)} new chapters:[/success]")
            for ch in new_chapters:
                console.print(f"  • {ch.display_title} ({ch.page_count} pages, {ch.group_display})")
            return

        # Check all library manga
        entries = manager.scan_directory(lib_dir)
        if not entries:
            console.print("[dim]No manga in library to check.[/dim]")
            return

        with console.status(f"[bold purple]Checking {len(entries)} manga for updates..."):
            checker = UpdateChecker()
            updates = checker.check_library(entries)

        if not updates:
            console.print("[dim]No updates found — your library is up to date![/dim]")
            return

        table = Table(title="🔄 Available Updates", show_header=True, header_style="bold green")
        table.add_column("Manga", style="bold")
        table.add_column("New Chapters")
        table.add_column("Range")

        for update in updates:
            table.add_row(
                update.manga_title,
                str(update.count),
                update.chapter_range,
            )

        console.print(table)
        console.print(f"\n[success]{len(updates)} manga with updates available[/success]")

    except (KeyboardInterrupt, typer.Exit):
        raise
    except Exception as e:
        handle_error(console, e)
        raise typer.Exit(1)
