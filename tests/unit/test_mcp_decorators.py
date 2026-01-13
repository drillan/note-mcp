"""Unit tests for MCP tool handler decorators.

Tests the require_session and handle_api_error decorators that provide
common functionality for MCP tool handlers.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from note_mcp.models import ErrorCode, NoteAPIError, Session


class TestRequireSessionDecorator:
    """Tests for the require_session decorator."""

    @pytest.fixture
    def valid_session(self) -> Session:
        """Create a valid, non-expired session."""
        return Session(
            username="testuser",
            user_id="12345",
            cookies={"session": "test_cookie"},
            created_at=1700000000,
            expires_at=9999999999,  # Far future, not expired
        )

    @pytest.fixture
    def expired_session(self) -> Session:
        """Create an expired session."""
        return Session(
            username="testuser",
            user_id="12345",
            cookies={"session": "test_cookie"},
            created_at=1700000000,
            expires_at=1,  # In the past, expired
        )

    @pytest.mark.asyncio
    async def test_require_session_with_valid_session(self, valid_session: Session) -> None:
        """When session is valid, the decorated function should be called."""
        from note_mcp.decorators import require_session

        call_args: list[tuple[Session, str]] = []

        @require_session
        async def mock_handler(session: Session, arg1: str) -> str:
            call_args.append((session, arg1))
            return f"success: {arg1}"

        with patch("note_mcp.decorators._session_manager") as mock_manager:
            mock_manager.load.return_value = valid_session

            result = await mock_handler("test_value")

        assert result == "success: test_value"
        assert len(call_args) == 1
        assert call_args[0][0] == valid_session
        assert call_args[0][1] == "test_value"

    @pytest.mark.asyncio
    async def test_require_session_with_no_session(self) -> None:
        """When session is None, should return error message."""
        from note_mcp.decorators import require_session

        @require_session
        async def mock_handler(session: Session, arg1: str) -> str:
            return f"success: {arg1}"

        with patch("note_mcp.decorators._session_manager") as mock_manager:
            mock_manager.load.return_value = None

            result = await mock_handler("test_value")

        assert result == "セッションが無効です。note_loginでログインしてください。"

    @pytest.mark.asyncio
    async def test_require_session_with_expired_session(self, expired_session: Session) -> None:
        """When session is expired, should return error message."""
        from note_mcp.decorators import require_session

        @require_session
        async def mock_handler(session: Session, arg1: str) -> str:
            return f"success: {arg1}"

        with patch("note_mcp.decorators._session_manager") as mock_manager:
            mock_manager.load.return_value = expired_session

            result = await mock_handler("test_value")

        assert result == "セッションが無効です。note_loginでログインしてください。"


class TestHandleApiErrorDecorator:
    """Tests for the handle_api_error decorator."""

    @pytest.mark.asyncio
    async def test_handle_api_error_on_success(self) -> None:
        """When function succeeds, should return the result."""
        from note_mcp.decorators import handle_api_error

        @handle_api_error
        async def mock_handler(arg1: str) -> str:
            return f"success: {arg1}"

        result = await mock_handler("test_value")

        assert result == "success: test_value"

    @pytest.mark.asyncio
    async def test_handle_api_error_on_note_api_error(self) -> None:
        """When NoteAPIError is raised, should return error message."""
        from note_mcp.decorators import handle_api_error

        @handle_api_error
        async def mock_handler(arg1: str) -> str:
            raise NoteAPIError(code=ErrorCode.API_ERROR, message="API failed")

        result = await mock_handler("test_value")

        assert result == "エラー [api_error]: API failed"

    @pytest.mark.asyncio
    async def test_handle_api_error_propagates_other_exceptions(self) -> None:
        """Non-NoteAPIError exceptions should propagate."""
        from note_mcp.decorators import handle_api_error

        @handle_api_error
        async def mock_handler(arg1: str) -> str:
            raise ValueError("unexpected error")

        with pytest.raises(ValueError, match="unexpected error"):
            await mock_handler("test_value")


class TestCombinedDecorators:
    """Tests for combining require_session and handle_api_error."""

    @pytest.fixture
    def valid_session(self) -> Session:
        """Create a valid, non-expired session."""
        return Session(
            username="testuser",
            user_id="12345",
            cookies={"session": "test_cookie"},
            created_at=1700000000,
            expires_at=9999999999,
        )

    @pytest.mark.asyncio
    async def test_combined_decorators_success_flow(self, valid_session: Session) -> None:
        """Combined decorators should work for successful flow."""
        from note_mcp.decorators import handle_api_error, require_session

        @require_session
        @handle_api_error
        async def mock_handler(session: Session, arg1: str) -> str:
            return f"success: {session.username}, {arg1}"

        with patch("note_mcp.decorators._session_manager") as mock_manager:
            mock_manager.load.return_value = valid_session

            result = await mock_handler("test_value")

        assert result == "success: testuser, test_value"

    @pytest.mark.asyncio
    async def test_combined_decorators_api_error_flow(self, valid_session: Session) -> None:
        """Combined decorators should handle API errors."""
        from note_mcp.decorators import handle_api_error, require_session

        @require_session
        @handle_api_error
        async def mock_handler(session: Session, arg1: str) -> str:
            raise NoteAPIError(code=ErrorCode.UPLOAD_FAILED, message="Upload failed")

        with patch("note_mcp.decorators._session_manager") as mock_manager:
            mock_manager.load.return_value = valid_session

            result = await mock_handler("test_value")

        assert result == "エラー [upload_failed]: Upload failed"

    @pytest.mark.asyncio
    async def test_combined_decorators_no_session_flow(self) -> None:
        """Combined decorators should handle missing session."""
        from note_mcp.decorators import handle_api_error, require_session

        @require_session
        @handle_api_error
        async def mock_handler(session: Session, arg1: str) -> str:
            return f"success: {arg1}"

        with patch("note_mcp.decorators._session_manager") as mock_manager:
            mock_manager.load.return_value = None

            result = await mock_handler("test_value")

        assert result == "セッションが無効です。note_loginでログインしてください。"

    @pytest.mark.asyncio
    async def test_decorator_order_matters(self, valid_session: Session) -> None:
        """Decorator order: require_session should be outer, handle_api_error inner."""
        from note_mcp.decorators import handle_api_error, require_session

        # This is the correct order: @require_session @handle_api_error
        # require_session checks session first, then handle_api_error wraps the call

        @require_session
        @handle_api_error
        async def mock_handler(session: Session, arg1: str) -> str:
            raise NoteAPIError(code=ErrorCode.API_ERROR, message="Test error")

        with patch("note_mcp.decorators._session_manager") as mock_manager:
            mock_manager.load.return_value = valid_session

            result = await mock_handler("test_value")

        # Should get the error message, not raise an exception
        assert result == "エラー [api_error]: Test error"


class TestDecoratorPreservesMetadata:
    """Tests that decorators preserve function metadata."""

    @pytest.mark.asyncio
    async def test_require_session_preserves_name(self) -> None:
        """require_session should preserve function name."""
        from note_mcp.decorators import require_session

        @require_session
        async def my_function(session: Session, arg: str) -> str:
            """My docstring."""
            return arg

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    @pytest.mark.asyncio
    async def test_handle_api_error_preserves_name(self) -> None:
        """handle_api_error should preserve function name."""
        from note_mcp.decorators import handle_api_error

        @handle_api_error
        async def my_function(arg: str) -> str:
            """My docstring."""
            return arg

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
