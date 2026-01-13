"""E2E tests for Markdown conversion on note.com.

Tests that Markdown syntax is correctly converted to HTML
when viewed in the preview page.

Requires:
- Valid note.com session (login first if not authenticated)
- Network access to note.com

Run with: uv run pytest tests/e2e/test_markdown_conversion.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from note_mcp.api.articles import update_article
from note_mcp.models import ArticleInput
from tests.e2e.helpers import PreviewValidator

if TYPE_CHECKING:
    from playwright.async_api import Page

    from note_mcp.models import Article, Session


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


class TestHeadingConversion:
    """Tests for heading (H2, H3) conversion."""

    async def test_h2_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """## 見出し → <h2>見出し</h2>"""
        # Arrange: Update article with H2 heading
        test_text = "テスト見出しH2"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"## {test_text}\n\n本文です。",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate H2
        validator = PreviewValidator(preview_page)
        result = await validator.validate_heading(2, test_text)

        # Assert
        assert result.success, f"H2 conversion failed: {result.message}"

    async def test_h3_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """### 見出し → <h3>見出し</h3>"""
        # Arrange: Update article with H3 heading
        test_text = "テスト見出しH3"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"### {test_text}\n\n本文です。",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate H3
        validator = PreviewValidator(preview_page)
        result = await validator.validate_heading(3, test_text)

        # Assert
        assert result.success, f"H3 conversion failed: {result.message}"


class TestStrikethroughConversion:
    """Tests for strikethrough conversion."""

    async def test_strikethrough_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """~~text~~ + space → <s>text</s>

        Note: ProseMirror requires space after ~~ pattern to trigger conversion.
        The markdown_to_html function should handle this correctly.
        """
        # Arrange: Update article with strikethrough
        test_text = "削除されたテキスト"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"通常のテキスト ~~{test_text}~~ さらにテキスト",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate strikethrough
        validator = PreviewValidator(preview_page)
        result = await validator.validate_strikethrough(test_text)

        # Assert
        assert result.success, f"Strikethrough conversion failed: {result.message}"


class TestCodeBlockConversion:
    """Tests for code block conversion."""

    async def test_fenced_code_block(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """```python\\ncode\\n``` → <pre><code>code</code></pre>"""
        # Arrange: Update article with code block
        code_content = "print('Hello, World!')"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"コード例:\n\n```python\n{code_content}\n```\n\n以上です。",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate code block
        validator = PreviewValidator(preview_page)
        result = await validator.validate_code_block(code_content)

        # Assert
        assert result.success, f"Code block conversion failed: {result.message}"


class TestTextAlignment:
    """Tests for text alignment conversion."""

    async def test_center_alignment(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """->text<- → style="text-align: center" """
        # Arrange: Update article with center-aligned text
        test_text = "中央揃えテキスト"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"->{test_text}<-\n\n通常のテキスト",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate center alignment
        validator = PreviewValidator(preview_page)
        result = await validator.validate_alignment(test_text, "center")

        # Assert
        assert result.success, f"Center alignment failed: {result.message}"

    async def test_right_alignment(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """->text → style="text-align: right" """
        # Arrange: Update article with right-aligned text
        test_text = "右揃えテキスト"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"->{test_text}\n\n通常のテキスト",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate right alignment
        validator = PreviewValidator(preview_page)
        result = await validator.validate_alignment(test_text, "right")

        # Assert
        assert result.success, f"Right alignment failed: {result.message}"


class TestBoldConversion:
    """Tests for bold text conversion."""

    async def test_bold_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """**text** → <strong>text</strong>"""
        # Arrange: Update article with bold text
        test_text = "太字テキスト"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"通常テキスト **{test_text}** 後続テキスト",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate bold
        validator = PreviewValidator(preview_page)
        result = await validator.validate_bold(test_text)

        # Assert
        assert result.success, f"Bold conversion failed: {result.message}"


class TestBlockquoteConversion:
    """Tests for blockquote conversion."""

    async def test_blockquote_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """> text → <blockquote>text</blockquote>"""
        # Arrange: Update article with blockquote
        quote_text = "引用テキストです"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"> {quote_text}\n\n後続テキスト",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate blockquote
        validator = PreviewValidator(preview_page)
        result = await validator.validate_blockquote(quote_text)

        # Assert
        assert result.success, f"Blockquote conversion failed: {result.message}"

    async def test_blockquote_with_citation(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """> text\\n> — source → <blockquote> with <figcaption>"""
        # Arrange: Update article with blockquote and citation
        quote_text = "これは引用テキストです"
        citation = "テストドキュメント"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"> {quote_text}\n> — {citation}\n\n後続テキスト",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate blockquote (citation is inside figcaption)
        validator = PreviewValidator(preview_page)
        result = await validator.validate_blockquote(quote_text)

        # Assert
        assert result.success, f"Blockquote with citation failed: {result.message}"


class TestListConversion:
    """Tests for list conversion."""

    async def test_unordered_list_single_item(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """- item → <ul><li>item</li></ul>"""
        # Arrange: Update article with single unordered list item
        items = ["単一項目"]
        body = "\n".join(f"- {item}" for item in items) + "\n\n後続テキスト"
        article_input = ArticleInput(title=draft_article.title, body=body)
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate unordered list
        validator = PreviewValidator(preview_page)
        result = await validator.validate_unordered_list(items)

        # Assert
        assert result.success, f"Unordered list failed: {result.message}"

    async def test_unordered_list_multiple_items(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """Multiple - items → <ul><li>...</li><li>...</li></ul>"""
        # Arrange: Update article with multiple unordered list items
        items = ["項目1", "項目2", "項目3"]
        body = "\n".join(f"- {item}" for item in items) + "\n\n後続テキスト"
        article_input = ArticleInput(title=draft_article.title, body=body)
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate unordered list
        validator = PreviewValidator(preview_page)
        result = await validator.validate_unordered_list(items)

        # Assert
        assert result.success, f"Unordered list with multiple items failed: {result.message}"

    async def test_ordered_list_single_item(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """1. item → <ol><li>item</li></ol>"""
        # Arrange: Update article with single ordered list item
        items = ["番号付き単一項目"]
        body = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items)) + "\n\n後続"
        article_input = ArticleInput(title=draft_article.title, body=body)
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate ordered list
        validator = PreviewValidator(preview_page)
        result = await validator.validate_ordered_list(items)

        # Assert
        assert result.success, f"Ordered list failed: {result.message}"

    async def test_ordered_list_multiple_items(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """Multiple numbered items → <ol><li>...</li><li>...</li></ol>"""
        # Arrange: Update article with multiple ordered list items
        items = ["最初の項目", "2番目の項目", "3番目の項目"]
        body = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items)) + "\n\n後続"
        article_input = ArticleInput(title=draft_article.title, body=body)
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate ordered list
        validator = PreviewValidator(preview_page)
        result = await validator.validate_ordered_list(items)

        # Assert
        assert result.success, f"Ordered list with multiple items failed: {result.message}"


class TestHorizontalLineConversion:
    """Tests for horizontal line conversion."""

    async def test_horizontal_line(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """--- → <hr>"""
        # Arrange: Update article with horizontal line
        article_input = ArticleInput(
            title=draft_article.title,
            body="前のテキスト\n\n---\n\n後のテキスト",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate horizontal line
        validator = PreviewValidator(preview_page)
        result = await validator.validate_horizontal_line()

        # Assert
        assert result.success, f"Horizontal line conversion failed: {result.message}"


class TestLinkConversion:
    """Tests for link conversion."""

    async def test_link_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """[text](url) → <a href="url">text</a>"""
        # Arrange: Update article with link
        link_text = "リンクテキスト"
        link_url = "https://example.com"
        article_input = ArticleInput(
            title=draft_article.title,
            body=f"テキスト [{link_text}]({link_url}) 後続",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate link
        validator = PreviewValidator(preview_page)
        result = await validator.validate_link(link_text, link_url)

        # Assert
        assert result.success, f"Link conversion failed: {result.message}"


class TestTocConversion:
    """Tests for TOC (Table of Contents) conversion."""

    async def test_toc_with_headings(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """[TOC] with headings → TOC element."""
        # Arrange: Update article with TOC marker and headings
        article_input = ArticleInput(
            title=draft_article.title,
            body="[TOC]\n\n## 見出し1\n\n本文1\n\n## 見出し2\n\n本文2",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate TOC
        validator = PreviewValidator(preview_page)
        result = await validator.validate_toc()

        # Assert
        assert result.success, f"TOC conversion failed: {result.message}"

    async def test_toc_without_headings_not_generated(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """[TOC] without headings → No TOC generated."""
        # Arrange: Update article with TOC marker but no headings
        article_input = ArticleInput(
            title=draft_article.title,
            body="[TOC]\n\n本文テキストのみ、見出しなし",
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Act: Validate TOC (should not exist)
        validator = PreviewValidator(preview_page)
        result = await validator.validate_toc()

        # Assert: TOC should NOT be generated without headings
        assert not result.success, f"TOC should not be generated without headings, but found: {result.message}"
