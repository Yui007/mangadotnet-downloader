"""Folder export — plain folder with images + metadata."""

from __future__ import annotations

import asyncio
from pathlib import Path

from manga_dotnet.export.base import BaseExporter, detect_extension


class FolderExporter(BaseExporter):
    """Export as plain folder with images and metadata file."""

    async def export(
        self,
        images: list[bytes],
        output_dir: Path,
        filename: str,
        metadata: dict,
    ) -> Path:
        folder_path = output_dir / filename
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._write_folder, images, folder_path, metadata
        )
        return folder_path

    def _write_folder(
        self, images: list[bytes], folder_path: Path, metadata: dict
    ) -> None:
        folder_path.mkdir(parents=True, exist_ok=True)

        # Write images
        for idx, img_data in enumerate(images):
            ext = detect_extension(img_data)
            page_path = folder_path / f"{idx + 1:04d}{ext}"
            page_path.write_bytes(img_data)

        # Write metadata
        meta_path = folder_path / "info.txt"
        lines = [
            f"Manga: {metadata.get('manga_title', 'Unknown')}",
            f"Chapter: {metadata.get('chapter_number', '')}",
        ]
        if metadata.get("chapter_title"):
            lines.append(f"Title: {metadata['chapter_title']}")
        lines.append(f"Pages: {len(images)}")
        meta_path.write_text("\n".join(lines), encoding="utf-8")

    def get_extension(self) -> str:
        return ""  # No extension for folders
