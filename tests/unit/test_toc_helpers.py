"""Unit tests for TOC browser helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from note_mcp.browser.toc_helpers import (
    TOC_PLACEHOLDER,
    has_toc_placeholder,
)


class TestTocPlaceholderConstant:
    """Tests for TOC_PLACEHOLDER constant."""

    def test_placeholder_is_text_marker(self) -> None:
        """Placeholder should be a unique text marker."""
        # Uses section signs as delimiters for uniqueness
        assert "§§" in TOC_PLACEHOLDER

    def test_placeholder_contains_toc(self) -> None:
        """Placeholder should contain TOC identifier."""
        assert "TOC" in TOC_PLACEHOLDER


class TestHasTocPlaceholder:
    """Tests for has_toc_placeholder function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_placeholder_exists(self) -> None:
        """Returns True when placeholder is in editor text content."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator
        mock_locator.text_content = AsyncMock(return_value=f"Content {TOC_PLACEHOLDER} More")

        result = await has_toc_placeholder(mock_page)

        assert result is True
        mock_page.locator.assert_called_once_with(".p-editorBody")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_placeholder(self) -> None:
        """Returns False when placeholder is not in editor text content."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator
        mock_locator.text_content = AsyncMock(return_value="Content without placeholder")

        result = await has_toc_placeholder(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_empty_editor(self) -> None:
        """Returns False for empty editor content."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator
        mock_locator.text_content = AsyncMock(return_value="")

        result = await has_toc_placeholder(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_none_content(self) -> None:
        """Returns False when text_content returns None."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator
        mock_locator.text_content = AsyncMock(return_value=None)

        result = await has_toc_placeholder(mock_page)

        assert result is False
