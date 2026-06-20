"""Tests for ChapterFilter — deduplication and filtering."""

from __future__ import annotations

import pytest

from manga_dotnet.core.engine import ChapterFilter
from manga_dotnet.core.models import Chapter


@pytest.fixture
def chapter_filter():
    return ChapterFilter()


@pytest.fixture
def sample_chapters():
    """Chapters with duplicates from multiple groups."""
    return [
        # Chapter 0 — 3 versions
        Chapter(id=1, chapter_number=0, title="Ep 0", page_count=83, group_id=100, group_name="ThunderScans", source="user", language="en"),
        Chapter(id=2, chapter_number=0, title="Ep 0", page_count=89, group_id=200, group_name="Qi Manhwa", source="user", language="en"),
        Chapter(id=3, chapter_number=0, title="Ep 0", page_count=31, group_id=0, group_name=None, source="scraper", language="en"),
        # Chapter 1 — 2 versions
        Chapter(id=4, chapter_number=1, title="Ch 1", page_count=216, group_id=100, group_name="ThunderScans", source="user", language="en"),
        Chapter(id=5, chapter_number=1, title="Ch 1", page_count=200, group_id=200, group_name="Qi Manhwa", source="user", language="en"),
        # Chapter 2 — 1 version
        Chapter(id=6, chapter_number=2, title="Ch 2", page_count=50, group_id=100, group_name="ThunderScans", source="user", language="en"),
        # Korean chapter
        Chapter(id=7, chapter_number=3, title="Ch 3", page_count=45, group_id=300, group_name="Korean Group", source="user", language="ko"),
    ]


class TestDeduplication:
    """Test chapter deduplication."""

    def test_dedup_removes_duplicates(self, chapter_filter, sample_chapters):
        result = chapter_filter.filter_and_deduplicate(sample_chapters)
        chapter_numbers = [c.chapter_number for c in result]
        # Each chapter_number should appear only once
        assert len(chapter_numbers) == len(set(chapter_numbers))

    def test_dedup_keeps_best_version(self, chapter_filter, sample_chapters):
        result = chapter_filter.filter_and_deduplicate(sample_chapters)
        ch0 = next(c for c in result if c.chapter_number == 0)
        # Should pick the one with most pages (Qi Manhwa, 89 pages)
        assert ch0.page_count == 89
        assert ch0.group_name == "Qi Manhwa"

    def test_dedup_sorted_by_chapter(self, chapter_filter, sample_chapters):
        result = chapter_filter.filter_and_deduplicate(sample_chapters)
        numbers = [c.chapter_number for c in result]
        assert numbers == sorted(numbers)


class TestLanguageFilter:
    """Test language filtering."""

    def test_filter_by_language(self, chapter_filter, sample_chapters):
        result = chapter_filter.filter_and_deduplicate(
            sample_chapters, language="en"
        )
        for ch in result:
            assert ch.language == "en"

    def test_filter_korean(self, chapter_filter, sample_chapters):
        result = chapter_filter.filter_and_deduplicate(
            sample_chapters, language="ko"
        )
        assert len(result) == 1
        assert result[0].language == "ko"


class TestGroupFilter:
    """Test group filtering."""

    def test_filter_by_group_id(self, chapter_filter, sample_chapters):
        result = chapter_filter.filter_and_deduplicate(
            sample_chapters, group_id=100
        )
        for ch in result:
            assert ch.group_id == 100

    def test_filter_by_group_name(self, chapter_filter, sample_chapters):
        result = chapter_filter.filter_and_deduplicate(
            sample_chapters, group_name="Thunder"
        )
        assert len(result) > 0
        for ch in result:
            assert ch.group_name and "Thunder" in ch.group_name


class TestAvailableGroups:
    """Test group listing."""

    def test_get_groups(self, chapter_filter, sample_chapters):
        groups = chapter_filter.get_available_groups(sample_chapters)
        names = [g["name"] for g in groups]
        assert "ThunderScans" in names
        assert "Qi Manhwa" in names

    def test_group_chapter_counts(self, chapter_filter, sample_chapters):
        groups = chapter_filter.get_available_groups(sample_chapters)
        thunder = next(g for g in groups if g["name"] == "ThunderScans")
        assert thunder["chapter_count"] >= 2  # chapters 1, 2 + deduped ch0


class TestAvailableLanguages:
    """Test language listing."""

    def test_get_languages(self, chapter_filter, sample_chapters):
        langs = chapter_filter.get_available_languages(sample_chapters)
        codes = [l["code"] for l in langs]
        assert "en" in codes
        assert "ko" in codes

    def test_language_counts(self, chapter_filter, sample_chapters):
        langs = chapter_filter.get_available_languages(sample_chapters)
        en = next(l for l in langs if l["code"] == "en")
        assert en["count"] >= 3  # chapters 0, 1, 2 (deduplicated)


class TestEmptyInput:
    """Test edge cases with empty input."""

    def test_empty_list(self, chapter_filter):
        result = chapter_filter.filter_and_deduplicate([])
        assert result == []

    def test_single_chapter(self, chapter_filter):
        chapters = [Chapter(id=1, chapter_number=1, page_count=50)]
        result = chapter_filter.filter_and_deduplicate(chapters)
        assert len(result) == 1
