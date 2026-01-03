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
        1. <table-of-contents> カスタム要素（note.com固有）
        2. nav要素（記事本文内）
        3. TableOfContentsを含むクラス名を持つ要素

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

        # note.com固有: <table-of-contents> カスタム要素を検索
        toc_custom_locator = article_body.locator("table-of-contents")
        toc_custom_count = await toc_custom_locator.count()
        if toc_custom_count > 0:
            return ValidationResult(
                success=True,
                expected="<table-of-contents> custom element",
                actual=f"Found {toc_custom_count} table-of-contents element(s)",
                message=f"Found {toc_custom_count} <table-of-contents> element(s) in article body",
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

    async def validate_math(
        self,
        formula_text: str | None = None,
        timeout_ms: int = 5000,
    ) -> ValidationResult:
        """数式がKaTeXでレンダリングされているか検証。

        note.comはKaTeXを使用して数式をレンダリングする。
        レンダリング後の要素は `.katex` クラスを持つ。

        Args:
            formula_text: 期待される数式テキスト（部分一致）。
                Noneの場合は数式要素の存在のみ確認。
            timeout_ms: 要素出現待機のタイムアウト（ミリ秒）

        Returns:
            ValidationResult with success=True if KaTeX element exists
        """
        # 記事本文がロードされるのを待機
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

        # KaTeX要素を検索
        katex_locator = article_body.locator(".katex")

        try:
            count = await katex_locator.count()
            if count == 0:
                return ValidationResult(
                    success=False,
                    expected=".katex element" + (f" containing '{formula_text}'" if formula_text else ""),
                    actual=None,
                    message="No KaTeX-rendered math elements found",
                )

            if formula_text:
                # 指定テキストを含む数式要素を検索
                matching_locator = katex_locator.filter(has_text=formula_text)
                matching_count = await matching_locator.count()
                if matching_count > 0:
                    return ValidationResult(
                        success=True,
                        expected=f".katex containing '{formula_text}'",
                        actual=f"Found {matching_count} matching element(s)",
                        message=f"Found KaTeX math containing '{formula_text}'",
                    )
                return ValidationResult(
                    success=False,
                    expected=f".katex containing '{formula_text}'",
                    actual=f"Found {count} .katex element(s), none containing '{formula_text}'",
                    message=f"KaTeX elements found but none contain '{formula_text}'",
                )

            return ValidationResult(
                success=True,
                expected=".katex element",
                actual=f"Found {count} element(s)",
                message=f"Found {count} KaTeX-rendered math element(s)",
            )
        except PlaywrightError as e:
            return ValidationResult(
                success=False,
                expected=".katex element",
                actual=None,
                message=f"Playwright error: {e}",
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
        # note.comのHTML出力が変更された場合に検知するため、フォールバック発生を明示
        b_locator = self.page.locator("b").filter(has_text=text)
        result = await self._validate_element(b_locator, f"<b> containing '{text}'")
        if result.success:
            result.message = f"[FALLBACK] Found <b> instead of <strong>: {result.message}"
        return result

    async def validate_horizontal_line(self) -> ValidationResult:
        """水平線が正しく変換されているか検証。

        Note:
            このメソッドは_validate_element()を使用しません。
            理由: <hr>は空要素のためinner_text()が取得できず、
            代わりに要素数をカウントして検証します。

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

    async def validate_blockquote(self, text: str) -> ValidationResult:
        """引用ブロックが正しく変換されているか検証。

        Args:
            text: 引用テキスト

        Returns:
            ValidationResult with success=True if <blockquote> contains text
        """
        locator = self.page.locator("blockquote").filter(has_text=text)
        return await self._validate_element(locator, f"<blockquote> containing '{text}'")

    async def _validate_list(
        self,
        items: list[str],
        list_tag: str,
    ) -> ValidationResult:
        """リスト検証の共通ロジック。

        Args:
            items: 期待されるリスト項目
            list_tag: リストのHTMLタグ名（"ul" または "ol"）

        Returns:
            ValidationResult with success=True if <{list_tag}><li> contains all items
        """
        if not items:
            return ValidationResult(
                success=False,
                expected=f"<{list_tag}> with items",
                actual=None,
                message="No items provided for validation",
            )

        try:
            # リスト要素の存在確認
            list_locator = self.page.locator(list_tag)
            list_count = await list_locator.count()
            if list_count == 0:
                return ValidationResult(
                    success=False,
                    expected=f"<{list_tag}> with {len(items)} item(s)",
                    actual=None,
                    message=f"No <{list_tag}> element found",
                )

            # 各項目が<{list_tag}> > <li>内に存在するか確認
            missing_items: list[str] = []
            for item in items:
                li_locator = self.page.locator(f"{list_tag} > li").filter(has_text=item)
                li_count = await li_locator.count()
                if li_count == 0:
                    missing_items.append(item)

            if missing_items:
                return ValidationResult(
                    success=False,
                    expected=f"<{list_tag}> with items: {items}",
                    actual=f"Missing: {missing_items}",
                    message=f"Missing {len(missing_items)} item(s) in <{list_tag}>: {missing_items}",
                )

            return ValidationResult(
                success=True,
                expected=f"<{list_tag}> with {len(items)} item(s)",
                actual=f"Found all {len(items)} item(s)",
                message=f"Found all items in <{list_tag}>: {items}",
            )
        except PlaywrightError as e:
            return ValidationResult(
                success=False,
                expected=f"<{list_tag}> with items: {items}",
                actual=None,
                message=f"Playwright error: {e}",
            )

    async def validate_unordered_list(self, items: list[str]) -> ValidationResult:
        """箇条書きリストが正しく変換されているか検証。

        Args:
            items: 期待されるリスト項目

        Returns:
            ValidationResult with success=True if <ul><li> contains all items
        """
        return await self._validate_list(items, "ul")

    async def validate_ordered_list(self, items: list[str]) -> ValidationResult:
        """番号付きリストが正しく変換されているか検証。

        Args:
            items: 期待されるリスト項目

        Returns:
            ValidationResult with success=True if <ol><li> contains all items
        """
        return await self._validate_list(items, "ol")
