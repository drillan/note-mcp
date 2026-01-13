"""Markdown to HTML conversion utility.

Uses markdown-it-py for CommonMark-compliant conversion.
"""

import re
import uuid

from markdown_it import MarkdownIt

from note_mcp.api.embeds import (
    NOTE_PATTERN,
    TWITTER_PATTERN,
    YOUTUBE_PATTERN,
    generate_embed_html,
    get_embed_service,
)

# Pre-compiled regex patterns for performance
# TOC pattern: [TOC] must be alone on a line
_TOC_PATTERN = re.compile(r"^\[TOC\]$", re.MULTILINE)
# TOC placeholder (text marker, not HTML comment)
# Must match TOC_PLACEHOLDER in toc_helpers.py
_TOC_PLACEHOLDER = "§§TOC§§"
# Pattern to match TOC placeholder wrapped in paragraph tags (after Markdown conversion)
_TOC_PLACEHOLDER_HTML_PATTERN = re.compile(
    r'<p\s+name="([^"]+)"\s+id="([^"]+)">' + re.escape(_TOC_PLACEHOLDER) + r"</p>",
    re.IGNORECASE,
)

# Note: <li> and <blockquote> are excluded because note.com doesn't add name/id to these tags
_TAG_PATTERN = re.compile(
    r"<(p|h[1-6]|ul|ol|code|hr|div|span)(\s[^>]*)?>",
    re.IGNORECASE,
)
_PRE_PATTERN = re.compile(r"<pre([^>]*)>(.*?)</pre>", re.DOTALL | re.IGNORECASE)
_IMG_IN_P_PATTERN = re.compile(
    r'<p>\s*<img\s+src="([^"]+)"\s+alt="([^"]*)"(?:\s+title="([^"]*)")?\s*/?\s*>\s*</p>',
    re.IGNORECASE,
)
_LANGUAGE_CLASS_PATTERN = re.compile(r'<code[^>]*class="language-[^"]*"[^>]*>')
# Pattern to match li elements with direct text content (not already wrapped in p)
# This matches <li ...>content</li> where content doesn't start with <p
_LI_CONTENT_PATTERN = re.compile(
    r"(<li[^>]*>)(?!<p)([^<]+|(?:(?!</li>).)*?)(</li>)",
    re.IGNORECASE | re.DOTALL,
)
# Pattern to match blockquote elements and their content
_BLOCKQUOTE_PATTERN = re.compile(
    r"(<blockquote[^>]*>)(.*?)(</blockquote>)",
    re.DOTALL | re.IGNORECASE,
)
# Pattern to detect citation line: em-dash followed by space at start of line or after <br>
# Matches: "— Text" or "<br>— Text" at the end of content
_CITATION_PATTERN = re.compile(
    r"(?:^|<br>)(—\s+.+?)(?:</p>|$)",
    re.IGNORECASE,
)
# Pattern to extract URL from citation: "Text (URL)"
_CITATION_URL_PATTERN = re.compile(r"^(.+?)\s+\((\S+)\)\s*$")

# Text alignment patterns (Issue #40)
# Center: ->text<- (must be at start of line, ends with <- at end of line)
# Right: ->text (must be at start of line, no closing marker)
# Left: <-text (must be at start of line)
# Order matters: center must be checked before right to avoid partial matches
_TEXT_ALIGN_CENTER_PATTERN = re.compile(r"^->(.+)<-$", re.MULTILINE)
_TEXT_ALIGN_RIGHT_PATTERN = re.compile(r"^->(.+)$", re.MULTILINE)
_TEXT_ALIGN_LEFT_PATTERN = re.compile(r"^<-(.+)$", re.MULTILINE)

# Pattern to find URLs that are alone on a line (potential embed URLs)
_STANDALONE_URL_PATTERN = re.compile(r"^(https?://\S+)$", re.MULTILINE)


def has_embed_url(content: str) -> bool:
    """Check if content contains URLs that should be embedded.

    Detects YouTube, Twitter/X, and note.com article URLs that appear
    alone on a line (indicating they should be embedded, not linked).

    Args:
        content: Markdown content to check.

    Returns:
        True if content contains embed-worthy URLs.
    """
    # Find all standalone URLs (URLs alone on their own line)
    for match in _STANDALONE_URL_PATTERN.finditer(content):
        url = match.group(1)
        # Check if this URL matches any embed pattern (using api.embeds patterns)
        if YOUTUBE_PATTERN.match(url) or TWITTER_PATTERN.match(url) or NOTE_PATTERN.match(url):
            return True
    return False


# Pattern to match standalone embed URLs in HTML paragraphs
# Matches: <p name="..." id="...">https://youtube.com/watch?v=xxx</p>
# Uses negative lookbehind to exclude paragraphs inside list items
_STANDALONE_EMBED_URL_IN_HTML_PATTERN = re.compile(
    r'(?<!<li>)<p\s+name="[^"]+"\s+id="[^"]+">(\s*)(https?://\S+?)(\s*)</p>',
    re.IGNORECASE,
)


def _convert_standalone_embed_urls(html: str) -> str:
    """Convert standalone embed URLs to figure elements.

    Detects standalone URLs (URLs that are alone in a paragraph) and converts
    supported embed URLs (YouTube, Twitter, note.com) to figure elements.

    This function should be called after markdown conversion and UUID addition,
    but before code block processing.

    Args:
        html: HTML content with paragraphs containing potential embed URLs.

    Returns:
        HTML with embed URLs converted to figure elements.
    """

    def replace_embed_url(match: re.Match[str]) -> str:
        url = match.group(2).strip()

        # Check if this URL is a supported embed URL
        service = get_embed_service(url)
        if service is None:
            # Not an embed URL, keep original paragraph
            return match.group(0)

        # Generate embed HTML
        return generate_embed_html(url, service)

    return _STANDALONE_EMBED_URL_IN_HTML_PATTERN.sub(replace_embed_url, html)


def _generate_uuid() -> str:
    """Generate a UUID for note.com element IDs."""
    return str(uuid.uuid4())


def _extract_citation(blockquote_content: str) -> tuple[str, str]:
    """Extract citation from blockquote content.

    Detects citation lines starting with em-dash (—) followed by space.
    Supports optional URL in parentheses: "— Source (https://example.com)"

    Args:
        blockquote_content: HTML content inside <blockquote> tags

    Returns:
        Tuple of (modified_content, figcaption_html):
        - modified_content: blockquote content with citation line removed
        - figcaption_html: HTML for figcaption element content (may be empty)

    Examples:
        >>> _extract_citation("<p>Quote<br>— Source</p>")
        ('<p>Quote</p>', 'Source')
        >>> _extract_citation("<p>Quote<br>— Source (https://example.com)</p>")
        ('<p>Quote</p>', '<a href="https://example.com">Source</a>')
    """
    # Look for citation pattern: "<br>— text" or "— text" at end of content
    # The pattern searches within <p> tags
    match = _CITATION_PATTERN.search(blockquote_content)
    if not match:
        return blockquote_content, ""

    citation_with_dash = match.group(1)  # "— Text" or "— Text (URL)"
    citation_text = citation_with_dash[2:].strip()  # Remove "— " prefix

    # Empty citation text
    if not citation_text:
        return blockquote_content, ""

    # Remove the citation line from blockquote content
    # Handle both "<br>— text" and standalone "— text"
    full_match = match.group(0)
    modified_content = blockquote_content.replace(full_match, "</p>")

    # Check for URL pattern: "Text (URL)"
    url_match = _CITATION_URL_PATTERN.match(citation_text)
    if url_match:
        text = url_match.group(1).strip()
        url = url_match.group(2)
        figcaption_html = f'<a href="{url}">{text}</a>'
    else:
        figcaption_html = citation_text

    return modified_content, figcaption_html


def _convert_text_alignment(content: str) -> str:
    """Convert text alignment Markdown notation to internal placeholders.

    This function processes text alignment markers BEFORE markdown conversion.
    It converts the custom notation to placeholders that will be converted
    to proper HTML after markdown processing.

    Notation:
        ->text<- : center alignment
        ->text   : right alignment
        <-text   : left alignment

    Args:
        content: Markdown content with alignment markers

    Returns:
        Content with alignment markers converted to placeholders
    """
    # Protect code blocks from alignment processing
    code_blocks: list[tuple[str, str]] = []

    def protect_code_block(match: re.Match[str]) -> str:
        placeholder = f"__CODE_BLOCK_ALIGN_{len(code_blocks)}__"
        code_blocks.append((placeholder, match.group(0)))
        return placeholder

    # Temporarily replace code blocks (fenced and inline)
    protected = re.sub(r"```[\s\S]*?```", protect_code_block, content)
    protected = re.sub(r"`[^`]+`", protect_code_block, protected)

    # Convert alignment markers to placeholders
    # Order matters: center first (more specific), then right/left
    protected = _TEXT_ALIGN_CENTER_PATTERN.sub(r"§§ALIGN_CENTER§§\1§§/ALIGN§§", protected)
    protected = _TEXT_ALIGN_RIGHT_PATTERN.sub(r"§§ALIGN_RIGHT§§\1§§/ALIGN§§", protected)
    protected = _TEXT_ALIGN_LEFT_PATTERN.sub(r"§§ALIGN_LEFT§§\1§§/ALIGN§§", protected)

    # Restore code blocks
    for placeholder, original in code_blocks:
        protected = protected.replace(placeholder, original)

    return protected


def _apply_text_alignment_to_html(html: str) -> str:
    """Convert text alignment placeholders to HTML style attributes.

    This function processes the alignment placeholders created by
    _convert_text_alignment and converts them to proper HTML paragraphs
    with text-align styles.

    Args:
        html: HTML content with alignment placeholders

    Returns:
        HTML with proper text-align styles applied
    """
    # Pattern to match paragraphs containing alignment placeholders
    # The placeholders will be inside <p> tags after markdown conversion
    align_p_pattern = re.compile(
        r"<p([^>]*)>§§ALIGN_(CENTER|RIGHT|LEFT)§§(.*?)§§/ALIGN§§</p>",
        re.DOTALL | re.IGNORECASE,
    )

    def apply_alignment(match: re.Match[str]) -> str:
        attrs = match.group(1)
        alignment = match.group(2).lower()
        content = match.group(3)

        # Add style attribute for text-align
        style = f"text-align: {alignment}"

        # If there are existing attributes, append style
        if attrs and 'style="' in attrs:
            # Append to existing style (unlikely but handle it)
            attrs = attrs.replace('style="', f'style="{style}; ')
        else:
            # Add new style attribute before other attrs
            attrs = f' style="{style}"' + (attrs or "")

        return f"<p{attrs}>{content}</p>"

    return align_p_pattern.sub(apply_alignment, html)


def _wrap_li_content_in_p(html: str) -> str:
    """Wrap list item content in paragraph tags.

    ProseMirror (used by note.com) expects list items to contain
    block content like paragraphs, not just inline text.

    Converts: <li>Item text</li>
    To: <li><p>Item text</p></li>

    Args:
        html: HTML string with list items

    Returns:
        HTML with list item content wrapped in <p> tags
    """

    def wrap_content(match: re.Match[str]) -> str:
        li_open = match.group(1)  # <li ...>
        content = match.group(2)  # text content
        li_close = match.group(3)  # </li>

        # Skip if content is empty or whitespace only
        if not content or not content.strip():
            return match.group(0)

        return f"{li_open}<p>{content.strip()}</p>{li_close}"

    return _LI_CONTENT_PATTERN.sub(wrap_content, html)


def _convert_blockquote_newlines_to_br(html: str) -> str:
    """Convert newlines inside blockquote paragraphs to <br> tags.

    note.com's browser editor uses <br> tags for line breaks inside blockquotes.
    This function converts newlines to <br> tags to match that format.

    Converts:
        <blockquote><p>Line 1
        Line 2</p></blockquote>
    To:
        <blockquote><p>Line 1<br>Line 2</p></blockquote>

    Note: While this generates correct HTML with <br> tags, note.com's API
    sanitizes <br> tags from blockquote content. This is a server-side
    limitation. Content created via browser editor preserves <br> tags,
    but API-submitted content has them stripped.

    Workaround for users: Use separate blockquotes for each line:
        > Line 1

        > Line 2

    Args:
        html: HTML string with blockquotes

    Returns:
        HTML with blockquote paragraph newlines converted to <br> tags
    """
    # Pattern to match <p> content inside blockquotes
    p_in_blockquote_pattern = re.compile(
        r"(<blockquote[^>]*>.*?)(<p[^>]*>)(.*?)(</p>)(.*?</blockquote>)",
        re.DOTALL | re.IGNORECASE,
    )

    def convert_p_newlines(match: re.Match[str]) -> str:
        before_p = match.group(1)  # <blockquote...> and anything before <p>
        p_open = match.group(2)  # <p ...>
        p_content = match.group(3)  # content inside <p>
        p_close = match.group(4)  # </p>
        after_p = match.group(5)  # anything after </p> including </blockquote>

        # Convert newlines to <br> tags (note.com uses <br> without slash)
        p_content = p_content.replace("\n", "<br>")

        return f"{before_p}{p_open}{p_content}{p_close}{after_p}"

    return p_in_blockquote_pattern.sub(convert_p_newlines, html)


def _convert_blockquotes_to_note_format(html: str) -> str:
    """Convert blockquotes to note.com figure format.

    note.com expects blockquotes to be wrapped in <figure> elements:
    <figure name="UUID" id="UUID">
      <blockquote><p name="UUID" id="UUID">content</p></blockquote>
      <figcaption>citation</figcaption>
    </figure>

    Citation is extracted from lines starting with em-dash (—):
    - "— Source" becomes <figcaption>Source</figcaption>
    - "— Source (URL)" becomes <figcaption><a href="URL">Source</a></figcaption>

    This format is required for the API to preserve <br> tags inside blockquotes.

    Args:
        html: HTML string with blockquotes

    Returns:
        HTML with blockquotes wrapped in figure elements
    """
    # Pattern to match blockquote elements
    blockquote_pattern = re.compile(
        r"<blockquote[^>]*>(.*?)</blockquote>",
        re.DOTALL | re.IGNORECASE,
    )

    def wrap_in_figure(match: re.Match[str]) -> str:
        blockquote_content = match.group(1)
        element_id = _generate_uuid()

        # Extract citation if present
        modified_content, figcaption_html = _extract_citation(blockquote_content)

        return (
            f'<figure name="{element_id}" id="{element_id}">'
            f"<blockquote>{modified_content}</blockquote>"
            f"<figcaption>{figcaption_html}</figcaption></figure>"
        )

    return blockquote_pattern.sub(wrap_in_figure, html)


def _add_uuid_to_elements(html: str) -> str:
    """Add name attribute (UUID) to HTML elements.

    note.com requires elements to have unique name attributes.
    Note: <pre> tags are handled separately by _convert_code_blocks_to_note_format.
    Note: <li> tags are excluded because note.com doesn't add name to <li> tags.

    Args:
        html: HTML string

    Returns:
        HTML with name attributes added to elements
    """

    def add_uuid(match: re.Match[str]) -> str:
        tag_name = match.group(1)
        attrs = match.group(2) or ""

        # Skip if already has name attribute
        if 'name="' in attrs:
            return match.group(0)

        element_id = _generate_uuid()
        # note.com requires both 'name' and 'id' attributes for proper content handling
        return f'<{tag_name} name="{element_id}" id="{element_id}"{attrs}>'

    return _TAG_PATTERN.sub(add_uuid, html)


def _convert_images_to_note_format(html: str) -> str:
    """Convert standard HTML img tags to note.com figure format.

    note.com expects images in this format:
    <figure name="UUID" id="UUID">
      <img src="URL" alt="" width="620" height="457"
           contenteditable="false" draggable="false">
      <figcaption></figcaption>
    </figure>

    Args:
        html: HTML string with standard img tags

    Returns:
        HTML with img tags converted to figure format
    """

    def replace_img(match: re.Match[str]) -> str:
        src = match.group(1)
        alt = match.group(2)
        caption = match.group(3) or ""  # titleがなければ空文字
        element_id = _generate_uuid()
        # note.com requires both 'name' and 'id' attributes for proper content handling
        return (
            f'<figure name="{element_id}" id="{element_id}">'
            f'<img src="{src}" alt="{alt}" width="620" height="457" '
            f'contenteditable="false" draggable="false">'
            f"<figcaption>{caption}</figcaption></figure>"
        )

    return _IMG_IN_P_PATTERN.sub(replace_img, html)


def _convert_code_blocks_to_note_format(html: str) -> str:
    """Convert code blocks to note.com format and handle newlines.

    note.com requires:
    - <pre class="codeBlock"> with name and id attributes
    - <code> without language class
    - Actual newlines preserved inside code blocks
    - Newlines removed from other HTML elements

    Uses placeholder approach to preserve newlines in code blocks
    while removing them from the rest of the HTML.

    Args:
        html: HTML string with code blocks

    Returns:
        HTML with code blocks in note.com format
    """
    pre_blocks: list[str] = []

    def convert_pre_block(match: re.Match[str]) -> str:
        """Convert pre block to note.com format and store for later restoration."""
        content = match.group(2)

        # Generate fresh UUIDs for code blocks
        element_id = _generate_uuid()

        # Remove language class from <code> tag
        # markdown-it-py adds class="language-xxx" which note.com doesn't use
        content = _LANGUAGE_CLASS_PATTERN.sub("<code>", content)

        # Build note.com format: <pre name="..." id="..." class="codeBlock">
        # note.com requires both 'name' and 'id' attributes for proper content handling
        pre_block = f'<pre name="{element_id}" id="{element_id}" class="codeBlock">{content}</pre>'
        pre_blocks.append(pre_block)

        return f"__PRE_BLOCK_{len(pre_blocks) - 1}__"

    # Replace pre blocks with placeholders
    result = _PRE_PATTERN.sub(convert_pre_block, html)

    # Remove newlines from the rest of the HTML
    result = result.replace("\n", "")

    # Restore pre blocks with their preserved newlines
    for i, block in enumerate(pre_blocks):
        result = result.replace(f"__PRE_BLOCK_{i}__", block)

    return result


def _has_toc_placeholder(content: str) -> bool:
    """Check if content contains [TOC] placeholder.

    Args:
        content: Markdown content to check.

    Returns:
        True if [TOC] placeholder exists on its own line.
    """
    return bool(_TOC_PATTERN.search(content))


def _convert_toc_to_placeholder(content: str) -> str:
    """Convert first [TOC] to HTML placeholder.

    Only the first [TOC] is converted. Subsequent ones are removed.
    [TOC] inside code blocks is not processed.

    Args:
        content: Markdown content with potential [TOC] markers.

    Returns:
        Content with [TOC] converted to placeholder.
    """
    # Protect code blocks from TOC processing
    code_blocks: list[tuple[str, str]] = []

    def protect_code_block(match: re.Match[str]) -> str:
        placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
        code_blocks.append((placeholder, match.group(0)))
        return placeholder

    # Temporarily replace code blocks
    protected = re.sub(r"```[\s\S]*?```", protect_code_block, content)
    protected = re.sub(r"`[^`]+`", protect_code_block, protected)

    # Convert only the first [TOC] to placeholder
    first_replaced = False

    def replace_toc(match: re.Match[str]) -> str:
        nonlocal first_replaced
        if not first_replaced:
            first_replaced = True
            return _TOC_PLACEHOLDER
        return ""  # Remove subsequent [TOC]s

    result = _TOC_PATTERN.sub(replace_toc, protected)

    # Restore code blocks
    for placeholder, original in code_blocks:
        result = result.replace(placeholder, original)

    return result


def _convert_toc_placeholder_to_html(html: str) -> str:
    """Convert TOC placeholder in HTML to <table-of-contents> element.

    Replaces <p name="..." id="...">§§TOC§§</p> with
    <table-of-contents name="..." id="..."></table-of-contents>

    This is called after markdown conversion and UUID addition to convert
    the placeholder to the actual custom element that note.com preserves via API.

    Issue #117: This enables TOC via API without browser automation.

    Args:
        html: HTML content with potential TOC placeholder

    Returns:
        HTML with TOC placeholder converted to <table-of-contents> element
    """

    def replace_with_toc(match: re.Match[str]) -> str:
        name = match.group(1)
        element_id = match.group(2)
        return f'<table-of-contents name="{name}" id="{element_id}"></table-of-contents>'

    return _TOC_PLACEHOLDER_HTML_PATTERN.sub(replace_with_toc, html)


def markdown_to_html(content: str) -> str:
    """Convert Markdown content to HTML.

    Uses markdown-it-py for CommonMark-compliant conversion.
    Converts images to note.com's figure format.

    Args:
        content: Markdown formatted text

    Returns:
        HTML formatted text. Returns empty string for empty input.

    Example:
        >>> markdown_to_html("# Hello")
        '<h1>Hello</h1>\\n'
    """
    if not content or not content.strip():
        return ""

    # 1. Convert [TOC] to placeholder FIRST (before any processing)
    content = _convert_toc_to_placeholder(content)

    # 2. Convert text alignment markers to placeholders BEFORE markdown conversion
    content = _convert_text_alignment(content)

    # 3. Markdown conversion
    md = MarkdownIt().enable("strikethrough")
    result: str = md.render(content)

    # Convert images to note.com format
    result = _convert_images_to_note_format(result)

    # Wrap list item content in p tags (ProseMirror requirement)
    result = _wrap_li_content_in_p(result)

    # Convert blockquote newlines to <br> tags (note.com browser editor format)
    result = _convert_blockquote_newlines_to_br(result)

    # Add UUID to all elements (note.com requirement)
    result = _add_uuid_to_elements(result)

    # Convert TOC placeholder to <table-of-contents> element (Issue #117)
    # Must be after UUID addition to preserve name/id attributes
    result = _convert_toc_placeholder_to_html(result)

    # Apply text alignment styles to paragraphs (must be after UUID addition)
    result = _apply_text_alignment_to_html(result)

    # Convert blockquotes to note.com figure format
    # This is required for the API to preserve <br> tags inside blockquotes
    result = _convert_blockquotes_to_note_format(result)

    # Convert standalone embed URLs to figure elements (Issue #116)
    # YouTube, Twitter, note.com URLs alone in a paragraph become embeds
    result = _convert_standalone_embed_urls(result)

    # Convert code blocks to note.com format and handle newlines
    result = _convert_code_blocks_to_note_format(result)

    return result
