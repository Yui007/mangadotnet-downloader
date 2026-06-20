"""MangaDotNet Downloader — main Typer CLI application.

Entry point: ``mdnet`` command or ``python -m manga_dotnet``.
"""

from __future__ import annotations

import typer

from manga_dotnet.cli.widgets.theme import CUSTOM_THEME

# Create the main app
app = typer.Typer(
    name="mdnet",
    help="📚 MangaDotNet Downloader — Beautiful manga downloader for MangaDotNet",
    add_completion=False,
    rich_markup_mode="rich",
)

# Import and register sub-commands
from manga_dotnet.cli.commands.search import search_app
from manga_dotnet.cli.commands.info import info_app
from manga_dotnet.cli.commands.download import download_app
from manga_dotnet.cli.commands.batch import batch_app
from manga_dotnet.cli.commands.library import library_app
from manga_dotnet.cli.commands.history import history_app
from manga_dotnet.cli.commands.settings_cmd import settings_app
from manga_dotnet.cli.commands.updates import updates_app

app.add_typer(search_app, name="search", help="🔍 Search for manga")
app.add_typer(info_app, name="info", help="📖 View manga details")
app.add_typer(download_app, name="download", help="⬇️  Download chapters")
app.add_typer(batch_app, name="batch", help="📦 Batch download from file")
app.add_typer(library_app, name="library", help="📚 Local library management")
app.add_typer(history_app, name="history", help="📋 Download history")
app.add_typer(settings_app, name="settings", help="⚙️  Configuration")
app.add_typer(updates_app, name="updates", help="🔄 Check for new chapters")


@app.command()
def shell() -> None:
    """🚀 Start interactive mode."""
    from manga_dotnet.cli.commands.interactive import interactive_shell

    interactive_shell()


@app.command()
def version() -> None:
    """Show version info."""
    from rich.console import Console

    from manga_dotnet import __version__

    console = Console()
    console.print(f"[bold magenta]MangaDotNet Downloader[/bold magenta] v{__version__}")


def main() -> None:
    """Entry point for the ``mdnet`` CLI command."""
    app()


if __name__ == "__main__":
    main()
