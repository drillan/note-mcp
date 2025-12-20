"""API module for note-mcp.

Provides HTTP client and API operations for note.com.
"""

from note_mcp.api.articles import create_draft, update_article
from note_mcp.api.client import NoteAPIClient

__all__ = ["NoteAPIClient", "create_draft", "update_article"]
