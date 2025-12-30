"""Browser-based article retrieval for note.com.

Uses Playwright to retrieve article content via the note.com editor interface.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from note_mcp.browser.manager import BrowserManager
from note_mcp.browser.url_helpers import validate_article_edit_url
from note_mcp.models import Article, ArticleStatus
from note_mcp.utils.html_to_markdown import html_to_markdown

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from note_mcp.models import Session


# note.com edit URL (accessed via note.com for proper auth flow)
NOTE_EDIT_URL = "https://note.com/notes"


async def get_article_via_browser(
    session: Session,
    article_id: str,
) -> Article:
    """Get article content via browser automation.

    Navigates to the article's edit page and extracts content.

    Args:
        session: Authenticated session
        article_id: ID of the article to retrieve

    Returns:
        Article object with content

    Raises:
        RuntimeError: If article retrieval fails
    """
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

    # Navigate to article edit page
    edit_url = f"{NOTE_EDIT_URL}/{article_id}/edit"
    await page.goto(edit_url, wait_until="domcontentloaded")

    # Wait for network to be idle (all initial requests completed)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception as e:
        logger.warning(f"Network idle wait interrupted for article {article_id}: {type(e).__name__}: {e}")

    await asyncio.sleep(2)  # Additional wait for JavaScript initialization

    # Check if we're on the right page (allow various redirect patterns)
    current_url = page.url
    if not validate_article_edit_url(current_url, article_id):
        raise RuntimeError(f"Failed to navigate to article edit page. Current URL: {current_url}")

    # Wait for the editor to be fully ready
    try:
        await page.wait_for_selector(".ProseMirror", state="visible", timeout=10000)
    except Exception as e:
        logger.warning(f"Editor selector wait interrupted for article {article_id}: {type(e).__name__}: {e}")

    await asyncio.sleep(1)  # Wait for editor initialization to complete

    # Extract title
    title = ""
    title_selectors = [
        'input[placeholder*="タイトル"]',
        'textarea[placeholder*="タイトル"]',
        '[data-testid="title-input"]',
    ]
    for selector in title_selectors:
        try:
            title_element = page.locator(selector).first
            if await title_element.count() > 0:
                title = await title_element.input_value()
                if title:
                    break
        except Exception as e:
            logger.debug(f"Title selector '{selector}' failed: {type(e).__name__}: {e}")
            continue

    # Extract body (HTML to Markdown to preserve structure including code blocks)
    body = ""
    body_selectors = [
        ".ProseMirror",
        '[data-testid="body-editor"]',
        ".note-body-editor",
    ]
    for selector in body_selectors:
        try:
            body_element = page.locator(selector).first
            if await body_element.count() > 0:
                body_html = await body_element.inner_html()
                body = html_to_markdown(body_html)
                if body:
                    break
        except Exception as e:
            logger.debug(f"Body selector '{selector}' failed: {type(e).__name__}: {e}")
            continue

    # Warn if title or body extraction failed
    if not title:
        logger.warning(f"Failed to extract title for article {article_id}")
    if not body:
        logger.warning(f"Failed to extract body for article {article_id}")

    # Return Article with extracted content
    return Article(
        id=article_id,
        key=article_id,
        title=title,
        body=body,
        status=ArticleStatus.DRAFT,  # Default, actual status unknown from editor
        tags=[],  # Tags not easily extractable from editor UI
    )
