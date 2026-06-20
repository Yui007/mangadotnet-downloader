"""Custom exception hierarchy for MangaDotNet Downloader."""

from __future__ import annotations


class MangaDotNetError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message)
        self.suggestion = suggestion


# ---------------------------------------------------------------------------
# API errors
# ---------------------------------------------------------------------------


class APIError(MangaDotNetError):
    """API request failed."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        url: str | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(message, suggestion=suggestion)
        self.status_code = status_code
        self.url = url


class RateLimitError(APIError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self, retry_after: float | None = None):
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


class NotFoundError(APIError):
    """Resource not found (HTTP 404)."""


class ServerError(APIError):
    """Server error (HTTP 5xx)."""


class ConnectionError(MangaDotNetError):
    """Network connection failed / Cloudflare bypass failed."""


# ---------------------------------------------------------------------------
# Download errors
# ---------------------------------------------------------------------------


class DownloadError(MangaDotNetError):
    """Download operation failed."""


class ImageDownloadError(DownloadError):
    """Failed to download a single image."""

    def __init__(self, url: str, reason: str):
        super().__init__(f"Failed to download image: {url} — {reason}")
        self.url = url


class ExportError(DownloadError):
    """Failed to create export file."""


class DiskSpaceError(DownloadError):
    """Insufficient disk space."""


# ---------------------------------------------------------------------------
# Config / validation errors
# ---------------------------------------------------------------------------


class ConfigError(MangaDotNetError):
    """Configuration error."""


class InvalidMangaIdError(MangaDotNetError):
    """Manga ID does not exist."""


class ValidationError(MangaDotNetError):
    """Input validation failed."""
