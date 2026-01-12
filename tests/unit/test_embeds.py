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
