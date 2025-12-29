"""Markdown to HTML conversion utility.

Uses markdown-it-py for CommonMark-compliant conversion.
"""

import re
import uuid

from markdown_it import MarkdownIt

# Pre-compiled regex patterns for performance
_TAG_PATTERN = re.compile(
    r"<(p|h[1-6]|ul|ol|li|blockquote|code|hr|div|span)(\s[^>]*)?>",
    re.IGNORECASE,
)
_PRE_PATTERN = re.compile(r"<pre([^>]*)>(.*?)</pre>", re.DOTALL | re.IGNORECASE)
_IMG_IN_P_PATTERN = re.compile(
    r'<p>\s*<img\s+src="([^"]+)"\s+alt="([^"]*)"(?:\s+title="([^"]*)")?\s*/?\s*>\s*</p>',
    re.IGNORECASE,
)
_LANGUAGE_CLASS_PATTERN = re.compile(r'<code[^>]*class="language-[^"]*"[^>]*>')


def _generate_uuid() -> str:
    """Generate a UUID for note.com element IDs."""
    return str(uuid.uuid4())


def _add_uuid_to_elements(html: str) -> str:
    """Add name and id attributes (UUID) to all HTML elements.

    note.com requires all elements to have unique name and id attributes.
    Note: <pre> tags are handled separately by _convert_code_blocks_to_note_format.

    Args:
        html: HTML string

    Returns:
        HTML with UUID attributes added to all elements
    """

    def add_uuid(match: re.Match[str]) -> str:
        tag_name = match.group(1)
        attrs = match.group(2) or ""

        # Skip if already has name attribute
        if 'name="' in attrs:
            return match.group(0)

        element_id = _generate_uuid()
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

    md = MarkdownIt()
    result: str = md.render(content)

    # Convert images to note.com format
    result = _convert_images_to_note_format(result)

    # Add UUID to all elements (note.com requirement)
    result = _add_uuid_to_elements(result)

    # Convert code blocks to note.com format and handle newlines
    result = _convert_code_blocks_to_note_format(result)

    return result
