"""Search command — ``mdnet search <query>``."""

from __future__ import annotations

import typer
from rich.console import Console

from manga_dotnet.cli.error_handler import handle_error

search_app = typer.Typer(invoke_without_command=True)


@search_app.callback(invoke_without_command=True)
def search_callback(
    ctx: typer.Context,
    query: str = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
    language: str = typer.Option("en", "--lang", help="Filter by language"),
    adult: bool = typer.Option(False, "--adult", help="Include adult content"),
) -> None:
    """🔍 Search for manga."""
    if ctx.invoked_subcommand is not None:
        return
    console = Console()

    if query is None:
        console.print("[error]Search query is required.[/error]")
        raise typer.Exit(1)

    try:
        with console.status("[bold purple]Searching..."):
            from manga_dotnet.api.client import MangaDotNetClient
            from manga_dotnet.api.search import SearchAPI
            from manga_dotnet.core.config import Config

            config = Config.load()
            client = MangaDotNetClient(config)
            client.initialize()
            search_api = SearchAPI(client)
            results = search_api.search(query, limit=limit)

        if not results:
            console.print("[warning]No results found for that query.[/warning]")
            raise typer.Exit(1)

        from manga_dotnet.cli.widgets.search_results import create_search_table

        table = create_search_table(results, query)
        console.print(table)
        console.print()

        if typer.confirm("Select a manga to view details?"):
            choice = typer.prompt("Enter number", type=int)
            if 1 <= choice <= len(results):
                from manga_dotnet.cli.commands.info import show_manga_info
                show_manga_info(results[choice - 1].id)

    except (KeyboardInterrupt, typer.Exit):
        raise
    except Exception as e:
        handle_error(console, e)
        raise typer.Exit(1)
