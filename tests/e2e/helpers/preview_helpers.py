"""Preview page helpers for E2E testing.

Provides utilities for opening and navigating to note.com preview pages.
Extracted from conftest.py to enable reuse across test modules.

As of Issue #134, preview access uses the API-based approach (get_preview_access_token)
instead of navigating through the editor UI.
"""

from __future__ import annotations

import logging
import os
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright

from note_mcp.api.articles import build_preview_url, get_preview_access_token

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


def _get_headless_default() -> bool:
    """Get default headless mode from environment variable.

    Uses NOTE_MCP_TEST_HEADLESS environment variable.
    Default: True (headless mode for CI/CD stability)

    Set NOTE_MCP_TEST_HEADLESS=false to show browser window for debugging.

    Returns:
        True if headless mode is enabled (default)
    """
    return os.environ.get("NOTE_MCP_TEST_HEADLESS", "true").lower() != "false"


async def open_preview_via_api(
    page: Page,
    session: Session,
    article_key: str,
    timeout: int = DEFAULT_NAVIGATION_TIMEOUT_MS,
) -> Page:
    """Navigate directly to preview URL using API-obtained token.

    Much faster than editor-based approach - no menu navigation required.
    Uses the access_tokens API to get a preview token, then navigates
    directly to the preview URL.

    Args:
        page: Playwright Page instance with session cookies injected
        session: Authenticated session (for API access)
        article_key: Article key (e.g., "n1234567890ab")
        timeout: Navigation timeout in milliseconds

    Returns:
        Same page instance (navigated to preview URL)

    Raises:
        NoteAPIError: If token fetch fails
        TimeoutError: If navigation times out
    """
    # Get preview access token via API
    logger.debug("Fetching preview access token for article: %s", article_key)
    token = await get_preview_access_token(session, article_key)
    logger.debug("Successfully obtained preview token")

    # Build direct preview URL
    preview_url = build_preview_url(article_key, token)
    logger.debug("Navigating to preview URL: %s", preview_url)

    # Navigate directly to preview URL
    await page.goto(
        preview_url,
        wait_until="domcontentloaded",
        timeout=timeout,
    )
    # Wait for JavaScript rendering (needed for math formulas like nwc-formula)
    await page.wait_for_load_state("networkidle", timeout=timeout)
    logger.debug("Preview page loaded successfully for article: %s", article_key)

    return page


async def open_preview_for_article_key(
    page: Page,
    article_key: str,
    timeout: int = DEFAULT_NAVIGATION_TIMEOUT_MS,
) -> Page:
    """Navigate to editor and open preview, returning the preview page.

    .. deprecated::
        Use :func:`open_preview_via_api` instead for faster access.
        This function navigates through the editor UI, which is slower
        and more fragile. The API-based approach is preferred.

    Opens the note.com editor for the given article key, then clicks
    the preview button to open the preview in a new tab.

    Args:
        page: Playwright Page instance with session cookies injected
        article_key: Article key (e.g., "n1234567890ab")
        timeout: Navigation timeout in milliseconds

    Returns:
        Playwright Page for the preview tab

    Raises:
        TimeoutError: If navigation or element waits time out
    """
    warnings.warn(
        "open_preview_for_article_key is deprecated. Use open_preview_via_api instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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
    headless: bool | None = None,
) -> AsyncGenerator[Page]:
    """Open preview page with automatic browser lifecycle management.

    Creates a fresh browser context, injects session cookies, and opens
    the article preview page using API-based access (Issue #134).
    Automatically cleans up all browser resources on context exit.

    Args:
        session: Authenticated Session object with cookies
        article_key: Article key (e.g., "n1234567890ab")
        headless: Whether to run browser in headless mode.
            Default: True (from NOTE_MCP_TEST_HEADLESS env var).
            Set NOTE_MCP_TEST_HEADLESS=false to show browser window.

    Yields:
        Playwright Page for the preview

    Raises:
        NoteAPIError: If preview token fetch fails
        TimeoutError: If navigation times out

    Example:
        async with preview_page_context(session, article_key) as preview_page:
            validator = PreviewValidator(preview_page)
            result = await validator.validate_toc()
    """
    if headless is None:
        headless = _get_headless_default()

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        await _inject_session_cookies(page, session)
        # Issue #134: Use API-based approach instead of editor navigation
        preview_page = await open_preview_via_api(page, session, article_key)
        yield preview_page
    finally:
        await context.close()
        await browser.close()
        await playwright.stop()
