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
_EDITOR_SELECTOR = ".p-editorBody"
_ADD_BUTTON_SELECTOR = 'button[class*="AddButton"]'
_TOC_MENU_ITEM_SELECTOR = 'button:has-text("目次")'
_TOC_ELEMENT_SELECTOR = '[class*="TableOfContents"]'

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
    await _move_cursor_to_placeholder(page)

    # 2. Remove the placeholder
    await _remove_placeholder(page)

    # 3. Click [+] button to open menu
    await _click_add_button(page, timeout)

    # 4. Click [目次] menu item
    await _click_toc_menu_item(page, timeout)

    # 5. Wait for TOC to be inserted
    await _wait_for_toc_inserted(page, timeout)

    logger.info("TOC inserted successfully")
    return True


async def _move_cursor_to_placeholder(page: Page) -> None:
    """Move cursor to TOC placeholder position.

    Uses JavaScript to find and select the placeholder text node.

    Args:
        page: Playwright page with note.com editor.
    """
    await page.evaluate(
        f"""
        () => {{
            const placeholder = '{TOC_PLACEHOLDER}';
            const editor = document.querySelector('.p-editorBody');
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
                    break;
                }}
            }}
        }}
    """
    )
    await asyncio.sleep(0.1)


async def _remove_placeholder(page: Page) -> None:
    """Remove the TOC placeholder text from editor.

    Args:
        page: Playwright page with note.com editor.
    """
    await page.evaluate(
        f"""
        () => {{
            const placeholder = '{TOC_PLACEHOLDER}';
            const editor = document.querySelector('.p-editorBody');
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
                    break;
                }}
            }}
        }}
    """
    )
    await asyncio.sleep(0.1)


async def _click_add_button(page: Page, timeout: int) -> None:
    """Click the [+] add button to open insert menu.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds.
    """
    # Click editor to focus
    editor = page.locator(_EDITOR_SELECTOR)
    await editor.click()
    await asyncio.sleep(0.2)

    # Find and click [+] button
    add_button = page.locator(_ADD_BUTTON_SELECTOR).first
    await add_button.wait_for(state="visible", timeout=timeout)
    await add_button.click()
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
