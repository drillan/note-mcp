"""Helper functions for extracting article information from MCP tool results.

Provides utilities for parsing the text output from MCP tools such as
note_create_from_file.fn() and note_create_draft.fn() to extract article metadata.
"""

from __future__ import annotations

import re

from note_mcp.api.articles import get_article_raw_html
from note_mcp.auth.session import SessionManager


def extract_article_key(result: str) -> str:
    """Extract article_key from MCP tool result.

    Parses the text output from MCP tools to find the article key,
    which is needed for preview page navigation.

    Args:
        result: The text result from MCP tools like note_create_draft.fn()
            or note_create_from_file.fn()
            Supported formats: "キー: n1234567890ab" or "記事キー: n1234567890ab"

    Returns:
        The extracted article key (e.g., "n1234567890ab")

    Raises:
        ValueError: If article key cannot be found in the result

    Example:
        >>> result = "下書きを作成しました。ID: 123、キー: n1234567890ab"
        >>> extract_article_key(result)
        'n1234567890ab'
    """
    match = re.search(r"(?:記事)?キー:\s*(\S+)", result)
    if not match:
        raise ValueError(f"Could not extract article key from result: {result}")
    return match.group(1)


def extract_article_id(result: str) -> str:
    """Extract article_id from MCP tool results.

    Parses the text output from MCP tools to find the article ID,
    which is the numeric identifier for the article.

    Args:
        result: The text result from MCP tools like note_create_draft.fn()
            or note_create_from_file.fn()
            Expected format includes "ID: 123456789" or "記事ID: 123456789"

    Returns:
        The extracted article ID (e.g., "123456789")

    Raises:
        ValueError: If article ID cannot be found in the result

    Example:
        >>> result = "下書きを作成しました。ID: 123456789、キー: n1234567890ab"
        >>> extract_article_id(result)
        '123456789'
    """
    match = re.search(r"(?:記事)?ID:\s*(\d+)", result)
    if not match:
        raise ValueError(f"Could not extract article ID from result: {result}")
    return match.group(1)


async def get_article_html(article_key: str) -> str:
    """Get article body as raw HTML (without Markdown conversion).

    Uses get_article_raw_html() to retrieve the article body in its original
    HTML format. This is useful for tests that need to validate HTML attributes
    like embedded-service that are lost during Markdown conversion.

    Args:
        article_key: The article key (e.g., "n1234567890ab")

    Returns:
        The article body as raw HTML

    Raises:
        RuntimeError: If session is not available or expired
        NoteAPIError: If API request fails (article not found, auth error, etc.)
        ValueError: If article body is empty

    Example:
        >>> html = await get_article_html("n1234567890ab")
        >>> assert 'embedded-service="youtube"' in html
    """
    session = SessionManager().load()
    if session is None:
        raise RuntimeError("Session not found. Please login first.")
    if session.is_expired():
        raise RuntimeError("Session has expired. Please login again.")

    article = await get_article_raw_html(session, article_key)
    if not article.body:
        raise ValueError(
            f"Article '{article_key}' has no body content. "
            f"Article title: '{article.title}', status: '{article.status.value}'."
        )
    return article.body
