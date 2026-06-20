"""Volume API — fetch volume listing for a manga."""

from __future__ import annotations

import logging
from typing import Any

from manga_dotnet.api.client import MangaDotNetClient
from manga_dotnet.core.models import Volume

logger = logging.getLogger(__name__)


class VolumeAPI:
    """Volume listing functionality."""

    def __init__(self, client: MangaDotNetClient):
        self.client = client

    def get_volumes(self, manga_id: int) -> list[Volume]:
        """Get all volumes for a manga."""
        raw = self.client.get_volumes(manga_id)
        return self._parse_volumes(raw)

    def _parse_volumes(self, data: Any) -> list[Volume]:
        """Parse volume API response into Volume models."""
        if not isinstance(data, list):
            logger.warning("Unexpected volume response type: %s", type(data))
            return []

        volumes: list[Volume] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                vol = Volume(
                    id=item["id"],
                    volume_number=item["volume_number"],
                    page_count=item.get("page_count", 0),
                    cover_url=item.get("cover_url", ""),
                    group_name=item.get("group_name", ""),
                )
                volumes.append(vol)
            except (KeyError, TypeError) as e:
                logger.warning("Failed to parse volume: %s", e)

        return sorted(volumes, key=lambda v: v.volume_number)
