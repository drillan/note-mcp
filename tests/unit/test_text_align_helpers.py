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


class TestSelectPlaceholderText:
    """Tests for _select_placeholder_text function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_placeholder_found(self) -> None:
        """Returns True when placeholder is found and selected."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": True})

        result = await _select_placeholder_text(mock_page, "center", "test text")

        assert result is True
        mock_page.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_editor_not_found(self) -> None:
        """Returns False when editor element is not found."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": False, "error": "Editor element not found"})

        result = await _select_placeholder_text(mock_page, "center", "test text")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_placeholder_not_found(self) -> None:
        """Returns False when placeholder is not found in text nodes."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": False, "error": "Placeholder not found in text nodes"})

        result = await _select_placeholder_text(mock_page, "right", "missing text")

        assert result is False

    @pytest.mark.asyncio
    async def test_uses_correct_alignment_marker(self) -> None:
        """Uses correct alignment marker based on alignment_type."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": True})

        await _select_placeholder_text(mock_page, "right", "test")

        # Check that the evaluate was called with RIGHT marker
        call_args = mock_page.evaluate.call_args[0][0]
        assert "§§ALIGN_RIGHT§§" in call_args
        assert "§§/ALIGN§§" in call_args


class TestRemovePlaceholderMarkers:
    """Tests for _remove_placeholder_markers function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_markers_removed(self) -> None:
        """Returns True when placeholder markers are successfully removed."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": True})

        result = await _remove_placeholder_markers(mock_page, "center", "aligned text")

        assert result is True
        mock_page.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_editor_not_found(self) -> None:
        """Returns False when editor is not found."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": False, "error": "Editor not found"})

        result = await _remove_placeholder_markers(mock_page, "center", "test text")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_placeholder_not_found(self) -> None:
        """Returns False when placeholder is not found in DOM."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": False, "error": "Placeholder not found"})

        result = await _remove_placeholder_markers(mock_page, "left", "missing text")

        assert result is False

    @pytest.mark.asyncio
    async def test_uses_correct_selector_constant(self) -> None:
        """Uses _EDITOR_SELECTOR constant in JavaScript evaluation."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": True})

        await _remove_placeholder_markers(mock_page, "center", "test")

        call_args = mock_page.evaluate.call_args[0][0]
        # Should use the constant value, not a hardcoded selector
        assert ".p-editorBody" in call_args

    @pytest.mark.asyncio
    async def test_logs_warning_on_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """Logs warning when marker removal fails."""
        import logging

        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value={"success": False, "error": "Placeholder not found"})

        with caplog.at_level(logging.WARNING):
            await _remove_placeholder_markers(mock_page, "center", "test content")

        assert "Failed to remove placeholder markers" in caplog.text
        assert "Alignment markers may remain in published article" in caplog.text
