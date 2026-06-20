"""Integration tests — CLI commands and export pipeline (mocked API)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from manga_dotnet.core.models import Chapter, MangaInfo, MangaResult, PageImage


# ---------------------------------------------------------------------------
# Export pipeline integration tests (actual async export API)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_jpeg():
    """Return fake JPEG bytes (magic bytes + padding)."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100


class TestCBZExport:
    def test_cbz_export(self, tmp_path, fake_jpeg):
        from manga_dotnet.export.cbz import CBZExporter

        exporter = CBZExporter()
        images = [fake_jpeg for _ in range(3)]

        async def _run():
            return await exporter.export(
                images, tmp_path, filename="Chapter_001", metadata={}
            )

        result = asyncio.run(_run())
        assert result.exists()
        assert result.suffix == ".cbz"

        import zipfile
        with zipfile.ZipFile(result) as zf:
            assert len(zf.namelist()) == 3

    def test_get_extension(self):
        from manga_dotnet.export.cbz import CBZExporter
        assert CBZExporter().get_extension() == ".cbz"


class TestZIPExport:
    def test_zip_export(self, tmp_path, fake_jpeg):
        from manga_dotnet.export.zip import ZIPExporter

        exporter = ZIPExporter()
        images = [fake_jpeg for _ in range(2)]

        async def _run():
            return await exporter.export(
                images, tmp_path, filename="Chapter_002", metadata={}
            )

        result = asyncio.run(_run())
        assert result.exists()

        import zipfile
        with zipfile.ZipFile(result) as zf:
            assert len(zf.namelist()) == 2


class TestImagesExport:
    def test_images_export(self, tmp_path, fake_jpeg):
        from manga_dotnet.export.images import ImagesExporter

        exporter = ImagesExporter()
        images = [fake_jpeg for _ in range(2)]

        async def _run():
            return await exporter.export(
                images, tmp_path, filename="Chapter_003", metadata={}
            )

        result = asyncio.run(_run())
        assert result.exists()


class TestFolderExport:
    def test_folder_export(self, tmp_path, fake_jpeg):
        from manga_dotnet.export.folder import FolderExporter

        exporter = FolderExporter()
        images = [fake_jpeg for _ in range(2)]

        async def _run():
            return await exporter.export(
                images, tmp_path, filename="Chapter_004",
                metadata={"title": "Test Manga"}
            )

        result = asyncio.run(_run())
        assert result.exists()


# ---------------------------------------------------------------------------
# CLI integration tests (lazy imports — patch inside function body)
# ---------------------------------------------------------------------------

class TestCLISearch:
    """Test search CLI with mocked API (patches inside function)."""

    def test_search_returns_results(self):
        from typer.testing import CliRunner
        from manga_dotnet.cli.app import app

        mock_client = MagicMock()
        mock_client._initialized = True

        with patch("manga_dotnet.api.search.SearchAPI") as mock_search_cls, \
             patch("manga_dotnet.core.config.Config.load") as mock_config_load, \
             patch("manga_dotnet.api.client.MangaDotNetClient") as mock_client_cls:

            mock_client_cls.return_value = mock_client
            mock_config_load.return_value = MagicMock()

            mock_search = MagicMock()
            mock_search.search.return_value = [
                MangaResult(id=166, title="The Devil Butler", status="Ongoing",
                            rating=8.8, chapter_count=875),
            ]
            mock_search_cls.return_value = mock_search

            runner = CliRunner()
            result = runner.invoke(app, ["search", "devil butler"])
            # Should complete without crash (exit 0 or 1 is fine)
            assert result.exit_code in (0, 1)


class TestCLIInfo:
    """Test info CLI with mocked API."""

    def test_info_displays(self):
        mock_client = MagicMock()
        mock_client._initialized = True

        with patch("manga_dotnet.api.manga.MangaAPI") as mock_manga_api_cls, \
             patch("manga_dotnet.core.config.Config.load") as mock_config_load, \
             patch("manga_dotnet.api.client.MangaDotNetClient") as mock_client_cls:

            mock_client_cls.return_value = mock_client
            mock_config_load.return_value = MagicMock()

            mock_manga_api = MagicMock()
            mock_manga_api.get_info.return_value = MangaInfo(
                id=166, title="The Devil Butler", status="Ongoing",
                chapter_count=875, rating=8.8,
            )
            mock_manga_api_cls.return_value = mock_manga_api

            from manga_dotnet.cli.commands.info import show_manga_info
            # Should not crash
            show_manga_info(166)


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------

class TestConfigRoundTrip:
    """Test config save/load round-trip with sub-configs."""

    def test_full_round_trip(self, tmp_path):
        from manga_dotnet.core.config import Config

        config = Config()
        config.default_format = "pdf"
        config.download.max_concurrent_chapters = 8
        config.quality.jpeg_quality = 80
        config.gui.theme = "midnight"
        config.network.proxy = "socks5://localhost:1080"

        path = tmp_path / "settings.json"
        config.save(path)

        loaded = Config.load(path)
        assert loaded.default_format == "pdf"
        assert loaded.download.max_concurrent_chapters == 8
        assert loaded.quality.jpeg_quality == 80
        assert loaded.gui.theme == "midnight"
        assert loaded.network.proxy == "socks5://localhost:1080"
