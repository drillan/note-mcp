"""Preview page helpers for E2E testing.

Provides utilities for opening and navigating to note.com preview pages.
Extracted from conftest.py to enable reuse across test modules.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright

from .constants import (
    DEFAULT_ELEMENT_WAIT_TIMEOUT_MS,
    DEFAULT_NAVIGATION_TIMEOUT_MS,
    NOTE_EDITOR_URL,
)

if TYPE_CHECKING:
    from playwright._impl._api_structures import SetCookieParam
    from playwright.async_api import Page

    from note_mcp.models import Session

logger = logging.getLogger(__name__)


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
    # Wait for JavaScript rendering (needed for math formulas like nwc-formula)
    await new_page.wait_for_load_state("networkidle", timeout=timeout)

    return new_page


async def _inject_session_cookies(page: Page, session: Session) -> None:
    """Inject session cookies into browser context.

    Args:
        page: Playwright Page instance
        session: Session with cookies to inject
    """
    playwright_cookies: list[SetCookieParam] = [
        {
            "name": name,
            "value": value,
            "domain": ".note.com",
            "path": "/",
        }
        for name, value in session.cookies.items()
    ]
    await page.context.add_cookies(playwright_cookies)


@asynccontextmanager
async def preview_page_context(
    session: Session,
    article_key: str,
    *,
    headless: bool = False,
) -> AsyncGenerator[Page, None]:
    """Open preview page with automatic browser lifecycle management.

    Creates a fresh browser context, injects session cookies, and opens
    the article preview page. Automatically cleans up all browser resources
    on context exit.

    Args:
        session: Authenticated Session object with cookies
        article_key: Article key (e.g., "n1234567890ab")
        headless: Whether to run browser in headless mode

    Yields:
        Playwright Page for the preview tab

    Raises:
        TimeoutError: If navigation or element waits time out

    Example:
        async with preview_page_context(session, article_key) as preview_page:
            validator = PreviewValidator(preview_page)
            result = await validator.validate_toc()
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        await _inject_session_cookies(page, session)
        preview_page = await open_preview_for_article_key(page, article_key)
        yield preview_page
    finally:
        await context.close()
        await browser.close()
        await playwright.stop()
