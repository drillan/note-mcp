"""Retry helper for E2E tests with transient network errors.

This module provides a `with_retry` helper function that automatically
retries operations that fail due to temporary network issues when
testing against note.com.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from playwright.async_api import Error as PlaywrightError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Retryable exception types
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    TimeoutError,
    asyncio.TimeoutError,
    httpx.TimeoutException,
    httpx.NetworkError,
)

DEFAULT_MAX_ATTEMPTS: int = 3
DEFAULT_BACKOFF_BASE: float = 1.0


def is_retryable(exception: Exception) -> bool:
    """Check if an exception is retryable.

    Args:
        exception: The exception to check.

    Returns:
        True if the exception is retryable, False otherwise.
    """
    # Direct match for standard retryable exceptions
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True

    # PlaywrightError with timeout-related message
    if isinstance(exception, PlaywrightError):
        msg = str(exception).lower()
        return "timeout" in msg or "timed out" in msg

    return False


async def with_retry(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> T:
    """Execute an async function with retry on transient errors.

    Implements exponential backoff: 1s, 2s, 4s, etc.

    Args:
        func: Async function to execute (typically a lambda wrapping the call).
        max_attempts: Maximum number of attempts (default: 3).
        backoff_base: Base delay in seconds for exponential backoff (default: 1.0).
        retryable_exceptions: Tuple of exception types to retry on.
            If None, uses RETRYABLE_EXCEPTIONS.

    Returns:
        The result of the function call.

    Raises:
        The last exception if all attempts fail.

    Example:
        >>> article = await with_retry(lambda: create_draft(session, input))
    """
    if retryable_exceptions is None:
        retryable_exceptions = RETRYABLE_EXCEPTIONS

    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except Exception as e:
            # Check if retryable (including PlaywrightError timeout check)
            if not is_retryable(e) and not isinstance(e, retryable_exceptions):
                raise

            last_exception = e

            if attempt < max_attempts:
                delay = backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "Attempt %d failed: %s. Retrying in %.1fs...",
                    attempt,
                    type(e).__name__,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Attempt %d failed: %s. No more retries.",
                    attempt,
                    type(e).__name__,
                )

    # Should not reach here, but type checker needs this
    assert last_exception is not None
    raise last_exception
