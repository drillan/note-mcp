"""Browser-based embed insertion for note.com.

Uses Playwright to insert embedded content (YouTube, Twitter, note.com articles)
into ProseMirror editor via browser automation.

note.com only supports embedding from specific services:
- YouTube: Video player embed
- Twitter/X: Tweet card embed
- note.com articles: Article card embed

Other URLs remain as plain links.
"""

from __future__ import annotations

import asyncio
import logging
import re
from enum import Enum
from typing import TYPE_CHECKING

from playwright.async_api import Error as PlaywrightError

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class EmbedResult(Enum):
    """埋め込み挿入の結果タイプ。

    埋め込みを挿入しようとした場合、以下の3つの結果があり得る:
    - SUCCESS: 埋め込みカードが正常に挿入された
    - LINK_INSERTED: URLが無効（削除済み、非公開等）でリンクとして挿入された
    - TIMEOUT: タイムアウト（予期しない失敗）
    """

    SUCCESS = "success"  # 埋め込みカード挿入成功
    LINK_INSERTED = "link"  # リンクとして挿入（URL無効等）
    TIMEOUT = "timeout"  # タイムアウト（予期しない失敗）


# Supported embed services and their URL patterns
YOUTUBE_PATTERN = re.compile(r"^https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+")
TWITTER_PATTERN = re.compile(r"^https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+")
NOTE_PATTERN = re.compile(r"^https?://note\.com/\w+/n/\w+")

# note.com editor selectors
_EDITOR_SELECTOR = ".ProseMirror"
_ADD_BUTTON_SELECTOR = 'button[aria-label="メニューを開く"]'
_EMBED_MENU_ITEM_TEXT = "埋め込み"
_EMBED_URL_INPUT_SELECTOR = 'textarea[placeholder="https://example.com"]'
_EMBED_APPLY_BUTTON_TEXT = "適用"
_EMBED_FIGURE_SELECTOR = "figure[embedded-service]"

# Timing constants
_CLICK_WAIT_SECONDS = 0.3
_INPUT_WAIT_SECONDS = 0.2
_EMBED_WAIT_TIMEOUT_MS = 10000


def is_supported_embed_url(url: str) -> bool:
    """Check if URL is from a supported embed service.

    Args:
        url: URL to check.

    Returns:
        True if URL is from YouTube, Twitter, or note.com.
    """
    return bool(YOUTUBE_PATTERN.match(url) or TWITTER_PATTERN.match(url) or NOTE_PATTERN.match(url))


def get_embed_service(url: str) -> str | None:
    """Get the embed service name for a URL.

    Args:
        url: URL to check.

    Returns:
        Service name ('youtube', 'twitter', 'note') or None if unsupported.
    """
    if YOUTUBE_PATTERN.match(url):
        return "youtube"
    if TWITTER_PATTERN.match(url):
        return "twitter"
    if NOTE_PATTERN.match(url):
        return "note"
    return None


async def insert_embed_at_cursor(
    page: Page,
    url: str,
    timeout: int = _EMBED_WAIT_TIMEOUT_MS,
) -> tuple[EmbedResult, str]:
    """Insert an embed at the current cursor position in the editor.

    This function uses the note.com editor's embed dialog:
    1. Click the "+" (add) button to open the menu
    2. Click "埋め込み" (embed) menu item
    3. Enter URL in the textarea
    4. Click "適用" (apply) button
    5. Wait for the embed figure or link to appear

    Args:
        page: Playwright page with note.com editor.
        url: URL to embed (YouTube, Twitter, or note.com).
        timeout: Maximum wait time in milliseconds for embed to appear.

    Returns:
        Tuple of (EmbedResult indicating what happened, debug info string).
        - EmbedResult.SUCCESS: Embed card was inserted
        - EmbedResult.LINK_INSERTED: URL was inserted as link (URL may be invalid)
        - EmbedResult.TIMEOUT: Neither detected within timeout

    Raises:
        ValueError: If URL is not from a supported service.
    """
    debug_steps: list[str] = []

    # Validate URL is from supported service
    service = get_embed_service(url)
    if not service:
        raise ValueError(f"Unsupported embed URL: {url}. Only YouTube, Twitter, and note.com URLs are supported.")

    logger.info(f"Inserting {service} embed: {url}")
    debug_steps.append(f"service={service}")

    # Get initial embed count
    initial_count = await _get_embed_count(page)
    logger.info(f"Step 0: Initial embed count: {initial_count}")
    debug_steps.append(f"cnt={initial_count}")

    # Step 1: Click the "+" button to open menu
    logger.info("Step 1: Clicking add button...")
    if not await _click_add_button(page):
        logger.error("Step 1 FAILED: Could not click add button")
        debug_steps.append("S1:FAIL")
        return EmbedResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S1:OK")

    # Step 2: Click "埋め込み" menu item
    logger.info("Step 2: Clicking embed menu item...")
    if not await _click_embed_menu_item(page):
        logger.error("Step 2 FAILED: Could not click embed menu item")
        debug_steps.append("S2:FAIL")
        return EmbedResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S2:OK")

    # Step 3: Enter URL in textarea
    logger.info(f"Step 3: Entering URL: {url}")
    if not await _enter_embed_url(page, url):
        logger.error("Step 3 FAILED: Could not enter embed URL")
        debug_steps.append("S3:FAIL")
        return EmbedResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S3:OK")

    # Step 4: Click "適用" button
    logger.info("Step 4: Clicking apply button...")
    if not await _click_apply_button(page):
        logger.error("Step 4 FAILED: Could not click apply button")
        debug_steps.append("S4:FAIL")
        return EmbedResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S4:OK")

    # Step 5: Wait for embed or link to appear
    logger.info("Step 5: Waiting for embed figure or link to appear...")
    result = await _wait_for_embed_insertion(page, initial_count, timeout, url)
    debug_steps.append(f"S5:{result.value}")

    if result == EmbedResult.SUCCESS:
        logger.info(f"Successfully inserted {service} embed")
    elif result == EmbedResult.LINK_INSERTED:
        logger.info(f"URL inserted as link (may be invalid): {url}")
    else:
        logger.error("Step 5 FAILED: Neither embed nor link detected within timeout")

    return result, "|".join(debug_steps)


async def _get_embed_count(page: Page) -> int:
    """Get current count of embed figures in editor.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        Number of embed figures.
    """
    count = await page.evaluate(
        f"""
        () => {{
            const editor = document.querySelector('{_EDITOR_SELECTOR}');
            if (!editor) return 0;
            return editor.querySelectorAll('{_EMBED_FIGURE_SELECTOR}').length;
        }}
        """
    )
    return count or 0


async def _click_add_button(page: Page) -> bool:
    """Click the "+" add button to open the insert menu.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if button was clicked successfully.
    """
    try:
        # First click on editor to ensure focus and show the add button
        editor = page.locator(_EDITOR_SELECTOR).first
        if await editor.count() > 0:
            await editor.click()
            await asyncio.sleep(_CLICK_WAIT_SECONDS)

        # Find and click the add button
        add_button = page.locator(_ADD_BUTTON_SELECTOR).first
        if await add_button.count() > 0:
            await add_button.click()
            await asyncio.sleep(_CLICK_WAIT_SECONDS)
            logger.debug("Clicked add button")
            return True

        # Fallback: Try JavaScript to find the button
        clicked = await page.evaluate(
            f"""
            () => {{
                const btn = document.querySelector('{_ADD_BUTTON_SELECTOR}');
                if (btn) {{
                    btn.click();
                    return true;
                }}
                return false;
            }}
            """
        )
        if clicked:
            await asyncio.sleep(_CLICK_WAIT_SECONDS)
            logger.debug("Clicked add button via JavaScript")
            return True

        logger.warning("Add button not found")
        return False

    except Exception as e:
        logger.warning(f"Error clicking add button: {type(e).__name__}: {e}")
        return False


async def _click_embed_menu_item(page: Page) -> bool:
    """Click the "埋め込み" menu item.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if menu item was clicked successfully.
    """
    try:
        # Find button with text "埋め込み"
        embed_button = page.locator(f'button:has-text("{_EMBED_MENU_ITEM_TEXT}")').first
        if await embed_button.count() > 0:
            await embed_button.click()
            await asyncio.sleep(_CLICK_WAIT_SECONDS)
            logger.debug("Clicked embed menu item")
            return True

        # Fallback: Try JavaScript
        clicked = await page.evaluate(
            f"""
            () => {{
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {{
                    if (btn.textContent.includes('{_EMBED_MENU_ITEM_TEXT}')) {{
                        btn.click();
                        return true;
                    }}
                }}
                return false;
            }}
            """
        )
        if clicked:
            await asyncio.sleep(_CLICK_WAIT_SECONDS)
            logger.debug("Clicked embed menu item via JavaScript")
            return True

        logger.warning("Embed menu item not found")
        return False

    except Exception as e:
        logger.warning(f"Error clicking embed menu item: {type(e).__name__}: {e}")
        return False


async def _enter_embed_url(page: Page, url: str) -> bool:
    """Enter URL into the embed dialog textarea.

    Args:
        page: Playwright page with note.com editor.
        url: URL to enter.

    Returns:
        True if URL was entered successfully.
    """
    try:
        # Wait for textarea to appear
        textarea = page.locator(_EMBED_URL_INPUT_SELECTOR).first
        await textarea.wait_for(state="visible", timeout=5000)

        # Clear and enter URL
        await textarea.fill(url)
        await asyncio.sleep(_INPUT_WAIT_SECONDS)
        logger.debug(f"Entered URL: {url}")
        return True

    except Exception as e:
        # Fallback: Try JavaScript
        try:
            entered = await page.evaluate(
                f"""
                (url) => {{
                    const textarea = document.querySelector('{_EMBED_URL_INPUT_SELECTOR}');
                    if (textarea) {{
                        textarea.value = url;
                        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        return true;
                    }}
                    return false;
                }}
                """,
                url,
            )
            if entered:
                await asyncio.sleep(_INPUT_WAIT_SECONDS)
                logger.debug(f"Entered URL via JavaScript: {url}")
                return True
        except Exception as js_error:
            logger.warning(f"JavaScript URL entry failed: {js_error}")

        logger.warning(f"Error entering embed URL: {type(e).__name__}: {e}")
        return False


async def _click_apply_button(page: Page) -> bool:
    """Click the "適用" apply button.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if button was clicked successfully.
    """
    try:
        # Find button with text "適用"
        apply_button = page.locator(f'button:has-text("{_EMBED_APPLY_BUTTON_TEXT}")').first
        if await apply_button.count() > 0:
            await apply_button.click()
            await asyncio.sleep(_CLICK_WAIT_SECONDS)
            logger.debug("Clicked apply button")
            return True

        # Fallback: Try JavaScript
        clicked = await page.evaluate(
            f"""
            () => {{
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {{
                    if (btn.textContent.includes('{_EMBED_APPLY_BUTTON_TEXT}')) {{
                        btn.click();
                        return true;
                    }}
                }}
                return false;
            }}
            """
        )
        if clicked:
            await asyncio.sleep(_CLICK_WAIT_SECONDS)
            logger.debug("Clicked apply button via JavaScript")
            return True

        logger.warning("Apply button not found")
        return False

    except Exception as e:
        logger.warning(f"Error clicking apply button: {type(e).__name__}: {e}")
        return False


async def _wait_for_embed_insertion(
    page: Page,
    initial_count: int,
    timeout: int,
    url: str,
) -> EmbedResult:
    """Wait for embed figure or link to appear in editor.

    Monitors the editor for either:
    1. Embed card insertion (SUCCESS)
    2. Link insertion (LINK_INSERTED) - occurs when URL is invalid
    3. Timeout (TIMEOUT) - neither detected within timeout

    Args:
        page: Playwright page with note.com editor.
        initial_count: Number of embeds before insertion.
        timeout: Maximum wait time in milliseconds.
        url: URL being embedded (used for link detection).

    Returns:
        EmbedResult indicating what happened.
    """
    try:
        # Wait for either embed card or link to appear
        result = await page.evaluate(
            f"""
            async (args) => {{
                const {{ initialCount, timeout, url }} = args;
                const startTime = Date.now();

                // Get initial link count for this URL
                const editor = document.querySelector('{_EDITOR_SELECTOR}');
                if (!editor) {{
                    return {{ type: 'timeout', reason: 'editor_not_found' }};
                }}

                const getEmbedCount = () => {{
                    return editor.querySelectorAll('{_EMBED_FIGURE_SELECTOR}').length;
                }};

                const hasNewLink = () => {{
                    // Check if a link with this URL exists in the editor
                    const links = editor.querySelectorAll('a');
                    for (const link of links) {{
                        if (link.href === url || link.textContent === url) {{
                            return true;
                        }}
                    }}
                    return false;
                }};

                // Record initial state
                const initialLinkExists = hasNewLink();

                while (Date.now() - startTime < timeout) {{
                    // Check for embed card first
                    if (getEmbedCount() > initialCount) {{
                        return {{ type: 'success' }};
                    }}

                    // Check for link (if it didn't exist before)
                    if (!initialLinkExists && hasNewLink()) {{
                        return {{ type: 'link_inserted' }};
                    }}

                    await new Promise(r => setTimeout(r, 200));
                }}
                return {{ type: 'timeout', reason: 'no_change_detected' }};
            }}
            """,
            {"initialCount": initial_count, "timeout": timeout, "url": url},
        )

        result_type = result.get("type", "timeout") if result else "timeout"

        if result_type == "success":
            logger.debug("Embed card inserted successfully")
            return EmbedResult.SUCCESS
        elif result_type == "link_inserted":
            logger.info(f"Link inserted instead of embed card (URL may be invalid): {url}")
            return EmbedResult.LINK_INSERTED
        else:
            reason = result.get("reason", "unknown") if result else "unknown"
            logger.warning(f"Embed not inserted within timeout: {reason}")
            return EmbedResult.TIMEOUT

    except PlaywrightError as e:
        logger.warning(f"Playwright error waiting for embed insertion: {type(e).__name__}: {e}")
        return EmbedResult.TIMEOUT
    except Exception as e:
        logger.error(f"Unexpected error waiting for embed insertion: {type(e).__name__}: {e}")
        raise
