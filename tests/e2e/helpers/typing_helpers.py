"""Typing helpers for E2E native HTML validation tests.

Provides utilities for typing Markdown patterns into ProseMirror
and navigating to preview pages.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

# Timeouts
DEFAULT_CONVERSION_WAIT_SECONDS = 0.1
DEFAULT_SAVE_WAIT_SECONDS = 1.0
DEFAULT_NAVIGATION_TIMEOUT_MS = 30000


async def type_markdown_pattern(
    page: Page,
    pattern: str,
    trigger: str = " ",
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """Markdownパターンをエディタに入力しProseMirror変換をトリガー。

    note.comのProseMirrorエディタでは、Markdownパターンの後にスペースを
    入力することで変換がトリガーされる。

    Args:
        page: Playwright Pageインスタンス
        pattern: 入力するMarkdownパターン（例: "## 見出し", "~~打消し~~"）
        trigger: 変換トリガー（デフォルトはスペース）
        wait_time: 変換待機時間（秒）

    Raises:
        ValueError: patternが空の場合
    """
    if not pattern:
        raise ValueError("pattern cannot be empty")

    # エディタにフォーカス
    editor = page.locator(".ProseMirror").first
    await editor.click()

    # パターンを入力
    await page.keyboard.type(pattern)

    # トリガーを入力（スペースでMarkdown変換発動）
    if trigger:
        await page.keyboard.type(trigger)

    # 変換完了を待機
    await asyncio.sleep(wait_time)


async def save_and_open_preview(
    page: Page,
    timeout: float = DEFAULT_NAVIGATION_TIMEOUT_MS,
) -> Page:
    """エディタ内容を保存し、プレビューページを開く。

    Args:
        page: エディタを表示しているPage
        timeout: ページ読み込みタイムアウト（ミリ秒）

    Returns:
        Page: プレビューページを表示しているPage

    Raises:
        TimeoutError: プレビューページが読み込めない場合
    """
    # 下書き保存（Ctrl+S）
    await page.keyboard.press("Control+s")
    await asyncio.sleep(DEFAULT_SAVE_WAIT_SECONDS)

    # メニューボタン（3点アイコン）をクリック
    menu_button = page.locator('button[aria-label="その他"]')
    await menu_button.wait_for(state="visible", timeout=timeout)
    await menu_button.click()

    # プレビューボタンをクリック
    preview_button = page.locator("#header-popover button", has_text="プレビュー")
    await preview_button.wait_for(state="visible", timeout=10000)

    # 新しいタブでプレビューを開く
    async with page.context.expect_page(timeout=timeout) as new_page_info:
        await preview_button.click()

    # プレビューページを取得
    preview_page = await new_page_info.value
    await preview_page.wait_for_load_state("domcontentloaded", timeout=timeout)

    return preview_page
