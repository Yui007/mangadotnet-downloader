"""Tests for library management and update checker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from manga_dotnet.core.history import (
    HistoryEntry,
    LibraryManager,
    LibraryStats,
    MangaEntry,
)
from manga_dotnet.core.updates import ChapterUpdate, UpdateChecker


class TestMangaEntry:
    def test_from_dict(self):
        data = {
            "manga_id": 166,
            "title": "The Devil Butler",
            "path": "/manga/the_devil_butler",
            "chapter_count": 50,
            "total_size_bytes": 1024000,
            "last_downloaded": "2024-01-15T10:30:00",
            "status": "ongoing",
        }
        entry = MangaEntry.from_dict(data)
        assert entry.manga_id == 166
        assert entry.title == "The Devil Butler"
        assert entry.chapter_count == 50

    def test_to_dict_roundtrip(self):
        entry = MangaEntry(manga_id=1, title="Test", path="/test")
        d = entry.to_dict()
        restored = MangaEntry.from_dict(d)
        assert restored.manga_id == 1
        assert restored.title == "Test"


class TestHistoryEntry:
    def test_from_dict(self):
        data = {
            "manga_id": 166,
            "manga_title": "The Devil Butler",
            "chapter_range": "1-10",
            "export_format": "cbz",
            "timestamp": "2024-01-15T10:30:00",
            "chapters_downloaded": 10,
            "total_pages": 500,
            "output_path": "/manga/the_devil_butler",
            "status": "success",
            "errors": [],
        }
        entry = HistoryEntry.from_dict(data)
        assert entry.manga_id == 166
        assert entry.chapters_downloaded == 10
        assert entry.status == "success"

    def test_to_dict_roundtrip(self):
        entry = HistoryEntry(
            manga_id=1, manga_title="Test", chapter_range="1-5",
            export_format="pdf", timestamp="2024-01-01T00:00:00",
        )
        d = entry.to_dict()
        restored = HistoryEntry.from_dict(d)
        assert restored.manga_title == "Test"
        assert restored.export_format == "pdf"


class TestLibraryManager:
    def test_init_creates_no_file(self, tmp_path):
        manager = LibraryManager(data_dir=tmp_path)
        assert manager._history_path.exists() is False

    def test_record_and_retrieve(self, tmp_path):
        manager = LibraryManager(data_dir=tmp_path)
        entry = manager.record_download(
            manga_id=166,
            manga_title="The Devil Butler",
            chapter_range="1-10",
            export_format="cbz",
            chapters_downloaded=10,
            total_pages=500,
        )
        assert entry.manga_id == 166

        history = manager.get_history()
        assert len(history) == 1
        assert history[0].manga_title == "The Devil Butler"

    def test_history_persists(self, tmp_path):
        # Write
        manager1 = LibraryManager(data_dir=tmp_path)
        manager1.record_download(
            manga_id=1, manga_title="Test", chapter_range="1",
            export_format="cbz",
        )

        # Read from new instance
        manager2 = LibraryManager(data_dir=tmp_path)
        history = manager2.get_history()
        assert len(history) == 1

    def test_clear_history(self, tmp_path):
        manager = LibraryManager(data_dir=tmp_path)
        manager.record_download(
            manga_id=1, manga_title="Test", chapter_range="1",
            export_format="cbz",
        )
        manager.clear_history()
        assert len(manager.get_history()) == 0

    def test_history_order_most_recent_first(self, tmp_path):
        manager = LibraryManager(data_dir=tmp_path)
        manager.record_download(manga_id=1, manga_title="First", chapter_range="1", export_format="cbz")
        manager.record_download(manga_id=2, manga_title="Second", chapter_range="2", export_format="pdf")

        history = manager.get_history()
        assert history[0].manga_title == "Second"
        assert history[1].manga_title == "First"

    def test_scan_empty_directory(self, tmp_path):
        manager = LibraryManager(data_dir=tmp_path)
        entries = manager.scan_directory(tmp_path)
        assert entries == []

    def test_scan_with_manga_dirs(self, tmp_path):
        # Create fake manga directories
        manga_dir = tmp_path / "The Devil Butler"
        manga_dir.mkdir()
        for i in range(3):
            (manga_dir / f"page_{i:03d}.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 10)

        manager = LibraryManager(data_dir=tmp_path)
        entries = manager.scan_directory(tmp_path)
        assert len(entries) == 1
        assert entries[0].title == "The Devil Butler"
        assert entries[0].chapter_count == 3

    def test_get_stats(self, tmp_path):
        manager = LibraryManager(data_dir=tmp_path)
        stats = manager.get_stats(tmp_path)
        assert stats.total_manga == 0
        assert stats.total_size_display == "0.0 B"


class TestLibraryStats:
    def test_total_size_display(self):
        stats = LibraryStats(total_size_bytes=1536)
        assert stats.total_size_display == "1.5 KB"

    def test_total_size_display_gb(self):
        stats = LibraryStats(total_size_bytes=1073741824)
        assert stats.total_size_display == "1.0 GB"


class TestChapterUpdate:
    def test_empty(self):
        update = ChapterUpdate(manga_id=1, manga_title="Test")
        assert update.count == 0
        assert update.chapter_range == ""

    def test_single_chapter(self):
        from manga_dotnet.core.models import Chapter

        ch = Chapter(id=1, chapter_number=5)
        update = ChapterUpdate(manga_id=1, manga_title="Test", new_chapters=[ch])
        assert update.count == 1
        assert update.chapter_range == "5"

    def test_range(self):
        from manga_dotnet.core.models import Chapter

        chapters = [
            Chapter(id=1, chapter_number=1),
            Chapter(id=2, chapter_number=5),
            Chapter(id=3, chapter_number=10),
        ]
        update = ChapterUpdate(manga_id=1, manga_title="Test", new_chapters=chapters)
        assert update.count == 3
        assert update.chapter_range == "1-10"
