"""Preview page helpers for E2E testing.

Provides utilities for opening and navigating to note.com preview pages.
Extracted from conftest.py to enable reuse across test modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

# Timeouts (milliseconds)
DEFAULT_NAVIGATION_TIMEOUT_MS = 30000
DEFAULT_ELEMENT_WAIT_TIMEOUT_MS = 15000

# note.com URLs
NOTE_EDITOR_URL = "https://editor.note.com/notes"


async def open_preview_for_article_key(
    page: Page,
    article_key: str,
    timeout: int = DEFAULT_NAVIGATION_TIMEOUT_MS,
) -> Page:
    """Navigate to editor and open preview, returning the preview page.

    Opens the note.com editor for the given article key, then clicks
    the preview button to open the preview in a new tab.

    Note: note.com does not support direct preview URLs. Preview must
    be accessed through the editor's menu button.

    Args:
        page: Playwright Page instance with session cookies injected
        article_key: Article key (e.g., "n1234567890ab")
        timeout: Navigation timeout in milliseconds

    Returns:
        Playwright Page for the preview tab

    Raises:
        TimeoutError: If navigation or element waits time out
    """
    # Navigate to editor page
    editor_url = f"{NOTE_EDITOR_URL}/{article_key}/edit/"
    await page.goto(
        editor_url,
        wait_until="domcontentloaded",
        timeout=timeout,
    )
    await page.wait_for_load_state("domcontentloaded", timeout=timeout)

    # Find and click the menu button (3-dot icon) to open header popover
    menu_button = page.locator('button[aria-label="その他"]')
    await menu_button.wait_for(state="visible", timeout=DEFAULT_ELEMENT_WAIT_TIMEOUT_MS)
    await menu_button.click()

    # Wait for popover and click "プレビュー" button
    preview_button = page.locator("#header-popover button", has_text="プレビュー")
    await preview_button.wait_for(state="visible", timeout=10000)

    # Capture new page (tab) when clicking preview
    async with page.context.expect_page(timeout=timeout) as new_page_info:
        await preview_button.click()

    # Get the new page (preview tab)
    new_page = await new_page_info.value
    await new_page.wait_for_load_state("domcontentloaded", timeout=timeout)

    return new_page
