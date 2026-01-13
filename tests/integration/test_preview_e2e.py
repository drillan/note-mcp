"""E2E tests for preview functionality.

Tests for:
- note_show_preview tool (browser-based preview)
- note_get_preview_html tool (programmatic HTML fetch)

These tests require authentication and should be run with:
    uv run pytest tests/integration/test_preview_e2e.py -v -m requires_auth
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.api.preview import get_preview_html
from note_mcp.browser.preview import show_preview
from note_mcp.models import Session

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


class TestShowPreviewE2E:
    """E2E tests for show_preview function."""

    @pytest.mark.asyncio
    async def test_show_preview_navigates_to_preview_url(self) -> None:
        """Test that show_preview navigates to preview URL via API token."""
        session = create_mock_session()
        article_key = "n1234567890ab"
        mock_token = "a1b2c3d4e5f607081920304050600a0b"

        with (
            patch(
                "note_mcp.browser.preview.get_preview_access_token",
                new_callable=AsyncMock,
                return_value=mock_token,
            ) as mock_get_token,
            patch(
                "note_mcp.browser.preview.build_preview_url",
                return_value=f"https://note.com/preview/{article_key}?prev_access_key={mock_token}",
            ) as mock_build_url,
            patch("note_mcp.browser.preview.BrowserManager") as mock_browser_manager,
        ):
            mock_page = AsyncMock()
            mock_page.context = MagicMock()
            mock_page.context.add_cookies = AsyncMock()

            mock_manager = MagicMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)
            mock_browser_manager.get_instance.return_value = mock_manager

            await show_preview(session, article_key)

            # Verify API token was fetched
            mock_get_token.assert_called_once_with(session, article_key)

            # Verify URL was built with token
            mock_build_url.assert_called_once_with(article_key, mock_token)

            # Verify browser navigated to preview URL
            mock_page.goto.assert_called_once()
            call_args = mock_page.goto.call_args
            assert "preview" in call_args[0][0]
            assert "prev_access_key" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_show_preview_injects_session_cookies(self) -> None:
        """Test that show_preview injects session cookies into browser context."""
        session = create_mock_session()
        article_key = "n1234567890ab"

        with (
            patch(
                "note_mcp.browser.preview.get_preview_access_token",
                new_callable=AsyncMock,
                return_value="token123",
            ),
            patch(
                "note_mcp.browser.preview.build_preview_url",
                return_value="https://note.com/preview/test",
            ),
            patch("note_mcp.browser.preview.BrowserManager") as mock_browser_manager,
        ):
            mock_page = AsyncMock()
            mock_page.context = MagicMock()
            mock_page.context.add_cookies = AsyncMock()

            mock_manager = MagicMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)
            mock_browser_manager.get_instance.return_value = mock_manager

            await show_preview(session, article_key)

            # Verify cookies were injected
            mock_page.context.add_cookies.assert_called_once()
            cookies = mock_page.context.add_cookies.call_args[0][0]

            # Should have cookies from session
            cookie_names = [c["name"] for c in cookies]
            assert "note_gql_auth_token" in cookie_names
            assert "_note_session_v5" in cookie_names

            # Verify cookie domain
            for cookie in cookies:
                assert cookie["domain"] == ".note.com"


class TestGetPreviewHtmlE2E:
    """E2E tests for get_preview_html function."""

    @pytest.mark.asyncio
    async def test_get_preview_html_fetches_html_content(self) -> None:
        """Test that get_preview_html fetches HTML content via API."""
        session = create_mock_session()
        article_key = "n1234567890ab"
        mock_token = "token123"
        mock_html = "<html><head><title>Test Article</title></head><body><h1>Test</h1></body></html>"

        with (
            patch(
                "note_mcp.api.preview.get_preview_access_token",
                new_callable=AsyncMock,
                return_value=mock_token,
            ) as mock_get_token,
            patch(
                "note_mcp.api.preview.build_preview_url",
                return_value=f"https://note.com/preview/{article_key}?prev_access_key={mock_token}",
            ),
            patch("httpx.AsyncClient") as mock_client_class,
        ):
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

            html = await get_preview_html(session, article_key)

            # Verify result
            assert html == mock_html
            assert "<html>" in html
            assert "<body>" in html

            # Verify API token was fetched
            mock_get_token.assert_called_once_with(session, article_key)

            # Verify HTTP request was made with cookies
            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args[1]
            assert "Cookie" in call_kwargs["headers"]

    @pytest.mark.asyncio
    async def test_get_preview_html_includes_session_cookies_in_request(self) -> None:
        """Test that get_preview_html includes session cookies in HTTP request."""
        session = create_mock_session()
        article_key = "n1234567890ab"

        with (
            patch(
                "note_mcp.api.preview.get_preview_access_token",
                new_callable=AsyncMock,
                return_value="token123",
            ),
            patch(
                "note_mcp.api.preview.build_preview_url",
                return_value="https://note.com/preview/test",
            ),
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html></html>"
            mock_response.is_success = True

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await get_preview_html(session, article_key)

            # Verify cookies were included in request
            call_kwargs = mock_client.get.call_args[1]
            cookie_header = call_kwargs["headers"]["Cookie"]

            # Should contain session cookies
            assert "note_gql_auth_token=token123" in cookie_header
            assert "_note_session_v5=session456" in cookie_header


class TestNoteShowPreviewToolE2E:
    """E2E tests for note_show_preview MCP tool."""

    @pytest.mark.asyncio
    async def test_note_show_preview_tool_success(self) -> None:
        """Test note_show_preview tool returns success message."""
        from note_mcp.server import note_show_preview

        session = create_mock_session()
        article_key = "n1234567890ab"

        with (
            patch("note_mcp.server._session_manager.load", return_value=session),
            patch(
                "note_mcp.server.show_preview",
                new_callable=AsyncMock,
            ) as mock_show_preview,
        ):
            fn = note_show_preview.fn
            result = await fn(article_key)

            assert "プレビュー" in result
            assert article_key in result
            mock_show_preview.assert_called_once_with(session, article_key)


class TestNoteGetPreviewHtmlToolE2E:
    """E2E tests for note_get_preview_html MCP tool."""

    @pytest.mark.asyncio
    async def test_note_get_preview_html_tool_success(self) -> None:
        """Test note_get_preview_html tool returns HTML content."""
        from note_mcp.server import note_get_preview_html

        session = create_mock_session()
        article_key = "n1234567890ab"
        mock_html = "<html><body><h1>Test Article</h1></body></html>"

        with (
            patch("note_mcp.server._session_manager.load", return_value=session),
            patch(
                "note_mcp.server.get_preview_html",
                new_callable=AsyncMock,
                return_value=mock_html,
            ),
        ):
            fn = note_get_preview_html.fn
            result = await fn(article_key)

            assert result == mock_html
            assert "<html>" in result
