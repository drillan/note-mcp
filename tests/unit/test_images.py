"""Unit tests for image upload."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.api.images import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    upload_image,
    validate_image_file,
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


class TestValidateImageFile:
    """Tests for validate_image_file function."""

    def test_validate_jpeg_file(self, tmp_path: Path) -> None:
        """Test validation of JPEG file."""
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)  # JPEG magic bytes

        validate_image_file(str(file_path))  # Should not raise

    def test_validate_png_file(self, tmp_path: Path) -> None:
        """Test validation of PNG file."""
        file_path = tmp_path / "test.png"
        file_path.write_bytes(b"\x89PNG" + b"x" * 100)  # PNG magic bytes

        validate_image_file(str(file_path))  # Should not raise

    def test_validate_gif_file(self, tmp_path: Path) -> None:
        """Test validation of GIF file."""
        file_path = tmp_path / "test.gif"
        file_path.write_bytes(b"GIF89a" + b"x" * 100)  # GIF magic bytes

        validate_image_file(str(file_path))  # Should not raise

    def test_validate_webp_file(self, tmp_path: Path) -> None:
        """Test validation of WebP file."""
        file_path = tmp_path / "test.webp"
        file_path.write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"x" * 100)  # WebP magic

        validate_image_file(str(file_path))  # Should not raise

    def test_validate_file_not_found(self) -> None:
        """Test validation raises error for non-existent file."""
        with pytest.raises(NoteAPIError) as exc_info:
            validate_image_file("/nonexistent/file.jpg")

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "not found" in exc_info.value.message.lower()

    def test_validate_invalid_extension(self, tmp_path: Path) -> None:
        """Test validation raises error for invalid extension."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"text content")

        with pytest.raises(NoteAPIError) as exc_info:
            validate_image_file(str(file_path))

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "format" in exc_info.value.message.lower()

    def test_validate_file_too_large(self, tmp_path: Path) -> None:
        """Test validation raises error for file exceeding size limit."""
        file_path = tmp_path / "test.jpg"
        # Create file larger than MAX_FILE_SIZE
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * (MAX_FILE_SIZE + 1))

        with pytest.raises(NoteAPIError) as exc_info:
            validate_image_file(str(file_path))

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "size" in exc_info.value.message.lower()

    def test_allowed_extensions_contains_expected(self) -> None:
        """Test that allowed extensions include expected formats."""
        expected = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        assert expected.issubset(ALLOWED_EXTENSIONS)


class TestUploadImage:
    """Tests for upload_image function."""

    @pytest.mark.asyncio
    async def test_upload_image_success(self, tmp_path: Path) -> None:
        """Test successful image upload."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        mock_response = {
            "data": {
                "key": "img_123456",
                "url": "https://assets.note.com/images/img_123456.jpg",
            }
        }

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            image = await upload_image(session, str(file_path))

            assert image.key == "img_123456"
            assert "note.com" in image.url
            assert image.original_path == str(file_path)

    @pytest.mark.asyncio
    async def test_upload_image_with_size(self, tmp_path: Path) -> None:
        """Test that upload includes file size."""
        session = create_mock_session()
        content = b"\xff\xd8\xff" + b"x" * 500
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(content)

        mock_response = {
            "data": {
                "key": "img_123456",
                "url": "https://assets.note.com/images/img_123456.jpg",
            }
        }

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            image = await upload_image(session, str(file_path))

            assert image.size_bytes == len(content)

    @pytest.mark.asyncio
    async def test_upload_image_validates_file(self, tmp_path: Path) -> None:
        """Test that upload validates file before sending."""
        session = create_mock_session()
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"not an image")

        with pytest.raises(NoteAPIError) as exc_info:
            await upload_image(session, str(file_path))

        assert exc_info.value.code == ErrorCode.INVALID_INPUT

    @pytest.mark.asyncio
    async def test_upload_image_sends_multipart(self, tmp_path: Path) -> None:
        """Test that upload uses multipart/form-data."""
        session = create_mock_session()
        file_path = tmp_path / "test.png"
        file_path.write_bytes(b"\x89PNG" + b"x" * 100)

        mock_response = {
            "data": {
                "key": "img_123456",
                "url": "https://assets.note.com/images/img_123456.png",
            }
        }

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            await upload_image(session, str(file_path))

            # Verify that post was called with files parameter
            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args[1]
            assert "files" in call_kwargs

    @pytest.mark.asyncio
    async def test_upload_image_api_error(self, tmp_path: Path) -> None:
        """Test that API errors are propagated."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            # Return False to propagate exception (not suppress it)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=NoteAPIError(
                    code=ErrorCode.API_ERROR,
                    message="Upload failed",
                )
            )

            with pytest.raises(NoteAPIError) as exc_info:
                await upload_image(session, str(file_path))

            assert exc_info.value.code == ErrorCode.API_ERROR
