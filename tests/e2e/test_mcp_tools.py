"""E2E tests for MCP tools on note.com.

Tests the MCP tool functions that interact with note.com API.
Requires valid authentication for most tests.

Note: These tests import and call the tool functions directly,
bypassing MCP protocol for E2E testing purposes.
The @mcp.tool() decorator wraps functions in FunctionTool objects,
which mypy doesn't recognize as callable. We use type: ignore for these calls.

Run with: uv run pytest tests/e2e/test_mcp_tools.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from note_mcp.auth.session import SessionManager
from note_mcp.server import (
    note_check_auth,
    note_logout,
    note_set_username,
)

if TYPE_CHECKING:
    from note_mcp.models import Session

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


class TestAuthenticationFlow:
    """認証フローテスト（依存関係なし、最初に実行）."""

    async def test_check_auth_authenticated(
        self,
        real_session: Session,
    ) -> None:
        """認証済み状態でcheck_authが認証済みメッセージを返す."""
        # Arrange: real_session fixture ensures we're authenticated

        # Act
        result = await note_check_auth()  # type: ignore[operator]

        # Assert
        assert "認証済み" in result
        assert real_session.username in result

    async def test_check_auth_not_authenticated(self) -> None:
        """未認証状態でcheck_authが未認証メッセージを返す."""
        # Arrange: Clear any existing session
        session_manager = SessionManager()
        original_session = session_manager.load()
        session_manager.clear()

        try:
            # Act
            result = await note_check_auth()  # type: ignore[operator]

            # Assert
            assert "未認証" in result or "ログイン" in result
        finally:
            # Restore original session if it existed
            if original_session:
                session_manager.save(original_session)

    async def test_set_username(
        self,
        real_session: Session,
    ) -> None:
        """ユーザー名設定が保存される."""
        # Arrange: Use a test username
        test_username = "test_user_e2e"
        original_username = real_session.username

        # Act
        result = await note_set_username(test_username)  # type: ignore[operator]

        # Assert
        assert "設定" in result
        assert test_username in result

        # Cleanup: Restore original username
        await note_set_username(original_username)  # type: ignore[operator]

    async def test_set_username_invalid(
        self,
        real_session: Session,
    ) -> None:
        """無効なユーザー名はエラーになる."""
        # Arrange: Invalid username with special characters
        invalid_username = "invalid@user!name"

        # Act
        result = await note_set_username(invalid_username)  # type: ignore[operator]

        # Assert
        assert "無効" in result

    async def test_logout(
        self,
        real_session: Session,
    ) -> None:
        """ログアウトでセッションがクリアされる."""
        # Arrange: Ensure we have a session
        session_manager = SessionManager()
        assert session_manager.has_session()

        # Act
        result = await note_logout()  # type: ignore[operator]

        # Assert
        assert "ログアウト" in result
        assert not session_manager.has_session()

        # Cleanup: Restore session for other tests
        session_manager.save(real_session)
