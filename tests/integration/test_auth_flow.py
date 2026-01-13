"""Integration tests for authentication flow."""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.auth.browser import extract_session_cookies, login_with_browser
from note_mcp.auth.session import SessionManager
from note_mcp.models import Session

if TYPE_CHECKING:
    pass


class TestLoginFlow:
    """Tests for browser-based login flow."""

    @pytest.mark.asyncio
    async def test_login_flow_extracts_cookies(self) -> None:
        """Test that login flow extracts cookies from browser."""
        with patch("note_mcp.auth.browser.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.wait_for_url = AsyncMock()
            mock_page.url = "https://note.com/login"  # Simulate being on login page
            mock_page.context = AsyncMock()
            mock_page.context.cookies = AsyncMock(
                return_value=[
                    {"name": "note_gql_auth_token", "value": "token123"},
                    {"name": "_note_session_v5", "value": "session456"},
                ]
            )
            mock_page.evaluate = AsyncMock(return_value=None)

            mock_manager.close = AsyncMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)

            # Mock session manager
            with patch("note_mcp.auth.browser.SessionManager") as mock_session_manager_class:
                mock_session_manager = MagicMock()
                mock_session_manager_class.return_value = mock_session_manager

                # Mock API response for user info
                with patch("note_mcp.auth.browser.get_current_user") as mock_get_user:
                    mock_get_user.return_value = {"id": "user123", "urlname": "testuser"}

                    session = await login_with_browser(timeout=60)

                    assert session is not None
                    assert session.cookies["note_gql_auth_token"] == "token123"
                    assert session.cookies["_note_session_v5"] == "session456"
                    assert session.user_id == "user123"
                    assert session.username == "testuser"

    @pytest.mark.asyncio
    async def test_login_flow_saves_session(self) -> None:
        """Test that login flow saves session to keyring."""
        with patch("note_mcp.auth.browser.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.wait_for_url = AsyncMock()
            mock_page.url = "https://note.com/login"  # Simulate being on login page
            mock_page.context = AsyncMock()
            mock_page.context.cookies = AsyncMock(
                return_value=[
                    {"name": "note_gql_auth_token", "value": "token123"},
                    {"name": "_note_session_v5", "value": "session456"},
                ]
            )
            mock_page.evaluate = AsyncMock(return_value=None)

            mock_manager.close = AsyncMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)

            with patch("note_mcp.auth.browser.SessionManager") as mock_session_manager_class:
                mock_session_manager = MagicMock()
                mock_session_manager_class.return_value = mock_session_manager

                with patch("note_mcp.auth.browser.get_current_user") as mock_get_user:
                    mock_get_user.return_value = {"id": "user123", "urlname": "testuser"}

                    await login_with_browser(timeout=60)

                    mock_session_manager.save.assert_called_once()


class TestExtractSessionCookies:
    """Tests for cookie extraction."""

    def test_extract_cookies_success(self) -> None:
        """Test successful cookie extraction."""
        cookies = [
            {"name": "note_gql_auth_token", "value": "token123"},
            {"name": "_note_session_v5", "value": "session456"},
            {"name": "other_cookie", "value": "ignored"},
        ]

        result = extract_session_cookies(cookies)

        assert result["note_gql_auth_token"] == "token123"
        assert result["_note_session_v5"] == "session456"
        assert "other_cookie" not in result

    def test_extract_cookies_auth_token_optional(self) -> None:
        """Test extraction succeeds without auth token (it's optional)."""
        cookies = [
            {"name": "_note_session_v5", "value": "session456"},
        ]

        result = extract_session_cookies(cookies)

        # note_gql_auth_token is optional, so extraction should succeed
        assert result["_note_session_v5"] == "session456"
        assert "note_gql_auth_token" not in result

    def test_extract_cookies_missing_session(self) -> None:
        """Test extraction when session cookie is missing."""
        cookies = [
            {"name": "note_gql_auth_token", "value": "token123"},
        ]

        with pytest.raises(ValueError, match="session"):
            extract_session_cookies(cookies)


class TestSessionFlow:
    """Tests for complete session flow."""

    @pytest.fixture
    def mock_keyring(self) -> Generator[MagicMock]:
        """Create a mock keyring."""
        with patch("note_mcp.auth.session.keyring") as mock:
            mock.get_password.return_value = None
            yield mock

    def test_session_save_and_load(self, mock_keyring: MagicMock) -> None:
        """Test saving and loading session."""
        manager = SessionManager()
        session = Session(
            cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
            user_id="user123",
            username="testuser",
            expires_at=int(time.time()) + 3600,
            created_at=int(time.time()),
        )

        # Save session
        manager.save(session)
        mock_keyring.set_password.assert_called_once()

        # Mock the saved data for load
        import json

        mock_keyring.get_password.return_value = json.dumps(session.model_dump())

        # Load session
        loaded = manager.load()

        assert loaded is not None
        assert loaded.user_id == session.user_id
        assert loaded.username == session.username

    def test_session_expiration_detection(self, mock_keyring: MagicMock) -> None:
        """Test detection of expired session."""
        import json

        manager = SessionManager()
        expired_session = Session(
            cookies={"note_gql_auth_token": "token123"},
            user_id="user123",
            username="testuser",
            expires_at=int(time.time()) - 3600,  # Expired 1 hour ago
            created_at=int(time.time()) - 7200,
        )

        mock_keyring.get_password.return_value = json.dumps(expired_session.model_dump())

        loaded = manager.load()

        assert loaded is not None
        assert loaded.is_expired() is True

    def test_logout_clears_session(self, mock_keyring: MagicMock) -> None:
        """Test that logout clears session."""
        manager = SessionManager()

        manager.clear()

        mock_keyring.delete_password.assert_called_once_with("note-mcp", "session")
