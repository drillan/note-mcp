#!/usr/bin/env python3
"""Search for note.com articles with math formulas to understand how they work.

This script:
1. Searches for public note.com articles that contain math/formulas
2. Analyzes how they implemented the math rendering
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> int:
    """Search for math articles on note.com."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        try:
            # Search for articles about math/formulas on note.com
            search_url = "https://note.com/search?q=数式%20KaTeX&context=note&mode=search"
            print(f"🔍 Searching for math articles: {search_url}")

            await page.goto(search_url, wait_until="networkidle")
            await asyncio.sleep(2)

            await page.screenshot(path=Path("/tmp/math_search_results.png"))
            print("📸 Search results saved to /tmp/math_search_results.png")

            # Find article links
            articles = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('a[href*="/n/"]');
                const results = [];
                links.forEach(link => {
                    const href = link.getAttribute('href');
                    const text = link.textContent?.trim().substring(0, 100) || '';
                    if (href && !results.find(r => r.href === href)) {
                        results.push({ href, text });
                    }
                });
                return results.slice(0, 5);
            }
            """)

            print(f"\n📋 Found {len(articles)} articles:")
            for i, article in enumerate(articles):
                print(f"  {i+1}. {article['text'][:50]}...")
                print(f"     {article['href']}")

            # Visit first article to analyze
            if articles:
                first_url = articles[0]['href']
                if not first_url.startswith('http'):
                    first_url = f"https://note.com{first_url}"

                print(f"\n🌐 Visiting first article: {first_url}")
                await page.goto(first_url, wait_until="networkidle")
                await asyncio.sleep(2)

                # Check for math elements
                math_check = await page.evaluate("""
                () => {
                    const katex = document.querySelectorAll('.katex');
                    const nwcFormula = document.querySelectorAll('nwc-formula');
                    const mathJax = document.querySelectorAll('.MathJax, .mjx-container');

                    // Look for any math-like elements
                    const allScripts = document.querySelectorAll('script[type*="math"], script[type*="tex"]');

                    // Check for $ patterns in text
                    const bodyText = document.body.textContent || '';
                    const dollarPatterns = bodyText.match(/\\$[^$]+\\$/g) || [];

                    return {
                        katexCount: katex.length,
                        nwcFormulaCount: nwcFormula.length,
                        mathJaxCount: mathJax.length,
                        mathScripts: allScripts.length,
                        dollarPatterns: dollarPatterns.length,
                        katexSamples: [...katex].slice(0, 3).map(el => ({
                            text: el.textContent?.substring(0, 50) || '',
                            parentTag: el.parentElement?.tagName || '',
                        })),
                        nwcFormulaSamples: [...nwcFormula].slice(0, 3).map(el => ({
                            html: el.outerHTML.substring(0, 200),
                            isBlock: el.getAttribute('is-block'),
                        })),
                    };
                }
                """)

                print("\n📊 Math Elements Analysis:")
                print(f"  KaTeX elements: {math_check['katexCount']}")
                print(f"  nwc-formula elements: {math_check['nwcFormulaCount']}")
                print(f"  MathJax elements: {math_check['mathJaxCount']}")
                print(f"  Math scripts: {math_check['mathScripts']}")
                print(f"  $ patterns in text: {math_check['dollarPatterns']}")

                if math_check['katexSamples']:
                    print("\n  KaTeX Samples:")
                    for sample in math_check['katexSamples']:
                        print(f"    - {sample['text']} (parent: {sample['parentTag']})")

                if math_check['nwcFormulaSamples']:
                    print("\n  nwc-formula Samples:")
                    for sample in math_check['nwcFormulaSamples']:
                        print(f"    - {sample['html']}")

                await page.screenshot(path=Path("/tmp/math_article_example.png"))
                print("\n📸 Article screenshot saved to /tmp/math_article_example.png")

            # Also try searching for note.com's official documentation about formulas
            print("\n🔍 Searching for note.com formula documentation...")
            await page.goto("https://www.google.com/search?q=site:note.com+数式+書き方", wait_until="networkidle")
            await asyncio.sleep(2)

            await page.screenshot(path=Path("/tmp/note_formula_docs_search.png"))
            print("📸 Google search saved to /tmp/note_formula_docs_search.png")

            print("\n⏸️ Browser open for 15 seconds for inspection...")
            await asyncio.sleep(15)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
