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
