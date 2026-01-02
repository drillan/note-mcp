"""E2E tests for TOC (Table of Contents) insertion functionality.

Tests the TOC insertion flow that was fixed in issue #58:
- Menu button selector: button[aria-label="メニューを開く"]
- TOC menu item selector: button:has-text("目次")
- TOC element selector: .ProseMirror nav
"""

import asyncio

import pytest
from playwright.async_api import Page

from note_mcp.browser.toc_helpers import (
    TOC_PLACEHOLDER,
    has_toc_placeholder,
    insert_toc_at_placeholder,
)


class TestTocPlaceholder:
    """Tests for TOC placeholder detection."""

    @pytest.mark.asyncio
    async def test_has_toc_placeholder_with_marker(
        self,
        editor_page: Page,
    ) -> None:
        """Test that §§TOC§§ placeholder is detected in content."""
        # Type content with TOC placeholder marker
        # Note: [TOC] in markdown is converted to §§TOC§§ by typing_helpers.py
        editor = editor_page.locator(".ProseMirror")
        await editor.click()
        await editor_page.keyboard.type(TOC_PLACEHOLDER)
        await editor_page.keyboard.press("Enter")
        await editor_page.keyboard.type("## 見出し1")

        # Check placeholder detection
        result = await has_toc_placeholder(editor_page)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_toc_placeholder_without_marker(
        self,
        editor_page: Page,
    ) -> None:
        """Test that absence of [TOC] placeholder is correctly detected."""
        # Type content without [TOC] marker
        editor = editor_page.locator(".ProseMirror")
        await editor.click()
        await editor_page.keyboard.type("## 見出し1")
        await editor_page.keyboard.press("Enter")
        await editor_page.keyboard.type("本文テキスト")

        # Check placeholder detection
        result = await has_toc_placeholder(editor_page)
        assert result is False


class TestTocInsertion:
    """Tests for TOC insertion via menu button.

    These tests verify the fix for issue #58 where the AddButton selector
    no longer exists and was replaced with the menu button selector.
    """

    @pytest.mark.asyncio
    async def test_insert_toc_with_headings(
        self,
        editor_page: Page,
    ) -> None:
        """Test TOC insertion when content has headings."""
        # Type content with TOC placeholder and headings
        editor = editor_page.locator(".ProseMirror")
        await editor.click()

        # Add TOC placeholder (§§TOC§§)
        await editor_page.keyboard.type(TOC_PLACEHOLDER)
        await editor_page.keyboard.press("Enter")
        await asyncio.sleep(0.3)

        # Add headings (required for TOC insertion)
        # Use ## + space to trigger ProseMirror heading conversion
        await editor_page.keyboard.type("## テスト見出し1 ")
        await asyncio.sleep(0.2)
        await editor_page.keyboard.press("Enter")
        await editor_page.keyboard.type("本文テキスト")
        await editor_page.keyboard.press("Enter")
        await asyncio.sleep(0.3)

        await editor_page.keyboard.type("## テスト見出し2 ")
        await asyncio.sleep(0.2)
        await editor_page.keyboard.press("Enter")
        await asyncio.sleep(0.5)

        # Insert TOC at placeholder
        result = await insert_toc_at_placeholder(editor_page)

        # Verify insertion succeeded
        assert result is True

        # Verify TOC element exists in editor
        toc_element = editor_page.locator(".ProseMirror nav")
        toc_count = await toc_element.count()
        assert toc_count >= 1, "TOC nav element should be inserted"

    @pytest.mark.asyncio
    async def test_insert_toc_without_placeholder_returns_false(
        self,
        editor_page: Page,
    ) -> None:
        """Test that TOC insertion returns False when no placeholder exists."""
        # Type content without [TOC] placeholder
        editor = editor_page.locator(".ProseMirror")
        await editor.click()
        await editor_page.keyboard.type("## 見出し1")
        await editor_page.keyboard.press("Enter")
        await editor_page.keyboard.type("本文テキスト")

        # Try to insert TOC (should return False)
        result = await insert_toc_at_placeholder(editor_page)

        # Verify no insertion happened
        assert result is False


class TestTocMenuButton:
    """Tests for TOC menu button interaction.

    These tests verify the new selectors work correctly:
    - Menu button: button[aria-label="メニューを開く"]
    - TOC menu item: button:has-text("目次")
    """

    @pytest.mark.asyncio
    async def test_menu_button_exists(
        self,
        editor_page: Page,
    ) -> None:
        """Test that the menu button with correct aria-label exists."""
        # First add some content to ensure editor is ready
        editor = editor_page.locator(".ProseMirror")
        await editor.click()
        await editor_page.keyboard.type("テスト")
        await editor_page.keyboard.press("Enter")

        # Check menu button exists
        menu_button = editor_page.locator('button[aria-label="メニューを開く"]')
        count = await menu_button.count()
        assert count >= 1, "Menu button should exist"

    @pytest.mark.asyncio
    async def test_menu_opens_with_toc_option(
        self,
        editor_page: Page,
    ) -> None:
        """Test that menu opens and contains TOC option."""
        # Add headings (required for TOC menu item to appear)
        editor = editor_page.locator(".ProseMirror")
        await editor.click()
        await editor_page.keyboard.type("## 見出し1")
        await editor_page.keyboard.press("Enter")
        await editor_page.keyboard.type("本文")
        await editor_page.keyboard.press("Enter")

        # Click menu button
        menu_button = editor_page.locator('button[aria-label="メニューを開く"]')
        await menu_button.first.click()
        await asyncio.sleep(0.5)

        # Check TOC menu item exists
        toc_menu_item = editor_page.locator('button:has-text("目次")')
        count = await toc_menu_item.count()
        assert count >= 1, "TOC menu item should exist after opening menu"

        # Find the visible menu item (not the sidebar one)
        found_visible = False
        for i in range(count):
            item = toc_menu_item.nth(i)
            if await item.is_visible():
                text = (await item.text_content() or "").strip()
                aria = await item.get_attribute("aria-label") or ""
                # Menu item has text "目次" with empty aria-label
                # Sidebar has aria-label="目次" with empty text
                if text == "目次" and aria == "":
                    found_visible = True
                    break

        assert found_visible, "Visible TOC menu item should exist in menu"

        # Close menu
        await editor_page.keyboard.press("Escape")
