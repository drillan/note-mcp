#!/usr/bin/env python3
"""Check note.com editor '+' menu for math insertion option.

This script opens an existing draft and clicks the '+' button to see
what menu options are available, specifically looking for '数式' (math).
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
    """Check editor '+' menu for math option."""
    # Use existing draft article
    article_key = "na60789b59c21"
    edit_url = f"https://note.com/notes/{article_key}/edit"

    # Load session
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
            await asyncio.sleep(2)

            # Find the '+' button
            add_button = page.locator('button[aria-label="メニューを開く"]')
            if await add_button.count() == 0:
                print("❌ '+' button not found")
                await page.screenshot(path=Path("/tmp/menu_check_no_button.png"))
                return 1

            print("✅ Found '+' button, clicking...")
            await add_button.click()
            await asyncio.sleep(1)

            # Take screenshot of open menu
            await page.screenshot(path=Path("/tmp/menu_check_open.png"))
            print("📸 Screenshot saved to /tmp/menu_check_open.png")

            # Find all menu items
            menu_items = await page.evaluate("""
            () => {
                // Look for menu items in various possible containers
                const items = [];

                // Try common menu selectors
                const selectors = [
                    '[role="menu"] [role="menuitem"]',
                    '[role="menu"] button',
                    '[role="listbox"] [role="option"]',
                    '.popover button',
                    '[class*="menu"] button',
                    '[class*="Menu"] button',
                    '[class*="dropdown"] button',
                    '[class*="Dropdown"] button',
                    'button[class*="MenuItem"]',
                    'div[class*="MenuItem"]',
                ];

                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        const text = el.textContent?.trim() || '';
                        if (text && !items.includes(text)) {
                            items.push(text);
                        }
                    });
                }

                // Also check any visible floating elements
                const floatingElements = document.querySelectorAll('[class*="float"], [class*="Float"], [class*="popup"], [class*="Popup"]');
                floatingElements.forEach(container => {
                    container.querySelectorAll('button, [role="menuitem"], [role="option"]').forEach(el => {
                        const text = el.textContent?.trim() || '';
                        if (text && !items.includes(text)) {
                            items.push(text);
                        }
                    });
                });

                return items;
            }
            """)

            print("\n📋 Menu Items Found:")
            print("=" * 40)
            for item in menu_items:
                # Highlight math-related items
                if any(keyword in item for keyword in ["数式", "Math", "Formula", "TeX", "KaTeX"]):
                    print(f"  ⭐ {item} ← MATH FOUND!")
                else:
                    print(f"  • {item}")
            print("=" * 40)

            # Check specifically for math option
            has_math = any(
                keyword in " ".join(menu_items)
                for keyword in ["数式", "Math", "Formula", "TeX", "KaTeX", "Equation"]
            )

            if has_math:
                print("\n✅ MATH MENU OPTION EXISTS!")
                print("→ Browser automation approach is viable")
            else:
                print("\n❌ No math menu option found")
                print("→ Need alternative approach (direct JS manipulation)")

            # Keep browser open for inspection
            print("\n⏸️ Browser open for 15 seconds for manual inspection...")
            await asyncio.sleep(15)

            return 0 if has_math else 1

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
