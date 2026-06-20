"""LRU in-memory cache + JSON file cache for API responses."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from hashlib import md5
from pathlib import Path
from typing import Any


class APICache:
    """Cache for API responses with TTL and size limits.

    Two-tier cache:
    - In-memory dict for hot reads (instant)
    - JSON files on disk for persistence across restarts
    """

    def __init__(self, cache_dir: Path, max_size_mb: int = 500, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl = timedelta(hours=ttl_hours)
        self._memory_cache: dict[str, tuple[datetime, Any]] = {}
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str, params: dict | None = None) -> str:
        """Generate cache key from URL + params."""
        raw = url + json.dumps(params or {}, sort_keys=True)
        return md5(raw.encode()).hexdigest()

    def get(self, url: str, params: dict | None = None) -> Any | None:
        """Get cached response if valid (sync for simplicity)."""
        key = self._key(url, params)

        # Check memory cache
        if key in self._memory_cache:
            ts, data = self._memory_cache[key]
            if datetime.now() - ts < self.ttl:
                return data
            del self._memory_cache[key]

        # Check disk cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                raw = json.loads(cache_file.read_text(encoding="utf-8"))
                ts = datetime.fromisoformat(raw["timestamp"])
                if datetime.now() - ts < self.ttl:
                    self._memory_cache[key] = (ts, raw["data"])
                    return raw["data"]
                else:
                    cache_file.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError, ValueError):
                cache_file.unlink(missing_ok=True)

        return None

    def set(self, url: str, data: Any, params: dict | None = None) -> None:
        """Cache a response."""
        key = self._key(url, params)
        now = datetime.now()

        # Memory cache
        self._memory_cache[key] = (now, data)

        # Disk cache
        cache_file = self.cache_dir / f"{key}.json"
        try:
            cache_file.write_text(
                json.dumps({"timestamp": now.isoformat(), "data": data}, ensure_ascii=False),
                encoding="utf-8",
            )
        except (OSError, TypeError):
            pass  # Non-critical — memory cache still works

        self._enforce_size_limit()

    def _enforce_size_limit(self) -> None:
        """Remove oldest disk cache entries if over size limit."""
        try:
            total = sum(f.stat().st_size for f in self.cache_dir.glob("*.json") if f.is_file())
            if total <= self.max_size_bytes:
                return

            # Sort by modification time (oldest first), remove until under limit
            files = sorted(
                self.cache_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
            )
            for f in files:
                if total <= self.max_size_bytes * 0.8:  # Stop at 80% to avoid thrashing
                    break
                size = f.stat().st_size
                f.unlink(missing_ok=True)
                total -= size
        except OSError:
            pass

    def clear(self) -> None:
        """Clear all cached data."""
        self._memory_cache.clear()
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        try:
            disk_files = list(self.cache_dir.glob("*.json"))
            disk_size = sum(f.stat().st_size for f in disk_files)
        except OSError:
            disk_files = []
            disk_size = 0

        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": len(disk_files),
            "disk_size_bytes": disk_size,
            "disk_size_mb": round(disk_size / (1024 * 1024), 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "ttl_hours": self.ttl.total_seconds() / 3600,
        }
