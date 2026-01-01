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
_EDITOR_SELECTOR = ".p-editorBody"
_ALIGN_BUTTON_SELECTOR = 'button[aria-label="文章の配置"]'

# Alignment menu item texts
_ALIGN_CENTER_TEXT = "中央寄せ"
_ALIGN_RIGHT_TEXT = "右寄せ"
_ALIGN_LEFT_TEXT = "指定なし"


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
    """Select the placeholder text including markers in the editor.

    If multiple placeholders have identical text content, only the first match
    is selected and processed.

    Args:
        page: Playwright page with note.com editor.
        alignment_type: 'center', 'right', or 'left'.
        text_content: The text content within the placeholder.

    Returns:
        True if text was successfully selected.
    """
    start_marker = f"§§ALIGN_{alignment_type.upper()}§§"
    full_placeholder = f"{start_marker}{text_content}{ALIGN_END}"

    result = await page.evaluate(
        f"""
        () => {{
            const placeholder = `{full_placeholder}`;
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
                    // Select the entire placeholder
                    const range = document.createRange();
                    const offset = node.nodeValue.indexOf(placeholder);
                    range.setStart(node, offset);
                    range.setEnd(node, offset + placeholder.length);

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
    await asyncio.sleep(0.2)

    if not result.get("success"):
        logger.warning(f"Failed to select placeholder: {result.get('error')}")
        return False
    return True


async def _click_alignment_button(page: Page, timeout: int) -> None:
    """Click the alignment button in the formatting toolbar.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds.
    """
    align_button = page.locator(_ALIGN_BUTTON_SELECTOR).first
    await align_button.wait_for(state="visible", timeout=timeout)
    await align_button.click()
    await asyncio.sleep(0.3)


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
    await asyncio.sleep(0.2)


async def _remove_placeholder_markers(
    page: Page,
    alignment_type: str,
    text_content: str,
) -> bool:
    """Remove placeholder markers, keeping only the text content.

    After alignment is applied, we need to remove the §§ALIGN_*§§ markers
    so only the actual text remains. If multiple placeholders have identical
    text content, only the first match is processed.

    Args:
        page: Playwright page with note.com editor.
        alignment_type: 'center', 'right', or 'left'.
        text_content: The text content to keep.

    Returns:
        True if markers were successfully removed, False otherwise.
    """
    start_marker = f"§§ALIGN_{alignment_type.upper()}§§"
    full_placeholder = f"{start_marker}{text_content}{ALIGN_END}"

    # Use JavaScript to find and replace the placeholder with clean text
    result = await page.evaluate(
        f"""
        () => {{
            const editor = document.querySelector('{_EDITOR_SELECTOR}');
            if (!editor) return {{ success: false, error: 'Editor not found' }};

            const walker = document.createTreeWalker(
                editor,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            let node;
            while (node = walker.nextNode()) {{
                if (node.nodeValue && node.nodeValue.includes('{full_placeholder}')) {{
                    // Replace placeholder with clean text
                    node.nodeValue = node.nodeValue.replace(
                        `{full_placeholder}`,
                        `{text_content}`
                    );
                    return {{ success: true }};
                }}
            }}
            return {{ success: false, error: 'Placeholder not found' }};
        }}
    """
    )
    await asyncio.sleep(0.1)

    if not result.get("success"):
        logger.warning(
            f"Failed to remove placeholder markers for: {text_content[:30]}... "
            f"({result.get('error')}). Alignment markers may remain in published article."
        )
        return False
    return True
