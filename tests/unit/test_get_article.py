"""Unit tests for get_article API implementation."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.api.articles import get_article_via_api
from note_mcp.models import ArticleStatus, Session


@pytest.fixture
def mock_session() -> Session:
    """Create a mock session for testing."""
    return Session(
        cookies={"note_gql_auth_token": "test_token", "_note_session_v5": "test_session"},
        user_id="12345",
        username="testuser",
        created_at=1700000000,
    )


@pytest.fixture
def draft_article_api_response() -> dict[str, Any]:
    """Create a mock API response for a draft article."""
    return {
        "data": {
            "id": 140252918,
            "key": "nf46de6f3ced9",
            "name": "テスト記事",
            "body": "<h1>見出し1</h1><p>本文テスト</p><pre><code>print('hello')</code></pre>",
            "status": "draft",
            "hashtags": [
                {"hashtag": {"name": "テスト"}},
                {"hashtag": {"name": "API調査"}},
            ],
            "created_at": "2025-12-31T13:57:58.000+09:00",
            "updated_at": "2025-12-31T14:00:00.000+09:00",
            "noteUrl": "https://note.com/testuser/n/nf46de6f3ced9",
        }
    }


@pytest.fixture
def published_article_api_response() -> dict[str, Any]:
    """Create a mock API response for a published article."""
    return {
        "data": {
            "id": 140252919,
            "key": "npub123456789",
            "name": "公開記事",
            "body": "<p>公開された記事の本文です。</p>",
            "status": "published",
            "hashtags": [],
            "created_at": "2025-12-31T10:00:00.000+09:00",
            "updated_at": "2025-12-31T12:00:00.000+09:00",
            "publish_at": "2025-12-31T12:00:00.000+09:00",
            "noteUrl": "https://note.com/testuser/n/npub123456789",
        }
    }


class TestGetArticleViaAPI:
    """Tests for get_article_via_api function."""

    @pytest.mark.asyncio
    async def test_get_draft_article_returns_article(
        self, mock_session: Session, draft_article_api_response: dict[str, Any]
    ) -> None:
        """Test that get_article_via_api returns an Article for draft."""
        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = draft_article_api_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            article = await get_article_via_api(mock_session, "nf46de6f3ced9")

            assert article.id == "140252918"
            assert article.key == "nf46de6f3ced9"
            assert article.title == "テスト記事"
            assert article.status == ArticleStatus.DRAFT

    @pytest.mark.asyncio
    async def test_get_article_body_is_converted_to_markdown(
        self, mock_session: Session, draft_article_api_response: dict[str, Any]
    ) -> None:
        """Test that body HTML is converted to Markdown."""
        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = draft_article_api_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            article = await get_article_via_api(mock_session, "nf46de6f3ced9")

            # Body should be converted from HTML to Markdown
            assert "# 見出し1" in article.body
            assert "本文テスト" in article.body

    @pytest.mark.asyncio
    async def test_get_article_with_tags(
        self, mock_session: Session, draft_article_api_response: dict[str, Any]
    ) -> None:
        """Test that article tags are extracted correctly."""
        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = draft_article_api_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            article = await get_article_via_api(mock_session, "nf46de6f3ced9")

            assert "テスト" in article.tags
            assert "API調査" in article.tags

    @pytest.mark.asyncio
    async def test_get_published_article(
        self, mock_session: Session, published_article_api_response: dict[str, Any]
    ) -> None:
        """Test that get_article_via_api works for published articles."""
        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = published_article_api_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            article = await get_article_via_api(mock_session, "npub123456789")

            assert article.status == ArticleStatus.PUBLISHED
            assert article.title == "公開記事"

    @pytest.mark.asyncio
    async def test_get_article_with_numeric_id(
        self, mock_session: Session, draft_article_api_response: dict[str, Any]
    ) -> None:
        """Test that numeric article IDs work correctly."""
        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = draft_article_api_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            article = await get_article_via_api(mock_session, "140252918")

            mock_client.get.assert_called_once_with("/v3/notes/140252918")
            assert article.id == "140252918"

    @pytest.mark.asyncio
    async def test_get_article_preserves_code_blocks(self, mock_session: Session) -> None:
        """Test that code blocks are preserved in markdown conversion."""
        response = {
            "data": {
                "id": 123,
                "key": "ntest",
                "name": "コードテスト",
                "body": '<pre><code>def hello():\n    print("world")</code></pre>',
                "status": "draft",
                "hashtags": [],
            }
        }
        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            article = await get_article_via_api(mock_session, "ntest")

            # Code blocks should be preserved
            assert "def hello():" in article.body
            assert 'print("world")' in article.body

    @pytest.mark.asyncio
    async def test_get_article_with_empty_body(self, mock_session: Session) -> None:
        """Test handling of article with empty body."""
        response = {
            "data": {
                "id": 123,
                "key": "nempty",
                "name": "空の記事",
                "body": "",
                "status": "draft",
                "hashtags": [],
            }
        }
        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            article = await get_article_via_api(mock_session, "nempty")

            assert article.body == ""
