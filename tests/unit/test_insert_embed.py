"""Unit tests for insert_embed module.

Tests URL pattern matching and service identification for embed functionality.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Error as PlaywrightError

from note_mcp.api.embeds import (
    NOTE_PATTERN,
    TWITTER_PATTERN,
    YOUTUBE_PATTERN,
)
from note_mcp.browser.insert_embed import (
    EmbedResult,
    _wait_for_embed_insertion,
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


class TestEmbedResult:
    """Tests for EmbedResult enum."""

    def test_success_value(self) -> None:
        """SUCCESS should have value 'success'."""
        assert EmbedResult.SUCCESS.value == "success"

    def test_link_inserted_value(self) -> None:
        """LINK_INSERTED should have value 'link'."""
        assert EmbedResult.LINK_INSERTED.value == "link"

    def test_timeout_value(self) -> None:
        """TIMEOUT should have value 'timeout'."""
        assert EmbedResult.TIMEOUT.value == "timeout"

    def test_enum_members(self) -> None:
        """EmbedResult should have exactly 3 members."""
        assert len(EmbedResult) == 3

    def test_all_members_present(self) -> None:
        """All expected members should be present."""
        members = {member.name for member in EmbedResult}
        assert members == {"SUCCESS", "LINK_INSERTED", "TIMEOUT"}


class TestWaitForEmbedInsertion:
    """Tests for _wait_for_embed_insertion function."""

    @pytest.mark.asyncio
    async def test_returns_success_when_embed_count_increases(self) -> None:
        """Should return SUCCESS when embed card count increases."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"type": "success"})

        result = await _wait_for_embed_insertion(
            mock_page,
            initial_count=0,
            timeout=5000,
            url="https://www.youtube.com/watch?v=abc123",
        )

        assert result == EmbedResult.SUCCESS

    @pytest.mark.asyncio
    async def test_returns_link_inserted_when_link_detected(self) -> None:
        """Should return LINK_INSERTED when link is detected instead of embed."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"type": "link_inserted"})

        result = await _wait_for_embed_insertion(
            mock_page,
            initial_count=0,
            timeout=5000,
            url="https://twitter.com/user/status/deleted_tweet",
        )

        assert result == EmbedResult.LINK_INSERTED

    @pytest.mark.asyncio
    async def test_returns_timeout_when_no_change_detected(self) -> None:
        """Should return TIMEOUT when no change is detected."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"type": "timeout", "reason": "no_change_detected"})

        result = await _wait_for_embed_insertion(
            mock_page,
            initial_count=0,
            timeout=5000,
            url="https://www.youtube.com/watch?v=abc123",
        )

        assert result == EmbedResult.TIMEOUT

    @pytest.mark.asyncio
    async def test_returns_timeout_when_editor_not_found(self) -> None:
        """Should return TIMEOUT when editor element is not found."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"type": "timeout", "reason": "editor_not_found"})

        result = await _wait_for_embed_insertion(
            mock_page,
            initial_count=0,
            timeout=5000,
            url="https://www.youtube.com/watch?v=abc123",
        )

        assert result == EmbedResult.TIMEOUT

    @pytest.mark.asyncio
    async def test_returns_timeout_on_playwright_error(self) -> None:
        """Should return TIMEOUT on Playwright errors (connection issues, timeouts)."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(side_effect=PlaywrightError("Connection closed"))

        result = await _wait_for_embed_insertion(
            mock_page,
            initial_count=0,
            timeout=5000,
            url="https://www.youtube.com/watch?v=abc123",
        )

        assert result == EmbedResult.TIMEOUT

    @pytest.mark.asyncio
    async def test_raises_on_unexpected_error(self) -> None:
        """Should raise on unexpected errors (bugs in code)."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(side_effect=TypeError("Unexpected bug"))

        with pytest.raises(TypeError, match="Unexpected bug"):
            await _wait_for_embed_insertion(
                mock_page,
                initial_count=0,
                timeout=5000,
                url="https://www.youtube.com/watch?v=abc123",
            )

    @pytest.mark.asyncio
    async def test_returns_timeout_when_evaluate_returns_none(self) -> None:
        """Should return TIMEOUT when evaluate returns None."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        result = await _wait_for_embed_insertion(
            mock_page,
            initial_count=0,
            timeout=5000,
            url="https://www.youtube.com/watch?v=abc123",
        )

        assert result == EmbedResult.TIMEOUT

    @pytest.mark.asyncio
    async def test_handles_initial_link_exists_scenario(self) -> None:
        """Should not misdetect when link already existed before insertion attempt."""
        mock_page = MagicMock()
        # Simulate case where link already existed - returns timeout because no NEW link was detected
        mock_page.evaluate = AsyncMock(return_value={"type": "timeout", "reason": "no_change_detected"})

        result = await _wait_for_embed_insertion(
            mock_page,
            initial_count=0,
            timeout=5000,
            url="https://twitter.com/user/status/123",
        )

        # Should return TIMEOUT, not LINK_INSERTED, because the link already existed
        assert result == EmbedResult.TIMEOUT
