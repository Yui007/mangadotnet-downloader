"""Progress tracking for downloads — stats, speed, ETA."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DownloadProgress:
    """Progress update for UI consumers."""

    chapter_id: int = 0
    chapter_number: float = 0.0
    current_page: int = 0
    total_pages: int = 0
    bytes_downloaded: int = 0
    speed_bps: float = 0.0
    elapsed_seconds: float = 0.0
    status: str = "idle"  # idle | downloading | exporting | completed | failed

    @property
    def percent(self) -> float:
        """Download progress as percentage."""
        if self.total_pages <= 0:
            return 0.0
        return min(100.0, (self.current_page / self.total_pages) * 100)

    @property
    def eta_seconds(self) -> float | None:
        """Estimated time remaining in seconds."""
        if self.speed_bps <= 0 or self.current_page <= 0:
            return None
        remaining_pages = self.total_pages - self.current_page
        avg_bytes_per_page = self.bytes_downloaded / self.current_page
        remaining_bytes = remaining_pages * avg_bytes_per_page
        return remaining_bytes / self.speed_bps


class SpeedTracker:
    """Tracks download speed over a rolling window."""

    def __init__(self, window_seconds: float = 5.0):
        self.window = window_seconds
        self._samples: list[tuple[float, int]] = []  # (timestamp, bytes)

    def record(self, bytes_downloaded: int) -> None:
        """Record a batch of bytes downloaded."""
        now = time.monotonic()
        self._samples.append((now, bytes_downloaded))
        # Prune old samples
        cutoff = now - self.window
        self._samples = [(t, b) for t, b in self._samples if t >= cutoff]

    @property
    def speed_bps(self) -> float:
        """Current speed in bytes per second."""
        if len(self._samples) < 2:
            return 0.0
        now = time.monotonic()
        cutoff = now - self.window
        recent = [(t, b) for t, b in self._samples if t >= cutoff]
        if len(recent) < 2:
            return 0.0
        total_bytes = sum(b for _, b in recent)
        time_span = recent[-1][0] - recent[0][0]
        if time_span <= 0:
            return 0.0
        return total_bytes / time_span

    def reset(self) -> None:
        """Reset the tracker."""
        self._samples.clear()
