"""Browser-based draft creation for note.com.

Uses Playwright to create drafts via the note.com web interface.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from typing import TYPE_CHECKING, Any

from playwright.async_api import Error as PlaywrightError

from note_mcp.browser.manager import BrowserManager
from note_mcp.browser.text_align_helpers import apply_text_alignments
from note_mcp.browser.toc_helpers import insert_toc_at_placeholder
from note_mcp.browser.typing_helpers import type_markdown_content
from note_mcp.models import Article, ArticleStatus, BrowserArticleResult

if TYPE_CHECKING:
    from note_mcp.models import ArticleInput, Session

logger = logging.getLogger(__name__)


# note.com URLs
NOTE_NEW_ARTICLE_URL = "https://note.com/notes/new"


async def create_draft_via_browser(
    session: Session,
    article_input: ArticleInput,
) -> BrowserArticleResult:
    """Create a draft article via browser automation.

    Navigates to the note.com new article page, fills in the content,
    and waits for auto-save to complete.

    Args:
        session: Authenticated session
        article_input: Article content and metadata

    Returns:
        BrowserArticleResult containing the created article and TOC insertion status

    Raises:
        RuntimeError: If draft creation fails
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

    # Navigate to new article page
    await page.goto(NOTE_NEW_ARTICLE_URL, wait_until="domcontentloaded")

    # Wait for network to be idle (all initial requests completed)
    with contextlib.suppress(Exception):
        await page.wait_for_load_state("networkidle", timeout=10000)

    await asyncio.sleep(2)  # Additional wait for JavaScript initialization

    # Check if we're on the right page
    # note.com may redirect to editor.note.com for the editor
    current_url = page.url
    valid_patterns = ["notes/new", "/n/", "editor.note.com"]
    if not any(pattern in current_url for pattern in valid_patterns):
        raise RuntimeError(f"Failed to navigate to new article page. Current URL: {current_url}")

    # Wait for the editor to be fully ready
    # Look for the ProseMirror editor element
    with contextlib.suppress(Exception):
        await page.wait_for_selector(".ProseMirror", state="visible", timeout=10000)

    await asyncio.sleep(2)  # Wait for editor initialization to complete

    # Fill the title using Playwright's type method
    # Try multiple selectors for the title input
    title_filled = False
    title_selectors = [
        'input[placeholder*="タイトル"]',
        'textarea[placeholder*="タイトル"]',
        '[data-testid="title-input"]',
        '[contenteditable="true"]:first-of-type',
    ]
    for selector in title_selectors:
        try:
            title_element = page.locator(selector).first
            if await title_element.count() > 0:
                await title_element.click()
                await title_element.fill(article_input.title)
                title_filled = True
                break
        except Exception:
            continue

    if not title_filled:
        # Fallback: try to find any contenteditable and type
        try:
            await page.keyboard.press("Tab")  # Move focus
            await page.keyboard.type(article_input.title)
        except Exception:
            pass

    # Fill the body - note.com uses a rich text editor (ProseMirror)
    # We need to click on the body area and type the content as plain text
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
                # Clear existing content
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Delete")
                # Type content line by line with Enter key
                # This allows ProseMirror to properly interpret list items
                await type_markdown_content(page, article_input.body)
                body_filled = True
                break
        except Exception:
            continue

    if not body_filled:
        # Fallback: Tab to body and type
        try:
            await page.keyboard.press("Tab")
            await type_markdown_content(page, article_input.body)
        except Exception:
            pass

    # Insert TOC at placeholder if present (after body typing, before save)
    toc_inserted = False
    toc_error: str | None = None
    try:
        toc_inserted = await insert_toc_at_placeholder(page)
        if toc_inserted:
            logger.info("TOC inserted into draft")
    except (TimeoutError, PlaywrightError) as e:
        toc_error = str(e)
        logger.warning(f"TOC insertion failed: {toc_error}")
        # TOC insertion failure is not fatal

    # Apply text alignments at placeholder positions (after body typing, before save)
    alignments_applied = 0
    alignment_error: str | None = None
    try:
        alignments_applied = await apply_text_alignments(page)
        if alignments_applied > 0:
            logger.info(f"Applied {alignments_applied} text alignment(s) to draft")
    except (TimeoutError, PlaywrightError) as e:
        alignment_error = str(e)
        logger.warning(f"Text alignment application failed: {alignment_error}")
        # Text alignment failure is not fatal

    # Click save draft button explicitly instead of relying on auto-save
    await asyncio.sleep(1)

    save_button_selectors = [
        'button:has-text("下書き保存")',
        '[data-testid="save-draft-button"]',
        'button:has-text("保存")',
        ".save-button",
    ]
    for selector in save_button_selectors:
        try:
            save_button = page.locator(selector).first
            if await save_button.count() > 0:
                await save_button.click()
                await asyncio.sleep(2)  # Wait for save to complete
                break
        except Exception:
            continue

    # Wait for save confirmation
    await asyncio.sleep(2)

    # Extract article key from URL
    article_key = await page.evaluate(
        """
        () => {
            const match = window.location.href.match(/(?:\\/n\\/|\\/notes\\/)(n[a-zA-Z0-9]+)/);
            return match ? match[1] : null;
        }
        """
    )

    # Wait a bit more for auto-save
    await asyncio.sleep(2)

    # Get the article key from URL if not returned by JavaScript
    # Supports both /n/{key} and /notes/{key}/ formats
    if not article_key:
        current_url = page.url
        match = re.search(r"(?:/n/|/notes/)(n[a-zA-Z0-9]+)", current_url)
        if match:
            article_key = match.group(1)

    if not article_key:
        raise RuntimeError("Failed to create draft: could not get article key from URL")

    # Create Article object with available info
    article = Article(
        id=article_key,  # Use key as ID since we don't have the actual ID
        key=article_key,
        title=article_input.title,
        body=article_input.body,
        status=ArticleStatus.DRAFT,
        tags=article_input.tags,
    )

    return BrowserArticleResult(
        article=article,
        toc_inserted=toc_inserted if toc_inserted else None,
        toc_error=toc_error,
        alignments_applied=alignments_applied if alignments_applied > 0 else None,
        alignment_error=alignment_error,
    )
