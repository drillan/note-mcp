#!/usr/bin/env python3
"""Verify issue101 Math KaTeX support (commit 67f2444).

This script tests:
1. Create a draft article with math formulas using note_create_from_file
2. Extract editor HTML to verify math is saved
3. Open preview page and verify KaTeX rendering
4. Save all artifacts to debug/output/

Success criteria: .katex elements > 0 OR nwc-formula elements > 0
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.async_api import async_playwright

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from note_mcp.auth.browser import login_with_browser
from note_mcp.auth.session import SessionManager
from note_mcp.server import note_create_from_file

# Add tests directory to path for importing article helpers
sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "e2e" / "helpers"))
from article_helpers import (  # type: ignore[import-not-found]  # noqa: E402
    extract_article_id,
    extract_article_key,
)

if TYPE_CHECKING:
    from playwright._impl._api_structures import SetCookieParam
    from playwright.async_api import Page

    from note_mcp.models import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "debug" / "output"
TEST_FILE = PROJECT_ROOT / "examples" / "sample_article.md"
NOTE_EDITOR_URL = "https://note.com/notes"


async def get_or_create_session() -> Session:
    """Get saved session or perform browser login.

    Returns:
        Valid Session object

    Raises:
        RuntimeError: If session cannot be obtained
    """
    session_manager = SessionManager()
    session = session_manager.load()

    if session and not session.is_expired():
        logger.info(f"Using saved session for user: {session.username}")
        return session

    logger.info("No valid session found, opening browser for login...")
    session = await login_with_browser(timeout=300)

    if not session:
        raise RuntimeError("Failed to obtain session")

    return session


async def inject_session_cookies(page: Page, session: Session) -> None:
    """Inject session cookies into browser context."""
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


async def get_editor_html(page: Page, article_key: str) -> str:
    """Navigate to editor and extract ProseMirror HTML."""
    editor_url = f"{NOTE_EDITOR_URL}/{article_key}/edit/"
    logger.info(f"Navigating to editor: {editor_url}")

    await page.goto(editor_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=30000)

    # Wait for editor to initialize
    await asyncio.sleep(2)

    # Find ProseMirror editor
    editor_selectors = [
        ".ProseMirror",
        '[data-placeholder="本文を入力"]',
        '[contenteditable="true"]',
    ]

    for selector in editor_selectors:
        try:
            element = page.locator(selector).first
            if await element.count() > 0:
                html = await element.inner_html()
                logger.info(f"Found editor with selector: {selector}")
                return html
        except Exception:
            continue

    # Fallback: get full page content
    logger.warning("Could not find ProseMirror editor, returning full page content")
    return await page.content()


async def open_preview_page(page: Page, article_key: str) -> Page:
    """Open preview page via editor menu."""
    editor_url = f"{NOTE_EDITOR_URL}/{article_key}/edit/"

    await page.goto(editor_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=30000)

    # Click menu button (3-dot icon)
    menu_button = page.locator('button[aria-label="その他"]')
    await menu_button.wait_for(state="visible", timeout=10000)
    await menu_button.click()

    # Click preview button
    preview_button = page.locator("#header-popover button", has_text="プレビュー")
    await preview_button.wait_for(state="visible", timeout=10000)

    # Capture new page (preview tab)
    async with page.context.expect_page(timeout=30000) as new_page_info:
        await preview_button.click()

    preview_page = await new_page_info.value
    await preview_page.wait_for_load_state("networkidle", timeout=30000)

    return preview_page


async def extract_math_elements(page: Page) -> dict[str, Any]:
    """Extract math-related elements from the page."""
    result: dict[str, Any] = await page.evaluate(
        r"""
    () => {
        const katex = document.querySelectorAll('.katex');
        const nwcFormula = document.querySelectorAll('nwc-formula');

        return {
            katex_count: katex.length,
            nwc_formula_count: nwcFormula.length,
            katex_elements: [...katex].map(el => ({
                text: el.textContent?.substring(0, 100) || '',
                outer_html: el.outerHTML.substring(0, 500)
            })),
            nwc_formula_elements: [...nwcFormula].map(el => ({
                is_block: el.getAttribute('is-block'),
                content: el.textContent?.substring(0, 100) || '',
                outer_html: el.outerHTML.substring(0, 500)
            })),
            // Check for unconverted math patterns (note.com uses $$ patterns)
            raw_patterns: {
                dollar_double: (document.body.textContent?.match(/\$\$[^$]+\$\$/g) || []).length,
                dollar_double_braces: (document.body.textContent?.match(/\$\$\{[^}]+\}\$\$/g) || []).length
            }
        };
    }
    """
    )
    return result


def save_output(filename: str, content: str | dict[str, Any]) -> Path:
    """Save output to debug/output/ directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / filename

    if isinstance(content, dict):
        filepath.write_text(json.dumps(content, ensure_ascii=False, indent=2))
    else:
        filepath.write_text(content, encoding="utf-8")

    logger.info(f"Saved: {filepath}")
    return filepath


async def main() -> int:
    """Run issue101 Math KaTeX verification.

    Returns:
        0: Success (KaTeX elements detected)
        1: Failure (KaTeX elements not detected)
        2: Error (processing exception)
    """
    logger.info("=" * 60)
    logger.info("ISSUE 101 MATH KATEX VERIFICATION")
    logger.info("=" * 60)

    # Verify test file exists
    if not TEST_FILE.exists():
        logger.error(f"Test file not found: {TEST_FILE}")
        return 2

    try:
        # Step 1: Get session
        logger.info("\n📋 Step 1: Getting session...")
        session = await get_or_create_session()

        # Step 2: Create draft article
        logger.info("\n📋 Step 2: Creating draft article...")
        result = await note_create_from_file.fn(file_path=str(TEST_FILE))
        logger.info(f"MCP Result: {result[:200]}...")

        article_id = extract_article_id(result)
        article_key = extract_article_key(result)
        logger.info(f"Article ID: {article_id}, Key: {article_key}")

        # Step 3: Browser automation (manual playwright management to avoid hang)
        logger.info("\n📋 Step 3: Starting browser automation...")
        p = await async_playwright().start()
        browser = None
        context = None
        preview_page = None
        exit_code = 2  # Default to error

        try:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

            # Inject session cookies
            await inject_session_cookies(page, session)

            # Step 4: Get editor HTML
            logger.info("\n📋 Step 4: Extracting editor HTML...")
            editor_html = await get_editor_html(page, article_key)
            save_output("issue101_editor_html.html", editor_html)

            # Step 5: Open preview and extract math
            logger.info("\n📋 Step 5: Opening preview page...")
            preview_page = await open_preview_page(page, article_key)

            # Wait for KaTeX to render
            await asyncio.sleep(3)

            # Get preview HTML
            preview_html = await preview_page.content()
            save_output("issue101_preview_html.html", preview_html)

            # Extract math elements
            logger.info("\n📋 Step 6: Extracting math elements...")
            math_elements = await extract_math_elements(preview_page)
            save_output("issue101_math_elements.json", math_elements)

            # Step 7: Determine result
            katex_count = math_elements["katex_count"]
            nwc_formula_count = math_elements["nwc_formula_count"]
            raw_patterns = math_elements.get("raw_patterns", {})

            # Success requires:
            # 1. At least one math element was rendered
            # 2. No unconverted $$...$$ patterns remain in raw text
            has_rendered_math = katex_count > 0 or nwc_formula_count > 0
            unconverted_display = raw_patterns.get("dollar_double", 0)
            unconverted_inline = raw_patterns.get("dollar_double_braces", 0)
            unconverted_count = unconverted_display + unconverted_inline

            if has_rendered_math and unconverted_count == 0:
                success = True
                message = "All math formulas rendered correctly"
            elif has_rendered_math and unconverted_count > 0:
                success = False
                message = f"Partial: {nwc_formula_count} rendered, {unconverted_count} unconverted"
            else:
                success = False
                message = "No KaTeX rendering detected"

            # Build result summary
            result_summary = {
                "timestamp": datetime.now(UTC).isoformat(),
                "commit": "67f2444",
                "test_file": str(TEST_FILE),
                "article": {
                    "id": article_id,
                    "key": article_key,
                },
                "math_detection": {
                    "katex_count": katex_count,
                    "nwc_formula_count": nwc_formula_count,
                    "raw_patterns": raw_patterns,
                    "unconverted_count": unconverted_count,
                },
                "success": success,
                "message": message,
            }
            save_output("issue101_result.json", result_summary)

            # Print summary
            print("\n" + "=" * 60)
            print("ISSUE 101 MATH KATEX VERIFICATION RESULTS")
            print("=" * 60)

            print("\n📋 Test Configuration:")
            print(f"   - Test file: {TEST_FILE.name}")
            print("   - Commit: 67f2444")

            print("\n📝 Article Created:")
            print(f"   - ID: {article_id}")
            print(f"   - Key: {article_key}")

            print("\n🔬 Math Rendering Analysis:")
            print(f"   - KaTeX elements found: {katex_count}")
            print(f"   - nwc-formula elements found: {nwc_formula_count}")
            print(f"   - Unconverted $...$ patterns: {unconverted_count}")
            if raw_patterns:
                print(f"   - Raw pattern details: {raw_patterns}")

            print("\n" + "=" * 60)
            if success:
                print(f"✅ RESULT: SUCCESS - {message}")
            else:
                print(f"❌ RESULT: FAILURE - {message}")
            print("=" * 60)

            print(f"\nOutput files: {OUTPUT_DIR}/issue101_*")

            exit_code = 0 if success else 1

        finally:
            logger.info("🔧 Cleanup: Closing preview page...")
            try:
                if preview_page:
                    await preview_page.close()
                    logger.info("   ✅ Preview page closed")
                else:
                    logger.info("   ⏭️ Preview page not opened, skipping")
            except Exception as e:
                logger.warning(f"   ⚠️ Preview page close failed: {e}")

            if context:
                logger.info("🔧 Cleanup: Closing browser context...")
                await context.close()
                logger.info("   ✅ Context closed")

            if browser:
                logger.info("🔧 Cleanup: Closing browser...")
                await browser.close()
                logger.info("   ✅ Browser closed")

            logger.info("🔧 Cleanup: Stopping Playwright server...")
            await p.stop()
            logger.info("   ✅ Playwright stopped")

        logger.info("🔧 Cleanup complete, returning from main()...")
        return exit_code

    except Exception as e:
        logger.exception(f"Error during verification: {e}")
        # Save error result
        error_result = {
            "timestamp": datetime.now(UTC).isoformat(),
            "commit": "67f2444",
            "success": False,
            "error": str(e),
        }
        save_output("issue101_result.json", error_result)
        return 2


if __name__ == "__main__":
    import os

    print("🚀 Starting verification script...")
    result = asyncio.run(main())
    print(f"🏁 asyncio.run() completed with result: {result}")
    # Use os._exit() to force termination - the MCP tool may leave browser processes
    # running that prevent normal sys.exit() from completing
    os._exit(result)
