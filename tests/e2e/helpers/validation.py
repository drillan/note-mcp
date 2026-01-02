"""Validation helpers for E2E testing.

Provides utilities for validating Markdown-to-HTML conversion
on note.com's preview pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from playwright.async_api import Error as PlaywrightError

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page


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

    async def _validate_element(
        self,
        locator: Locator,
        expected_description: str,
        *,
        truncate_length: int | None = None,
    ) -> ValidationResult:
        """共通のバリデーションロジック。

        Args:
            locator: 検証対象のPlaywright Locator
            expected_description: 期待される要素の説明（エラーメッセージ用）
            truncate_length: 実際のテキストを切り詰める長さ（Noneで切り詰めなし）

        Returns:
            ValidationResult with success=True if element is found
        """
        try:
            count = await locator.count()
            if count > 0:
                actual_text = await locator.first.inner_text()
                display_text = actual_text
                if truncate_length and len(actual_text) > truncate_length:
                    display_text = actual_text[:truncate_length] + "..."
                return ValidationResult(
                    success=True,
                    expected=expected_description,
                    actual=actual_text,
                    message=f"Found: {display_text}",
                )
            else:
                return ValidationResult(
                    success=False,
                    expected=expected_description,
                    actual=None,
                    message=f"No element found matching: {expected_description}",
                )
        except PlaywrightError as e:
            return ValidationResult(
                success=False,
                expected=expected_description,
                actual=None,
                message=f"Playwright error: {e}",
            )

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
        return await self._validate_element(locator, f"<h{level}> containing '{text}'")

    async def validate_strikethrough(self, text: str) -> ValidationResult:
        """打消し線が正しく変換されているか検証。

        Args:
            text: 打消し線で囲まれるテキスト

        Returns:
            ValidationResult with success=True if <s> contains text
        """
        locator = self.page.locator("s").filter(has_text=text)
        return await self._validate_element(locator, f"<s> containing '{text}'")

    async def validate_code_block(self, code: str) -> ValidationResult:
        """コードブロックが正しく変換されているか検証。

        Args:
            code: コード内容

        Returns:
            ValidationResult with success=True if <pre><code> contains code
        """
        # note.comのコードブロック構造: <pre><code>...</code></pre>
        locator = self.page.locator("pre code").filter(has_text=code)
        return await self._validate_element(locator, f"<pre><code> containing '{code}'", truncate_length=50)

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
        return await self._validate_element(locator, f"Element with text-align: {alignment} containing '{text}'")

    async def validate_toc(self, timeout_ms: int = 5000) -> ValidationResult:
        """目次（TOC）がプレビューに表示されているか検証。

        note.comのTOC要素は以下のいずれかで検出:
        1. nav要素（記事本文内）
        2. TableOfContentsを含むクラス名を持つ要素

        プレビューページのロード完了を待機してから検証を行う。

        Args:
            timeout_ms: 要素出現待機のタイムアウト（ミリ秒）

        Returns:
            ValidationResult with success=True if TOC element exists
        """
        # まず記事本文がロードされるのを待機
        article_body = self.page.locator(".note-common-styles__textnote-body, .p-noteBody")
        try:
            await article_body.first.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightError:
            return ValidationResult(
                success=False,
                expected="Article body container",
                actual=None,
                message="Article body not found on preview page",
            )

        # nav要素を検索（記事本文内のTOC）
        nav_locator = article_body.locator("nav")
        try:
            # nav要素の出現を待機（TOCが存在する場合）
            await nav_locator.first.wait_for(state="visible", timeout=timeout_ms)
            return await self._validate_element(
                nav_locator,
                "TOC nav element in article body",
            )
        except PlaywrightError:
            pass

        # フォールバック: TableOfContentsクラスを検索
        toc_class_locator = self.page.locator("[class*='TableOfContents']")
        return await self._validate_element(
            toc_class_locator,
            "TOC element with class containing 'TableOfContents'",
        )

    async def validate_link(self, text: str, url: str) -> ValidationResult:
        """リンクが正しく変換されているか検証。

        Args:
            text: リンクテキスト
            url: 期待されるhref値

        Returns:
            ValidationResult with success=True if <a href="{url}">{text}</a> exists
        """
        # href属性でリンクを検索し、テキストでフィルタ
        locator = self.page.locator(f'a[href="{url}"]').filter(has_text=text)
        return await self._validate_element(locator, f"<a href='{url}'> containing '{text}'")

    async def validate_bold(self, text: str) -> ValidationResult:
        """太字が正しく変換されているか検証。

        Args:
            text: 太字で囲まれるテキスト

        Returns:
            ValidationResult with success=True if <strong> or <b> contains text
        """
        # strongまたはbタグを検索
        strong_locator = self.page.locator("strong").filter(has_text=text)
        strong_count = await strong_locator.count()
        if strong_count > 0:
            return await self._validate_element(strong_locator, f"<strong> containing '{text}'")

        # フォールバック: bタグを検索
        b_locator = self.page.locator("b").filter(has_text=text)
        return await self._validate_element(b_locator, f"<b> containing '{text}'")

    async def validate_italic(self, text: str) -> ValidationResult:
        """斜体が正しく変換されているか検証。

        Args:
            text: 斜体で囲まれるテキスト

        Returns:
            ValidationResult with success=True if <em> or <i> contains text
        """
        # emまたはiタグを検索
        em_locator = self.page.locator("em").filter(has_text=text)
        em_count = await em_locator.count()
        if em_count > 0:
            return await self._validate_element(em_locator, f"<em> containing '{text}'")

        # フォールバック: iタグを検索
        i_locator = self.page.locator("i").filter(has_text=text)
        return await self._validate_element(i_locator, f"<i> containing '{text}'")

    async def validate_horizontal_line(self) -> ValidationResult:
        """水平線が正しく変換されているか検証。

        Returns:
            ValidationResult with success=True if <hr> element exists
        """
        locator = self.page.locator("hr")
        try:
            count = await locator.count()
            if count > 0:
                return ValidationResult(
                    success=True,
                    expected="<hr> element",
                    actual="<hr>",
                    message=f"Found {count} <hr> element(s)",
                )
            else:
                return ValidationResult(
                    success=False,
                    expected="<hr> element",
                    actual=None,
                    message="No <hr> element found",
                )
        except PlaywrightError as e:
            return ValidationResult(
                success=False,
                expected="<hr> element",
                actual=None,
                message=f"Playwright error: {e}",
            )
