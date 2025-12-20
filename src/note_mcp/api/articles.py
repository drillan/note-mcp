"""Article operations for note.com API.

Provides functions for creating, updating, and managing articles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from note_mcp.api.client import NoteAPIClient
from note_mcp.models import Article, ArticleInput, Session, from_api_response
from note_mcp.utils import markdown_to_html

if TYPE_CHECKING:
    pass


async def create_draft(
    session: Session,
    article_input: ArticleInput,
) -> Article:
    """Create a new draft article.

    Converts Markdown body to HTML before sending to API.

    Args:
        session: Authenticated session
        article_input: Article content and metadata

    Returns:
        Created Article object

    Raises:
        NoteAPIError: If API request fails
    """
    # Convert Markdown to HTML
    html_body = markdown_to_html(article_input.body)

    # Build request payload
    payload: dict[str, Any] = {
        "name": article_input.title,
        "body": html_body,
        "status": "draft",
    }

    # Add tags if present
    if article_input.tags:
        # Normalize tags (remove # prefix if present)
        normalized_tags = [tag.lstrip("#") for tag in article_input.tags]
        payload["hashtags"] = [{"hashtag": {"name": tag}} for tag in normalized_tags]

    async with NoteAPIClient(session) as client:
        response = await client.post("/v3/notes", json=payload)

    # Parse response
    article_data = response.get("data", {})
    return from_api_response(article_data)


async def update_article(
    session: Session,
    article_id: str,
    article_input: ArticleInput,
) -> Article:
    """Update an existing article.

    Converts Markdown body to HTML before sending to API.

    Args:
        session: Authenticated session
        article_id: ID of the article to update
        article_input: New article content and metadata

    Returns:
        Updated Article object

    Raises:
        NoteAPIError: If API request fails
    """
    # Convert Markdown to HTML if body is provided
    html_body = markdown_to_html(article_input.body) if article_input.body else ""

    # Build request payload
    payload: dict[str, Any] = {
        "name": article_input.title,
    }

    # Only include body if provided
    if html_body:
        payload["body"] = html_body

    # Add tags if present
    if article_input.tags:
        normalized_tags = [tag.lstrip("#") for tag in article_input.tags]
        payload["hashtags"] = [{"hashtag": {"name": tag}} for tag in normalized_tags]

    async with NoteAPIClient(session) as client:
        response = await client.put(f"/v3/notes/{article_id}", json=payload)

    # Parse response
    article_data = response.get("data", {})
    return from_api_response(article_data)
