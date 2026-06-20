"""ChapterFilter — deduplicate and filter chapters by language, group, preferences."""

from __future__ import annotations

import logging
from typing import Any

from manga_dotnet.core.models import Chapter

logger = logging.getLogger(__name__)


class ChapterFilter:
    """Filter and deduplicate chapters by language, group, and preferences.

    Since the same chapter_number can appear from multiple scanlator groups,
    this class picks the best version using a priority system:
    user-uploaded > grouped > more pages > more recent.
    """

    def filter_and_deduplicate(
        self,
        chapters: list[Chapter],
        language: str | None = None,
        group_id: int | None = None,
        group_name: str | None = None,
        prefer_user_uploaded: bool = True,
    ) -> list[Chapter]:
        """Filter chapters and keep best version of each chapter number."""
        # Step 1: Filter by language
        if language:
            chapters = [c for c in chapters if c.language == language]

        # Step 2: Filter by group
        if group_id:
            chapters = [c for c in chapters if c.group_id == group_id]
        elif group_name:
            chapters = [
                c for c in chapters
                if c.group_name and group_name.lower() in c.group_name.lower()
            ]

        # Step 3: Deduplicate by chapter_number
        by_number: dict[float, list[Chapter]] = {}
        for ch in chapters:
            by_number.setdefault(ch.chapter_number, []).append(ch)

        result: list[Chapter] = []
        for number, variants in by_number.items():
            best = self._pick_best(variants, prefer_user_uploaded)
            result.append(best)

        return sorted(result, key=lambda c: c.sort_key)

    def _pick_best(self, variants: list[Chapter], prefer_user: bool) -> Chapter:
        """Pick best version: user > group > pages > recency."""
        return sorted(variants, key=lambda c: (
            (c.source == "user") if prefer_user else False,
            bool(c.group_name),
            c.page_count,
            c.date_added or "",
        ), reverse=True)[0]

    def get_available_groups(
        self,
        chapters: list[Chapter],
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get list of scanlation groups with chapter counts."""
        if language:
            chapters = [c for c in chapters if c.language == language]

        groups: dict[int, dict[str, Any]] = {}
        for ch in chapters:
            if ch.group_id and ch.group_name:
                if ch.group_id not in groups:
                    groups[ch.group_id] = {
                        "id": ch.group_id,
                        "name": ch.group_name,
                        "chapter_count": 0,
                    }
                groups[ch.group_id]["chapter_count"] += 1

        return sorted(groups.values(), key=lambda g: g["chapter_count"], reverse=True)

    def get_available_languages(self, chapters: list[Chapter]) -> list[dict[str, Any]]:
        """Get list of languages with chapter counts."""
        langs: dict[str, int] = {}
        for ch in chapters:
            langs.setdefault(ch.language, 0)
            langs[ch.language] += 1

        return [
            {"code": code, "count": count}
            for code, count in sorted(langs.items(), key=lambda x: -x[1])
        ]
