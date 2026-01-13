"""Unit tests for update_article function.

Issue #146: Tests for the article ID resolution logic fix.
When numeric ID is passed to update_article without embeds,
it should not attempt to fetch the article key via API.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.models import ArticleInput, Session


def create_mock_session() -> Session:
    """Create a mock session for testing."""
    return Session(
        cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
        user_id="user123",
        username="testuser",
        expires_at=int(time.time()) + 3600,
        created_at=int(time.time()),
    )


class TestUpdateArticleIdResolution:
    """Tests for update_article ID resolution logic (Issue #146).

    The update_article function should:
    1. Not attempt to fetch article key when there are no embeds
    2. Only fetch article key when embeds need resolution
    3. Handle both numeric ID and key format inputs
    """

    @pytest.mark.asyncio
    async def test_update_article_with_numeric_id_no_embeds(self) -> None:
        """Numeric ID + no embeds → Should NOT call /v3/notes/ endpoint.

        This is the fix for Issue #146: when no embeds are present,
        there's no need to fetch the article key, avoiding the 400 error.
        """
        from note_mcp.api.articles import update_article

        session = create_mock_session()
        article_input = ArticleInput(
            title="Test Article",
            body="## Heading\n\nSimple text without embeds.",
        )

        mock_response: dict[str, Any] = {
            "data": {
                "id": 12345,
                "key": "n12345abcdef",
                "name": "Test Article",
                "body": "<h2>Heading</h2><p>Simple text without embeds.</p>",
                "publish_status": "draft",
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await update_article(session, "12345", article_input)

            # Should call draft_save (POST) once
            assert mock_client.post.call_count == 1
            post_call = mock_client.post.call_args
            assert "/v1/text_notes/draft_save" in post_call[0][0]
            assert "id=12345" in post_call[0][0]

            # Should NOT call /v3/notes/ (GET) to fetch article key
            # because there are no embeds to resolve
            mock_client.get.assert_not_called()

            assert result.id == "12345"

    @pytest.mark.asyncio
    async def test_update_article_with_key_no_embeds(self) -> None:
        """Key format + no embeds → Should NOT call /v3/notes/ endpoint.

        When article_id is already in key format and no embeds present,
        _resolve_numeric_note_id is called once, then draft_save is called.
        """
        from note_mcp.api.articles import update_article

        session = create_mock_session()
        article_input = ArticleInput(
            title="Test Article",
            body="Simple text without embeds.",
        )

        mock_post_response: dict[str, Any] = {
            "data": {
                "id": 12345,
                "key": "n12345abcdef",
                "name": "Test Article",
                "body": "<p>Simple text without embeds.</p>",
                "publish_status": "draft",
            }
        }

        with (
            patch("note_mcp.api.articles._resolve_numeric_note_id") as mock_resolve,
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
        ):
            mock_resolve.return_value = "12345"

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_post_response)
            mock_client_class.return_value = mock_client

            result = await update_article(session, "n12345abcdef", article_input)

            # _resolve_numeric_note_id should be called once
            mock_resolve.assert_called_once_with(session, "n12345abcdef")

            # Should call POST once for draft_save
            assert mock_client.post.call_count == 1

            assert result.key == "n12345abcdef"

    @pytest.mark.asyncio
    async def test_update_article_with_numeric_id_with_embeds(self) -> None:
        """Numeric ID + embeds → Should save twice (once to get key, once with resolved embeds).

        When numeric ID is provided and body contains embeds:
        1. First draft_save to get article key from response
        2. Use key to resolve embed keys
        3. Second draft_save with resolved embed HTML
        """
        from note_mcp.api.articles import update_article

        session = create_mock_session()
        # Body with YouTube embed URL that will be converted to embed figure
        article_input = ArticleInput(
            title="Test Article",
            body="Check this video:\n\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

        # First save response (to get key)
        mock_first_post_response: dict[str, Any] = {
            "data": {
                "id": 12345,
                "key": "n12345abcdef",
                "name": "Test Article",
                "body": "<p>Check this video:</p><figure ...>",
                "publish_status": "draft",
            }
        }

        # Second save response (with resolved embeds)
        mock_second_post_response: dict[str, Any] = {
            "data": {
                "id": 12345,
                "key": "n12345abcdef",
                "name": "Test Article",
                "body": "<p>Check this video:</p><figure embedded-content-key='resolved'>",
                "publish_status": "draft",
            }
        }

        with (
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles.resolve_embed_keys") as mock_resolve,
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[mock_first_post_response, mock_second_post_response])
            mock_client_class.return_value = mock_client

            # Mock resolve_embed_keys to return modified HTML
            mock_resolve.return_value = "<p>Check this video:</p><figure embedded-content-key='resolved'>"

            result = await update_article(session, "12345", article_input)

            # Should call POST twice (first to get key, second with resolved embeds)
            assert mock_client.post.call_count == 2

            # resolve_embed_keys should be called with the article key from first response
            mock_resolve.assert_called_once()
            resolve_call_args = mock_resolve.call_args[0]
            assert resolve_call_args[2] == "n12345abcdef"  # article_key

            # Should NOT call GET (no need to fetch article for numeric ID with embed flow)
            mock_client.get.assert_not_called()

            assert result.id == "12345"

    @pytest.mark.asyncio
    async def test_update_article_with_key_with_embeds(self) -> None:
        """Key format + embeds → Should save once (key already known for embed resolution).

        When article_id is already in key format and embeds are present:
        1. Use provided key directly for embed resolution
        2. Single draft_save with resolved embed HTML
        """
        from note_mcp.api.articles import update_article

        session = create_mock_session()
        # Body with YouTube embed URL
        article_input = ArticleInput(
            title="Test Article",
            body="Check this:\n\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

        mock_post_response: dict[str, Any] = {
            "data": {
                "id": 12345,
                "key": "n12345abcdef",
                "name": "Test Article",
                "body": "<p>Check this:</p><figure embedded-content-key='resolved'>",
                "publish_status": "draft",
            }
        }

        with (
            patch("note_mcp.api.articles._resolve_numeric_note_id") as mock_resolve_id,
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles.resolve_embed_keys") as mock_resolve_embeds,
        ):
            mock_resolve_id.return_value = "12345"

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_post_response)
            mock_client_class.return_value = mock_client

            mock_resolve_embeds.return_value = "<p>Check this:</p><figure embedded-content-key='resolved'>"

            result = await update_article(session, "n12345abcdef", article_input)

            # _resolve_numeric_note_id should be called once
            mock_resolve_id.assert_called_once_with(session, "n12345abcdef")

            # Should call POST only once (key already known for embed resolution)
            assert mock_client.post.call_count == 1

            # resolve_embed_keys should be called with the provided key directly
            mock_resolve_embeds.assert_called_once()
            resolve_call_args = mock_resolve_embeds.call_args[0]
            assert resolve_call_args[2] == "n12345abcdef"  # article_key

            assert result.key == "n12345abcdef"
