"""Helper functions for extracting article information from MCP tool results.

Provides utilities for parsing the text output from note_create_from_file.fn()
and similar MCP tools to extract article metadata.
"""

from __future__ import annotations

import re


def extract_article_key(result: str) -> str:
    """Extract article_key from note_create_from_file.fn() result.

    Parses the text output from MCP tools to find the article key,
    which is needed for preview page navigation.

    Args:
        result: The text result from note_create_from_file.fn()
            Expected format includes "記事キー: n1234567890ab"

    Returns:
        The extracted article key (e.g., "n1234567890ab")

    Raises:
        ValueError: If article key cannot be found in the result

    Example:
        >>> result = "✅ 下書きを作成しました\\n   タイトル: Test\\n   記事ID: 123\\n   記事キー: n1234567890ab"
        >>> extract_article_key(result)
        'n1234567890ab'
    """
    match = re.search(r"記事キー:\s*(\S+)", result)
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
