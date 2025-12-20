"""Markdown to HTML conversion utility.

Uses markdown-it-py for CommonMark-compliant conversion.
"""

from markdown_it import MarkdownIt


def markdown_to_html(content: str) -> str:
    """Convert Markdown content to HTML.

    Uses markdown-it-py for CommonMark-compliant conversion.
    Suitable for note.com's HTML body format requirement.

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
    return result
