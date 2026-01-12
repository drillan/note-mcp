"""Image insertion helpers for note.com editor.

This module provides functions to insert images at placeholder positions
in the note.com ProseMirror editor.

Workflow:
1. typing_helpers.py detects image patterns ![alt](url) and inserts placeholders
   (§§IMAGE:alt||url§§)
2. This module finds all placeholders and replaces them with actual images
3. For local files: uses browser automation to upload via note.com's UI
4. For URLs: downloads first, then uploads via browser automation

Note: note.com does not support direct URL image embedding.
All images must be uploaded to note.com's servers.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# note.com editor selectors
_EDITOR_SELECTOR = ".ProseMirror"

# Placeholder markers (must match typing_helpers.py)
_IMAGE_PLACEHOLDER_START = "§§IMAGE:"
_IMAGE_PLACEHOLDER_SEPARATOR = "||"
_IMAGE_PLACEHOLDER_END = "§§"

# Regex to find image placeholders: §§IMAGE:alt||url§§
_IMAGE_PLACEHOLDER_PATTERN = re.compile(r"§§IMAGE:(.+?)\|\|(.+?)§§")

# Supported image extensions for download
_SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Maximum file size for downloaded images (10MB)
_MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024


async def has_image_placeholders(page: Page) -> bool:
    """Check if editor contains any image placeholders.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        True if any image placeholder exists in editor.
    """
    editor = page.locator(_EDITOR_SELECTOR)
    text = await editor.text_content()
    logger.debug(f"Editor text content (first 500 chars): {text[:500] if text else 'None'}")
    has_placeholder = text is not None and _IMAGE_PLACEHOLDER_START in text
    logger.info(f"has_image_placeholders: {has_placeholder}, text length: {len(text) if text else 0}")
    return has_placeholder


async def apply_images(page: Page, timeout: int = 30000) -> tuple[int, str]:
    """Insert images at all placeholder positions in editor.

    Finds image placeholders one at a time (re-searching after each insertion)
    and uses browser automation to insert actual images via note.com's UI.

    Note: We must re-search for placeholders after each image insertion because
    the DOM is reconstructed when an image is inserted, invalidating any
    previously cached placeholder locations.

    Args:
        page: Playwright page with note.com editor.
        timeout: Maximum wait time in milliseconds per image.

    Returns:
        Tuple of (number of images successfully inserted, debug info string).
    """
    debug_steps: list[str] = []
    logger.info("apply_images() called - checking for image placeholders...")
    debug_steps.append("apply_images() started")

    has_placeholders = await has_image_placeholders(page)
    logger.info(f"has_image_placeholders returned: {has_placeholders}")
    debug_steps.append(f"has_placeholders={has_placeholders}")

    if not has_placeholders:
        logger.info("No image placeholders found in editor - returning 0")
        debug_steps.append("No placeholders found - returning 0")
        return 0, " → ".join(debug_steps)

    applied_count = 0
    max_iterations = 20  # Safety limit to prevent infinite loops

    for iteration in range(max_iterations):
        logger.info(f"apply_images iteration {iteration + 1}/{max_iterations}")
        debug_steps.append(f"iter{iteration + 1}")

        # Re-search for placeholders after each image insertion
        # because DOM changes after image is inserted
        placeholders = await _find_image_placeholders(page)
        logger.info(f"_find_image_placeholders returned: {len(placeholders)} placeholders")
        debug_steps.append(f"found={len(placeholders)}")

        if not placeholders:
            logger.info("No more image placeholders found in DOM - breaking loop")
            debug_steps.append("no_placeholders_break")
            break

        # Process only the first placeholder found
        alt_text, image_path = placeholders[0]
        logger.info(f"Processing image {applied_count + 1}: alt={alt_text[:20]}..., path={image_path[:30]}...")
        debug_steps.append(f"processing:{alt_text[:15]}...")

        try:
            success, insert_debug = await _insert_single_image(page, alt_text, image_path, timeout)
            debug_steps.append(f"insert:{insert_debug}")

            if success:
                applied_count += 1
                logger.info(f"Successfully inserted image: {alt_text}")
                debug_steps.append("SUCCESS")
            else:
                logger.warning(f"Failed to insert image: {alt_text}")
                debug_steps.append("FAILED")
                # Remove placeholder to avoid infinite loop
                await _remove_placeholder_text(page, alt_text, image_path)

        except Exception as e:
            logger.warning(f"Error inserting image {alt_text}: {e}")
            debug_steps.append(f"ERROR:{type(e).__name__}:{str(e)[:50]}")
            # Remove problematic placeholder to avoid infinite loop
            await _remove_placeholder_text(page, alt_text, image_path)

    logger.info(f"Inserted {applied_count} image(s)")
    debug_steps.append(f"TOTAL:{applied_count}")
    return applied_count, " → ".join(debug_steps)


async def _find_image_placeholders(page: Page) -> list[tuple[str, str]]:
    """Find all image placeholder alt/path pairs in the editor.

    Args:
        page: Playwright page with note.com editor.

    Returns:
        List of (alt_text, image_path) tuples from image placeholders.
    """
    result = await page.evaluate(
        f"""
        () => {{
            const editor = document.querySelector('{_EDITOR_SELECTOR}');
            if (!editor) return {{"items": [], "text": "Editor not found"}};

            const text = editor.textContent || '';
            const pattern = /§§IMAGE:(.+?)\\|\\|(.+?)§§/g;
            const items = [];

            let match;
            while ((match = pattern.exec(text)) !== null) {{
                items.push({{alt: match[1], path: match[2]}});
            }}
            return {{"items": items, "text": text.substring(0, 500)}};
        }}
        """
    )
    items = result.get("items", []) if result else []
    text_preview = (result.get("text", "") if result else "")[:200]
    logger.info(f"_find_image_placeholders result: items={len(items)}, text preview={text_preview}")

    return [(item["alt"], item["path"]) for item in items]


async def _insert_single_image(page: Page, alt_text: str, image_path: str, timeout: int) -> tuple[bool, str]:
    """Insert a single image at its placeholder position.

    Args:
        page: Playwright page with note.com editor.
        alt_text: Alt text for the image.
        image_path: Path or URL to the image.
        timeout: Maximum wait time in milliseconds.

    Returns:
        Tuple of (success boolean, debug info string).
    """
    placeholder = (
        f"{_IMAGE_PLACEHOLDER_START}{alt_text}{_IMAGE_PLACEHOLDER_SEPARATOR}{image_path}{_IMAGE_PLACEHOLDER_END}"
    )
    debug_steps: list[str] = []

    # 1. Determine if path is URL or local file
    is_url = image_path.startswith("http://") or image_path.startswith("https://")
    debug_steps.append(f"is_url={is_url}")

    # 2. Get local file path (download if URL)
    local_path: Path | None = None
    temp_file: str | None = None

    if is_url:
        # Download image to temp file
        try:
            temp_file, download_debug = await _download_image(image_path)
            debug_steps.append(f"download:{download_debug}")
            if temp_file:
                local_path = Path(temp_file)
            else:
                debug_steps.append("download_failed")
                return False, "→".join(debug_steps)
        except Exception as e:
            debug_steps.append(f"download_error:{type(e).__name__}")
            return False, "→".join(debug_steps)
    else:
        # Use local file directly
        local_path = Path(image_path)
        if not local_path.exists():
            debug_steps.append("file_not_found")
            return False, "→".join(debug_steps)

    try:
        # 3. Find and select the placeholder
        select_result = await _select_placeholder(page, placeholder)
        debug_steps.append(f"select={select_result}")
        if not select_result:
            return False, "→".join(debug_steps)

        # 4. Delete the selected placeholder
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.2)
        debug_steps.append("deleted")

        # 5. Get initial image count
        initial_img_count = await page.evaluate(
            "() => document.querySelectorAll('.ProseMirror figure img, .ProseMirror img').length"
        )
        debug_steps.append(f"init_count={initial_img_count}")

        # 6. Click the add image button
        if not await _click_add_image_button(page):
            debug_steps.append("button_failed")
            return False, "→".join(debug_steps)
        debug_steps.append("button_clicked")

        # 7. Upload the image file
        if not await _upload_image_file(page, str(local_path.absolute())):
            debug_steps.append("upload_failed")
            return False, "→".join(debug_steps)
        debug_steps.append("uploaded")

        # 8. Wait for image to appear in editor
        if not await _wait_for_image_insertion(page, initial_img_count, alt_text, timeout):
            debug_steps.append("wait_timeout")
            return False, "→".join(debug_steps)
        debug_steps.append("inserted")

        return True, "→".join(debug_steps)

    finally:
        # Cleanup temp file if downloaded
        if temp_file:
            with contextlib.suppress(Exception):
                Path(temp_file).unlink(missing_ok=True)


async def _download_image(url: str) -> tuple[str | None, str]:
    """Download image from URL to a temporary file.

    Args:
        url: URL of the image to download.

    Returns:
        Tuple of (temp file path or None, debug info string).
    """
    debug_steps: list[str] = []

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            debug_steps.append(f"status={response.status_code}")

            if response.status_code != 200:
                return None, "→".join(debug_steps)

            # Check content length
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > _MAX_DOWNLOAD_SIZE:
                debug_steps.append("too_large")
                return None, "→".join(debug_steps)

            # Determine file extension from URL or content-type
            ext = _get_image_extension(url, response.headers.get("content-type", ""))
            if ext not in _SUPPORTED_EXTENSIONS:
                debug_steps.append(f"unsupported_ext={ext}")
                return None, "→".join(debug_steps)

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(response.content)
                temp_path = f.name

            debug_steps.append(f"saved={Path(temp_path).name}")
            return temp_path, "→".join(debug_steps)

    except Exception as e:
        debug_steps.append(f"error:{type(e).__name__}")
        return None, "→".join(debug_steps)


def _get_image_extension(url: str, content_type: str) -> str:
    """Get image file extension from URL or content-type.

    Args:
        url: URL of the image.
        content_type: Content-Type header value.

    Returns:
        File extension including dot (e.g., ".jpg").
    """
    # Try to get from URL path
    url_path = url.split("?")[0]  # Remove query string
    for ext in _SUPPORTED_EXTENSIONS:
        if url_path.lower().endswith(ext):
            return ext

    # Try to get from content-type
    content_type_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    for ct, ext in content_type_map.items():
        if ct in content_type.lower():
            return ext

    # Default to .jpg
    return ".jpg"


async def _select_placeholder(page: Page, placeholder: str) -> bool:
    """Select the placeholder text in the editor.

    Uses JavaScript to find the placeholder text node and select it.

    Args:
        page: Playwright page with note.com editor.
        placeholder: Full placeholder string to find and select.

    Returns:
        True if placeholder was found and selected.
    """
    result = await page.evaluate(
        f"""
        (placeholder) => {{
            const editor = document.querySelector('{_EDITOR_SELECTOR}');
            if (!editor) {{
                return {{ success: false, error: 'Editor element not found' }};
            }}

            const walker = document.createTreeWalker(
                editor,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            let node;
            while (node = walker.nextNode()) {{
                if (node.nodeValue && node.nodeValue.includes(placeholder)) {{
                    // Select the placeholder text
                    const range = document.createRange();
                    const startOffset = node.nodeValue.indexOf(placeholder);
                    const endOffset = startOffset + placeholder.length;
                    range.setStart(node, startOffset);
                    range.setEnd(node, endOffset);

                    const selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    return {{ success: true }};
                }}
            }}
            return {{ success: false, error: 'Placeholder not found in text nodes' }};
        }}
        """,
        placeholder,
    )
    await asyncio.sleep(0.1)

    if not result.get("success"):
        logger.warning(f"Failed to select placeholder: {result.get('error')}")
        return False
    return True


async def _click_add_image_button(page: Page) -> bool:
    """Click the add image button in the editor.

    note.com editor shows a floating menu with options like "画像", "音声", etc.
    The menu may already be visible on page load, or may appear after clicking
    on the editor.

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


async def _upload_image_file(page: Page, file_path: str) -> bool:
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


async def _wait_for_image_insertion(page: Page, initial_img_count: int, alt_text: str, timeout: int = 10000) -> bool:
    """Wait for image to be inserted and optionally add caption.

    note.com inserts images directly into the editor after file upload.
    This function waits for the image count to increase, then adds alt text
    to the figcaption element if provided.

    Args:
        page: Playwright Page instance
        initial_img_count: Number of images before upload
        alt_text: Alt text to use as caption (optional)
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

        # Enter alt text as caption if provided
        if alt_text:
            await _input_image_caption(page, alt_text)

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


async def _remove_placeholder_text(page: Page, alt_text: str, image_path: str) -> None:
    """Remove a placeholder from the editor when image insertion fails.

    This prevents infinite loops when a particular image cannot be processed.
    Falls back to displaying the alt text as plain text.

    Args:
        page: Playwright page with note.com editor.
        alt_text: Alt text of the placeholder.
        image_path: Path/URL of the placeholder.
    """
    placeholder = (
        f"{_IMAGE_PLACEHOLDER_START}{alt_text}{_IMAGE_PLACEHOLDER_SEPARATOR}{image_path}{_IMAGE_PLACEHOLDER_END}"
    )

    try:
        if await _select_placeholder(page, placeholder):
            # Delete the selected placeholder
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)
            # Type the alt text as fallback (or URL if no alt text)
            fallback_text = alt_text if alt_text else image_path
            await page.keyboard.type(f"[画像: {fallback_text}]")
            await asyncio.sleep(0.1)
            logger.info(f"Replaced failed image placeholder with text: {fallback_text}")
    except Exception as e:
        logger.warning(f"Could not remove placeholder for {alt_text}: {e}")
