"""Unit tests for text alignment browser helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from note_mcp.browser.text_align_helpers import (
    ALIGN_CENTER_START,
    ALIGN_END,
    ALIGN_LEFT_START,
    ALIGN_RIGHT_START,
    has_alignment_placeholders,
)


class TestAlignmentPlaceholderConstants:
    """Tests for alignment placeholder constants."""

    def test_center_placeholder_format(self) -> None:
        """Center placeholder should contain ALIGN_CENTER."""
        assert "§§" in ALIGN_CENTER_START
        assert "CENTER" in ALIGN_CENTER_START

    def test_right_placeholder_format(self) -> None:
        """Right placeholder should contain ALIGN_RIGHT."""
        assert "§§" in ALIGN_RIGHT_START
        assert "RIGHT" in ALIGN_RIGHT_START

    def test_left_placeholder_format(self) -> None:
        """Left placeholder should contain ALIGN_LEFT."""
        assert "§§" in ALIGN_LEFT_START
        assert "LEFT" in ALIGN_LEFT_START

    def test_end_placeholder_format(self) -> None:
        """End placeholder should contain /ALIGN."""
        assert "§§" in ALIGN_END
        assert "/ALIGN" in ALIGN_END

    def test_placeholders_are_unique(self) -> None:
        """All placeholders should be unique."""
        placeholders = [ALIGN_CENTER_START, ALIGN_RIGHT_START, ALIGN_LEFT_START, ALIGN_END]
        assert len(placeholders) == len(set(placeholders))


class TestHasAlignmentPlaceholders:
    """Tests for has_alignment_placeholders function."""

    @pytest.mark.asyncio
    async def test_returns_true_for_center_placeholder(self) -> None:
        """Returns True when center placeholder is in editor."""
        mock_page = MagicMock()
        mock_editor = MagicMock()
        mock_page.locator.return_value = mock_editor
        mock_editor.text_content = AsyncMock(return_value=f"Text {ALIGN_CENTER_START}centered{ALIGN_END} more")

        result = await has_alignment_placeholders(mock_page)

        assert result is True
        mock_page.locator.assert_called_once_with(".p-editorBody")

    @pytest.mark.asyncio
    async def test_returns_true_for_right_placeholder(self) -> None:
        """Returns True when right placeholder is in editor."""
        mock_page = MagicMock()
        mock_editor = MagicMock()
        mock_page.locator.return_value = mock_editor
        mock_editor.text_content = AsyncMock(return_value=f"Text {ALIGN_RIGHT_START}right aligned{ALIGN_END}")

        result = await has_alignment_placeholders(mock_page)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_for_left_placeholder(self) -> None:
        """Returns True when left placeholder is in editor."""
        mock_page = MagicMock()
        mock_editor = MagicMock()
        mock_page.locator.return_value = mock_editor
        mock_editor.text_content = AsyncMock(return_value=f"Text {ALIGN_LEFT_START}left aligned{ALIGN_END}")

        result = await has_alignment_placeholders(mock_page)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_placeholder(self) -> None:
        """Returns False when no placeholder is in editor."""
        mock_page = MagicMock()
        mock_editor = MagicMock()
        mock_page.locator.return_value = mock_editor
        mock_editor.text_content = AsyncMock(return_value="Normal text without placeholders")

        result = await has_alignment_placeholders(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_empty_editor(self) -> None:
        """Returns False for empty editor content."""
        mock_page = MagicMock()
        mock_editor = MagicMock()
        mock_page.locator.return_value = mock_editor
        mock_editor.text_content = AsyncMock(return_value="")

        result = await has_alignment_placeholders(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_none_content(self) -> None:
        """Returns False when text_content returns None."""
        mock_page = MagicMock()
        mock_editor = MagicMock()
        mock_page.locator.return_value = mock_editor
        mock_editor.text_content = AsyncMock(return_value=None)

        result = await has_alignment_placeholders(mock_page)

        assert result is False
