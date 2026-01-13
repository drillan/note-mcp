"""Retry helper for E2E tests with transient network errors.

This module provides a `with_retry` helper function that automatically
retries operations that fail due to temporary network issues when
testing against note.com.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx
from playwright.async_api import Error as PlaywrightError

from note_mcp.models import ErrorCode, NoteAPIError

logger = logging.getLogger(__name__)

# Retryable exception types
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    TimeoutError,
    asyncio.TimeoutError,
    httpx.TimeoutException,
    httpx.NetworkError,
)

DEFAULT_MAX_ATTEMPTS: int = 3
DEFAULT_BACKOFF_BASE: float = 1.0


def is_transient_access_denied_error(exception: Exception) -> bool:
    """Check if exception is a transient Access Denied (403) error.

    Distinguishes between transient 403 errors (rate limiting) and
    permanent 403 errors (true permission denied).

    Transient 403 criteria:
        - status_code is 403 AND
        - response body contains "Access denied" (rate limiting pattern)

    Args:
        exception: The exception to check.

    Returns:
        True if the exception is a transient 403 error suitable for retry.
    """
    if not isinstance(exception, NoteAPIError):
        return False

    status_code = exception.details.get("status_code")
    if status_code != 403:
        return False

    # Check response body for "Access denied" pattern (rate limiting)
    response_text = exception.details.get("response", "")
    if isinstance(response_text, str) and "Access denied" in response_text:
        logger.debug(
            "Detected transient 403 (Access denied in response body): %s",
            exception.message,
        )
        return True

    # Other 403 errors are likely true permission errors
    logger.debug(
        "403 error without 'Access denied' pattern - not retrying: %s",
        exception.message,
    )
    return False


def is_rate_limited_error(exception: Exception) -> bool:
    """Check if exception is a rate limiting (429) error.

    Args:
        exception: The exception to check.

    Returns:
        True if the exception is a NoteAPIError with RATE_LIMITED code.
    """
    if isinstance(exception, NoteAPIError) and exception.code == ErrorCode.RATE_LIMITED:
        logger.debug("Detected rate limited error (429): %s", exception.message)
        return True
    return False


def is_retryable(exception: Exception) -> bool:
    """Check if an exception is retryable.

    Args:
        exception: The exception to check.

    Returns:
        True if the exception is retryable, False otherwise.
    """
    # Direct match for standard retryable exceptions
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        logger.debug(
            "Retryable exception type: %s",
            type(exception).__name__,
        )
        return True

    # PlaywrightError with timeout-related message
    if isinstance(exception, PlaywrightError):
        msg = str(exception).lower()
        if "timeout" in msg or "timed out" in msg:
            logger.debug("Retryable Playwright timeout error: %s", msg)
            return True
        return False

    # Rate limited (429) error
    if is_rate_limited_error(exception):
        return True

    # Transient Access Denied (403) error - rate limiting pattern
    return is_transient_access_denied_error(exception)


async def with_retry[T](
    func: Callable[[], Awaitable[T]],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> T:
    """Execute an async function with retry on transient errors.

    Implements exponential backoff with formula: backoff_base * 2^(attempt-1)
    Example with backoff_base=1.0: 1s, 2s, 4s for attempts 1, 2, 3.
    Example with backoff_base=2.0: 2s, 4s, 8s for attempts 1, 2, 3.

    Retryable errors:
        - Timeout errors (TimeoutError, httpx.TimeoutException)
        - Network errors (httpx.NetworkError)
        - Playwright timeout errors
        - Rate limited errors (429 / ErrorCode.RATE_LIMITED)
        - Transient 403 errors (with "Access denied" in response body)

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
                    "Attempt %d/%d failed: %s: %s. Retrying in %.1fs...",
                    attempt,
                    max_attempts,
                    type(e).__name__,
                    str(e),
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Attempt %d/%d failed: %s: %s. No more retries.",
                    attempt,
                    max_attempts,
                    type(e).__name__,
                    str(e),
                )

    # Should not reach here, but type checker needs this
    assert last_exception is not None
    raise last_exception
