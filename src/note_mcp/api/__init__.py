"""API module for note-mcp.

Provides HTTP client and API operations for note.com.
"""

from note_mcp.api.articles import (
    create_draft,
    delete_all_drafts,
    delete_draft,
    get_separator_candidates,
    list_articles,
    publish_article,
    set_paid_settings,
    update_article,
)
from note_mcp.api.client import NoteAPIClient
from note_mcp.api.images import upload_body_image, upload_eyecatch_image
from note_mcp.api.magazines import list_circle_plans, list_my_magazines

__all__ = [
    "NoteAPIClient",
    "create_draft",
    "delete_all_drafts",
    "delete_draft",
    "get_separator_candidates",
    "list_articles",
    "list_circle_plans",
    "list_my_magazines",
    "publish_article",
    "set_paid_settings",
    "update_article",
    "upload_body_image",
    "upload_eyecatch_image",
]
