"""Library management — track downloaded manga and download history.

Uses a lightweight JSON database stored alongside the config for
persistence without requiring SQLite.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from manga_dotnet.core.config import SETTINGS_FILE

logger = logging.getLogger(__name__)

HISTORY_FILE = "download_history.json"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class MangaEntry:
    """A single manga in the local library."""

    manga_id: int
    title: str
    path: str  # Absolute path to the manga directory
    chapter_count: int = 0
    total_size_bytes: int = 0
    last_downloaded: str = ""  # ISO timestamp
    status: str = "unknown"  # "ongoing", "completed", "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MangaEntry:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HistoryEntry:
    """A single download history record."""

    manga_id: int
    manga_title: str
    chapter_range: str
    export_format: str
    timestamp: str  # ISO timestamp
    chapters_downloaded: int = 0
    total_pages: int = 0
    output_path: str = ""
    cover_url: str = ""       # Manga cover/thumbnail URL
    status: str = "success"  # "success", "partial", "failed"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryEntry:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LibraryStats:
    """Aggregate library statistics."""

    total_manga: int = 0
    total_chapters: int = 0
    total_size_bytes: int = 0
    total_downloads: int = 0
    last_download: str = ""

    @property
    def total_size_display(self) -> str:
        return _format_size(self.total_size_bytes)


# ---------------------------------------------------------------------------
# Library Manager
# ---------------------------------------------------------------------------

class LibraryManager:
    """Track and manage downloaded manga and download history.

    Data is stored as JSON files in the same directory as settings.json
    (project root by default).
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            # Default: project root (same as settings.json)
            data_dir = Path.cwd()
        self._data_dir = data_dir
        self._history_path = data_dir / HISTORY_FILE
        self._entries: list[HistoryEntry] = []
        self._load_history()

    # ------------------------------------------------------------------
    # History: load / save
    # ------------------------------------------------------------------

    def _load_history(self) -> None:
        if self._history_path.exists():
            try:
                with open(self._history_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = [HistoryEntry.from_dict(e) for e in data]
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Failed to load history: %s", e)
                self._entries = []
        else:
            self._entries = []

    def _save_history(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._entries]
        with open(self._history_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # History: public API
    # ------------------------------------------------------------------

    def record_download(
        self,
        manga_id: int,
        manga_title: str,
        chapter_range: str,
        export_format: str,
        chapters_downloaded: int = 0,
        total_pages: int = 0,
        output_path: str = "",
        cover_url: str = "",
        status: str = "success",
        errors: list[str] | None = None,
    ) -> HistoryEntry:
        """Record a completed download."""
        entry = HistoryEntry(
            manga_id=manga_id,
            manga_title=manga_title,
            chapter_range=chapter_range,
            export_format=export_format,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            chapters_downloaded=chapters_downloaded,
            total_pages=total_pages,
            output_path=output_path,
            cover_url=cover_url,
            status=status,
            errors=errors or [],
        )
        self._entries.insert(0, entry)  # Most recent first
        self._save_history()
        logger.info("Recorded download: %s — %s", manga_title, chapter_range)
        return entry

    def get_history(self, limit: int = 50) -> list[HistoryEntry]:
        """Get recent download history."""
        return self._entries[:limit]

    def clear_history(self) -> None:
        """Clear all download history."""
        self._entries.clear()
        self._save_history()

    # ------------------------------------------------------------------
    # Library scanning
    # ------------------------------------------------------------------

    def scan_directory(self, path: Path | str | None = None) -> list[MangaEntry]:
        """Scan a directory for downloaded manga.

        Looks for subdirectories containing image files, CBZ/ZIP archives,
        or PDF files.
        """
        if path is None:
            from manga_dotnet.core.config import Config

            config = Config.load()
            path = config.output_dir
        else:
            path = Path(path)

        if not path.exists():
            return []

        entries: list[MangaEntry] = []
        manga_extensions = {".jpg", ".jpeg", ".png", ".webp", ".cbz", ".zip", ".pdf"}

        for entry in sorted(path.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue

            # Count manga files (recursive)
            files = [f for f in entry.rglob("*") if f.is_file()]
            manga_files = [f for f in files if f.suffix.lower() in manga_extensions]

            if not manga_files:
                continue

            total_size = sum(f.stat().st_size for f in files)
            last_modified = max(
                (f.stat().st_mtime for f in manga_files), default=0
            )

            entries.append(MangaEntry(
                manga_id=hash(entry.name) % 100000,  # Deterministic pseudo-ID
                title=entry.name,
                path=str(entry),
                chapter_count=len(manga_files),
                total_size_bytes=total_size,
                last_downloaded=time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(last_modified)
                ),
            ))

        return entries

    def get_stats(self, path: Path | str | None = None) -> LibraryStats:
        """Get aggregate library statistics."""
        entries = self.scan_directory(path)
        return LibraryStats(
            total_manga=len(entries),
            total_chapters=sum(e.chapter_count for e in entries),
            total_size_bytes=sum(e.total_size_bytes for e in entries),
            total_downloads=len(self._entries),
            last_download=self._entries[0].timestamp if self._entries else "",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
