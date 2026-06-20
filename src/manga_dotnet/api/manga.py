"""Manga info API — fetch full manga metadata."""

from __future__ import annotations

import logging
from typing import Any

from manga_dotnet.api.client import MangaDotNetClient
from manga_dotnet.core.models import MangaInfo

logger = logging.getLogger(__name__)


class MangaAPI:
    """Manga info endpoint wrapper."""

    def __init__(self, client: MangaDotNetClient):
        self.client = client

    def get_info(self, manga_id: int) -> MangaInfo:
        """Get full manga info and return as MangaInfo model."""
        data = self.client.get_manga(manga_id)
        return MangaInfo.from_api(data)

    def get_raw(self, manga_id: int) -> dict[str, Any]:
        """Get raw API response for manga info."""
        return self.client.get_manga(manga_id)
