"""Unit tests for image upload."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.api.images import (
    ALLOWED_EXTENSIONS,
    IMAGE_UPLOAD_ENDPOINTS,
    MAX_FILE_SIZE,
    upload_body_image,
    upload_eyecatch_image,
    validate_image_file,
)
from note_mcp.models import ErrorCode, ImageType, NoteAPIError, Session

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


class TestImageType:
    """Tests for ImageType enum."""

    def test_image_type_values(self) -> None:
        """Test ImageType enum values."""
        assert ImageType.EYECATCH.value == "eyecatch"
        assert ImageType.BODY.value == "body"

    def test_image_upload_endpoints(self) -> None:
        """Test that endpoints are defined for all image types."""
        assert ImageType.EYECATCH in IMAGE_UPLOAD_ENDPOINTS
        assert ImageType.BODY in IMAGE_UPLOAD_ENDPOINTS
        assert "eyecatch" in IMAGE_UPLOAD_ENDPOINTS[ImageType.EYECATCH]
        # Body images use the same eyecatch endpoint (note.com API limitation)
        assert "eyecatch" in IMAGE_UPLOAD_ENDPOINTS[ImageType.BODY]


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


class TestUploadEyecatchImage:
    """Tests for upload_eyecatch_image function."""

    @pytest.mark.asyncio
    async def test_upload_eyecatch_image_success(self, tmp_path: Path) -> None:
        """Test successful eyecatch image upload."""
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

            image = await upload_eyecatch_image(session, str(file_path), note_id="12345")

            assert image.key == "img_123456"
            assert "note.com" in image.url
            assert image.original_path == str(file_path)
            assert image.image_type == ImageType.EYECATCH

    @pytest.mark.asyncio
    async def test_upload_eyecatch_image_uses_correct_endpoint(self, tmp_path: Path) -> None:
        """Test that eyecatch upload uses the correct endpoint."""
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

            await upload_eyecatch_image(session, str(file_path), note_id="12345")

            # Verify endpoint contains "eyecatch"
            call_args = mock_client.post.call_args
            endpoint = call_args[0][0]
            assert "eyecatch" in endpoint

    @pytest.mark.asyncio
    async def test_upload_eyecatch_image_with_size(self, tmp_path: Path) -> None:
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

            image = await upload_eyecatch_image(session, str(file_path), note_id="12345")

            assert image.size_bytes == len(content)

    @pytest.mark.asyncio
    async def test_upload_eyecatch_image_validates_file(self, tmp_path: Path) -> None:
        """Test that upload validates file before sending."""
        session = create_mock_session()
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"not an image")

        with pytest.raises(NoteAPIError) as exc_info:
            await upload_eyecatch_image(session, str(file_path), note_id="12345")

        assert exc_info.value.code == ErrorCode.INVALID_INPUT


class TestUploadBodyImage:
    """Tests for upload_body_image function.

    Body image upload uses the presigned_post flow:
    1. POST to /v3/images/upload/presigned_post to get S3 presigned URL
    2. Upload file directly to S3 using the presigned URL
    """

    @pytest.mark.asyncio
    async def test_upload_body_image_success(self, tmp_path: Path) -> None:
        """Test successful body image upload using presigned_post flow."""
        session = create_mock_session()
        file_path = tmp_path / "test.png"
        file_path.write_bytes(b"\x89PNG" + b"x" * 100)

        # Mock response from /v3/images/upload/presigned_post
        presigned_response = {
            "data": {
                "action": "https://s3.amazonaws.com/note-images",
                "url": "https://assets.note.com/images/img_789012.png",
                "post": {
                    "key": "img_789012",
                    "acl": "public-read",
                    "Expires": "2024-12-31T23:59:59Z",
                    "policy": "base64policy",
                    "x-amz-credential": "AKIAIOSFODNN7EXAMPLE",
                    "x-amz-algorithm": "AWS4-HMAC-SHA256",
                    "x-amz-date": "20241220T000000Z",
                    "x-amz-signature": "signature123",
                },
            }
        }

        # Mock S3 response
        mock_s3_response = AsyncMock()
        mock_s3_response.is_success = True
        mock_s3_response.status_code = 204

        with (
            patch("note_mcp.api.images.NoteAPIClient") as mock_client_class,
            patch("httpx.AsyncClient") as mock_httpx_class,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=presigned_response)

            mock_http_client = AsyncMock()
            mock_httpx_class.return_value = mock_http_client
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_s3_response)

            image = await upload_body_image(session, str(file_path), note_id="12345")

            assert image.key == "img_789012"
            assert "note.com" in image.url
            assert image.original_path == str(file_path)
            assert image.image_type == ImageType.BODY

    @pytest.mark.asyncio
    async def test_upload_body_image_uses_presigned_post_endpoint(self, tmp_path: Path) -> None:
        """Test that body upload uses the presigned_post endpoint."""
        session = create_mock_session()
        file_path = tmp_path / "test.png"
        file_path.write_bytes(b"\x89PNG" + b"x" * 100)

        presigned_response = {
            "data": {
                "action": "https://s3.amazonaws.com/note-images",
                "url": "https://assets.note.com/images/img_789012.png",
                "post": {
                    "key": "img_789012",
                    "acl": "public-read",
                    "Expires": "2024-12-31T23:59:59Z",
                    "policy": "base64policy",
                    "x-amz-credential": "AKIAIOSFODNN7EXAMPLE",
                    "x-amz-algorithm": "AWS4-HMAC-SHA256",
                    "x-amz-date": "20241220T000000Z",
                    "x-amz-signature": "signature123",
                },
            }
        }

        mock_s3_response = AsyncMock()
        mock_s3_response.is_success = True
        mock_s3_response.status_code = 204

        with (
            patch("note_mcp.api.images.NoteAPIClient") as mock_client_class,
            patch("httpx.AsyncClient") as mock_httpx_class,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=presigned_response)

            mock_http_client = AsyncMock()
            mock_httpx_class.return_value = mock_http_client
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_s3_response)

            await upload_body_image(session, str(file_path), note_id="12345")

            # Verify presigned_post endpoint is used
            call_args = mock_client.post.call_args
            endpoint = call_args[0][0]
            assert "presigned_post" in endpoint

    @pytest.mark.asyncio
    async def test_upload_body_image_uploads_to_s3(self, tmp_path: Path) -> None:
        """Test that file is uploaded to S3 using presigned URL."""
        session = create_mock_session()
        file_path = tmp_path / "test.png"
        file_path.write_bytes(b"\x89PNG" + b"x" * 100)

        presigned_response = {
            "data": {
                "action": "https://s3.amazonaws.com/note-images",
                "url": "https://assets.note.com/images/img_789012.png",
                "post": {
                    "key": "img_789012",
                    "acl": "public-read",
                    "Expires": "2024-12-31T23:59:59Z",
                    "policy": "base64policy",
                    "x-amz-credential": "AKIAIOSFODNN7EXAMPLE",
                    "x-amz-algorithm": "AWS4-HMAC-SHA256",
                    "x-amz-date": "20241220T000000Z",
                    "x-amz-signature": "signature123",
                },
            }
        }

        mock_s3_response = AsyncMock()
        mock_s3_response.is_success = True
        mock_s3_response.status_code = 204

        with (
            patch("note_mcp.api.images.NoteAPIClient") as mock_client_class,
            patch("httpx.AsyncClient") as mock_httpx_class,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=presigned_response)

            mock_http_client = AsyncMock()
            mock_httpx_class.return_value = mock_http_client
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_s3_response)

            await upload_body_image(session, str(file_path), note_id="12345")

            # Verify S3 upload was called with presigned URL
            mock_http_client.post.assert_called_once()
            s3_call_args = mock_http_client.post.call_args
            s3_url = s3_call_args[0][0]
            assert "s3.amazonaws.com" in s3_url
            # Verify files parameter is passed
            assert "files" in s3_call_args[1]

    @pytest.mark.asyncio
    async def test_upload_body_image_api_error(self, tmp_path: Path) -> None:
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
                await upload_body_image(session, str(file_path), note_id="12345")

            assert exc_info.value.code == ErrorCode.API_ERROR


class TestImageUploadArticle6Compliance:
    """Tests for Article 6 (Data Accuracy Mandate) compliance in image upload.

    Article 6 requires:
    - No implicit fallback to default values for required fields
    - Missing 'url' should raise NoteAPIError (required field)
    - Missing 'key' is acceptable for eyecatch API (optional field)
    """

    @pytest.mark.asyncio
    async def test_upload_image_succeeds_without_key(self, tmp_path: Path) -> None:
        """Eyecatch upload should succeed when API response is missing 'key'.

        Note: note.com eyecatch API doesn't return 'key' field, only 'url'.
        This is documented API behavior, not a missing field error.
        """
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        # Response without 'key' field (actual eyecatch API behavior)
        mock_response = {
            "data": {
                "url": "https://assets.note.com/images/img_123456.jpg",
            }
        }

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await upload_eyecatch_image(session, str(file_path), note_id="12345")

            assert result.url == "https://assets.note.com/images/img_123456.jpg"
            assert result.key is None  # eyecatch API doesn't return key

    @pytest.mark.asyncio
    async def test_upload_image_raises_on_missing_url(self, tmp_path: Path) -> None:
        """Eyecatch upload should raise error when API response is missing 'url'."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        # Response missing 'url' field
        mock_response = {
            "data": {
                "key": "img_123456",
            }
        }

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(NoteAPIError) as exc_info:
                await upload_eyecatch_image(session, str(file_path), note_id="12345")

            assert exc_info.value.code == ErrorCode.API_ERROR
            assert "url" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_upload_image_raises_on_empty_data(self, tmp_path: Path) -> None:
        """Eyecatch upload should raise error when API response data is empty."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        # Response with empty data
        mock_response: dict[str, dict[str, str]] = {"data": {}}

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(NoteAPIError) as exc_info:
                await upload_eyecatch_image(session, str(file_path), note_id="12345")

            assert exc_info.value.code == ErrorCode.API_ERROR


class TestUploadBodyImageArticle6Compliance:
    """Tests for Article 6 compliance in upload_body_image S3 presigned POST.

    Article 6 requires:
    - No implicit fallback to default values for required S3 fields
    - Missing required S3 fields should raise NoteAPIError
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "missing_field",
        [
            "key",
            "policy",
            "x-amz-credential",
            "x-amz-algorithm",
            "x-amz-date",
            "x-amz-signature",
        ],
    )
    async def test_upload_body_image_raises_on_missing_s3_field(self, tmp_path: Path, missing_field: str) -> None:
        """Upload should raise error when required S3 field is missing."""
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        # Complete post fields minus the missing field
        complete_post_fields = {
            "key": "img_789012",
            "acl": "public-read",
            "Expires": "2024-12-31T23:59:59Z",
            "policy": "base64policy",
            "x-amz-credential": "AKIAIOSFODNN7EXAMPLE",
            "x-amz-algorithm": "AWS4-HMAC-SHA256",
            "x-amz-date": "20241220T000000Z",
            "x-amz-signature": "signature123",
        }
        # Remove the field being tested
        del complete_post_fields[missing_field]

        presigned_response = {
            "data": {
                "action": "https://s3.amazonaws.com/note-images",
                "url": "https://assets.note.com/images/img_789012.png",
                "post": complete_post_fields,
            }
        }

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=presigned_response)

            with pytest.raises(NoteAPIError) as exc_info:
                await upload_body_image(session, str(file_path), note_id="12345")

            assert exc_info.value.code == ErrorCode.API_ERROR
            assert missing_field in exc_info.value.message
            assert "S3 field" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_body_image_raises_on_empty_post_fields(self, tmp_path: Path) -> None:
        """Upload should raise error when post fields dict is empty.

        Note: Empty dict is falsy in Python, so it's caught by the earlier
        validation check (not post_fields) before reaching S3 field validation.
        """
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        presigned_response = {
            "data": {
                "action": "https://s3.amazonaws.com/note-images",
                "url": "https://assets.note.com/images/img_789012.png",
                "post": {},
            }
        }

        with patch("note_mcp.api.images.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=presigned_response)

            with pytest.raises(NoteAPIError) as exc_info:
                await upload_body_image(session, str(file_path), note_id="12345")

            assert exc_info.value.code == ErrorCode.API_ERROR
            # Empty post dict is caught early by "if not post_fields" check
            assert "presigned URL" in exc_info.value.message
