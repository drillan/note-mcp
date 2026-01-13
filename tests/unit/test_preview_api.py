"""Unit tests for preview API functions.

Tests for:
- show_preview (browser-based preview via API token)
- get_preview_html (programmatic HTML fetch)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.models import ErrorCode, NoteAPIError, Session


@pytest.fixture
def mock_session() -> Session:
    """Create a mock session for testing."""
    return Session(
        username="testuser",
        user_id="12345",
        cookies={"session": "test_cookie", "XSRF-TOKEN": "test_xsrf"},
        created_at=1700000000,
    )


class TestShowPreview:
    """Tests for show_preview function (browser-based preview)."""

    @pytest.mark.asyncio
    async def test_show_preview_gets_token_and_navigates(self, mock_session: Session) -> None:
        """show_preview should get token via API and navigate to preview URL."""
        from note_mcp.browser.preview import show_preview

        # Mock the API token fetch
        with (
            patch(
                "note_mcp.browser.preview.get_preview_access_token",
                new_callable=AsyncMock,
            ) as mock_get_token,
            patch("note_mcp.browser.preview.build_preview_url") as mock_build_url,
            patch("note_mcp.browser.preview.BrowserManager") as mock_browser_manager,
        ):
            mock_get_token.return_value = "a1b2c3d4e5f607081920304050600a0b"
            mock_build_url.return_value = (
                "https://note.com/preview/n1234567890ab?prev_access_key=a1b2c3d4e5f607081920304050600a0b"
            )

            # Mock browser page
            mock_page = AsyncMock()
            mock_page.context = MagicMock()
            mock_page.context.add_cookies = AsyncMock()

            mock_manager = MagicMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)
            mock_browser_manager.get_instance.return_value = mock_manager

            await show_preview(mock_session, "n1234567890ab")

            # Verify API token was fetched
            mock_get_token.assert_called_once_with(mock_session, "n1234567890ab")

            # Verify URL was built
            mock_build_url.assert_called_once_with("n1234567890ab", "a1b2c3d4e5f607081920304050600a0b")

            # Verify browser navigated to preview URL
            mock_page.goto.assert_called_once()
            call_args = mock_page.goto.call_args
            assert "preview" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_show_preview_injects_cookies(self, mock_session: Session) -> None:
        """show_preview should inject session cookies into browser."""
        from note_mcp.browser.preview import show_preview

        with (
            patch(
                "note_mcp.browser.preview.get_preview_access_token",
                new_callable=AsyncMock,
            ) as mock_get_token,
            patch("note_mcp.browser.preview.build_preview_url") as mock_build_url,
            patch("note_mcp.browser.preview.BrowserManager") as mock_browser_manager,
        ):
            mock_get_token.return_value = "token123"
            mock_build_url.return_value = "https://note.com/preview/test"

            mock_page = AsyncMock()
            mock_page.context = MagicMock()
            mock_page.context.add_cookies = AsyncMock()

            mock_manager = MagicMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)
            mock_browser_manager.get_instance.return_value = mock_manager

            await show_preview(mock_session, "n1234567890ab")

            # Verify cookies were added
            mock_page.context.add_cookies.assert_called_once()
            cookies = mock_page.context.add_cookies.call_args[0][0]
            assert any(c["name"] == "session" for c in cookies)

    @pytest.mark.asyncio
    async def test_show_preview_propagates_api_errors(self, mock_session: Session) -> None:
        """show_preview should propagate API errors from token fetch."""
        from note_mcp.browser.preview import show_preview

        api_error = NoteAPIError(
            code=ErrorCode.ARTICLE_NOT_FOUND,
            message="Article not found",
            details={"status_code": 404},
        )

        with patch(
            "note_mcp.browser.preview.get_preview_access_token",
            new_callable=AsyncMock,
            side_effect=api_error,
        ):
            with pytest.raises(NoteAPIError) as exc_info:
                await show_preview(mock_session, "n_nonexistent")

            assert exc_info.value.code == ErrorCode.ARTICLE_NOT_FOUND


class TestGetPreviewHtml:
    """Tests for get_preview_html function (programmatic HTML fetch)."""

    @pytest.mark.asyncio
    async def test_get_preview_html_success(self, mock_session: Session) -> None:
        """get_preview_html should return HTML content."""
        from note_mcp.api.preview import get_preview_html

        mock_html = "<html><body><h1>Test Article</h1></body></html>"

        with (
            patch(
                "note_mcp.api.preview.get_preview_access_token",
                new_callable=AsyncMock,
            ) as mock_get_token,
            patch("note_mcp.api.preview.build_preview_url") as mock_build_url,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_get_token.return_value = "token123"
            mock_build_url.return_value = "https://note.com/preview/test?prev_access_key=token123"

            # Mock httpx response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_response.is_success = True

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            html = await get_preview_html(mock_session, "n1234567890ab")

            assert html == mock_html
            mock_get_token.assert_called_once_with(mock_session, "n1234567890ab")

    @pytest.mark.asyncio
    async def test_get_preview_html_propagates_token_errors(self, mock_session: Session) -> None:
        """get_preview_html should propagate token fetch errors."""
        from note_mcp.api.preview import get_preview_html

        api_error = NoteAPIError(
            code=ErrorCode.NOT_AUTHENTICATED,
            message="Not authenticated",
            details={"status_code": 401},
        )

        with patch(
            "note_mcp.api.preview.get_preview_access_token",
            new_callable=AsyncMock,
            side_effect=api_error,
        ):
            with pytest.raises(NoteAPIError) as exc_info:
                await get_preview_html(mock_session, "n1234567890ab")

            assert exc_info.value.code == ErrorCode.NOT_AUTHENTICATED

    @pytest.mark.asyncio
    async def test_get_preview_html_handles_http_errors(self, mock_session: Session) -> None:
        """get_preview_html should raise error on HTTP failure."""
        from note_mcp.api.preview import get_preview_html

        with (
            patch(
                "note_mcp.api.preview.get_preview_access_token",
                new_callable=AsyncMock,
            ) as mock_get_token,
            patch("note_mcp.api.preview.build_preview_url") as mock_build_url,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_get_token.return_value = "token123"
            mock_build_url.return_value = "https://note.com/preview/test"

            # Mock 403 response
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.is_success = False

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await get_preview_html(mock_session, "n1234567890ab")

            assert exc_info.value.code == ErrorCode.API_ERROR


class TestNoteGetPreviewHtmlTool:
    """Tests for note_get_preview_html MCP tool."""

    @pytest.mark.asyncio
    async def test_tool_returns_html_on_success(self, mock_session: Session) -> None:
        """Tool should return HTML on successful fetch."""
        from note_mcp.server import note_get_preview_html

        mock_html = "<html><body>Test</body></html>"

        with (
            patch(
                "note_mcp.server._session_manager.load",
                return_value=mock_session,
            ),
            patch(
                "note_mcp.server.get_preview_html",
                new_callable=AsyncMock,
                return_value=mock_html,
            ),
        ):
            # Access the underlying function (not the FunctionTool wrapper)
            fn = note_get_preview_html.fn
            result = await fn("n1234567890ab")
            assert result == mock_html

    @pytest.mark.asyncio
    async def test_tool_returns_error_on_no_session(self) -> None:
        """Tool should return error message when not logged in."""
        from note_mcp.server import note_get_preview_html

        with patch("note_mcp.server._session_manager.load", return_value=None):
            fn = note_get_preview_html.fn
            result = await fn("n1234567890ab")
            assert "ログイン" in result

    @pytest.mark.asyncio
    async def test_tool_returns_error_on_expired_session(self) -> None:
        """Tool should return error message when session is expired."""
        from note_mcp.server import note_get_preview_html

        expired_session = Session(
            username="testuser",
            user_id="12345",
            cookies={"session": "test"},
            created_at=1700000000,
            expires_at=1,  # Expired
        )

        with patch(
            "note_mcp.server._session_manager.load",
            return_value=expired_session,
        ):
            fn = note_get_preview_html.fn
            result = await fn("n1234567890ab")
            assert "ログイン" in result or "セッション" in result

    @pytest.mark.asyncio
    async def test_tool_returns_error_message_on_api_error(self, mock_session: Session) -> None:
        """Tool should return error message on API failure."""
        from note_mcp.server import note_get_preview_html

        api_error = NoteAPIError(
            code=ErrorCode.ARTICLE_NOT_FOUND,
            message="記事が見つかりませんでした",
        )

        with (
            patch(
                "note_mcp.server._session_manager.load",
                return_value=mock_session,
            ),
            patch(
                "note_mcp.server.get_preview_html",
                new_callable=AsyncMock,
                side_effect=api_error,
            ),
        ):
            fn = note_get_preview_html.fn
            result = await fn("n1234567890ab")
            assert "エラー" in result
