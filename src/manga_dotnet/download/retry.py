"""Retry strategies with exponential backoff."""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


def retry_with_backoff(
    func: Callable[..., T],
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Execute func with retry + exponential backoff + jitter."""
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions as e:
            last_error = e
            if attempt < max_attempts:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                jitter = random.uniform(0, delay * 0.3)
                wait = delay + jitter
                logger.warning(
                    "Attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt,
                    max_attempts,
                    e,
                    wait,
                )
                time.sleep(wait)
            else:
                logger.error("All %d attempts failed", max_attempts)

    raise last_error  # type: ignore[misc]


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is worth retrying."""
    error_type = type(error).__name__
    retryable = (
        "ConnectionError",
        "TimeoutError",
        "RateLimitError",
        "ServerError",
    )
    return error_type in retryable or "429" in str(error) or "503" in str(error)
