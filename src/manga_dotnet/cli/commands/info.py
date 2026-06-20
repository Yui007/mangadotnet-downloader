"""Info command — ``mdnet info <manga_id>``."""

from __future__ import annotations

import re

import typer
from rich.console import Console

from manga_dotnet.cli.error_handler import handle_error

info_app = typer.Typer(invoke_without_command=True)


def _extract_manga_id(value: str) -> int | None:
    """Extract manga ID from a URL or plain number.

    Supports:
    - https://mangadot.net/manga/166
    - https://mangadot.net/166/the-devil-butler
    - 166
    """
    value = value.strip()

    # Plain number
    if value.isdigit():
        return int(value)

    # URL patterns
    match = re.search(r"mangadot\.net/(?:manga/)?(\d+)", value, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def show_manga_info(manga_id: int) -> None:
    """Fetch and display manga info."""
    console = Console()

    try:
        with console.status("[bold purple]Fetching manga info..."):
            from manga_dotnet.api.client import MangaDotNetClient
            from manga_dotnet.api.manga import MangaAPI
            from manga_dotnet.core.config import Config

            config = Config.load()
            client = MangaDotNetClient(config)
            client.initialize()
            manga_api = MangaAPI(client)
            manga = manga_api.get_info(manga_id)

        from manga_dotnet.cli.widgets.manga_panel import create_manga_panel
        panel = create_manga_panel(manga)
        console.print(panel)

    except (KeyboardInterrupt, typer.Exit):
        raise
    except Exception as e:
        handle_error(console, e)
        raise typer.Exit(1)


@info_app.callback(invoke_without_command=True)
def info_callback(
    ctx: typer.Context,
    manga_id: str = typer.Argument(None, help="Manga ID or URL"),
) -> None:
    """📖 View manga details.

    Accepts a manga ID (e.g. 166) or a MangaDotNet URL
    (e.g. https://mangadot.net/manga/166).
    """
    if ctx.invoked_subcommand is not None:
        return
    if manga_id is None:
        console = Console()
        console.print("[error]Manga ID or URL is required.[/error]")
        console.print("[dim]Usage: mdnet info 166[/dim]")
        console.print("[dim]       mdnet info https://mangadot.net/manga/166[/dim]")
        raise typer.Exit(1)

    parsed_id = _extract_manga_id(manga_id)
    if parsed_id is None:
        console = Console()
        console.print(f"[error]Could not extract manga ID from: {manga_id}[/error]")
        raise typer.Exit(1)

    show_manga_info(parsed_id)
