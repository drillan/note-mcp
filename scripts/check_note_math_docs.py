#!/usr/bin/env python3
"""Check note.com's official documentation for math/formula syntax."""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> int:
    """Visit note.com help center for formula documentation."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        try:
            # Go to note.com help center for formula syntax
            help_url = "https://www.help-note.com/hc/ja/articles/29461067945625"
            print(f"🌐 Visiting note.com help: {help_url}")

            await page.goto(help_url, wait_until="networkidle")
            await asyncio.sleep(2)

            await page.screenshot(path=Path("/tmp/note_formula_help.png"), full_page=True)
            print("📸 Help page saved to /tmp/note_formula_help.png")

            # Extract text content
            content = await page.evaluate("""
            () => {
                const article = document.querySelector('article') || document.body;
                return article.innerText.substring(0, 5000);
            }
            """)

            print("\n📄 Help Page Content:")
            print("=" * 60)
            print(content[:3000])
            print("=" * 60)

            # Also check the editor features page
            print("\n🌐 Checking editor features page...")
            await page.goto("https://www.help-note.com/hc/ja/articles/360000316861", wait_until="networkidle")
            await asyncio.sleep(2)

            await page.screenshot(path=Path("/tmp/note_editor_features.png"), full_page=True)
            print("📸 Editor features saved to /tmp/note_editor_features.png")

            print("\n⏸️ Browser open for 10 seconds...")
            await asyncio.sleep(10)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
