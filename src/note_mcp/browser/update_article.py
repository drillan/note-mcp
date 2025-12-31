"""Browser-based article update for note.com.

Uses Playwright to update articles via the note.com web interface.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from playwright.async_api import Error as PlaywrightError

from note_mcp.browser.manager import BrowserManager
from note_mcp.browser.toc_helpers import insert_toc_at_placeholder
from note_mcp.browser.typing_helpers import type_markdown_content
from note_mcp.browser.url_helpers import validate_article_edit_url
from note_mcp.models import Article, ArticleStatus, BrowserArticleResult

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from note_mcp.models import ArticleInput, Session


# note.com edit URL (accessed via note.com for proper auth flow)
NOTE_EDIT_URL = "https://note.com/notes"


async def update_article_via_browser(
    session: Session,
    article_id: str,
    article_input: ArticleInput,
) -> BrowserArticleResult:
    """Update an article via browser automation.

    Navigates to the article's edit page, updates the content,
    and waits for auto-save to complete.

    Args:
        session: Authenticated session
        article_id: ID of the article to update
        article_input: New article content and metadata

    Returns:
        BrowserArticleResult containing the updated article and TOC insertion status

    Raises:
        RuntimeError: If article update fails
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

    await asyncio.sleep(2)  # Wait for editor initialization to complete

    # Fill the title
    title_selectors = [
        'input[placeholder*="タイトル"]',
        'textarea[placeholder*="タイトル"]',
        '[data-testid="title-input"]',
        '[contenteditable="true"]:first-of-type',
    ]
    title_filled = False
    for selector in title_selectors:
        try:
            title_element = page.locator(selector).first
            if await title_element.count() > 0:
                await title_element.click()
                await page.keyboard.press("Control+a")
                await title_element.fill(article_input.title)
                title_filled = True
                break
        except Exception as e:
            logger.debug(f"Title selector '{selector}' failed: {type(e).__name__}: {e}")
            continue

    if not title_filled:
        try:
            await page.keyboard.press("Tab")
            await page.keyboard.press("Control+a")
            await page.keyboard.type(article_input.title)
            title_filled = True
        except Exception as e:
            logger.warning(f"Title fill fallback failed for article {article_id}: {type(e).__name__}: {e}")

    # Fill the body
    await asyncio.sleep(0.5)
    body_selectors = [
        ".ProseMirror",
        '[data-testid="body-editor"]',
        ".note-body-editor",
        '[contenteditable="true"]:not(:first-of-type)',
    ]
    body_filled = False
    for selector in body_selectors:
        try:
            body_element = page.locator(selector).first
            if await body_element.count() > 0:
                await body_element.click()
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Delete")
                # Use type_markdown_content for proper blockquote/list handling
                await type_markdown_content(page, article_input.body)
                body_filled = True
                break
        except Exception as e:
            logger.debug(f"Body selector '{selector}' failed: {type(e).__name__}: {e}")
            continue

    if not body_filled:
        try:
            await page.keyboard.press("Tab")
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")
            await type_markdown_content(page, article_input.body)
            body_filled = True
        except Exception as e:
            logger.warning(f"Body fill fallback failed for article {article_id}: {type(e).__name__}: {e}")

    # Insert TOC at placeholder if present (after body typing, before save)
    toc_inserted = False
    toc_error: str | None = None
    try:
        toc_inserted = await insert_toc_at_placeholder(page)
        if toc_inserted:
            logger.info(f"TOC inserted into article {article_id}")
    except (TimeoutError, PlaywrightError) as e:
        toc_error = str(e)
        logger.warning(f"TOC insertion failed for article {article_id}: {toc_error}")
        # TOC insertion failure is not fatal

    # Click save draft button explicitly instead of relying on auto-save
    await asyncio.sleep(1)

    save_button_selectors = [
        'button:has-text("下書き保存")',
        '[data-testid="save-draft-button"]',
        'button:has-text("保存")',
        ".save-button",
    ]
    save_clicked = False
    for selector in save_button_selectors:
        try:
            save_button = page.locator(selector).first
            if await save_button.count() > 0:
                await save_button.click()
                await asyncio.sleep(2)  # Wait for save to complete
                save_clicked = True
                break
        except Exception as e:
            logger.debug(f"Save button selector '{selector}' failed: {type(e).__name__}: {e}")
            continue

    if not save_clicked:
        logger.warning(f"Failed to click save button for article {article_id}. Changes may not be saved.")

    # Wait for save confirmation
    await asyncio.sleep(2)

    # Create Article object with updated info
    article = Article(
        id=article_id,
        key=article_id,
        title=article_input.title,
        body=article_input.body,
        status=ArticleStatus.DRAFT,
        tags=article_input.tags,
    )

    return BrowserArticleResult(
        article=article,
        toc_inserted=toc_inserted if toc_inserted else None,
        toc_error=toc_error,
    )
