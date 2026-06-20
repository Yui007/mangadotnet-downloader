"""Test configuration and shared fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_manga_info():
    """Sample MangaInfo dict as returned by the API."""
    return {
        "manga": {
            "id": 166,
            "title": "The Devil Butler",
            "photo": "/uploads/manga/the_devil_butler/cover.jpg",
            "status": "Ongoing",
            "rating": "81.7",
            "chapter_count": 875,
            "genres": ["Action", "Adventure", "Drama", "Fantasy"],
            "is_adult": False,
            "description": "As the Demon King...",
            "authors": '["Bao Ke Ai"]',
            "artists": '["Ye Xiao"]',
            "alt_titles": ["악마 집사"],
        },
        "total_chapters": 875,
    }


@pytest.fixture
def sample_chapter():
    """Sample Chapter data dict."""
    return {
        "id": 129806,
        "chapter_number": 0,
        "volume_number": None,
        "chapter_title": "Episode 0",
        "language": "en",
        "page_count": 83,
        "group_id": 100,
        "group_name": "ThunderScans",
        "groups": [{"id": 100, "name": "ThunderScans"}],
        "scanlator_name": "ThunderScans",
        "source": "user",
        "uploader_id": "123",
        "uploader_username": "testuser",
        "date_added": "2024-01-15",
        "comment_count": 5,
    }


@pytest.fixture
def sample_search_result():
    """Sample search result data dict."""
    return {
        "id": 166,
        "title": "The Devil Butler",
        "photo": "/uploads/manga/the_devil_butler/cover.jpg",
        "status": "Ongoing",
        "rating": "81.7",
        "chapter_count": 875,
        "genres": ["Action", "Adventure"],
        "is_adult": False,
    }
