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
    # Build query parameters
    params: dict[str, Any] = {
        "page": page,
        "limit": min(limit, 10),  # Max 10 as per API contract
    }

    # Add status filter if specified
    if status is not None:
        params["status"] = status.value

    async with NoteAPIClient(session) as client:
        response = await client.get(f"/v3/users/{session.user_id}/notes", params=params)

    # Parse response
    data = response.get("data", {})
    notes_data = data.get("notesByAuthor", {})

    contents = notes_data.get("contents", [])
    total_count = notes_data.get("totalCount", 0)
    is_last_page = notes_data.get("isLastPage", True)

    # Convert each article
    articles: list[Article] = []
    for item in contents:
        article = from_api_response(item)
        articles.append(article)

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
