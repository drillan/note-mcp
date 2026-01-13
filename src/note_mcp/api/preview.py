"""Preview API functions for note.com.

Provides functionality to get preview access tokens
and fetch preview page HTML.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from note_mcp.api.articles import build_preview_url, get_preview_access_token
from note_mcp.models import ErrorCode, NoteAPIError

if TYPE_CHECKING:
    from note_mcp.models import Session


# Re-export for convenience
__all__ = ["get_preview_access_token", "build_preview_url", "get_preview_html"]


async def get_preview_html(
    session: Session,
    article_key: str,
) -> str:
    """Fetch preview page HTML for an article.

    Gets preview access token via API and fetches the preview page HTML.
    Useful for E2E testing and content verification.

    Args:
        session: Authenticated session
        article_key: Article key (e.g., "n1234567890ab")

    Returns:
        Preview page HTML as string

    Raises:
        NoteAPIError: If token fetch or HTML fetch fails
    """
    # Get preview access token via API
    access_token = await get_preview_access_token(session, article_key)

    # Build preview URL
    preview_url = build_preview_url(article_key, access_token)

    # Build cookies header
    cookie_parts = [f"{k}={v}" for k, v in session.cookies.items()]
    cookies_header = "; ".join(cookie_parts)

    # Fetch HTML via httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(
            preview_url,
            headers={
                "Cookie": cookies_header,
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
                ),
            },
            follow_redirects=True,
        )

    if not response.is_success:
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message=f"Failed to fetch preview HTML. Status: {response.status_code}",
            details={
                "article_key": article_key,
                "status_code": response.status_code,
            },
        )

    return response.text
