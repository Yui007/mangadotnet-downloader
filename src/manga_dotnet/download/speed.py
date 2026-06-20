"""Bandwidth throttling and speed control."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class BandwidthThrottle:
    """Simple bandwidth throttle using token bucket algorithm."""

    def __init__(self, max_bytes_per_second: int | None = None):
        self.max_bps = max_bytes_per_second
        self._tokens = 0.0
        self._last_refill = 0.0

    async def acquire(self, num_bytes: int) -> None:
        """Wait if necessary to stay under the bandwidth limit."""
        if self.max_bps is None or self.max_bps <= 0:
            return

        now = asyncio.get_event_loop().time()

        # Refill tokens
        if self._last_refill > 0:
            elapsed = now - self._last_refill
            self._tokens = min(
                self.max_bps,
                self._tokens + elapsed * self.max_bps,
            )
        self._last_refill = now

        # If not enough tokens, wait
        if self._tokens < num_bytes:
            wait_time = (num_bytes - self._tokens) / self.max_bps
            await asyncio.sleep(wait_time)
            self._tokens = 0.0
        else:
            self._tokens -= num_bytes

    def reset(self) -> None:
        """Reset the throttle."""
        self._tokens = 0.0
        self._last_refill = 0.0
