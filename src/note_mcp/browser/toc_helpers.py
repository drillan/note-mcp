"""TOC insertion helpers for note.com editor.

This module provides functions to insert table of contents (TOC) at
placeholder positions in the note.com ProseMirror editor.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# note.com editor selectors
_EDITOR_SELECTOR = ".ProseMirror"
# Changed from 'button[class*="AddButton"]' which no longer exists (issue #58)
# The "メニューを開く" button opens the insert menu containing TOC option
_MENU_BUTTON_SELECTOR = 'button[aria-label="メニューを開く"]'
_TOC_MENU_ITEM_SELECTOR = 'button:has-text("目次")'
# TOC element is a nav tag within the editor (uses Tailwind classes, no specific class name)
_TOC_ELEMENT_SELECTOR = ".ProseMirror nav"

# Placeholder marker (text marker, not HTML comment)
# Must match _TOC_PLACEHOLDER in typing_helpers.py
TOC_PLACEHOLDER = "§§TOC§§"


async def has_toc_placeholder(page: Page) -> bool:
    """Check if editor contains TOC placeholder.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if placeholder exists in editor.
    """
    editor = page.locator(_EDITOR_SELECTOR)
    # Use text_content() since placeholder is typed as text, not HTML
    text = await editor.text_content()
    return text is not None and TOC_PLACEHOLDER in text


async def insert_toc_at_placeholder(page: Page, timeout: int = 10000) -> bool:
    """Insert TOC at placeholder position in editor.

    Finds the TOC placeholder, positions cursor there, and uses
    note.com's UI to insert a table of contents.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds.

    Returns:
        True if TOC was successfully inserted.

    Raises:
        TimeoutError: If TOC insertion times out.
    """
    logger.info("Checking for TOC placeholder...")

    if not await has_toc_placeholder(page):
        logger.debug("No TOC placeholder found")
        return False

    logger.info("TOC placeholder found, inserting table of contents...")

    # 1. Move cursor to placeholder position
    if not await _move_cursor_to_placeholder(page):
        logger.error("Failed to move cursor to TOC placeholder")
        return False

    # 2. Remove the placeholder
    if not await _remove_placeholder(page):
        logger.error("Failed to remove TOC placeholder")
        return False

    # 3. Click menu button to open insert menu
    await _click_menu_button(page, timeout)

    # 4. Click [目次] menu item
    await _click_toc_menu_item(page, timeout)

    # 5. Wait for TOC to be inserted
    await _wait_for_toc_inserted(page, timeout)

    logger.info("TOC inserted successfully")
    return True


async def _move_cursor_to_placeholder(page: Page) -> bool:
    """Move cursor to TOC placeholder position.

    Uses JavaScript to find and select the placeholder text node.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if cursor was successfully moved to placeholder.
    """
    result = await page.evaluate(
        f"""
        () => {{
            const placeholder = '{TOC_PLACEHOLDER}';
            const editor = document.querySelector('{_EDITOR_SELECTOR}');
            if (!editor) {{
                return {{ success: false, error: 'Editor element not found' }};
            }}

            const walker = document.createTreeWalker(
                editor,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            let node;
            while (node = walker.nextNode()) {{
                if (node.nodeValue && node.nodeValue.includes(placeholder)) {{
                    // Position cursor at the start of placeholder text
                    const range = document.createRange();
                    const offset = node.nodeValue.indexOf(placeholder);
                    range.setStart(node, offset);
                    range.collapse(true);

                    const selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    return {{ success: true }};
                }}
            }}
            return {{ success: false, error: 'Placeholder not found in text nodes' }};
        }}
    """
    )
    await asyncio.sleep(0.1)

    if not result.get("success"):
        logger.warning(f"Failed to move cursor to placeholder: {result.get('error')}")
        return False
    return True


async def _remove_placeholder(page: Page) -> bool:
    """Remove the TOC placeholder text from editor.

    Modifies the DOM by removing the placeholder text from the text node.
    If the parent paragraph becomes empty, focuses it for TOC insertion.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if placeholder was successfully removed.
    """
    result = await page.evaluate(
        f"""
        () => {{
            const placeholder = '{TOC_PLACEHOLDER}';
            const editor = document.querySelector('{_EDITOR_SELECTOR}');
            if (!editor) {{
                return {{ success: false, error: 'Editor element not found' }};
            }}

            const walker = document.createTreeWalker(
                editor,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            let node;
            while (node = walker.nextNode()) {{
                if (node.nodeValue && node.nodeValue.includes(placeholder)) {{
                    // Remove only the placeholder text, keep any surrounding text
                    node.nodeValue = node.nodeValue.replace(placeholder, '');

                    // If the parent is now empty, consider cleaning it up
                    const parent = node.parentElement;
                    if (parent && parent.textContent.trim() === '') {{
                        // Parent paragraph is empty, focus it for TOC insertion
                        parent.focus();
                    }}
                    return {{ success: true }};
                }}
            }}
            return {{ success: false, error: 'Placeholder not found in text nodes' }};
        }}
    """
    )
    await asyncio.sleep(0.1)

    if not result.get("success"):
        logger.warning(f"Failed to remove placeholder: {result.get('error')}")
        return False
    return True


async def _click_menu_button(page: Page, timeout: int) -> None:
    """Click the menu button to open insert menu.

    The menu button (aria-label="メニューを開く") opens the insert menu
    containing the TOC option. This replaced the old AddButton approach.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds.
    """
    # Click editor to focus
    editor = page.locator(_EDITOR_SELECTOR)
    await editor.click()
    await asyncio.sleep(0.2)

    # Find and click menu button
    menu_button = page.locator(_MENU_BUTTON_SELECTOR).first
    await menu_button.wait_for(state="visible", timeout=timeout)
    await menu_button.click()
    await asyncio.sleep(0.3)


async def _click_toc_menu_item(page: Page, timeout: int) -> None:
    """Click the TOC menu item.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds.
    """
    toc_button = page.locator(_TOC_MENU_ITEM_SELECTOR).first
    await toc_button.wait_for(state="visible", timeout=timeout)
    await toc_button.click()
    await asyncio.sleep(0.3)


async def _wait_for_toc_inserted(page: Page, timeout: int) -> None:
    """Wait for TOC element to appear in editor.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds.

    Raises:
        TimeoutError: If TOC element doesn't appear.
    """
    toc_element = page.locator(_TOC_ELEMENT_SELECTOR).first
    await toc_element.wait_for(state="visible", timeout=timeout)
