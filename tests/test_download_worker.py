"""Unit tests for background _DownloadWorker class."""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QCoreApplication

from manga_dotnet.gui.main_window import _DownloadWorker
from manga_dotnet.core.models import ChapterImages, PageImage, DownloadResult

# Ensure QCoreApplication exists for QThread/Signals
app = QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock()
    config.output_dir = tmp_path
    config.download.max_retries = 1
    config.download.retry_delay = 0.01
    config.download.max_concurrent_chapters = 2
    return config


@pytest.fixture
def mock_chapter_images():
    images = [
        PageImage(url="/img1.jpg", width=100, height=100, filename="img1.jpg"),
        PageImage(url="/img2.jpg", width=100, height=100, filename="img2.jpg"),
    ]
    return ChapterImages(
        chapter={"id": 1, "chapter_number": 1.0},
        manga={"id": 166, "title": "Test Manga"},
        images=images,
    )


def test_download_worker_success(mock_config, mock_chapter_images, tmp_path):
    mock_client = MagicMock()

    with patch("manga_dotnet.core.config.Config.load") as mock_load, \
         patch("manga_dotnet.api.images.ImageAPI") as mock_image_api_cls, \
         patch("manga_dotnet.export.cleanup.get_exporter") as mock_get_exporter:

        mock_load.return_value = mock_config

        # Mock ImageAPI
        mock_image_api = MagicMock()
        mock_image_api.get_images.return_value = mock_chapter_images
        mock_image_api.download_image.return_value = b"fake_jpeg_data"
        mock_image_api_cls.return_value = mock_image_api

        # Mock exporter
        mock_exporter = MagicMock()

        async def mock_export(*args, **kwargs):
            return tmp_path / "Chapter_1.cbz"

        mock_exporter.export = mock_export
        mock_get_exporter.return_value = mock_exporter

        worker = _DownloadWorker(
            client=mock_client,
            chapter_ids=[1],
            export_format="cbz",
            delete_images=False,
            manga_title="Test Manga",
            chapter_numbers=[1.0],
        )

        # Listen for signals
        progress_calls = []
        finished_calls = []
        error_calls = []

        worker.progress.connect(lambda *args: progress_calls.append(args))
        worker.finished_ok.connect(lambda res: finished_calls.append(res))
        worker.error_occurred.connect(lambda err: error_calls.append(err))

        # Run worker synchronously for test simplicity by calling run directly
        worker.run()

        # Process Qt events to flush any queued signal connections across threads
        QCoreApplication.processEvents()

        assert not error_calls
        assert len(finished_calls) == 1
        assert isinstance(finished_calls[0], DownloadResult)
        assert finished_calls[0].chapters_downloaded == 1
        assert finished_calls[0].total_pages == 2
        assert len(progress_calls) >= 2


def test_download_worker_pause_resume(mock_config, mock_chapter_images, tmp_path):
    mock_client = MagicMock()

    with patch("manga_dotnet.core.config.Config.load") as mock_load, \
         patch("manga_dotnet.api.images.ImageAPI") as mock_image_api_cls, \
         patch("manga_dotnet.export.cleanup.get_exporter") as mock_get_exporter:

        mock_load.return_value = mock_config

        # Mock ImageAPI
        mock_image_api = MagicMock()
        mock_image_api.get_images.return_value = mock_chapter_images
        mock_image_api.download_image.return_value = b"fake_jpeg_data"
        mock_image_api_cls.return_value = mock_image_api

        # Mock exporter
        mock_exporter = MagicMock()

        async def mock_export(*args, **kwargs):
            return tmp_path / "Chapter_1.cbz"

        mock_exporter.export = mock_export
        mock_get_exporter.return_value = mock_exporter

        worker = _DownloadWorker(
            client=mock_client,
            chapter_ids=[1],
            export_format="cbz",
            delete_images=False,
            manga_title="Test Manga",
            chapter_numbers=[1.0],
        )

        # Start in separate thread to test concurrency controls
        worker.start()

        # Pause immediately
        is_paused = worker.toggle_pause()
        assert is_paused is True

        # Wait a short moment to let thread run and hit pause condition
        time.sleep(0.1)

        # Resume
        is_paused = worker.toggle_pause()
        assert is_paused is False

        # Wait for thread to finish
        worker.wait(5000)
        assert worker.isFinished()


def test_download_worker_cancel(mock_config, mock_chapter_images, tmp_path):
    mock_client = MagicMock()

    with patch("manga_dotnet.core.config.Config.load") as mock_load, \
         patch("manga_dotnet.api.images.ImageAPI") as mock_image_api_cls, \
         patch("manga_dotnet.export.cleanup.get_exporter") as mock_get_exporter:

        mock_load.return_value = mock_config

        # Mock ImageAPI with delay to give time to cancel
        mock_image_api = MagicMock()
        mock_image_api.get_images.return_value = mock_chapter_images

        def slow_download(*args, **kwargs):
            time.sleep(0.5)
            return b"fake"

        mock_image_api.download_image.side_effect = slow_download
        mock_image_api_cls.return_value = mock_image_api

        mock_exporter = MagicMock()
        mock_get_exporter.return_value = mock_exporter

        worker = _DownloadWorker(
            client=mock_client,
            chapter_ids=[1],
            export_format="cbz",
            delete_images=False,
            manga_title="Test Manga",
            chapter_numbers=[1.0],
        )

        worker.start()

        # Cancel immediately
        worker.cancel()

        # Wait for thread to exit
        worker.wait(5000)
        assert worker.isFinished()


def test_download_worker_keep_images(mock_config, mock_chapter_images, tmp_path):
    mock_client = MagicMock()

    with patch("manga_dotnet.core.config.Config.load") as mock_load, \
         patch("manga_dotnet.api.images.ImageAPI") as mock_image_api_cls, \
         patch("manga_dotnet.export.cleanup.get_exporter") as mock_get_exporter:

        mock_load.return_value = mock_config

        # Mock ImageAPI
        mock_image_api = MagicMock()
        mock_image_api.get_images.return_value = mock_chapter_images
        mock_image_api.download_image.return_value = b"fake_jpeg_data"
        mock_image_api_cls.return_value = mock_image_api

        # Mock exporter
        mock_exporter = MagicMock()
        async def mock_export(*args, **kwargs):
            return tmp_path / "Chapter_1.cbz"
        mock_exporter.export = mock_export
        mock_get_exporter.return_value = mock_exporter

        worker = _DownloadWorker(
            client=mock_client,
            chapter_ids=[1],
            export_format="cbz",
            delete_images=False,
            manga_title="Test Manga",
            chapter_numbers=[1.0],
        )

        worker.run()
        QCoreApplication.processEvents()

        # Check if loose images were written to output dir
        chapter_dir = tmp_path / "Test_Manga" / "Chapter_1"
        assert chapter_dir.exists()
        assert (chapter_dir / "0001.jpg").exists()
        assert (chapter_dir / "0002.jpg").exists()
        assert (chapter_dir / "0001.jpg").read_bytes() == b"fake_jpeg_data"
