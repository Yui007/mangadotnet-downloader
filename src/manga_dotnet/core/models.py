"""Pydantic v2 data models — the backbone of type safety throughout the app.

All models map directly to MangaDotNet API response structures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_list(value: Any) -> list[str]:
    """Parse a JSON-encoded string list like ``'[\"a\",\"b\"]'`` into a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
    return []


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------


class ScanlatorGroup(BaseModel):
    """A scanlation/translation group."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str


class MangaResult(BaseModel):
    """Lightweight search result — compact representation from search endpoint."""

    model_config = ConfigDict(frozen=True)

    id: int
    title: str
    photo: str = ""
    status: str = ""
    rating: float | None = None
    chapter_count: int = 0
    genres: list[str] = Field(default_factory=list)
    description: str = ""
    is_adult: bool = False

    @property
    def cover_url(self) -> str:
        """Full cover image URL."""
        if self.photo.startswith("http"):
            return self.photo
        return f"https://mangadot.net{self.photo}"


class MangaInfo(BaseModel):
    """Complete manga metadata — every field from the ``/api/manga/{id}/`` endpoint."""

    id: int
    title: str
    genres: list[str] = Field(default_factory=list)
    status: str = ""  # "Ongoing", "Completed", "Hiatus", etc.
    description: str = ""
    authors: list[str] = Field(default_factory=list)  # Parsed from JSON-encoded string
    artists: list[str] = Field(default_factory=list)  # Parsed from JSON-encoded string
    chapter_count: int = 0
    rating: float | None = None  # Aggregate percentage string ("81.7")
    avg_rating: float | None = None  # Average rating (0-10)
    rating_count: int = 0
    alt_titles: list[str] = Field(default_factory=list)
    is_adult: bool = False
    country_of_origin: str = ""  # "JP", "KR", "CN", etc.
    year: int | None = None
    photo: str = ""  # Cover/thumbnail image path
    banner_image: str | None = None  # Banner image path
    date_added: str = ""
    hiatus: str = "No"  # "No" or "Yes" (string, not bool!)
    source_url: str | None = None
    scanlation_group: str | None = None
    is_blurworthy: bool = False
    content_rating: str = "safe"  # "safe", "suggestive", "erotica", "pornographic"
    is_hot: bool = False
    is_popular: bool = False
    view_count: int = 0
    comment_count: int = 0
    tracked_count: int = 0
    last_chapter_date: str | None = None
    update_day: str | None = None
    review_count: int = 0
    # External tracking IDs
    mangaupdates_id: str | None = None
    anilist_id: int | None = None
    mangadex_id: str | None = None
    mal_id: int | None = None
    kitsu_id: int | None = None
    mangabaka_id: int | None = None
    # Computed from top-level wrapper
    total_chapters: int = 0
    first_chapter_id: int | None = None
    first_chapter_source: str | None = None
    status_text: str = ""
    date_added_formatted: str = ""

    @field_validator("authors", "artists", mode="before")
    @classmethod
    def _parse_json_string_list(cls, v: Any) -> list[str]:
        return _parse_json_list(v)

    @field_validator("rating", mode="before")
    @classmethod
    def _parse_rating(cls, v: Any) -> float | None:
        if isinstance(v, str):
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        return v

    @property
    def cover_url(self) -> str:
        """Full cover image URL."""
        if self.photo.startswith("http"):
            return self.photo
        return f"https://mangadot.net{self.photo}"

    @property
    def banner_url(self) -> str | None:
        """Full banner image URL."""
        if not self.banner_image:
            return None
        if self.banner_image.startswith("http"):
            return self.banner_image
        return f"https://mangadot.net{self.banner_image}"

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> MangaInfo:
        """Parse from the ``{ manga: {...}, total_chapters: N, ... }`` wrapper."""
        manga = data.get("manga", data)
        return cls(
            id=manga["id"],
            title=manga["title"],
            genres=manga.get("genres", []),
            status=manga.get("status", ""),
            description=manga.get("description", ""),
            authors=manga.get("authors", []),
            artists=manga.get("artists", []),
            chapter_count=manga.get("chapter_count", 0),
            rating=manga.get("rating"),
            avg_rating=manga.get("avg_rating"),
            rating_count=manga.get("rating_count", 0),
            alt_titles=manga.get("alt_titles", []),
            is_adult=manga.get("is_adult", False),
            country_of_origin=manga.get("country_of_origin", ""),
            year=manga.get("year"),
            photo=manga.get("photo", ""),
            banner_image=manga.get("banner_image"),
            date_added=manga.get("date_added", ""),
            hiatus=manga.get("hiatus", "No"),
            source_url=manga.get("source_url"),
            scanlation_group=manga.get("scanlation_group"),
            is_blurworthy=manga.get("is_blurworthy", False),
            content_rating=manga.get("content_rating", "safe"),
            is_hot=manga.get("is_hot", False),
            is_popular=manga.get("is_popular", False),
            view_count=manga.get("view_count", 0),
            comment_count=manga.get("comment_count", 0),
            tracked_count=manga.get("tracked_count", 0),
            last_chapter_date=manga.get("last_chapter_date"),
            update_day=manga.get("update_day"),
            review_count=manga.get("review_count", 0),
            mangaupdates_id=manga.get("mangaupdates_id"),
            anilist_id=manga.get("anilist_id"),
            mangadex_id=manga.get("mangadex_id"),
            mal_id=manga.get("mal_id"),
            kitsu_id=manga.get("kitsu_id"),
            mangabaka_id=manga.get("mangabaka_id"),
            total_chapters=data.get("total_chapters", 0),
            first_chapter_id=data.get("first_chapter_id"),
            first_chapter_source=data.get("first_chapter_source"),
            status_text=data.get("status_text", ""),
            date_added_formatted=data.get("date_added_formatted", ""),
        )


class Chapter(BaseModel):
    """A single chapter — includes language and group info for deduplication."""

    id: int
    chapter_number: float
    volume_number: float | None = None
    chapter_title: str | None = None
    language: str = "en"  # Language code: "en", "ko", "zh", etc.
    page_count: int = 0
    group_id: int = 0  # Scanlation group ID (0 = unknown/scraper)
    group_name: str | None = None  # Primary group name
    groups: list[ScanlatorGroup] = Field(default_factory=list)  # All groups involved
    scanlator_name: str | None = None  # Scanlator display name
    source: str = ""  # "scraper" or "user"
    uploader_id: str | None = None
    uploader_username: str | None = None
    uploader_upload_status: str | None = None
    date_added: str | None = None
    comment_count: int = 0

    @property
    def display_title(self) -> str:
        """Human-readable chapter title."""
        if self.chapter_title:
            return self.chapter_title
        return f"Chapter {self.chapter_number}"

    @property
    def group_display(self) -> str:
        """Display name for the scanlation group."""
        if self.scanlator_name:
            return self.scanlator_name
        if self.group_name:
            return self.group_name
        return "Unknown"

    @property
    def source_badge(self) -> str:
        """Badge for the upload source."""
        return "🔗" if self.source == "scraper" else "👤"

    @property
    def sort_key(self) -> tuple:
        """For sorting chapters by volume then number."""
        vol = self.volume_number or 999
        return (vol, self.chapter_number)


class Volume(BaseModel):
    """A single volume entry."""

    id: int
    volume_number: int
    page_count: int = 0
    cover_url: str = ""
    group_name: str | None = None
    uploader_username: str | None = None
    groups: list[dict[str, Any]] = Field(default_factory=list)


class PageImage(BaseModel):
    """A single page image metadata."""

    url: str
    width: int = 0
    height: int = 0
    filename: str = ""

    @property
    def full_url(self) -> str:
        """Construct full URL from relative path."""
        if self.url.startswith("http"):
            return self.url
        return f"https://mangadot.net{self.url}"

    @property
    def extension(self) -> str:
        """File extension from filename."""
        return Path(self.filename).suffix or ".jpg"


class ChapterImages(BaseModel):
    """Chapter metadata + its page images."""

    chapter: dict[str, Any]  # Raw chapter metadata
    manga: dict[str, Any]  # Basic manga info
    images: list[PageImage]
    prev_chapter_id: int | None = None
    next_chapter_id: int | None = None
    prev_volume_id: int | None = None
    next_volume_id: int | None = None
    type: str = "chapter"  # "chapter" or "volume"
    volume_number: int | None = None
    source: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ChapterImages:
        """Parse from the ``/api/uploads/{id}/images`` response."""
        images = [
            PageImage(
                url=img.get("url", ""),
                width=img.get("w", 0),
                height=img.get("h", 0),
                filename=img.get("filename", ""),
            )
            for img in data.get("images", [])
        ]
        return cls(
            chapter=data.get("chapter", {}),
            manga=data.get("manga", {}),
            images=images,
            prev_chapter_id=data.get("prev_chapter_id"),
            next_chapter_id=data.get("next_chapter_id"),
            prev_volume_id=data.get("prev_volume_id"),
            next_volume_id=data.get("next_volume_id"),
            type=data.get("type", "chapter"),
            volume_number=data.get("volume_number"),
            source=data.get("source", ""),
        )


# ---------------------------------------------------------------------------
# Download Tracking Models
# ---------------------------------------------------------------------------


class DownloadResult(BaseModel):
    """Result of a download operation."""

    manga_id: int
    manga_title: str
    chapters_downloaded: int = 0
    chapters_failed: int = 0
    total_pages: int = 0
    total_size_bytes: int = 0
    duration_seconds: float = 0.0
    export_format: str = "cbz"
    output_path: Path | None = None
    errors: list[str] = Field(default_factory=list)


class ChapterResult(BaseModel):
    """Result of a single chapter download."""

    chapter_id: int
    chapter_number: float
    success: bool
    pages_downloaded: int = 0
    pages_failed: int = 0
    size_bytes: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
    output_path: Path | None = None


class DownloadTask(BaseModel):
    """A pending download task."""

    manga_id: int
    manga_title: str = ""
    chapter_ids: list[int] = Field(default_factory=list)
    chapter_ranges: list[str] = Field(default_factory=list)  # ["1-50", "100"]
    export_format: str = "cbz"
    output_dir: Path | None = None
    priority: int = 0
