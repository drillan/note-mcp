"""Validation helpers for E2E testing.

Provides utilities for validating Markdown-to-HTML conversion
on note.com's preview pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


@dataclass
class ValidationResult:
    """検証結果を表すデータクラス。

    Attributes:
        success: 検証成功かどうか
        expected: 期待されるHTML要素（セレクタ形式）
        actual: 実際に見つかった要素（テキストまたはNone）
        message: 詳細メッセージ（成功時は確認内容、失敗時はエラー詳細）
    """

    success: bool
    expected: str
    actual: str | None
    message: str


class PreviewValidator:
    """プレビューページのHTML要素を検証するヘルパー。

    note.comのプレビューページでMarkdown変換結果を検証する。
    各メソッドはPlaywrightのLocatorを使用して要素を検索し、
    ValidationResultを返す。

    Attributes:
        page: Playwright Pageインスタンス
    """

    def __init__(self, page: Page) -> None:
        """Initialize validator with a Playwright page.

        Args:
            page: Playwright Page instance to validate
        """
        self.page = page

    async def validate_heading(self, level: int, text: str) -> ValidationResult:
        """見出しが正しく変換されているか検証。

        Args:
            level: 見出しレベル（2 or 3）
            text: 見出しテキスト

        Returns:
            ValidationResult with success=True if <h{level}> contains text
        """
        selector = f"h{level}"
        locator = self.page.locator(selector).filter(has_text=text)

        try:
            count = await locator.count()
            if count > 0:
                actual_text = await locator.first.inner_text()
                return ValidationResult(
                    success=True,
                    expected=f"<h{level}> containing '{text}'",
                    actual=actual_text,
                    message=f"Found h{level} with text: {actual_text}",
                )
            else:
                return ValidationResult(
                    success=False,
                    expected=f"<h{level}> containing '{text}'",
                    actual=None,
                    message=f"No h{level} element found containing '{text}'",
                )
        except Exception as e:
            return ValidationResult(
                success=False,
                expected=f"<h{level}> containing '{text}'",
                actual=None,
                message=f"Error during validation: {e}",
            )

    async def validate_strikethrough(self, text: str) -> ValidationResult:
        """打消し線が正しく変換されているか検証。

        Args:
            text: 打消し線で囲まれるテキスト

        Returns:
            ValidationResult with success=True if <s> contains text
        """
        locator = self.page.locator("s").filter(has_text=text)

        try:
            count = await locator.count()
            if count > 0:
                actual_text = await locator.first.inner_text()
                return ValidationResult(
                    success=True,
                    expected=f"<s> containing '{text}'",
                    actual=actual_text,
                    message=f"Found strikethrough: {actual_text}",
                )
            else:
                return ValidationResult(
                    success=False,
                    expected=f"<s> containing '{text}'",
                    actual=None,
                    message=f"No <s> element found containing '{text}'",
                )
        except Exception as e:
            return ValidationResult(
                success=False,
                expected=f"<s> containing '{text}'",
                actual=None,
                message=f"Error during validation: {e}",
            )

    async def validate_code_block(self, code: str, language: str | None = None) -> ValidationResult:
        """コードブロックが正しく変換されているか検証。

        Args:
            code: コード内容
            language: 言語指定（オプション）

        Returns:
            ValidationResult with success=True if <pre><code> contains code
        """
        # note.comのコードブロック構造: <pre><code>...</code></pre>
        locator = self.page.locator("pre code").filter(has_text=code)

        try:
            count = await locator.count()
            if count > 0:
                actual_text = await locator.first.inner_text()
                truncated = actual_text[:50] + "..." if len(actual_text) > 50 else actual_text
                return ValidationResult(
                    success=True,
                    expected=f"<pre><code> containing '{code}'",
                    actual=actual_text,
                    message=f"Found code block: {truncated}",
                )
            else:
                return ValidationResult(
                    success=False,
                    expected=f"<pre><code> containing '{code}'",
                    actual=None,
                    message=f"No code block found containing '{code}'",
                )
        except Exception as e:
            return ValidationResult(
                success=False,
                expected=f"<pre><code> containing '{code}'",
                actual=None,
                message=f"Error during validation: {e}",
            )

    async def validate_alignment(self, text: str, alignment: str) -> ValidationResult:
        """テキスト配置が正しく適用されているか検証。

        Args:
            text: テキスト内容
            alignment: 配置（"center", "right", "left"）

        Returns:
            ValidationResult with success=True if element has correct text-align style
        """
        # text-align: {alignment} スタイルを持つ要素を検索
        selector = f"[style*='text-align: {alignment}']"
        locator = self.page.locator(selector).filter(has_text=text)

        try:
            count = await locator.count()
            if count > 0:
                actual_text = await locator.first.inner_text()
                return ValidationResult(
                    success=True,
                    expected=f"Element with text-align: {alignment} containing '{text}'",
                    actual=actual_text,
                    message=f"Found aligned text: {actual_text}",
                )
            else:
                return ValidationResult(
                    success=False,
                    expected=f"Element with text-align: {alignment} containing '{text}'",
                    actual=None,
                    message=f"No element with text-align: {alignment} found containing '{text}'",
                )
        except Exception as e:
            return ValidationResult(
                success=False,
                expected=f"Element with text-align: {alignment} containing '{text}'",
                actual=None,
                message=f"Error during validation: {e}",
            )
