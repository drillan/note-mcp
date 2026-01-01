"""Unit tests for embed_helpers module.

Tests placeholder detection and extraction for embed functionality.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from note_mcp.browser.embed_helpers import (
    _EMBED_PLACEHOLDER_END,
    _EMBED_PLACEHOLDER_PATTERN,
    _EMBED_PLACEHOLDER_START,
    _find_embed_placeholders,
    _select_placeholder,
    has_embed_placeholders,
)


class TestEmbedPlaceholderConstants:
    """Tests for embed placeholder constant definitions."""

    def test_placeholder_start_marker(self) -> None:
        """Placeholder start marker should be §§EMBED:"""
        assert _EMBED_PLACEHOLDER_START == "§§EMBED:"

    def test_placeholder_end_marker(self) -> None:
        """Placeholder end marker should be §§"""
        assert _EMBED_PLACEHOLDER_END == "§§"

    def test_placeholder_pattern_matches_valid_format(self) -> None:
        """Pattern should match valid placeholder format."""
        text = "§§EMBED:https://www.youtube.com/watch?v=abc123§§"
        match = _EMBED_PLACEHOLDER_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "https://www.youtube.com/watch?v=abc123"

    def test_placeholder_pattern_extracts_url(self) -> None:
        """Pattern should extract URL from placeholder."""
        text = "Some text §§EMBED:https://twitter.com/user/status/123§§ more text"
        match = _EMBED_PLACEHOLDER_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "https://twitter.com/user/status/123"

    def test_placeholder_pattern_finds_multiple(self) -> None:
        """Pattern should find multiple placeholders."""
        text = "§§EMBED:url1§§ text §§EMBED:url2§§"
        matches = _EMBED_PLACEHOLDER_PATTERN.findall(text)
        assert matches == ["url1", "url2"]


class TestHasEmbedPlaceholders:
    """Tests for has_embed_placeholders function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_placeholder_exists(self) -> None:
        """Should return True when editor contains embed placeholder."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.text_content = AsyncMock(return_value="Some text §§EMBED:https://youtube.com/watch?v=abc§§ more")
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await has_embed_placeholders(mock_page)

        assert result is True
        mock_page.locator.assert_called_once_with(".ProseMirror")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_placeholder(self) -> None:
        """Should return False when editor has no embed placeholder."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.text_content = AsyncMock(return_value="Regular text without placeholders")
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await has_embed_placeholders(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_text_is_none(self) -> None:
        """Should return False when text_content returns None."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.text_content = AsyncMock(return_value=None)
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await has_embed_placeholders(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_for_partial_placeholder(self) -> None:
        """Should return True when start marker exists (even without end marker).

        The has_embed_placeholders function only checks for the start marker
        presence, not for complete placeholders. This is a fast pre-check.
        """
        mock_page = MagicMock()
        mock_locator = MagicMock()
        # Has start marker but no end marker - still detected as potential placeholder
        mock_locator.text_content = AsyncMock(return_value="Text with §§EMBED: but no end")
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await has_embed_placeholders(mock_page)

        # Returns True because it checks for start marker only
        assert result is True


class TestFindEmbedPlaceholders:
    """Tests for _find_embed_placeholders function."""

    @pytest.mark.asyncio
    async def test_finds_single_placeholder(self) -> None:
        """Should find single placeholder and extract URL."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(
            return_value={"urls": ["https://www.youtube.com/watch?v=abc123"], "text": "sample text"}
        )

        result = await _find_embed_placeholders(mock_page)

        assert result == ["https://www.youtube.com/watch?v=abc123"]

    @pytest.mark.asyncio
    async def test_finds_multiple_placeholders(self) -> None:
        """Should find multiple placeholders and extract all URLs."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(
            return_value={
                "urls": [
                    "https://www.youtube.com/watch?v=abc123",
                    "https://twitter.com/user/status/456",
                    "https://note.com/user/n/n789",
                ],
                "text": "sample text",
            }
        )

        result = await _find_embed_placeholders(mock_page)

        assert len(result) == 3
        assert "https://www.youtube.com/watch?v=abc123" in result
        assert "https://twitter.com/user/status/456" in result
        assert "https://note.com/user/n/n789" in result

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_placeholders(self) -> None:
        """Should return empty list when no placeholders found."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"urls": [], "text": ""})

        result = await _find_embed_placeholders(mock_page)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_evaluate_returns_none(self) -> None:
        """Should return empty list when evaluate returns None."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        result = await _find_embed_placeholders(mock_page)

        assert result == []


class TestSelectPlaceholder:
    """Tests for _select_placeholder function."""

    @pytest.mark.asyncio
    async def test_returns_true_on_successful_selection(self) -> None:
        """Should return True when placeholder is successfully selected."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": True})

        placeholder = "§§EMBED:https://youtube.com/watch?v=abc§§"
        result = await _select_placeholder(mock_page, placeholder)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_placeholder_not_found(self) -> None:
        """Should return False when placeholder is not found."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": False, "error": "Placeholder not found in text nodes"})

        placeholder = "§§EMBED:https://youtube.com/watch?v=abc§§"
        result = await _select_placeholder(mock_page, placeholder)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_editor_not_found(self) -> None:
        """Should return False when editor element is not found."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": False, "error": "Editor element not found"})

        placeholder = "§§EMBED:https://youtube.com/watch?v=abc§§"
        result = await _select_placeholder(mock_page, placeholder)

        assert result is False
