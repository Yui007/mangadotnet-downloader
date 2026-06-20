"""Image utilities — WebP conversion, image info extraction."""

from __future__ import annotations

import io

from PIL import Image


async def convert_webp_to_jpg(webp_data: bytes, quality: int = 95) -> bytes:
    """Convert WebP image to JPEG for better compatibility."""
    img = Image.open(io.BytesIO(webp_data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def get_image_info(data: bytes) -> tuple[int, int, str]:
    """Get (width, height, format) from image bytes."""
    img = Image.open(io.BytesIO(data))
    return img.width, img.height, img.format or "UNKNOWN"


def is_webp(data: bytes) -> bool:
    """Check if image data is WebP format."""
    return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
