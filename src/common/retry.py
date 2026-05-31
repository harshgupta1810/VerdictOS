"""Exponential Backoff Retry Utilities.

Provides decorator/utility for retrying asynchronous functions (especially LLM and HTTP calls)
with exponential backoff and jitter.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, Callable, TypeVar, cast

import httpx

from src.common.exceptions import LLMClientError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def with_exponential_backoff(
    retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 32.0,
    exceptions: tuple[type[BaseException], ...] = (
        LLMClientError,
        httpx.TimeoutException,
        httpx.HTTPStatusError,
    ),
) -> Callable[[F], F]:
    """Decorator to retry asynchronous functions with exponential backoff and jitter.

    Specifically retries on rate limits (HTTP 429/503), timeouts, and client errors.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    # If it's an HTTPStatusError, only retry on 429, 503, or similar retryable codes
                    if isinstance(exc, httpx.HTTPStatusError):
                        if exc.response.status_code not in (429, 503, 504):
                            raise exc

                    attempt += 1
                    if attempt > retries:
                        logger.error(
                            "Retry limit of %d reached for %s. Raising exception.",
                            retries,
                            func.__name__,
                        )
                        raise exc

                    # Calculate exponential backoff: base * (2 ** (attempt - 1))
                    delay = base_delay * (2 ** (attempt - 1))
                    delay = min(delay, max_delay)
                    # Add jitter: +/- 10%
                    jitter = random.uniform(-0.1, 0.1) * delay
                    actual_delay = max(0.1, min(max_delay, delay + jitter))

                    logger.warning(
                        "Attempt %d failed for %s with %s. Retrying in %.2fs...",
                        attempt,
                        func.__name__,
                        exc.__class__.__name__,
                        actual_delay,
                    )
                    await asyncio.sleep(actual_delay)

        return cast(F, wrapper)

    return decorator
