"""Typing helpers for E2E native HTML validation tests.

Provides utilities for typing Markdown patterns into ProseMirror
and navigating to preview pages.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from note_mcp.browser.toc_helpers import TOC_PLACEHOLDER

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
    await preview_button.wait_for(state="visible", timeout=DEFAULT_NAVIGATION_TIMEOUT_MS)

    # 新しいタブでプレビューを開く
    async with page.context.expect_page(timeout=timeout) as new_page_info:
        await preview_button.click()

    # プレビューページを取得
    preview_page = await new_page_info.value
    await preview_page.wait_for_load_state("domcontentloaded", timeout=timeout)

    return preview_page


async def type_code_block(
    page: Page,
    code: str,
    language: str = "",
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """コードブロックをエディタに入力。

    バッククォート3つで囲んだコードブロックを入力し、
    ProseMirror変換をトリガーする。

    Args:
        page: Playwright Pageインスタンス
        code: コードブロック内のコード
        language: 言語指定（オプション）
        wait_time: 変換待機時間（秒）

    Raises:
        ValueError: codeが空の場合
    """
    if not code:
        raise ValueError("code cannot be empty")

    # エディタにフォーカス
    editor = page.locator(".ProseMirror").first
    await editor.click()

    # 開始フェンス
    await page.keyboard.type(f"```{language}")
    await page.keyboard.press("Enter")

    # コード本文
    await page.keyboard.type(code)
    await page.keyboard.press("Enter")

    # 終了フェンス
    await page.keyboard.type("```")
    await page.keyboard.type(" ")  # 変換トリガー

    await asyncio.sleep(wait_time)


async def insert_toc_placeholder(
    page: Page,
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """TOCプレースホルダー（§§TOC§§）をエディタに入力。

    note.comのTOC挿入機能をテストするためのプレースホルダーを入力する。
    プレースホルダーは後続の保存処理でTOC要素に置換される。

    Args:
        page: Playwright Pageインスタンス
        wait_time: 入力後の待機時間（秒）
    """
    editor = page.locator(".ProseMirror").first
    await editor.click()

    # プレースホルダーを入力
    await page.keyboard.type(TOC_PLACEHOLDER)
    await page.keyboard.press("Enter")  # 次の行へ移動

    await asyncio.sleep(wait_time)


async def type_link(
    page: Page,
    text: str,
    url: str,
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """リンクをエディタに入力しProseMirror変換をトリガー。

    [text](url) + スペース → <a href="url">text</a>

    Args:
        page: Playwright Pageインスタンス
        text: リンクテキスト
        url: リンクURL
        wait_time: 変換待機時間（秒）

    Raises:
        ValueError: textまたはurlが空の場合
    """
    if not text:
        raise ValueError("text cannot be empty")
    if not url:
        raise ValueError("url cannot be empty")

    # エディタにフォーカス
    editor = page.locator(".ProseMirror").first
    await editor.click()

    # Markdownリンク記法を入力
    await page.keyboard.type(f"[{text}]({url})")

    # スペースで変換トリガー
    await page.keyboard.type(" ")

    # 変換完了を待機
    await asyncio.sleep(wait_time)


async def type_horizontal_line(
    page: Page,
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """水平線をエディタに入力しProseMirror変換をトリガー。

    --- + Enter → <hr>

    Note: 水平線はスペースではなくEnterで変換がトリガーされる。

    Args:
        page: Playwright Pageインスタンス
        wait_time: 変換待機時間（秒）
    """
    # エディタにフォーカス
    editor = page.locator(".ProseMirror").first
    await editor.click()

    # 水平線記法を入力
    await page.keyboard.type("---")

    # Enterで変換トリガー（水平線はスペースではなくEnterでトリガー）
    await page.keyboard.press("Enter")

    # 変換完了を待機
    await asyncio.sleep(wait_time)


async def type_blockquote(
    page: Page,
    text: str,
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """引用ブロックをエディタに入力しProseMirror変換をトリガー。

    "> " + text + space → <blockquote><p>text</p></blockquote>

    Note:
        この関数は行頭でのみ機能します。ProseMirrorは "> " の入力時点で
        引用ブロックを開始し、テキスト入力後のスペースで変換を完了します。

    Args:
        page: Playwright Pageインスタンス
        text: 引用テキスト
        wait_time: 変換待機時間（秒）

    Raises:
        ValueError: textが空の場合
    """
    if not text:
        raise ValueError("text cannot be empty")

    # エディタにフォーカス
    editor = page.locator(".ProseMirror").first
    await editor.click()

    # 引用記法を入力
    await page.keyboard.type(f"> {text}")

    # スペースで変換トリガー
    await page.keyboard.type(" ")

    # 変換完了を待機
    await asyncio.sleep(wait_time)


async def _type_list(
    page: Page,
    items: list[str],
    first_prefix: str,
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """リスト入力の共通ロジック。

    Note:
        この関数は行頭でのみ機能します。ProseMirrorは最初のプレフィックス入力時点で
        リストを開始し、以降の項目は自動でプレフィックスが追加されます。

    Args:
        page: Playwright Pageインスタンス
        items: リスト項目のリスト
        first_prefix: 最初の項目のプレフィックス（"- " または "1. "）
        wait_time: 変換待機時間（秒）

    Raises:
        ValueError: itemsが空の場合
    """
    if not items:
        raise ValueError("items cannot be empty")

    # エディタにフォーカス
    editor = page.locator(".ProseMirror").first
    await editor.click()

    # 最初の項目: プレフィックスで開始
    await page.keyboard.type(f"{first_prefix}{items[0]}")
    await page.keyboard.press("Enter")
    await asyncio.sleep(wait_time)

    # 以降の項目: ProseMirrorが自動でプレフィックスを追加するためテキストのみ入力
    for item in items[1:]:
        await page.keyboard.type(item)
        await page.keyboard.press("Enter")
        await asyncio.sleep(wait_time)


async def type_unordered_list(
    page: Page,
    items: list[str],
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """箇条書きリストをエディタに入力しProseMirror変換をトリガー。

    "- " + item1 + Enter → <ul><li>item1</li></ul>
    item2 + Enter → <ul><li>item1</li><li>item2</li></ul>
    （ProseMirrorが自動で "- " を追加）

    Note:
        この関数は行頭でのみ機能します。ProseMirrorは "- " の入力時点で
        箇条書きリストを開始します。

    Args:
        page: Playwright Pageインスタンス
        items: リスト項目のリスト
        wait_time: 変換待機時間（秒）

    Raises:
        ValueError: itemsが空の場合
    """
    await _type_list(page, items, "- ", wait_time)


async def type_ordered_list(
    page: Page,
    items: list[str],
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,
) -> None:
    """番号付きリストをエディタに入力しProseMirror変換をトリガー。

    "1. " + item1 + Enter → <ol><li>item1</li></ol>
    item2 + Enter → <ol><li>item1</li><li>item2</li></ol>
    （ProseMirrorが自動で番号をインクリメント）

    Note:
        この関数は行頭でのみ機能します。ProseMirrorは "1. " の入力時点で
        番号付きリストを開始します。

    Args:
        page: Playwright Pageインスタンス
        items: リスト項目のリスト
        wait_time: 変換待機時間（秒）

    Raises:
        ValueError: itemsが空の場合
    """
    await _type_list(page, items, "1. ", wait_time)
