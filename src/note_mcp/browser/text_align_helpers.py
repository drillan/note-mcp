"""Text alignment helpers for note.com editor.

This module provides functions to apply text alignment (center, right, left)
at placeholder positions in the note.com ProseMirror editor.

note.com's API strips style attributes from HTML, so we use browser automation
to apply alignment via the editor's UI controls.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# Placeholder markers for text alignment
# Format: §§ALIGN_CENTER§§text§§/ALIGN§§
ALIGN_CENTER_START = "§§ALIGN_CENTER§§"
ALIGN_RIGHT_START = "§§ALIGN_RIGHT§§"
ALIGN_LEFT_START = "§§ALIGN_LEFT§§"
ALIGN_END = "§§/ALIGN§§"

# Regex to find alignment placeholders in editor content
_ALIGN_PLACEHOLDER_PATTERN = re.compile(r"§§ALIGN_(CENTER|RIGHT|LEFT)§§(.+?)§§/ALIGN§§")

# note.com editor selectors
_EDITOR_SELECTOR = ".ProseMirror"
_ALIGN_BUTTON_SELECTOR = 'button[aria-label="文章の配置"]'

# Alignment menu item texts
_ALIGN_CENTER_TEXT = "中央寄せ"
_ALIGN_RIGHT_TEXT = "右寄せ"
_ALIGN_LEFT_TEXT = "指定なし"

# Timing constants for browser automation
_CLICK_WAIT_SECONDS = 0.2
_KEYBOARD_WAIT_SECONDS = 0.1
_ALIGNMENT_WAIT_SECONDS = 0.3


async def has_alignment_placeholders(page: Page) -> bool:
    """Check if editor contains any alignment placeholders.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if any alignment placeholder exists in editor.
    """
    editor = page.locator(_EDITOR_SELECTOR)
    text = await editor.text_content()
    return text is not None and "§§ALIGN_" in text


async def apply_text_alignments(page: Page, timeout: int = 10000) -> int:
    """Apply text alignments at all placeholder positions in editor.

    Finds all alignment placeholders, selects the text, and uses
    note.com's UI to apply the appropriate alignment.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds per operation.

    Returns:
        Number of alignments successfully applied.

    Raises:
        TimeoutError: If alignment application times out.
    """
    logger.info("Checking for alignment placeholders...")

    if not await has_alignment_placeholders(page):
        logger.debug("No alignment placeholders found")
        return 0

    # Find all alignment placeholders
    placeholders = await _find_alignment_placeholders(page)
    if not placeholders:
        logger.debug("No alignment placeholders found in DOM")
        return 0

    logger.info(f"Found {len(placeholders)} alignment placeholder(s)")

    applied_count = 0
    for placeholder in placeholders:
        alignment_type = placeholder["type"]
        text_content = placeholder["text"]

        logger.info(f"Applying {alignment_type} alignment to: {text_content[:30]}...")

        try:
            success = await _apply_single_alignment(page, alignment_type, text_content, timeout)
            if success:
                applied_count += 1
                logger.info(f"Successfully applied {alignment_type} alignment")
            else:
                logger.warning(f"Failed to apply {alignment_type} alignment")
        except Exception as e:
            logger.warning(f"Error applying {alignment_type} alignment: {e}")

    logger.info(f"Applied {applied_count}/{len(placeholders)} alignments")
    return applied_count


async def _find_alignment_placeholders(page: Page) -> list[dict[str, str]]:
    """Find all alignment placeholders in the editor.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        List of dicts with 'type' and 'text' keys.
    """
    result = await page.evaluate(
        f"""
        () => {{
            const editor = document.querySelector('{_EDITOR_SELECTOR}');
            if (!editor) return [];

            const text = editor.textContent || '';
            const pattern = /§§ALIGN_(CENTER|RIGHT|LEFT)§§(.+?)§§\\/ALIGN§§/g;
            const placeholders = [];

            let match;
            while ((match = pattern.exec(text)) !== null) {{
                placeholders.push({{
                    type: match[1].toLowerCase(),
                    text: match[2]
                }});
            }}
            return placeholders;
        }}
        """
    )
    return result or []


async def _apply_single_alignment(
    page: Page,
    alignment_type: str,
    text_content: str,
    timeout: int,
) -> bool:
    """Apply alignment to a single placeholder.

    Args:
        page: Playwright page with note.com editor.
        alignment_type: 'center', 'right', or 'left'.
        text_content: The text that should be aligned.
        timeout: Maximum wait time in milliseconds.

    Returns:
        True if alignment was successfully applied.
    """
    # 1. Find and select the placeholder text
    if not await _select_placeholder_text(page, alignment_type, text_content):
        return False

    # 2. Click alignment button in toolbar
    await _click_alignment_button(page, timeout)

    # 3. Select the appropriate alignment option
    await _select_alignment_option(page, alignment_type, timeout)

    # 4. Remove placeholder markers (keep only the content)
    marker_removed = await _remove_placeholder_markers(page, alignment_type, text_content)
    if not marker_removed:
        logger.warning(f"Alignment applied but marker removal failed for: {text_content[:30]}...")

    return True


async def _select_placeholder_text(
    page: Page,
    alignment_type: str,
    text_content: str,
) -> bool:
    """Select the paragraph containing the placeholder using Playwright operations.

    Uses Playwright locator and click operations instead of browser Selection API
    to ensure ProseMirror recognizes the interaction.

    If multiple placeholders have identical text content, only the first match
    is selected and processed.

    Args:
        page: Playwright page with note.com editor.
        alignment_type: 'center', 'right', or 'left'.
        text_content: The text content within the placeholder.

    Returns:
        True if paragraph was found and clicked.
    """
    start_marker = f"§§ALIGN_{alignment_type.upper()}§§"

    # Find paragraphs in the editor using Playwright locator
    paragraphs = page.locator(f"{_EDITOR_SELECTOR} p")
    count = await paragraphs.count()

    for i in range(count):
        p = paragraphs.nth(i)
        text = await p.text_content()
        if text and start_marker in text:
            # Click in the paragraph - ProseMirror recognizes Playwright clicks
            # This is enough to apply alignment to the paragraph
            await p.click()
            await asyncio.sleep(_CLICK_WAIT_SECONDS)
            return True

    logger.warning(f"Placeholder paragraph not found for {alignment_type}")
    return False


async def _click_alignment_button(page: Page, timeout: int) -> None:
    """Click the alignment button in the formatting toolbar.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds.
    """
    align_button = page.locator(_ALIGN_BUTTON_SELECTOR).first
    await align_button.wait_for(state="visible", timeout=timeout)
    await align_button.click()
    await asyncio.sleep(_ALIGNMENT_WAIT_SECONDS)


async def _select_alignment_option(
    page: Page,
    alignment_type: str,
    timeout: int,
) -> None:
    """Select the appropriate alignment option from the dropdown menu.

    Args:
        page: Playwright page with note.com editor.
        alignment_type: 'center', 'right', or 'left'.
        timeout: Maximum wait time in milliseconds.
    """
    # Map alignment type to menu item text
    menu_text_map = {
        "center": _ALIGN_CENTER_TEXT,
        "right": _ALIGN_RIGHT_TEXT,
        "left": _ALIGN_LEFT_TEXT,
    }
    menu_text = menu_text_map.get(alignment_type, _ALIGN_LEFT_TEXT)

    # Find and click the menu item
    menu_item = page.locator(f'button:has-text("{menu_text}")').first
    await menu_item.wait_for(state="visible", timeout=timeout)
    await menu_item.click()
    await asyncio.sleep(_CLICK_WAIT_SECONDS)


async def _remove_placeholder_markers(
    page: Page,
    alignment_type: str,
    text_content: str,
) -> bool:
    """Remove placeholder markers using keyboard operations.

    Uses Playwright keyboard operations instead of direct DOM manipulation
    to ensure ProseMirror syncs its internal state.

    After alignment is applied, finds the paragraph containing the placeholder,
    selects it, and types the clean content. If multiple placeholders have
    identical text content, only the first match is processed.

    Args:
        page: Playwright page with note.com editor.
        alignment_type: 'center', 'right', or 'left'.
        text_content: The text content to keep.

    Returns:
        True if markers were successfully removed, False otherwise.
    """
    start_marker = f"§§ALIGN_{alignment_type.upper()}§§"
    full_placeholder = f"{start_marker}{text_content}{ALIGN_END}"

    # Find the paragraph containing the placeholder using Playwright locator
    paragraphs = page.locator(f"{_EDITOR_SELECTOR} p")
    count = await paragraphs.count()

    for i in range(count):
        p = paragraphs.nth(i)
        text = await p.text_content()
        if text and full_placeholder in text:
            # Calculate clean paragraph text (remove markers)
            clean_text = text.replace(full_placeholder, text_content)

            # Triple-click to select entire paragraph
            await p.click(click_count=3)
            await asyncio.sleep(_KEYBOARD_WAIT_SECONDS)

            # Type the clean text (replaces selection)
            # ProseMirror recognizes keyboard input
            await page.keyboard.type(clean_text)
            await asyncio.sleep(_KEYBOARD_WAIT_SECONDS)
            return True

    # Placeholder not found - might have been handled differently
    logger.warning(
        f"Failed to remove placeholder markers for: {text_content[:30]}... "
        "Alignment markers may remain in published article."
    )
    return False
