"""ProseMirror editor stabilization helpers for E2E testing.

Provides utilities for reliably interacting with the ProseMirror editor
on note.com, addressing the 6 failure points identified in issue #53:

1. AI dialog dismissal timing
2. ProseMirror editor mount waiting
3. Floating menu visibility
4. Image insertion DOM change detection
5. figcaption focus
6. Save processing timing
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from playwright.async_api import Error as PlaywrightError

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


# Configuration constants
DEFAULT_TIMEOUT_MS = 15000
EDITOR_LOAD_WAIT_MS = 20000
IMAGE_INSERT_TIMEOUT_MS = 10000
SAVE_COMPLETION_TIMEOUT_MS = 5000

# UI element positioning constants
FLOATING_MENU_MIN_Y = 200  # Minimum Y position for floating menu buttons
FLOATING_MENU_MAX_Y = 800  # Maximum Y position for floating menu buttons

# UI text constants
IMAGE_BUTTON_TEXT = "画像"
DRAFT_SAVE_BUTTON_TEXT = "下書き保存"
SAVE_FAILED_TEXT = "保存に失敗"


class ProseMirrorStabilizer:
    """Provides stable interactions with the ProseMirror editor.

    This class addresses the timing-dependent issues when interacting
    with note.com's ProseMirror-based editor.

    Attributes:
        page: Playwright Page instance
    """

    def __init__(self, page: Page) -> None:
        """Initialize stabilizer with a Playwright page.

        Args:
            page: Playwright Page instance to interact with
        """
        self.page = page

    async def dismiss_ai_dialog(self, timeout_ms: int = 5000) -> bool:
        """Dismiss the AI dialog popup if present.

        Issue #53 Point 1: AI dialog can block editor initialization.
        This method waits for and dismisses the "AIと相談" dialog.

        Args:
            timeout_ms: Maximum time to wait for dialog

        Returns:
            True if dialog was dismissed or not present
        """
        try:
            # Check for the AI dialog using multiple detection strategies
            dialog_dismissed = await self.page.evaluate(
                """
                async (timeout) => {
                    const startTime = Date.now();
                    while (Date.now() - startTime < timeout) {
                        // Strategy 1: Look for close button with aria-label
                        const closeButtons = document.querySelectorAll(
                            'button[aria-label="閉じる"], button[aria-label="close"]'
                        );
                        for (const btn of closeButtons) {
                            if (btn.offsetParent !== null) {  // visible check
                                btn.click();
                                return { dismissed: true, strategy: "aria-label" };
                            }
                        }

                        // Strategy 2: Look for dialog with AI text and × button
                        const elements = document.querySelectorAll(
                            '[class*="dialog"], [class*="popup"], [class*="modal"]'
                        );
                        for (const el of elements) {
                            if (el.textContent.includes('AIと相談') && el.offsetParent !== null) {
                                const closeBtn = el.querySelector('button');
                                if (closeBtn) {
                                    closeBtn.click();
                                    return { dismissed: true, strategy: "ai-dialog" };
                                }
                            }
                        }

                        // Strategy 3: Look for standalone × button
                        const allButtons = document.querySelectorAll('button');
                        for (const btn of allButtons) {
                            const text = btn.textContent.trim();
                            if ((text === '×' || text === '✕') && btn.offsetParent !== null) {
                                btn.click();
                                return { dismissed: true, strategy: "x-button" };
                            }
                        }

                        await new Promise(r => setTimeout(r, 200));
                    }
                    return { dismissed: false, strategy: "no-dialog-found" };
                }
                """,
                timeout_ms,
            )

            if dialog_dismissed.get("dismissed"):
                await asyncio.sleep(0.5)  # Wait for animation
                logger.debug(f"AI dialog dismissed via {dialog_dismissed.get('strategy')}")
            return True

        except PlaywrightError as e:
            # Playwright errors (timeouts, element not found) are expected
            logger.debug(f"AI dialog check completed (no dialog found): {e}")
            return True  # No dialog present is a valid state
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.warning(f"Unexpected error during AI dialog dismissal: {type(e).__name__}: {e}")
            return False

    async def wait_for_editor_ready(self, timeout_ms: int = EDITOR_LOAD_WAIT_MS) -> bool:
        """Wait for the ProseMirror editor to be fully ready.

        Issue #53 Point 2: Editor mount timing varies by environment.
        Uses multiple strategies to detect editor readiness.

        Args:
            timeout_ms: Maximum time to wait for editor

        Returns:
            True if editor is ready

        Raises:
            TimeoutError: If editor doesn't become ready within timeout
        """
        try:
            # First wait for the .ProseMirror element to exist
            await self.page.wait_for_selector(
                ".ProseMirror",
                state="visible",
                timeout=timeout_ms,
            )

            # Then verify editor is truly interactive
            is_ready = await self.page.evaluate(
                """
                async (timeout) => {
                    const startTime = Date.now();
                    while (Date.now() - startTime < timeout) {
                        const editor = document.querySelector('.ProseMirror');
                        if (editor &&
                            editor.offsetParent !== null &&
                            editor.contentEditable === 'true') {
                            // Additional check: editor should be focusable
                            editor.focus();
                            if (document.activeElement === editor ||
                                document.activeElement?.closest('.ProseMirror')) {
                                return true;
                            }
                        }
                        await new Promise(r => setTimeout(r, 100));
                    }
                    return false;
                }
                """,
                min(timeout_ms, 5000),  # Secondary check timeout
            )

            if not is_ready:
                raise TimeoutError("Editor element found but not interactive")

            logger.debug("ProseMirror editor is ready")
            return True

        except Exception as e:
            logger.error(f"Editor readiness wait failed: {e}")
            raise TimeoutError(f"Editor not ready within {timeout_ms}ms: {e}") from e

    async def show_floating_menu(self, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> bool:
        """Trigger and wait for the floating menu to appear.

        Issue #53 Point 3: Menu may not be visible initially.
        Clicks editor to trigger menu and waits for "画像" button.

        Args:
            timeout_ms: Maximum time to wait for menu

        Returns:
            True if menu is visible with image button
        """
        try:
            # Click editor to focus and potentially trigger menu
            editor = self.page.locator(".ProseMirror").first
            await editor.click()
            await asyncio.sleep(0.3)

            # Wait for image button to appear using shared search logic
            menu_ready = await self.page.evaluate(
                """
                async (args) => {
                    const { buttonText, minY, maxY, timeout } = args;
                    const startTime = Date.now();
                    while (Date.now() - startTime < timeout) {
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            if (btn.textContent.trim() === buttonText &&
                                btn.offsetParent !== null) {
                                const rect = btn.getBoundingClientRect();
                                if (rect.y > minY && rect.y < maxY) {
                                    return { found: true, y: rect.y };
                                }
                            }
                        }
                        await new Promise(r => setTimeout(r, 100));
                    }
                    return { found: false };
                }
                """,
                {
                    "buttonText": IMAGE_BUTTON_TEXT,
                    "minY": FLOATING_MENU_MIN_Y,
                    "maxY": FLOATING_MENU_MAX_Y,
                    "timeout": timeout_ms,
                },
            )

            if menu_ready.get("found"):
                logger.debug(f"Floating menu visible at y={menu_ready.get('y')}")
                return True

            logger.warning("Floating menu not found")
            return False

        except PlaywrightError as e:
            logger.error(f"Playwright error during floating menu wait: {e}")
            return False
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.warning(f"Unexpected error during floating menu wait: {type(e).__name__}: {e}")
            return False

    async def click_image_button(self) -> bool:
        """Click the "画像" (image) button in the floating menu.

        Returns:
            True if button was clicked successfully
        """
        clicked = await self.page.evaluate(
            """
            (args) => {
                const { buttonText, minY, maxY } = args;
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.textContent.trim() === buttonText &&
                        btn.offsetParent !== null) {
                        const rect = btn.getBoundingClientRect();
                        if (rect.y > minY && rect.y < maxY) {
                            btn.click();
                            return true;
                        }
                    }
                }
                return false;
            }
            """,
            {
                "buttonText": IMAGE_BUTTON_TEXT,
                "minY": FLOATING_MENU_MIN_Y,
                "maxY": FLOATING_MENU_MAX_Y,
            },
        )

        if clicked:
            await asyncio.sleep(0.3)  # Wait for file chooser activation
            logger.debug(f"Clicked '{IMAGE_BUTTON_TEXT}' button")
        return bool(clicked)

    async def wait_for_image_insertion(
        self,
        initial_count: int,
        timeout_ms: int = IMAGE_INSERT_TIMEOUT_MS,
    ) -> bool:
        """Wait for image to be inserted into the editor.

        Issue #53 Point 4: DOM change detection for image insertion.
        Uses polling with MutationObserver-like approach.

        Args:
            initial_count: Number of images before upload started
            timeout_ms: Maximum time to wait for insertion

        Returns:
            True if a new image was detected
        """
        try:
            inserted = await self.page.evaluate(
                """
                async (args) => {
                    const { initialCount, timeout } = args;
                    const startTime = Date.now();

                    while (Date.now() - startTime < timeout) {
                        // Check for images in ProseMirror
                        const images = document.querySelectorAll(
                            '.ProseMirror figure img, .ProseMirror img'
                        );
                        if (images.length > initialCount) {
                            // Verify image is fully loaded
                            const lastImg = images[images.length - 1];
                            if (lastImg.complete && lastImg.naturalHeight > 0) {
                                return { inserted: true, count: images.length };
                            }
                        }
                        await new Promise(r => setTimeout(r, 200));
                    }
                    return { inserted: false, count: 0 };
                }
                """,
                {"initialCount": initial_count, "timeout": timeout_ms},
            )

            if inserted.get("inserted"):
                logger.debug(f"Image inserted, total count: {inserted.get('count')}")
                return True

            logger.warning("Image insertion not detected within timeout")
            return False

        except PlaywrightError as e:
            logger.error(f"Playwright error during image insertion wait: {e}")
            return False
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.warning(f"Unexpected error during image insertion wait: {type(e).__name__}: {e}")
            return False

    async def focus_figcaption(self, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> bool:
        """Focus on the figcaption element for the most recent image.

        Issue #53 Point 5: Figcaption focus after image insertion.
        Waits for figcaption to be available and focuses it.

        Args:
            timeout_ms: Maximum time to wait for figcaption

        Returns:
            True if figcaption was focused successfully
        """
        try:
            focused = await self.page.evaluate(
                """
                async (timeout) => {
                    const startTime = Date.now();

                    while (Date.now() - startTime < timeout) {
                        const figcaptions = document.querySelectorAll(
                            '.ProseMirror figure figcaption'
                        );
                        if (figcaptions.length > 0) {
                            const lastFigcaption = figcaptions[figcaptions.length - 1];
                            if (lastFigcaption.offsetParent !== null) {
                                lastFigcaption.click();
                                lastFigcaption.focus();
                                // Verify focus
                                await new Promise(r => setTimeout(r, 100));
                                const active = document.activeElement;
                                if (active === lastFigcaption ||
                                    lastFigcaption.contains(active)) {
                                    return { focused: true };
                                }
                            }
                        }
                        await new Promise(r => setTimeout(r, 100));
                    }
                    return { focused: false };
                }
                """,
                timeout_ms,
            )

            if focused.get("focused"):
                logger.debug("Figcaption focused successfully")
                return True

            logger.warning("Could not focus figcaption")
            return False

        except PlaywrightError as e:
            logger.error(f"Playwright error during figcaption focus: {e}")
            return False
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.warning(f"Unexpected error during figcaption focus: {type(e).__name__}: {e}")
            return False

    async def type_caption(self, caption: str) -> bool:
        """Type caption text into the focused figcaption.

        Args:
            caption: Caption text to type

        Returns:
            True if caption was typed successfully
        """
        if not caption:
            return True

        try:
            await self.page.keyboard.type(caption)
            await asyncio.sleep(0.2)  # Wait for text to be processed
            logger.debug(f"Typed caption: {caption}")
            return True
        except PlaywrightError as e:
            logger.error(f"Playwright error during caption typing: {e}")
            return False
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.warning(f"Unexpected error during caption typing: {type(e).__name__}: {e}")
            return False

    async def save_article(
        self,
        timeout_ms: int = SAVE_COMPLETION_TIMEOUT_MS,
        max_retries: int = 3,
    ) -> bool:
        """Save the article and wait for completion.

        Issue #53 Point 6: Save completion timing.
        Uses multiple indicators to detect save completion.

        Args:
            timeout_ms: Maximum time to wait for save per attempt
            max_retries: Number of retry attempts

        Returns:
            True if save was successful
        """
        for attempt in range(max_retries):
            try:
                # Click save button using constants
                save_clicked = await self.page.evaluate(
                    """
                    (buttonText) => {
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            if (btn.textContent.trim() === buttonText &&
                                btn.offsetParent !== null &&
                                !btn.disabled) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }
                    """,
                    DRAFT_SAVE_BUTTON_TEXT,
                )

                if not save_clicked:
                    logger.warning(f"Save button not found (attempt {attempt + 1})")
                    continue

                logger.debug(f"Clicked save button (attempt {attempt + 1})")

                # Wait for save to complete - check for various indicators
                save_result = await self.page.evaluate(
                    """
                    async (args) => {
                        const { timeout, buttonText, errorText } = args;
                        const startTime = Date.now();

                        while (Date.now() - startTime < timeout) {
                            // Check for error messages
                            const body = document.body.innerText;
                            if (body.includes(errorText)) {
                                return { success: false, error: errorText };
                            }

                            // Check for success indicators (button state change, toast)
                            const saveBtn = Array.from(document.querySelectorAll('button'))
                                .find(b => b.textContent.trim() === buttonText);

                            // If button is not disabled and no error, assume success
                            if (saveBtn && !saveBtn.disabled) {
                                // Wait a bit more to ensure save is processed
                                await new Promise(r => setTimeout(r, 500));
                                // Recheck for error
                                if (!document.body.innerText.includes(errorText)) {
                                    return { success: true };
                                }
                            }

                            await new Promise(r => setTimeout(r, 200));
                        }

                        // Timeout reached - check final state
                        if (!document.body.innerText.includes(errorText)) {
                            return { success: true };
                        }
                        return { success: false, error: 'timeout' };
                    }
                    """,
                    {
                        "timeout": timeout_ms,
                        "buttonText": DRAFT_SAVE_BUTTON_TEXT,
                        "errorText": SAVE_FAILED_TEXT,
                    },
                )

                if save_result.get("success"):
                    logger.debug("Article saved successfully")
                    return True

                error = save_result.get("error", "unknown")
                logger.warning(f"Save attempt {attempt + 1} failed: {error}")

                if attempt < max_retries - 1:
                    # Dismiss error toast and retry
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(1)

            except PlaywrightError as e:
                # Playwright errors are retryable
                logger.warning(f"Playwright error on save attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                # Unexpected errors - log and continue to next attempt
                logger.error(f"Unexpected error on save attempt {attempt + 1}: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

        return False

    async def get_image_count(self) -> int:
        """Get the current number of images in the editor.

        Returns:
            Number of images in the ProseMirror editor
        """
        count = await self.page.evaluate(
            """
            () => document.querySelectorAll(
                '.ProseMirror figure img, .ProseMirror img'
            ).length
            """
        )
        return int(count)
