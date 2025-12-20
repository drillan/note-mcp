"""Article operations for note.com API.

Provides functions for creating, updating, and managing articles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from note_mcp.api.client import NoteAPIClient
from note_mcp.models import (
    Article,
    ArticleInput,
    ArticleListResult,
    ArticleStatus,
    Session,
    from_api_response,
)
from note_mcp.utils import markdown_to_html

if TYPE_CHECKING:
    pass


async def create_draft(
    session: Session,
    article_input: ArticleInput,
) -> Article:
    """Create a new draft article.

    Uses browser automation to create the draft via note.com's web interface.

    Args:
        session: Authenticated session
        article_input: Article content and metadata

    Returns:
        Created Article object

    Raises:
        RuntimeError: If draft creation fails
    """
    from note_mcp.browser.create_draft import create_draft_via_browser

    return await create_draft_via_browser(session, article_input)


async def update_article(
    session: Session,
    article_id: str,
    article_input: ArticleInput,
) -> Article:
    """Update an existing article.

    Uses browser automation to update the article via note.com's web interface.

    Args:
        session: Authenticated session
        article_id: ID of the article to update
        article_input: New article content and metadata

    Returns:
        Updated Article object

    Raises:
        RuntimeError: If article update fails
    """
    from note_mcp.browser.update_article import update_article_via_browser

    return await update_article_via_browser(session, article_id, article_input)


async def get_article(
    session: Session,
    article_id: str,
) -> Article:
    """Get article content by ID.

    Retrieves article content via browser automation.
    Use this to retrieve existing content before editing.

    Recommended workflow:
    1. get_article(article_id) - retrieve current content
    2. Edit content as needed
    3. update_article(article_id, ...) - save changes

    Args:
        session: Authenticated session
        article_id: ID of the article to retrieve

    Returns:
        Article object with title, body, and status

    Raises:
        RuntimeError: If article retrieval fails
    """
    from note_mcp.browser.get_article import get_article_via_browser

    return await get_article_via_browser(session, article_id)


async def list_articles(
    session: Session,
    status: ArticleStatus | None = None,
    page: int = 1,
    limit: int = 10,
) -> ArticleListResult:
    """List articles for the authenticated user.

    Args:
        session: Authenticated session
        status: Filter by article status (draft, published, all)
        page: Page number (1-indexed)
        limit: Number of articles per page (max 10)

    Returns:
        ArticleListResult containing articles and pagination info

    Raises:
        NoteAPIError: If API request fails
    """
    # Build query parameters using the v2 creators endpoint
    # Reference: https://note.com/karupoimou/n/n5d8124747158
    params: dict[str, Any] = {
        "kind": "note",
        "page": page,
    }

    # Add status filter if specified
    if status is not None:
        params["status"] = status.value

    # Use the username-specific endpoint to get the user's own articles
    async with NoteAPIClient(session) as client:
        response = await client.get(f"/v2/creators/{session.username}/contents", params=params)

    # Parse response - v2 endpoint returns different structure
    data = response.get("data", {})

    # The v2 endpoint returns contents directly in data
    contents = data.get("contents", [])
    total_count = data.get("totalCount", len(contents))
    is_last_page = data.get("isLastPage", True)

    # Convert each article
    articles: list[Article] = []
    for item in contents:
        article = from_api_response(item)
        articles.append(article)

    # Apply limit client-side if needed (v2 may not support limit param)
    articles = articles[:limit]

    return ArticleListResult(
        articles=articles,
        total=total_count,
        page=page,
        has_more=not is_last_page,
    )


async def publish_article(
    session: Session,
    article_id: str | None = None,
    article_input: ArticleInput | None = None,
) -> Article:
    """Publish an article.

    Either publishes an existing draft or creates and publishes a new article.

    Args:
        session: Authenticated session
        article_id: ID of existing draft to publish (mutually exclusive with article_input)
        article_input: New article content to create and publish (mutually exclusive with article_id)

    Returns:
        Published Article object

    Raises:
        ValueError: If neither or both article_id and article_input are provided
        NoteAPIError: If API request fails
    """
    if article_id is None and article_input is None:
        raise ValueError("Either article_id or article_input must be provided")

    if article_id is not None and article_input is not None:
        raise ValueError("Cannot provide both article_id and article_input")

    async with NoteAPIClient(session) as client:
        if article_id is not None:
            # Publish existing draft
            payload: dict[str, Any] = {"status": "published"}
            response = await client.post(f"/v3/notes/{article_id}/publish", json=payload)
        else:
            # Create and publish new article
            assert article_input is not None  # Type narrowing
            html_body = markdown_to_html(article_input.body)

            payload = {
                "name": article_input.title,
                "body": html_body,
                "status": "published",
            }

            # Add tags if present
            if article_input.tags:
                normalized_tags = [tag.lstrip("#") for tag in article_input.tags]
                payload["hashtags"] = [{"hashtag": {"name": tag}} for tag in normalized_tags]

            response = await client.post("/v3/notes", json=payload)

    # Parse response
    article_data = response.get("data", {})
    return from_api_response(article_data)
