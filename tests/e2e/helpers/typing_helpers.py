"""Typing helpers for E2E native HTML validation tests.

Provides utilities for typing Markdown patterns into ProseMirror
and navigating to preview pages.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from note_mcp.browser.toc_helpers import TOC_PLACEHOLDER
from note_mcp.browser.typing_helpers import type_markdown_content

if TYPE_CHECKING:
    from playwright.async_api import Page

# Timeouts
DEFAULT_CONVERSION_WAIT_SECONDS = 0.1
DEFAULT_SAVE_WAIT_SECONDS = 1.0
DEFAULT_NAVIGATION_TIMEOUT_MS = 30000


async def type_markdown_pattern(
    page: Page,
    pattern: str,
    trigger: str = " ",  # 互換性のため維持（未使用）
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,  # 互換性のため維持（未使用）
) -> None:
    """Markdownパターンをエディタに入力しProseMirror変換をトリガー。

    Note: 内部実装は本番コード type_markdown_content() に委譲。
    trigger/wait_time パラメータは後方互換性のため維持されているが、
    実際の変換タイミングは本番コードが制御する。

    Args:
        page: Playwright Pageインスタンス
        pattern: 入力するMarkdownパターン（例: "## 見出し", "~~打消し~~"）
        trigger: 変換トリガー（デフォルトはスペース）（未使用）
        wait_time: 変換待機時間（秒）（未使用）

    Raises:
        ValueError: patternが空の場合
    """
    # 未使用パラメータの警告を抑制
    _ = trigger
    _ = wait_time

    if not pattern:
        raise ValueError("pattern cannot be empty")

    await type_markdown_content(page, pattern)


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
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,  # 互換性のため維持（未使用）
) -> None:
    """コードブロックをエディタに入力。

    Note: 内部実装は本番コード type_markdown_content() に委譲。

    Args:
        page: Playwright Pageインスタンス
        code: コードブロック内のコード
        language: 言語指定（オプション）
        wait_time: 変換待機時間（秒）（未使用）

    Raises:
        ValueError: codeが空の場合
    """
    # 未使用パラメータの警告を抑制
    _ = wait_time

    if not code:
        raise ValueError("code cannot be empty")

    # Markdown形式に変換して本番コードに委譲
    markdown = f"```{language}\n{code}\n```"
    await type_markdown_content(page, markdown)


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
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,  # 互換性のため維持（未使用）
) -> None:
    """リンクをエディタに入力しProseMirror変換をトリガー。

    Note: 内部実装は本番コード type_markdown_content() に委譲。
    ⚠️ 本番コードにリンク処理が未実装のため、テストは失敗が期待される（#75）

    Args:
        page: Playwright Pageインスタンス
        text: リンクテキスト
        url: リンクURL
        wait_time: 変換待機時間（秒）（未使用）

    Raises:
        ValueError: textまたはurlが空の場合
    """
    # 未使用パラメータの警告を抑制
    _ = wait_time

    if not text:
        raise ValueError("text cannot be empty")
    if not url:
        raise ValueError("url cannot be empty")

    # Markdown形式に変換して本番コードに委譲
    markdown = f"[{text}]({url})"
    await type_markdown_content(page, markdown)


async def type_horizontal_line(
    page: Page,
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,  # 互換性のため維持（未使用）
) -> None:
    """水平線をエディタに入力しProseMirror変換をトリガー。

    Note: 内部実装は本番コード type_markdown_content() に委譲。
    ⚠️ 本番コードに水平線処理が未実装のため、テストは失敗が期待される（#75）

    Args:
        page: Playwright Pageインスタンス
        wait_time: 変換待機時間（秒）（未使用）
    """
    # 未使用パラメータの警告を抑制
    _ = wait_time

    # Markdown形式で本番コードに委譲
    await type_markdown_content(page, "---")


async def type_blockquote(
    page: Page,
    text: str,
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,  # 互換性のため維持（未使用）
) -> None:
    """引用ブロックをエディタに入力しProseMirror変換をトリガー。

    Note: 内部実装は本番コード type_markdown_content() に委譲。

    Args:
        page: Playwright Pageインスタンス
        text: 引用テキスト
        wait_time: 変換待機時間（秒）（未使用）

    Raises:
        ValueError: textが空の場合
    """
    # 未使用パラメータの警告を抑制
    _ = wait_time

    if not text:
        raise ValueError("text cannot be empty")

    # Markdown形式に変換して本番コードに委譲
    markdown = f"> {text}"
    await type_markdown_content(page, markdown)


async def type_unordered_list(
    page: Page,
    items: list[str],
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,  # 互換性のため維持（未使用）
) -> None:
    """箇条書きリストをエディタに入力しProseMirror変換をトリガー。

    Note: 内部実装は本番コード type_markdown_content() に委譲。

    Args:
        page: Playwright Pageインスタンス
        items: リスト項目のリスト
        wait_time: 変換待機時間（秒）（未使用）

    Raises:
        ValueError: itemsが空の場合
    """
    # 未使用パラメータの警告を抑制
    _ = wait_time

    if not items:
        raise ValueError("items cannot be empty")

    # Markdown形式に変換して本番コードに委譲
    markdown = "\n".join(f"- {item}" for item in items)
    await type_markdown_content(page, markdown)


async def type_ordered_list(
    page: Page,
    items: list[str],
    wait_time: float = DEFAULT_CONVERSION_WAIT_SECONDS,  # 互換性のため維持（未使用）
) -> None:
    """番号付きリストをエディタに入力しProseMirror変換をトリガー。

    Note: 内部実装は本番コード type_markdown_content() に委譲。

    Args:
        page: Playwright Pageインスタンス
        items: リスト項目のリスト
        wait_time: 変換待機時間（秒）（未使用）

    Raises:
        ValueError: itemsが空の場合
    """
    # 未使用パラメータの警告を抑制
    _ = wait_time

    if not items:
        raise ValueError("items cannot be empty")

    # Markdown形式に変換して本番コードに委譲
    markdown = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
    await type_markdown_content(page, markdown)
