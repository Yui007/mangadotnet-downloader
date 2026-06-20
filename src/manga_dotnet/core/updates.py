"""Auto update — git pull latest from GitHub."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

GITHUB_REPO = "https://github.com/Yui007/mangadotnet-downloader"


def get_project_root() -> Path:
    """Find the project root (where .git lives)."""
    # Start from this file and walk up
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    # Fallback: assume we're in src/manga_dotnet/core, go up 3 levels
    return current.parent.parent.parent.parent


def get_current_version() -> str:
    """Get current version from the installed package."""
    try:
        from manga_dotnet import __version__
        return __version__
    except Exception:
        return "unknown"


def get_local_commit() -> str:
    """Get the current local git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(get_project_root()),
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def get_remote_commit() -> str:
    """Get the latest remote git commit hash."""
    try:
        # Fetch latest without merging
        subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True, text=True, cwd=str(get_project_root()),
            timeout=30,
        )
        result = subprocess.run(
            ["git", "rev-parse", "--short", "origin/main"],
            capture_output=True, text=True, cwd=str(get_project_root()),
            timeout=10,
        )
        if result.returncode != 0:
            # Try master branch
            result = subprocess.run(
                ["git", "rev-parse", "--short", "origin/master"],
                capture_output=True, text=True, cwd=str(get_project_root()),
                timeout=10,
            )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def check_for_updates() -> dict:
    """Check if updates are available.

    Returns:
        dict with keys: update_available (bool), local_commit, remote_commit, message
    """
    local = get_local_commit()
    remote = get_remote_commit()

    if local == "unknown" or remote == "unknown":
        return {
            "update_available": False,
            "local_commit": local,
            "remote_commit": remote,
            "message": "Could not check for updates (git not available).",
        }

    if local == remote:
        return {
            "update_available": False,
            "local_commit": local,
            "remote_commit": remote,
            "message": f"Already up to date (commit: {local}).",
        }

    return {
        "update_available": True,
        "local_commit": local,
        "remote_commit": remote,
        "message": f"Update available: {local} → {remote}",
    }


def auto_update(force: bool = False) -> dict:
    """Run git pull to update to the latest version.

    Args:
        force: If True, pull even if already up to date.

    Returns:
        dict with keys: success (bool), message, pulled (bool)
    """
    check = check_for_updates()

    if not check["update_available"] and not force:
        return {"success": True, "pulled": False, "message": check["message"]}

    try:
        project_root = get_project_root()
        result = subprocess.run(
            ["git", "pull", "origin"],
            capture_output=True, text=True, cwd=str(project_root),
            timeout=60,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if "Already up to date" in output:
                return {"success": True, "pulled": False, "message": "Already up to date."}
            return {
                "success": True,
                "pulled": True,
                "message": f"Updated successfully!\n{output}",
            }
        else:
            error = result.stderr.strip() or result.stdout.strip()
            return {
                "success": False,
                "pulled": False,
                "message": f"Update failed:\n{error}",
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "pulled": False, "message": "Update timed out."}
    except FileNotFoundError:
        return {"success": False, "pulled": False, "message": "git command not found."}
    except Exception as e:
        return {"success": False, "pulled": False, "message": f"Update error: {e}"}


class UpdateChecker:
    """Backward-compatible stub. Use check_for_updates() and auto_update() instead."""

    def __init__(self, client=None) -> None:
        pass

    def check_single(self, manga_id: int, latest_downloaded: float = 0):
        return []

    def check_library(self, library_entries: list) -> list:
        return []


# Backward-compatible dataclass for tests
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ChapterUpdate:
    """A new chapter available for a manga."""
    manga_id: int
    manga_title: str
    new_chapters: list = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.new_chapters)

    @property
    def chapter_range(self) -> str:
        if not self.new_chapters:
            return ""
        nums = sorted(c.chapter_number for c in self.new_chapters)
        if len(nums) == 1:
            return f"{nums[0]:g}"
        return f"{nums[0]:g}-{nums[-1]:g}"
