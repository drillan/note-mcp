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
    """Tests for insert_image_via_api function (Issue #111 API-based image insertion)."""

    @pytest.mark.asyncio
    async def test_insert_image_via_api_success(self, tmp_path: Path) -> None:
        """Test successful image insertion via API + ProseMirror."""
        from note_mcp.browser.insert_image import insert_image_via_api
        from note_mcp.models import Article, ArticleStatus, Image, ImageType

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="Test body",
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
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
            patch("note_mcp.browser.insert_image.get_article") as mock_get_article,
            patch("note_mcp.browser.insert_image._setup_page_with_session") as mock_setup,
            patch("note_mcp.browser.insert_image._insert_image_via_prosemirror") as mock_insert,
            patch("note_mcp.browser.insert_image._input_image_caption") as mock_caption,
            patch("note_mcp.browser.insert_image._save_article") as mock_save,
        ):
            mock_upload.return_value = mock_image
            mock_get_article.return_value = mock_article
            mock_setup.return_value = AsyncMock()
            mock_insert.return_value = True
            mock_caption.return_value = True
            mock_save.return_value = True

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

            mock_upload.assert_called_once()
            mock_get_article.assert_called_once_with(session, "12345")
            mock_insert.assert_called_once()
            mock_save.assert_called_once()

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
            body="Test body",
            status=ArticleStatus.DRAFT,
        )

        with (
            patch("note_mcp.browser.insert_image.get_article") as mock_get_article,
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
        ):
            mock_get_article.return_value = mock_article
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
    async def test_insert_image_via_api_prosemirror_fallback(self, tmp_path: Path) -> None:
        """Test fallback to browser UI when ProseMirror insertion fails."""
        from note_mcp.browser.insert_image import insert_image_via_api
        from note_mcp.models import Article, ArticleStatus, Image, ImageType

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_article = Article(
            id="12345",
            key="n12345abcdef",
            title="Test Article",
            body="Test body",
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
            patch("note_mcp.browser.insert_image.upload_body_image") as mock_upload,
            patch("note_mcp.browser.insert_image.get_article") as mock_get_article,
            patch("note_mcp.browser.insert_image._setup_page_with_session") as mock_setup,
            patch("note_mcp.browser.insert_image._insert_image_via_prosemirror") as mock_insert,
            patch("note_mcp.browser.insert_image._click_add_image_button") as mock_click,
            patch("note_mcp.browser.insert_image._upload_image_via_file_chooser") as mock_upload_ui,
            patch("note_mcp.browser.insert_image._wait_for_image_insertion") as mock_wait,
            patch("note_mcp.browser.insert_image._save_article") as mock_save,
        ):
            mock_upload.return_value = mock_image
            mock_get_article.return_value = mock_article
            mock_page = AsyncMock()
            mock_page.evaluate = AsyncMock(return_value=0)
            mock_setup.return_value = mock_page
            mock_insert.return_value = False  # ProseMirror fails
            mock_click.return_value = True
            mock_upload_ui.return_value = True
            mock_wait.return_value = True
            mock_save.return_value = True

            result = await insert_image_via_api(
                session=session,
                article_id="12345",
                file_path=str(file_path),
            )

            assert result["success"] is True
            assert result["fallback_used"] is True
            mock_insert.assert_called_once()  # ProseMirror attempted
            mock_click.assert_called_once()  # Fallback to browser UI

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

        with patch("note_mcp.browser.insert_image.get_article") as mock_get_article:
            mock_get_article.side_effect = NoteAPIError(
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
