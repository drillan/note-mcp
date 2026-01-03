"""Embed insertion helpers for note.com editor.

This module provides functions to insert embeds (YouTube, Twitter, note.com articles)
at placeholder positions in the note.com ProseMirror editor.

Workflow:
1. typing_helpers.py detects embed URLs and inserts placeholders (§§EMBED:url§§)
2. This module finds all placeholders and replaces them with actual embeds
3. insert_embed.py handles the browser automation for embed insertion
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

from note_mcp.browser.insert_embed import EmbedResult, insert_embed_at_cursor

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# note.com editor selectors
_EDITOR_SELECTOR = ".ProseMirror"

# Placeholder markers (must match typing_helpers.py)
_EMBED_PLACEHOLDER_START = "§§EMBED:"
_EMBED_PLACEHOLDER_END = "§§"

# Regex to find embed placeholders: §§EMBED:url§§
_EMBED_PLACEHOLDER_PATTERN = re.compile(r"§§EMBED:(.+?)§§")


async def has_embed_placeholders(page: Page) -> bool:
    """Check if editor contains any embed placeholders.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if any embed placeholder exists in editor.
    """
    editor = page.locator(_EDITOR_SELECTOR)
    text = await editor.text_content()
    logger.debug(f"Editor text content (first 500 chars): {text[:500] if text else 'None'}")
    has_placeholder = text is not None and _EMBED_PLACEHOLDER_START in text
    logger.info(f"has_embed_placeholders: {has_placeholder}, text length: {len(text) if text else 0}")
    return has_placeholder


async def apply_embeds(page: Page, timeout: int = 10000) -> tuple[int, str]:
    """Insert embeds at all placeholder positions in editor.

    Finds embed placeholders one at a time (re-searching after each insertion)
    and uses browser automation to insert actual embeds via note.com's UI.

    Note: We must re-search for placeholders after each embed insertion because
    the DOM is reconstructed when an embed is inserted, invalidating any
    previously cached placeholder locations.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds per embed.

    Returns:
        Tuple of (number of embeds successfully inserted, debug info string).
    """
    debug_steps: list[str] = []
    logger.info("apply_embeds() called - checking for embed placeholders...")
    debug_steps.append("apply_embeds() started")

    has_placeholders = await has_embed_placeholders(page)
    logger.info(f"has_embed_placeholders returned: {has_placeholders}")
    debug_steps.append(f"has_placeholders={has_placeholders}")

    if not has_placeholders:
        logger.info("No embed placeholders found in editor - returning 0")
        debug_steps.append("No placeholders found - returning 0")
        return 0, " → ".join(debug_steps)

    applied_count = 0
    max_iterations = 20  # Safety limit to prevent infinite loops

    for iteration in range(max_iterations):
        logger.info(f"apply_embeds iteration {iteration + 1}/{max_iterations}")
        debug_steps.append(f"iter{iteration + 1}")
        # Re-search for placeholders after each embed insertion
        # because DOM changes after embed is inserted
        placeholders = await _find_embed_placeholders(page)
        logger.info(f"_find_embed_placeholders returned: {placeholders}")
        debug_steps.append(f"found_urls={len(placeholders)}")
        if not placeholders:
            logger.info("No more embed placeholders found in DOM - breaking loop")
            debug_steps.append("no_placeholders_break")
            break

        # Process only the first placeholder found
        url = placeholders[0]
        logger.info(f"Inserting embed {applied_count + 1} for: {url}")
        debug_steps.append(f"processing:{url[:30]}...")

        try:
            result, insert_debug = await _insert_single_embed(page, url, timeout)
            debug_steps.append(f"insert_result:{insert_debug}")
            if result == EmbedResult.SUCCESS:
                applied_count += 1
                logger.info(f"Successfully inserted embed for: {url}")
                debug_steps.append("SUCCESS")
            elif result == EmbedResult.LINK_INSERTED:
                applied_count += 1  # 処理は完了（リンクとして挿入された）
                logger.info(f"Embed inserted as link (URL may be invalid): {url}")
                debug_steps.append("LINK_INSERTED")
            else:
                logger.warning(f"Failed to insert embed for: {url}")
                debug_steps.append("TIMEOUT")
                # If insertion fails, try to remove the placeholder to avoid infinite loop
                await _remove_placeholder_text(page, url)
        except Exception as e:
            logger.warning(f"Error inserting embed for {url}: {e}")
            debug_steps.append(f"ERROR:{type(e).__name__}:{str(e)[:50]}")
            # Remove problematic placeholder to avoid infinite loop
            await _remove_placeholder_text(page, url)

    logger.info(f"Inserted {applied_count} embed(s)")
    debug_steps.append(f"TOTAL:{applied_count}")
    return applied_count, " → ".join(debug_steps)


async def _find_embed_placeholders(page: Page) -> list[str]:
    """Find all embed placeholder URLs in the editor.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        List of URLs from embed placeholders.
    """
    result = await page.evaluate(
        f"""
        () => {{
            const editor = document.querySelector('{_EDITOR_SELECTOR}');
            if (!editor) return {{"urls": [], "text": "Editor not found"}};

            const text = editor.textContent || '';
            const pattern = /§§EMBED:(.+?)§§/g;
            const urls = [];

            let match;
            while ((match = pattern.exec(text)) !== null) {{
                urls.push(match[1]);
            }}
            return {{"urls": urls, "text": text.substring(0, 500)}};
        }}
        """
    )
    urls = result.get("urls", []) if result else []
    text_preview = (result.get("text", "") if result else "")[:200]
    logger.info(f"_find_embed_placeholders result: urls={urls}, text preview={text_preview}")
    return result.get("urls", []) if result else []


async def _insert_single_embed(page: Page, url: str, timeout: int) -> tuple[EmbedResult, str]:
    """Insert a single embed at its placeholder position.

    Args:
        page: Playwright page with note.com editor.
        url: URL to embed.
        timeout: Maximum wait time in milliseconds.

    Returns:
        Tuple of (EmbedResult indicating what happened, debug info string).
    """
    placeholder = f"{_EMBED_PLACEHOLDER_START}{url}{_EMBED_PLACEHOLDER_END}"
    debug_steps: list[str] = []

    # 1. Find and select the placeholder
    select_result = await _select_placeholder(page, placeholder)
    debug_steps.append(f"select={select_result}")
    if not select_result:
        return EmbedResult.TIMEOUT, "select_failed"

    # 2. Delete the selected placeholder
    await page.keyboard.press("Backspace")
    await asyncio.sleep(0.2)
    debug_steps.append("deleted")

    # 3. Insert the actual embed using browser automation
    try:
        result, insert_debug = await insert_embed_at_cursor(page, url, timeout)
        debug_steps.append(f"insert[{insert_debug}]")
        return result, "→".join(debug_steps)
    except Exception as e:
        debug_steps.append(f"insert_error:{type(e).__name__}")
        return EmbedResult.TIMEOUT, "→".join(debug_steps)


async def _select_placeholder(page: Page, placeholder: str) -> bool:
    """Select the placeholder text in the editor.

    Uses JavaScript to find the placeholder text node and select it.

    Args:
        page: Playwright page with note.com editor.
        placeholder: Full placeholder string to find and select.

    Returns:
        True if placeholder was found and selected.
    """
    result = await page.evaluate(
        f"""
        (placeholder) => {{
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
                    // Select the placeholder text
                    const range = document.createRange();
                    const startOffset = node.nodeValue.indexOf(placeholder);
                    const endOffset = startOffset + placeholder.length;
                    range.setStart(node, startOffset);
                    range.setEnd(node, endOffset);

                    const selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    return {{ success: true }};
                }}
            }}
            return {{ success: false, error: 'Placeholder not found in text nodes' }};
        }}
        """,
        placeholder,
    )
    await asyncio.sleep(0.1)

    if not result.get("success"):
        logger.warning(f"Failed to select placeholder: {result.get('error')}")
        return False
    return True


async def _remove_placeholder_text(page: Page, url: str) -> None:
    """Remove a placeholder from the editor when embed insertion fails.

    This prevents infinite loops when a particular embed URL cannot be processed.

    Args:
        page: Playwright page with note.com editor.
        url: URL of the placeholder to remove.
    """
    placeholder = f"{_EMBED_PLACEHOLDER_START}{url}{_EMBED_PLACEHOLDER_END}"

    try:
        if await _select_placeholder(page, placeholder):
            # Delete the selected placeholder
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)
            # Type the URL as plain text (fallback)
            await page.keyboard.type(url)
            await asyncio.sleep(0.1)
            logger.info(f"Replaced failed placeholder with plain URL: {url}")
    except Exception as e:
        logger.warning(f"Could not remove placeholder for {url}: {e}")
