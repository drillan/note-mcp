"""Unit tests for text alignment browser helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from note_mcp.browser.text_align_helpers import (
    ALIGN_CENTER_START,
    ALIGN_END,
    ALIGN_LEFT_START,
    ALIGN_RIGHT_START,
    _remove_placeholder_markers,
    _select_placeholder_text,
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
        mock_page.locator.assert_called_once_with(".ProseMirror")

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


class TestSelectPlaceholderText:
    """Tests for _select_placeholder_text function using Playwright locators."""

    @pytest.mark.asyncio
    async def test_returns_true_when_placeholder_found(self) -> None:
        """Returns True when placeholder paragraph is found and clicked."""
        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=1)

        mock_p = MagicMock()
        mock_paragraphs.nth.return_value = mock_p
        mock_p.text_content = AsyncMock(return_value=f"{ALIGN_CENTER_START}test text{ALIGN_END}")
        mock_p.click = AsyncMock()

        result = await _select_placeholder_text(mock_page, "center", "test text")

        assert result is True
        mock_page.locator.assert_called_once_with(".ProseMirror p")
        mock_p.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_paragraphs(self) -> None:
        """Returns False when editor has no paragraphs."""
        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=0)

        result = await _select_placeholder_text(mock_page, "center", "test text")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_placeholder_not_found(self) -> None:
        """Returns False when placeholder is not found in paragraphs."""
        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=2)

        mock_p1 = MagicMock()
        mock_p1.text_content = AsyncMock(return_value="Some other text")
        mock_p2 = MagicMock()
        mock_p2.text_content = AsyncMock(return_value="Another paragraph")

        mock_paragraphs.nth.side_effect = [mock_p1, mock_p2]

        result = await _select_placeholder_text(mock_page, "right", "missing text")

        assert result is False

    @pytest.mark.asyncio
    async def test_uses_correct_alignment_marker(self) -> None:
        """Uses correct alignment marker based on alignment_type."""
        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=1)

        mock_p = MagicMock()
        mock_paragraphs.nth.return_value = mock_p
        # Use RIGHT marker
        mock_p.text_content = AsyncMock(return_value=f"{ALIGN_RIGHT_START}test{ALIGN_END}")
        mock_p.click = AsyncMock()

        result = await _select_placeholder_text(mock_page, "right", "test")

        assert result is True


class TestRemovePlaceholderMarkers:
    """Tests for _remove_placeholder_markers function using Playwright operations."""

    @pytest.mark.asyncio
    async def test_returns_true_when_markers_removed(self) -> None:
        """Returns True when placeholder markers are successfully removed."""
        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=1)

        mock_p = MagicMock()
        mock_paragraphs.nth.return_value = mock_p
        full_placeholder = f"{ALIGN_CENTER_START}aligned text{ALIGN_END}"
        mock_p.text_content = AsyncMock(return_value=full_placeholder)
        mock_p.click = AsyncMock()

        mock_keyboard = MagicMock()
        mock_page.keyboard = mock_keyboard
        mock_keyboard.type = AsyncMock()

        result = await _remove_placeholder_markers(mock_page, "center", "aligned text")

        assert result is True
        mock_p.click.assert_called_once_with(click_count=3)
        mock_keyboard.type.assert_called_once_with("aligned text")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_paragraphs(self) -> None:
        """Returns False when editor has no paragraphs."""
        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=0)

        result = await _remove_placeholder_markers(mock_page, "center", "test text")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_placeholder_not_found(self) -> None:
        """Returns False when placeholder is not found in paragraphs."""
        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=1)

        mock_p = MagicMock()
        mock_paragraphs.nth.return_value = mock_p
        mock_p.text_content = AsyncMock(return_value="Different content")

        result = await _remove_placeholder_markers(mock_page, "left", "missing text")

        assert result is False

    @pytest.mark.asyncio
    async def test_uses_correct_selector_constant(self) -> None:
        """Uses _EDITOR_SELECTOR constant when locating paragraphs."""
        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=1)

        mock_p = MagicMock()
        mock_paragraphs.nth.return_value = mock_p
        full_placeholder = f"{ALIGN_CENTER_START}test{ALIGN_END}"
        mock_p.text_content = AsyncMock(return_value=full_placeholder)
        mock_p.click = AsyncMock()

        mock_keyboard = MagicMock()
        mock_page.keyboard = mock_keyboard
        mock_keyboard.type = AsyncMock()

        await _remove_placeholder_markers(mock_page, "center", "test")

        # Should use .ProseMirror selector (from _EDITOR_SELECTOR constant)
        mock_page.locator.assert_called_once_with(".ProseMirror p")

    @pytest.mark.asyncio
    async def test_logs_warning_on_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """Logs warning when marker removal fails."""
        import logging

        mock_page = MagicMock()
        mock_paragraphs = MagicMock()
        mock_page.locator.return_value = mock_paragraphs
        mock_paragraphs.count = AsyncMock(return_value=1)

        mock_p = MagicMock()
        mock_paragraphs.nth.return_value = mock_p
        mock_p.text_content = AsyncMock(return_value="Different content - placeholder not found")

        with caplog.at_level(logging.WARNING):
            await _remove_placeholder_markers(mock_page, "center", "test content")

        assert "Failed to remove placeholder markers" in caplog.text
        assert "Alignment markers may remain in published article" in caplog.text
