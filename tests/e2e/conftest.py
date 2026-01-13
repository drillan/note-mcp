"""E2E test fixtures for note-mcp.

Provides real session and article management fixtures.
Requires valid session (via login) for authentication.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from playwright.async_api import Error as PlaywrightError

from note_mcp.api.articles import create_draft
from note_mcp.api.preview import get_preview_html
from note_mcp.auth.browser import login_with_browser
from note_mcp.auth.session import SessionManager
from note_mcp.browser.config import get_headless_mode
from note_mcp.browser.manager import BrowserManager
from note_mcp.models import Article, ArticleInput, LoginError, NoteAPIError, Session
from tests.e2e.helpers.constants import (
    DEFAULT_ELEMENT_WAIT_TIMEOUT_MS,
    DEFAULT_NAVIGATION_TIMEOUT_MS,
    LOGIN_TIMEOUT_SECONDS,
    NOTE_EDITOR_URL,
)
from tests.e2e.helpers.html_validator import HtmlValidator
from tests.e2e.helpers.retry import with_retry

if TYPE_CHECKING:
    from playwright._impl._api_structures import SetCookieParam
    from playwright.async_api import Page


# Test article prefix for identification and cleanup
E2E_TEST_PREFIX = "[E2E-TEST-"

# Inter-test delay for rate limiting (configurable via environment variable)
E2E_INTER_TEST_DELAY = float(os.environ.get("NOTE_MCP_E2E_DELAY", "0.5"))


# Alias for backward compatibility with existing test code
_is_headless_test = get_headless_mode


def _generate_test_article_title() -> str:
    """Generate a unique test article title with timestamp."""
    timestamp = int(time.time())
    return f"{E2E_TEST_PREFIX}{timestamp}]"


@pytest_asyncio.fixture(autouse=True)
async def cleanup_browser_manager() -> AsyncGenerator[None]:
    """Clean up BrowserManager singleton after each test.

    This fixture ensures that the BrowserManager singleton is properly
    cleaned up after each test to prevent stale browser state from
    affecting subsequent tests.

    Some E2E tests (e.g., test_create_from_toc_file) trigger browser
    automation via MCP tools, which use BrowserManager.get_instance().
    Without cleanup, the singleton persists and can cause hangs in
    subsequent tests that use different browser fixtures.
    """
    yield
    # Clean up BrowserManager singleton if it was used
    if BrowserManager._instance is not None:
        await BrowserManager.get_instance().close()


@pytest_asyncio.fixture(autouse=True)
async def inter_test_delay() -> AsyncGenerator[None]:
    """Add delay between tests to avoid API rate limiting.

    Configurable via NOTE_MCP_E2E_DELAY environment variable.
    Default: 0.5 seconds. Set to 0 to disable.

    This helps prevent 403 (Access denied) errors during bulk
    E2E test execution (Issue #166).
    """
    yield
    if E2E_INTER_TEST_DELAY > 0:
        await asyncio.sleep(E2E_INTER_TEST_DELAY)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create an event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def real_session() -> AsyncGenerator[Session]:
    """Get a real authenticated session.

    Session acquisition priority:
        1. Saved session: Use if valid and not expired
        2. Auto-login: If NOTE_USERNAME and NOTE_PASSWORD are set
        3. Manual login: Wait for user to complete login in browser

    Environment variables:
        NOTE_USERNAME: note.com username/email for automatic login
        NOTE_PASSWORD: note.com password for automatic login

    Yields:
        Authenticated Session object

    Raises:
        pytest.skip: If login fails (LoginError, timeout, etc.)
    """
    # Try to load existing session
    session_manager = SessionManager()
    session = session_manager.load()

    if session and not session.is_expired():
        yield session
        return

    # Check for credentials in environment variables
    username = os.environ.get("NOTE_USERNAME")
    password = os.environ.get("NOTE_PASSWORD")
    credentials: tuple[str, str] | None = None
    if username and password:
        credentials = (username, password)

    # No valid session - need to login
    try:
        session = await login_with_browser(
            timeout=LOGIN_TIMEOUT_SECONDS,
            credentials=credentials,
        )
        session_manager.save(session)
        yield session
    except LoginError as e:
        pytest.skip(
            f"E2Eテスト用セッション取得失敗: {e.message}. 対処法: {e.resolution or '手動でログインしてください'}"
        )
    except (PlaywrightError, TimeoutError) as e:
        pytest.skip(
            f"E2E tests require valid note.com session. Login failed: {e}. "
            "Run `uv run python -c 'from note_mcp.auth.browser import login_with_browser; "
            "import asyncio; asyncio.run(login_with_browser())'` to authenticate first."
        )


@pytest_asyncio.fixture
async def draft_article(
    real_session: Session,
) -> AsyncGenerator[Article]:
    """Create a test draft article with automatic cleanup.

    Creates a draft with the [E2E-TEST-{timestamp}] prefix for identification.
    Attempts cleanup after test completion (best-effort).

    Uses retry logic to handle transient 403 (Access denied) errors that
    may occur during bulk E2E test execution due to rate limiting.

    Args:
        real_session: Authenticated session fixture

    Yields:
        Created Article object
    """
    # Create test article
    title = _generate_test_article_title()
    article_input = ArticleInput(
        title=title,
        body="# Test Article\n\nThis is a test article created by E2E tests.",
        tags=["e2e-test"],
    )

    # Use retry wrapper to handle transient 403 errors (Issue #166)
    article = await with_retry(
        lambda: create_draft(real_session, article_input),
        backoff_base=2.0,  # Longer delay for rate limiting
    )

    yield article

    # Cleanup: Best-effort deletion
    # Note: Delete API may not exist - articles with [E2E-TEST-] prefix can be manually cleaned
    # TODO: Implement deletion if API exists (after mitmproxy investigation)


async def _inject_session_cookies(page: Page, session: Session) -> None:
    """Inject session cookies into browser context.

    Args:
        page: Playwright Page instance
        session: Session with cookies to inject
    """
    playwright_cookies: list[SetCookieParam] = [
        {
            "name": name,
            "value": value,
            "domain": ".note.com",
            "path": "/",
        }
        for name, value in session.cookies.items()
    ]
    await page.context.add_cookies(playwright_cookies)


async def _open_preview_and_get_page(page: Page, session: Session, article_key: str) -> Page:
    """Navigate directly to preview URL using API-based access.

    Uses the access_tokens API to get a preview token, then navigates
    directly to the preview URL. This is faster and more reliable than
    the editor-based approach.

    Args:
        page: Playwright Page instance with session cookies
        session: Authenticated session (for API access)
        article_key: Article key (e.g., "n1234567890ab")

    Returns:
        Playwright Page for the preview
    """
    from tests.e2e.helpers.preview_helpers import open_preview_via_api

    return await open_preview_via_api(page, session, article_key)


@pytest_asyncio.fixture
async def preview_html(
    real_session: Session,
    draft_article: Article,
) -> str:
    """Get preview HTML via API without Playwright.

    Uses note_get_preview_html API for fast HTML retrieval.
    Suitable for static HTML validation tests.

    Args:
        real_session: Authenticated session fixture
        draft_article: Draft article to get preview for

    Returns:
        Preview page HTML content

    Raises:
        pytest.skip: If API call fails
    """
    try:
        return await get_preview_html(real_session, draft_article.key)
    except NoteAPIError as e:
        pytest.skip(f"Failed to fetch preview HTML: {e.message}")


@pytest_asyncio.fixture
async def html_validator(preview_html: str) -> HtmlValidator:
    """Get HtmlValidator for static HTML validation.

    Provides BeautifulSoup-based validator for fast, Playwright-free
    HTML element verification.

    Args:
        preview_html: HTML content from preview_html fixture

    Returns:
        HtmlValidator instance
    """
    return HtmlValidator(preview_html)


@pytest_asyncio.fixture
async def preview_page(
    real_session: Session,
    draft_article: Article,
) -> AsyncGenerator[Page]:
    """Get a browser page with the draft article preview loaded.

    Creates a fresh browser context for each test to ensure clean state.
    Supports headless mode via NOTE_MCP_TEST_HEADLESS environment variable.

    Args:
        real_session: Authenticated session fixture
        draft_article: Draft article to preview

    Yields:
        Playwright Page with preview loaded
    """
    from playwright.async_api import async_playwright

    # Create fresh browser context for each test to avoid state pollution
    playwright = await async_playwright().start()
    headless = _is_headless_test()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # Inject session cookies
        await _inject_session_cookies(page, real_session)

        # Open preview using API-based access (Issue #134)
        preview = await _open_preview_and_get_page(page, real_session, draft_article.key)

        yield preview

    finally:
        # Clean up all browser resources
        await context.close()
        await browser.close()
        await playwright.stop()


@pytest_asyncio.fixture
async def editor_page(
    real_session: Session,
    draft_article: Article,
) -> AsyncGenerator[Page]:
    """エディタページを開いた状態のブラウザページ。

    既存の下書き記事をエディタで開き、ProseMirrorが表示された状態を提供。
    ネイティブHTML変換テスト用にエディタへの直接入力を可能にする。
    Supports headless mode via NOTE_MCP_TEST_HEADLESS environment variable.

    Args:
        real_session: 認証済みセッション
        draft_article: テスト用下書き記事

    Yields:
        Page: ProseMirrorエディタが表示されたページ
    """
    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    headless = _is_headless_test()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # セッションCookie注入
        await _inject_session_cookies(page, real_session)

        # エディタページへ移動
        editor_url = f"{NOTE_EDITOR_URL}/{draft_article.key}/edit/"
        await page.goto(
            editor_url,
            wait_until="domcontentloaded",
            timeout=DEFAULT_NAVIGATION_TIMEOUT_MS,
        )

        # ProseMirrorエディタ要素を待機
        await page.locator(".ProseMirror").wait_for(
            state="visible",
            timeout=DEFAULT_ELEMENT_WAIT_TIMEOUT_MS,
        )

        yield page

    finally:
        await context.close()
        await browser.close()
        await playwright.stop()


@pytest.fixture
def test_image_path() -> Path:
    """テスト用画像ファイルのパスを返す。

    100x100ピクセルのPNG画像へのパスを返す。
    画像アップロードテストで使用。

    Returns:
        Path: テスト画像ファイルのパス

    Raises:
        FileNotFoundError: 画像ファイルが存在しない場合
    """
    path = Path(__file__).parent / "assets" / "test_image.png"
    if not path.exists():
        raise FileNotFoundError(f"Test image not found: {path}")
    return path


@pytest.fixture
def env_credentials() -> tuple[str, str]:
    """環境変数から認証情報を取得。

    NOTE_USERNAME と NOTE_PASSWORD 環境変数から
    認証情報を取得する。未設定時はテストをスキップ。

    Returns:
        tuple[str, str]: (username, password)

    Raises:
        pytest.skip: 環境変数が設定されていない場合
    """
    username = os.environ.get("NOTE_USERNAME")
    password = os.environ.get("NOTE_PASSWORD")
    if not username or not password:
        pytest.skip("NOTE_USERNAME and NOTE_PASSWORD required")
    return username, password
