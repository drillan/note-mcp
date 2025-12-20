"""Browser-based article preview.

Provides functionality to show article preview in browser.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from note_mcp.browser.manager import BrowserManager

if TYPE_CHECKING:
    from note_mcp.models import Session


# note.com editor URL
NOTE_EDITOR_URL = "https://editor.note.com"


async def show_preview(
    session: Session,
    article_key: str,
) -> None:
    """Show article preview in browser.

    Opens the article edit page in the browser for preview.
    The browser window will remain open for the user to view.

    Args:
        session: Authenticated session with username
        article_key: Article key (e.g., "n1234567890ab")

    Raises:
        RuntimeError: If browser navigation fails
    """
    # Build edit page URL using editor.note.com
    edit_url = f"{NOTE_EDITOR_URL}/notes/{article_key}/edit/"

    # Get browser page
    manager = BrowserManager.get_instance()
    page = await manager.get_page()

    # Inject session cookies into browser context
    playwright_cookies: list[dict[str, Any]] = []
    for name, value in session.cookies.items():
        playwright_cookies.append(
            {
                "name": name,
                "value": value,
                "domain": ".note.com",
                "path": "/",
            }
        )
    await page.context.add_cookies(playwright_cookies)  # type: ignore[arg-type]

    # Navigate to edit page
    await page.goto(edit_url)
