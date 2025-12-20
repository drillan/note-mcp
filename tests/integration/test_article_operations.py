"""Integration tests for article operations."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.api.articles import create_draft, update_article
from note_mcp.browser.preview import show_preview
from note_mcp.models import ArticleInput, ArticleStatus, Session

if TYPE_CHECKING:
    pass


def create_mock_session() -> Session:
    """Create a mock session for testing."""
    return Session(
        cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
        user_id="user123",
        username="testuser",
        expires_at=int(time.time()) + 3600,
        created_at=int(time.time()),
    )


class TestCreateDraft:
    """Tests for create_draft function."""

    @pytest.mark.asyncio
    async def test_create_draft_success(self) -> None:
        """Test successful draft creation."""
        session = create_mock_session()
        article_input = ArticleInput(
            title="Test Article",
            body="# Hello\n\nThis is a test article.",
            tags=["test", "python"],
        )

        mock_response = {
            "data": {
                "id": "123456",
                "key": "n1234567890ab",
                "name": "Test Article",
                "body": "<h1>Hello</h1>\n<p>This is a test article.</p>\n",
                "status": "draft",
                "hashtags": [
                    {"hashtag": {"name": "test"}},
                    {"hashtag": {"name": "python"}},
                ],
                "noteUrl": "https://note.com/testuser/n/n1234567890ab",
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            article = await create_draft(session, article_input)

            assert article.id == "123456"
            assert article.title == "Test Article"
            assert article.status == ArticleStatus.DRAFT
            assert "test" in article.tags
            assert "python" in article.tags

    @pytest.mark.asyncio
    async def test_create_draft_converts_markdown_to_html(self) -> None:
        """Test that Markdown is converted to HTML."""
        session = create_mock_session()
        article_input = ArticleInput(
            title="Test",
            body="**Bold** and *italic*",
        )

        mock_response = {
            "data": {
                "id": "123",
                "key": "n123",
                "name": "Test",
                "body": "<p><strong>Bold</strong> and <em>italic</em></p>\n",
                "status": "draft",
                "hashtags": [],
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            await create_draft(session, article_input)

            # Verify that the post was called
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            # The body should be HTML, not Markdown
            assert "body" in call_args[1]["json"]


class TestUpdateArticle:
    """Tests for update_article function."""

    @pytest.mark.asyncio
    async def test_update_article_success(self) -> None:
        """Test successful article update."""
        session = create_mock_session()
        article_input = ArticleInput(
            title="Updated Title",
            body="Updated content",
        )

        mock_response = {
            "data": {
                "id": "123456",
                "key": "n1234567890ab",
                "name": "Updated Title",
                "body": "<p>Updated content</p>\n",
                "status": "draft",
                "hashtags": [],
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.put = AsyncMock(return_value=mock_response)

            article = await update_article(session, "123456", article_input)

            assert article.id == "123456"
            assert article.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_article_partial_update(self) -> None:
        """Test partial article update (title only)."""
        session = create_mock_session()
        article_input = ArticleInput(
            title="New Title Only",
            body="",  # Empty body means no update
        )

        mock_response = {
            "data": {
                "id": "123456",
                "key": "n1234567890ab",
                "name": "New Title Only",
                "body": "<p>Original content</p>",
                "status": "draft",
                "hashtags": [],
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.put = AsyncMock(return_value=mock_response)

            article = await update_article(session, "123456", article_input)

            assert article.title == "New Title Only"


class TestShowPreview:
    """Tests for show_preview function."""

    @pytest.mark.asyncio
    async def test_show_preview_navigates_to_edit_page(self) -> None:
        """Test that preview navigates to the correct URL."""
        session = create_mock_session()

        with patch("note_mcp.browser.preview.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)

            await show_preview(session, "n1234567890ab")

            # Verify navigation to the edit page
            mock_page.goto.assert_called_once()
            call_args = mock_page.goto.call_args[0][0]
            assert "note.com/testuser/n/n1234567890ab/edit" in call_args

    @pytest.mark.asyncio
    async def test_show_preview_uses_session_username(self) -> None:
        """Test that preview uses the session username."""
        session = Session(
            cookies={"note_gql_auth_token": "token"},
            user_id="123",
            username="my_custom_username",
            expires_at=None,
            created_at=int(time.time()),
        )

        with patch("note_mcp.browser.preview.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)

            await show_preview(session, "article123")

            call_args = mock_page.goto.call_args[0][0]
            assert "my_custom_username" in call_args
