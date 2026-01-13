"""E2E tests for blockquote structure validation.

Tests that content after blockquotes with citations is correctly
positioned OUTSIDE the blockquote element.

Issue: #83 - note_create_from_fileで引用ブロック以降のコンテンツが引用内に含まれる

Run with: uv run pytest tests/e2e/test_blockquote_structure.py -v
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


class TestBlockquoteContentStructure:
    """Tests for blockquote content structure after citation.

    Verifies that content following a blockquote with citation
    is correctly positioned outside the blockquote element.
    """

    async def test_content_after_blockquote_not_nested(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """引用ブロック後のコンテンツが引用外に配置される。

        再現手順:
        1. 引用ブロック + 出典を入力
        2. 引用後に見出しを入力
        3. プレビューで見出しが<blockquote>外にあることを確認

        Issue #83 の修正を検証するテスト。
        """
        # Arrange
        quote_text = "これは引用テキストです"
        citation = "テストドキュメント"
        heading_text = "引用後の見出し"

        # Create article with blockquote, citation, and heading after
        markdown_content = f"""> {quote_text}
> — {citation}

## {heading_text}"""

        article_input = ArticleInput(
            title=draft_article.title,
            body=markdown_content,
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Assert: 引用ブロックと見出しの検証
        validator = PreviewValidator(preview_page)

        # 1. 引用ブロックが存在することを確認
        blockquote_result = await validator.validate_blockquote(quote_text)
        assert blockquote_result.success, f"Blockquote validation failed: {blockquote_result.message}"

        # 2. 見出しが存在することを確認
        heading_result = await validator.validate_heading(2, heading_text)
        assert heading_result.success, f"Heading validation failed: {heading_result.message}"

        # 3. 見出しがblockquote内にないことを確認（最重要）
        nested_heading = preview_page.locator(f"blockquote h2:has-text('{heading_text}')")
        nested_count = await nested_heading.count()
        assert nested_count == 0, (
            f"CRITICAL: Heading '{heading_text}' should NOT be inside blockquote, "
            f"but found {nested_count} nested h2 element(s). "
            "This indicates Issue #83 is not fixed."
        )

    async def test_paragraph_after_blockquote_not_nested(
        self,
        real_session: Session,
        draft_article: Article,
        preview_page: Page,
    ) -> None:
        """引用ブロック後の段落が引用外に配置される。

        見出しだけでなく、通常の段落も引用外に配置されることを確認。
        """
        # Arrange
        quote_text = "引用テキスト"
        citation = "出典"
        paragraph_text = "これは引用後の段落です"

        # Create article with blockquote, citation, and paragraph after
        markdown_content = f"""> {quote_text}
> — {citation}

{paragraph_text}"""

        article_input = ArticleInput(
            title=draft_article.title,
            body=markdown_content,
        )
        await update_article(real_session, draft_article.id, article_input)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Assert
        validator = PreviewValidator(preview_page)

        # 1. 引用ブロックが存在することを確認
        blockquote_result = await validator.validate_blockquote(quote_text)
        assert blockquote_result.success, f"Blockquote validation failed: {blockquote_result.message}"

        # 2. 段落テキストがページ上に存在することを確認
        paragraph_locator = preview_page.locator(f"p:has-text('{paragraph_text}')")
        paragraph_count = await paragraph_locator.count()
        assert paragraph_count >= 1, (
            f"Paragraph '{paragraph_text}' should exist on the page, "
            f"but found {paragraph_count} matching element(s). "
            "The paragraph text may not have been correctly typed or saved."
        )

        # 3. 段落がblockquote内にないことを確認（最重要）
        nested_paragraph = preview_page.locator(f"blockquote p:has-text('{paragraph_text}')")
        nested_count = await nested_paragraph.count()
        assert nested_count == 0, (
            f"CRITICAL: Paragraph '{paragraph_text}' should NOT be inside blockquote, "
            f"but found {nested_count} nested p element(s). "
            "This indicates Issue #83 is not fixed."
        )
