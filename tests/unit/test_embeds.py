"""Unit tests for embed API functions.

Tests for api/embeds.py module which provides embed URL detection,
service identification, and HTML generation for note.com embeds.
"""

from __future__ import annotations

import re
import uuid

import pytest


class TestGetEmbedService:
    """Tests for get_embed_service function."""

    def test_youtube_watch_url(self) -> None:
        """Test YouTube watch URL detection."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
        assert get_embed_service("https://youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
        assert get_embed_service("http://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"

    def test_youtube_short_url(self) -> None:
        """Test YouTube short URL (youtu.be) detection."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://youtu.be/dQw4w9WgXcQ") == "youtube"
        assert get_embed_service("http://youtu.be/dQw4w9WgXcQ") == "youtube"

    def test_twitter_url(self) -> None:
        """Test Twitter URL detection."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://twitter.com/user/status/1234567890") == "twitter"
        assert get_embed_service("https://www.twitter.com/user/status/1234567890") == "twitter"

    def test_x_url(self) -> None:
        """Test X (Twitter rebrand) URL detection."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://x.com/user/status/1234567890") == "twitter"
        assert get_embed_service("https://www.x.com/user/status/1234567890") == "twitter"

    def test_note_url(self) -> None:
        """Test note.com article URL detection."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://note.com/username/n/n1234567890ab") == "note"
        assert get_embed_service("http://note.com/username/n/n1234567890ab") == "note"

    def test_unsupported_url_returns_none(self) -> None:
        """Test that unsupported URLs return None."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://example.com") is None
        assert get_embed_service("https://google.com") is None
        assert get_embed_service("https://vimeo.com/123456") is None
        assert get_embed_service("not a url") is None


class TestIsEmbedUrl:
    """Tests for is_embed_url function."""

    def test_youtube_urls_are_embed_urls(self) -> None:
        """Test that YouTube URLs are recognized as embed URLs."""
        from note_mcp.api.embeds import is_embed_url

        assert is_embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
        assert is_embed_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_twitter_urls_are_embed_urls(self) -> None:
        """Test that Twitter/X URLs are recognized as embed URLs."""
        from note_mcp.api.embeds import is_embed_url

        assert is_embed_url("https://twitter.com/user/status/1234567890") is True
        assert is_embed_url("https://x.com/user/status/1234567890") is True

    def test_note_urls_are_embed_urls(self) -> None:
        """Test that note.com article URLs are recognized as embed URLs."""
        from note_mcp.api.embeds import is_embed_url

        assert is_embed_url("https://note.com/username/n/n1234567890ab") is True

    def test_unsupported_urls_are_not_embed_urls(self) -> None:
        """Test that unsupported URLs are not recognized as embed URLs."""
        from note_mcp.api.embeds import is_embed_url

        assert is_embed_url("https://example.com") is False
        assert is_embed_url("https://google.com") is False
        assert is_embed_url("not a url") is False


class TestGenerateEmbedHtml:
    """Tests for generate_embed_html function."""

    def test_youtube_embed_structure(self) -> None:
        """Test YouTube embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        html = generate_embed_html(url)

        # Verify required attributes
        assert "<figure" in html
        assert 'data-src="https://www.youtube.com/watch?v=dQw4w9WgXcQ"' in html
        assert 'embedded-service="youtube"' in html
        assert 'contenteditable="false"' in html
        assert "embedded-content-key=" in html
        assert "</figure>" in html

    def test_twitter_embed_structure(self) -> None:
        """Test Twitter embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://twitter.com/user/status/1234567890"
        html = generate_embed_html(url, service="twitter")

        assert 'embedded-service="twitter"' in html
        assert f'data-src="{url}"' in html

    def test_note_embed_structure(self) -> None:
        """Test note.com embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://note.com/username/n/n1234567890ab"
        html = generate_embed_html(url, service="note")

        assert 'embedded-service="note"' in html
        assert f'data-src="{url}"' in html

    def test_embed_key_format(self) -> None:
        """Test that embed content key has correct format (emb + 13 hex chars)."""
        from note_mcp.api.embeds import generate_embed_html

        html = generate_embed_html("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # Extract embedded-content-key value
        match = re.search(r'embedded-content-key="(emb[a-f0-9]+)"', html)
        assert match is not None
        key = match.group(1)
        assert key.startswith("emb")
        assert len(key) == 16  # "emb" + 13 chars

    def test_uuid_attributes(self) -> None:
        """Test that name and id attributes are valid UUIDs."""
        from note_mcp.api.embeds import generate_embed_html

        html = generate_embed_html("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # Extract name/id values
        name_match = re.search(r'name="([^"]+)"', html)
        id_match = re.search(r'id="([^"]+)"', html)

        assert name_match is not None
        assert id_match is not None

        # Verify they are valid UUIDs
        name_uuid = uuid.UUID(name_match.group(1))
        id_uuid = uuid.UUID(id_match.group(1))

        assert name_uuid == id_uuid  # Should be the same

    def test_auto_detect_service(self) -> None:
        """Test that service is auto-detected when not provided."""
        from note_mcp.api.embeds import generate_embed_html

        # YouTube
        html = generate_embed_html("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert 'embedded-service="youtube"' in html

        # Twitter
        html = generate_embed_html("https://twitter.com/user/status/123")
        assert 'embedded-service="twitter"' in html

        # note.com
        html = generate_embed_html("https://note.com/user/n/n123")
        assert 'embedded-service="note"' in html

    def test_url_escaping(self) -> None:
        """Test that special characters in URL are properly escaped."""
        from note_mcp.api.embeds import generate_embed_html

        url = 'https://www.youtube.com/watch?v=test&feature=share"<script>'
        html = generate_embed_html(url, service="youtube")

        # HTML special characters should be escaped
        assert "&amp;" in html or "feature=share" in html
        assert '"<script>' not in html  # Should be escaped

    def test_unsupported_url_raises_error(self) -> None:
        """Test that unsupported URL raises ValueError."""
        from note_mcp.api.embeds import generate_embed_html

        with pytest.raises(ValueError, match="Unsupported embed URL"):
            generate_embed_html("https://example.com")


class TestEmbedPatterns:
    """Tests for embed URL pattern constants."""

    def test_youtube_pattern_exports(self) -> None:
        """Test that YOUTUBE_PATTERN is exported."""
        from note_mcp.api.embeds import YOUTUBE_PATTERN

        assert YOUTUBE_PATTERN.match("https://www.youtube.com/watch?v=abc123")
        assert YOUTUBE_PATTERN.match("https://youtu.be/abc123")
        assert not YOUTUBE_PATTERN.match("https://youtube.com/channel/abc")

    def test_twitter_pattern_exports(self) -> None:
        """Test that TWITTER_PATTERN is exported."""
        from note_mcp.api.embeds import TWITTER_PATTERN

        assert TWITTER_PATTERN.match("https://twitter.com/user/status/123")
        assert TWITTER_PATTERN.match("https://x.com/user/status/123")
        assert not TWITTER_PATTERN.match("https://twitter.com/user")

    def test_note_pattern_exports(self) -> None:
        """Test that NOTE_PATTERN is exported."""
        from note_mcp.api.embeds import NOTE_PATTERN

        assert NOTE_PATTERN.match("https://note.com/user/n/nabc123")
        assert not NOTE_PATTERN.match("https://note.com/user")


class TestFetchEmbedKey:
    """Tests for fetch_embed_key function."""

    @pytest.mark.asyncio
    async def test_fetch_youtube_embed_key(self) -> None:
        """Test fetching embed key for YouTube URL."""
        import time
        from unittest.mock import AsyncMock, patch

        from note_mcp.api.embeds import fetch_embed_key
        from note_mcp.models import Session

        # Mock session with all required fields
        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        # Mock API response
        mock_response = {
            "data": {
                "key": "emb0076d44f4f7f",
                "html_for_embed": '<span><iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe></span>',
            }
        }

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            embed_key, html_for_embed = await fetch_embed_key(
                session,
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "n1234567890ab",
            )

            assert embed_key == "emb0076d44f4f7f"
            assert "iframe" in html_for_embed

            # Verify API call parameters
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "/v2/embed_by_external_api" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_fetch_twitter_embed_key(self) -> None:
        """Test fetching embed key for Twitter URL."""
        import time
        from unittest.mock import AsyncMock, patch

        from note_mcp.api.embeds import fetch_embed_key
        from note_mcp.models import Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        mock_response = {
            "data": {
                "key": "emb1234567890abc",
                "html_for_embed": "<span><blockquote>Tweet content</blockquote></span>",
            }
        }

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            embed_key, html_for_embed = await fetch_embed_key(
                session,
                "https://twitter.com/user/status/1234567890",
                "n1234567890ab",
            )

            assert embed_key == "emb1234567890abc"
            assert "blockquote" in html_for_embed

    @pytest.mark.asyncio
    async def test_fetch_embed_key_unsupported_url(self) -> None:
        """Test that unsupported URL raises ValueError."""
        import time

        from note_mcp.api.embeds import fetch_embed_key
        from note_mcp.models import Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        with pytest.raises(ValueError, match="Unsupported embed URL"):
            await fetch_embed_key(session, "https://example.com", "n1234567890ab")

    @pytest.mark.asyncio
    async def test_fetch_embed_key_api_error(self) -> None:
        """Test handling of API errors."""
        import time
        from unittest.mock import AsyncMock, patch

        from note_mcp.api.embeds import fetch_embed_key
        from note_mcp.models import ErrorCode, NoteAPIError, Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="API request failed",
            )
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(NoteAPIError):
                await fetch_embed_key(
                    session,
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "n1234567890ab",
                )

    @pytest.mark.asyncio
    async def test_fetch_embed_key_empty_response(self) -> None:
        """Test handling of empty API response."""
        import time
        from unittest.mock import AsyncMock, patch

        from note_mcp.api.embeds import fetch_embed_key
        from note_mcp.models import NoteAPIError, Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        mock_response: dict[str, dict[str, str]] = {"data": {}}

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(NoteAPIError, match="empty response"):
                await fetch_embed_key(
                    session,
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "n1234567890ab",
                )


class TestResolveEmbedKeys:
    """Tests for resolve_embed_keys function."""

    @pytest.mark.asyncio
    async def test_resolve_single_youtube_embed(self) -> None:
        """Test resolving a single YouTube embed key."""
        import time
        from unittest.mock import patch

        from note_mcp.api.embeds import resolve_embed_keys
        from note_mcp.models import Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        # HTML with random embed key
        html_body = (
            '<p name="p1" id="p1">Hello</p>'
            '<figure name="fig1" id="fig1" '
            'data-src="https://www.youtube.com/watch?v=dQw4w9WgXcQ" '
            'embedded-service="youtube" '
            'embedded-content-key="embrandomkey1234" '
            'contenteditable="false"></figure>'
        )

        # Mock fetch_embed_key to return a server key
        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            mock_fetch.return_value = ("emb0076d44f4f7f", "<iframe>...</iframe>")

            result = await resolve_embed_keys(session, html_body, "n1234567890ab")

            # Verify the key was replaced
            assert 'embedded-content-key="emb0076d44f4f7f"' in result
            assert 'embedded-content-key="embrandomkey1234"' not in result
            mock_fetch.assert_called_once_with(
                session,
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "n1234567890ab",
            )

    @pytest.mark.asyncio
    async def test_resolve_multiple_embeds(self) -> None:
        """Test resolving multiple embed keys."""
        import time
        from unittest.mock import patch

        from note_mcp.api.embeds import resolve_embed_keys
        from note_mcp.models import Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        html_body = (
            '<figure name="fig1" id="fig1" '
            'data-src="https://www.youtube.com/watch?v=video1" '
            'embedded-service="youtube" '
            'embedded-content-key="embrandom1" '
            'contenteditable="false"></figure>'
            '<p name="p1" id="p1">Between embeds</p>'
            '<figure name="fig2" id="fig2" '
            'data-src="https://twitter.com/user/status/123" '
            'embedded-service="twitter" '
            'embedded-content-key="embrandom2" '
            'contenteditable="false"></figure>'
        )

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            # Return different keys for different URLs
            mock_fetch.side_effect = [
                ("embserver1", "<iframe>yt</iframe>"),
                ("embserver2", "<blockquote>tw</blockquote>"),
            ]

            result = await resolve_embed_keys(session, html_body, "n1234567890ab")

            assert 'embedded-content-key="embserver1"' in result
            assert 'embedded-content-key="embserver2"' in result
            assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_no_embeds_returns_unchanged(self) -> None:
        """Test that HTML without embeds is returned unchanged."""
        import time
        from unittest.mock import patch

        from note_mcp.api.embeds import resolve_embed_keys
        from note_mcp.models import Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        html_body = '<p name="p1" id="p1">Just text, no embeds</p>'

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            result = await resolve_embed_keys(session, html_body, "n1234567890ab")

            assert result == html_body
            mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_server_registered_keys(self) -> None:
        """Test that already server-registered keys are not re-fetched."""
        import time
        from unittest.mock import patch

        from note_mcp.api.embeds import resolve_embed_keys
        from note_mcp.models import Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        # HTML with a key that looks like it was already fetched from server
        # (We can't actually distinguish, so all keys get processed)
        html_body = (
            '<figure name="fig1" id="fig1" '
            'data-src="https://www.youtube.com/watch?v=video1" '
            'embedded-service="youtube" '
            'embedded-content-key="embrandomkey123" '
            'contenteditable="false"></figure>'
        )

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            mock_fetch.return_value = ("embserverkey456", "<iframe>...</iframe>")

            result = await resolve_embed_keys(session, html_body, "n1234567890ab")

            # Key should be updated regardless
            assert 'embedded-content-key="embserverkey456"' in result

    @pytest.mark.asyncio
    async def test_api_error_propagates(self) -> None:
        """Test that API errors are propagated."""
        import time
        from unittest.mock import patch

        from note_mcp.api.embeds import resolve_embed_keys
        from note_mcp.models import ErrorCode, NoteAPIError, Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        html_body = (
            '<figure name="fig1" id="fig1" '
            'data-src="https://www.youtube.com/watch?v=video1" '
            'embedded-service="youtube" '
            'embedded-content-key="embrandom1" '
            'contenteditable="false"></figure>'
        )

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            mock_fetch.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="API request failed",
            )

            with pytest.raises(NoteAPIError):
                await resolve_embed_keys(session, html_body, "n1234567890ab")
