"""Settings command — ``mdnet settings``."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

settings_app = typer.Typer(invoke_without_command=True)


@settings_app.callback()
def settings_callback(
    ctx: typer.Context,
    key: str = typer.Option(None, "--key", "-k", help="Setting key (dotted path)"),
    value: str = typer.Option(None, "--value", "-v", help="New value"),
) -> None:
    """⚙️ View or modify settings."""
    if ctx.invoked_subcommand is not None:
        return

    console = Console()

    from manga_dotnet.core.config import Config

    config = Config.load()

    if key and value is not None:
        # Set a value
        try:
            if value.lower() in ("true", "false"):
                config.set(key, value.lower() == "true")
            elif value.isdigit():
                config.set(key, int(value))
            else:
                try:
                    config.set(key, float(value))
                except ValueError:
                    config.set(key, value)

            config.save()
            console.print(f"[success]Set {key} = {config.get(key)}[/success]")
        except KeyError:
            console.print(f"[error]Unknown setting: {key}[/error]")
            raise typer.Exit(1)
    elif key:
        val = config.get(key)
        if val is None:
            console.print(f"[warning]Setting not found: {key}[/warning]")
        else:
            console.print(f"{key} = {val}")
    else:
        # Show all settings
        table = Table(
            title="⚙️ Settings",
            show_header=True,
            header_style="bold purple",
        )
        table.add_column("Key", style="bold")
        table.add_column("Value")

        settings_list = [
            ("output_dir", str(config.output_dir)),
            ("default_format", config.default_format),
            ("default_language", config.default_language),
            ("download.max_concurrent_chapters", str(config.download.max_concurrent_chapters)),
            ("download.max_concurrent_images", str(config.download.max_concurrent_images)),
            ("download.max_concurrent_downloads", str(config.download.max_concurrent_downloads)),
            ("download.max_retries", str(config.download.max_retries)),
            ("download.timeout", f"{config.download.timeout}s"),
            ("quality.delete_images_after_export", str(config.quality.delete_images_after_export)),
            ("cache.enabled", str(config.cache.enabled)),
            ("cache.max_size_mb", str(config.cache.max_size_mb)),
            ("network.proxy", config.network.proxy or "none"),
            ("gui.theme", config.gui.theme),
        ]

        for k, v in settings_list:
            table.add_row(k, v)

        console.print(table)
        console.print(f"\n[dim]Edit settings.json directly or use: mdnet settings --key <key> --value <val>[/dim]")
