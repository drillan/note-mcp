"""Pytest configuration and shared fixtures for note-mcp tests.

This module provides common fixtures used across unit, integration, and contract tests.
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.models import Session

if TYPE_CHECKING:
    pass


# ============================================================================
# Session Fixtures
# ============================================================================


@pytest.fixture
def mock_session() -> Session:
    """Create a mock session for testing.

    Returns:
        A valid Session object with test credentials.
    """
    return Session(
        cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
        user_id="user123",
        username="testuser",
        expires_at=int(time.time()) + 3600,
        created_at=int(time.time()),
    )


@pytest.fixture
def expired_session() -> Session:
    """Create an expired session for testing.

    Returns:
        A Session object that has already expired.
    """
    return Session(
        cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
        user_id="user123",
        username="testuser",
        expires_at=int(time.time()) - 3600,  # Expired 1 hour ago
        created_at=int(time.time()) - 7200,
    )


# ============================================================================
# Keyring Fixtures
# ============================================================================


@pytest.fixture
def mock_keyring() -> Generator[MagicMock, None, None]:
    """Create a mock keyring for testing session storage.

    Yields:
        A mocked keyring module.
    """
    with patch("note_mcp.auth.session.keyring") as mock:
        mock.get_password.return_value = None
        yield mock


@pytest.fixture
def mock_keyring_with_session(mock_keyring: MagicMock, mock_session: Session) -> MagicMock:
    """Create a mock keyring with a stored session.

    Args:
        mock_keyring: The base mock keyring fixture.
        mock_session: The mock session to store.

    Returns:
        A mocked keyring that returns the mock session.
    """
    mock_keyring.get_password.return_value = json.dumps(mock_session.model_dump())
    return mock_keyring


# ============================================================================
# API Client Fixtures
# ============================================================================


@pytest.fixture
def mock_api_client() -> Generator[AsyncMock, None, None]:
    """Create a mock NoteAPIClient for testing API operations.

    Yields:
        A mocked NoteAPIClient that can be configured for specific tests.
    """
    with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        yield mock_client


# ============================================================================
# Browser Fixtures
# ============================================================================


@pytest.fixture
def mock_browser_manager() -> Generator[tuple[MagicMock, AsyncMock], None, None]:
    """Create a mock BrowserManager for testing browser operations.

    Yields:
        A tuple of (mock_manager, mock_page) for configuring browser behavior.
    """
    with patch("note_mcp.browser.preview.BrowserManager") as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_manager.get_page = AsyncMock(return_value=mock_page)

        yield mock_manager, mock_page


# ============================================================================
# Test Data Factories
# ============================================================================


def create_article_response(
    article_id: str = "123456",
    key: str = "n1234567890ab",
    title: str = "Test Article",
    body: str = "<p>Test content</p>",
    status: str = "draft",
    tags: list[str] | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Create a mock API response for an article.

    Args:
        article_id: The article ID.
        key: The article key.
        title: The article title.
        body: The article body (HTML).
        status: The article status (draft/published).
        tags: List of tag names.
        url: The article URL.

    Returns:
        A dictionary matching the note.com API response format.
    """
    response: dict[str, Any] = {
        "data": {
            "id": article_id,
            "key": key,
            "name": title,
            "body": body,
            "status": status,
            "hashtags": [{"hashtag": {"name": tag}} for tag in (tags or [])],
        }
    }

    if url:
        response["data"]["noteUrl"] = url

    return response


def create_article_list_response(
    articles: list[dict[str, Any]] | None = None,
    total_count: int | None = None,
    is_last_page: bool = True,
) -> dict[str, Any]:
    """Create a mock API response for article listing.

    Args:
        articles: List of article data dictionaries.
        total_count: Total number of articles (defaults to len(articles)).
        is_last_page: Whether this is the last page.

    Returns:
        A dictionary matching the note.com API list response format.
    """
    if articles is None:
        articles = []

    return {
        "data": {
            "notesByAuthor": {
                "contents": articles,
                "totalCount": total_count if total_count is not None else len(articles),
                "isLastPage": is_last_page,
            }
        }
    }
