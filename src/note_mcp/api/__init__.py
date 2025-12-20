"""API module for note-mcp.

Provides HTTP client and API operations for note.com.
"""

from note_mcp.api.articles import create_draft, list_articles, publish_article, update_article
from note_mcp.api.client import NoteAPIClient
from note_mcp.api.images import upload_image

__all__ = [
    "NoteAPIClient",
    "create_draft",
    "list_articles",
    "publish_article",
    "update_article",
    "upload_image",
]
