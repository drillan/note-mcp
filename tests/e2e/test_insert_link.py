"""E2E tests for UI-based link insertion.

Tests that insert_link_at_cursor() correctly inserts links via UI automation
in note.com's ProseMirror editor.

Requires:
- Valid note.com session (login first if not authenticated)
- Network access to note.com

Run with: uv run pytest tests/e2e/test_insert_link.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from playwright.async_api import Page

from note_mcp.browser.insert_link import LinkResult, insert_link_at_cursor
from tests.e2e.helpers import PreviewValidator
from tests.e2e.helpers.preview_helpers import open_preview_for_article_key

if TYPE_CHECKING:
    from note_mcp.models import Article, Session


async def _save_and_open_preview(editor_page: Page) -> Page:
    """Save article and open preview (local helper).

    This helper is local to test_insert_link.py because it tests
    UI-based link insertion that requires editor_page.
    """
    # Save with Ctrl+S
    await editor_page.keyboard.press("Control+s")
    await editor_page.wait_for_timeout(1000)

    # Get article key from URL and open preview
    url = editor_page.url
    # URL format: .../notes/{key}/edit/
    key = url.split("/")[-2]
    return await open_preview_for_article_key(editor_page, key)


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


class TestInsertLinkBasic:
    """Basic link insertion tests via UI automation."""

    async def test_insert_link_basic(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """基本的なリンク挿入テスト。

        UI経由でリンクを挿入し、エディタ内にリンクが作成されることを確認。
        """
        # Arrange
        text = "テストリンク"
        url = "https://example.com"

        # Act
        result, debug = await insert_link_at_cursor(editor_page, text, url)

        # Assert
        assert result == LinkResult.SUCCESS, f"Link insertion failed: {debug}"

        # Verify link exists in editor
        link = await editor_page.query_selector(f'a[href="{url}"]')
        assert link is not None, "Link element not found in editor"

        # Verify link text
        link_text = await link.text_content()
        assert link_text == text, f"Expected link text '{text}', got '{link_text}'"

    async def test_insert_link_english_text(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """英語テキストのリンク挿入テスト。"""
        # Arrange
        text = "Example Link"
        url = "https://example.com/english"

        # Act
        result, debug = await insert_link_at_cursor(editor_page, text, url)

        # Assert
        assert result == LinkResult.SUCCESS, f"Link insertion failed: {debug}"

        # Verify link in editor
        link = await editor_page.query_selector(f'a[href="{url}"]')
        assert link is not None, "Link element not found in editor"


class TestInsertLinkJapanese:
    """Japanese text link insertion tests."""

    async def test_insert_link_japanese_text(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """日本語テキストのリンク挿入テスト。"""
        # Arrange
        text = "日本語リンクテキスト"
        url = "https://example.com/japanese"

        # Act
        result, debug = await insert_link_at_cursor(editor_page, text, url)

        # Assert
        assert result == LinkResult.SUCCESS, f"Link insertion failed: {debug}"

        # Verify link in editor
        link = await editor_page.query_selector(f'a[href="{url}"]')
        assert link is not None, "Link element not found in editor"

        link_text = await link.text_content()
        assert link_text == text, f"Expected '{text}', got '{link_text}'"

    async def test_insert_link_japanese_url(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """日本語を含むURLのリンク挿入テスト。"""
        # Arrange
        text = "日本語URL"
        url = "https://example.com/日本語パス"

        # Act
        result, debug = await insert_link_at_cursor(editor_page, text, url)

        # Assert
        assert result == LinkResult.SUCCESS, f"Link insertion failed: {debug}"


class TestInsertMultipleLinks:
    """Multiple link insertion tests."""

    async def test_insert_multiple_links(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """複数リンクの連続挿入テスト。"""
        # Arrange
        links = [
            ("リンク1", "https://example.com/1"),
            ("リンク2", "https://example.com/2"),
            ("リンク3", "https://example.com/3"),
        ]

        # Act & Assert
        for text, url in links:
            result, debug = await insert_link_at_cursor(editor_page, text, url)
            assert result == LinkResult.SUCCESS, f"Failed to insert {text}: {debug}"

            # Add space between links
            await editor_page.keyboard.type(" ")

        # Verify all links exist
        for _text, url in links:
            link = await editor_page.query_selector(f'a[href="{url}"]')
            assert link is not None, f"Link with href={url} not found"


class TestInsertLinkPreview:
    """Link insertion with preview validation tests."""

    async def test_link_appears_in_preview(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """リンクがプレビューページに正しく表示されることを確認。"""
        # Arrange
        text = "プレビューテスト"
        url = "https://example.com/preview"

        # Act: Insert link
        result, debug = await insert_link_at_cursor(editor_page, text, url)
        assert result == LinkResult.SUCCESS, f"Link insertion failed: {debug}"

        # Save and open preview
        preview_page = await _save_and_open_preview(editor_page)

        # Assert: Validate on preview page
        validator = PreviewValidator(preview_page)
        validation_result = await validator.validate_link(text, url)

        assert validation_result.success, f"Link not found in preview: {validation_result.message}"


class TestInsertLinkEdgeCases:
    """Edge case tests for link insertion."""

    async def test_insert_link_long_text(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """長いテキストのリンク挿入テスト。"""
        # Arrange
        text = "これは非常に長いリンクテキストです。テキスト選択が正しく動作することを確認します。"
        url = "https://example.com/long-text"

        # Act
        result, debug = await insert_link_at_cursor(editor_page, text, url)

        # Assert
        assert result == LinkResult.SUCCESS, f"Link insertion failed: {debug}"

    async def test_insert_link_special_chars_in_url(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """特殊文字を含むURLのリンク挿入テスト。"""
        # Arrange
        text = "特殊文字URL"
        url = "https://example.com/path?query=value&param=test#anchor"

        # Act
        result, debug = await insert_link_at_cursor(editor_page, text, url)

        # Assert
        assert result == LinkResult.SUCCESS, f"Link insertion failed: {debug}"

    async def test_insert_link_empty_text_raises(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """空テキストでValueErrorが発生することを確認。"""
        with pytest.raises(ValueError, match="text cannot be empty"):
            await insert_link_at_cursor(editor_page, "", "https://example.com")

    async def test_insert_link_empty_url_raises(
        self,
        real_session: Session,
        draft_article: Article,
        editor_page: Page,
    ) -> None:
        """空URLでValueErrorが発生することを確認。"""
        with pytest.raises(ValueError, match="url cannot be empty"):
            await insert_link_at_cursor(editor_page, "テスト", "")
