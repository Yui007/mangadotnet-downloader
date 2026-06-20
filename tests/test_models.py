"""Tests for core data models."""

from __future__ import annotations

import pytest

from manga_dotnet.core.models import (
    Chapter,
    MangaInfo,
    MangaResult,
    PageImage,
    ScanlatorGroup,
)


class TestMangaResult:
    """Tests for the MangaResult model."""

    def test_from_dict(self):
        data = {
            "id": 166,
            "title": "The Devil Butler",
            "photo": "/uploads/manga/devil_butler/cover.jpg",
            "status": "Ongoing",
            "rating": 8.8,
            "chapter_count": 875,
            "genres": ["Action", "Fantasy"],
            "is_adult": False,
        }
        result = MangaResult(**data)
        assert result.id == 166
        assert result.title == "The Devil Butler"
        assert result.status == "Ongoing"
        assert result.chapter_count == 875

    def test_cover_url_relative(self):
        result = MangaResult(
            id=1, title="Test", photo="/uploads/cover.jpg"
        )
        assert result.cover_url == "https://mangadot.net/uploads/cover.jpg"

    def test_cover_url_absolute(self):
        result = MangaResult(
            id=1, title="Test", photo="https://example.com/cover.jpg"
        )
        assert result.cover_url == "https://example.com/cover.jpg"

    def test_defaults(self):
        result = MangaResult(id=1, title="Test")
        assert result.photo == ""
        assert result.status == ""
        assert result.rating is None
        assert result.chapter_count == 0
        assert result.genres == []
        assert result.is_adult is False

    def test_frozen(self):
        result = MangaResult(id=1, title="Test")
        with pytest.raises(Exception):
            result.title = "Changed"  # type: ignore


class TestMangaInfo:
    """Tests for the MangaInfo model."""

    def test_from_api(self, sample_manga_info):
        info = MangaInfo.from_api(sample_manga_info)
        assert info.id == 166
        assert info.title == "The Devil Butler"
        assert info.chapter_count == 875
        assert info.status == "Ongoing"
        assert "Action" in info.genres

    def test_authors_parsed_from_json_string(self, sample_manga_info):
        info = MangaInfo.from_api(sample_manga_info)
        assert info.authors == ["Bao Ke Ai"]

    def test_artists_parsed_from_json_string(self, sample_manga_info):
        info = MangaInfo.from_api(sample_manga_info)
        assert info.artists == ["Ye Xiao"]

    def test_rating_converted_to_float(self, sample_manga_info):
        info = MangaInfo.from_api(sample_manga_info)
        assert isinstance(info.rating, float)
        assert info.rating == pytest.approx(81.7, abs=0.1)

    def test_empty_description(self):
        data = {
            "manga": {"id": 1, "title": "Test"},
            "total_chapters": 0,
        }
        info = MangaInfo.from_api(data)
        assert info.description == ""


class TestChapter:
    """Tests for the Chapter model."""

    def test_display_title(self):
        ch = Chapter(
            id=1, chapter_number=5, chapter_title="The Beginning"
        )
        assert ch.display_title == "The Beginning"

    def test_display_title_fallback(self):
        ch = Chapter(id=1, chapter_number=5)
        assert ch.display_title == "Chapter 5.0"

    def test_group_display_scanlator(self):
        ch = Chapter(
            id=1, chapter_number=1, scanlator_name="ThunderScans"
        )
        assert ch.group_display == "ThunderScans"

    def test_group_display_group_name(self):
        ch = Chapter(
            id=1, chapter_number=1, group_name="ThunderScans"
        )
        assert ch.group_display == "ThunderScans"

    def test_group_display_unknown(self):
        ch = Chapter(id=1, chapter_number=1)
        assert ch.group_display == "Unknown"

    def test_source_badge(self):
        ch_scraper = Chapter(id=1, chapter_number=1, source="scraper")
        assert ch_scraper.source_badge == "🔗"

        ch_user = Chapter(id=1, chapter_number=1, source="user")
        assert ch_user.source_badge == "👤"

    def test_sort_key(self):
        ch = Chapter(id=1, chapter_number=5, volume_number=2)
        assert ch.sort_key == (2, 5.0)

    def test_sort_key_no_volume(self):
        ch = Chapter(id=1, chapter_number=5)
        assert ch.sort_key == (999, 5.0)

    def test_from_dict(self, sample_chapter):
        ch = Chapter(**sample_chapter)
        assert ch.id == 129806
        assert ch.chapter_number == 0
        assert ch.page_count == 83
        assert ch.group_name == "ThunderScans"


class TestPageImage:
    """Tests for the PageImage model."""

    def test_full_url_relative(self):
        img = PageImage(
            filename="001.jpg",
            url="/uploads/chapter/1/001.jpg",
        )
        assert img.full_url == "https://mangadot.net/uploads/chapter/1/001.jpg"

    def test_full_url_absolute(self):
        img = PageImage(
            filename="001.jpg",
            url="https://cdn.example.com/001.jpg",
        )
        assert img.full_url == "https://cdn.example.com/001.jpg"

    def test_extension(self):
        img = PageImage(filename="page.png", url="/test")
        assert img.extension == ".png"
