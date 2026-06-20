"""ZIP export — standard ZIP archive."""

from __future__ import annotations

import asyncio
import zipfile
from pathlib import Path

from manga_dotnet.export.base import BaseExporter, detect_extension


class ZIPExporter(BaseExporter):
    """Export as standard ZIP archive (.zip)."""

    async def export(
        self,
        images: list[bytes],
        output_dir: Path,
        filename: str,
        metadata: dict,
    ) -> Path:
        output_path = output_dir / f"{filename}.zip"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_zip, images, output_path)
        return output_path

    def _write_zip(self, images: list[bytes], output_path: Path) -> None:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img_data in enumerate(images):
                ext = detect_extension(img_data)
                page_name = f"{idx + 1:04d}{ext}"
                zf.writestr(page_name, img_data)

    def get_extension(self) -> str:
        return ".zip"
