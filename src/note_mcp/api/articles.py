"""Article operations for note.com API.

Provides functions for creating, updating, and managing articles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from note_mcp.api.client import NoteAPIClient
from note_mcp.api.images import _resolve_numeric_note_id
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


def _normalize_tags(tags: list[str] | None) -> list[dict[str, Any]] | None:
    """Normalize tags to API format.

    Removes leading '#' and converts to hashtag dict format.

    Args:
        tags: List of tags (may include '#' prefix)

    Returns:
        List of hashtag dicts for API, or None if no tags
    """
    if not tags:
        return None
    normalized = [tag.lstrip("#") for tag in tags]
    return [{"hashtag": {"name": tag}} for tag in normalized]


def _build_article_payload(
    article_input: ArticleInput,
    html_body: str | None = None,
    include_body: bool = True,
) -> dict[str, Any]:
    """Build common article payload for API requests.

    Args:
        article_input: Article content and metadata
        html_body: Pre-converted HTML body (optional)
        include_body: Whether to include body in payload

    Returns:
        Payload dict for note.com API
    """
    payload: dict[str, Any] = {
        "name": article_input.title,
        "index": False,
        "is_lead_form": False,
    }

    if include_body and html_body is not None:
        payload["body"] = html_body
        payload["body_length"] = len(article_input.body)

    hashtags = _normalize_tags(article_input.tags)
    if hashtags:
        payload["hashtags"] = hashtags

    return payload


async def create_draft(
    session: Session,
    article_input: ArticleInput,
) -> Article:
    """Create a new draft article.

    Uses the note.com API to create the draft directly.
    Converts Markdown body to HTML as required by the API.

    Note: This function performs two API calls:
    1. POST /v1/text_notes - Creates the article entry (without body)
    2. POST /v1/text_notes/draft_save - Saves the body content

    The body is sent only via draft_save to preserve HTML structure.
    However, note that note.com's API sanitizes certain HTML elements
    (e.g., <br> tags inside blockquotes) regardless of how content is sent.
    This is a server-side limitation that cannot be worked around.

    Args:
        session: Authenticated session
        article_input: Article content and metadata

    Returns:
        Created Article object

    Raises:
        NoteAPIError: If API request fails
    """
    # Convert Markdown to HTML for API
    html_body = markdown_to_html(article_input.body)

    # Step 1 payload: without body to avoid sanitization
    create_payload = _build_article_payload(article_input, include_body=False)

    async with NoteAPIClient(session) as client:
        # Step 1: Create the article entry (without body)
        # The body is saved separately via draft_save to preserve <br> tags
        response = await client.post("/v1/text_notes", json=create_payload)

        # Get the numeric article ID from response
        article_data = response.get("data", {})
        article_id = article_data.get("id")

        if article_id:
            # Step 2: Save the body content with draft_save
            # This endpoint preserves <br> tags unlike /v1/text_notes
            save_payload = _build_article_payload(article_input, html_body)

            await client.post(
                f"/v1/text_notes/draft_save?id={article_id}&is_temp_saved=true",
                json=save_payload,
            )

    # Parse response
    return from_api_response(article_data)


async def update_article(
    session: Session,
    article_id: str,
    article_input: ArticleInput,
) -> Article:
    """Update an existing article.

    Uses the note.com API to update the article.
    Converts Markdown body to HTML as required by the API.

    Args:
        session: Authenticated session
        article_id: ID of the article to update
        article_input: New article content and metadata

    Returns:
        Updated Article object

    Raises:
        NoteAPIError: If API request fails
    """
    # Resolve to numeric ID (API requirement)
    numeric_id = await _resolve_numeric_note_id(session, article_id)

    # Convert Markdown to HTML for API
    html_body = markdown_to_html(article_input.body)

    # Build payload using helper
    payload = _build_article_payload(article_input, html_body)

    async with NoteAPIClient(session) as client:
        # Use draft_save endpoint with POST (not PUT)
        response = await client.post(
            f"/v1/text_notes/draft_save?id={numeric_id}&is_temp_saved=true",
            json=payload,
        )

    # Parse response
    article_data = response.get("data", {})
    return from_api_response(article_data)


async def get_article_via_api(
    session: Session,
    article_id: str,
) -> Article:
    """Get article content by ID via API.

    Retrieves article content directly from the note.com API.
    Faster and more reliable than browser-based retrieval.

    Args:
        session: Authenticated session
        article_id: ID of the article to retrieve (numeric or key format)

    Returns:
        Article object with title, body (as Markdown), and status

    Raises:
        NoteAPIError: If API request fails
    """
    from note_mcp.utils.html_to_markdown import html_to_markdown

    async with NoteAPIClient(session) as client:
        response = await client.get(f"/v3/notes/{article_id}")

    # Parse response
    article_data = response.get("data", {})
    article = from_api_response(article_data)

    # Convert HTML body to Markdown for consistent output
    if article.body:
        article = Article(
            id=article.id,
            key=article.key,
            title=article.title,
            body=html_to_markdown(article.body),
            status=article.status,
            tags=article.tags,
            eyecatch_image_key=article.eyecatch_image_key,
            prev_access_key=article.prev_access_key,
            created_at=article.created_at,
            updated_at=article.updated_at,
            published_at=article.published_at,
            url=article.url,
        )

    return article


async def get_article(
    session: Session,
    article_id: str,
) -> Article:
    """Get article content by ID.

    Retrieves article content via API.
    Use this to retrieve existing content before editing.

    Recommended workflow:
    1. get_article(article_id) - retrieve current content
    2. Edit content as needed
    3. update_article(article_id, ...) - save changes

    Args:
        session: Authenticated session
        article_id: ID of the article to retrieve

    Returns:
        Article object with title, body (as Markdown), and status

    Raises:
        NoteAPIError: If API request fails
    """
    return await get_article_via_api(session, article_id)


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
            hashtags = _normalize_tags(article_input.tags)
            if hashtags:
                payload["hashtags"] = hashtags

            response = await client.post("/v3/notes", json=payload)

    # Parse response
    article_data = response.get("data", {})
    return from_api_response(article_data)
