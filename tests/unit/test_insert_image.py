"""Unit tests for browser-based image insertion."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.browser.insert_image import (
    _click_add_image_button,
    _input_image_caption,
    _save_article,
    _upload_image_via_file_chooser,
    _wait_for_image_insertion,
    insert_image_via_browser,
)
from note_mcp.models import ErrorCode, NoteAPIError, Session

if TYPE_CHECKING:
    pass


def create_mock_session() -> Session:
    """Create a mock session for testing."""
    return Session(
        cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
        user_id="user123",
        username="testuser",
        expires_at=int(time.time()) + 3600,
        created_at=int(time.time()),
    )


class TestInsertImageValidation:
    """Tests for image file validation in insert_image_via_browser."""

    @pytest.mark.asyncio
    async def test_file_not_found_raises_error(self) -> None:
        """Test that missing file raises NoteAPIError."""
        session = create_mock_session()

        with pytest.raises(NoteAPIError) as exc_info:
            await insert_image_via_browser(
                session=session,
                article_key="n12345abcdef",
                file_path="/nonexistent/file.jpg",
            )

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_invalid_extension_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid file extension raises NoteAPIError."""
        session = create_mock_session()
        file_path = tmp_path / "test.txt"
        file_path.write_text("text content")

        with pytest.raises(NoteAPIError) as exc_info:
            await insert_image_via_browser(
                session=session,
                article_key="n12345abcdef",
                file_path=str(file_path),
            )

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "format" in exc_info.value.message.lower()


class TestClickAddImageButton:
    """Tests for _click_add_image_button function."""

    @pytest.mark.asyncio
    async def test_click_add_image_button_success(self) -> None:
        """Test successful click on add image button via JavaScript."""
        mock_page = AsyncMock()
        # Mock page.evaluate to return success on first call
        mock_page.evaluate = AsyncMock(return_value={"clicked": True, "y": 500})

        result = await _click_add_image_button(mock_page)

        assert result is True
        mock_page.evaluate.assert_called()

    @pytest.mark.asyncio
    async def test_click_add_image_button_not_found(self) -> None:
        """Test when add image button is not found."""
        mock_page = AsyncMock()
        # Mock page.evaluate to return not clicked
        mock_page.evaluate = AsyncMock(return_value={"clicked": False})

        # Mock editor locator for fallback click
        mock_editor_first = AsyncMock()
        mock_editor_first.count = AsyncMock(return_value=1)
        mock_editor_first.click = AsyncMock()

        mock_editor_locator = MagicMock()
        mock_editor_locator.first = mock_editor_first

        mock_page.locator = MagicMock(return_value=mock_editor_locator)

        result = await _click_add_image_button(mock_page)

        assert result is False


class TestUploadImageViaFileChooser:
    """Tests for _upload_image_via_file_chooser function."""

    @pytest.mark.asyncio
    async def test_upload_image_via_file_chooser_success(self) -> None:
        """Test successful file upload via hidden file input."""
        mock_page = AsyncMock()

        # Mock file input locator with .first property
        mock_input_first = AsyncMock()
        mock_input_first.count = AsyncMock(return_value=1)
        mock_input_first.set_input_files = AsyncMock()

        mock_input_locator = MagicMock()
        mock_input_locator.first = mock_input_first

        mock_page.locator = MagicMock(return_value=mock_input_locator)

        result = await _upload_image_via_file_chooser(mock_page, "/path/to/image.jpg")

        assert result is True
        mock_input_first.set_input_files.assert_called_once_with("/path/to/image.jpg")

    @pytest.mark.asyncio
    async def test_upload_image_via_file_chooser_input_not_found(self) -> None:
        """Test when file input is not found."""
        mock_page = AsyncMock()

        # Mock file input locator with .first property - not found
        mock_input_first = AsyncMock()
        mock_input_first.count = AsyncMock(return_value=0)

        mock_input_locator = MagicMock()
        mock_input_locator.first = mock_input_first

        mock_page.locator = MagicMock(return_value=mock_input_locator)

        result = await _upload_image_via_file_chooser(mock_page, "/path/to/image.jpg")

        assert result is False


class TestWaitForImageInsertion:
    """Tests for _wait_for_image_insertion function."""

    @pytest.mark.asyncio
    async def test_wait_for_image_insertion_success(self) -> None:
        """Test successful wait for image insertion."""
        mock_page = AsyncMock()
        # Mock page.evaluate to return True (image inserted)
        mock_page.evaluate = AsyncMock(return_value=True)

        result = await _wait_for_image_insertion(mock_page, initial_img_count=0)

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_image_insertion_timeout(self) -> None:
        """Test timeout during image insertion wait."""
        mock_page = AsyncMock()
        # Mock page.evaluate to return False (no image inserted within timeout)
        mock_page.evaluate = AsyncMock(return_value=False)

        result = await _wait_for_image_insertion(mock_page, initial_img_count=0)

        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_image_insertion_with_caption(self) -> None:
        """Test image insertion with caption."""
        mock_page = AsyncMock()
        # First call: image inserted, second call: caption input
        mock_page.evaluate = AsyncMock(return_value=True)

        # Mock figcaption locator
        mock_figcaption = AsyncMock()
        mock_figcaption.count = AsyncMock(return_value=1)
        mock_figcaption_element = AsyncMock()
        mock_figcaption.nth = MagicMock(return_value=mock_figcaption_element)

        mock_keyboard = AsyncMock()
        mock_keyboard.type = AsyncMock()
        mock_page.keyboard = mock_keyboard

        mock_page.locator = MagicMock(return_value=mock_figcaption)

        result = await _wait_for_image_insertion(mock_page, initial_img_count=0, caption="Test caption")

        assert result is True


class TestInputImageCaption:
    """Tests for _input_image_caption function."""

    @pytest.mark.asyncio
    async def test_input_image_caption_empty_caption(self) -> None:
        """Test that empty caption returns True without action."""
        mock_page = AsyncMock()

        result = await _input_image_caption(mock_page, "")

        assert result is True
        mock_page.locator.assert_not_called()

    @pytest.mark.asyncio
    async def test_input_image_caption_success(self) -> None:
        """Test successful caption input."""
        mock_page = AsyncMock()
        mock_figcaption = AsyncMock()
        mock_figcaption.count = AsyncMock(return_value=1)
        mock_figcaption.nth = MagicMock(return_value=AsyncMock())
        mock_figcaption.nth.return_value.click = AsyncMock()

        mock_keyboard = AsyncMock()
        mock_keyboard.type = AsyncMock()
        mock_page.keyboard = mock_keyboard

        mock_page.locator = MagicMock(return_value=mock_figcaption)

        result = await _input_image_caption(mock_page, "Test caption")

        assert result is True


class TestSaveArticle:
    """Tests for _save_article function."""

    @pytest.mark.asyncio
    async def test_save_article_success(self) -> None:
        """Test successful article save via JavaScript."""
        mock_page = AsyncMock()
        mock_page.keyboard = AsyncMock()

        # First evaluate returns True (save button clicked)
        # Second evaluate returns None (no error message)
        mock_page.evaluate = AsyncMock(side_effect=[True, None])

        result = await _save_article(mock_page)

        assert result is True
        assert mock_page.evaluate.call_count >= 1

    @pytest.mark.asyncio
    async def test_save_article_button_not_found(self) -> None:
        """Test when save button is not found."""
        mock_page = AsyncMock()
        mock_page.keyboard = AsyncMock()

        # evaluate returns False (save button not found)
        mock_page.evaluate = AsyncMock(return_value=False)

        result = await _save_article(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_save_article_retry_on_error(self) -> None:
        """Test retry when save fails with error message."""
        mock_page = AsyncMock()
        mock_page.keyboard = AsyncMock()

        # First attempt: button clicked, but error
        # Second attempt: button clicked, success
        mock_page.evaluate = AsyncMock(
            side_effect=[
                True,  # First button click
                "保存に失敗しました",  # First error check
                True,  # Second button click
                None,  # Second error check (success)
            ]
        )

        result = await _save_article(mock_page)

        assert result is True


class TestInsertImageViaBrowser:
    """Tests for insert_image_via_browser function."""

    @pytest.mark.asyncio
    async def test_insert_image_via_browser_success(self, tmp_path: Path) -> None:
        """Test successful image insertion via browser."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        with patch("note_mcp.browser.insert_image._setup_page_with_session") as mock_setup:
            mock_page = AsyncMock()
            # Mock page.evaluate to return initial image count
            mock_page.evaluate = AsyncMock(return_value=0)
            mock_setup.return_value = mock_page

            with (
                patch("note_mcp.browser.insert_image._click_add_image_button") as mock_click,
                patch("note_mcp.browser.insert_image._upload_image_via_file_chooser") as mock_upload,
                patch("note_mcp.browser.insert_image._wait_for_image_insertion") as mock_wait,
                patch("note_mcp.browser.insert_image._save_article") as mock_save,
            ):
                mock_click.return_value = True
                mock_upload.return_value = True
                mock_wait.return_value = True

                result = await insert_image_via_browser(
                    session=session,
                    article_key="n12345abcdef",
                    file_path=str(file_path),
                    caption="Test caption",
                )

                assert result["success"] is True
                assert result["article_key"] == "n12345abcdef"
                assert result["file_path"] == str(file_path)
                assert result["caption"] == "Test caption"

                mock_setup.assert_called_once()
                mock_click.assert_called_once()
                mock_upload.assert_called_once()
                mock_wait.assert_called_once()
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_image_via_browser_click_fails(self, tmp_path: Path) -> None:
        """Test image insertion fails when add image button click fails."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        with patch("note_mcp.browser.insert_image._setup_page_with_session") as mock_setup:
            mock_page = AsyncMock()
            # Mock page.evaluate to return initial image count
            mock_page.evaluate = AsyncMock(return_value=0)
            mock_setup.return_value = mock_page

            with patch("note_mcp.browser.insert_image._click_add_image_button") as mock_click:
                mock_click.return_value = False

                with pytest.raises(NoteAPIError) as exc_info:
                    await insert_image_via_browser(
                        session=session,
                        article_key="n12345abcdef",
                        file_path=str(file_path),
                    )

                assert exc_info.value.code == ErrorCode.API_ERROR
                assert "add image button" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_insert_image_via_browser_upload_fails(self, tmp_path: Path) -> None:
        """Test image insertion fails when upload fails."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        with patch("note_mcp.browser.insert_image._setup_page_with_session") as mock_setup:
            mock_page = AsyncMock()
            # Mock page.evaluate to return initial image count
            mock_page.evaluate = AsyncMock(return_value=0)
            mock_setup.return_value = mock_page

            with (
                patch("note_mcp.browser.insert_image._click_add_image_button") as mock_click,
                patch("note_mcp.browser.insert_image._upload_image_via_file_chooser") as mock_upload,
            ):
                mock_click.return_value = True
                mock_upload.return_value = False

                with pytest.raises(NoteAPIError) as exc_info:
                    await insert_image_via_browser(
                        session=session,
                        article_key="n12345abcdef",
                        file_path=str(file_path),
                    )

                assert exc_info.value.code == ErrorCode.API_ERROR
                assert "upload" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_insert_image_via_browser_wait_fails(self, tmp_path: Path) -> None:
        """Test image insertion fails when wait for insertion fails."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        with patch("note_mcp.browser.insert_image._setup_page_with_session") as mock_setup:
            mock_page = AsyncMock()
            # Mock page.evaluate to return initial image count
            mock_page.evaluate = AsyncMock(return_value=0)
            mock_setup.return_value = mock_page

            with (
                patch("note_mcp.browser.insert_image._click_add_image_button") as mock_click,
                patch("note_mcp.browser.insert_image._upload_image_via_file_chooser") as mock_upload,
                patch("note_mcp.browser.insert_image._wait_for_image_insertion") as mock_wait,
            ):
                mock_click.return_value = True
                mock_upload.return_value = True
                mock_wait.return_value = False

                with pytest.raises(NoteAPIError) as exc_info:
                    await insert_image_via_browser(
                        session=session,
                        article_key="n12345abcdef",
                        file_path=str(file_path),
                    )

                assert exc_info.value.code == ErrorCode.API_ERROR
                assert "insertion" in exc_info.value.message.lower() or "failed" in exc_info.value.message.lower()


class TestInsertImageViaApi:
    """Tests for insert_image_via_api function (Issue #114 API-only image insertion)."""

    @pytest.mark.asyncio
    async def test_insert_image_via_api_success(self, tmp_path: Path) -> None:
        """Test successful image insertion via API-only (no Playwright)."""
        from note_mcp.browser.insert_image import insert_image_via_api
        from note_mcp.models import Article, ArticleStatus, Image, ImageType

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="<p>Test body</p>",
            status=ArticleStatus.DRAFT,
        )

        mock_image = Image(
            key="image_key_123",
            url="https://d2l930y2yx77uc.cloudfront.net/production/uploads/images/123.jpg",
            original_path=str(file_path),
            uploaded_at=1234567890,
            image_type=ImageType.BODY,
        )

        mock_updated_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="<p>Test body</p><figure>...</figure>",
            status=ArticleStatus.DRAFT,
        )

        with (
            patch("note_mcp.browser.insert_image.get_article_raw_html") as mock_get,
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
            patch("note_mcp.browser.insert_image.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_update.return_value = mock_updated_article

            result = await insert_image_via_api(
                session=session,
                article_id="12345",
                file_path=str(file_path),
                caption="Test caption",
            )

            assert result["success"] is True
            assert result["article_id"] == "12345"
            assert result["article_key"] == "n12345abcdef"
            assert result["image_url"] == mock_image.url
            assert result["fallback_used"] is False  # API-only mode

            mock_get.assert_called_once_with(session, "12345")
            mock_upload.assert_called_once()
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_image_via_api_upload_fails(self, tmp_path: Path) -> None:
        """Test API insertion fails when image upload fails."""
        from note_mcp.browser.insert_image import insert_image_via_api
        from note_mcp.models import Article, ArticleStatus

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="<p>Test body</p>",
            status=ArticleStatus.DRAFT,
        )

        with (
            patch("note_mcp.browser.insert_image.get_article_raw_html") as mock_get,
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
        ):
            mock_get.return_value = mock_article
            mock_upload.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="Upload failed",
            )

            with pytest.raises(NoteAPIError) as exc_info:
                await insert_image_via_api(
                    session=session,
                    article_id="12345",
                    file_path=str(file_path),
                )

            assert exc_info.value.code == ErrorCode.API_ERROR

    @pytest.mark.asyncio
    async def test_insert_image_via_api_update_fails(self, tmp_path: Path) -> None:
        """Test API insertion fails when article update fails."""
        from note_mcp.browser.insert_image import insert_image_via_api
        from note_mcp.models import Article, ArticleStatus, Image, ImageType

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="<p>Test body</p>",
            status=ArticleStatus.DRAFT,
        )

        mock_image = Image(
            key="image_key_123",
            url="https://d2l930y2yx77uc.cloudfront.net/production/uploads/images/123.jpg",
            original_path=str(file_path),
            uploaded_at=1234567890,
            image_type=ImageType.BODY,
        )

        with (
            patch("note_mcp.browser.insert_image.get_article_raw_html") as mock_get,
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
            patch("note_mcp.browser.insert_image.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_update.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="Save failed",
            )

            with pytest.raises(NoteAPIError) as exc_info:
                await insert_image_via_api(
                    session=session,
                    article_id="12345",
                    file_path=str(file_path),
                )

            assert exc_info.value.code == ErrorCode.API_ERROR

    @pytest.mark.asyncio
    async def test_insert_image_via_api_file_not_found(self) -> None:
        """Test API insertion fails when file not found."""
        from note_mcp.browser.insert_image import insert_image_via_api

        session = create_mock_session()

        with pytest.raises(NoteAPIError) as exc_info:
            await insert_image_via_api(
                session=session,
                article_id="12345",
                file_path="/nonexistent/file.jpg",
            )

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_insert_image_via_api_invalid_article_id(self, tmp_path: Path) -> None:
        """Test API insertion fails when article ID is invalid."""
        from note_mcp.browser.insert_image import insert_image_via_api

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        with patch("note_mcp.browser.insert_image.get_article_raw_html") as mock_get:
            mock_get.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="API request failed with status 400",
            )

            with pytest.raises(NoteAPIError) as exc_info:
                await insert_image_via_api(
                    session=session,
                    article_id="invalid_id",
                    file_path=str(file_path),
                )

            assert exc_info.value.code == ErrorCode.INVALID_INPUT
            assert "invalid_id" in exc_info.value.message.lower()
            assert "verify" in exc_info.value.message.lower()


# =============================================================================
# Issue #114: API-only Image Insertion Tests
# =============================================================================


class TestGenerateImageHtml:
    """Tests for generate_image_html function (Issue #114)."""

    def test_generate_basic_html(self) -> None:
        """Test generating basic image HTML without caption."""
        from note_mcp.api.articles import generate_image_html

        result = generate_image_html(
            image_url="https://example.com/image.jpg",
        )

        assert "<figure" in result
        assert 'src="https://example.com/image.jpg"' in result
        assert "<figcaption></figcaption>" in result
        assert 'width="620"' in result
        assert 'height="457"' in result
        assert 'contenteditable="false"' in result
        assert 'draggable="false"' in result

    def test_generate_html_with_caption(self) -> None:
        """Test generating image HTML with caption."""
        from note_mcp.api.articles import generate_image_html

        result = generate_image_html(
            image_url="https://example.com/image.jpg",
            caption="Test caption",
        )

        assert "<figcaption>Test caption</figcaption>" in result

    def test_generate_html_with_custom_dimensions(self) -> None:
        """Test generating image HTML with custom dimensions."""
        from note_mcp.api.articles import generate_image_html

        result = generate_image_html(
            image_url="https://example.com/image.jpg",
            width=800,
            height=600,
        )

        assert 'width="800"' in result
        assert 'height="600"' in result

    def test_html_contains_uuid(self) -> None:
        """Test that generated HTML contains valid UUID in name and id attributes."""
        import re

        from note_mcp.api.articles import generate_image_html

        result = generate_image_html(
            image_url="https://example.com/image.jpg",
        )

        # Extract name and id attributes
        uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
        name_match = re.search(rf'name="({uuid_pattern})"', result)
        id_match = re.search(rf'id="({uuid_pattern})"', result)

        assert name_match is not None, "name attribute should contain a UUID"
        assert id_match is not None, "id attribute should contain a UUID"
        assert name_match.group(1) == id_match.group(1), "name and id should match"

    def test_html_matches_note_format(self) -> None:
        """Test that HTML matches note.com expected format."""
        from note_mcp.api.articles import generate_image_html

        result = generate_image_html(
            image_url="https://cdn.note.com/image.jpg",
            caption="キャプション",
        )

        # Verify structure matches note.com format
        assert result.startswith("<figure")
        assert "<img " in result
        assert result.endswith("</figure>")
        # Check order: figure > img > figcaption > /figure
        img_pos = result.find("<img ")
        figcaption_pos = result.find("<figcaption>")
        assert img_pos < figcaption_pos


class TestAppendImageToBody:
    """Tests for append_image_to_body function (Issue #114)."""

    def test_append_to_empty_body(self) -> None:
        """Test appending image to empty body."""
        from note_mcp.api.articles import append_image_to_body

        image_html = '<figure name="uuid" id="uuid"><img src="test.jpg"></figure>'
        result = append_image_to_body("", image_html)

        assert result == image_html

    def test_append_to_existing_body(self) -> None:
        """Test appending image to body with existing content."""
        from note_mcp.api.articles import append_image_to_body

        existing_body = "<p>Existing content</p>"
        image_html = '<figure name="uuid" id="uuid"><img src="test.jpg"></figure>'
        result = append_image_to_body(existing_body, image_html)

        assert result == existing_body + image_html
        assert result.startswith("<p>Existing content</p>")
        assert result.endswith("</figure>")

    def test_multiple_appends(self) -> None:
        """Test appending multiple images sequentially."""
        from note_mcp.api.articles import append_image_to_body

        body = "<p>Start</p>"
        image1 = '<figure id="1"><img src="img1.jpg"></figure>'
        image2 = '<figure id="2"><img src="img2.jpg"></figure>'

        body = append_image_to_body(body, image1)
        body = append_image_to_body(body, image2)

        assert "<p>Start</p>" in body
        assert 'src="img1.jpg"' in body
        assert 'src="img2.jpg"' in body
        assert body.index("img1.jpg") < body.index("img2.jpg")


class TestGetArticleRawHtml:
    """Tests for get_article_raw_html function (Issue #114)."""

    @pytest.mark.asyncio
    async def test_get_article_returns_html_body(self) -> None:
        """Test that get_article_raw_html returns HTML body without conversion."""
        from note_mcp.api.articles import get_article_raw_html

        session = create_mock_session()

        mock_response = {
            "data": {
                "id": "12345",
                "key": "n12345abcdef",
                "name": "Test Article",
                "body": "<p>HTML content</p><figure><img src='test.jpg'></figure>",
                "status": "draft",
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await get_article_raw_html(session, "12345")

            assert result.id == "12345"
            assert result.key == "n12345abcdef"
            # Body should be raw HTML, not converted to Markdown
            assert "<p>HTML content</p>" in result.body
            assert "<figure>" in result.body

    @pytest.mark.asyncio
    async def test_get_article_with_key_format(self) -> None:
        """Test get_article_raw_html with key format article ID."""
        from note_mcp.api.articles import get_article_raw_html

        session = create_mock_session()

        mock_response = {
            "data": {
                "id": "12345",
                "key": "n12345abcdef",
                "name": "Test Article",
                "body": "<p>Content</p>",
                "status": "draft",
            }
        }

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await get_article_raw_html(session, "n12345abcdef")

            mock_client.get.assert_called_once_with("/v3/notes/n12345abcdef")
            assert result.id == "12345"


class TestUpdateArticleRawHtml:
    """Tests for update_article_raw_html function (Issue #114)."""

    @pytest.mark.asyncio
    async def test_update_article_with_html_body(self) -> None:
        """Test that update_article_raw_html saves HTML body without conversion."""
        from note_mcp.api.articles import update_article_raw_html

        session = create_mock_session()

        html_body = "<p>Updated content</p><figure><img src='new.jpg'></figure>"

        mock_response = {
            "data": {
                "id": "12345",
                "key": "n12345abcdef",
                "name": "Updated Title",
                "body": html_body,
                "status": "draft",
            }
        }

        with (
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles._resolve_numeric_note_id") as mock_resolve,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_resolve.return_value = "12345"

            result = await update_article_raw_html(
                session=session,
                article_id="12345",
                title="Updated Title",
                html_body=html_body,
            )

            # Verify API was called with raw HTML body
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["body"] == html_body
            assert payload["name"] == "Updated Title"
            assert result.id == "12345"

    @pytest.mark.asyncio
    async def test_update_article_with_tags(self) -> None:
        """Test update_article_raw_html with tags."""
        from note_mcp.api.articles import update_article_raw_html

        session = create_mock_session()

        mock_response = {
            "data": {
                "id": "12345",
                "key": "n12345abcdef",
                "name": "Title",
                "body": "<p>Content</p>",
                "status": "draft",
            }
        }

        with (
            patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles._resolve_numeric_note_id") as mock_resolve,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_resolve.return_value = "12345"

            await update_article_raw_html(
                session=session,
                article_id="12345",
                title="Title",
                html_body="<p>Content</p>",
                tags=["tag1", "#tag2"],
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            # Tags should be normalized (# removed)
            assert payload["hashtags"] == [
                {"hashtag": {"name": "tag1"}},
                {"hashtag": {"name": "tag2"}},
            ]


class TestInsertImageViaApiOnly:
    """Tests for new API-only insert_image_via_api function (Issue #114)."""

    @pytest.mark.asyncio
    async def test_api_only_insertion_success(self, tmp_path: Path) -> None:
        """Test successful API-only image insertion without Playwright."""
        from note_mcp.browser.insert_image import insert_image_via_api
        from note_mcp.models import Article, ArticleStatus, Image, ImageType

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="<p>Existing content</p>",
            status=ArticleStatus.DRAFT,
        )

        mock_image = Image(
            key="image_key_123",
            url="https://cdn.note.com/images/123.jpg",
            original_path=str(file_path),
            uploaded_at=1234567890,
            image_type=ImageType.BODY,
        )

        mock_updated_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="<p>Existing content</p><figure><img src='...'></figure>",
            status=ArticleStatus.DRAFT,
        )

        with (
            patch("note_mcp.browser.insert_image.get_article_raw_html") as mock_get,
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
            patch("note_mcp.browser.insert_image.generate_image_html") as mock_gen,
            patch("note_mcp.browser.insert_image.append_image_to_body") as mock_append,
            patch("note_mcp.browser.insert_image.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_gen.return_value = "<figure><img src='test'></figure>"
            mock_append.return_value = "<p>Existing content</p><figure><img src='test'></figure>"
            mock_update.return_value = mock_updated_article

            result = await insert_image_via_api(
                session=session,
                article_id="12345",
                file_path=str(file_path),
                caption="Test caption",
            )

            assert result["success"] is True
            assert result["article_id"] == "12345"
            assert result["article_key"] == "n12345abcdef"
            assert result["image_url"] == mock_image.url
            assert result["fallback_used"] is False

            # Verify API-only flow was used
            mock_get.assert_called_once()
            mock_upload.assert_called_once()
            mock_gen.assert_called_once()
            mock_append.assert_called_once()
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_only_no_playwright_dependency(self, tmp_path: Path) -> None:
        """Verify no Playwright/browser calls are made in API-only mode."""
        from note_mcp.browser.insert_image import insert_image_via_api
        from note_mcp.models import Article, ArticleStatus, Image, ImageType

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="<p>Content</p>",
            status=ArticleStatus.DRAFT,
        )

        mock_image = Image(
            key="image_key_123",
            url="https://cdn.note.com/images/123.jpg",
            original_path=str(file_path),
            uploaded_at=1234567890,
            image_type=ImageType.BODY,
        )

        with (
            patch("note_mcp.browser.insert_image.get_article_raw_html") as mock_get,
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
            patch("note_mcp.browser.insert_image.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_update.return_value = mock_article

            result = await insert_image_via_api(
                session=session,
                article_id="12345",
                file_path=str(file_path),
            )

            # API-only mode: no Playwright, no fallback
            assert result["success"] is True
            assert result["fallback_used"] is False

            # All API functions should be called
            mock_get.assert_called_once()
            mock_upload.assert_called_once()
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_only_with_caption(self, tmp_path: Path) -> None:
        """Test API-only insertion passes caption to generate_image_html."""
        from note_mcp.browser.insert_image import insert_image_via_api
        from note_mcp.models import Article, ArticleStatus, Image, ImageType

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="<p>Content</p>",
            status=ArticleStatus.DRAFT,
        )

        mock_image = Image(
            key="image_key_123",
            url="https://cdn.note.com/images/123.jpg",
            original_path=str(file_path),
            uploaded_at=1234567890,
            image_type=ImageType.BODY,
        )

        with (
            patch("note_mcp.browser.insert_image.get_article_raw_html") as mock_get,
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
            patch("note_mcp.browser.insert_image.generate_image_html") as mock_gen,
            patch("note_mcp.browser.insert_image.append_image_to_body") as mock_append,
            patch("note_mcp.browser.insert_image.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_gen.return_value = "<figure><img><figcaption>My Caption</figcaption></figure>"
            mock_append.return_value = "<p>Content</p><figure>...</figure>"
            mock_update.return_value = mock_article

            await insert_image_via_api(
                session=session,
                article_id="12345",
                file_path=str(file_path),
                caption="My Caption",
            )

            # Verify caption was passed to generate_image_html
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs.get("caption") == "My Caption"
