"""Filesystem utilities — path sanitization, disk space, file size formatting."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """Remove or replace characters invalid in filenames across platforms."""
    # Replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Collapse multiple underscores/spaces
    name = re.sub(r"[_\s]+", " ", name).strip()
    # Remove leading/trailing dots (Windows issue)
    name = name.strip(".")
    # Truncate to reasonable length
    if len(name) > 200:
        name = name[:200].rstrip()
    return name or "untitled"


def check_disk_space(path: Path, required_bytes: int) -> bool:
    """Check if the filesystem at *path* has at least *required_bytes* free."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free >= required_bytes
    except OSError:
        return False


def get_disk_free_bytes(path: Path) -> int:
    """Return free bytes on the filesystem containing *path*."""
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return 0


def format_size(size_bytes: int) -> str:
    """Human-readable file size (e.g. '1.5 MB')."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} PB"


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it doesn't exist. Returns the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path
