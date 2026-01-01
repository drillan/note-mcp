"""Unit tests for insert_embed module.

Tests URL pattern matching and service identification for embed functionality.
"""

from __future__ import annotations

import pytest

from note_mcp.browser.insert_embed import (
    NOTE_PATTERN,
    TWITTER_PATTERN,
    YOUTUBE_PATTERN,
    get_embed_service,
    is_supported_embed_url,
)


class TestYouTubePattern:
    """Tests for YouTube URL pattern matching."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://youtube.com/watch?v=abc123XYZ",
            "https://youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/abc-123_XYZ",
        ],
    )
    def test_valid_youtube_urls(self, url: str) -> None:
        """Valid YouTube URLs should match the pattern."""
        assert YOUTUBE_PATTERN.match(url) is not None

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/channel/UC123",
            "https://www.youtube.com/playlist?list=PL123",
            "https://www.youtube.com/",
            "https://youtu.be/",
            "https://vimeo.com/123456",
            "https://example.com/watch?v=123",
            "youtube.com/watch?v=123",  # Missing protocol
        ],
    )
    def test_invalid_youtube_urls(self, url: str) -> None:
        """Invalid YouTube URLs should not match the pattern."""
        assert YOUTUBE_PATTERN.match(url) is None


class TestTwitterPattern:
    """Tests for Twitter/X URL pattern matching."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://twitter.com/user/status/1234567890",
            "https://www.twitter.com/user/status/1234567890",
            "http://twitter.com/username123/status/9876543210",
            "https://x.com/user/status/1234567890",
            "https://www.x.com/user/status/1234567890",
            "http://x.com/user/status/1234567890",
        ],
    )
    def test_valid_twitter_urls(self, url: str) -> None:
        """Valid Twitter/X URLs should match the pattern."""
        assert TWITTER_PATTERN.match(url) is not None

    @pytest.mark.parametrize(
        "url",
        [
            "https://twitter.com/user",
            "https://twitter.com/user/likes",
            "https://twitter.com/",
            "https://x.com/",
            "https://x.com/user",
            "https://facebook.com/user/status/123",
            "twitter.com/user/status/123",  # Missing protocol
        ],
    )
    def test_invalid_twitter_urls(self, url: str) -> None:
        """Invalid Twitter/X URLs should not match the pattern."""
        assert TWITTER_PATTERN.match(url) is None


class TestNotePattern:
    """Tests for note.com URL pattern matching."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://note.com/username/n/n1234567890ab",
            "http://note.com/user123/n/nabc123def456",
            "https://note.com/user_name/n/n12345",
        ],
    )
    def test_valid_note_urls(self, url: str) -> None:
        """Valid note.com article URLs should match the pattern."""
        assert NOTE_PATTERN.match(url) is not None

    @pytest.mark.parametrize(
        "url",
        [
            "https://note.com/username",
            "https://note.com/username/m/m123",  # Magazine, not article
            "https://note.com/",
            "https://note.mu/user/n/n123",  # Old domain
            "https://example.com/user/n/n123",
            "note.com/user/n/n123",  # Missing protocol
        ],
    )
    def test_invalid_note_urls(self, url: str) -> None:
        """Invalid note.com URLs should not match the pattern."""
        assert NOTE_PATTERN.match(url) is None


class TestIsSupportedEmbedUrl:
    """Tests for is_supported_embed_url function."""

    @pytest.mark.parametrize(
        "url",
        [
            # YouTube
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            # Twitter/X
            "https://twitter.com/user/status/1234567890",
            "https://x.com/user/status/1234567890",
            # note.com
            "https://note.com/username/n/n1234567890ab",
        ],
    )
    def test_supported_urls_return_true(self, url: str) -> None:
        """Supported embed URLs should return True."""
        assert is_supported_embed_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/page",
            "https://github.com/user/repo",
            "https://vimeo.com/123456",
            "https://facebook.com/post/123",
            "https://instagram.com/p/abc123",
            "https://www.google.com",
            "",
            "not a url",
        ],
    )
    def test_unsupported_urls_return_false(self, url: str) -> None:
        """Unsupported URLs should return False."""
        assert is_supported_embed_url(url) is False


class TestGetEmbedService:
    """Tests for get_embed_service function."""

    @pytest.mark.parametrize(
        ("url", "expected_service"),
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
            ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
            ("https://twitter.com/user/status/1234567890", "twitter"),
            ("https://x.com/user/status/1234567890", "twitter"),
            ("https://note.com/username/n/n1234567890ab", "note"),
        ],
    )
    def test_returns_correct_service_name(self, url: str, expected_service: str) -> None:
        """Should return correct service name for supported URLs."""
        assert get_embed_service(url) == expected_service

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/page",
            "https://vimeo.com/123456",
            "",
            "not a url",
        ],
    )
    def test_returns_none_for_unsupported_urls(self, url: str) -> None:
        """Should return None for unsupported URLs."""
        assert get_embed_service(url) is None
