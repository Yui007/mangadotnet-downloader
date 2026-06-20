"""Manga search — parse the Nuxt-style packed search response format.

The search API returns a flat array where objects use index references
(``_N`` keys) pointing to positions in the parent array. This module
unpacks it into ``MangaResult`` models.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from manga_dotnet.api.client import MangaDotNetClient
from manga_dotnet.core.models import MangaResult

logger = logging.getLogger(__name__)

# Field name → index mapping for the manga schema
# These are derived from the actual API response structure
_FIELD_MAP = {
    "id": "_id",
    "title": "_title",
    "photo": "_photo",
    "status": "_status",
    "rating": "_rating",
    "chapter_count": "_chapter_count",
    "genres": "_genres",
    "is_adult": "_is_adult",
    "avg_rating": "_avg_rating",
    "rating_count": "_rating_count",
    "description": "_description",
    "authors": "_authors",
    "artists": "_artists",
    "country_of_origin": "_country_of_origin",
}


class SearchAPI:
    """Manga search functionality."""

    def __init__(self, client: MangaDotNetClient):
        self.client = client

    def search(self, query: str, limit: int = 50) -> list[MangaResult]:
        """Search for manga by title."""
        raw = self.client.search(query, per_page=limit)
        return self._parse_search_response(raw)

    def _parse_search_response(self, data: Any) -> list[MangaResult]:
        """Parse the Nuxt-style packed search response.

        The response is a flat array where:
        1. Objects use ``_N`` keys where N is an index in the flat array
        2. The value at that index is either a primitive or another reference
        3. We need to resolve the reference chain to get actual values
        """
        if not isinstance(data, list):
            logger.warning("Unexpected search response type: %s", type(data))
            return []

        try:
            return self._resolve_manga_results(data)
        except Exception as e:
            logger.warning("Reference resolution failed (%s), falling back to regex", e)
            return self._regex_extract(data)

    def _resolve_manga_results(self, data: list) -> list[MangaResult]:
        """Resolve the packed array into manga results."""
        results: list[MangaResult] = []

        # Find the "results" key and its associated array of indices
        results_indices = None
        for i, item in enumerate(data):
            if item == "results" and i + 1 < len(data) and isinstance(data[i + 1], list):
                results_indices = data[i + 1]
                break

        if not results_indices:
            logger.warning("Could not find 'results' key in search response")
            return []

        for idx in results_indices:
            if idx >= len(data):
                continue
            manga_obj = data[idx]
            if not isinstance(manga_obj, dict):
                continue

            manga = self._resolve_manga_object(data, manga_obj)
            if manga:
                results.append(manga)

        return results

    def _resolve_manga_object(self, data: list, obj: dict) -> MangaResult | None:
        """Resolve a single manga object from the packed format.

        Each key in the object is ``_N`` where N is the index of the field
        name in the flat array. The value is either a primitive or another
        index reference.
        """
        resolved: dict[str, Any] = {}

        for key, value in obj.items():
            if not key.startswith("_"):
                continue

            field_idx = int(key[1:])
            if field_idx >= len(data):
                continue

            field_name = data[field_idx]
            if not isinstance(field_name, str):
                continue

            # Resolve the value
            resolved[field_name] = self._resolve_value(data, value)

        # Build MangaResult from resolved fields
        manga_id = resolved.get("id")
        title = resolved.get("title")

        if not manga_id or not title or not isinstance(manga_id, (int, float)):
            return None

        return MangaResult(
            id=int(manga_id),
            title=str(title),
            photo=str(resolved.get("photo", "")),
            status=str(resolved.get("status", "")),
            rating=resolved.get("avg_rating") or resolved.get("rating"),
            chapter_count=int(resolved.get("chapter_count", 0) or 0),
            genres=resolved.get("genres", []) if isinstance(resolved.get("genres"), list) else [],
            description=str(resolved.get("description", "")),
            is_adult=bool(resolved.get("is_blurworthy", 0)),
        )

    def _resolve_value(self, data: list, value: Any) -> Any:
        """Resolve a value from the packed format.

        If the value is an integer index into the data array, resolve it.
        If it's a primitive, return as-is.
        """
        if isinstance(value, int) and 0 <= value < len(data):
            resolved = data[value]
            if isinstance(resolved, (str, int, float, bool)):
                return resolved
            elif isinstance(resolved, list):
                # Resolve list items
                return [self._resolve_value(data, item) for item in resolved]
        return value

    def _regex_extract(self, data: list) -> list[MangaResult]:
        """Fallback: extract manga entries using regex patterns."""
        results: list[MangaResult] = []
        raw = json.dumps(data)

        # Find manga title + ID patterns
        title_pattern = re.compile(r'"([A-Z][^"]{3,80})"')
        id_pattern = re.compile(r'"id"\s*:\s*(\d+)')

        titles = title_pattern.findall(raw)
        ids = id_pattern.findall(raw)

        seen_ids: set[int] = set()
        for manga_id_str in ids:
            manga_id = int(manga_id_str)
            if manga_id in seen_ids or manga_id < 1:
                continue
            seen_ids.add(manga_id)

            idx = raw.find(f'"id":{manga_id}')
            if idx < 0:
                idx = raw.find(f'"id": {manga_id}')
            if idx < 0:
                continue

            nearby = raw[max(0, idx - 500):idx + 500]
            title_match = title_pattern.search(nearby)
            if title_match:
                results.append(MangaResult(
                    id=manga_id,
                    title=title_match.group(1),
                ))

            if len(results) >= 50:
                break

        return results
