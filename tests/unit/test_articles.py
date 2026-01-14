"""Unit tests for article operations."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.api.articles import (
    _build_article_payload,
    _execute_get,
    _execute_post,
    _parse_article_response,
    get_article_raw_html,
    get_article_via_api,
)
from note_mcp.models import Article, ArticleInput, ArticleStatus, ErrorCode, NoteAPIError, Session


class TestParseArticleResponse:
    """Tests for _parse_article_response helper function."""

    def test_parses_standard_api_response(self) -> None:
        """_parse_article_response should extract Article from standard API response."""
        response = {
            "data": {
                "id": 12345,
                "key": "n1234567890ab",
                "name": "Test Article",
                "body": "<p>Test body</p>",
                "status": "draft",
            }
        }

        article = _parse_article_response(response)

        assert isinstance(article, Article)
        assert article.id == "12345"
        assert article.key == "n1234567890ab"
        assert article.title == "Test Article"
        assert article.body == "<p>Test body</p>"
        assert article.status == ArticleStatus.DRAFT

    def test_handles_empty_data(self) -> None:
        """_parse_article_response should handle empty data gracefully."""
        response: dict[str, dict[str, str]] = {"data": {}}

        article = _parse_article_response(response)

        assert isinstance(article, Article)
        assert article.id == ""
        assert article.key == ""
        assert article.title == ""

    def test_raises_error_when_data_key_missing(self) -> None:
        """_parse_article_response should raise error when 'data' key is missing."""
        response: dict[str, str] = {}

        with pytest.raises(NoteAPIError) as exc_info:
            _parse_article_response(response)

        assert exc_info.value.code == ErrorCode.API_ERROR
        assert "missing 'data' key" in exc_info.value.message

    def test_parses_published_article(self) -> None:
        """_parse_article_response should correctly parse published article status."""
        response = {
            "data": {
                "id": 67890,
                "key": "nabcdef123456",
                "name": "Published Article",
                "body": "<p>Content</p>",
                "status": "published",
            }
        }

        article = _parse_article_response(response)

        assert article.status == ArticleStatus.PUBLISHED


class TestBuildArticlePayload:
    """Tests for _build_article_payload function."""

    def test_body_length_matches_html_not_markdown(self) -> None:
        """body_length should match HTML body length, not Markdown body length.

        This is critical because note.com API validates body_length against
        the actual body content. Using Markdown length when body is HTML
        causes 400 errors.
        """
        # Markdown body (short)
        markdown_body = "![image](https://example.com/img.png)"

        # HTML body (much longer after conversion)
        html_body = (
            '<figure name="abc123" id="abc123">'
            '<img src="https://example.com/img.png" alt="" width="620" height="457">'
            "<figcaption></figcaption></figure>"
        )

        article_input = ArticleInput(
            title="Test Article",
            body=markdown_body,
        )

        payload = _build_article_payload(article_input, html_body)

        # body_length must match HTML body length, not Markdown body length
        assert payload["body_length"] == len(html_body)
        assert payload["body_length"] != len(markdown_body)
        assert payload["body"] == html_body

    def test_body_length_with_no_body(self) -> None:
        """body_length should not be set when include_body=False."""
        article_input = ArticleInput(
            title="Test Article",
            body="Some content",
        )

        payload = _build_article_payload(article_input, include_body=False)

        assert "body" not in payload
        assert "body_length" not in payload

    def test_payload_includes_title(self) -> None:
        """Payload should always include the title."""
        article_input = ArticleInput(
            title="My Test Title",
            body="Content",
        )

        payload = _build_article_payload(article_input, "<p>Content</p>")

        assert payload["name"] == "My Test Title"

    def test_payload_includes_tags_when_provided(self) -> None:
        """Payload should include hashtags when tags are provided."""
        article_input = ArticleInput(
            title="Test Article",
            body="Content",
            tags=["python", "testing"],
        )

        payload = _build_article_payload(article_input, "<p>Content</p>")

        assert "hashtags" in payload
        assert len(payload["hashtags"]) == 2
        assert payload["hashtags"][0] == {"hashtag": {"name": "python"}}
        assert payload["hashtags"][1] == {"hashtag": {"name": "testing"}}

    def test_tags_with_hash_prefix_are_normalized(self) -> None:
        """Tags with # prefix should have prefix removed."""
        article_input = ArticleInput(
            title="Test Article",
            body="Content",
            tags=["#python", "#testing"],
        )

        payload = _build_article_payload(article_input, "<p>Content</p>")

        assert payload["hashtags"][0] == {"hashtag": {"name": "python"}}
        assert payload["hashtags"][1] == {"hashtag": {"name": "testing"}}

    def test_body_not_included_when_html_body_is_none(self) -> None:
        """body and body_length should not be set when html_body is None.

        This handles the edge case where include_body=True (default) but
        html_body is not provided. The payload should omit body fields
        to avoid sending invalid data to the API.
        """
        article_input = ArticleInput(
            title="Test Article",
            body="Markdown content",
        )

        # html_body=None with include_body=True (default)
        payload = _build_article_payload(article_input, html_body=None)

        # body and body_length should NOT be in payload
        assert "body" not in payload
        assert "body_length" not in payload
        # But title should still be included
        assert payload["name"] == "Test Article"


class TestGetArticleViaApiNumericIdValidation:
    """Tests for numeric ID validation in get_article_via_api()."""

    @pytest.fixture
    def mock_session(self) -> Session:
        """Create a mock session for testing."""
        return Session(
            cookies={"note_gql_auth_token": "test_token", "XSRF-TOKEN": "test_xsrf"},
            user_id="test_user",
            username="testuser",
            created_at=1700000000,
        )

    @pytest.mark.asyncio
    async def test_get_article_via_api_rejects_numeric_id(self, mock_session: Session) -> None:
        """get_article_via_api() should reject numeric IDs.

        Issue #154: /v3/notes/ endpoint does not support numeric IDs.
        """
        with pytest.raises(NoteAPIError) as exc_info:
            await get_article_via_api(mock_session, "123456789")

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "Numeric article ID" in exc_info.value.message
        assert "123456789" in exc_info.value.message
        assert "n1234567890ab" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_article_raw_html_rejects_numeric_id(self, mock_session: Session) -> None:
        """get_article_raw_html() should reject numeric IDs.

        Issue #154: /v3/notes/ endpoint does not support numeric IDs.
        """
        with pytest.raises(NoteAPIError) as exc_info:
            await get_article_raw_html(mock_session, "987654321")

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "Numeric article ID" in exc_info.value.message
        assert "987654321" in exc_info.value.message
        assert "n1234567890ab" in exc_info.value.message


class TestExecuteGet:
    """Tests for _execute_get helper function."""

    @pytest.fixture
    def mock_session(self) -> Session:
        """Create a mock session for testing."""
        return Session(
            cookies={"note_gql_auth_token": "test_token", "XSRF-TOKEN": "test_xsrf"},
            user_id="test_user",
            username="testuser",
            created_at=1700000000,
        )

    @pytest.mark.asyncio
    async def test_execute_get_calls_client_and_parses_response(self, mock_session: Session) -> None:
        """_execute_get should call client.get and apply parser to response."""
        mock_response = {"data": {"id": 123, "key": "n123abc"}}

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            def parser(resp: dict[str, Any]) -> str:
                return str(resp["data"]["key"])

            result = await _execute_get(
                mock_session,
                "/v3/notes/n123abc",
                parser,
            )

            assert result == "n123abc"
            mock_client.get.assert_called_once_with("/v3/notes/n123abc", params=None)

    @pytest.mark.asyncio
    async def test_execute_get_passes_params(self, mock_session: Session) -> None:
        """_execute_get should pass query params to client.get."""
        mock_response: dict[str, Any] = {"data": {"notes": []}}

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            def parser(resp: dict[str, Any]) -> dict[str, Any]:
                data: dict[str, Any] = resp["data"]
                return data

            result = await _execute_get(
                mock_session,
                "/v2/note_list/contents",
                parser,
                params={"page": 1, "status": "draft"},
            )

            assert result == {"notes": []}
            mock_client.get.assert_called_once_with("/v2/note_list/contents", params={"page": 1, "status": "draft"})


class TestExecutePost:
    """Tests for _execute_post helper function."""

    @pytest.fixture
    def mock_session(self) -> Session:
        """Create a mock session for testing."""
        return Session(
            cookies={"note_gql_auth_token": "test_token", "XSRF-TOKEN": "test_xsrf"},
            user_id="test_user",
            username="testuser",
            created_at=1700000000,
        )

    @pytest.mark.asyncio
    async def test_execute_post_calls_client_and_parses_response(self, mock_session: Session) -> None:
        """_execute_post should call client.post and apply parser to response."""
        mock_response = {"data": {"result": True, "note_days_count": 1}}

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)

            def parser(resp: dict[str, Any]) -> bool:
                return bool(resp["data"]["result"])

            result = await _execute_post(
                mock_session,
                "/v1/text_notes/draft_save?id=123",
                parser,
                payload={"name": "Test", "body": "<p>Content</p>"},
            )

            assert result is True
            mock_client.post.assert_called_once_with(
                "/v1/text_notes/draft_save?id=123",
                json={"name": "Test", "body": "<p>Content</p>"},
            )

    @pytest.mark.asyncio
    async def test_execute_post_without_payload(self, mock_session: Session) -> None:
        """_execute_post should work without payload."""
        mock_response = {"data": {"status": "published"}}

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)

            def parser(resp: dict[str, Any]) -> str:
                return str(resp["data"]["status"])

            result = await _execute_post(
                mock_session,
                "/v3/notes/n123abc/publish",
                parser,
            )

            assert result == "published"
            mock_client.post.assert_called_once_with("/v3/notes/n123abc/publish", json=None)
