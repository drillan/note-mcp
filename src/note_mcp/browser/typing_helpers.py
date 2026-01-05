"""Typing helpers for browser automation.

Provides functions to type Markdown content into ProseMirror editors
with proper handling for lists, blockquotes, citations, code blocks,
text alignment, embeds, and math formulas.

Supported inline formatting with native ProseMirror conversion:
- Bold (**text** + space → <strong>text</strong>)
- Strikethrough (~~text~~ + space → <s>text</s>)
- Math formulas ($${formula}$$ and $$formula$$ → KaTeX rendering) (Issue #101)

NOT supported for native conversion (requires UI automation):
- Links ([text](url)) - No InputRule exists; use insert_link_at_cursor() from insert_link.py

Processing order (most specific pattern first):
1. Math formulas $${...}$$ and $$...$$ - parsed first, typed with markers preserved
2. Links [text](url) - parsed second, inserted via insert_link_at_cursor()
3. Bold **text** - processed third (double asterisk)
4. Strikethrough ~~text~~ - processed last (double tilde)

Note: Italic (*text*) and inline code (`code`) are NOT supported
by note.com's ProseMirror schema. Technical investigation revealed (verified: 2025-12):
- `em`/`italic` mark does not exist in the schema
- `code` mark is forbidden in paragraph nodes (only "strong strike link" allowed)
- `link` mark exists in schema but NO markdown InputRule for [text](url) conversion
These are platform limitations and cannot be worked around via typing.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
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
# Link pattern: [text](url)
_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# Bold pattern: **text**
_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
# Math formula patterns (Issue #101)
# note.com uses $$ for math formulas (KaTeX notation):
# - Inline math: $${formula}$$ (double dollar signs WITH curly braces)
# - Display math: $$formula$$ (double dollar signs WITHOUT curly braces)
_MATH_INLINE_PATTERN = re.compile(r"\$\$\{(.+?)\}\$\$", re.DOTALL)
_MATH_DISPLAY_PATTERN = re.compile(r"\$\$([^{].*?)\$\$", re.DOTALL)
# Horizontal line pattern: --- (must be standalone line)
_HR_PATTERN = re.compile(r"^---$")
# Ruby notation pattern: ｜漢字《かんじ》 or |漢字《かんじ》 or 漢字《かんじ》
# Note: Vertical bar is REQUIRED by note.com, but pattern accepts omission for detection
_RUBY_PATTERN = re.compile(r"[｜|]?([一-龯ぁ-んァ-ヶー]+)《([^》]+)》")
# TOC pattern: [TOC] alone on a line
_TOC_PATTERN = re.compile(r"^\[TOC\]$")
# TOC placeholder for browser insertion (text marker, not HTML comment)
# Must match TOC_PLACEHOLDER in toc_helpers.py
_TOC_PLACEHOLDER = "§§TOC§§"
# Heading patterns: ## for h2, ### for h3, etc.
# ProseMirror requires typing the pattern followed by space to trigger conversion
_HEADING_PATTERN = re.compile(r"^(#{2,6})\s+(.*)$")

# Text alignment patterns:
# ->text<- : center alignment
# ->text   : right alignment (no closing marker)
# <-text   : left alignment (opening marker only)
_ALIGN_CENTER_PATTERN = re.compile(r"^->(.+)<-$")
_ALIGN_RIGHT_PATTERN = re.compile(r"^->(.+)$")
_ALIGN_LEFT_PATTERN = re.compile(r"^<-(.+)$")

# Text alignment placeholders (must match text_align_helpers.py)
_ALIGN_CENTER_PLACEHOLDER = "§§ALIGN_CENTER§§"
_ALIGN_RIGHT_PLACEHOLDER = "§§ALIGN_RIGHT§§"
_ALIGN_LEFT_PLACEHOLDER = "§§ALIGN_LEFT§§"
_ALIGN_END_PLACEHOLDER = "§§/ALIGN§§"

# Embed URL patterns (must match insert_embed.py)
# Supported services: YouTube, Twitter/X, note.com articles
_EMBED_YOUTUBE_PATTERN = re.compile(r"^https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+$")
_EMBED_TWITTER_PATTERN = re.compile(r"^https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+$")
_EMBED_NOTE_PATTERN = re.compile(r"^https?://note\.com/\w+/n/\w+$")

# Embed placeholder format: §§EMBED:url§§
_EMBED_PLACEHOLDER_START = "§§EMBED:"
_EMBED_PLACEHOLDER_END = "§§"


def _is_embed_url(url: str) -> bool:
    """Check if URL should be embedded (YouTube, Twitter, note.com).

    Args:
        url: URL string to check.

    Returns:
        True if URL matches a supported embed service.
    """
    is_youtube = bool(_EMBED_YOUTUBE_PATTERN.match(url))
    is_twitter = bool(_EMBED_TWITTER_PATTERN.match(url))
    is_note = bool(_EMBED_NOTE_PATTERN.match(url))
    is_embed = is_youtube or is_twitter or is_note
    if is_embed:
        logger.info(f"_is_embed_url: {url} -> youtube={is_youtube}, twitter={is_twitter}, note={is_note}")
    return is_embed


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


async def _type_with_inline_pattern(
    page: Any,
    text: str,
    pattern: re.Pattern[str],
    formatter: Callable[[re.Match[str]], str],
) -> str:
    """Generic inline pattern handler for ProseMirror.

    Processes the first match of a pattern in text, types it with proper trigger,
    and returns the remaining text for further processing.

    Args:
        page: Playwright page object
        text: Text that may contain the pattern
        pattern: Compiled regex pattern to search for
        formatter: Function that takes a match and returns the formatted string to type

    Returns:
        Remaining text after first pattern is processed, or empty string if no match.
    """
    match = pattern.search(text)
    if not match:
        await page.keyboard.type(text)
        return ""

    # Type text before pattern
    before = text[: match.start()]
    if before:
        await page.keyboard.type(before)

    # Type formatted pattern with space trigger
    await page.keyboard.type(formatter(match))
    await page.keyboard.type(" ")
    await asyncio.sleep(0.1)

    # Return remaining text (remove trigger space if needed)
    remaining = text[match.end() :]
    if remaining and not remaining.startswith(" "):
        await page.keyboard.press("Backspace")

    return remaining


async def _type_with_link(page: Any, text: str) -> str:
    """Process link patterns [text](url) via UI automation.

    ProseMirror has NO InputRule for [text](url) conversion.
    This function uses insert_link_at_cursor() for proper link insertion.

    Args:
        page: Playwright page object
        text: Text that may contain [text](url) patterns

    Returns:
        Remaining text after first link is processed, or empty string if no match.
    """
    from note_mcp.browser.insert_link import LinkResult, insert_link_at_cursor

    match = _LINK_PATTERN.search(text)
    if not match:
        await page.keyboard.type(text)
        return ""

    # Type text before link
    before = text[: match.start()]
    if before:
        await page.keyboard.type(before)

    # Extract link text and URL
    link_text = match.group(1)
    link_url = match.group(2)

    # Insert link via UI automation (Ctrl+K dialog)
    result, debug = await insert_link_at_cursor(page, link_text, link_url)
    if result != LinkResult.SUCCESS:
        logger.error(
            f"Link insertion FAILED for [{link_text}]({link_url}): {debug}. "
            "Falling back to plain text (link will NOT be clickable)."
        )
        # Fallback: type as plain text
        await page.keyboard.type(f"[{link_text}]({link_url})")

    # Return remaining text
    return text[match.end() :]


async def _type_with_bold(page: Any, text: str) -> str:
    """Process bold patterns **text** and type with proper trigger."""
    return await _type_with_inline_pattern(
        page,
        text,
        _BOLD_PATTERN,
        lambda m: f"**{m.group(1)}**",
    )


async def _type_with_math_formula(page: Any, text: str) -> str:
    """Process math formula patterns and type them preserving $$ markers.

    note.com's ProseMirror editor recognizes $$ patterns and renders them
    as KaTeX math formulas. This function ensures the $$ markers are preserved
    during typing so the editor can process them correctly.

    Patterns:
    - Inline: $${formula}$$ (double dollar with curly braces)
    - Display: $$formula$$ (double dollar without curly braces)

    Args:
        page: Playwright page object
        text: Text that may contain math formula patterns

    Returns:
        Remaining text after first math pattern is processed, or empty string if no match.
    """
    # Check for inline math first (more specific pattern)
    inline_match = _MATH_INLINE_PATTERN.search(text)
    display_match = _MATH_DISPLAY_PATTERN.search(text)

    # Find the first match
    match = None
    is_inline = False
    if inline_match and display_match:
        if inline_match.start() <= display_match.start():
            match = inline_match
            is_inline = True
        else:
            match = display_match
    elif inline_match:
        match = inline_match
        is_inline = True
    elif display_match:
        match = display_match

    if not match:
        await page.keyboard.type(text)
        return ""

    # Type text before math formula
    before = text[: match.start()]
    if before:
        await page.keyboard.type(before)

    # Type the math formula with $$ markers preserved
    formula = match.group(1)
    if is_inline:
        # Inline: $${formula}$$
        await page.keyboard.type(f"$${{{formula}}}$$")
    else:
        # Display: $$formula$$
        await page.keyboard.type(f"$${formula}$$")

    logger.debug(f"Typed math formula: {'inline' if is_inline else 'display'} - {formula[:30]}...")

    # Return remaining text
    return text[match.end() :]


async def _type_with_inline_formatting(page: Any, text: str) -> None:
    """Process all inline formatting patterns in correct order.

    Supported formats (note.com ProseMirror schema limitations):
    - Math formulas $${...}$$ and $$...$$ - processed first (Issue #101)
    - Links [text](url) - bracket/parenthesis delimited
    - Bold **text** - double asterisk
    - Strikethrough ~~text~~ - double tilde

    Note: Italic (*text*) and inline code (`code`) are NOT supported
    by note.com's ProseMirror schema. These marks do not exist in
    the editor's schema, so they cannot be applied.

    This function processes one pattern at a time, recursively handling
    remaining text until all patterns are processed.

    Args:
        page: Playwright page object
        text: Text that may contain inline formatting patterns
    """
    if not text:
        return

    # Check for math formula patterns first (highest priority for Issue #101)
    # Math patterns must be processed before other patterns to preserve $$ markers
    if _MATH_INLINE_PATTERN.search(text) or _MATH_DISPLAY_PATTERN.search(text):
        remaining = await _type_with_math_formula(page, text)
        if remaining:
            await _type_with_inline_formatting(page, remaining)
        return

    # Check for link pattern (most specific among remaining patterns)
    if _LINK_PATTERN.search(text):
        remaining = await _type_with_link(page, text)
        if remaining:
            await _type_with_inline_formatting(page, remaining)
        return

    # Check for bold pattern
    if _BOLD_PATTERN.search(text):
        remaining = await _type_with_bold(page, text)
        if remaining:
            await _type_with_inline_formatting(page, remaining)
        return

    # Check for strikethrough pattern
    if "~~" in text:
        await _type_with_strikethrough(page, text)
        return

    # No inline formatting, type as plain text
    await page.keyboard.type(text)


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

        # Check for [TOC] marker
        if _TOC_PATTERN.match(stripped_line):
            # Type placeholder for TOC insertion
            # insert_toc_at_placeholder() will replace this with actual TOC
            await page.keyboard.type(_TOC_PLACEHOLDER)
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
            in_unordered_list = False
            in_ordered_list = False
            in_blockquote = False
            continue

        # Check for horizontal line pattern (---)
        if _HR_PATTERN.match(stripped_line):
            await page.keyboard.type("---")
            await page.keyboard.type(" ")  # Trigger conversion
            await asyncio.sleep(0.1)
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
            in_unordered_list = False
            in_ordered_list = False
            in_blockquote = False
            continue

        # Check for text alignment patterns
        # Order matters: check center first (->text<-), then right (->text), then left (<-text)
        align_center_match = _ALIGN_CENTER_PATTERN.match(stripped_line)
        align_right_match = _ALIGN_RIGHT_PATTERN.match(stripped_line)
        align_left_match = _ALIGN_LEFT_PATTERN.match(stripped_line)

        if align_center_match:
            # Center alignment: ->text<-
            content = align_center_match.group(1)
            placeholder = f"{_ALIGN_CENTER_PLACEHOLDER}{content}{_ALIGN_END_PLACEHOLDER}"
            await page.keyboard.type(placeholder)
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
            in_unordered_list = False
            in_ordered_list = False
            in_blockquote = False
            continue
        elif align_right_match and not align_center_match:
            # Right alignment: ->text (but not ->text<-)
            content = align_right_match.group(1)
            placeholder = f"{_ALIGN_RIGHT_PLACEHOLDER}{content}{_ALIGN_END_PLACEHOLDER}"
            await page.keyboard.type(placeholder)
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
            in_unordered_list = False
            in_ordered_list = False
            in_blockquote = False
            continue
        elif align_left_match:
            # Left alignment: <-text
            content = align_left_match.group(1)
            placeholder = f"{_ALIGN_LEFT_PLACEHOLDER}{content}{_ALIGN_END_PLACEHOLDER}"
            await page.keyboard.type(placeholder)
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
            in_unordered_list = False
            in_ordered_list = False
            in_blockquote = False
            continue

        # Check for standalone embed URL (YouTube, Twitter, note.com articles)
        # These get converted to embed placeholders for later browser insertion
        if _is_embed_url(stripped_line):
            placeholder = f"{_EMBED_PLACEHOLDER_START}{stripped_line}{_EMBED_PLACEHOLDER_END}"
            logger.info(f"Typing embed placeholder: {placeholder}")
            await page.keyboard.type(placeholder)
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
            in_unordered_list = False
            in_ordered_list = False
            in_blockquote = False
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
                    await _type_with_inline_formatting(page, bq_content)
            else:
                # Start new blockquote, type with prefix to trigger blockquote mode
                await page.keyboard.type("> ")
                await _type_with_inline_formatting(page, bq_content)
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
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.1)
                # Use ArrowDown multiple times to reliably exit blockquote structure
                # ProseMirror blockquote with figcaption requires multiple presses
                # to move past the block (same pattern as code block exit)
                for _ in range(3):
                    await page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.05)
                await asyncio.sleep(0.1)
                # Create a new paragraph to ensure cursor is at start of a new line
                # This is required for heading conversion (## ) to work properly
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.1)

        # Check for heading pattern (## h2, ### h3, etc.)
        heading_match = _HEADING_PATTERN.match(stripped_line)
        if heading_match:
            heading_level = heading_match.group(1)  # "##", "###", etc.
            heading_content = heading_match.group(2)  # The heading text

            # Type heading prefix with space to trigger ProseMirror conversion
            # ProseMirror converts "## " at the start of a line to <h2>
            await page.keyboard.type(f"{heading_level} ")
            await asyncio.sleep(0.1)  # Wait for conversion

            # Type the heading content
            if heading_content:
                await _type_with_inline_formatting(page, heading_content)

            # Reset list/blockquote states
            in_unordered_list = False
            in_ordered_list = False
            in_blockquote = False

            # Press Enter for next line
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
            continue

        # Check for unordered list item
        ul_match = _UNORDERED_LIST_PATTERN.match(line)
        if ul_match:
            if in_unordered_list:
                # Already in list, just type content without prefix
                await _type_with_inline_formatting(page, ul_match.group(1))
            else:
                # Start new list, type prefix then content
                prefix_match = re.match(r"^([-*+]\s+)", line)
                prefix = prefix_match.group(1) if prefix_match else "- "
                await page.keyboard.type(prefix)
                await _type_with_inline_formatting(page, ul_match.group(1))
                in_unordered_list = True
            in_ordered_list = False
        # Check for ordered list item
        elif ol_match := _ORDERED_LIST_PATTERN.match(line):
            if in_ordered_list:
                # Already in list, just type content without prefix
                await _type_with_inline_formatting(page, ol_match.group(2))
            else:
                # Start new list, type prefix then content
                prefix = f"{ol_match.group(1)}. "
                await page.keyboard.type(prefix)
                await _type_with_inline_formatting(page, ol_match.group(2))
                in_ordered_list = True
            in_unordered_list = False
        else:
            # Not a list item
            if line:
                await _type_with_inline_formatting(page, line)
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
