"""UI経由でリンクを挿入するモジュール。

note.comのProseMirrorエディタはMarkdown記法 [text](url) を
自動変換しない（InputRule未実装）。このモジュールは
UI自動化でリンク挿入を実現する。

UI操作フロー:
    1. テキストを入力
    2. テキストを選択（Shift+ArrowLeft × 文字数）
    3. リンクダイアログを開く（Ctrl+K）
    4. URL入力フィールドを待機
    5. URLを入力
    6. 適用（Enter）
    7. リンク挿入を検証
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import TYPE_CHECKING

from playwright.async_api import Error as PlaywrightError

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class LinkResult(Enum):
    """リンク挿入の結果タイプ。

    リンクを挿入しようとした場合、以下の2つの結果があり得る:
    - SUCCESS: リンクが正常に挿入された
    - TIMEOUT: タイムアウト（予期しない失敗）
    """

    SUCCESS = "success"  # リンク挿入成功
    TIMEOUT = "timeout"  # タイムアウト（予期しない失敗）


# note.com editor selectors
_EDITOR_SELECTOR = ".ProseMirror"
_LINK_URL_INPUT_SELECTOR = 'textarea[placeholder="https://"]'

# Timing constants
_CLICK_WAIT_SECONDS = 0.3
_INPUT_WAIT_SECONDS = 0.2
_LINK_WAIT_TIMEOUT_MS = 5000


async def insert_link_at_cursor(
    page: Page,
    text: str,
    url: str,
    timeout: int = _LINK_WAIT_TIMEOUT_MS,
) -> tuple[LinkResult, str]:
    """現在のカーソル位置にリンクを挿入する。

    この関数はnote.comエディタのリンクダイアログを使用する:
    1. テキストを入力
    2. テキストを選択（Shift+Left × 文字数）
    3. リンクダイアログを開く（Ctrl+K）
    4. URL入力フィールドにURLを入力
    5. Enterで適用
    6. リンク挿入を検証

    Args:
        page: Playwright page with note.com editor.
        text: リンクテキスト.
        url: リンク先URL.
        timeout: タイムアウト（ミリ秒）.

    Returns:
        Tuple of (LinkResult, debug_info).
        - LinkResult.SUCCESS: リンクが正常に挿入された
        - LinkResult.TIMEOUT: タイムアウト

    Raises:
        ValueError: テキストまたはURLが空の場合.
    """
    debug_steps: list[str] = []

    # Validate inputs
    if not text:
        raise ValueError("text cannot be empty")
    if not url:
        raise ValueError("url cannot be empty")

    logger.info(f"Inserting link: {text} -> {url}")
    debug_steps.append(f"text={text[:20]}")

    # Step 1: Click editor to ensure focus
    logger.info("Step 1: Ensuring editor focus...")
    success, reason = await _ensure_editor_focus(page)
    if not success:
        logger.error(f"Step 1 FAILED: Could not focus editor ({reason})")
        debug_steps.append(f"S1:FAIL:{reason}")
        return LinkResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S1:OK")

    # Step 2: Type the link text
    logger.info(f"Step 2: Typing text: {text}")
    success, reason = await _type_text(page, text)
    if not success:
        logger.error(f"Step 2 FAILED: Could not type text ({reason})")
        debug_steps.append(f"S2:FAIL:{reason}")
        return LinkResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S2:OK")

    # Step 3: Select the typed text
    logger.info("Step 3: Selecting text...")
    success, reason = await _select_text(page, text)
    if not success:
        logger.error(f"Step 3 FAILED: Could not select text ({reason})")
        debug_steps.append(f"S3:FAIL:{reason}")
        return LinkResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S3:OK")

    # Step 4: Open link dialog with Ctrl+K
    logger.info("Step 4: Opening link dialog...")
    success, reason = await _open_link_dialog(page, timeout)
    if not success:
        logger.error(f"Step 4 FAILED: Could not open link dialog ({reason})")
        debug_steps.append(f"S4:FAIL:{reason}")
        return LinkResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S4:OK")

    # Step 5: Enter URL
    logger.info(f"Step 5: Entering URL: {url}")
    success, reason = await _enter_url(page, url)
    if not success:
        logger.error(f"Step 5 FAILED: Could not enter URL ({reason})")
        debug_steps.append(f"S5:FAIL:{reason}")
        return LinkResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S5:OK")

    # Step 6: Apply link (press Enter)
    logger.info("Step 6: Applying link...")
    success, reason = await _apply_link(page)
    if not success:
        logger.error(f"Step 6 FAILED: Could not apply link ({reason})")
        debug_steps.append(f"S6:FAIL:{reason}")
        return LinkResult.TIMEOUT, "|".join(debug_steps)
    debug_steps.append("S6:OK")

    # Step 7: Verify link was inserted
    logger.info("Step 7: Verifying link insertion...")
    result = await _verify_link_insertion(page, text, url, timeout)
    debug_steps.append(f"S7:{result.value}")

    if result == LinkResult.SUCCESS:
        logger.info(f"Successfully inserted link: {text} -> {url}")
    else:
        logger.error("Step 7 FAILED: Link not detected within timeout")

    return result, "|".join(debug_steps)


async def _ensure_editor_focus(page: Page) -> tuple[bool, str]:
    """エディタにフォーカスを確保する。

    Args:
        page: Playwright page with note.com editor.

    Returns:
        Tuple of (success, reason) where reason explains failure.
    """
    try:
        editor = page.locator(_EDITOR_SELECTOR).first
        if await editor.count() > 0:
            await editor.click()
            await asyncio.sleep(_CLICK_WAIT_SECONDS)
            logger.debug("Clicked editor to focus")
            return True, ""

        logger.warning("Editor not found")
        return False, "editor_not_found"

    except asyncio.CancelledError:
        raise
    except PlaywrightError as e:
        logger.warning(f"Playwright error focusing editor: {type(e).__name__}: {e}")
        return False, f"playwright_error:{type(e).__name__}"
    except Exception as e:
        logger.warning(f"Error focusing editor: {type(e).__name__}: {e}")
        return False, f"unexpected_error:{type(e).__name__}"


async def _type_text(page: Page, text: str) -> tuple[bool, str]:
    """テキストを入力する。

    Args:
        page: Playwright page with note.com editor.
        text: 入力するテキスト.

    Returns:
        Tuple of (success, reason) where reason explains failure.
    """
    try:
        await page.keyboard.type(text)
        await asyncio.sleep(_INPUT_WAIT_SECONDS)
        logger.debug(f"Typed text: {text}")
        return True, ""

    except asyncio.CancelledError:
        raise
    except PlaywrightError as e:
        logger.warning(f"Playwright error typing text: {type(e).__name__}: {e}")
        return False, f"playwright_error:{type(e).__name__}"
    except Exception as e:
        logger.warning(f"Error typing text: {type(e).__name__}: {e}")
        return False, f"unexpected_error:{type(e).__name__}"


async def _select_text(page: Page, text: str) -> tuple[bool, str]:
    """入力したテキストを選択する。

    Shift+Leftを文字数分繰り返してテキストを選択する。

    Args:
        page: Playwright page with note.com editor.
        text: 選択するテキスト（文字数計算用）.

    Returns:
        Tuple of (success, reason) where reason explains failure.
    """
    try:
        # 日本語文字の場合、文字数分だけShift+ArrowLeftを実行
        # 英語の場合は単語単位で選択されるが、日本語は文字単位
        # Note: Playwrightでは "Left" ではなく "ArrowLeft" を使用
        char_count = len(text)
        for _ in range(char_count):
            await page.keyboard.press("Shift+ArrowLeft")
            await asyncio.sleep(0.05)

        await asyncio.sleep(_INPUT_WAIT_SECONDS)
        logger.debug(f"Selected text ({char_count} chars)")
        return True, ""

    except asyncio.CancelledError:
        raise
    except PlaywrightError as e:
        logger.warning(f"Playwright error selecting text: {type(e).__name__}: {e}")
        return False, f"playwright_error:{type(e).__name__}"
    except Exception as e:
        logger.warning(f"Error selecting text: {type(e).__name__}: {e}")
        return False, f"unexpected_error:{type(e).__name__}"


async def _open_link_dialog(page: Page, timeout: int) -> tuple[bool, str]:
    """リンクダイアログを開く（Ctrl+K）。

    Args:
        page: Playwright page with note.com editor.
        timeout: タイムアウト（ミリ秒）.

    Returns:
        Tuple of (success, reason) where reason explains failure.
    """
    try:
        # Press Ctrl+K to open link dialog
        await page.keyboard.press("Control+k")
        await asyncio.sleep(_CLICK_WAIT_SECONDS)

        # Wait for URL input field to appear
        url_input = page.locator(_LINK_URL_INPUT_SELECTOR).first
        await url_input.wait_for(state="visible", timeout=timeout)

        logger.debug("Link dialog opened")
        return True, ""

    except asyncio.CancelledError:
        raise
    except PlaywrightError as e:
        logger.warning(f"Timeout waiting for link dialog: {type(e).__name__}: {e}")
        return False, f"dialog_timeout:{type(e).__name__}"
    except Exception as e:
        logger.warning(f"Error opening link dialog: {type(e).__name__}: {e}")
        return False, f"unexpected_error:{type(e).__name__}"


async def _enter_url(page: Page, url: str) -> tuple[bool, str]:
    """URL入力フィールドにURLを入力する。

    Args:
        page: Playwright page with note.com editor.
        url: 入力するURL.

    Returns:
        Tuple of (success, reason) where reason explains failure.
    """
    try:
        url_input = page.locator(_LINK_URL_INPUT_SELECTOR).first
        if await url_input.count() > 0:
            await url_input.fill(url)
            await asyncio.sleep(_INPUT_WAIT_SECONDS)
            logger.debug(f"Entered URL: {url}")
            return True, ""

        logger.warning("URL input field not found")
        return False, "url_input_not_found"

    except asyncio.CancelledError:
        raise
    except PlaywrightError as e:
        logger.warning(f"Playwright error entering URL: {type(e).__name__}: {e}")
        return False, f"playwright_error:{type(e).__name__}"
    except Exception as e:
        logger.warning(f"Error entering URL: {type(e).__name__}: {e}")
        return False, f"unexpected_error:{type(e).__name__}"


async def _apply_link(page: Page) -> tuple[bool, str]:
    """リンクを適用する（Enterキー）。

    Args:
        page: Playwright page with note.com editor.

    Returns:
        Tuple of (success, reason) where reason explains failure.
    """
    try:
        await page.keyboard.press("Enter")
        await asyncio.sleep(_CLICK_WAIT_SECONDS)
        logger.debug("Applied link with Enter key")
        return True, ""

    except asyncio.CancelledError:
        raise
    except PlaywrightError as e:
        logger.warning(f"Playwright error applying link: {type(e).__name__}: {e}")
        return False, f"playwright_error:{type(e).__name__}"
    except Exception as e:
        logger.warning(f"Error applying link: {type(e).__name__}: {e}")
        return False, f"unexpected_error:{type(e).__name__}"


async def _verify_link_insertion(
    page: Page,
    text: str,
    url: str,
    timeout: int,
) -> LinkResult:
    """リンクが正しく挿入されたか検証する。

    エディタ内に指定したhrefを持つリンクが存在するか確認する。
    相対URLの絶対URL解決やURL正規化（末尾スラッシュ等）を考慮した
    柔軟なマッチングを行う。

    Args:
        page: Playwright page with note.com editor.
        text: リンクテキスト.
        url: リンクURL.
        timeout: タイムアウト（ミリ秒）.

    Returns:
        LinkResult indicating success or timeout.
    """
    try:
        # Wait for link to appear in editor
        result = await page.evaluate(
            r"""
            async (args) => {
                const { url, text, timeout } = args;
                const startTime = Date.now();

                const editor = document.querySelector('.ProseMirror');
                if (!editor) {
                    return { type: 'timeout', reason: 'editor_not_found' };
                }

                // Normalize URL for comparison (remove trailing slash, lowercase)
                const normalizeUrl = (u) => {
                    if (!u) return '';
                    // Remove trailing slash for comparison
                    let normalized = u.replace(/\/$/, '');
                    return normalized.toLowerCase();
                };

                // Extract filename from URL for relative URL matching
                const getFilename = (u) => {
                    if (!u) return '';
                    // Get the last path segment
                    const parts = u.split('/');
                    return parts[parts.length - 1] || parts[parts.length - 2] || '';
                };

                const targetUrl = normalizeUrl(url);
                const targetFilename = getFilename(url);
                const targetText = text.toLowerCase();

                // Check for link with matching href or text
                const findLink = () => {
                    const links = editor.querySelectorAll('a');
                    for (const link of links) {
                        const href = link.getAttribute('href') || '';
                        const resolvedHref = link.href || '';
                        const linkText = (link.textContent || '').toLowerCase();

                        // Exact match on href attribute
                        if (href === url) {
                            return { matched: true, method: 'exact_href' };
                        }

                        // Normalized URL comparison
                        if (normalizeUrl(href) === targetUrl ||
                            normalizeUrl(resolvedHref) === targetUrl) {
                            return { matched: true, method: 'normalized_url' };
                        }

                        // For relative URLs: check if resolved URL ends with target path
                        // e.g., "./images/sample.png" matches "https://note.com/.../images/sample.png"
                        if (url.startsWith('./') || url.startsWith('../')) {
                            const targetPath = url.replace(/^\.+\//, '');
                            if (resolvedHref.endsWith(targetPath) ||
                                resolvedHref.includes('/' + targetPath)) {
                                return { matched: true, method: 'relative_path' };
                            }
                        }

                        // Filename matching as fallback for relative URLs
                        if (targetFilename && getFilename(resolvedHref) === targetFilename) {
                            // Also verify link text matches to avoid false positives
                            if (linkText.includes(targetText) || targetText.includes(linkText)) {
                                return { matched: true, method: 'filename_and_text' };
                            }
                        }

                        // Text content matching as final fallback
                        if (linkText === targetText) {
                            return { matched: true, method: 'text_only' };
                        }
                    }
                    return { matched: false };
                };

                while (Date.now() - startTime < timeout) {
                    const found = findLink();
                    if (found.matched) {
                        return { type: 'success', method: found.method };
                    }
                    await new Promise(r => setTimeout(r, 100));
                }
                return { type: 'timeout', reason: 'link_not_found' };
            }
            """,
            {"url": url, "text": text, "timeout": timeout},
        )

        result_type = result.get("type", "timeout") if result else "timeout"

        if result_type == "success":
            method = result.get("method", "unknown") if result else "unknown"
            logger.debug(f"Link verified: {url} (method: {method})")
            return LinkResult.SUCCESS
        else:
            reason = result.get("reason", "unknown") if result else "unknown"
            logger.warning(f"Link not found within timeout: {reason}")
            return LinkResult.TIMEOUT

    except PlaywrightError as e:
        logger.warning(f"Playwright error verifying link: {type(e).__name__}: {e}")
        return LinkResult.TIMEOUT
    except Exception as e:
        logger.error(f"Unexpected error verifying link: {type(e).__name__}: {e}")
        raise
