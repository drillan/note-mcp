#!/usr/bin/env python3
"""Search for note.com's math/formula help documentation."""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> int:
    """Search note.com help center for formula documentation."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        try:
            # Search help center for formula/math
            search_url = "https://www.help-note.com/hc/ja/search?utf8=%E2%9C%93&query=%E6%95%B0%E5%BC%8F"
            print(f"🔍 Searching help center: {search_url}")

            await page.goto(search_url, wait_until="networkidle")
            await asyncio.sleep(2)

            await page.screenshot(path=Path("/tmp/help_search_formula.png"))
            print("📸 Search results saved to /tmp/help_search_formula.png")

            # Find help article links
            links = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('a').forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const text = a.textContent?.trim() || '';
                    if (href.includes('articles') && text) {
                        results.push({ href, text: text.substring(0, 100) });
                    }
                });
                return results.slice(0, 10);
            }
            """)

            print("\n📋 Help Articles Found:")
            for link in links:
                print(f"  • {link['text']}")
                print(f"    {link['href']}")

            # Try alternative: search for KaTeX
            print("\n🔍 Also searching for 'KaTeX'...")
            await page.goto("https://www.help-note.com/hc/ja/search?utf8=%E2%9C%93&query=KaTeX", wait_until="networkidle")
            await asyncio.sleep(1)

            await page.screenshot(path=Path("/tmp/help_search_katex.png"))

            # Try going to editor help directly
            print("\n🌐 Checking editor help page...")
            await page.goto("https://www.help-note.com/hc/ja/categories/360000081262", wait_until="networkidle")
            await asyncio.sleep(2)

            await page.screenshot(path=Path("/tmp/help_editor_category.png"))

            # Extract all article links from editor category
            editor_links = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('a').forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const text = a.textContent?.trim() || '';
                    if (href.includes('articles') && text && text.length > 5) {
                        results.push({ href, text: text.substring(0, 80) });
                    }
                });
                return results;
            }
            """)

            print("\n📋 Editor Category Articles:")
            for link in editor_links[:15]:
                # Highlight math-related
                if any(k in link['text'] for k in ['数式', 'KaTeX', 'TeX', '数学', 'formula']):
                    print(f"  ⭐ {link['text']}")
                else:
                    print(f"  • {link['text']}")

            print("\n⏸️ Browser open for 10 seconds...")
            await asyncio.sleep(10)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
