"""Unit tests for session management."""

from __future__ import annotations

import json
import platform
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from note_mcp.auth.session import SessionManager
from note_mcp.models import Session

if TYPE_CHECKING:
    pass


class TestSessionManager:
    """Tests for SessionManager class."""

    def test_init_default_service_name(self) -> None:
        """Test that SessionManager initializes with default service name."""
        manager = SessionManager()
        assert manager.service_name == "note-mcp"

    def test_init_custom_service_name(self) -> None:
        """Test that SessionManager accepts custom service name."""
        manager = SessionManager(service_name="custom-service")
        assert manager.service_name == "custom-service"

    @patch("note_mcp.auth.session.keyring")
    def test_save_session(self, mock_keyring: MagicMock) -> None:
        """Test saving a session to keyring."""
        manager = SessionManager()
        session = Session(
            cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
            user_id="user123",
            username="testuser",
            expires_at=int(time.time()) + 3600,
            created_at=int(time.time()),
        )

        manager.save(session)

        mock_keyring.set_password.assert_called_once()
        call_args = mock_keyring.set_password.call_args
        assert call_args[0][0] == "note-mcp"  # service name
        assert call_args[0][1] == "session"  # username key
        # Verify JSON structure
        saved_data = json.loads(call_args[0][2])
        assert saved_data["user_id"] == "user123"
        assert saved_data["username"] == "testuser"
        assert "note_gql_auth_token" in saved_data["cookies"]

    @patch("note_mcp.auth.session.keyring")
    def test_load_session_exists(self, mock_keyring: MagicMock) -> None:
        """Test loading an existing session from keyring."""
        manager = SessionManager()
        session_data = {
            "cookies": {"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
            "user_id": "user123",
            "username": "testuser",
            "expires_at": int(time.time()) + 3600,
            "created_at": int(time.time()),
        }
        mock_keyring.get_password.return_value = json.dumps(session_data)

        session = manager.load()

        assert session is not None
        assert session.user_id == "user123"
        assert session.username == "testuser"
        assert session.cookies["note_gql_auth_token"] == "token123"
        mock_keyring.get_password.assert_called_once_with("note-mcp", "session")

    @patch("note_mcp.auth.session.keyring")
    def test_load_session_not_exists(self, mock_keyring: MagicMock) -> None:
        """Test loading when no session exists."""
        manager = SessionManager()
        mock_keyring.get_password.return_value = None

        session = manager.load()

        assert session is None

    @patch("note_mcp.auth.session.keyring")
    def test_load_session_invalid_json(self, mock_keyring: MagicMock) -> None:
        """Test loading when stored data is invalid JSON."""
        manager = SessionManager()
        mock_keyring.get_password.return_value = "not valid json"

        session = manager.load()

        assert session is None

    @patch("note_mcp.auth.session.keyring")
    def test_clear_session(self, mock_keyring: MagicMock) -> None:
        """Test clearing session from keyring."""
        manager = SessionManager()

        manager.clear()

        mock_keyring.delete_password.assert_called_once_with("note-mcp", "session")

    @patch("note_mcp.auth.session.keyring")
    def test_clear_session_not_exists(self, mock_keyring: MagicMock) -> None:
        """Test clearing when no session exists."""
        from keyring.errors import PasswordDeleteError

        manager = SessionManager()
        mock_keyring.delete_password.side_effect = PasswordDeleteError("No password found")

        # Should not raise an exception
        manager.clear()

    @patch("note_mcp.auth.session.keyring")
    def test_has_session_true(self, mock_keyring: MagicMock) -> None:
        """Test has_session returns True when session exists."""
        manager = SessionManager()
        session_data = {
            "cookies": {"note_gql_auth_token": "token123"},
            "user_id": "user123",
            "username": "testuser",
            "expires_at": int(time.time()) + 3600,
            "created_at": int(time.time()),
        }
        mock_keyring.get_password.return_value = json.dumps(session_data)

        assert manager.has_session() is True

    @patch("note_mcp.auth.session.keyring")
    def test_has_session_false(self, mock_keyring: MagicMock) -> None:
        """Test has_session returns False when no session exists."""
        manager = SessionManager()
        mock_keyring.get_password.return_value = None

        assert manager.has_session() is False

    @patch("note_mcp.auth.session.keyring")
    def test_load_expired_session(self, mock_keyring: MagicMock) -> None:
        """Test loading an expired session returns it but marks as expired."""
        manager = SessionManager()
        session_data = {
            "cookies": {"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
            "user_id": "user123",
            "username": "testuser",
            "expires_at": int(time.time()) - 3600,  # Expired 1 hour ago
            "created_at": int(time.time()) - 7200,
        }
        mock_keyring.get_password.return_value = json.dumps(session_data)

        session = manager.load()

        assert session is not None
        assert session.is_expired() is True


class TestSessionManagerErrors:
    """Tests for SessionManager error handling."""

    @patch("note_mcp.auth.session.keyring")
    def test_save_keyring_error_raises_with_diagnostics(self, mock_keyring: MagicMock) -> None:
        """Test that keyring errors include diagnostic information."""
        from note_mcp.auth.session import KeyringError

        manager = SessionManager()
        session = Session(
            cookies={"note_gql_auth_token": "token123"},
            user_id="user123",
            username="testuser",
            expires_at=int(time.time()) + 3600,
            created_at=int(time.time()),
        )
        mock_keyring.set_password.side_effect = Exception("Backend not available")

        with pytest.raises(KeyringError) as exc_info:
            manager.save(session)

        error = exc_info.value
        assert "keyring" in str(error).lower()
        assert error.os_info is not None
        assert error.backend_info is not None

    @patch("note_mcp.auth.session.keyring")
    def test_load_keyring_error_raises_with_diagnostics(self, mock_keyring: MagicMock) -> None:
        """Test that keyring errors on load include diagnostic information."""
        from note_mcp.auth.session import KeyringError

        manager = SessionManager()
        mock_keyring.get_password.side_effect = Exception("Backend not available")

        with pytest.raises(KeyringError) as exc_info:
            manager.load()

        error = exc_info.value
        assert "keyring" in str(error).lower()
        assert error.os_info is not None

    @patch("note_mcp.auth.session.keyring")
    def test_keyring_error_includes_os_info(self, mock_keyring: MagicMock) -> None:
        """Test that KeyringError includes OS information."""
        from note_mcp.auth.session import KeyringError

        manager = SessionManager()
        mock_keyring.get_password.side_effect = Exception("Test error")

        with pytest.raises(KeyringError) as exc_info:
            manager.load()

        error = exc_info.value
        # Should include current platform info
        assert platform.system() in error.os_info

    @patch("note_mcp.auth.session.keyring")
    def test_keyring_error_includes_setup_instructions(self, mock_keyring: MagicMock) -> None:
        """Test that KeyringError includes setup instructions."""
        from note_mcp.auth.session import KeyringError

        manager = SessionManager()
        mock_keyring.get_password.side_effect = Exception("Test error")

        with pytest.raises(KeyringError) as exc_info:
            manager.load()

        error = exc_info.value
        # Should include instructions
        assert error.setup_instructions is not None
        assert len(error.setup_instructions) > 0


class TestKeyringError:
    """Tests for KeyringError exception."""

    def test_keyring_error_str(self) -> None:
        """Test KeyringError string representation."""
        from note_mcp.auth.session import KeyringError

        error = KeyringError(
            message="Test error",
            os_info="Linux",
            backend_info="SecretService",
            setup_instructions=["Install keyring backend"],
        )

        error_str = str(error)
        assert "Test error" in error_str
        assert "Linux" in error_str
        assert "SecretService" in error_str

    def test_keyring_error_attributes(self) -> None:
        """Test KeyringError attributes."""
        from note_mcp.auth.session import KeyringError

        error = KeyringError(
            message="Test error",
            os_info="macOS",
            backend_info="Keychain",
            setup_instructions=["Step 1", "Step 2"],
        )

        assert error.os_info == "macOS"
        assert error.backend_info == "Keychain"
        assert len(error.setup_instructions) == 2
