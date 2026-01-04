#!/usr/bin/env python3
"""Analyze a note.com article that has nwc-formula elements.

This script examines how formulas are implemented in an actual published article.
"""

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> int:
    """Analyze article with formulas."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        try:
            # Article we found that has nwc-formula elements
            article_url = "https://note.com/show_ando/n/n13a51f700811"
            print(f"🌐 Visiting article with formulas: {article_url}")

            await page.goto(article_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Scroll down to load all content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # Deep analysis of formula elements
            analysis = await page.evaluate("""
            () => {
                const formulas = document.querySelectorAll('nwc-formula');
                const results = {
                    totalFormulas: formulas.length,
                    formulas: [],
                    parentInfo: [],
                    articleType: null,
                    articleMeta: {},
                };

                // Get article metadata
                const metaTags = document.querySelectorAll('meta');
                metaTags.forEach(meta => {
                    const property = meta.getAttribute('property') || meta.getAttribute('name');
                    const content = meta.getAttribute('content');
                    if (property && content) {
                        results.articleMeta[property] = content.substring(0, 200);
                    }
                });

                // Check article type indicators
                const typeIndicators = document.querySelectorAll('[class*="type"], [data-type]');
                typeIndicators.forEach(el => {
                    const type = el.getAttribute('data-type') || el.className;
                    if (type) results.articleType = type;
                });

                // Analyze each formula
                formulas.forEach((formula, i) => {
                    if (i >= 5) return; // Limit to first 5

                    const formulaInfo = {
                        index: i,
                        isBlock: formula.getAttribute('is-block'),
                        latex: formula.textContent?.substring(0, 300) || '',
                        outerHtml: formula.outerHTML.substring(0, 500),
                        parentTag: formula.parentElement?.tagName || 'unknown',
                        parentClass: formula.parentElement?.className || '',
                        hasKatex: formula.querySelector('.katex') !== null,
                        attributes: {},
                    };

                    // Get all attributes
                    for (const attr of formula.attributes) {
                        formulaInfo.attributes[attr.name] = attr.value;
                    }

                    results.formulas.push(formulaInfo);
                });

                // Check for KaTeX scripts/styles
                const katexScripts = document.querySelectorAll('script[src*="katex"], link[href*="katex"]');
                results.katexResources = katexScripts.length;

                // Check body classes
                results.bodyClass = document.body.className;

                // Check for note type in URL or page
                const noteType = document.querySelector('[class*="noteType"], [data-note-type]');
                if (noteType) {
                    results.detectedNoteType = noteType.textContent || noteType.getAttribute('data-note-type');
                }

                return results;
            }
            """)

            print("\n📊 Formula Article Analysis:")
            print("=" * 60)
            print(f"Total formulas: {analysis['totalFormulas']}")
            print(f"Article type: {analysis.get('articleType', 'unknown')}")
            print(f"Body class: {analysis.get('bodyClass', '')}")
            print(f"KaTeX resources: {analysis.get('katexResources', 0)}")

            print("\n📝 Formula Details:")
            for formula in analysis.get('formulas', []):
                print(f"\n  Formula #{formula['index']}:")
                print(f"    is-block: {formula['isBlock']}")
                print(f"    has KaTeX rendered: {formula['hasKatex']}")
                print(f"    parent: {formula['parentTag']} ({formula['parentClass'][:50]})")
                print(f"    attributes: {formula['attributes']}")
                print(f"    LaTeX: {formula['latex'][:100]}...")

            print("\n📋 Relevant Meta Tags:")
            for key, value in analysis.get('articleMeta', {}).items():
                if any(k in key.lower() for k in ['type', 'note', 'og:', 'article']):
                    print(f"  {key}: {value}")

            # Take screenshot showing formulas
            await page.screenshot(path=Path("/tmp/formula_article_analysis.png"), full_page=True)
            print("\n📸 Full page screenshot saved to /tmp/formula_article_analysis.png")

            # Check if there's a specific article type that supports formulas
            print("\n🔍 Checking if this is a special article type...")

            # Look at page source for clues
            page_html = await page.content()

            # Check for any mention of premium/pro features
            if 'premium' in page_html.lower() or 'pro' in page_html.lower():
                print("  ⚠️ This might be a premium feature")

            # Check for any mention of formula/math in scripts
            if 'formula' in page_html.lower():
                print("  ✅ Page contains 'formula' references")
            if 'katex' in page_html.lower():
                print("  ✅ Page contains 'katex' references")
            if 'nwc-formula' in page_html.lower():
                print("  ✅ Page contains 'nwc-formula' element")

            # Save detailed analysis
            output_path = Path("/tmp/formula_article_analysis.json")
            output_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2))
            print(f"\n💾 Detailed analysis saved to {output_path}")

            print("\n⏸️ Browser open for 15 seconds for inspection...")
            await asyncio.sleep(15)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
