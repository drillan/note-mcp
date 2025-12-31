"""Browser-based image insertion for note.com.

Uses Playwright to insert images into ProseMirror editor via browser automation.
This bypasses the API limitation where HTML image tags are not properly saved.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from note_mcp.api.images import validate_image_file
from note_mcp.browser.manager import BrowserManager
from note_mcp.browser.url_helpers import validate_article_edit_url
from note_mcp.models import ErrorCode, NoteAPIError

if TYPE_CHECKING:
    from playwright.async_api import Page

    from note_mcp.models import Session

logger = logging.getLogger(__name__)

# note.com edit URL
NOTE_EDIT_URL = "https://note.com/notes"


async def _dismiss_ai_dialog(page: Page) -> None:
    """Dismiss the AI dialog popup if present.

    note.com shows an "AIと相談" (Consult with AI) dialog on page load.
    This function clicks the × button to dismiss it.

    Args:
        page: Playwright Page instance
    """
    try:
        # Look for the AI dialog close button (× button)
        # The dialog has "AIと相談" text and a close button
        close_selectors = [
            'button[aria-label="閉じる"]',
            '[aria-label="close"]',
            '.ai-dialog button:has-text("×")',
            'button:near(:text("AIと相談")):has-text("×")',
        ]

        for selector in close_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    await button.click()
                    await asyncio.sleep(0.5)
                    logger.debug(f"Dismissed AI dialog using selector: {selector}")
                    return
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {type(e).__name__}: {e}")
                continue

        # Try clicking × directly by locating the dialog element
        # The dialog typically has a dark background with "AIと相談" text
        dialog_result = await page.evaluate(
            """
            () => {
                // Find dialog by looking for "AIと相談" text
                const dialogs = document.querySelectorAll('[class*="dialog"], [class*="popup"], [class*="modal"]');
                for (const dialog of dialogs) {
                    if (dialog.textContent.includes('AIと相談')) {
                        // Find close button within or near the dialog
                        const closeBtn = dialog.querySelector('button, [role="button"]');
                        if (closeBtn) {
                            closeBtn.click();
                            return true;
                        }
                    }
                }
                // Try finding a button with × near AI text
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.textContent.trim() === '×' || btn.textContent.trim() === '✕') {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
            """
        )
        if dialog_result:
            await asyncio.sleep(0.5)
            logger.debug("Dismissed AI dialog via JavaScript")
    except Exception as e:
        logger.debug(f"No AI dialog to dismiss or error: {e}")


async def _setup_page_with_session(session: Session, article_id: str) -> Page:
    """Setup browser page with session cookies and navigate to article edit page.

    Args:
        session: Authenticated session
        article_id: ID of the article to edit

    Returns:
        Playwright Page instance ready for editing

    Raises:
        RuntimeError: If navigation fails
    """
    manager = BrowserManager.get_instance()
    page = await manager.get_page()

    # Inject session cookies for .note.com domain
    # The browser will automatically share cookies with subdomains (editor.note.com)
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

    # Wait for network to be idle
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception as e:
        logger.warning(f"Network idle wait interrupted: {type(e).__name__}: {e}")

    # Validate URL first
    current_url = page.url
    if not validate_article_edit_url(current_url, article_id):
        raise RuntimeError(f"Failed to navigate to article edit page. Current URL: {current_url}")

    # Dismiss AI dialog FIRST before waiting for editor
    # The dialog can block editor initialization
    await _dismiss_ai_dialog(page)

    # Wait additional time for React to mount the editor component
    # The editor is lazy-loaded after article data is fetched
    await asyncio.sleep(3)

    # Try to wait for editor with extended timeout
    editor_found = False
    try:
        await page.wait_for_selector(".ProseMirror", state="visible", timeout=20000)
        editor_found = True
    except Exception as e:
        logger.warning(f"Initial editor wait failed: {type(e).__name__}: {e}")

    # If editor not found, try clicking on the main content area to trigger initialization
    if not editor_found:
        logger.info("Attempting to trigger editor initialization by clicking main area")
        try:
            # Click on main content area where editor should appear
            main_selectors = [
                "main",
                '[class*="editor"]',
                '[class*="body"]',
                ".sc-523daef7-0",  # Editor container class from HTML
            ]
            for selector in main_selectors:
                element = page.locator(selector).first
                if await element.count() > 0:
                    await element.click()
                    await asyncio.sleep(1)
                    break

            # Wait again for editor
            await page.wait_for_selector(".ProseMirror", state="visible", timeout=15000)
            editor_found = True
        except Exception as e:
            logger.warning(f"Second editor wait failed: {type(e).__name__}: {e}")
            # Save debug files only if debug directory exists
            try:
                debug_dir = Path("debug")
                if debug_dir.exists():
                    await page.screenshot(path="debug/editor_wait_failed.png")
                    html_content = await page.content()
                    Path("debug/editor_html.html").write_text(html_content)
            except Exception as debug_error:
                logger.debug(f"Failed to save debug files: {debug_error}")

    if not editor_found:
        raise RuntimeError("Editor failed to load - ProseMirror element not found")

    await asyncio.sleep(1)

    return page


async def _click_add_image_button(page: Page) -> bool:
    """Click the add image button in the editor.

    note.com editor shows a floating menu with options like "画像", "音声", etc.
    The menu may already be visible on page load, or may appear after clicking
    on the editor.

    Flow:
    1. Check if "画像" button is already visible
    2. If not, click on the editor to trigger the menu
    3. Click "画像" in the menu

    Args:
        page: Playwright Page instance

    Returns:
        True if button was clicked successfully
    """
    # First, try to click "画像" button directly (it may already be visible)
    image_clicked = await page.evaluate(
        """() => {
        const buttons = document.querySelectorAll("button");
        for (const btn of buttons) {
            const text = btn.textContent.trim();
            const rect = btn.getBoundingClientRect();
            // Look for "画像" button in the menu area (y > 300)
            if (text === "画像" && rect.y > 300 && rect.y < 700) {
                btn.click();
                return { clicked: true, text: text, y: rect.y };
            }
        }
        return { clicked: false };
    }"""
    )

    if image_clicked.get("clicked"):
        logger.debug(f"Clicked 画像 button directly at y={image_clicked.get('y')}")
        await asyncio.sleep(0.3)
        return True

    # If not found, click on the editor to focus it and show the menu
    editor = page.locator(".ProseMirror").first
    if await editor.count() > 0:
        await editor.click()
        await asyncio.sleep(0.5)
        logger.debug("Clicked ProseMirror editor to show menu")

    # Try clicking "画像" button again
    image_clicked = await page.evaluate(
        """() => {
        const buttons = document.querySelectorAll("button");
        for (const btn of buttons) {
            const text = btn.textContent.trim();
            const rect = btn.getBoundingClientRect();
            // Look for "画像" button in the menu area (y > 300)
            if (text === "画像" && rect.y > 300 && rect.y < 700) {
                btn.click();
                return { clicked: true, text: text, y: rect.y };
            }
        }
        return { clicked: false };
    }"""
    )

    if image_clicked.get("clicked"):
        logger.debug(f"Clicked 画像 button after editor click at y={image_clicked.get('y')}")
        await asyncio.sleep(0.3)
        return True

    logger.warning("Could not find 画像 button")
    return False


async def _upload_image_via_file_chooser(page: Page, file_path: str) -> bool:
    """Upload image by setting file on hidden file input.

    note.com uses a hidden file input that accepts image files.
    After clicking the 画像 button in the floating menu, the file input
    becomes active and we can set files directly on it.

    Args:
        page: Playwright Page instance
        file_path: Path to the image file

    Returns:
        True if upload was initiated successfully
    """
    try:
        # Find the hidden file input for images
        # The input has accept attribute for image types
        file_input = page.locator('input[type="file"][accept*="image"]').first

        # Check if file input exists
        if await file_input.count() == 0:
            logger.warning("No file input found for images")
            return False

        # Set the file directly on the input element
        await file_input.set_input_files(file_path)
        logger.debug(f"File set on input element: {file_path}")

        # Wait for upload to process
        await asyncio.sleep(2)
        return True

    except Exception as e:
        logger.warning(f"File upload failed: {type(e).__name__}: {e}")
        return False


async def _wait_for_image_insertion(
    page: Page, initial_img_count: int, caption: str | None = None, timeout: int = 10000
) -> bool:
    """Wait for image to be inserted and optionally add caption.

    note.com inserts images directly into the editor after file upload.
    This function waits for the image count to increase, then adds caption
    to the figcaption element if provided.

    Args:
        page: Playwright Page instance
        initial_img_count: Number of images before upload
        caption: Optional caption for the image
        timeout: Maximum wait time in milliseconds

    Returns:
        True if image was inserted successfully
    """
    try:
        # Wait for image count to increase
        image_inserted = await page.evaluate(
            """
            async (args) => {
                const { initialCount, timeout } = args;
                const startTime = Date.now();
                while (Date.now() - startTime < timeout) {
                    const imgs = document.querySelectorAll('.ProseMirror figure img, .ProseMirror img');
                    if (imgs.length > initialCount) {
                        return true;
                    }
                    await new Promise(r => setTimeout(r, 500));
                }
                return false;
            }
            """,
            {"initialCount": initial_img_count, "timeout": timeout},
        )

        if not image_inserted:
            logger.warning("Image was not inserted within timeout")
            return False

        logger.debug("Image inserted into editor")
        await asyncio.sleep(0.5)

        # Enter caption if provided
        if caption:
            caption_success = await _input_image_caption(page, caption)
            if not caption_success:
                logger.warning(f"Failed to input caption: {caption}")

        return True

    except Exception as e:
        logger.warning(f"Image insertion wait failed: {type(e).__name__}: {e}")
        return False


async def _input_image_caption(page: Page, caption: str) -> bool:
    """Input caption for the uploaded image.

    Args:
        page: Playwright Page instance
        caption: Caption text for the image

    Returns:
        True if caption was entered successfully
    """
    if not caption:
        return True

    # Find the figcaption element for the most recently added image
    caption_selectors = [
        ".ProseMirror figure figcaption",
        ".ProseMirror figcaption[contenteditable='true']",
        ".ProseMirror [data-placeholder*='キャプション']",
    ]

    for selector in caption_selectors:
        try:
            # Get all figcaptions and click the last one (most recent image)
            figcaptions = page.locator(selector)
            count = await figcaptions.count()
            if count > 0:
                last_figcaption = figcaptions.nth(count - 1)
                await last_figcaption.click()
                await asyncio.sleep(0.2)
                await page.keyboard.type(caption)
                await asyncio.sleep(0.2)
                return True
        except Exception as e:
            logger.debug(f"Caption selector '{selector}' failed: {e}")
            continue

    # Fallback: Try JavaScript to find and focus figcaption
    try:
        result = await page.evaluate(
            """
            () => {
                const figcaptions = document.querySelectorAll('.ProseMirror figure figcaption');
                if (figcaptions.length === 0) return false;
                const lastFigcaption = figcaptions[figcaptions.length - 1];
                lastFigcaption.click();
                lastFigcaption.focus();
                return true;
            }
            """
        )
        if result:
            await asyncio.sleep(0.2)
            await page.keyboard.type(caption)
            return True
    except Exception as e:
        logger.warning(f"JavaScript figcaption focus failed: {e}")

    return False


async def _save_article(page: Page, max_retries: int = 3) -> bool:
    """Save the article by clicking the save button.

    Args:
        page: Playwright Page instance
        max_retries: Maximum number of retry attempts

    Returns:
        True if save was successful, False otherwise
    """
    # Wait a moment for editor state to stabilize
    await asyncio.sleep(1)

    for attempt in range(max_retries):
        # Try clicking the save button
        save_clicked = await page.evaluate(
            """() => {
            const buttons = document.querySelectorAll("button");
            for (const btn of buttons) {
                const text = btn.textContent.trim();
                if (text === "下書き保存") {
                    btn.click();
                    return true;
                }
            }
            return false;
        }"""
        )

        if not save_clicked:
            logger.warning("Could not find '下書き保存' button")
            return False

        logger.debug(f"Clicked '下書き保存' button (attempt {attempt + 1})")

        # Wait for save to complete
        await asyncio.sleep(3)

        # Check for error message
        error_msg = await page.evaluate(
            """() => {
            const body = document.body.innerText;
            if (body.includes("保存に失敗")) {
                return "保存に失敗しました";
            }
            return null;
        }"""
        )

        if error_msg:
            logger.warning(f"Save attempt {attempt + 1} failed: {error_msg}")
            if attempt < max_retries - 1:
                # Wait before retry
                await asyncio.sleep(2)
                # Dismiss error toast if present by clicking elsewhere
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
                continue
            return False

        logger.debug("Article saved successfully")
        return True

    return False


async def insert_image_via_browser(
    session: Session,
    article_id: str,
    file_path: str,
    caption: str | None = None,
) -> dict[str, Any]:
    """Insert an image into an article via browser automation.

    This function uses Playwright to:
    1. Navigate to the article edit page
    2. Click the add image button
    3. Upload the image file
    4. Add caption if provided
    5. Save the article

    Args:
        session: Authenticated session
        article_id: ID of the article to edit
        file_path: Path to the image file to insert
        caption: Optional caption for the image

    Returns:
        Dictionary with status and details

    Raises:
        NoteAPIError: If image insertion fails
    """
    # Validate file (existence, extension, and size)
    validate_image_file(file_path)
    path = Path(file_path)

    # Setup page
    page = await _setup_page_with_session(session, article_id)

    # Get initial image count before upload
    initial_img_count = await page.evaluate(
        "() => document.querySelectorAll('.ProseMirror figure img, .ProseMirror img').length"
    )
    logger.debug(f"Initial image count: {initial_img_count}")

    # Click add image button
    if not await _click_add_image_button(page):
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message="Failed to click add image button",
            details={"article_id": article_id},
        )

    # Upload image
    if not await _upload_image_via_file_chooser(page, str(path.absolute())):
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message="Failed to upload image via file chooser",
            details={"article_id": article_id, "file_path": file_path},
        )

    # Wait for image to be inserted directly into editor (no modal)
    if not await _wait_for_image_insertion(page, initial_img_count, caption):
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message="Image insertion failed",
            details={"article_id": article_id, "file_path": file_path},
        )

    # Save article
    if not await _save_article(page):
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message="Failed to save article after image insertion",
            details={"article_id": article_id, "file_path": file_path},
        )

    return {
        "success": True,
        "article_id": article_id,
        "file_path": file_path,
        "caption": caption,
    }
