"""E2E tests for native HTML validation on note.com.

Tests that Markdown syntax typed directly into the ProseMirror editor
is correctly converted to HTML by note.com's native conversion.

This test suite verifies native HTML generation, NOT the markdown_to_html()
function, thus eliminating the tautology problem in the original tests.

Requires:
- Valid note.com session (login first if not authenticated)
- Network access to note.com

Run with: uv run pytest tests/e2e/test_native_html_validation.py -v
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from note_mcp.browser.toc_helpers import insert_toc_at_placeholder
from tests.e2e.helpers import (
    PreviewValidator,
    insert_toc_placeholder,
    save_and_open_preview,
    type_code_block,
    type_markdown_pattern,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

    from note_mcp.models import Article, Session

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


class TestNativeHeadingConversion:
    """Tests for native heading (H2, H3) conversion via ProseMirror."""

    async def test_h2_native_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """## 見出し + space → <h2>見出し</h2> (native conversion)."""
        # Arrange
        test_text = "ネイティブH2見出し"

        # Act: Type markdown pattern into editor (triggers ProseMirror conversion)
        await type_markdown_pattern(editor_page, f"## {test_text}")

        # Save and open preview
        preview_page = await save_and_open_preview(editor_page)

        # Assert: Validate on preview page (native HTML)
        validator = PreviewValidator(preview_page)
        result = await validator.validate_heading(2, test_text)

        assert result.success, f"Native H2 conversion failed: {result.message}"

    async def test_h3_native_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """### 見出し + space → <h3>見出し</h3> (native conversion)."""
        # Arrange
        test_text = "ネイティブH3見出し"

        # Act: Type markdown pattern into editor
        await type_markdown_pattern(editor_page, f"### {test_text}")

        # Save and open preview
        preview_page = await save_and_open_preview(editor_page)

        # Assert: Validate on preview page
        validator = PreviewValidator(preview_page)
        result = await validator.validate_heading(3, test_text)

        assert result.success, f"Native H3 conversion failed: {result.message}"


class TestNativeStrikethroughConversion:
    """Tests for native strikethrough conversion via ProseMirror."""

    async def test_strikethrough_native_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """~~text~~ + space → <s>text</s> (native conversion)."""
        # Arrange
        test_text = "ネイティブ打消し"

        # Act: Type strikethrough pattern
        await type_markdown_pattern(editor_page, f"~~{test_text}~~")

        # Save and open preview
        preview_page = await save_and_open_preview(editor_page)

        # Assert: Validate on preview page
        validator = PreviewValidator(preview_page)
        result = await validator.validate_strikethrough(test_text)

        assert result.success, f"Native strikethrough conversion failed: {result.message}"


class TestNativeCodeBlockConversion:
    """Tests for native code block conversion via ProseMirror."""

    async def test_code_block_native_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """```code``` → <pre><code>code</code></pre> (native conversion)."""
        # Arrange
        test_code = "console.log('test')"

        # Act: Type code block into editor (triggers ProseMirror conversion)
        await type_code_block(editor_page, test_code)

        # Save and open preview
        preview_page = await save_and_open_preview(editor_page)

        # Assert: Validate on preview page (native HTML)
        validator = PreviewValidator(preview_page)
        result = await validator.validate_code_block(test_code)

        assert result.success, f"Native code block conversion failed: {result.message}"

    async def test_code_block_with_language(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """```javascript code``` → <pre><code>code</code></pre> with language hint."""
        # Arrange
        test_code = "function hello() { return 'world'; }"
        language = "javascript"

        # Act: Type code block with language hint
        await type_code_block(editor_page, test_code, language=language)

        # Save and open preview
        preview_page = await save_and_open_preview(editor_page)

        # Assert: Validate code content is preserved
        validator = PreviewValidator(preview_page)
        result = await validator.validate_code_block(test_code)

        assert result.success, f"Native code block with language failed: {result.message}"


class TestNativeAlignmentConversion:
    """Tests for native text alignment conversion via ProseMirror."""

    async def test_center_alignment_native_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """->text<- → text-align: center (native conversion)."""
        # Arrange
        test_text = "中央揃えテキスト"

        # Act: Type center alignment pattern
        await type_markdown_pattern(editor_page, f"->{test_text}<-")

        # Save and open preview
        preview_page = await save_and_open_preview(editor_page)

        # Assert: Validate alignment style
        validator = PreviewValidator(preview_page)
        result = await validator.validate_alignment(test_text, "center")

        assert result.success, f"Native center alignment conversion failed: {result.message}"

    async def test_right_alignment_native_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """->text → text-align: right (native conversion)."""
        # Arrange
        test_text = "右揃えテキスト"

        # Act: Type right alignment pattern
        await type_markdown_pattern(editor_page, f"->{test_text}")

        # Save and open preview
        preview_page = await save_and_open_preview(editor_page)

        # Assert: Validate alignment style
        validator = PreviewValidator(preview_page)
        result = await validator.validate_alignment(test_text, "right")

        assert result.success, f"Native right alignment conversion failed: {result.message}"


class TestNativeTableOfContentsConversion:
    """Tests for native TOC (Table of Contents) conversion."""

    async def test_toc_native_conversion(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """§§TOC§§ + 見出し → UIからTOC挿入 → プレビューでTOC表示.

        TOCが生成されるには見出し（H2/H3）が必要。
        note.comのUIメニューからTOCを挿入する。
        """
        # Arrange: TOCプレースホルダーを先に入力（既存テストと同じ順序）
        await insert_toc_placeholder(editor_page)

        # 見出しを追加（TOC生成に必須）
        await type_markdown_pattern(editor_page, "## TOCテスト見出し1")
        await asyncio.sleep(0.2)
        await editor_page.keyboard.press("Enter")
        await editor_page.keyboard.type("本文テキスト")
        await editor_page.keyboard.press("Enter")
        await asyncio.sleep(0.3)

        await type_markdown_pattern(editor_page, "## TOCテスト見出し2")
        await asyncio.sleep(0.2)
        await editor_page.keyboard.press("Enter")
        await asyncio.sleep(0.5)

        # Act: UIメニューからTOCを挿入
        toc_inserted = await insert_toc_at_placeholder(editor_page)
        assert toc_inserted, "Failed to insert TOC via UI menu"

        # エディタ内でTOCが挿入されたことを確認
        toc_in_editor = editor_page.locator(".ProseMirror nav")
        toc_count = await toc_in_editor.count()
        assert toc_count >= 1, "TOC should exist in editor before saving"

        # 保存してプレビューを開く
        preview_page = await save_and_open_preview(editor_page)

        # Assert: プレビューでTOC要素を検証
        validator = PreviewValidator(preview_page)
        result = await validator.validate_toc()

        assert result.success, f"Native TOC conversion failed: {result.message}"

    async def test_toc_without_headings_not_generated(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """§§TOC§§のみ（見出しなし）→ TOC未生成を確認.

        見出しがない場合、TOCは生成されない。
        """
        # Arrange: TOCプレースホルダーのみ（見出しなし）
        await insert_toc_placeholder(editor_page)
        await editor_page.keyboard.type("本文テキストのみ")

        # Act: 保存してプレビューを開く
        preview_page = await save_and_open_preview(editor_page)

        # Assert: TOC要素が存在しないことを確認
        validator = PreviewValidator(preview_page)
        result = await validator.validate_toc()

        # TOCが生成されないことを確認
        assert not result.success, f"TOC should not be generated without headings, but found: {result.message}"
