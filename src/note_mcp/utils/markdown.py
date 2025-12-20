"""Markdown to HTML conversion utility.

Uses markdown-it-py for CommonMark-compliant conversion.
"""

import re
import uuid

from markdown_it import MarkdownIt


def _generate_uuid() -> str:
    """Generate a UUID for note.com element IDs."""
    return str(uuid.uuid4())


def _add_uuid_to_elements(html: str) -> str:
    """Add name and id attributes (UUID) to all HTML elements.

    note.com requires all elements to have unique name and id attributes.

    Args:
        html: HTML string

    Returns:
        HTML with UUID attributes added to all elements
    """
    # Pattern to match opening tags without name attribute
    # Matches: <tagname> or <tagname attr="value">
    tag_pattern = re.compile(
        r"<(p|h[1-6]|ul|ol|li|blockquote|pre|code|hr|div|span)(\s[^>]*)?>",
        re.IGNORECASE,
    )

    def add_uuid(match: re.Match[str]) -> str:
        tag_name = match.group(1)
        attrs = match.group(2) or ""

        # Skip if already has name attribute
        if 'name="' in attrs:
            return match.group(0)

        element_id = _generate_uuid()
        return f'<{tag_name} name="{element_id}" id="{element_id}"{attrs}>'

    return tag_pattern.sub(add_uuid, html)


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
    # Pattern to match <p> tags containing only an img tag
    # markdown-it-py wraps images in <p> tags
    img_in_p_pattern = re.compile(
        r'<p>\s*<img\s+src="([^"]+)"\s+alt="([^"]*)"\s*/?\s*>\s*</p>',
        re.IGNORECASE,
    )

    def replace_img(match: re.Match[str]) -> str:
        src = match.group(1)
        alt = match.group(2)
        element_id = _generate_uuid()
        return (
            f'<figure name="{element_id}" id="{element_id}">'
            f'<img src="{src}" alt="{alt}" width="620" height="457" '
            f'contenteditable="false" draggable="false">'
            f"<figcaption></figcaption></figure>"
        )

    return img_in_p_pattern.sub(replace_img, html)


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

    # Remove all newlines - note.com API expects single-line HTML
    result = result.replace("\n", "")

    return result
