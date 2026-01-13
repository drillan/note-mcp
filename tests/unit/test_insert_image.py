"""Unit tests for API-based image insertion."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.api.images import insert_image_via_api
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


class TestInsertImageViaApi:
    """Tests for insert_image_via_api function (Issue #114 API-only image insertion)."""

    @pytest.mark.asyncio
    async def test_insert_image_via_api_success(self, tmp_path: Path) -> None:
        """Test successful image insertion via API-only (no Playwright)."""
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
            patch("note_mcp.api.articles.get_article_raw_html") as mock_get,
            patch("note_mcp.api.images.upload_body_image") as mock_upload,
            patch("note_mcp.api.articles.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_update.return_value = mock_updated_article

            # Use key format to bypass numeric ID resolution (tested in Issue #147)
            result = await insert_image_via_api(
                session=session,
                article_id="n12345abcdef",  # Key format
                file_path=str(file_path),
                caption="Test caption",
            )

            assert result["success"] is True
            assert result["article_id"] == "12345"
            assert result["article_key"] == "n12345abcdef"
            assert result["image_url"] == mock_image.url
            assert result["fallback_used"] is False  # API-only mode

            mock_get.assert_called_once_with(session, "n12345abcdef")
            mock_upload.assert_called_once()
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_image_via_api_upload_fails(self, tmp_path: Path) -> None:
        """Test API insertion fails when image upload fails."""
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
            patch("note_mcp.api.articles.get_article_raw_html") as mock_get,
            patch("note_mcp.api.images.upload_body_image") as mock_upload,
        ):
            mock_get.return_value = mock_article
            mock_upload.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="Upload failed",
            )

            with pytest.raises(NoteAPIError) as exc_info:
                # Use key format to bypass numeric ID resolution (tested in Issue #147)
                await insert_image_via_api(
                    session=session,
                    article_id="n12345abcdef",  # Key format
                    file_path=str(file_path),
                )

            assert exc_info.value.code == ErrorCode.API_ERROR

    @pytest.mark.asyncio
    async def test_insert_image_via_api_update_fails(self, tmp_path: Path) -> None:
        """Test API insertion fails when article update fails."""
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
            patch("note_mcp.api.articles.get_article_raw_html") as mock_get,
            patch("note_mcp.api.images.upload_body_image") as mock_upload,
            patch("note_mcp.api.articles.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_update.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="Save failed",
            )

            with pytest.raises(NoteAPIError) as exc_info:
                # Use key format to bypass numeric ID resolution (tested in Issue #147)
                await insert_image_via_api(
                    session=session,
                    article_id="n12345abcdef",  # Key format
                    file_path=str(file_path),
                )

            assert exc_info.value.code == ErrorCode.API_ERROR

    @pytest.mark.asyncio
    async def test_insert_image_via_api_file_not_found(self) -> None:
        """Test API insertion fails when file not found."""
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
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        with patch("note_mcp.api.articles.get_article_raw_html") as mock_get:
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

    def test_xss_prevention_in_caption(self) -> None:
        """Test that caption is HTML-escaped to prevent XSS attacks."""
        from note_mcp.api.articles import generate_image_html

        result = generate_image_html(
            image_url="https://example.com/image.jpg",
            caption="<script>alert('XSS')</script>",
        )

        # Script tags should be escaped
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "alert(&#x27;XSS&#x27;)" in result

    def test_special_characters_in_caption(self) -> None:
        """Test that special HTML characters in caption are escaped."""
        from note_mcp.api.articles import generate_image_html

        result = generate_image_html(
            image_url="https://example.com/image.jpg",
            caption='Caption with "quotes" & <brackets>',
        )

        # Special characters should be escaped
        assert "&quot;" in result
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_xss_prevention_in_url(self) -> None:
        """Test that URL is HTML-escaped to prevent XSS attacks."""
        from note_mcp.api.articles import generate_image_html

        result = generate_image_html(
            image_url='javascript:alert("XSS")',
            caption="",
        )

        # URL should be escaped
        assert 'javascript:alert("XSS")' not in result
        assert "javascript:alert(&quot;XSS&quot;)" in result


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
                "result": "saved",  # draft_save returns result, not id
                "note_days_count": 1,
                "updated_at": 1234567890,
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
                "result": "saved",  # draft_save returns result, not id
                "note_days_count": 1,
                "updated_at": 1234567890,
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

    @pytest.mark.asyncio
    async def test_update_article_empty_response_raises_error(self) -> None:
        """Test that empty API response raises NoteAPIError."""
        from note_mcp.api.articles import update_article_raw_html

        session = create_mock_session()

        # Empty data in response
        mock_response: dict[str, dict[str, str]] = {"data": {}}

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

            with pytest.raises(NoteAPIError) as exc_info:
                await update_article_raw_html(
                    session=session,
                    article_id="12345",
                    title="Title",
                    html_body="<p>Content</p>",
                )

            assert exc_info.value.code == ErrorCode.API_ERROR
            assert "empty response" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_update_article_response_missing_id_raises_error(self) -> None:
        """Test that response without id field raises NoteAPIError."""
        from note_mcp.api.articles import update_article_raw_html

        session = create_mock_session()

        # Response with data but no id field
        mock_response = {"data": {"name": "Title", "body": "<p>Content</p>"}}

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

            with pytest.raises(NoteAPIError) as exc_info:
                await update_article_raw_html(
                    session=session,
                    article_id="12345",
                    title="Title",
                    html_body="<p>Content</p>",
                )

            assert exc_info.value.code == ErrorCode.API_ERROR
            assert "empty response" in exc_info.value.message.lower()


class TestInsertImageViaApiOnly:
    """Tests for new API-only insert_image_via_api function (Issue #114)."""

    @pytest.mark.asyncio
    async def test_api_only_insertion_success(self, tmp_path: Path) -> None:
        """Test successful API-only image insertion without Playwright."""
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
            patch("note_mcp.api.articles.get_article_raw_html") as mock_get,
            patch("note_mcp.api.images.upload_body_image") as mock_upload,
            patch("note_mcp.api.articles.generate_image_html") as mock_gen,
            patch("note_mcp.api.articles.append_image_to_body") as mock_append,
            patch("note_mcp.api.articles.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_gen.return_value = "<figure><img src='test'></figure>"
            mock_append.return_value = "<p>Existing content</p><figure><img src='test'></figure>"
            mock_update.return_value = mock_updated_article

            # Use key format to bypass numeric ID resolution (tested in Issue #147)
            result = await insert_image_via_api(
                session=session,
                article_id="n12345abcdef",  # Key format
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
            patch("note_mcp.api.articles.get_article_raw_html") as mock_get,
            patch("note_mcp.api.images.upload_body_image") as mock_upload,
            patch("note_mcp.api.articles.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_update.return_value = mock_article

            # Use key format to bypass numeric ID resolution (tested in Issue #147)
            result = await insert_image_via_api(
                session=session,
                article_id="n12345abcdef",  # Key format
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
            patch("note_mcp.api.articles.get_article_raw_html") as mock_get,
            patch("note_mcp.api.images.upload_body_image") as mock_upload,
            patch("note_mcp.api.articles.generate_image_html") as mock_gen,
            patch("note_mcp.api.articles.append_image_to_body") as mock_append,
            patch("note_mcp.api.articles.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_gen.return_value = "<figure><img><figcaption>My Caption</figcaption></figure>"
            mock_append.return_value = "<p>Content</p><figure>...</figure>"
            mock_update.return_value = mock_article

            # Use key format to bypass numeric ID resolution (tested in Issue #147)
            await insert_image_via_api(
                session=session,
                article_id="n12345abcdef",  # Key format
                file_path=str(file_path),
                caption="My Caption",
            )

            # Verify caption was passed to generate_image_html
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs.get("caption") == "My Caption"


# =============================================================================
# Issue #147: Numeric ID to Key Format Resolution Tests
# =============================================================================


class TestInsertImageIdResolution:
    """Tests for insert_image_via_api ID validation logic (Issue #147).

    The insert_image_via_api function:
    - Rejects numeric IDs with a clear error message
    - Requires article key format (e.g., 'n1234567890ab')
    - Works directly with key format IDs

    Note: This behavior changed from the initial plan because the /v3/notes/
    endpoint does not support numeric IDs and draft_save does not return
    the article key in its response.
    """

    @pytest.mark.asyncio
    async def test_insert_image_with_numeric_id_raises_error(self, tmp_path: Path) -> None:
        """Numeric IDs should be rejected with a clear error message.

        This is the fix for Issue #147: numeric IDs are not supported
        because /v3/notes/ API returns 400 error for numeric IDs.
        """
        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        with pytest.raises(NoteAPIError) as exc_info:
            await insert_image_via_api(
                session=session,
                article_id="12345",  # Numeric ID should be rejected
                file_path=str(file_path),
            )

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "Numeric article ID" in exc_info.value.message
        assert "n1234567890ab" in exc_info.value.message  # Suggests key format

    @pytest.mark.asyncio
    async def test_insert_image_with_key_format_direct(self, tmp_path: Path) -> None:
        """Key format ID should be used directly without draft_save resolution.

        When article_id is already in key format (starts with 'n'),
        no draft_save call is needed for key resolution.
        """
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
            patch("note_mcp.api.images.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles.get_article_raw_html") as mock_get,
            patch("note_mcp.api.images.upload_body_image") as mock_upload,
            patch("note_mcp.api.articles.update_article_raw_html") as mock_update,
        ):
            mock_get.return_value = mock_article
            mock_upload.return_value = mock_image
            mock_update.return_value = mock_article

            result = await insert_image_via_api(
                session=session,
                article_id="n12345abcdef",  # Key format
                file_path=str(file_path),
            )

            assert result["success"] is True
            assert result["article_key"] == "n12345abcdef"

            # Verify NoteAPIClient was NOT used for draft_save (key resolution)
            # The only NoteAPIClient usage should be in upload_body_image
            mock_client_class.assert_not_called()

            # Verify get_article_raw_html was called with key format directly
            mock_get.assert_called_once_with(session, "n12345abcdef")

    @pytest.mark.asyncio
    async def test_insert_image_invalid_numeric_id_error(self, tmp_path: Path) -> None:
        """Invalid numeric ID should raise appropriate error.

        When both get_article_raw_html and draft_save fail, an error should be raised
        with a clear message.
        """
        from unittest.mock import MagicMock

        session = create_mock_session()
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        # Mock draft_save response without key (invalid article)
        mock_draft_save_response: dict[str, dict[str, str]] = {"data": {}}

        with (
            patch("note_mcp.api.images.NoteAPIClient") as mock_client_class,
            patch("note_mcp.api.articles.get_article_raw_html") as mock_get,
        ):
            # First get_article_raw_html fails
            mock_get.side_effect = NoteAPIError(code=ErrorCode.API_ERROR, message="Article not found")

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_draft_save_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await insert_image_via_api(
                    session=session,
                    article_id="99999999",  # Invalid numeric ID
                    file_path=str(file_path),
                )

            assert exc_info.value.code == ErrorCode.INVALID_INPUT
            assert "99999999" in exc_info.value.message
