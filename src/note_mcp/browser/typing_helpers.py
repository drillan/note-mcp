"""Typing helpers for browser automation.

Provides functions to type Markdown content into ProseMirror editors
with proper handling for lists and blockquotes.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# Regex patterns for Markdown list and blockquote detection
_UNORDERED_LIST_PATTERN = re.compile(r"^[-*+]\s+(.*)$")
_ORDERED_LIST_PATTERN = re.compile(r"^(\d+)\.\s+(.*)$")
_BLOCKQUOTE_PATTERN = re.compile(r"^>\s*(.*)$")


async def type_markdown_content(page: Any, content: str) -> None:
    """Type Markdown content with proper handling for lists and blockquotes.

    ProseMirror converts "- " at the start of a line to a list item.
    Once in list mode, pressing Enter creates a new list item automatically.
    So for subsequent items, we should NOT type the "- " prefix.

    For blockquotes, typing "> " triggers blockquote mode.
    Subsequent lines within the same blockquote use Shift+Enter for soft breaks
    (which creates <br> tags), preserving multiline content in a single blockquote.

    Args:
        page: Playwright page object
        content: Markdown content to type
    """
    lines = content.split("\n")
    in_unordered_list = False
    in_ordered_list = False
    in_blockquote = False

    for i, line in enumerate(lines):
        # Check for blockquote line
        bq_match = _BLOCKQUOTE_PATTERN.match(line)
        if bq_match:
            bq_content = bq_match.group(1)
            if in_blockquote:
                # Already in blockquote, use Shift+Enter for soft break (creates <br>)
                await page.keyboard.press("Shift+Enter")
                if bq_content:
                    await page.keyboard.type(bq_content)
            else:
                # Start new blockquote, type with prefix to trigger blockquote mode
                await page.keyboard.type("> " + bq_content)
                in_blockquote = True
            in_unordered_list = False
            in_ordered_list = False
            continue

        # Exit blockquote mode if we were in one
        if in_blockquote:
            # Press Enter to exit blockquote
            await page.keyboard.press("Enter")
            in_blockquote = False

        # Check for unordered list item
        ul_match = _UNORDERED_LIST_PATTERN.match(line)
        if ul_match:
            if in_unordered_list:
                # Already in list, just type content without prefix
                await page.keyboard.type(ul_match.group(1))
            else:
                # Start new list, type with prefix
                await page.keyboard.type(line)
                in_unordered_list = True
            in_ordered_list = False
        # Check for ordered list item
        elif ol_match := _ORDERED_LIST_PATTERN.match(line):
            if in_ordered_list:
                # Already in list, just type content without prefix
                await page.keyboard.type(ol_match.group(2))
            else:
                # Start new list, type with prefix
                await page.keyboard.type(line)
                in_ordered_list = True
            in_unordered_list = False
        else:
            # Not a list item
            if line:
                await page.keyboard.type(line)
            in_unordered_list = False
            in_ordered_list = False

        # Press Enter between lines (for non-blockquote content)
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        if i < len(lines) - 1:
            if not _BLOCKQUOTE_PATTERN.match(next_line):
                await page.keyboard.press("Enter")
            elif not in_blockquote:
                # Moving from non-blockquote to blockquote, press Enter
                await page.keyboard.press("Enter")
