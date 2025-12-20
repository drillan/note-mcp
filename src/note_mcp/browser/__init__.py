"""Browser module for note-mcp.

Provides Playwright-based browser automation for login and preview.
"""

from note_mcp.browser.manager import BrowserManager
from note_mcp.browser.preview import show_preview

__all__ = ["BrowserManager", "show_preview"]
