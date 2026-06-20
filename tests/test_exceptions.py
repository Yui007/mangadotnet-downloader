"""Tests for exceptions and error handling."""

from __future__ import annotations

import pytest

from manga_dotnet.core.exceptions import (
    APIError,
    ConfigError,
    ConnectionError,
    DiskSpaceError,
    DownloadError,
    ExportError,
    ImageDownloadError,
    InvalidMangaIdError,
    MangaDotNetError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test exception inheritance."""

    def test_all_inherit_from_base(self):
        exceptions = [
            APIError("test"),
            RateLimitError(),
            NotFoundError("test"),
            ServerError("test", status_code=500),
            ConnectionError("test"),
            DownloadError("test"),
            ImageDownloadError("http://test.com/img.jpg", "timeout"),
            ExportError("test"),
            DiskSpaceError("test"),
            ConfigError("test"),
            InvalidMangaIdError("test"),
            ValidationError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, MangaDotNetError)
            assert isinstance(exc, Exception)

    def test_api_errors_have_status_code(self):
        exc = APIError("test", status_code=404, url="http://test.com")
        assert exc.status_code == 404
        assert exc.url == "http://test.com"

    def test_rate_limit_has_retry_after(self):
        exc = RateLimitError(retry_after=30.0)
        assert exc.retry_after == 30.0

    def test_image_error_has_url(self):
        exc = ImageDownloadError("http://img.com/1.jpg", "not found")
        assert exc.url == "http://img.com/1.jpg"
        assert "not found" in str(exc)

    def test_suggestion(self):
        exc = MangaDotNetError("error", suggestion="try again")
        assert exc.suggestion == "try again"

    def test_no_suggestion(self):
        exc = MangaDotNetError("error")
        assert exc.suggestion is None


class TestCLIErrorHandler:
    """Test the CLI error handler produces output without crashing."""

    def test_handle_rate_limit(self):
        from io import StringIO
        from rich.console import Console

        from manga_dotnet.cli.error_handler import handle_error

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        handle_error(console, RateLimitError(retry_after=10.0))
        text = output.getvalue()
        assert "Rate Limited" in text or "rate" in text.lower()

    def test_handle_not_found(self):
        from io import StringIO
        from rich.console import Console

        from manga_dotnet.cli.error_handler import handle_error

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        handle_error(console, NotFoundError("not found"))
        text = output.getvalue()
        assert "Not Found" in text or "not found" in text.lower()

    def test_handle_generic_error(self):
        from io import StringIO
        from rich.console import Console

        from manga_dotnet.cli.error_handler import handle_error

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        handle_error(console, ValueError("bad value"))
        text = output.getvalue()
        assert "ValueError" in text or "bad value" in text
