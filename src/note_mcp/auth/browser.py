"""Browser-based login flow for note.com.

Uses Playwright to open a browser for manual user login,
then extracts session cookies for API authentication.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from note_mcp.auth.session import SessionManager
from note_mcp.browser.manager import BrowserManager
from note_mcp.models import Session

if TYPE_CHECKING:
    pass


# note.com URLs
NOTE_LOGIN_URL = "https://note.com/login"
NOTE_HOME_URL = "https://note.com/"
NOTE_DASHBOARD_URL = "https://note.com/dashboard"

# Required cookie names
REQUIRED_COOKIES = ["note_gql_auth_token", "_note_session_v5"]

# Default timeout for login (5 minutes)
DEFAULT_LOGIN_TIMEOUT = 300


def extract_session_cookies(cookies: list[dict[str, Any]]) -> dict[str, str]:
    """Extract required session cookies from browser cookies.

    Args:
        cookies: List of cookie dictionaries from Playwright

    Returns:
        Dictionary with required cookie name-value pairs

    Raises:
        ValueError: If required cookies are missing
    """
    result: dict[str, str] = {}

    for cookie in cookies:
        name = cookie.get("name", "")
        if name in REQUIRED_COOKIES:
            result[name] = cookie.get("value", "")

    # Validate required cookies
    if "note_gql_auth_token" not in result:
        raise ValueError("Missing required cookie: note_gql_auth_token")
    if "_note_session_v5" not in result:
        raise ValueError("Missing required cookie: _note_session_v5")

    return result


async def get_current_user(cookies: dict[str, str]) -> dict[str, Any]:
    """Get current user info from note.com API.

    Args:
        cookies: Session cookies for authentication

    Returns:
        User info dictionary with 'id' and 'urlname' fields

    Raises:
        ValueError: If user info cannot be retrieved
    """
    import httpx

    async with httpx.AsyncClient() as client:
        # Build cookie header
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

        response = await client.get(
            "https://note.com/api/v1/stats/pv",
            headers={
                "Cookie": cookie_header,
                "Accept": "application/json",
            },
        )

        if response.status_code != 200:
            raise ValueError(f"Failed to get user info: HTTP {response.status_code}")

        data = response.json()

        # Extract user info from response
        # The stats/pv endpoint includes user info
        user_data = data.get("data", {})
        user_id = user_data.get("user_id") or user_data.get("id")
        urlname = user_data.get("urlname") or user_data.get("username")

        if not user_id or not urlname:
            # Try alternative endpoint
            response = await client.get(
                "https://note.com/api/v2/self",
                headers={
                    "Cookie": cookie_header,
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                raise ValueError(f"Failed to get user info: HTTP {response.status_code}")

            data = response.json()
            user_data = data.get("data", {})
            user_id = user_data.get("id", "")
            urlname = user_data.get("urlname", "")

        if not user_id:
            raise ValueError("Could not retrieve user ID")

        return {"id": str(user_id), "urlname": urlname or ""}


async def login_with_browser(timeout: int = DEFAULT_LOGIN_TIMEOUT) -> Session:
    """Open browser for manual login and extract session.

    Opens the note.com login page in a visible browser window.
    Waits for user to complete login manually.
    Extracts session cookies and creates a Session object.

    Args:
        timeout: Maximum time to wait for login (seconds)

    Returns:
        Session object with cookies and user info

    Raises:
        TimeoutError: If login is not completed within timeout
        ValueError: If required cookies are not found
    """
    manager = BrowserManager.get_instance()
    page = await manager.get_page()

    # Navigate to login page
    await page.goto(NOTE_LOGIN_URL)

    # Wait for user to complete login (redirected to home or dashboard)
    try:
        await page.wait_for_url(
            lambda url: url.startswith(NOTE_HOME_URL) or url.startswith(NOTE_DASHBOARD_URL),
            timeout=timeout * 1000,  # Convert to milliseconds
        )
    except Exception as e:
        raise TimeoutError(f"Login not completed within {timeout} seconds") from e

    # Extract cookies from browser context
    browser_cookies = await page.context.cookies()
    # Convert Cookie objects to dicts for extraction
    cookie_dicts: list[dict[str, Any]] = [
        {"name": c.get("name", ""), "value": c.get("value", "")} for c in browser_cookies
    ]
    cookies = extract_session_cookies(cookie_dicts)

    # Get user info
    user_info = await get_current_user(cookies)

    # Create session
    session = Session(
        cookies=cookies,
        user_id=user_info["id"],
        username=user_info["urlname"],
        expires_at=None,  # No explicit expiry from cookies
        created_at=int(time.time()),
    )

    # Save session to keyring
    session_manager = SessionManager()
    session_manager.save(session)

    return session
