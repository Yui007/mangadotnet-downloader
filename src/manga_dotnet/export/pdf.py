"""PDF export — PDF with bookmarks using img2pdf + PyMuPDF."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

from manga_dotnet.export.base import BaseExporter


class PDFExporter(BaseExporter):
    """Export as PDF with bookmarks."""

    async def export(
        self,
        images: list[bytes],
        output_dir: Path,
        filename: str,
        metadata: dict,
    ) -> Path:
        output_path = output_dir / f"{filename}.pdf"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._write_pdf, images, output_path, metadata
        )
        return output_path

    def _write_pdf(
        self, images: list[bytes], output_path: Path, metadata: dict
    ) -> None:
        import img2pdf
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ImportError(
                "PyMuPDF (fitz) is not installed. Please install it with: pip install PyMuPDF"
            ) from e

        # Convert all images to JPEG for PDF compatibility
        jpeg_images = [self._ensure_jpeg(img) for img in images]

        # Create PDF
        pdf_bytes = img2pdf.convert(jpeg_images)

        # Write initial PDF
        temp_path = output_path.with_suffix(".tmp.pdf")
        temp_path.write_bytes(pdf_bytes)

        # Add bookmarks with PyMuPDF
        doc = fitz.open(temp_path)
        title = metadata.get("chapter_title", "")
        if not title:
            ch_num = metadata.get("chapter_number", "")
            title = f"Chapter {ch_num}" if ch_num else "Chapter"
        toc = [[1, title, 1]]
        doc.set_toc(toc)
        doc.save(output_path)
        doc.close()
        temp_path.unlink(missing_ok=True)

    @staticmethod
    def _ensure_jpeg(img_data: bytes) -> bytes:
        """Convert image to JPEG if needed."""
        if img_data[:3] == b"\xff\xd8\xff":  # Already JPEG
            return img_data

        from PIL import Image

        img = Image.open(io.BytesIO(img_data))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    def get_extension(self) -> str:
        return ".pdf"
