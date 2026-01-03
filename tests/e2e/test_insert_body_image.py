"""E2E tests for note_insert_body_image MCP tool.

Tests that images can be reliably inserted into articles via browser automation,
addressing the 6 ProseMirror state-dependent failure points identified in issue #53.

Failure points addressed:
1. AI dialog dismissal timing
2. ProseMirror editor mount waiting
3. Floating menu visibility
4. Image insertion DOM change detection
5. figcaption focus
6. Save processing timing

Requires:
- Valid note.com session (login first if not authenticated)
- Network access to note.com

Run with: uv run pytest tests/e2e/test_insert_body_image.py -v
"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from note_mcp.browser.insert_image import insert_image_via_browser
from tests.e2e.helpers import (
    ImageValidator,
    ProseMirrorStabilizer,
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


# Test configuration
EDITOR_URL_TEMPLATE = "https://editor.note.com/notes/{article_key}/edit/"


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


@pytest_asyncio.fixture
async def editor_page(
    real_session: Session,
    draft_article: Article,
) -> AsyncGenerator[Page, None]:
    """Get a browser page with the editor loaded for the draft article.

    Creates a fresh browser context and navigates to the article editor.
    Uses ProseMirrorStabilizer to ensure editor is ready.

    Args:
        real_session: Authenticated session fixture
        draft_article: Draft article to edit

    Yields:
        Playwright Page with editor loaded and ready
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # Inject session cookies
        from tests.e2e.conftest import _inject_session_cookies

        await _inject_session_cookies(page, real_session)

        # Navigate to editor
        editor_url = EDITOR_URL_TEMPLATE.format(article_key=draft_article.key)
        await page.goto(editor_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle", timeout=30000)

        # Use stabilizer to prepare editor
        stabilizer = ProseMirrorStabilizer(page)
        await stabilizer.dismiss_ai_dialog()
        await stabilizer.wait_for_editor_ready()

        yield page

    finally:
        await context.close()
        await browser.close()
        await playwright.stop()


class TestProseMirrorStabilization:
    """Tests for ProseMirror editor stabilization.

    These tests verify that the 6 failure points identified in issue #53
    can be reliably handled by the ProseMirrorStabilizer.
    """

    async def test_ai_dialog_dismissal(
        self,
        real_session: Session,
        draft_article: Article,
    ) -> None:
        """Test that AI dialog can be dismissed reliably.

        Issue #53 Point 1: AI dialog dismissal timing.
        """
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            from tests.e2e.conftest import _inject_session_cookies

            await _inject_session_cookies(page, real_session)

            editor_url = EDITOR_URL_TEMPLATE.format(article_key=draft_article.key)
            await page.goto(editor_url, wait_until="domcontentloaded")

            # Test AI dialog dismissal
            stabilizer = ProseMirrorStabilizer(page)
            result = await stabilizer.dismiss_ai_dialog()

            assert result is True, "AI dialog dismissal should succeed (or no dialog present)"

        finally:
            await context.close()
            await browser.close()
            await playwright.stop()

    async def test_editor_ready_detection(
        self,
        editor_page: Page,
    ) -> None:
        """Test that editor readiness can be detected reliably.

        Issue #53 Point 2: ProseMirror editor mount waiting.
        """
        # Editor page fixture already ensures editor is ready
        # Verify by checking for .ProseMirror element
        editor = editor_page.locator(".ProseMirror")
        count = await editor.count()

        assert count > 0, "ProseMirror element should exist"
        assert await editor.first.is_visible(), "ProseMirror should be visible"

    async def test_floating_menu_visibility(
        self,
        editor_page: Page,
    ) -> None:
        """Test that floating menu can be made visible.

        Issue #53 Point 3: Floating menu visibility.
        """
        stabilizer = ProseMirrorStabilizer(editor_page)
        result = await stabilizer.show_floating_menu()

        assert result is True, "Floating menu should become visible with '画像' button"

    async def test_image_button_click(
        self,
        editor_page: Page,
    ) -> None:
        """Test that image button can be clicked.

        Prerequisite: Floating menu is visible.
        """
        stabilizer = ProseMirrorStabilizer(editor_page)

        # First show the menu
        await stabilizer.show_floating_menu()

        # Then click the image button
        result = await stabilizer.click_image_button()

        assert result is True, "'画像' button should be clickable"


class TestImageInsertion:
    """Tests for image insertion functionality.

    Tests the complete image insertion flow including upload,
    DOM detection, caption, and save.
    """

    async def test_image_insertion_without_caption(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """Test basic image insertion without caption.

        Verifies:
        - Image can be uploaded via file input
        - Image appears in editor (Issue #53 Point 4)
        - Article can be saved (Issue #53 Point 6)
        """
        result = await insert_image_via_browser(
            session=real_session,
            article_key=draft_article.key,
            file_path=str(test_image_path),
            caption=None,
        )

        assert result["success"] is True
        assert result["article_key"] == draft_article.key
        assert result["file_path"] == str(test_image_path)
        assert result["caption"] is None

    async def test_image_insertion_with_caption(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """Test image insertion with caption.

        Verifies:
        - Image can be uploaded
        - Caption can be entered (Issue #53 Point 5)
        - Both image and caption are saved
        """
        test_caption = "テスト画像のキャプション"

        result = await insert_image_via_browser(
            session=real_session,
            article_key=draft_article.key,
            file_path=str(test_image_path),
            caption=test_caption,
        )

        assert result["success"] is True
        assert result["article_key"] == draft_article.key
        assert result["caption"] == test_caption


class TestImageValidation:
    """Tests for image validation in preview.

    Verifies that inserted images are correctly displayed
    in the preview page.
    """

    async def test_inserted_image_visible_in_preview(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
        preview_page: Page,
    ) -> None:
        """Test that inserted image is visible in preview.

        Complete end-to-end test:
        1. Insert image via browser automation
        2. Refresh preview
        3. Validate image is visible
        """
        # Insert image
        await insert_image_via_browser(
            session=real_session,
            article_key=draft_article.key,
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

        assert result.success, f"Image validation failed: {result.message}"

    async def test_inserted_image_with_caption_in_preview(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
        preview_page: Page,
    ) -> None:
        """Test that inserted image with caption is visible in preview.

        End-to-end test with caption validation.
        """
        test_caption = "E2Eテスト用キャプション"

        # Insert image with caption
        await insert_image_via_browser(
            session=real_session,
            article_key=draft_article.key,
            file_path=str(test_image_path),
            caption=test_caption,
        )

        # Wait for changes to propagate
        await asyncio.sleep(2)

        # Refresh preview
        await preview_page.reload()
        await preview_page.wait_for_load_state("domcontentloaded")

        # Validate image with caption
        validator = ImageValidator(preview_page)
        result = await validator.validate_image_with_caption(test_caption)

        assert result.success, f"Image with caption validation failed: {result.message}"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_multiple_image_insertions(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """Test inserting multiple images sequentially.

        Verifies that multiple images can be inserted into the same article.
        """
        # Insert first image
        result1 = await insert_image_via_browser(
            session=real_session,
            article_key=draft_article.key,
            file_path=str(test_image_path),
            caption="最初の画像",
        )
        assert result1["success"] is True

        # Insert second image
        result2 = await insert_image_via_browser(
            session=real_session,
            article_key=draft_article.key,
            file_path=str(test_image_path),
            caption="二番目の画像",
        )
        assert result2["success"] is True

    async def test_invalid_file_path_raises_error(
        self,
        real_session: Session,
        draft_article: Article,
    ) -> None:
        """Test that invalid file path raises appropriate error."""
        from note_mcp.models import NoteAPIError

        with pytest.raises(NoteAPIError):
            await insert_image_via_browser(
                session=real_session,
                article_key=draft_article.key,
                file_path="/nonexistent/path/image.png",
                caption=None,
            )
