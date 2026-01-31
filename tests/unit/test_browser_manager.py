"""Unit tests for browser manager."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.browser.manager import BrowserManager

if TYPE_CHECKING:
    pass


class TestBrowserManager:
    """Tests for BrowserManager class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton instance before each test."""
        BrowserManager._instance = None
        BrowserManager._browser = None
        BrowserManager._context = None
        BrowserManager._page = None
        BrowserManager._lock = None

    def test_get_instance_creates_singleton(self) -> None:
        """Test that get_instance creates a singleton."""
        instance1 = BrowserManager.get_instance()
        instance2 = BrowserManager.get_instance()
        assert instance1 is instance2

    @pytest.mark.asyncio
    async def test_get_page_creates_browser(self) -> None:
        """Test that get_page creates browser and returns page."""
        manager = BrowserManager.get_instance()

        with patch("note_mcp.browser.manager.async_playwright") as mock_playwright:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_page.is_closed = MagicMock(return_value=False)

            mock_pw = AsyncMock()
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value.__aexit__ = AsyncMock()

            # Mock the start method
            manager._playwright = mock_pw
            manager._browser = mock_browser
            manager._context = mock_context
            manager._page = mock_page

            page = await manager.get_page()

            assert page is mock_page

    @pytest.mark.asyncio
    async def test_get_page_reuses_existing_page(self) -> None:
        """Test that get_page reuses existing page."""
        manager = BrowserManager.get_instance()

        mock_page = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        manager._page = mock_page
        manager._browser = AsyncMock()
        manager._context = AsyncMock()
        manager._lock = asyncio.Lock()

        page = await manager.get_page()

        assert page is mock_page

    @pytest.mark.asyncio
    async def test_close_closes_browser(self) -> None:
        """Test that close closes browser."""
        manager = BrowserManager.get_instance()

        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        # Set on class, not instance (matches implementation)
        BrowserManager._browser = mock_browser
        BrowserManager._playwright = mock_playwright
        BrowserManager._lock = asyncio.Lock()

        await manager.close()

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_handles_no_browser(self) -> None:
        """Test that close handles case when no browser exists."""
        manager = BrowserManager.get_instance()
        manager._lock = asyncio.Lock()

        # Should not raise
        await manager.close()


class TestBrowserManagerHeadlessParameter:
    """Tests for BrowserManager headless parameter support."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton instance before each test."""
        BrowserManager._instance = None
        BrowserManager._browser = None
        BrowserManager._context = None
        BrowserManager._page = None
        BrowserManager._lock = None
        BrowserManager._playwright = None

    @pytest.mark.asyncio
    async def test_get_page_accepts_headless_parameter(self) -> None:
        """Test that get_page accepts headless parameter."""
        manager = BrowserManager.get_instance()

        with patch("note_mcp.browser.manager.async_playwright") as mock_playwright:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_page.is_closed = MagicMock(return_value=False)

            mock_pw = AsyncMock()
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_playwright.return_value.start = AsyncMock(return_value=mock_pw)

            page = await manager.get_page(headless=False)

            assert page is mock_page
            # Verify chromium.launch was called with headless=False
            mock_pw.chromium.launch.assert_called_once_with(headless=False)

    @pytest.mark.asyncio
    async def test_get_page_headless_true_uses_headless_mode(self) -> None:
        """Test that get_page with headless=True launches in headless mode."""
        manager = BrowserManager.get_instance()

        with patch("note_mcp.browser.manager.async_playwright") as mock_playwright:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_page.is_closed = MagicMock(return_value=False)

            mock_pw = AsyncMock()
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_playwright.return_value.start = AsyncMock(return_value=mock_pw)

            page = await manager.get_page(headless=True)

            assert page is mock_page
            mock_pw.chromium.launch.assert_called_once_with(headless=True)

    @pytest.mark.asyncio
    async def test_get_page_default_uses_config(self) -> None:
        """Test that get_page without headless parameter uses config default."""
        manager = BrowserManager.get_instance()

        with (
            patch("note_mcp.browser.manager.async_playwright") as mock_playwright,
            patch("note_mcp.browser.config.get_headless_mode", return_value=True) as mock_config,
        ):
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_page.is_closed = MagicMock(return_value=False)

            mock_pw = AsyncMock()
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_playwright.return_value.start = AsyncMock(return_value=mock_pw)

            page = await manager.get_page()

            assert page is mock_page
            mock_config.assert_called_once()
            mock_pw.chromium.launch.assert_called_once_with(headless=True)

    @pytest.mark.asyncio
    async def test_get_page_ignores_headless_when_browser_exists(self) -> None:
        """Test that headless parameter is ignored when browser already exists.

        This documents the expected behavior: once a browser is launched,
        subsequent get_page() calls reuse it regardless of headless parameter.
        Call close() first if you need to change the headless mode.
        """
        manager = BrowserManager.get_instance()

        # Set up existing browser and page
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)

        BrowserManager._browser = mock_browser
        BrowserManager._page = mock_page
        BrowserManager._lock = asyncio.Lock()

        # Call get_page with headless=False, but browser already exists
        page = await manager.get_page(headless=False)

        # Should return existing page, not launch new browser
        assert page is mock_page
        # Browser launch should NOT have been called
        mock_browser.new_context.assert_not_called()


class TestBrowserManagerLock:
    """Tests for BrowserManager locking behavior."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton instance before each test."""
        BrowserManager._instance = None
        BrowserManager._browser = None
        BrowserManager._context = None
        BrowserManager._page = None
        BrowserManager._lock = None

    @pytest.mark.asyncio
    async def test_concurrent_get_page_uses_lock(self) -> None:
        """Test that concurrent get_page calls use lock."""
        manager = BrowserManager.get_instance()

        call_order: list[str] = []

        mock_page = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)

        async def mock_get_page() -> AsyncMock:
            call_order.append("get_page_start")
            await asyncio.sleep(0.01)
            call_order.append("get_page_end")
            return mock_page

        manager._page = mock_page
        manager._browser = AsyncMock()
        manager._context = AsyncMock()
        manager._lock = asyncio.Lock()

        # Multiple concurrent calls should all succeed
        results = await asyncio.gather(
            manager.get_page(),
            manager.get_page(),
            manager.get_page(),
        )

        assert len(results) == 3
        assert all(r is mock_page for r in results)
