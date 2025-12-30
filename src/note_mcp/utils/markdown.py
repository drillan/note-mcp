"""Backward compatibility alias for markdown_to_html module.

This module re-exports markdown_to_html from markdown_to_html.py for backward compatibility.
New code should import directly from note_mcp.utils.markdown_to_html.
"""

from note_mcp.utils.markdown_to_html import markdown_to_html

__all__ = ["markdown_to_html"]
