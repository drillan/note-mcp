#!/usr/bin/env python3
"""Test note.com's math syntax patterns in the editor.

Based on the official help documentation, note.com supports:
- Inline math: some delimiter pattern
- Display (block) math: another delimiter pattern

This script tests various math syntax patterns to find what triggers
the formula rendering.
"""

import asyncio
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


async def main() -> int:
    """Test math syntax patterns in note.com editor."""
    article_key = "na60789b59c21"
    edit_url = f"https://note.com/notes/{article_key}/edit"

    session_manager = SessionManager()
    session = session_manager.load()

    if not session or session.is_expired():
        print("❌ No valid session. Run `uv run note-mcp login` first.")
        return 1

    print(f"📋 Using session for user: {session.username}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        await inject_session_cookies(page, session)

        try:
            print(f"🌐 Navigating to: {edit_url}")
            await page.goto(edit_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Test patterns based on official documentation research
            # Common math delimiters to test:
            # 1. $formula$ - LaTeX inline
            # 2. $$formula$$ - LaTeX display
            # 3. \(formula\) - LaTeX alternative inline
            # 4. \[formula\] - LaTeX alternative display
            # 5. $$formula$$ with space trigger (like other markdown patterns)

            test_patterns = [
                ("$E=mc^2$", "Dollar inline"),
                ("$$E=mc^2$$", "Double dollar display"),
                ("\\(E=mc^2\\)", "LaTeX inline"),
                ("\\[E=mc^2\\]", "LaTeX display"),
                ("$${E=mc^2}$$", "Double dollar with braces"),
                ("$$\nE=mc^2\n$$", "Double dollar block"),
            ]

            # Click in the editor
            editor = page.locator(".ProseMirror")
            await editor.click()
            await asyncio.sleep(0.5)

            # Go to end of content
            await page.keyboard.press("Control+End")
            await asyncio.sleep(0.3)

            # Press Enter to start new line
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.3)

            print("\n🧪 Testing math syntax patterns...")

            for pattern, name in test_patterns:
                print(f"\n  Testing: {name} → {pattern}")

                # Type the pattern
                await page.keyboard.type(pattern)
                await asyncio.sleep(0.5)

                # Try pressing space (trigger for some markdown patterns)
                await page.keyboard.type(" ")
                await asyncio.sleep(0.3)

                # Check for formula elements
                result = await page.evaluate(
                    """
                () => {
                    const editor = document.querySelector('.ProseMirror');
                    const formulas = editor?.querySelectorAll('nwc-formula') || [];
                    const katex = editor?.querySelectorAll('.katex') || [];
                    const lastP = editor?.querySelector('p:last-child');

                    return {
                        formulaCount: formulas.length,
                        katexCount: katex.length,
                        lastParagraphHtml: lastP?.innerHTML.substring(0, 200) || '',
                    };
                }
                """
                )

                if result["formulaCount"] > 0 or result["katexCount"] > 0:
                    print(f"    ✅ SUCCESS! formula={result['formulaCount']}, katex={result['katexCount']}")
                else:
                    print(f"    ❌ No formula detected")
                    print(f"       Last paragraph: {result['lastParagraphHtml'][:100]}")

                # Press Enter to start new line for next test
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.3)

            # Also test by directly examining what patterns are in the DOM
            print("\n📊 Checking editor state after all tests...")

            final_state = await page.evaluate(
                """
            () => {
                const editor = document.querySelector('.ProseMirror');
                const formulas = editor?.querySelectorAll('nwc-formula') || [];
                const katex = editor?.querySelectorAll('.katex') || [];

                return {
                    totalFormulas: formulas.length,
                    totalKatex: katex.length,
                    editorContent: editor?.textContent?.substring(0, 500) || '',
                    hasFormulaElements: formulas.length > 0,
                };
            }
            """
            )

            print(f"  Total nwc-formula elements: {final_state['totalFormulas']}")
            print(f"  Total KaTeX rendered: {final_state['totalKatex']}")

            # Take screenshot
            await page.screenshot(path=Path("/tmp/math_syntax_test.png"))
            print("\n📸 Screenshot saved to /tmp/math_syntax_test.png")

            # Wait for inspection
            print("\n⏸️ Browser open for 15 seconds for inspection...")
            await asyncio.sleep(15)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
