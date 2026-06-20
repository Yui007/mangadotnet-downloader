"""Shared Rich console instance for consistent CLI output."""

from __future__ import annotations

from rich.console import Console

console = Console()
error_console = Console(stderr=True)
