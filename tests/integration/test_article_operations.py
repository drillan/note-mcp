"""Integration tests for article operations."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.api.articles import create_draft, get_article, list_articles, publish_article, update_article
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
        """Test successful draft creation via browser."""
        from note_mcp.models import Article

        session = create_mock_session()
        article_input = ArticleInput(
            title="Test Article",
            body="# Hello\n\nThis is a test article.",
            tags=["test", "python"],
        )

        mock_article = Article(
            id="123456",
            key="n1234567890ab",
            title="Test Article",
            body="<h1>Hello</h1>\n<p>This is a test article.</p>\n",
            status=ArticleStatus.DRAFT,
            tags=["test", "python"],
        )

        with patch("note_mcp.browser.create_draft.create_draft_via_browser") as mock_create:
            mock_create.return_value = mock_article

            article = await create_draft(session, article_input)

            assert article.id == "123456"
            assert article.title == "Test Article"
            assert article.status == ArticleStatus.DRAFT
            assert "test" in article.tags
            assert "python" in article.tags
            mock_create.assert_called_once_with(session, article_input)

    @pytest.mark.asyncio
    async def test_create_draft_converts_markdown_to_html(self) -> None:
        """Test that create_draft delegates to browser function."""
        from note_mcp.models import Article

        session = create_mock_session()
        article_input = ArticleInput(
            title="Test",
            body="**Bold** and *italic*",
        )

        mock_article = Article(
            id="123",
            key="n123",
            title="Test",
            body="<p><strong>Bold</strong> and <em>italic</em></p>\n",
            status=ArticleStatus.DRAFT,
            tags=[],
        )

        with patch("note_mcp.browser.create_draft.create_draft_via_browser") as mock_create:
            mock_create.return_value = mock_article

            await create_draft(session, article_input)

            # Verify that the browser function was called with correct arguments
            mock_create.assert_called_once_with(session, article_input)


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
            # Uses POST to draft_save endpoint
            mock_client.post = AsyncMock(return_value=mock_response)

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
            # Uses POST to draft_save endpoint
            mock_client.post = AsyncMock(return_value=mock_response)

            article = await update_article(session, "123456", article_input)

            assert article.title == "New Title Only"


class TestGetArticle:
    """Tests for get_article function."""

    @pytest.mark.asyncio
    async def test_get_article_success(self) -> None:
        """Test successful article retrieval via browser."""
        from note_mcp.models import Article

        session = create_mock_session()

        mock_article = Article(
            id="123456",
            key="n1234567890ab",
            title="Existing Article",
            body="This is the existing content.\n\nWith multiple paragraphs.",
            status=ArticleStatus.DRAFT,
            tags=[],
        )

        with patch("note_mcp.browser.get_article.get_article_via_browser") as mock_get:
            mock_get.return_value = mock_article

            article = await get_article(session, "123456")

            assert article.id == "123456"
            assert article.title == "Existing Article"
            assert "existing content" in article.body
            mock_get.assert_called_once_with(session, "123456")

    @pytest.mark.asyncio
    async def test_get_article_preserves_newlines(self) -> None:
        """Test that article body preserves newlines."""
        from note_mcp.models import Article

        session = create_mock_session()

        mock_article = Article(
            id="123",
            key="n123",
            title="Test",
            body="Line 1\n\nLine 2\n\nLine 3",
            status=ArticleStatus.DRAFT,
            tags=[],
        )

        with patch("note_mcp.browser.get_article.get_article_via_browser") as mock_get:
            mock_get.return_value = mock_article

            article = await get_article(session, "123")

            assert article.body.count("\n") >= 2

    @pytest.mark.asyncio
    async def test_get_article_returns_article_object(self) -> None:
        """Test that get_article returns proper Article object."""
        from note_mcp.models import Article

        session = create_mock_session()

        mock_article = Article(
            id="789",
            key="n789",
            title="Test Title",
            body="Test body content",
            status=ArticleStatus.DRAFT,
            tags=[],
        )

        with patch("note_mcp.browser.get_article.get_article_via_browser") as mock_get:
            mock_get.return_value = mock_article

            article = await get_article(session, "789")

            assert isinstance(article, Article)
            assert article.title == "Test Title"
            assert article.status == ArticleStatus.DRAFT


class TestShowPreview:
    """Tests for show_preview function.

    show_preview navigates to the editor page, clicks the menu button
    to open the header popover, then clicks the preview button which
    opens a new tab with the preview page.
    """

    @pytest.mark.asyncio
    async def test_show_preview_navigates_to_edit_page(self) -> None:
        """Test that preview navigates to the editor first then clicks preview."""
        session = create_mock_session()

        with patch("note_mcp.browser.preview.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            # Mock the page object with all required methods
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.wait_for_load_state = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()

            # Mock the locator for menu button
            mock_menu_button = AsyncMock()
            mock_menu_button.click = AsyncMock()

            # Mock the locator for preview button
            mock_preview_button = AsyncMock()
            mock_preview_button.click = AsyncMock()

            # Mock page.locator to return appropriate mocks
            def locator_side_effect(selector: str, **kwargs: object) -> AsyncMock:
                if 'aria-label="その他"' in selector:
                    return mock_menu_button
                else:
                    return mock_preview_button

            mock_page.locator = MagicMock(side_effect=locator_side_effect)

            # Mock context for new page handling
            mock_new_page = AsyncMock()
            mock_new_page.wait_for_load_state = AsyncMock()
            mock_new_page.bring_to_front = AsyncMock()

            mock_context = MagicMock()
            mock_context.add_cookies = AsyncMock()
            mock_page.context = mock_context

            # Create async context manager for expect_page
            # The value property needs to be awaitable
            async def get_new_page() -> AsyncMock:
                return mock_new_page

            mock_expect_page = MagicMock()
            mock_expect_page.__aenter__ = AsyncMock(return_value=mock_expect_page)
            mock_expect_page.__aexit__ = AsyncMock(return_value=None)
            mock_expect_page.value = get_new_page()  # Returns coroutine
            mock_context.expect_page = MagicMock(return_value=mock_expect_page)

            mock_manager.get_page = AsyncMock(return_value=mock_page)

            await show_preview(session, "n1234567890ab")

            # Verify navigation to the edit page on editor.note.com
            mock_page.goto.assert_called_once()
            call_args = mock_page.goto.call_args[0][0]
            assert call_args == "https://editor.note.com/notes/n1234567890ab/edit/"

            # Verify menu button was clicked
            mock_menu_button.click.assert_called_once()

            # Verify preview button was clicked
            mock_preview_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_preview_uses_article_key(self) -> None:
        """Test that preview uses the article key in URL."""
        session = create_mock_session()

        with patch("note_mcp.browser.preview.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            # Mock the page object with all required methods
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.wait_for_load_state = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()

            # Mock the locator for menu button
            mock_menu_button = AsyncMock()
            mock_menu_button.click = AsyncMock()

            # Mock the locator for preview button
            mock_preview_button = AsyncMock()
            mock_preview_button.click = AsyncMock()

            # Mock page.locator to return appropriate mocks
            def locator_side_effect(selector: str, **kwargs: object) -> AsyncMock:
                if 'aria-label="その他"' in selector:
                    return mock_menu_button
                else:
                    return mock_preview_button

            mock_page.locator = MagicMock(side_effect=locator_side_effect)

            # Mock context for new page handling
            mock_new_page = AsyncMock()
            mock_new_page.wait_for_load_state = AsyncMock()
            mock_new_page.bring_to_front = AsyncMock()

            mock_context = MagicMock()
            mock_context.add_cookies = AsyncMock()
            mock_page.context = mock_context

            # Create async context manager for expect_page
            # The value property needs to be awaitable
            async def get_new_page() -> AsyncMock:
                return mock_new_page

            mock_expect_page = MagicMock()
            mock_expect_page.__aenter__ = AsyncMock(return_value=mock_expect_page)
            mock_expect_page.__aexit__ = AsyncMock(return_value=None)
            mock_expect_page.value = get_new_page()  # Returns coroutine
            mock_context.expect_page = MagicMock(return_value=mock_expect_page)

            mock_manager.get_page = AsyncMock(return_value=mock_page)

            await show_preview(session, "article123")

            call_args = mock_page.goto.call_args[0][0]
            assert "article123" in call_args
            assert call_args == "https://editor.note.com/notes/article123/edit/"


class TestListArticles:
    """Tests for list_articles function."""

    @pytest.mark.asyncio
    async def test_list_articles_success(self) -> None:
        """Test successful article listing."""
        session = create_mock_session()

        # Mock response matches /v2/creators/{username}/contents API structure
        mock_response = {
            "data": {
                "contents": [
                    {
                        "id": "123",
                        "key": "n123",
                        "name": "Article 1",
                        "status": "published",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-02T00:00:00Z",
                        "noteUrl": "https://note.com/testuser/n/n123",
                    },
                    {
                        "id": "456",
                        "key": "n456",
                        "name": "Article 2",
                        "status": "draft",
                        "createdAt": "2024-01-03T00:00:00Z",
                        "updatedAt": "2024-01-04T00:00:00Z",
                        "noteUrl": "https://note.com/testuser/n/n456",
                    },
                ],
                "totalCount": 2,
                "isLastPage": True,
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await list_articles(session)

            assert len(result.articles) == 2
            assert result.total == 2
            assert result.articles[0].id == "123"
            assert result.articles[0].title == "Article 1"
            assert result.articles[1].id == "456"
            assert result.articles[1].status == ArticleStatus.DRAFT

    @pytest.mark.asyncio
    async def test_list_articles_with_status_filter(self) -> None:
        """Test listing articles with status filter."""
        session = create_mock_session()

        # Mock response matches /v2/creators/{username}/contents API structure
        mock_response = {
            "data": {
                "contents": [
                    {
                        "id": "123",
                        "key": "n123",
                        "name": "Draft Article",
                        "status": "draft",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-02T00:00:00Z",
                    }
                ],
                "totalCount": 1,
                "isLastPage": True,
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await list_articles(session, status=ArticleStatus.DRAFT)

            assert len(result.articles) == 1
            assert result.articles[0].status == ArticleStatus.DRAFT

    @pytest.mark.asyncio
    async def test_list_articles_pagination(self) -> None:
        """Test listing articles with pagination."""
        session = create_mock_session()

        # Mock response matches /v2/creators/{username}/contents API structure
        mock_response = {
            "data": {
                "contents": [
                    {
                        "id": "789",
                        "key": "n789",
                        "name": "Page 2 Article",
                        "status": "published",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-02T00:00:00Z",
                    }
                ],
                "totalCount": 11,
                "isLastPage": False,
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await list_articles(session, page=2, limit=10)

            assert result.page == 2
            assert result.has_more is True
            assert result.total == 11


class TestPublishArticle:
    """Tests for publish_article function."""

    @pytest.mark.asyncio
    async def test_publish_existing_draft(self) -> None:
        """Test publishing an existing draft article."""
        session = create_mock_session()

        mock_response = {
            "data": {
                "id": "123456",
                "key": "n1234567890ab",
                "name": "Published Article",
                "body": "<p>Content</p>",
                "status": "published",
                "hashtags": [],
                "noteUrl": "https://note.com/testuser/n/n1234567890ab",
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            article = await publish_article(session, article_id="123456")

            assert article.id == "123456"
            assert article.status == ArticleStatus.PUBLISHED
            assert article.url == "https://note.com/testuser/n/n1234567890ab"

    @pytest.mark.asyncio
    async def test_publish_new_article(self) -> None:
        """Test publishing a new article directly."""
        session = create_mock_session()
        article_input = ArticleInput(
            title="New Published Article",
            body="# Hello\n\nContent here.",
            tags=["test"],
        )

        mock_response = {
            "data": {
                "id": "789",
                "key": "n789",
                "name": "New Published Article",
                "body": "<h1>Hello</h1>\n<p>Content here.</p>\n",
                "status": "published",
                "hashtags": [{"hashtag": {"name": "test"}}],
                "noteUrl": "https://note.com/testuser/n/n789",
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            article = await publish_article(session, article_input=article_input)

            assert article.id == "789"
            assert article.status == ArticleStatus.PUBLISHED
            assert "test" in article.tags

    @pytest.mark.asyncio
    async def test_publish_requires_id_or_input(self) -> None:
        """Test that publish_article requires either article_id or article_input."""
        session = create_mock_session()

        with pytest.raises(ValueError) as exc_info:
            await publish_article(session)

        assert "article_id" in str(exc_info.value) or "article_input" in str(exc_info.value)
