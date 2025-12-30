"""Typing helpers for browser automation.

Provides functions to type Markdown content into ProseMirror editors
with proper handling for lists, blockquotes, citations, code blocks, and strikethrough.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Regex patterns for Markdown list, blockquote, and code block detection
_UNORDERED_LIST_PATTERN = re.compile(r"^[-*+]\s+(.*)$")
_ORDERED_LIST_PATTERN = re.compile(r"^(\d+)\.\s+(.*)$")
_BLOCKQUOTE_PATTERN = re.compile(r"^>\s*(.*)$")
# Code block fence pattern: ``` optionally followed by language identifier
_CODE_FENCE_PATTERN = re.compile(r"^```(\w*)$")
# Citation pattern: em-dash followed by space and text
# Matches: "— Source" or "— Source (https://example.com)"
_CITATION_PATTERN = re.compile(r"^—\s+(.+)$")
# Citation URL pattern: "Text (URL)"
_CITATION_URL_PATTERN = re.compile(r"^(.+?)\s+\((\S+)\)\s*$")
# Strikethrough pattern: ~~text~~
_STRIKETHROUGH_PATTERN = re.compile(r"~~(.+?)~~")


async def _type_with_strikethrough(page: Any, text: str) -> None:
    """Type text with proper strikethrough handling for ProseMirror.

    ProseMirror requires a SPACE after ~~text~~ to trigger the markdown-to-HTML
    conversion. Without a trailing space, the pattern remains as literal text.
    This function types strikethrough patterns and adds a temporary space to
    trigger conversion, then removes it with backspace if needed.

    Args:
        page: Playwright page object
        text: Text that may contain ~~strikethrough~~ patterns
    """
    if not text:
        return

    # Check if text contains strikethrough patterns
    if "~~" not in text:
        # No strikethrough, type normally
        await page.keyboard.type(text)
        return

    # Split text by strikethrough pattern, keeping the matched groups
    parts = _STRIKETHROUGH_PATTERN.split(text)

    for i, part in enumerate(parts):
        if not part:
            continue

        if i % 2 == 0:
            # Even indices are normal text (outside ~~ markers)
            await page.keyboard.type(part)
        else:
            # Odd indices are strikethrough content (inside ~~ markers)
            # Type the strikethrough pattern
            await page.keyboard.type(f"~~{part}~~")
            # Space triggers ProseMirror to convert ~~text~~ to <s>text</s>
            await page.keyboard.type(" ")
            await asyncio.sleep(0.1)  # Brief pause for conversion
            # Check if there's more content after this strikethrough
            has_more_content = i + 1 < len(parts) and parts[i + 1]
            if has_more_content and not parts[i + 1].startswith(" "):
                # Remove the space if next content doesn't start with space
                await page.keyboard.press("Backspace")


async def _input_citation_to_figcaption(page: Any, citation: str) -> None:
    """Input citation text into the last figcaption element.

    Uses JavaScript to find and interact with the figcaption element
    since it requires special handling in ProseMirror.

    Args:
        page: Playwright page object
        citation: Citation text to input (without em-dash prefix)
    """
    # Check for URL pattern: "Text (URL)"
    # For now, extract text part only. URL linking is not yet supported
    # because ProseMirror requires special handling for hyperlinks.
    url_match = _CITATION_URL_PATTERN.match(citation)
    citation_text = url_match.group(1).strip() if url_match else citation

    # Use JavaScript to find and focus the figcaption element
    # The figcaption is inside the figure element that contains the blockquote
    js_code = """
    () => {
        // Find all figcaption elements
        const figcaptions = document.querySelectorAll('figure figcaption');
        if (figcaptions.length === 0) return false;

        // Get the last figcaption (most recently created)
        const figcaption = figcaptions[figcaptions.length - 1];
        if (!figcaption) return false;

        // Click to focus
        figcaption.click();

        // Try to focus the figcaption or its editable child
        const editable = figcaption.querySelector('[contenteditable="true"]') || figcaption;
        if (editable) {
            editable.focus();
            // Place cursor at end
            const range = document.createRange();
            range.selectNodeContents(editable);
            range.collapse(false);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        }

        return true;
    }
    """

    # Wait a bit for the blockquote to be fully created
    await asyncio.sleep(0.3)

    # Execute JavaScript to focus figcaption
    result = await page.evaluate(js_code)

    if result:
        # Wait for focus
        await asyncio.sleep(0.1)
        # Type the citation
        await page.keyboard.type(citation_text)
        # Wait for input to be processed
        await asyncio.sleep(0.1)
    else:
        logger.warning(f"Failed to find figcaption element for citation: {citation_text}")


async def type_markdown_content(page: Any, content: str) -> None:
    """Type Markdown content with proper handling for lists, blockquotes, citations, and code blocks.

    ProseMirror converts "- " at the start of a line to a list item.
    Once in list mode, pressing Enter creates a new list item automatically.
    So for subsequent items, we should NOT type the "- " prefix.

    For blockquotes, typing "> " triggers blockquote mode.
    Subsequent lines within the same blockquote use Shift+Enter for soft breaks
    (which creates <br> tags), preserving multiline content in a single blockquote.

    Citations are detected by em-dash at the start of blockquote lines:
    - "— Source" becomes figcaption text
    - "— Source (URL)" becomes figcaption with link

    For code blocks, typing "``` " (with space) triggers code block mode.
    The content is typed directly without fence markers, and the block
    is exited by pressing ArrowDown multiple times to move past the block.

    Args:
        page: Playwright page object
        content: Markdown content to type
    """
    lines = content.split("\n")
    in_unordered_list = False
    in_ordered_list = False
    in_blockquote = False
    in_code_block = False
    pending_citation: str | None = None  # Citation to add after exiting blockquote

    for i, line in enumerate(lines):
        # Strip line for pattern matching (handles \r from Windows line endings)
        stripped_line = line.strip()

        # Check for code fence (``` or ```language)
        code_fence_match = _CODE_FENCE_PATTERN.match(stripped_line)
        if code_fence_match:
            if in_code_block:
                # Closing fence - exit code block
                # In ProseMirror, press ArrowDown multiple times to exit code block
                # and position cursor below it
                for _ in range(3):
                    await page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.05)
                in_code_block = False
                # Press Enter to start new paragraph for next content
                if i < len(lines) - 1:
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(0.1)
            else:
                # Opening fence - enter code block mode
                # Type ``` followed by space to trigger ProseMirror code block
                # Note: note.com's ProseMirror uses space (not Enter) to trigger code block
                await page.keyboard.type("``` ")
                await asyncio.sleep(0.2)
                in_code_block = True
            in_unordered_list = False
            in_ordered_list = False
            in_blockquote = False
            continue

        # If in code block, type content directly
        if in_code_block:
            if line:
                await page.keyboard.type(line)
            # Use Enter for line breaks within code block
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if i < len(lines) - 1 and not _CODE_FENCE_PATTERN.match(next_line):
                await page.keyboard.press("Enter")
            continue

        # Check for blockquote line
        bq_match = _BLOCKQUOTE_PATTERN.match(line)
        if bq_match:
            bq_content = bq_match.group(1)

            # Check if this line is a citation (starts with em-dash)
            citation_match = _CITATION_PATTERN.match(bq_content)
            if citation_match:
                # Store citation for later input into figcaption
                pending_citation = citation_match.group(1)
                # Don't type the citation line into the blockquote
                continue

            if in_blockquote:
                # Already in blockquote, use Shift+Enter for soft break (creates <br>)
                await page.keyboard.press("Shift+Enter")
                if bq_content:
                    await _type_with_strikethrough(page, bq_content)
            else:
                # Start new blockquote, type with prefix to trigger blockquote mode
                await page.keyboard.type("> ")
                await _type_with_strikethrough(page, bq_content)
                in_blockquote = True
            in_unordered_list = False
            in_ordered_list = False
            continue

        # Exit blockquote mode if we were in one
        if in_blockquote:
            # Press Enter to exit blockquote
            await page.keyboard.press("Enter")
            in_blockquote = False

            # If there's a pending citation, input it to figcaption
            if pending_citation:
                await _input_citation_to_figcaption(page, pending_citation)
                pending_citation = None
                # After citation input, we need to move focus back to main editor
                # Press Enter to continue with next content
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.1)
                # Click on the editor to refocus
                await page.locator(".ProseMirror").first.click()
                await asyncio.sleep(0.1)

        # Check for unordered list item
        ul_match = _UNORDERED_LIST_PATTERN.match(line)
        if ul_match:
            if in_unordered_list:
                # Already in list, just type content without prefix
                await _type_with_strikethrough(page, ul_match.group(1))
            else:
                # Start new list, type prefix then content
                prefix_match = re.match(r"^([-*+]\s+)", line)
                prefix = prefix_match.group(1) if prefix_match else "- "
                await page.keyboard.type(prefix)
                await _type_with_strikethrough(page, ul_match.group(1))
                in_unordered_list = True
            in_ordered_list = False
        # Check for ordered list item
        elif ol_match := _ORDERED_LIST_PATTERN.match(line):
            if in_ordered_list:
                # Already in list, just type content without prefix
                await _type_with_strikethrough(page, ol_match.group(2))
            else:
                # Start new list, type prefix then content
                prefix = f"{ol_match.group(1)}. "
                await page.keyboard.type(prefix)
                await _type_with_strikethrough(page, ol_match.group(2))
                in_ordered_list = True
            in_unordered_list = False
        else:
            # Not a list item
            if line:
                await _type_with_strikethrough(page, line)
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

    # Handle pending citation if blockquote was the last element
    if in_blockquote and pending_citation:
        # Exit blockquote first
        await page.keyboard.press("Enter")
        # Input citation to figcaption
        await _input_citation_to_figcaption(page, pending_citation)
