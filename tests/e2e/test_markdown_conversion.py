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
