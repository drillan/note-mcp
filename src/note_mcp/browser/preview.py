"""Browser-based article preview.

Provides functionality to show article preview in browser.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from note_mcp.browser.manager import BrowserManager

if TYPE_CHECKING:
    from note_mcp.models import Session


# note.com URLs
NOTE_EDITOR_URL = "https://editor.note.com/notes"


async def show_preview(
    session: Session,
    article_key: str,
) -> None:
    """Show article preview in browser.

    Opens the article preview page by navigating to the editor
    and clicking the preview button. The preview opens in a new tab.

    Args:
        session: Authenticated session with username
        article_key: Article key (e.g., "n1234567890ab")

    Raises:
        RuntimeError: If browser navigation fails or preview button not found
    """
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

    # Navigate to editor page
    editor_url = f"{NOTE_EDITOR_URL}/{article_key}/edit/"
    await page.goto(editor_url, wait_until="networkidle")

    # Wait for the page to be fully loaded
    await page.wait_for_load_state("networkidle")

    # Find and click the menu button (3-dot icon) to open header popover
    # The menu button has aria-label="その他" and aria-haspopup="true"
    menu_button = page.locator('button[aria-label="その他"]')
    await menu_button.wait_for(state="visible")
    await menu_button.click()

    # Wait for popover to appear and click the "プレビュー" (Preview) button
    preview_button = page.locator("#header-popover button", has_text="プレビュー")
    await preview_button.wait_for(state="visible")

    # Set up handler for new page (tab) before clicking
    async with page.context.expect_page() as new_page_info:
        await preview_button.click()

    # Get the new page (preview tab)
    new_page = await new_page_info.value

    # Wait for navigation to complete
    await new_page.wait_for_load_state("networkidle")

    # The new page is now showing the preview - keep it open for user to view
    # Bring the new page to front
    await new_page.bring_to_front()
