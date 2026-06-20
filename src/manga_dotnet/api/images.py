"""Image URL API — fetch page images for a chapter or volume."""

from __future__ import annotations

import logging
from typing import Any

from manga_dotnet.api.client import MangaDotNetClient
from manga_dotnet.core.models import ChapterImages

logger = logging.getLogger(__name__)


class ImageAPI:
    """Chapter/volume image endpoint wrapper."""

    def __init__(self, client: MangaDotNetClient):
        self.client = client

    def get_images(self, chapter_id: int) -> ChapterImages:
        """Get page images for a chapter or volume."""
        data = self.client.get_images(chapter_id)
        return ChapterImages.from_api(data)

    def get_raw(self, chapter_id: int) -> dict[str, Any]:
        """Get raw API response for chapter images."""
        return self.client.get_images(chapter_id)

    def download_image(self, url: str) -> bytes:
        """Download raw image bytes."""
        return self.client.get_image_bytes(url)
