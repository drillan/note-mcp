"""Unit tests for preview access token functions."""

from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.models import ErrorCode, NoteAPIError, Session


class TestGetPreviewAccessToken:
    """Tests for get_preview_access_token function."""

    @pytest.fixture
    def mock_session(self) -> Session:
        """Create a mock session for testing."""
        return Session(
            username="testuser",
            user_id="12345",
            cookies={"session": "test_cookie", "XSRF-TOKEN": "test_xsrf"},
            created_at=1700000000,
        )

    @pytest.mark.asyncio
    async def test_get_preview_access_token_success(
        self, mock_session: Session
    ) -> None:
        """Normal case: successfully get preview_access_token."""
        from note_mcp.api.articles import get_preview_access_token

        mock_response = {"data": {"preview_access_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"}}

        with patch(
            "note_mcp.api.articles.NoteAPIClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            token = await get_preview_access_token(mock_session, "n1234567890ab")

            assert token == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
            mock_client.post.assert_called_once_with(
                "/v2/notes/n1234567890ab/access_tokens",
                json={"key": "n1234567890ab"},
            )

    @pytest.mark.asyncio
    async def test_get_preview_access_token_returns_32_char_hex(
        self, mock_session: Session
    ) -> None:
        """preview_access_token should be 32-character hex string."""
        from note_mcp.api.articles import get_preview_access_token

        # Actual hex token from API
        hex_token = "ec416231ef6b60f12e830f37144432b3"
        mock_response = {"data": {"preview_access_token": hex_token}}

        with patch(
            "note_mcp.api.articles.NoteAPIClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            token = await get_preview_access_token(mock_session, "n1234567890ab")

            # Verify token format
            assert len(token) == 32
            assert all(c in "0123456789abcdef" for c in token)

    @pytest.mark.asyncio
    async def test_get_preview_access_token_raises_on_empty_response(
        self, mock_session: Session
    ) -> None:
        """Should raise NoteAPIError when token is missing from response."""
        from note_mcp.api.articles import get_preview_access_token

        mock_response: dict[str, dict[str, str]] = {"data": {}}

        with patch(
            "note_mcp.api.articles.NoteAPIClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await get_preview_access_token(mock_session, "n1234567890ab")

            assert exc_info.value.code == ErrorCode.API_ERROR


class TestBuildPreviewUrl:
    """Tests for build_preview_url function."""

    def test_build_preview_url_format(self) -> None:
        """Preview URL should be constructed in correct format."""
        from note_mcp.api.articles import build_preview_url

        url = build_preview_url(
            article_key="n1234567890ab",
            preview_access_token="ec416231ef6b60f12e830f37144432b3",
        )

        expected = "https://note.com/preview/n1234567890ab?prev_access_key=ec416231ef6b60f12e830f37144432b3"
        assert url == expected

    def test_build_preview_url_with_different_key(self) -> None:
        """URL should contain the provided article key."""
        from note_mcp.api.articles import build_preview_url

        url = build_preview_url(
            article_key="n83ec3518a2d0",
            preview_access_token="abcdef1234567890abcdef1234567890",
        )

        assert "n83ec3518a2d0" in url
        assert "prev_access_key=abcdef1234567890abcdef1234567890" in url
