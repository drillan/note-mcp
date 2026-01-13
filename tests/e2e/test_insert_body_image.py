"""E2E tests for note_insert_body_image MCP tool (API-only).

Tests that images can be reliably inserted into articles via API.
Browser automation has been removed in favor of API-based implementation (Issue #131).

Requires:
- Valid note.com session (login first if not authenticated)
- Network access to note.com

Run with: uv run pytest tests/e2e/test_insert_body_image.py -v
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from note_mcp.api.images import insert_image_via_api
from tests.e2e.helpers import (
    ImageValidator,
    create_test_png,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

    from note_mcp.models import Article, Session


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


@pytest.fixture
def test_image_path() -> Path:
    """Create a test PNG image for upload.

    Creates a temporary file that is automatically cleaned up.

    Returns:
        Path to the test PNG file
    """
    # Create temp directory that won't be cleaned up until test completes
    temp_dir = Path(tempfile.mkdtemp())
    image_path = temp_dir / "test_image.png"

    # Create a valid PNG file
    create_test_png(image_path, width=200, height=150, color=(50, 100, 200))

    return image_path


class TestInsertImageViaApiE2E:
    """E2E tests for insert_image_via_api function (Issue #114 API-only).

    Tests the fully API-based image insertion flow (no Playwright dependency):
    1. Upload image to S3 via API
    2. Get article HTML body via API
    3. Append image HTML to body
    4. Save via draft_save API
    """

    async def test_api_image_insertion_without_caption(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """Test API-based image insertion without caption.

        Uses article_id instead of article_key.
        Verifies API-only mode (no fallback).
        """
        result = await insert_image_via_api(
            session=real_session,
            article_id=draft_article.id,
            file_path=str(test_image_path),
            caption=None,
        )

        assert result["success"] is True
        assert result["article_id"] == draft_article.id
        assert result["article_key"] == draft_article.key
        assert result["image_url"].startswith("https://")
        assert result["fallback_used"] is False  # API-only mode (Issue #114)

    async def test_api_image_insertion_with_caption(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """Test API-based image insertion with caption."""
        test_caption = "API経由テスト画像のキャプション"

        result = await insert_image_via_api(
            session=real_session,
            article_id=draft_article.id,
            file_path=str(test_image_path),
            caption=test_caption,
        )

        assert result["success"] is True
        assert result["article_id"] == draft_article.id
        assert result["caption"] == test_caption

    async def test_api_image_insertion_with_key_format(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """Test API-based image insertion using article_key format.

        The article_id parameter should accept both numeric ID and key format.
        """
        result = await insert_image_via_api(
            session=real_session,
            article_id=draft_article.key,  # Using key format
            file_path=str(test_image_path),
            caption=None,
        )

        assert result["success"] is True
        assert result["article_key"] == draft_article.key

    async def test_api_image_visible_in_preview(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
        preview_page: Page,
    ) -> None:
        """Test that API-inserted image is visible in preview."""
        # Insert image via API
        await insert_image_via_api(
            session=real_session,
            article_id=draft_article.id,
            file_path=str(test_image_path),
            caption=None,
        )

        # Wait for changes to propagate
        await asyncio.sleep(2)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Validate image
        validator = ImageValidator(preview_page)
        result = await validator.validate_image_exists(expected_count=1)

        assert result.success, f"API-inserted image validation failed: {result.message}"

    async def test_api_only_caption_persisted(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """Test that caption is persisted in article body (Issue #114).

        Verifies that the figcaption HTML is correctly saved via draft_save API.
        """
        from note_mcp.api.articles import get_article_raw_html

        test_caption = "E2E検証用キャプション_API保存確認"

        # Insert image with caption via API
        result = await insert_image_via_api(
            session=real_session,
            article_id=draft_article.id,
            file_path=str(test_image_path),
            caption=test_caption,
        )

        assert result["success"] is True
        assert result["fallback_used"] is False

        # Verify caption is in the article body
        article = await get_article_raw_html(real_session, draft_article.id)
        assert test_caption in article.body, f"Caption not found in article body: {article.body[:500]}..."

    async def test_api_only_no_playwright_required(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """Test that API-only insertion works without browser (Issue #114).

        Verifies that the image insertion completes faster than browser-based
        insertion would (indicating no Playwright startup overhead).
        """
        import time

        start = time.time()
        result = await insert_image_via_api(
            session=real_session,
            article_id=draft_article.id,
            file_path=str(test_image_path),
            caption=None,
        )
        elapsed = time.time() - start

        assert result["success"] is True
        assert result["fallback_used"] is False
        # API-only should complete in under 5 seconds (browser would take 10-15s)
        assert elapsed < 5.0, f"API-only insertion took too long: {elapsed:.2f}s (expected < 5s)"
