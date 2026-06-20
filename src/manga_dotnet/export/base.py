"""Abstract base exporter for all export formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseExporter(ABC):
    """Abstract base for all export formats."""

    @abstractmethod
    async def export(
        self,
        images: list[bytes],
        output_dir: Path,
        filename: str,
        metadata: dict,
    ) -> Path:
        """Export images to the target format. Returns output path."""
        ...

    @abstractmethod
    def get_extension(self) -> str:
        """File extension for this format (e.g. '.cbz')."""
        ...


def detect_extension(data: bytes) -> str:
    """Detect image file extension from magic bytes."""
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"\x89PNG":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:4] == b"GIF8":
        return ".gif"
    return ".jpg"  # Default fallback
