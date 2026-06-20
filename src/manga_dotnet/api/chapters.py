"""Chapter listing API — fetch all chapters for a manga."""

from __future__ import annotations

import logging
from typing import Any

from manga_dotnet.api.client import MangaDotNetClient
from manga_dotnet.core.models import Chapter, ScanlatorGroup

logger = logging.getLogger(__name__)


class ChapterAPI:
    """Chapter listing endpoint wrapper."""

    def __init__(self, client: MangaDotNetClient):
        self.client = client

    def get_chapters(self, manga_id: int) -> list[Chapter]:
        """Get all chapters for a manga, parsed into Chapter models.

        Note: Returns ALL chapters including duplicates from multiple groups.
        Use ChapterFilter to deduplicate.
        """
        raw = self.client.get_chapters(manga_id)
        return [self._parse_chapter(ch) for ch in raw]

    def get_raw(self, manga_id: int) -> list[dict[str, Any]]:
        """Get raw API response for chapter listing."""
        return self.client.get_chapters(manga_id)

    @staticmethod
    def _parse_chapter(data: dict[str, Any]) -> Chapter:
        """Parse a raw chapter dict into a Chapter model."""
        groups = [
            ScanlatorGroup(id=g["id"], name=g["name"])
            for g in data.get("groups", [])
            if isinstance(g, dict) and "id" in g and "name" in g
        ]
        return Chapter(
            id=data["id"],
            chapter_number=float(data.get("chapter_number", 0)),
            volume_number=float(data["volume_number"]) if data.get("volume_number") is not None else None,
            chapter_title=data.get("chapter_title"),
            language=data.get("language", "en"),
            page_count=data.get("page_count", 0),
            group_id=data.get("group_id", 0),
            group_name=data.get("group_name"),
            groups=groups,
            scanlator_name=data.get("scanlator_name"),
            source=data.get("source", ""),
            uploader_id=data.get("uploader_id"),
            uploader_username=data.get("uploader_username"),
            uploader_upload_status=data.get("uploader_upload_status"),
            date_added=data.get("date_added"),
            comment_count=data.get("comment_count", 0),
        )
