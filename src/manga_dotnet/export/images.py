"""Images export — save as loose image files."""

from __future__ import annotations

import asyncio
from pathlib import Path

from manga_dotnet.export.base import BaseExporter, detect_extension


class ImagesExporter(BaseExporter):
    """Export as loose image files in a folder."""

    async def export(
        self,
        images: list[bytes],
        output_dir: Path,
        filename: str,
        metadata: dict,
    ) -> Path:
        folder_path = output_dir / filename
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_images, images, folder_path)
        return folder_path

    def _write_images(self, images: list[bytes], folder_path: Path) -> None:
        folder_path.mkdir(parents=True, exist_ok=True)
        for idx, img_data in enumerate(images):
            ext = detect_extension(img_data)
            page_path = folder_path / f"{idx + 1:04d}{ext}"
            page_path.write_bytes(img_data)

    def get_extension(self) -> str:
        return ""  # No extension for folders
