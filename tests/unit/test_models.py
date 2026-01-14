"""Unit tests for Pydantic models."""

import time

import pytest

from note_mcp.models import (
    Article,
    ArticleInput,
    ArticleStatus,
    ErrorCode,
    Image,
    NoteAPIError,
    Session,
    Tag,
    from_api_response,
)


class TestSession:
    """Tests for Session model."""

    def test_session_creation_with_required_fields(self) -> None:
        """Test creating a session with all required fields."""
        session = Session(
            cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
            user_id="user123",
            username="testuser",
            created_at=int(time.time()),
        )
        assert session.user_id == "user123"
        assert session.username == "testuser"
        assert "note_gql_auth_token" in session.cookies

    def test_session_is_not_expired_when_no_expiry(self) -> None:
        """Test that session without expires_at is not expired."""
        session = Session(
            cookies={"note_gql_auth_token": "token", "_note_session_v5": "session"},
            user_id="user123",
            username="testuser",
            created_at=int(time.time()),
        )
        assert session.is_expired() is False

    def test_session_is_expired_when_past_expiry(self) -> None:
        """Test that session with past expires_at is expired."""
        past_time = int(time.time()) - 3600  # 1 hour ago
        session = Session(
            cookies={"note_gql_auth_token": "token", "_note_session_v5": "session"},
            user_id="user123",
            username="testuser",
            created_at=past_time - 3600,
            expires_at=past_time,
        )
        assert session.is_expired() is True

    def test_session_is_not_expired_when_future_expiry(self) -> None:
        """Test that session with future expires_at is not expired."""
        future_time = int(time.time()) + 3600  # 1 hour from now
        session = Session(
            cookies={"note_gql_auth_token": "token", "_note_session_v5": "session"},
            user_id="user123",
            username="testuser",
            created_at=int(time.time()),
            expires_at=future_time,
        )
        assert session.is_expired() is False


class TestArticleStatus:
    """Tests for ArticleStatus enum."""

    def test_draft_status(self) -> None:
        """Test DRAFT status value."""
        assert ArticleStatus.DRAFT.value == "draft"

    def test_published_status(self) -> None:
        """Test PUBLISHED status value."""
        assert ArticleStatus.PUBLISHED.value == "published"

    def test_private_status(self) -> None:
        """Test PRIVATE status value."""
        assert ArticleStatus.PRIVATE.value == "private"


class TestArticle:
    """Tests for Article model."""

    def test_article_creation(self) -> None:
        """Test creating an article with required fields."""
        article = Article(
            id="123",
            key="my-article",
            title="Test Article",
            body="<p>Content</p>",
            status=ArticleStatus.DRAFT,
        )
        assert article.id == "123"
        assert article.key == "my-article"
        assert article.title == "Test Article"
        assert article.status == ArticleStatus.DRAFT

    def test_article_with_optional_fields(self) -> None:
        """Test creating an article with optional fields."""
        article = Article(
            id="123",
            key="my-article",
            title="Test Article",
            body="<p>Content</p>",
            status=ArticleStatus.PUBLISHED,
            tags=["python", "programming"],
            eyecatch_image_key="img123",
            url="https://note.com/user/n/my-article",
        )
        assert article.tags == ["python", "programming"]
        assert article.eyecatch_image_key == "img123"
        assert article.url == "https://note.com/user/n/my-article"

    def test_article_default_empty_tags(self) -> None:
        """Test that tags default to empty list."""
        article = Article(
            id="123",
            key="my-article",
            title="Test",
            body="<p>Content</p>",
            status=ArticleStatus.DRAFT,
        )
        assert article.tags == []


class TestArticleInput:
    """Tests for ArticleInput model."""

    def test_article_input_creation(self) -> None:
        """Test creating article input."""
        input_data = ArticleInput(
            title="My Article",
            body="# Hello\n\nThis is content.",
        )
        assert input_data.title == "My Article"
        assert input_data.body == "# Hello\n\nThis is content."
        assert input_data.tags == []

    def test_article_input_with_tags(self) -> None:
        """Test creating article input with tags."""
        input_data = ArticleInput(
            title="My Article",
            body="Content",
            tags=["python", "note"],
        )
        assert input_data.tags == ["python", "note"]

    def test_article_input_with_eyecatch(self) -> None:
        """Test creating article input with eyecatch image."""
        input_data = ArticleInput(
            title="My Article",
            body="Content",
            eyecatch_image_path="/path/to/image.png",
        )
        assert input_data.eyecatch_image_path == "/path/to/image.png"


class TestImage:
    """Tests for Image model."""

    def test_image_creation(self) -> None:
        """Test creating an image."""
        image = Image(
            key="img123",
            url="https://note.com/images/img123.png",
            original_path="/local/path/image.png",
            uploaded_at=int(time.time()),
        )
        assert image.key == "img123"
        assert image.url == "https://note.com/images/img123.png"
        assert image.original_path == "/local/path/image.png"

    def test_image_with_size(self) -> None:
        """Test creating an image with size."""
        image = Image(
            key="img123",
            url="https://note.com/images/img123.png",
            original_path="/local/path/image.png",
            size_bytes=1024,
            uploaded_at=int(time.time()),
        )
        assert image.size_bytes == 1024

    def test_image_creation_without_key(self) -> None:
        """Test creating an image without key (eyecatch API behavior).

        The eyecatch upload API (/v1/image_upload/note_eyecatch) only returns
        'url' in the response, not 'key'. This test verifies that Image model
        accepts key=None for this API behavior.
        """
        image = Image(
            url="https://note.com/images/img123.png",
            original_path="/local/path/image.png",
            uploaded_at=int(time.time()),
        )
        assert image.key is None
        assert image.url == "https://note.com/images/img123.png"


class TestTag:
    """Tests for Tag model."""

    def test_tag_creation(self) -> None:
        """Test creating a tag."""
        tag = Tag(name="python")
        assert tag.name == "python"

    def test_tag_normalize_with_hash(self) -> None:
        """Test normalizing tag with hash prefix."""
        normalized = Tag.normalize("#python")
        assert normalized == "python"

    def test_tag_normalize_without_hash(self) -> None:
        """Test normalizing tag without hash prefix."""
        normalized = Tag.normalize("python")
        assert normalized == "python"

    def test_tag_normalize_multiple_hashes(self) -> None:
        """Test normalizing tag with multiple hash prefixes."""
        normalized = Tag.normalize("##python")
        assert normalized == "python"


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_codes_exist(self) -> None:
        """Test that all error codes exist."""
        assert ErrorCode.NOT_AUTHENTICATED.value == "not_authenticated"
        assert ErrorCode.SESSION_EXPIRED.value == "session_expired"
        assert ErrorCode.ARTICLE_NOT_FOUND.value == "article_not_found"
        assert ErrorCode.RATE_LIMITED.value == "rate_limited"
        assert ErrorCode.API_ERROR.value == "api_error"
        assert ErrorCode.UPLOAD_FAILED.value == "upload_failed"
        assert ErrorCode.INVALID_INPUT.value == "invalid_input"


class TestNoteAPIError:
    """Tests for NoteAPIError exception."""

    def test_error_creation(self) -> None:
        """Test creating an API error."""
        error = NoteAPIError(
            code=ErrorCode.NOT_AUTHENTICATED,
            message="Not authenticated",
        )
        assert error.code == ErrorCode.NOT_AUTHENTICATED
        assert error.message == "Not authenticated"
        assert error.details == {}

    def test_error_with_details(self) -> None:
        """Test creating an API error with details."""
        error = NoteAPIError(
            code=ErrorCode.API_ERROR,
            message="API request failed",
            details={"status_code": 500, "response": "Internal Server Error"},
        )
        assert error.details["status_code"] == 500

    def test_error_string_representation(self) -> None:
        """Test error string representation."""
        error = NoteAPIError(
            code=ErrorCode.RATE_LIMITED,
            message="Rate limited, please wait",
        )
        assert str(error) == "Rate limited, please wait"


class TestFromApiResponse:
    """Tests for from_api_response function.

    Article 6 (Data Accuracy Mandate) compliance tests:
    - Required fields (id, key, status) must be present
    - No implicit fallback to default values for required fields
    """

    def test_from_api_response_missing_id_raises_error(self) -> None:
        """Test that missing 'id' field raises NoteAPIError."""
        data: dict[str, object] = {
            "key": "test-key",
            "status": "draft",
            "name": "Test Article",
            "body": "<p>Content</p>",
        }
        with pytest.raises(NoteAPIError) as exc_info:
            from_api_response(data)
        assert exc_info.value.code == ErrorCode.API_ERROR
        assert "id" in exc_info.value.message.lower()

    def test_from_api_response_missing_key_raises_error(self) -> None:
        """Test that missing 'key' field raises NoteAPIError."""
        data: dict[str, object] = {
            "id": "123",
            "status": "draft",
            "name": "Test Article",
            "body": "<p>Content</p>",
        }
        with pytest.raises(NoteAPIError) as exc_info:
            from_api_response(data)
        assert exc_info.value.code == ErrorCode.API_ERROR
        assert "key" in exc_info.value.message.lower()

    def test_from_api_response_missing_status_raises_error(self) -> None:
        """Test that missing 'status' field raises NoteAPIError."""
        data: dict[str, object] = {
            "id": "123",
            "key": "test-key",
            "name": "Test Article",
            "body": "<p>Content</p>",
        }
        with pytest.raises(NoteAPIError) as exc_info:
            from_api_response(data)
        assert exc_info.value.code == ErrorCode.API_ERROR
        assert "status" in exc_info.value.message.lower()

    def test_from_api_response_invalid_status_raises_error(self) -> None:
        """Test that invalid 'status' value raises NoteAPIError."""
        data: dict[str, object] = {
            "id": "123",
            "key": "test-key",
            "status": "",
            "name": "Test Article",
            "body": "<p>Content</p>",
        }
        with pytest.raises(NoteAPIError) as exc_info:
            from_api_response(data)
        assert exc_info.value.code == ErrorCode.API_ERROR
        assert "status" in exc_info.value.message.lower()

    def test_from_api_response_with_valid_data_succeeds(self) -> None:
        """Test that valid API response data creates Article successfully."""
        data: dict[str, object] = {
            "id": "123",
            "key": "test-article",
            "status": "draft",
            "name": "Test Article",
            "body": "<p>Content</p>",
            "hashtags": [
                {"hashtag": {"name": "python"}},
                {"hashtag": {"name": "programming"}},
            ],
        }
        article = from_api_response(data)
        assert article.id == "123"
        assert article.key == "test-article"
        assert article.title == "Test Article"
        assert article.status == ArticleStatus.DRAFT
        assert article.tags == ["python", "programming"]

    def test_from_api_response_empty_body_is_valid(self) -> None:
        """Test that empty body is a valid value (not a missing field)."""
        data: dict[str, object] = {
            "id": "123",
            "key": "test-article",
            "status": "draft",
            "name": "Test Article",
            "body": "",
        }
        article = from_api_response(data)
        assert article.body == ""

    def test_from_api_response_hashtag_without_name_is_skipped(self) -> None:
        """Test that hashtags without name are silently skipped."""
        data: dict[str, object] = {
            "id": "123",
            "key": "test-article",
            "status": "draft",
            "name": "Test",
            "body": "",
            "hashtags": [
                {"hashtag": {"name": "valid"}},
                {"hashtag": {}},
                {"hashtag": {"name": ""}},
            ],
        }
        article = from_api_response(data)
        assert article.tags == ["valid"]

    def test_from_api_response_title_from_note_draft(self) -> None:
        """Test that title can be extracted from noteDraft.name for drafts."""
        data: dict[str, object] = {
            "id": "123",
            "key": "test-article",
            "status": "draft",
            "body": "",
            "noteDraft": {"name": "Draft Title"},
        }
        article = from_api_response(data)
        assert article.title == "Draft Title"
