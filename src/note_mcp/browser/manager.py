"""Browser manager for Playwright automation.

Provides singleton browser instance management with page reuse.
"""

from __future__ import annotations

import asyncio
import atexit
from typing import TYPE_CHECKING, ClassVar

from playwright.async_api import Page, async_playwright

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Playwright


class BrowserManager:
    """Manages Playwright browser instance as singleton.

    Provides page reuse and proper cleanup on exit.
    Uses asyncio.Lock for thread-safe access.

    Class Attributes:
        _instance: Singleton instance
        _browser: Playwright Browser instance
        _context: Browser context
        _page: Reusable page instance
        _lock: Async lock for thread-safe access
    """

    _instance: ClassVar[BrowserManager | None] = None
    _playwright: Playwright | None = None
    _browser: Browser | None = None
    _context: BrowserContext | None = None
    _page: Page | None = None
    _lock: asyncio.Lock | None = None

    def __init__(self) -> None:
        """Initialize browser manager.

        Should not be called directly. Use get_instance() instead.
        """
        pass

    @classmethod
    def get_instance(cls) -> BrowserManager:
        """Get singleton instance of BrowserManager.

        Returns:
            BrowserManager singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
            cls._lock = asyncio.Lock()
            # Register cleanup on exit
            atexit.register(cls._sync_cleanup)
        return cls._instance

    @classmethod
    def _sync_cleanup(cls) -> None:
        """Synchronous cleanup for atexit hook."""
        if cls._browser is not None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule cleanup if loop is running
                    loop.create_task(cls._async_cleanup())
                else:
                    # Run cleanup directly if loop is not running
                    loop.run_until_complete(cls._async_cleanup())
            except RuntimeError:
                # No event loop, create one for cleanup
                asyncio.run(cls._async_cleanup())

    @classmethod
    async def _async_cleanup(cls) -> None:
        """Async cleanup for browser resources."""
        if cls._browser is not None:
            await cls._safe_close_browser()
            cls._browser = None
        if cls._playwright is not None:
            await cls._safe_stop_playwright()
            cls._playwright = None
        cls._context = None
        cls._page = None

    @classmethod
    async def _safe_close_browser(cls) -> None:
        """Safely close browser, ignoring errors."""
        try:
            if cls._browser is not None:
                await cls._browser.close()
        except Exception:  # noqa: S110 - intentionally broad for cleanup
            pass

    @classmethod
    async def _safe_stop_playwright(cls) -> None:
        """Safely stop playwright, ignoring errors."""
        try:
            if cls._playwright is not None:
                await cls._playwright.stop()
        except Exception:  # noqa: S110 - intentionally broad for cleanup
            pass

    async def _ensure_browser(self) -> None:
        """Ensure browser is started."""
        if self._playwright is None:
            self.__class__._playwright = await async_playwright().start()
        playwright = self._playwright
        assert playwright is not None

        if self._browser is None:
            import os

            # Use NOTE_MCP_TEST_HEADLESS for consistency with E2E test fixtures
            # Default: True (headless mode for CI/CD stability)
            # Set NOTE_MCP_TEST_HEADLESS=false to show browser window
            headless = os.environ.get("NOTE_MCP_TEST_HEADLESS", "true").lower() != "false"
            self.__class__._browser = await playwright.chromium.launch(headless=headless)
        browser = self._browser
        assert browser is not None

        if self._context is None:
            self.__class__._context = await browser.new_context()
        context = self._context
        assert context is not None

        if self._page is None or self._page.is_closed():
            self.__class__._page = await context.new_page()

    async def get_page(self) -> Page:
        """Get a browser page, creating if necessary.

        Reuses existing page if available and not closed.
        Uses lock for thread-safe access.

        Returns:
            Playwright Page instance
        """
        if self._lock is None:
            self.__class__._lock = asyncio.Lock()
        lock = self._lock
        assert lock is not None

        async with lock:
            # Check if existing page is still valid
            if self._page is not None and not self._page.is_closed():
                return self._page

            # Create new browser/page if needed
            await self._ensure_browser()
            assert self._page is not None
            return self._page

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._lock is None:
            self.__class__._lock = asyncio.Lock()
        lock = self._lock
        assert lock is not None

        async with lock:
            await self._async_cleanup()
