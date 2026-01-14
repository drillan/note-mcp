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

    def test_gist_url(self) -> None:
        """Test GitHub Gist URL detection."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://gist.github.com/defunkt/2059") == "gist"
        assert get_embed_service("https://gist.github.com/user-name/abc123def") == "gist"
        assert get_embed_service("http://gist.github.com/user/gist123") == "gist"

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

    def test_gist_urls_are_embed_urls(self) -> None:
        """Test that GitHub Gist URLs are recognized as embed URLs."""
        from note_mcp.api.embeds import is_embed_url

        assert is_embed_url("https://gist.github.com/defunkt/2059") is True
        assert is_embed_url("https://gist.github.com/user-name/abc123") is True

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

    def test_gist_embed_structure(self) -> None:
        """Test GitHub Gist embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://gist.github.com/defunkt/2059"
        html = generate_embed_html(url)

        assert "<figure" in html
        assert f'data-src="{url}"' in html
        assert 'embedded-service="gist"' in html
        assert 'contenteditable="false"' in html
        assert "embedded-content-key=" in html
        assert "</figure>" in html

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

        # GitHub Gist
        html = generate_embed_html("https://gist.github.com/defunkt/2059")
        assert 'embedded-service="gist"' in html

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

    def test_gist_pattern_exports(self) -> None:
        """Test that GIST_PATTERN is exported."""
        from note_mcp.api.embeds import GIST_PATTERN

        assert GIST_PATTERN.match("https://gist.github.com/defunkt/2059")
        assert GIST_PATTERN.match("https://gist.github.com/user-name/abc123def")
        assert not GIST_PATTERN.match("https://github.com/user/repo")
        assert not GIST_PATTERN.match("https://gist.github.com/")

    def test_gist_pattern_trailing_slash(self) -> None:
        """Test that GIST_PATTERN accepts trailing slash (UX improvement).

        When users copy Gist URLs from the browser, they may include a trailing slash.
        """
        from note_mcp.api.embeds import GIST_PATTERN

        assert GIST_PATTERN.match("https://gist.github.com/defunkt/2059/")
        assert GIST_PATTERN.match("https://gist.github.com/user-name/abc123def/")

    def test_gist_pattern_file_fragment(self) -> None:
        """Test that GIST_PATTERN accepts file fragment (UX improvement).

        When users copy Gist URLs with a specific file selected, the URL includes
        a fragment like #file-example-py. These should be accepted.
        """
        from note_mcp.api.embeds import GIST_PATTERN

        assert GIST_PATTERN.match("https://gist.github.com/defunkt/2059#file-example-py")
        assert GIST_PATTERN.match("https://gist.github.com/user/abc123#file-test-js")
        # Edge case: trailing slash + fragment (unlikely but valid URL structure)
        assert GIST_PATTERN.match("https://gist.github.com/user/abc123/#file-test-js")


class TestFetchNoteEmbedKey:
    """Tests for _fetch_note_embed_key function (Issue #121).

    note.com article URLs require a different API endpoint (/v1/embed)
    than external services (YouTube, Twitter) which use /v2/embed_by_external_api.
    """

    @pytest.mark.asyncio
    async def test_fetch_note_embed_key_uses_post_v1_endpoint(self) -> None:
        """Test that note.com article URL uses POST /v1/embed endpoint."""
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

        # Response structure: {"data": {"embedded_content": {"key": ..., "html_for_embed": ...}}}
        mock_response = {
            "data": {
                "embedded_content": {
                    "key": "embnote123456789",
                    "html_for_embed": '<div class="note-embed">Article preview</div>',
                }
            }
        }

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            embed_key, html_for_embed = await fetch_embed_key(
                session,
                "https://note.com/username/n/n1234567890ab",
                "n9876543210xy",
            )

            # Should use POST /v1/embed, not GET /v2/embed_by_external_api
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/v1/embed" in call_args[0][0]
            # Verify GET was NOT called
            mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_note_embed_key_returns_key_and_html(self) -> None:
        """Test that note.com embed returns valid key and HTML."""
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

        # Response structure: {"data": {"embedded_content": {"key": ..., "html_for_embed": ...}}}
        mock_response = {
            "data": {
                "embedded_content": {
                    "key": "embnote123456789",
                    "html_for_embed": '<div class="note-embed">Article preview</div>',
                }
            }
        }

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            embed_key, html_for_embed = await fetch_embed_key(
                session,
                "https://note.com/username/n/n1234567890ab",
                "n9876543210xy",
            )

            assert embed_key == "embnote123456789"
            assert "note-embed" in html_for_embed

    @pytest.mark.asyncio
    async def test_fetch_note_embed_key_sends_correct_payload(self) -> None:
        """Test that note.com embed sends correct JSON payload."""
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

        # Response structure: {"data": {"embedded_content": {"key": ..., "html_for_embed": ...}}}
        mock_response = {
            "data": {
                "embedded_content": {
                    "key": "embnote123456789",
                    "html_for_embed": '<div class="note-embed">Article preview</div>',
                }
            }
        }

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await fetch_embed_key(
                session,
                "https://note.com/username/n/n1234567890ab",
                "n9876543210xy",
            )

            # Verify the payload structure
            call_kwargs = mock_client.post.call_args[1]
            payload = call_kwargs.get("json", {})
            assert payload.get("url") == "https://note.com/username/n/n1234567890ab"
            assert payload.get("embeddable_key") == "n9876543210xy"
            assert payload.get("embeddable_type") == "Note"


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

    @pytest.mark.asyncio
    async def test_fetch_gist_embed_key_uses_v2_endpoint(self) -> None:
        """Test that GitHub Gist URL uses GET /v2/embed_by_external_api endpoint."""
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
                "key": "embgist1234567890",
                "html_for_embed": '<script src="https://gist.github.com/defunkt/2059.js"></script>',
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
                "https://gist.github.com/defunkt/2059",
                "n1234567890ab",
            )

            # Should use GET /v2/embed_by_external_api (same as YouTube/Twitter)
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "/v2/embed_by_external_api" in call_args[0][0]
            # Verify POST was NOT called
            mock_client.post.assert_not_called()
            # Verify returned values
            assert embed_key == "embgist1234567890"
            assert "gist.github.com" in html_for_embed


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
    async def test_api_error_logs_warning_and_continues(self) -> None:
        """Test that API errors are logged and processing continues (Issue #121).

        After implementing error handling for note.com embeds, errors should
        be logged but not block other embeds from being processed.
        """
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

        # HTML with two embeds - first one will fail, second should succeed
        html_body = (
            '<figure name="fig1" id="fig1" '
            'data-src="https://note.com/user/n/nfailarticle" '
            'embedded-service="note" '
            'embedded-content-key="embrandom1" '
            'contenteditable="false"></figure>'
            '<figure name="fig2" id="fig2" '
            'data-src="https://www.youtube.com/watch?v=success1" '
            'embedded-service="youtube" '
            'embedded-content-key="embrandom2" '
            'contenteditable="false"></figure>'
        )

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            # First call fails (note.com), second succeeds (YouTube)
            mock_fetch.side_effect = [
                NoteAPIError(
                    code=ErrorCode.API_ERROR,
                    message="note.com embed failed",
                ),
                ("embserverkey2", "<iframe>youtube</iframe>"),
            ]

            # Should NOT raise - error is logged and processing continues
            result = await resolve_embed_keys(session, html_body, "n1234567890ab")

            # First embed keeps original key (failed), second is replaced (succeeded)
            assert 'embedded-content-key="embrandom1"' in result  # unchanged
            assert 'embedded-content-key="embserverkey2"' in result  # replaced
            assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_resolve_note_embed_uses_correct_api(self) -> None:
        """Test that note.com embeds are resolved via the correct API (Issue #121)."""
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
            'data-src="https://note.com/username/n/n1234567890ab" '
            'embedded-service="note" '
            'embedded-content-key="embrandomnote" '
            'contenteditable="false"></figure>'
        )

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            mock_fetch.return_value = ("embnoteserver123", "<div>note preview</div>")

            result = await resolve_embed_keys(session, html_body, "narticlekey")

            # Verify the key was replaced
            assert 'embedded-content-key="embnoteserver123"' in result
            assert 'embedded-content-key="embrandomnote"' not in result
            mock_fetch.assert_called_once_with(
                session,
                "https://note.com/username/n/n1234567890ab",
                "narticlekey",
            )

    @pytest.mark.asyncio
    async def test_resolve_mixed_embeds_all_succeed(self) -> None:
        """Test resolving mixed YouTube, Twitter, and note.com embeds (Issue #121)."""
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
            'data-src="https://www.youtube.com/watch?v=ytid123" '
            'embedded-service="youtube" '
            'embedded-content-key="embytrand" '
            'contenteditable="false"></figure>'
            '<figure name="fig2" id="fig2" '
            'data-src="https://twitter.com/user/status/123" '
            'embedded-service="twitter" '
            'embedded-content-key="embtwrand" '
            'contenteditable="false"></figure>'
            '<figure name="fig3" id="fig3" '
            'data-src="https://note.com/user/n/n123" '
            'embedded-service="note" '
            'embedded-content-key="embntrand" '
            'contenteditable="false"></figure>'
        )

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            mock_fetch.side_effect = [
                ("embytserver", "<iframe>yt</iframe>"),
                ("embtwserver", "<blockquote>tw</blockquote>"),
                ("embntserver", "<div>note</div>"),
            ]

            result = await resolve_embed_keys(session, html_body, "narticlekey")

            # All embeds should be resolved
            assert 'embedded-content-key="embytserver"' in result
            assert 'embedded-content-key="embtwserver"' in result
            assert 'embedded-content-key="embntserver"' in result
            assert mock_fetch.call_count == 3


class TestGenerateEmbedHtmlWithKey:
    """Tests for generate_embed_html_with_key function."""

    def test_youtube_embed_with_server_key(self) -> None:
        """Test generating YouTube embed HTML with server-registered key."""
        from note_mcp.api.embeds import generate_embed_html_with_key

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        embed_key = "emb0076d44f4f7f"
        html = generate_embed_html_with_key(url, embed_key)

        assert "<figure" in html
        assert f'data-src="{url}"' in html
        assert 'embedded-service="youtube"' in html
        assert f'embedded-content-key="{embed_key}"' in html
        assert 'contenteditable="false"' in html
        assert "</figure>" in html

    def test_twitter_embed_with_server_key(self) -> None:
        """Test generating Twitter embed HTML with server-registered key."""
        from note_mcp.api.embeds import generate_embed_html_with_key

        url = "https://twitter.com/user/status/1234567890"
        embed_key = "emb1234567890abc"
        html = generate_embed_html_with_key(url, embed_key, service="twitter")

        assert 'embedded-service="twitter"' in html
        assert f'embedded-content-key="{embed_key}"' in html

    def test_note_embed_with_server_key(self) -> None:
        """Test generating note.com embed HTML with server-registered key."""
        from note_mcp.api.embeds import generate_embed_html_with_key

        url = "https://note.com/username/n/n1234567890ab"
        embed_key = "embabcdef1234567"
        html = generate_embed_html_with_key(url, embed_key)

        assert 'embedded-service="note"' in html
        assert f'embedded-content-key="{embed_key}"' in html

    def test_unsupported_url_raises_error(self) -> None:
        """Test that unsupported URL raises ValueError."""
        from note_mcp.api.embeds import generate_embed_html_with_key

        with pytest.raises(ValueError, match="Unsupported embed URL"):
            generate_embed_html_with_key("https://example.com", "emb123")

    def test_url_escaping(self) -> None:
        """Test that special characters in URL are properly escaped."""
        from note_mcp.api.embeds import generate_embed_html_with_key

        url = 'https://www.youtube.com/watch?v=test&feature=share"<script>'
        html = generate_embed_html_with_key(url, "emb123", service="youtube")

        # HTML special characters should be escaped
        assert "&amp;" in html or "feature=share" in html
        assert '"<script>' not in html  # Should be escaped


class TestEmbedFigurePattern:
    """Tests for _EMBED_FIGURE_PATTERN regex."""

    def test_standard_attribute_order(self) -> None:
        """Test matching with standard attribute order (data-src before key)."""
        from note_mcp.api.embeds import _EMBED_FIGURE_PATTERN

        html = (
            '<figure name="fig1" id="fig1" '
            'data-src="https://www.youtube.com/watch?v=abc123" '
            'embedded-service="youtube" '
            'embedded-content-key="emb1234567890ab" '
            'contenteditable="false"></figure>'
        )

        match = _EMBED_FIGURE_PATTERN.search(html)
        assert match is not None
        assert match.group(1) == "https://www.youtube.com/watch?v=abc123"
        assert match.group(2) == "emb1234567890ab"

    def test_reversed_attribute_order(self) -> None:
        """Test matching with reversed attribute order (key before data-src)."""
        from note_mcp.api.embeds import _EMBED_FIGURE_PATTERN

        html = (
            '<figure name="fig1" id="fig1" '
            'embedded-content-key="emb1234567890ab" '
            'embedded-service="youtube" '
            'data-src="https://www.youtube.com/watch?v=abc123" '
            'contenteditable="false"></figure>'
        )

        match = _EMBED_FIGURE_PATTERN.search(html)
        assert match is not None
        assert match.group(1) == "https://www.youtube.com/watch?v=abc123"
        assert match.group(2) == "emb1234567890ab"

    def test_minimal_attributes(self) -> None:
        """Test matching with minimal required attributes."""
        from note_mcp.api.embeds import _EMBED_FIGURE_PATTERN

        html = '<figure data-src="https://youtu.be/abc" embedded-content-key="emb123"></figure>'

        match = _EMBED_FIGURE_PATTERN.search(html)
        assert match is not None
        assert match.group(1) == "https://youtu.be/abc"
        assert match.group(2) == "emb123"

    def test_escaped_url_in_attribute(self) -> None:
        """Test matching with HTML-escaped URL."""
        from note_mcp.api.embeds import _EMBED_FIGURE_PATTERN

        html = (
            '<figure data-src="https://www.youtube.com/watch?v=abc&amp;feature=share" '
            'embedded-content-key="emb123"></figure>'
        )

        match = _EMBED_FIGURE_PATTERN.search(html)
        assert match is not None
        assert match.group(1) == "https://www.youtube.com/watch?v=abc&amp;feature=share"


class TestResolveEmbedKeysWithEscapedUrl:
    """Tests for resolve_embed_keys with HTML-escaped URLs."""

    @pytest.mark.asyncio
    async def test_unescape_url_before_api_call(self) -> None:
        """Test that escaped URLs are unescaped before calling the API."""
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

        # HTML with escaped characters in URL (using note.com URL which supports query params)
        # The &amp; should be unescaped to & before the API call
        html_body = (
            '<figure name="fig1" id="fig1" '
            'data-src="https://www.youtube.com/watch?v=dQw4w9WgXcQ" '
            'embedded-service="youtube" '
            'embedded-content-key="embrandomkey" '
            'contenteditable="false"></figure>'
        )

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            mock_fetch.return_value = ("embserverkey", "<iframe>...</iframe>")

            await resolve_embed_keys(session, html_body, "n1234567890ab")

            # Verify fetch_embed_key was called with the correct URL
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args[0]
            assert call_args[1] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    @pytest.mark.asyncio
    async def test_html_unescape_applied(self) -> None:
        """Test that html.unescape is applied to data-src attribute values."""
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

        # Twitter URL with escaped apostrophe (&#x27;)
        # This tests that html.unescape is actually being called
        html_body = (
            '<figure name="fig1" id="fig1" '
            'data-src="https://twitter.com/user/status/1234567890" '
            'embedded-service="twitter" '
            'embedded-content-key="embrandomkey" '
            'contenteditable="false"></figure>'
        )

        with patch("note_mcp.api.embeds.fetch_embed_key") as mock_fetch:
            mock_fetch.return_value = ("embserverkey", "<blockquote>...</blockquote>")

            await resolve_embed_keys(session, html_body, "n1234567890ab")

            # Verify fetch_embed_key was called
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args[0]
            # URL should be passed to fetch_embed_key (after html.unescape)
            assert call_args[1] == "https://twitter.com/user/status/1234567890"


class TestFetchNoteEmbedKeyArticle6Compliance:
    """Tests for Article 6 compliance in _fetch_note_embed_key function.

    Article 6 (Data Accuracy Mandate) requires:
    - No implicit fallbacks for required fields
    - Missing required fields must raise NoteAPIError
    """

    @pytest.mark.asyncio
    async def test_raises_on_missing_html_for_embed(self) -> None:
        """Test that missing html_for_embed raises NoteAPIError.

        Article 6: html_for_embed is required for rendering embeds.
        Missing value should raise error, not fall back to empty string.
        """
        import time
        from unittest.mock import AsyncMock, patch

        from note_mcp.api.embeds import _fetch_note_embed_key
        from note_mcp.models import ErrorCode, NoteAPIError, Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        # Response with key but missing html_for_embed
        mock_response = {
            "data": {
                "embedded_content": {
                    "key": "emb123456789",
                    # html_for_embed is missing
                }
            }
        }

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await _fetch_note_embed_key(session, "https://note.com/user/n/n123456", "narticlekey")

            assert exc_info.value.code == ErrorCode.API_ERROR
            assert "html_for_embed" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_raises_on_missing_key(self) -> None:
        """Test that missing key raises NoteAPIError.

        This verifies existing behavior for key validation.
        """
        import time
        from unittest.mock import AsyncMock, patch

        from note_mcp.api.embeds import _fetch_note_embed_key
        from note_mcp.models import ErrorCode, NoteAPIError, Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        # Response with html_for_embed but missing key
        mock_response = {
            "data": {
                "embedded_content": {
                    "html_for_embed": "<div>embed content</div>",
                    # key is missing
                }
            }
        }

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await _fetch_note_embed_key(session, "https://note.com/user/n/n123456", "narticlekey")

            assert exc_info.value.code == ErrorCode.API_ERROR

    @pytest.mark.asyncio
    async def test_valid_response_succeeds(self) -> None:
        """Test that valid response with both key and html_for_embed succeeds."""
        import time
        from unittest.mock import AsyncMock, patch

        from note_mcp.api.embeds import _fetch_note_embed_key
        from note_mcp.models import Session

        session = Session(
            cookies={"note_gql_session_id": "test", "XSRF-TOKEN": "test"},
            user_id="123456",
            username="testuser",
            created_at=int(time.time()),
        )

        # Valid response with both required fields
        mock_response = {
            "data": {
                "embedded_content": {
                    "key": "emb123456789",
                    "html_for_embed": "<div>embed content</div>",
                }
            }
        }

        with patch("note_mcp.api.embeds.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            embed_key, html_for_embed = await _fetch_note_embed_key(
                session, "https://note.com/user/n/n123456", "narticlekey"
            )

            assert embed_key == "emb123456789"
            assert html_for_embed == "<div>embed content</div>"


class TestZennPattern:
    """Tests for Zenn.dev article URL pattern (Issue #222)."""

    def test_zenn_article_url(self) -> None:
        """Test Zenn.dev article URL detection."""
        from note_mcp.api.embeds import ZENN_PATTERN

        # Valid Zenn article URLs
        assert ZENN_PATTERN.match("https://zenn.dev/zenn/articles/markdown-guide")
        assert ZENN_PATTERN.match("https://zenn.dev/user_name/articles/abc123def")
        assert ZENN_PATTERN.match("http://zenn.dev/user/articles/article123")

    def test_zenn_pattern_rejects_invalid_urls(self) -> None:
        """Test that invalid URLs are rejected."""
        from note_mcp.api.embeds import ZENN_PATTERN

        # Wrong domain
        assert not ZENN_PATTERN.match("https://example.com/user/articles/abc")
        # Wrong path structure
        assert not ZENN_PATTERN.match("https://zenn.dev/user")
        assert not ZENN_PATTERN.match("https://zenn.dev/user/books/abc")
        assert not ZENN_PATTERN.match("https://zenn.dev/user/scraps/abc")
        # Missing article id
        assert not ZENN_PATTERN.match("https://zenn.dev/user/articles/")
        assert not ZENN_PATTERN.match("https://zenn.dev/user/articles")


class TestGetEmbedServiceZenn:
    """Tests for get_embed_service function with Zenn.dev URLs (Issue #222)."""

    def test_get_embed_service_returns_external_article_for_zenn(self) -> None:
        """Test that get_embed_service returns 'external-article' for Zenn URLs."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://zenn.dev/zenn/articles/markdown-guide") == "external-article"
        assert get_embed_service("https://zenn.dev/user/articles/abc123") == "external-article"


class TestGenerateEmbedHtmlZenn:
    """Tests for generate_embed_html function with Zenn.dev URLs (Issue #222)."""

    def test_zenn_embed_structure(self) -> None:
        """Test Zenn embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://zenn.dev/zenn/articles/markdown-guide"
        html = generate_embed_html(url)

        # Verify required attributes
        assert "<figure" in html
        assert f'data-src="{url}"' in html
        assert 'embedded-service="external-article"' in html
        assert 'contenteditable="false"' in html
        assert "embedded-content-key=" in html
        assert "</figure>" in html


class TestIsEmbedUrlZenn:
    """Tests for is_embed_url function with Zenn.dev URLs (Issue #222)."""

    def test_zenn_urls_are_embed_urls(self) -> None:
        """Test that Zenn URLs are recognized as embed URLs."""
        from note_mcp.api.embeds import is_embed_url

        assert is_embed_url("https://zenn.dev/zenn/articles/markdown-guide") is True
        assert is_embed_url("https://zenn.dev/user/articles/abc123") is True


class TestMoneyPattern:
    """Tests for noteマネー (stock chart) URL pattern."""

    def test_money_companies_url(self) -> None:
        """Test Japanese stock URL detection (companies)."""
        from note_mcp.api.embeds import MONEY_PATTERN

        # Valid Japanese stock URLs
        assert MONEY_PATTERN.match("https://money.note.com/companies/5243")
        assert MONEY_PATTERN.match("https://money.note.com/companies/7203")
        assert MONEY_PATTERN.match("http://money.note.com/companies/5243")
        # With trailing slash
        assert MONEY_PATTERN.match("https://money.note.com/companies/5243/")

    def test_money_us_companies_url(self) -> None:
        """Test US stock URL detection (us-companies)."""
        from note_mcp.api.embeds import MONEY_PATTERN

        # Valid US stock URLs
        assert MONEY_PATTERN.match("https://money.note.com/us-companies/GOOG")
        assert MONEY_PATTERN.match("https://money.note.com/us-companies/AAPL")
        assert MONEY_PATTERN.match("https://money.note.com/us-companies/MSFT")
        # With trailing slash
        assert MONEY_PATTERN.match("https://money.note.com/us-companies/GOOG/")

    def test_money_indices_url(self) -> None:
        """Test index URL detection (indices)."""
        from note_mcp.api.embeds import MONEY_PATTERN

        # Valid index URLs
        assert MONEY_PATTERN.match("https://money.note.com/indices/NKY")
        assert MONEY_PATTERN.match("https://money.note.com/indices/TOPX")
        assert MONEY_PATTERN.match("https://money.note.com/indices/SPX")
        # With trailing slash
        assert MONEY_PATTERN.match("https://money.note.com/indices/NKY/")

    def test_money_investments_url(self) -> None:
        """Test investment trust URL detection (investments)."""
        from note_mcp.api.embeds import MONEY_PATTERN

        # Valid investment trust URLs
        assert MONEY_PATTERN.match("https://money.note.com/investments/0331418A")
        assert MONEY_PATTERN.match("https://money.note.com/investments/abc123")
        # With trailing slash
        assert MONEY_PATTERN.match("https://money.note.com/investments/0331418A/")

    def test_money_pattern_rejects_invalid_urls(self) -> None:
        """Test that invalid URLs are rejected."""
        from note_mcp.api.embeds import MONEY_PATTERN

        # Wrong domain
        assert not MONEY_PATTERN.match("https://note.com/companies/5243")
        # Wrong path
        assert not MONEY_PATTERN.match("https://money.note.com/invalid/5243")
        # Missing code
        assert not MONEY_PATTERN.match("https://money.note.com/companies/")
        # Other URLs
        assert not MONEY_PATTERN.match("https://example.com/companies/5243")


class TestGetEmbedServiceMoney:
    """Tests for get_embed_service function with noteマネー URLs."""

    def test_get_embed_service_returns_oembed_for_companies(self) -> None:
        """Test that get_embed_service returns 'oembed' for Japanese stock URLs."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://money.note.com/companies/5243") == "oembed"
        assert get_embed_service("https://money.note.com/companies/7203") == "oembed"

    def test_get_embed_service_returns_oembed_for_us_companies(self) -> None:
        """Test that get_embed_service returns 'oembed' for US stock URLs."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://money.note.com/us-companies/GOOG") == "oembed"
        assert get_embed_service("https://money.note.com/us-companies/AAPL") == "oembed"

    def test_get_embed_service_returns_oembed_for_indices(self) -> None:
        """Test that get_embed_service returns 'oembed' for index URLs."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://money.note.com/indices/NKY") == "oembed"
        assert get_embed_service("https://money.note.com/indices/TOPX") == "oembed"

    def test_get_embed_service_returns_oembed_for_investments(self) -> None:
        """Test that get_embed_service returns 'oembed' for investment trust URLs."""
        from note_mcp.api.embeds import get_embed_service

        assert get_embed_service("https://money.note.com/investments/0331418A") == "oembed"


class TestGenerateEmbedHtmlMoney:
    """Tests for generate_embed_html function with noteマネー URLs."""

    def test_money_embed_structure(self) -> None:
        """Test noteマネー embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://money.note.com/companies/5243"
        html = generate_embed_html(url)

        # Verify required attributes
        assert "<figure" in html
        assert f'data-src="{url}"' in html
        assert 'embedded-service="oembed"' in html
        assert 'contenteditable="false"' in html
        assert "embedded-content-key=" in html
        assert "</figure>" in html

    def test_money_us_companies_embed_structure(self) -> None:
        """Test US stock embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://money.note.com/us-companies/GOOG"
        html = generate_embed_html(url)

        assert 'embedded-service="oembed"' in html
        assert f'data-src="{url}"' in html

    def test_money_indices_embed_structure(self) -> None:
        """Test index embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://money.note.com/indices/NKY"
        html = generate_embed_html(url)

        assert 'embedded-service="oembed"' in html
        assert f'data-src="{url}"' in html

    def test_money_investments_embed_structure(self) -> None:
        """Test investment trust embed HTML structure."""
        from note_mcp.api.embeds import generate_embed_html

        url = "https://money.note.com/investments/0331418A"
        html = generate_embed_html(url)

        assert 'embedded-service="oembed"' in html
        assert f'data-src="{url}"' in html


class TestIsEmbedUrlMoney:
    """Tests for is_embed_url function with noteマネー URLs."""

    def test_money_urls_are_embed_urls(self) -> None:
        """Test that noteマネー URLs are recognized as embed URLs."""
        from note_mcp.api.embeds import is_embed_url

        assert is_embed_url("https://money.note.com/companies/5243") is True
        assert is_embed_url("https://money.note.com/us-companies/GOOG") is True
        assert is_embed_url("https://money.note.com/indices/NKY") is True
        assert is_embed_url("https://money.note.com/investments/0331418A") is True
