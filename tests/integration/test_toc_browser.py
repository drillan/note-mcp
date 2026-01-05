"""Integration tests for TOC browser insertion."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from note_mcp.browser.toc_helpers import (
    TOC_PLACEHOLDER,
    has_toc_placeholder,
    insert_toc_at_placeholder,
)


class TestTocPlaceholderDetection:
    """Tests for TOC placeholder detection in browser."""

    @pytest.mark.asyncio
    async def test_detects_placeholder_in_editor(self) -> None:
        """Placeholder in editor text content is detected."""
        page = MagicMock()
        editor = MagicMock()
        page.locator.return_value = editor
        editor.text_content = AsyncMock(return_value=f"Text {TOC_PLACEHOLDER} Heading")

        result = await has_toc_placeholder(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_placeholder_returns_false(self) -> None:
        """Editor without placeholder returns False."""
        page = MagicMock()
        editor = MagicMock()
        page.locator.return_value = editor
        editor.text_content = AsyncMock(return_value="Text Heading")

        result = await has_toc_placeholder(page)
        assert result is False


class TestTocInsertion:
    """Tests for TOC insertion via browser."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_placeholder(self) -> None:
        """Returns False when no placeholder exists."""
        page = MagicMock()
        editor = MagicMock()
        page.locator.return_value = editor
        editor.text_content = AsyncMock(return_value="Text")

        result = await insert_toc_at_placeholder(page)
        assert result is False

    @pytest.mark.asyncio
    async def test_inserts_toc_at_placeholder(self) -> None:
        """TOC is inserted when placeholder exists."""
        page = MagicMock()
        editor = MagicMock()
        menu_button = MagicMock()
        toc_button = MagicMock()
        toc_element = MagicMock()

        # Setup mocks for new selector pattern (issue #58 fix)
        def locator_side_effect(selector: str) -> MagicMock:
            if selector == ".ProseMirror":
                return editor
            elif "メニューを開く" in selector:
                return menu_button
            elif "目次" in selector:
                return toc_button
            elif "nav" in selector:
                return toc_element
            return MagicMock()

        page.locator.side_effect = locator_side_effect
        editor.text_content = AsyncMock(return_value=f"Content {TOC_PLACEHOLDER} More")
        editor.click = AsyncMock()
        menu_button.first = menu_button
        menu_button.wait_for = AsyncMock()
        menu_button.click = AsyncMock()
        toc_button.first = toc_button
        toc_button.wait_for = AsyncMock()
        toc_button.click = AsyncMock()
        toc_element.first = toc_element
        toc_element.wait_for = AsyncMock()
        page.evaluate = AsyncMock(return_value={"success": True})
        # Mock keyboard for placeholder removal
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()

        result = await insert_toc_at_placeholder(page)
        assert result is True
        menu_button.click.assert_called_once()
        toc_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_toc_insertion_with_multiple_headings(self) -> None:
        """TOC is inserted when editor has multiple headings."""
        page = MagicMock()
        editor = MagicMock()
        menu_button = MagicMock()
        toc_button = MagicMock()
        toc_element = MagicMock()

        text_content = f"Title {TOC_PLACEHOLDER} Section 1 Content 1 Section 2 Content 2 Subsection 2.1 Content 2.1"

        # Setup mocks for new selector pattern (issue #58 fix)
        def locator_side_effect(selector: str) -> MagicMock:
            if selector == ".ProseMirror":
                return editor
            elif "メニューを開く" in selector:
                return menu_button
            elif "目次" in selector:
                return toc_button
            elif "nav" in selector:
                return toc_element
            return MagicMock()

        page.locator.side_effect = locator_side_effect
        editor.text_content = AsyncMock(return_value=text_content)
        editor.click = AsyncMock()
        menu_button.first = menu_button
        menu_button.wait_for = AsyncMock()
        menu_button.click = AsyncMock()
        toc_button.first = toc_button
        toc_button.wait_for = AsyncMock()
        toc_button.click = AsyncMock()
        toc_element.first = toc_element
        toc_element.wait_for = AsyncMock()
        page.evaluate = AsyncMock(return_value={"success": True})
        # Mock keyboard for placeholder removal
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()

        result = await insert_toc_at_placeholder(page)
        assert result is True


class TestTocPlaceholderConstant:
    """Tests for TOC placeholder constant."""

    def test_placeholder_format(self) -> None:
        """Placeholder should be a text marker with section signs."""
        assert "§§" in TOC_PLACEHOLDER
        assert "TOC" in TOC_PLACEHOLDER
