"""Batch command — ``mdnet batch <file>``."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

batch_app = typer.Typer(invoke_without_command=True)


@batch_app.callback(invoke_without_command=True)
def batch_callback(
    ctx: typer.Context,
    file: Path = typer.Argument(None, help="JSON file with batch download tasks"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be downloaded"),
) -> None:
    """📦 Batch download from JSON file."""
    if ctx.invoked_subcommand is not None:
        return
    console = Console()

    if file is None:
        console.print("[error]File path is required.[/error]")
        raise typer.Exit(1)

    if not file.exists():
        console.print(f"[error]File not found: {file}[/error]")
        raise typer.Exit(1)

    try:
        with open(file, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[error]Invalid JSON: {e}[/error]")
        raise typer.Exit(1)

    downloads = data.get("downloads", [])
    if not downloads:
        console.print("[error]No downloads found in file.[/error]")
        raise typer.Exit(1)

    console.print(f"[info]Found {len(downloads)} tasks[/info]")
    for idx, task in enumerate(downloads, 1):
        manga_id = task.get("manga_id", "?")
        chapters = task.get("chapters", task.get("latest", "all"))
        fmt = task.get("format", "cbz")
        console.print(f"  {idx}. Manga #{manga_id} — chapters: {chapters} — format: {fmt}")

    if dry_run:
        console.print("\n[dim]Dry run — no downloads performed[/dim]")
        return

    if not typer.confirm("Proceed with batch download?"):
        raise typer.Exit(0)
    console.print("[success]Batch download started (implementation pending)[/success]")
