"""Cleanup helpers for E2E tests.

Provides utilities for cleaning up test articles with retry logic.
Issue #200: E2E tests were not properly cleaning up created articles.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from note_mcp.api.articles import delete_draft
from note_mcp.models import NoteAPIError

from .retry import with_retry

if TYPE_CHECKING:
    from note_mcp.models import Session

logger = logging.getLogger(__name__)

# Retry settings for cleanup operations
CLEANUP_MAX_ATTEMPTS: int = 3
CLEANUP_BACKOFF_BASE: float = 1.0


async def delete_draft_with_retry(
    session: Session,
    article_key: str,
    *,
    max_attempts: int = CLEANUP_MAX_ATTEMPTS,
    backoff_base: float = CLEANUP_BACKOFF_BASE,
) -> None:
    """Delete a draft article with retry logic.

    Attempts to delete the article with exponential backoff on transient errors.
    Silently ignores errors if the article does not exist or deletion fails
    after all retries.

    This is designed for cleanup operations where we don't want to fail the
    test if cleanup fails, but we do want to make a best effort.

    Args:
        session: Authenticated session
        article_key: Key of the article to delete (e.g., "n1234567890ab")
        max_attempts: Maximum number of deletion attempts (default: 3)
        backoff_base: Base delay in seconds for exponential backoff (default: 1.0)
    """
    try:
        await with_retry(
            lambda: delete_draft(session, article_key, confirm=True),
            max_attempts=max_attempts,
            backoff_base=backoff_base,
        )
        logger.debug("Successfully deleted article: %s", article_key)
    except NoteAPIError as e:
        # Check if article doesn't exist (404) - that's fine, nothing to delete
        status_code = e.details.get("status_code")
        if status_code == 404:
            logger.debug("Article %s does not exist, nothing to delete", article_key)
        else:
            logger.warning(
                "Failed to delete article %s after %d attempts: %s: %s",
                article_key,
                max_attempts,
                type(e).__name__,
                e.message,
            )
    except Exception as e:
        # Log but don't raise - cleanup should not fail tests
        logger.warning(
            "Unexpected error deleting article %s: %s: %s",
            article_key,
            type(e).__name__,
            e,
        )
