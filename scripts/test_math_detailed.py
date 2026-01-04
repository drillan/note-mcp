#!/usr/bin/env python3
"""Test note.com's math syntax with detailed debugging.

This script types math syntax in a new paragraph and monitors
what happens in the DOM.
"""

import asyncio
import json
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
    """Test math syntax with detailed debugging."""
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

            # Get initial editor state
            initial_state = await page.evaluate("""
            () => {
                const editor = document.querySelector('.ProseMirror');
                return {
                    paragraphCount: editor?.querySelectorAll('p').length || 0,
                    html: editor?.innerHTML.substring(0, 500) || '',
                };
            }
            """)
            print(f"\n📊 Initial state: {initial_state['paragraphCount']} paragraphs")

            # Click at the END of the editor to focus
            editor = page.locator(".ProseMirror")
            await editor.click()
            await asyncio.sleep(0.5)

            # Go to the very end
            await page.keyboard.press("Control+End")
            await asyncio.sleep(0.3)

            # Start a new paragraph
            await page.keyboard.press("Enter")
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.5)

            # Verify we're in a new paragraph
            state_after_enter = await page.evaluate("""
            () => {
                const editor = document.querySelector('.ProseMirror');
                const paragraphs = editor?.querySelectorAll('p') || [];
                return {
                    paragraphCount: paragraphs.length,
                    lastPHtml: paragraphs[paragraphs.length - 1]?.innerHTML || '',
                };
            }
            """)
            print(f"After Enter: {state_after_enter['paragraphCount']} paragraphs")
            print(f"Last paragraph HTML: '{state_after_enter['lastPHtml']}'")

            # Type a test pattern: $$E=mc^2$$
            print("\n🧪 Testing: $$E=mc^2$$")
            await page.keyboard.type("$$E=mc^2$$", delay=50)
            await asyncio.sleep(0.5)

            state_after_type = await page.evaluate("""
            () => {
                const editor = document.querySelector('.ProseMirror');
                const paragraphs = editor?.querySelectorAll('p') || [];
                const formulas = editor?.querySelectorAll('nwc-formula') || [];
                const lastP = paragraphs[paragraphs.length - 1];

                // Check for any elements that might indicate formula
                const allElements = lastP?.querySelectorAll('*') || [];
                const elementTags = [...allElements].map(el => el.tagName);

                return {
                    paragraphCount: paragraphs.length,
                    lastPHtml: lastP?.innerHTML || '',
                    lastPText: lastP?.textContent || '',
                    formulaCount: formulas.length,
                    childElements: elementTags,
                };
            }
            """)

            print(f"After typing:")
            print(f"  Last P text: {state_after_type['lastPText']}")
            print(f"  Last P HTML: {state_after_type['lastPHtml']}")
            print(f"  Formula count: {state_after_type['formulaCount']}")
            print(f"  Child elements: {state_after_type['childElements']}")

            # Now try pressing space (trigger for markdown patterns)
            print("\n🔄 Pressing space to trigger conversion...")
            await page.keyboard.type(" ")
            await asyncio.sleep(1)

            state_after_space = await page.evaluate("""
            () => {
                const editor = document.querySelector('.ProseMirror');
                const paragraphs = editor?.querySelectorAll('p') || [];
                const formulas = editor?.querySelectorAll('nwc-formula') || [];
                const katex = editor?.querySelectorAll('.katex') || [];
                const lastP = paragraphs[paragraphs.length - 1];

                return {
                    lastPHtml: lastP?.innerHTML || '',
                    formulaCount: formulas.length,
                    katexCount: katex.length,
                };
            }
            """)

            print(f"After space trigger:")
            print(f"  Last P HTML: {state_after_space['lastPHtml']}")
            print(f"  Formula count: {state_after_space['formulaCount']}")
            print(f"  KaTeX count: {state_after_space['katexCount']}")

            # Try Enter trigger
            print("\n🔄 Pressing Enter to trigger conversion...")
            await page.keyboard.press("Enter")
            await asyncio.sleep(1)

            state_after_enter2 = await page.evaluate("""
            () => {
                const editor = document.querySelector('.ProseMirror');
                const formulas = editor?.querySelectorAll('nwc-formula') || [];
                const katex = editor?.querySelectorAll('.katex') || [];

                // Get all paragraph contents for inspection
                const paragraphs = editor?.querySelectorAll('p') || [];
                const pContents = [...paragraphs].slice(-3).map(p => ({
                    html: p.innerHTML.substring(0, 200),
                    text: p.textContent?.substring(0, 100) || '',
                }));

                return {
                    formulaCount: formulas.length,
                    katexCount: katex.length,
                    lastParagraphs: pContents,
                };
            }
            """)

            print(f"After Enter trigger:")
            print(f"  Formula count: {state_after_enter2['formulaCount']}")
            print(f"  KaTeX count: {state_after_enter2['katexCount']}")
            print(f"  Last 3 paragraphs:")
            for i, p in enumerate(state_after_enter2["lastParagraphs"]):
                print(f"    [{i}] text: {p['text']}")

            # Check if there are any custom InputRules registered
            print("\n🔍 Checking for math-related InputRules in ProseMirror...")

            inputrule_check = await page.evaluate("""
            () => {
                // Search for any math-related patterns in the window
                const patterns = [];

                // Check window properties
                for (const key of Object.keys(window)) {
                    try {
                        const val = window[key];
                        if (typeof val === 'object' && val !== null) {
                            const str = JSON.stringify(val);
                            if (str && (str.includes('formula') || str.includes('math') || str.includes('katex'))) {
                                patterns.push(key);
                            }
                        }
                    } catch (e) {}
                }

                return {
                    mathRelatedGlobals: patterns.slice(0, 10),
                };
            }
            """)

            print(f"  Math-related globals: {inputrule_check['mathRelatedGlobals']}")

            # Take screenshot
            await page.screenshot(path=Path("/tmp/math_detailed_test.png"))
            print("\n📸 Screenshot saved to /tmp/math_detailed_test.png")

            print("\n⏸️ Browser open for 15 seconds for inspection...")
            await asyncio.sleep(15)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
