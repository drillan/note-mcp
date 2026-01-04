#!/usr/bin/env python3
"""Capture note.com help page about math syntax.

Visit the help page and capture its content to understand
how users are supposed to input math formulas.
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> int:
    """Capture help page about math syntax."""
    help_url = "https://www.help-note.com/hc/ja/articles/4410665086873-数式記法の使い方"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 1200})
        page = await context.new_page()

        try:
            print(f"🌐 Visiting: {help_url}")
            response = await page.goto(help_url, wait_until="networkidle")

            if response and response.status == 403:
                print("❌ Access denied (403). Trying alternative...")
                # Try without specific article
                help_url = "https://www.help-note.com/hc/ja"
                await page.goto(help_url, wait_until="networkidle")

            await asyncio.sleep(2)

            # Get page content
            content = await page.evaluate("""
            () => {
                const article = document.querySelector('article, .article-body, [class*="article"]');
                const main = document.querySelector('main, [role="main"]');
                const body = document.body;

                return {
                    title: document.title,
                    url: window.location.href,
                    articleText: article?.textContent?.substring(0, 3000) || '',
                    mainText: main?.textContent?.substring(0, 3000) || '',
                    h1: document.querySelector('h1')?.textContent || '',
                    h2s: [...document.querySelectorAll('h2')].map(h => h.textContent).slice(0, 10),
                };
            }
            """)

            print(f"\n📄 Page: {content['title']}")
            print(f"🔗 URL: {content['url']}")
            print(f"📌 H1: {content['h1']}")
            print(f"📌 H2s: {content['h2s']}")

            if content['articleText']:
                print(f"\n📝 Article content (first 2000 chars):")
                print(content['articleText'][:2000])

            # Take full page screenshot
            await page.screenshot(path=Path("/tmp/help_page.png"), full_page=True)
            print("\n📸 Screenshot saved to /tmp/help_page.png")

            # Also search for math-related articles
            print("\n🔍 Searching for math-related help articles...")

            # Try search
            search_url = "https://www.help-note.com/hc/ja/search?query=数式"
            await page.goto(search_url, wait_until="networkidle")
            await asyncio.sleep(2)

            search_results = await page.evaluate("""
            () => {
                const results = document.querySelectorAll('[class*="search-result"], [class*="article-list"] a, a[href*="/articles/"]');
                return [...results].map(r => ({
                    text: r.textContent?.substring(0, 100),
                    href: r.href,
                })).slice(0, 10);
            }
            """)

            print(f"\nSearch results for '数式':")
            for r in search_results:
                if '数式' in r['text'] or 'math' in r['text'].lower():
                    print(f"  ⭐ {r['text']}")
                    print(f"     {r['href']}")
                else:
                    print(f"  - {r['text'][:50]}")

            await page.screenshot(path=Path("/tmp/help_search.png"), full_page=True)
            print("\n📸 Search screenshot saved to /tmp/help_search.png")

            print("\n⏸️ Browser open for 10 seconds...")
            await asyncio.sleep(10)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
