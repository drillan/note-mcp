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

from typing import TYPE_CHECKING

import pytest

from tests.e2e.helpers import PreviewValidator, save_and_open_preview, type_markdown_pattern

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
