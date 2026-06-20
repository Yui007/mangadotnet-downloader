"""Async helpers — semaphore, throttle, bounded gather."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


async def gather_n(
    *coros: Awaitable[T],
    limit: int = 8,
) -> list[T]:
    """Run awaitables with bounded concurrency.

    Like ``asyncio.gather`` but caps the number of concurrent tasks.
    """
    semaphore = asyncio.Semaphore(limit)

    async def _wrap(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    return await asyncio.gather(*(_wrap(c) for c in coros))


class Throttle:
    """Simple rate limiter — at most *rate* calls per second."""

    def __init__(self, rate: float = 10.0):
        self.min_interval = 1.0 / rate
        self._last = 0.0

    async def acquire(self) -> None:
        """Wait until we can make another request."""
        now = time.monotonic()
        wait = self.min_interval - (now - self._last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = time.monotonic()

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator version (sync functions only)."""
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await self.acquire()
            return func(*args, **kwargs)
        return wrapper  # type: ignore[return-value]
