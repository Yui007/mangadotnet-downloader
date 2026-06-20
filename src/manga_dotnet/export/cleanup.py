"""Post-export image cleanup manager.

Safety: Images are only deleted AFTER the export file is verified
to exist and be non-empty. If export fails, images are preserved.
"""

from __future__ import annotations

import logging
from pathlib import Path

from manga_dotnet.export.base import BaseExporter
from manga_dotnet.export.cbz import CBZExporter
from manga_dotnet.export.zip import ZIPExporter
from manga_dotnet.export.pdf import PDFExporter
from manga_dotnet.export.images import ImagesExporter
from manga_dotnet.export.folder import FolderExporter

logger = logging.getLogger(__name__)


class ImageCleanupManager:
    """Manages deletion of source images after successful export."""

    @staticmethod
    async def cleanup(
        image_paths: list[Path],
        export_path: Path,
        enabled: bool = False,
    ) -> int:
        """Delete source images if cleanup is enabled and export is valid.

        Returns number of files deleted.
        """
        if not enabled:
            return 0

        # Verify export file exists and is non-empty
        if not export_path.exists() or export_path.stat().st_size == 0:
            logger.warning(
                "Export file %s missing or empty — skipping image cleanup for safety",
                export_path,
            )
            return 0

        deleted = 0
        for path in image_paths:
            try:
                if path.exists():
                    path.unlink()
                    deleted += 1
            except OSError as e:
                logger.warning("Failed to delete %s: %s", path, e)

        return deleted


# Export registry — maps format names to exporter instances
EXPORTERS: dict[str, BaseExporter] = {
    "cbz": CBZExporter(),
    "zip": ZIPExporter(),
    "pdf": PDFExporter(),
    "images": ImagesExporter(),
    "folder": FolderExporter(),
}


def get_exporter(format_name: str) -> BaseExporter:
    """Get exporter by format name."""
    exporter = EXPORTERS.get(format_name.lower())
    if exporter is None:
        raise ValueError(f"Unknown export format: {format_name}")
    return exporter


def record_export(
    manga_id: int,
    manga_title: str,
    chapter_range: str,
    export_format: str,
    chapters_downloaded: int = 0,
    total_pages: int = 0,
    output_path: str = "",
    status: str = "success",
    errors: list[str] | None = None,
) -> None:
    """Record a completed export to the download history.

    This is a convenience wrapper around LibraryManager.record_download().
    Call this after a successful export to keep history up to date.
    """
    try:
        from manga_dotnet.core.history import LibraryManager
        manager = LibraryManager()
        manager.record_download(
            manga_id=manga_id,
            manga_title=manga_title,
            chapter_range=chapter_range,
            export_format=export_format,
            chapters_downloaded=chapters_downloaded,
            total_pages=total_pages,
            output_path=output_path,
            status=status,
            errors=errors,
        )
    except Exception as e:
        logger.warning("Failed to record export to history: %s", e)
