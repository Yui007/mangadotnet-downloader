"""Download command — ``mdnet download <manga_id>``."""

from __future__ import annotations

import re
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from manga_dotnet.cli.error_handler import handle_error

download_app = typer.Typer(invoke_without_command=True)


def _parse_chapter_range(range_str: str) -> list[int]:
    """Parse chapter range string into list of chapter numbers."""
    chapters: list[int] = []
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            chapters.extend(range(int(start), int(end) + 1))
        elif part.isdigit():
            chapters.append(int(part))
    return sorted(set(chapters))


def _parse_range(range_str: str) -> list[float]:
    """Parse a numeric range string."""
    result: list[float] = []
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            result.extend(range(int(float(start)), int(float(end)) + 1))
        elif part:
            result.append(float(part))
    return sorted(set(result))


def _show_manga_panel(console: Console, info: object) -> None:
    """Show a compact manga info panel before download."""
    from manga_dotnet.cli.widgets.manga_panel import create_manga_panel

    panel = create_manga_panel(info)
    console.print(panel)


def _show_result_panel(console: Console, result: object) -> None:
    """Show download result summary."""
    console.print()
    if getattr(result, "chapters_failed", 0) == 0:
        console.print(Panel(
            f"[success]✓ Download complete![/success]\n"
            f"  Chapters: {getattr(result, 'chapters_downloaded', 0)}\n"
            f"  Pages: {getattr(result, 'total_pages', 0)}\n"
            f"  Output: {getattr(result, 'output_path', '?')}",
            title="Result",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[warning]⚠ Download completed with errors[/warning]\n"
            f"  OK: {getattr(result, 'chapters_downloaded', 0)}  "
            f"Failed: {getattr(result, 'chapters_failed', 0)}\n"
            f"  Errors: {', '.join(getattr(result, 'errors', [])[:3])}",
            title="Result",
            border_style="yellow",
        ))


def _do_download(
    manga_id: int,
    chapters: str | None,
    volumes: str | None,
    latest: int | None,
    all_flag: bool,
    output_dir: Path | None,
    fmt: str,
    language: str,
    concurrency: int,
    delete_images: bool,
) -> None:
    """Core download logic shared by CLI and interactive mode."""
    console = Console()

    from manga_dotnet.api.client import MangaDotNetClient
    from manga_dotnet.api.manga import MangaAPI
    from manga_dotnet.api.chapters import ChapterAPI
    from manga_dotnet.core.config import Config
    from manga_dotnet.core.engine import ChapterFilter

    try:
        config = Config.load()
        client = MangaDotNetClient(config)
        client.initialize()
        manga_api = MangaAPI(client)
        chapter_api = ChapterAPI(client)
        cf = ChapterFilter()

        with console.status("[bold purple]Fetching manga info..."):
            info = manga_api.get_info(manga_id)

        _show_manga_panel(console, info)

        with console.status("[bold purple]Fetching chapters..."):
            all_chapters = chapter_api.get_chapters(manga_id)

        # Filter and deduplicate
        deduped = cf.filter_and_deduplicate(
            all_chapters, language=language, prefer_user_uploaded=config.prefer_user_uploaded
        )

        # Select chapters
        if all_flag:
            selected = deduped
        elif latest:
            selected = sorted(deduped, key=lambda c: c.chapter_number)[-latest:]
        elif chapters:
            nums = _parse_chapter_range(chapters)
            selected = [c for c in deduped if int(c.chapter_number) in nums]
        elif volumes:
            vol_range = _parse_range(volumes)
            selected = [c for c in deduped if c.volume_number and c.volume_number in vol_range]
        else:
            # Interactive selection
            from manga_dotnet.cli.widgets.chapter_table import create_chapter_table

            table = create_chapter_table(deduped, title="Available Chapters")
            console.print(table)
            console.print()
            range_str = typer.prompt("Chapter range (e.g. 1-10, 15, 20-30)")
            nums = _parse_chapter_range(range_str)
            selected = [c for c in deduped if int(c.chapter_number) in nums]

        if not selected:
            console.print("[error]No chapters selected.[/error]")
            raise typer.Exit(1)

        total_pages = sum(c.page_count for c in selected)
        console.print(f"\n[info]Selected: {len(selected)} chapters, {total_pages} pages[/info]")

        if not typer.confirm("Proceed with download?"):
            raise typer.Exit(0)

        console.print(f"\n[success]Ready to download {len(selected)} chapters to {output_dir or config.output_dir}[/success]")
        console.print("[dim](Full download pipeline will be wired in Phase 3.2)[/dim]")

        _show_result_panel(console, type("R", (), {
            "chapters_downloaded": len(selected),
            "chapters_failed": 0,
            "total_pages": total_pages,
            "output_path": output_dir or config.output_dir,
            "errors": [],
        })())

    except (KeyboardInterrupt, typer.Exit):
        raise
    except Exception as e:
        handle_error(console, e)
        raise typer.Exit(1)


@download_app.callback(invoke_without_command=True)
def download_callback(
    ctx: typer.Context,
    manga_id: str = typer.Argument(None, help="Manga ID or URL"),
    chapters: str = typer.Option(None, "--chapters", "-c", help="Chapter range: 1-50,100"),
    volumes: str = typer.Option(None, "--volumes", "-v", help="Volume range: 1-5"),
    latest: int = typer.Option(None, "--latest", "-n", help="Download latest N chapters"),
    all_chapters: bool = typer.Option(False, "--all", help="Download all chapters"),
    output_dir: Path = typer.Option(None, "--output", "-o", help="Output directory"),
    format: str = typer.Option("cbz", "--format", "-f", help="Export format: cbz|zip|pdf|images|folder"),
    language: str = typer.Option("en", "--lang", "-l", help="Preferred language"),
    concurrency: int = typer.Option(8, "--concurrency", help="Max concurrent downloads"),
    delete_images: bool = typer.Option(False, "--delete-images", help="Delete images after export"),
) -> None:
    """⬇️ Download manga chapters.

    Accepts a manga ID (e.g. 166) or a MangaDotNet URL
    (e.g. https://mangadot.net/manga/166).
    """
    if ctx.invoked_subcommand is not None:
        return
    if manga_id is None:
        console = Console()
        console.print("[error]Manga ID or URL is required.[/error]")
        console.print("[dim]Usage: mdnet download 166 --chapters 1-10[/dim]")
        console.print("[dim]       mdnet download https://mangadot.net/manga/166 -c 1-10[/dim]")
        raise typer.Exit(1)

    from manga_dotnet.cli.commands.info import _extract_manga_id

    parsed_id = _extract_manga_id(manga_id)
    if parsed_id is None:
        console = Console()
        console.print(f"[error]Could not extract manga ID from: {manga_id}[/error]")
        raise typer.Exit(1)

    _do_download(parsed_id, chapters, volumes, latest, all_chapters, output_dir, format, language, concurrency, delete_images)
