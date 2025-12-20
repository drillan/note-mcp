"""Unit tests for API client."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest

from note_mcp.api.client import NoteAPIClient
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


class TestNoteAPIClient:
    """Tests for NoteAPIClient class."""

    def test_init_with_session(self) -> None:
        """Test client initialization with session."""
        session = create_mock_session()
        client = NoteAPIClient(session)
        assert client.session is session

    def test_init_without_session(self) -> None:
        """Test client initialization without session."""
        client = NoteAPIClient(None)
        assert client.session is None

    def test_build_headers_with_session(self) -> None:
        """Test header building with session cookies."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        headers = client._build_headers()

        assert "Cookie" in headers
        assert "note_gql_auth_token=token123" in headers["Cookie"]
        assert "_note_session_v5=session456" in headers["Cookie"]

    def test_build_headers_without_session(self) -> None:
        """Test header building without session."""
        client = NoteAPIClient(None)

        headers = client._build_headers()

        assert "Cookie" not in headers
        assert "Accept" in headers

    @pytest.mark.asyncio
    async def test_get_success(self) -> None:
        """Test successful GET request."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"key": "value"}}

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                result = await client.get("/test-endpoint")

        assert result == {"data": {"key": "value"}}

    @pytest.mark.asyncio
    async def test_post_success(self) -> None:
        """Test successful POST request."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": "123"}}

        with patch.object(httpx.AsyncClient, "post", return_value=mock_response):
            async with client:
                result = await client.post("/test-endpoint", json={"name": "test"})

        assert result == {"data": {"id": "123"}}


class TestNoteAPIClientErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_401_error_raises_not_authenticated(self) -> None:
        """Test that 401 response raises NOT_AUTHENTICATED error."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.is_success = False
        mock_response.text = "Unauthorized"

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                with pytest.raises(NoteAPIError) as exc_info:
                    await client.get("/test-endpoint")

        assert exc_info.value.code == ErrorCode.NOT_AUTHENTICATED

    @pytest.mark.asyncio
    async def test_403_error_raises_api_error(self) -> None:
        """Test that 403 response raises API_ERROR."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.is_success = False
        mock_response.text = "Forbidden"

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                with pytest.raises(NoteAPIError) as exc_info:
                    await client.get("/test-endpoint")

        assert exc_info.value.code == ErrorCode.API_ERROR

    @pytest.mark.asyncio
    async def test_404_error_raises_article_not_found(self) -> None:
        """Test that 404 response raises ARTICLE_NOT_FOUND error."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.is_success = False
        mock_response.text = "Not found"

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                with pytest.raises(NoteAPIError) as exc_info:
                    await client.get("/test-endpoint")

        assert exc_info.value.code == ErrorCode.ARTICLE_NOT_FOUND

    @pytest.mark.asyncio
    async def test_429_error_raises_rate_limited(self) -> None:
        """Test that 429 response raises RATE_LIMITED error."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.is_success = False
        mock_response.text = "Too Many Requests"

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                with pytest.raises(NoteAPIError) as exc_info:
                    await client.get("/test-endpoint")

        assert exc_info.value.code == ErrorCode.RATE_LIMITED

    @pytest.mark.asyncio
    async def test_5xx_error_raises_api_error(self) -> None:
        """Test that 5xx responses raise API_ERROR."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.is_success = False
        mock_response.text = "Internal Server Error"

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                with pytest.raises(NoteAPIError) as exc_info:
                    await client.get("/test-endpoint")

        assert exc_info.value.code == ErrorCode.API_ERROR


class TestNoteAPIClientRateLimiting:
    """Tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_tracked(self) -> None:
        """Test that requests are tracked for rate limiting."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                # Make a request
                await client.get("/test-endpoint")

                # Check that request was tracked
                assert len(client._request_times) == 1

    @pytest.mark.asyncio
    async def test_old_requests_cleaned_up(self) -> None:
        """Test that old request timestamps are cleaned up."""
        session = create_mock_session()
        client = NoteAPIClient(session)

        # Add some old timestamps (more than 1 minute ago)
        old_time = time.time() - 120  # 2 minutes ago
        client._request_times = [old_time, old_time + 1, old_time + 2]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                await client.get("/test-endpoint")

                # Old requests should be cleaned up
                # Only the new request should remain
                assert len(client._request_times) == 1


class TestNoteAPIClientNoSession:
    """Tests for client behavior without session."""

    @pytest.mark.asyncio
    async def test_request_without_session(self) -> None:
        """Test that requests work without session (for public endpoints)."""
        client = NoteAPIClient(None)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"public": True}}

        with patch.object(httpx.AsyncClient, "get", return_value=mock_response):
            async with client:
                result = await client.get("/public-endpoint")

        assert result == {"data": {"public": True}}
