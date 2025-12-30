"""HTTP traffic investigation core module.

Provides proxy management and capture session handling for API investigation.
"""

from __future__ import annotations

import contextlib
import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)


@dataclass
class CapturedRequest:
    """Represents a captured HTTP request/response pair."""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    response_status: int = 0
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str | None = None


class ProxyManager:
    """Manages mitmproxy (mitmdump) process lifecycle.

    Attributes:
        port: Proxy server port
        process: Subprocess running mitmdump
        output_file: Path to traffic capture file
    """

    def __init__(self, port: int = 8080) -> None:
        """Initialize proxy manager.

        Args:
            port: Port number for the proxy server
        """
        self.port = port
        self.process: subprocess.Popen[bytes] | None = None
        self.output_file: Path | None = None

    def start(self, output: Path, domain_filter: str | None = None) -> None:
        """Start mitmproxy in dump mode.

        Args:
            output: Path to save captured traffic
            domain_filter: Optional domain to filter (e.g., "note.com")
        """
        self.output_file = output

        # Use uv run to execute mitmdump within the project's virtual environment
        cmd = [
            "uv",
            "run",
            "mitmdump",
            "--mode",
            f"regular@{self.port}",
            "--set",
            "flow_detail=3",
            "-w",
            str(output),
        ]

        # Add domain filter if specified
        if domain_filter:
            cmd.extend(["--set", f"filter=~d {domain_filter}"])

        # Don't capture stdout/stderr with PIPE - it causes blocking issues
        # mitmproxy needs to write output freely without buffer pressure
        # Redirect to DEVNULL since we capture traffic to file anyway
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for proxy to start
        time.sleep(1.0)

        if self.process.poll() is not None:
            raise RuntimeError(f"Failed to start mitmproxy on port {self.port}. Check if the port is already in use.")

    def stop(self) -> None:
        """Stop mitmproxy process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

    def is_running(self) -> bool:
        """Check if mitmproxy is running.

        Returns:
            True if process is running
        """
        return self.process is not None and self.process.poll() is None


class CaptureSession:
    """Manages a traffic capture session with browser.

    Combines ProxyManager with Playwright browser for interactive
    traffic investigation.
    """

    def __init__(self, proxy_port: int = 8080) -> None:
        """Initialize capture session.

        Args:
            proxy_port: Port for the proxy server
        """
        self.proxy = ProxyManager(proxy_port)
        self.proxy_port = proxy_port
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def _verify_proxy_ready(self, timeout: float = 5.0) -> bool:
        """Verify that the proxy is accepting connections.

        Args:
            timeout: Maximum time to wait for proxy

        Returns:
            True if proxy is ready, False otherwise
        """
        import socket

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1.0)
                    result = sock.connect_ex(("127.0.0.1", self.proxy_port))
                    if result == 0:
                        logger.info(f"Proxy is ready on port {self.proxy_port}")
                        return True
            except OSError:
                pass
            time.sleep(0.5)

        logger.error(f"Proxy did not become ready on port {self.proxy_port}")
        return False

    async def start(
        self,
        output: Path,
        domain_filter: str | None = None,
        restore_session: bool = True,
    ) -> Page:
        """Start capture session with browser.

        Args:
            output: Path to save captured traffic
            domain_filter: Optional domain to filter
            restore_session: Whether to restore saved session cookies

        Returns:
            Playwright Page instance for interaction
        """
        # Start proxy first
        self.proxy.start(output, domain_filter)

        # Verify proxy is accepting connections before launching browser
        if not self._verify_proxy_ready():
            raise RuntimeError(f"Proxy is not accepting connections on port {self.proxy_port}")

        # Start browser with proxy settings
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        # Use Playwright's bundled Chromium with certificate bypass flags
        # This avoids certificate trust issues with mitmproxy
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            proxy={"server": f"http://127.0.0.1:{self.proxy_port}"},
            args=[
                "--no-sandbox",  # Required for some WSL2 configurations
                "--ignore-certificate-errors",  # Bypass all certificate validation
                "--allow-insecure-localhost",  # Allow insecure localhost connections
            ],
        )
        self._context = await self._browser.new_context(
            ignore_https_errors=True,
        )
        self._page = await self._context.new_page()

        # Restore session if available and requested
        if restore_session:
            await self._restore_session()

        return self._page

    async def _restore_session(self) -> bool:
        """Restore saved session cookies to browser context.

        Returns:
            True if session was restored, False otherwise
        """
        try:
            from note_mcp.auth.session import SessionManager

            session_manager = SessionManager()
            saved_session = session_manager.load()

            if saved_session and not saved_session.is_expired() and saved_session.cookies:
                logger.info("Restoring saved session cookies...")

                # Convert saved cookies to Playwright format
                playwright_cookies: list[dict[str, Any]] = []
                for name, value in saved_session.cookies.items():
                    playwright_cookies.append(
                        {
                            "name": name,
                            "value": value,
                            "domain": ".note.com",
                            "path": "/",
                        }
                    )

                if self._context:
                    await self._context.add_cookies(playwright_cookies)  # type: ignore[arg-type]
                    logger.info(f"Restored {len(playwright_cookies)} cookies for user: {saved_session.username}")
                    return True
                else:
                    logger.warning("No browser context available for session restore")
                    return False

            logger.info("No valid saved session found - manual login required")
            return False

        except Exception as e:
            logger.warning(f"Failed to restore session: {e}")
            return False

    async def wait_for_close(self) -> None:
        """Wait for browser to be closed by user."""
        if self._page:
            # Wait indefinitely for page close (suppress if page already closed)
            with contextlib.suppress(Exception):
                await self._page.wait_for_event("close", timeout=0)

    async def close(self) -> None:
        """Close browser and stop proxy."""
        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self.proxy.stop()

        self._context = None
        self._page = None


async def run_capture_session(
    output: Path,
    initial_url: str = "https://note.com",
    proxy_port: int = 8080,
    domain_filter: str | None = None,
    restore_session: bool = True,
) -> None:
    """Run an interactive capture session.

    Starts proxy and browser, navigates to initial URL,
    then waits for user to close browser.

    Args:
        output: Path to save captured traffic
        initial_url: URL to navigate to initially
        proxy_port: Port for proxy server
        domain_filter: Optional domain to filter traffic
        restore_session: Whether to restore saved session cookies
    """
    session = CaptureSession(proxy_port)

    try:
        page = await session.start(output, domain_filter, restore_session)

        # Try to navigate, but don't fail if it times out
        # User can manually navigate if automatic navigation fails
        try:
            await page.goto(initial_url, timeout=30000, wait_until="domcontentloaded")
        except Exception as nav_error:
            import logging

            logging.warning(f"Auto-navigation failed: {nav_error}")
            logging.info("Please navigate manually in the browser")

        # Wait for user to close browser
        await session.wait_for_close()

    finally:
        await session.close()
