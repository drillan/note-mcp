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

# Common User-Agent string for API requests
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"


async def get_preview_html(
    session: Session,
    article_key: str,
) -> str:
    """Fetch preview page HTML for an article.

    Gets preview access token via API and fetches the preview page HTML.
    Useful for E2E testing and content verification.

    On authentication errors (401/403), automatically retries once with
    a fresh token in case the original token expired.

    Args:
        session: Authenticated session
        article_key: Article key (e.g., "n1234567890ab")

    Returns:
        Preview page HTML as string

    Raises:
        NoteAPIError: If token fetch or HTML fetch fails after retry
    """
    # Build cookie header
    cookie_parts = [f"{k}={v}" for k, v in session.cookies.items()]
    cookies_header = "; ".join(cookie_parts)

    # HTTP headers for requests
    headers = {
        "Cookie": cookies_header,
        "User-Agent": USER_AGENT,
    }

    # Auth error status codes that trigger retry
    auth_error_codes = {401, 403}

    # Try up to 2 times (initial + 1 retry for auth errors)
    last_response = None
    for attempt in range(2):
        # Get preview access token via API
        access_token = await get_preview_access_token(session, article_key)

        # Build preview URL
        preview_url = build_preview_url(article_key, access_token)

        # Fetch HTML via httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                preview_url,
                headers=headers,
                follow_redirects=True,
            )

        if response.is_success:
            return response.text

        last_response = response

        # Only retry on auth errors, and only on first attempt
        if response.status_code not in auth_error_codes or attempt > 0:
            break

    # All attempts failed
    assert last_response is not None

    # Use NOT_AUTHENTICATED for auth errors, API_ERROR for others
    error_code = ErrorCode.NOT_AUTHENTICATED if last_response.status_code == 401 else ErrorCode.API_ERROR

    raise NoteAPIError(
        code=error_code,
        message=f"Failed to fetch preview HTML. Status: {last_response.status_code}",
        details={
            "article_key": article_key,
            "status_code": last_response.status_code,
            "response_text": last_response.text[:500] if last_response.text else "(empty)",
        },
    )
