#!/usr/bin/env python3
"""Find math keyboard shortcuts in note.com editor.

Tests various keyboard shortcuts that might trigger math/formula insertion:
- Ctrl+M (common math shortcut)
- Ctrl+Shift+M
- Alt+M
- Etc.
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


async def check_for_math_dialog(page: "Page") -> dict:
    """Check if a math dialog or input appeared."""
    result = await page.evaluate("""
    () => {
        // Check for any dialogs or modals that might have appeared
        const dialogs = document.querySelectorAll('[role="dialog"], .modal, [class*="dialog"], [class*="modal"]');
        const mathInputs = document.querySelectorAll('input[placeholder*="数式"], input[placeholder*="formula"], input[placeholder*="tex"], input[placeholder*="math"]');
        const formulaElements = document.querySelectorAll('nwc-formula');

        // Check for any new elements with math-related classes
        const mathClasses = document.querySelectorAll('[class*="math"], [class*="formula"], [class*="katex"], [class*="tex"]');

        // Check for any popup menus
        const popups = document.querySelectorAll('[class*="popup"], [class*="dropdown"], [class*="menu"]:not(nav)');

        return {
            dialogCount: dialogs.length,
            mathInputCount: mathInputs.length,
            formulaCount: formulaElements.length,
            mathClassCount: mathClasses.length,
            popupCount: popups.length,
            dialogTexts: [...dialogs].map(d => d.textContent?.substring(0, 100) || ''),
            popupTexts: [...popups].slice(0, 5).map(p => p.textContent?.substring(0, 50) || ''),
        };
    }
    """)
    return result


async def main() -> int:
    """Test keyboard shortcuts for math insertion."""
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

            # Click in the editor
            editor = page.locator(".ProseMirror")
            await editor.click()
            await asyncio.sleep(0.5)

            # Get baseline state
            baseline = await check_for_math_dialog(page)
            print(f"\n📊 Baseline state:")
            print(f"   Dialogs: {baseline['dialogCount']}, Popups: {baseline['popupCount']}")

            # Keyboard shortcuts to test
            shortcuts = [
                ("Control+m", "Ctrl+M"),
                ("Control+Shift+m", "Ctrl+Shift+M"),
                ("Alt+m", "Alt+M"),
                ("Control+e", "Ctrl+E (equation)"),
                ("Control+Shift+e", "Ctrl+Shift+E"),
                ("Control+4", "Ctrl+4 ($ sign)"),
                ("Control+Shift+4", "Ctrl+Shift+4"),
                ("F7", "F7 (some editors use this)"),
                ("Control+.", "Ctrl+. (insert special)"),
            ]

            print("\n🧪 Testing keyboard shortcuts...")

            for shortcut, name in shortcuts:
                print(f"\n  Testing: {name}")

                # Press Escape first to clear any existing dialogs
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.2)

                # Press the shortcut
                await page.keyboard.press(shortcut)
                await asyncio.sleep(0.5)

                # Check for changes
                result = await check_for_math_dialog(page)

                # Compare to baseline
                if (result['dialogCount'] > baseline['dialogCount'] or
                    result['mathInputCount'] > 0 or
                    result['popupCount'] > baseline['popupCount'] + 1):
                    print(f"    ⚠️ POSSIBLE MATCH!")
                    print(f"       Dialogs: {baseline['dialogCount']} → {result['dialogCount']}")
                    print(f"       Popups: {baseline['popupCount']} → {result['popupCount']}")
                    print(f"       Math inputs: {result['mathInputCount']}")
                    if result['dialogTexts']:
                        print(f"       Dialog text: {result['dialogTexts']}")
                    if result['popupTexts']:
                        print(f"       Popup text: {result['popupTexts'][:3]}")

                    # Take a screenshot
                    await page.screenshot(path=Path(f"/tmp/math_shortcut_{shortcut.replace('+', '_')}.png"))
                    print(f"       Screenshot saved")
                else:
                    print(f"    ❌ No effect")

                # Press Escape to close any dialogs
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.2)

            # Also check the slash command
            print("\n🔍 Testing slash commands...")

            # Go to end and start new paragraph
            await page.keyboard.press("Control+End")
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.3)

            slash_commands = ["/math", "/formula", "/tex", "/数式", "/equation"]

            for cmd in slash_commands:
                print(f"\n  Testing: {cmd}")

                # Type the command
                await page.keyboard.type(cmd)
                await asyncio.sleep(0.5)

                # Check for autocomplete/menu
                result = await check_for_math_dialog(page)

                if result['popupCount'] > baseline['popupCount']:
                    print(f"    ⚠️ Popup appeared!")
                    print(f"       Popup texts: {result['popupTexts'][:3]}")

                    # Take screenshot
                    await page.screenshot(path=Path(f"/tmp/slash_cmd_{cmd[1:]}.png"))
                else:
                    print(f"    ❌ No menu")

                # Clear the text
                for _ in range(len(cmd)):
                    await page.keyboard.press("Backspace")
                await asyncio.sleep(0.2)

            # Take final screenshot
            await page.screenshot(path=Path("/tmp/math_shortcut_test.png"))
            print("\n📸 Final screenshot saved to /tmp/math_shortcut_test.png")

            print("\n⏸️ Browser open for 15 seconds for inspection...")
            await asyncio.sleep(15)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
