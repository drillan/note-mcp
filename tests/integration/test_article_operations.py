"""Integration tests for article operations."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.api.articles import create_draft, get_article, list_articles, publish_article, update_article
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
        """Test successful draft creation via API."""
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
                "hashtags": [{"hashtag": {"name": "test"}}, {"hashtag": {"name": "python"}}],
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
            # create_draft calls POST twice: /v1/text_notes and /v1/text_notes/draft_save
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_create_draft_converts_markdown_to_html(self) -> None:
        """Test that create_draft converts Markdown body to HTML."""
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

            # Verify that the API was called with HTML body
            call_args = mock_client.post.call_args
            assert call_args is not None
            _, kwargs = call_args
            payload = kwargs.get("json", {})
            # Body should be HTML, not Markdown
            assert "<strong>Bold</strong>" in payload.get("body", "")
            assert "<em>italic</em>" in payload.get("body", "")


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

        with (
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles._resolve_numeric_note_id") as mock_resolve,
            patch("note_mcp.api.articles.resolve_embed_keys") as mock_resolve_embeds,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            # Uses POST to draft_save endpoint
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.get = AsyncMock(return_value={"data": {"key": "n1234567890ab"}})
            mock_resolve.return_value = "123456"
            mock_resolve_embeds.return_value = "<p>Updated content</p>\n"

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

        with (
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles._resolve_numeric_note_id") as mock_resolve,
            patch("note_mcp.api.articles.resolve_embed_keys") as mock_resolve_embeds,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            # Uses POST to draft_save endpoint
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.get = AsyncMock(return_value={"data": {"key": "n1234567890ab"}})
            mock_resolve.return_value = "123456"
            mock_resolve_embeds.return_value = ""

            article = await update_article(session, "123456", article_input)

            assert article.title == "New Title Only"


class TestGetArticle:
    """Tests for get_article function."""

    @pytest.mark.asyncio
    async def test_get_article_success(self) -> None:
        """Test successful article retrieval via API."""
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

        with patch("note_mcp.api.articles.get_article_via_api") as mock_get:
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

        with patch("note_mcp.api.articles.get_article_via_api") as mock_get:
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

        with patch("note_mcp.api.articles.get_article_via_api") as mock_get:
            mock_get.return_value = mock_article

            article = await get_article(session, "789")

            assert isinstance(article, Article)
            assert article.title == "Test Title"
            assert article.status == ArticleStatus.DRAFT


class TestListArticles:
    """Tests for list_articles function."""

    @pytest.mark.asyncio
    async def test_list_articles_success(self) -> None:
        """Test successful article listing."""
        session = create_mock_session()

        # Mock response matches /v2/note_list/contents API structure
        mock_response = {
            "data": {
                "notes": [
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

        # Mock response matches /v2/note_list/contents API structure
        mock_response = {
            "data": {
                "notes": [
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

        # Mock response matches /v2/note_list/contents API structure
        mock_response = {
            "data": {
                "notes": [
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


class TestCreateDraftWithEmbeds:
    """Integration tests for create_draft with embed URL resolution."""

    @pytest.mark.asyncio
    async def test_create_draft_resolves_youtube_embed(self) -> None:
        """Test that create_draft resolves YouTube embed keys via API."""
        session = create_mock_session()
        article_input = ArticleInput(
            title="Article with YouTube",
            body="Check out this video:\n\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

        # Mock response for article creation
        mock_create_response = {
            "data": {
                "id": "123456",
                "key": "n1234567890ab",
                "name": "Article with YouTube",
                "body": "",
                "status": "draft",
                "hashtags": [],
            }
        }

        # Mock response for draft_save
        embed_html = (
            '<figure data-src="https://www.youtube.com/watch?v=dQw4w9WgXcQ" '
            'embedded-content-key="emb0076d44f4f7f"></figure>'
        )
        mock_save_response = {
            "data": {
                "id": "123456",
                "key": "n1234567890ab",
                "name": "Article with YouTube",
                "body": embed_html,
                "status": "draft",
                "hashtags": [],
            }
        }

        with (
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles.resolve_embed_keys") as mock_resolve_embeds,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            # Different responses for different endpoints
            def mock_post(endpoint: str, **kwargs: object) -> dict[str, Any]:
                if "/v1/text_notes/draft_save" in endpoint:
                    return mock_save_response
                return mock_create_response

            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_resolve_embeds.return_value = embed_html

            article = await create_draft(session, article_input)

            assert article.id == "123456"
            # Verify both create and draft_save were called
            assert mock_client.post.call_count == 2
            # Verify resolve_embed_keys was called with correct article_key
            mock_resolve_embeds.assert_called_once()
            call_args = mock_resolve_embeds.call_args[0]
            assert call_args[2] == "n1234567890ab"  # article_key

    @pytest.mark.asyncio
    async def test_create_draft_fails_without_article_key(self) -> None:
        """Test that create_draft raises error when API returns no article key."""
        from note_mcp.models import NoteAPIError

        session = create_mock_session()
        article_input = ArticleInput(
            title="Test Article",
            body="Content",
        )

        # Mock response missing the key field
        mock_response = {
            "data": {
                "id": "123456",
                # "key" is missing!
                "name": "Test Article",
                "status": "draft",
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(NoteAPIError, match="no article key"):
                await create_draft(session, article_input)

    @pytest.mark.asyncio
    async def test_create_draft_fails_without_article_id(self) -> None:
        """Test that create_draft raises error when API returns no article ID."""
        from note_mcp.models import NoteAPIError

        session = create_mock_session()
        article_input = ArticleInput(
            title="Test Article",
            body="Content",
        )

        # Mock response missing the id field
        mock_response = {
            "data": {
                # "id" is missing!
                "key": "n1234567890ab",
                "name": "Test Article",
                "status": "draft",
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(NoteAPIError, match="no article ID"):
                await create_draft(session, article_input)


class TestUpdateArticleWithEmbeds:
    """Integration tests for update_article with embed URL resolution."""

    @pytest.mark.asyncio
    async def test_update_article_resolves_embed_keys(self) -> None:
        """Test that update_article resolves embed keys for new embeds."""
        session = create_mock_session()
        article_input = ArticleInput(
            title="Updated with Twitter",
            body="Check this tweet:\n\nhttps://twitter.com/user/status/1234567890",
        )

        # Mock response for draft_save
        twitter_embed_html = (
            '<figure data-src="https://twitter.com/user/status/1234567890" '
            'embedded-content-key="emb1234567890abc"></figure>'
        )
        mock_save_response = {
            "data": {
                "id": "123456",
                "key": "n1234567890ab",
                "name": "Updated with Twitter",
                "body": twitter_embed_html,
                "status": "draft",
                "hashtags": [],
            }
        }

        with (
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles._resolve_numeric_note_id") as mock_resolve,
            patch("note_mcp.api.articles.resolve_embed_keys") as mock_resolve_embeds,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_save_response)
            mock_client.get = AsyncMock(return_value={"data": {"key": "n1234567890ab"}})

            mock_resolve.return_value = "123456"
            mock_resolve_embeds.return_value = twitter_embed_html

            article = await update_article(session, "123456", article_input)

            assert article.id == "123456"
            # Verify resolve_embed_keys was called
            mock_resolve_embeds.assert_called_once()
