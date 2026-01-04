#!/usr/bin/env python3
"""Verify if note.com's ProseMirror has InputRule for math formulas.

This script tests:
1. Inline math: $${E=mc^2}$$ + space
2. Block math: $$ + Enter + formula + $$ + Enter

If InputRule exists, the pattern will be converted to <nwc-formula>.
If not, UI automation (like insert_link.py) will be required.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from note_mcp.auth.session import SessionManager
from note_mcp.models import Session

if TYPE_CHECKING:
    from playwright._impl._api_structures import SetCookieParam
    from playwright.async_api import Page

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def inject_session_cookies(page: "Page", session: Session) -> None:
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


async def check_for_formula_element(page) -> dict:
    """Check if nwc-formula element exists in the editor."""
    result = await page.evaluate("""
    () => {
        const prosemirrorDoc = document.querySelector('.ProseMirror');
        const innerHtml = prosemirrorDoc ? prosemirrorDoc.innerHTML : 'No ProseMirror found';

        // Check formulas specifically INSIDE the ProseMirror editor
        const editorFormulas = prosemirrorDoc ?
            prosemirrorDoc.querySelectorAll('nwc-formula') : [];
        const editorKatex = prosemirrorDoc ?
            prosemirrorDoc.querySelectorAll('.katex') : [];

        // Also check entire document for comparison
        const allFormulas = document.querySelectorAll('nwc-formula');
        const allKatex = document.querySelectorAll('.katex');

        // Check for $$ patterns in text content (means InputRule didn't convert)
        const textContent = prosemirrorDoc ? prosemirrorDoc.textContent : '';
        const rawPatterns = textContent.match(/\$\$[^$]+\$\$/g) || [];

        return {
            editorFormulaCount: editorFormulas.length,
            editorKatexCount: editorKatex.length,
            allFormulaCount: allFormulas.length,
            allKatexCount: allKatex.length,
            hasEditorNwcFormula: editorFormulas.length > 0,
            hasEditorKatex: editorKatex.length > 0,
            hasKatex: allKatex.length > 0,
            hasNwcFormula: allFormulas.length > 0,
            rawDollarPatterns: rawPatterns.length,
            editorSnippet: innerHtml.substring(0, 2000),
            editorFormulaHtml: [...editorFormulas].map(el => el.outerHTML).slice(0, 3)
        };
    }
    """)
    return result


async def test_inline_math(page) -> bool:
    """Test inline math pattern: $${E=mc^2}$$ + space."""
    logger.info("Testing inline math: $${E=mc^2}$$ + space")

    # Type inline math pattern
    await page.keyboard.type("$${E=mc^2}$$")
    await asyncio.sleep(0.2)

    # Trigger with space
    await page.keyboard.type(" ")
    await asyncio.sleep(0.5)

    # Check result
    result = await check_for_formula_element(page)
    logger.info(f"After inline math + space: {result}")

    return result["hasNwcFormula"] or result["hasKatex"]


async def test_inline_math_enter(page) -> bool:
    """Test inline math pattern: $${E=mc^2}$$ + Enter."""
    logger.info("Testing inline math: $${E=mc^2}$$ + Enter")

    # New line first
    await page.keyboard.press("Enter")
    await asyncio.sleep(0.1)

    # Type inline math pattern
    await page.keyboard.type("$${a^2+b^2=c^2}$$")
    await asyncio.sleep(0.2)

    # Trigger with Enter
    await page.keyboard.press("Enter")
    await asyncio.sleep(0.5)

    # Check result
    result = await check_for_formula_element(page)
    logger.info(f"After inline math + Enter: {result}")

    return result["hasNwcFormula"] or result["hasKatex"]


async def test_block_math(page) -> bool:
    """Test block math pattern: $$ on its own line."""
    logger.info("Testing block math: $$ + Enter + formula + $$ + Enter")

    # New line
    await page.keyboard.press("Enter")
    await asyncio.sleep(0.1)

    # Opening $$
    await page.keyboard.type("$$")
    await page.keyboard.press("Enter")
    await asyncio.sleep(0.3)

    # Formula
    await page.keyboard.type("\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}")
    await asyncio.sleep(0.2)

    # Closing $$
    await page.keyboard.press("Enter")
    await page.keyboard.type("$$")
    await page.keyboard.press("Enter")
    await asyncio.sleep(0.5)

    # Check result
    result = await check_for_formula_element(page)
    logger.info(f"After block math: {result}")

    return result["hasNwcFormula"] or result["hasKatex"]


async def check_editor_menu(page) -> dict:
    """Check if editor has a math insertion menu option."""
    logger.info("Checking editor menu for math option...")

    result = await page.evaluate("""
    () => {
        // Look for toolbar buttons
        const toolbar = document.querySelector('[class*="toolbar"], [class*="Toolbar"]');
        const buttons = document.querySelectorAll('button, [role="button"]');

        const buttonTexts = [];
        buttons.forEach(btn => {
            const text = btn.textContent || btn.getAttribute('aria-label') || btn.getAttribute('title') || '';
            if (text) buttonTexts.push(text);
        });

        // Check for math-related menu items
        const hasMathButton = buttonTexts.some(t =>
            t.includes('数式') || t.includes('Math') || t.includes('formula') || t.includes('TeX')
        );

        return {
            hasToolbar: !!toolbar,
            buttonCount: buttons.length,
            hasMathButton: hasMathButton,
            buttonTexts: buttonTexts.slice(0, 20)  // First 20 buttons
        };
    }
    """)
    return result


async def main() -> int:
    """Run math InputRule verification tests."""
    article_key = "nab5964cf695c"  # Created draft
    edit_url = f"https://note.com/notes/{article_key}/edit"

    # Load session from SessionManager (same as MCP uses)
    session_manager = SessionManager()
    session = session_manager.load()

    if not session or session.is_expired():
        logger.error("No valid session found. Please run `uv run note-mcp login` first.")
        return 2

    logger.info(f"Using session for user: {session.username}")

    async with async_playwright() as p:
        # Use regular browser with cookie injection (same as E2E tests)
        browser = await p.chromium.launch(
            headless=False,  # Show browser for visual verification
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        # Inject session cookies
        await inject_session_cookies(page, session)

        try:
            logger.info(f"Navigating to: {edit_url}")
            await page.goto(edit_url, wait_until="networkidle")
            await asyncio.sleep(3)  # Wait for editor to initialize

            # Take screenshot to see current state
            screenshot_path = Path("/tmp/math_test_initial.png")
            await page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to: {screenshot_path}")

            # Check page content
            page_content = await page.content()
            logger.info(f"Page title: {await page.title()}")

            # Try different editor selectors
            selectors_to_try = [
                '[data-placeholder="本文を入力"]',
                ".ProseMirror",
                '[contenteditable="true"]',
                ".note-editor",
                "#editor",
                '[class*="editor"]',
            ]

            body_editor = None
            for selector in selectors_to_try:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        logger.info(f"Found editor with selector: {selector}")
                        body_editor = element
                        break
                except Exception:
                    continue

            if body_editor is None:
                logger.error("Could not find editor element")
                # Print page HTML for debugging
                logger.info(f"Page HTML snippet: {page_content[:2000]}")
                return 2

            await body_editor.click()
            await asyncio.sleep(0.5)

            # Take screenshot after click
            await page.screenshot(path=Path("/tmp/math_test_after_click.png"))

            # Clear existing content
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")
            await asyncio.sleep(0.3)

            # Test 1: Check editor menu
            menu_result = await check_editor_menu(page)
            logger.info(f"Menu check: {menu_result}")

            # Test 2: Inline math with space
            inline_space_result = await test_inline_math(page)
            logger.info(f"Inline math + space: {'✅ CONVERTED' if inline_space_result else '❌ NOT CONVERTED'}")

            # Take screenshot after inline test
            await page.screenshot(path=Path("/tmp/math_test_inline.png"))

            # Test 3: Inline math with Enter
            inline_enter_result = await test_inline_math_enter(page)
            logger.info(f"Inline math + Enter: {'✅ CONVERTED' if inline_enter_result else '❌ NOT CONVERTED'}")

            # Test 4: Block math
            block_result = await test_block_math(page)
            logger.info(f"Block math: {'✅ CONVERTED' if block_result else '❌ NOT CONVERTED'}")

            # Take final screenshot
            await page.screenshot(path=Path("/tmp/math_test_final.png"))

            # Final HTML check
            final_result = await check_for_formula_element(page)

            # Summary
            print("\n" + "=" * 60)
            print("MATH INPUTRULE VERIFICATION RESULTS")
            print("=" * 60)
            print("\n📊 Editor Menu:")
            print(f"   - Has toolbar: {menu_result['hasToolbar']}")
            print(f"   - Has math button: {menu_result['hasMathButton']}")
            print(f"   - Button samples: {menu_result['buttonTexts'][:5]}")

            print("\n🔬 InputRule Tests:")
            print(f"   - Inline $${{formula}}$$ + space: {'✅ YES' if inline_space_result else '❌ NO'}")
            print(f"   - Inline $${{formula}}$$ + Enter: {'✅ YES' if inline_enter_result else '❌ NO'}")
            print(f"   - Block $$ formula $$: {'✅ YES' if block_result else '❌ NO'}")

            print("\n📝 Final Editor State:")
            print(f"   - nwc-formula elements: {final_result['hasNwcFormula']}")
            print(f"   - KaTeX elements: {final_result['hasKatex']}")
            print(f"   - Editor HTML snippet:\n{final_result['editorSnippet'][:500]}...")

            has_inputrule = inline_space_result or inline_enter_result or block_result
            print(f"\n{'=' * 60}")
            if has_inputrule:
                print("✅ CONCLUSION: InputRule EXISTS - Simple implementation possible")
            else:
                print("❌ CONCLUSION: InputRule NOT FOUND - UI automation required")
            print("=" * 60)

            print("\nScreenshots saved to /tmp/math_test_*.png")

            # Keep browser open for manual inspection
            print("\n⏸️  Browser open for manual inspection. Press Ctrl+C to close.")
            await asyncio.sleep(30)

            return 0 if has_inputrule else 1

        except Exception as e:
            logger.error(f"Error during verification: {e}")
            import traceback

            traceback.print_exc()
            # Take error screenshot
            try:
                await page.screenshot(path=Path("/tmp/math_test_error.png"))
                logger.info("Error screenshot saved to /tmp/math_test_error.png")
            except Exception:
                pass
            return 2
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
