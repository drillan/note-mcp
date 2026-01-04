#!/usr/bin/env python3
"""Get the raw HTML source of an article with formulas.

This will help understand how formulas are actually stored in note.com.
"""

import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> int:
    """Get article source with formulas."""
    # Article with formulas
    article_url = "https://note.com/show_ando/n/n13a51f700811"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        try:
            print(f"🌐 Visiting: {article_url}")
            await page.goto(article_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Scroll to load all content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # Get full page HTML
            html_content = await page.content()

            # Save full HTML
            output_path = Path("/tmp/formula_article_full.html")
            output_path.write_text(html_content)
            print(f"💾 Full HTML saved to {output_path}")

            # Extract and analyze nwc-formula elements
            formula_pattern = r"<nwc-formula[^>]*>[\s\S]*?</nwc-formula>"
            formulas = re.findall(formula_pattern, html_content)

            print(f"\n📊 Found {len(formulas)} nwc-formula elements:")
            for i, formula in enumerate(formulas[:5]):
                print(f"\n{'='*60}")
                print(f"Formula #{i}:")
                print(formula[:500])
                if len(formula) > 500:
                    print(f"... ({len(formula)} chars total)")

            # Also check if there are any script tags that handle formula rendering
            print("\n🔍 Checking for KaTeX/math-related scripts...")

            scripts_info = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                const mathScripts = [];

                scripts.forEach(script => {
                    const src = script.src || '';
                    const content = script.textContent?.substring(0, 200) || '';

                    if (src.includes('katex') ||
                        src.includes('math') ||
                        content.includes('katex') ||
                        content.includes('formula')) {
                        mathScripts.push({
                            src: src,
                            contentPreview: content.substring(0, 100),
                        });
                    }
                });

                // Check for KaTeX in stylesheets
                const styles = document.querySelectorAll('link[rel="stylesheet"]');
                const katexStyles = [];
                styles.forEach(style => {
                    if (style.href && style.href.includes('katex')) {
                        katexStyles.push(style.href);
                    }
                });

                return {
                    mathScripts: mathScripts,
                    katexStyles: katexStyles,
                    hasKatexCSS: katexStyles.length > 0,
                };
            }
            """)

            print(f"  KaTeX stylesheets: {scripts_info['katexStyles']}")
            print(f"  Math-related scripts: {len(scripts_info['mathScripts'])}")
            for script in scripts_info["mathScripts"][:3]:
                print(f"    - src: {script['src'][:100] if script['src'] else 'inline'}")

            # Check the actual article body element
            print("\n📝 Analyzing article body structure...")

            body_info = await page.evaluate("""
            () => {
                const articleBody = document.querySelector('[class*="article-body"], [class*="noteBody"], .p-bodyContainer');

                if (!articleBody) {
                    // Try alternative selectors
                    const article = document.querySelector('article');
                    if (article) {
                        const formulas = article.querySelectorAll('nwc-formula');
                        return {
                            selector: 'article',
                            formulaCount: formulas.length,
                            firstFormulaOuter: formulas[0]?.outerHTML.substring(0, 300) || '',
                            parentOfFormula: formulas[0]?.parentElement?.tagName || '',
                        };
                    }
                    return { error: 'No article body found' };
                }

                const formulas = articleBody.querySelectorAll('nwc-formula');

                return {
                    selector: 'article-body',
                    formulaCount: formulas.length,
                    firstFormulaOuter: formulas[0]?.outerHTML.substring(0, 300) || '',
                    parentOfFormula: formulas[0]?.parentElement?.tagName || '',
                };
            }
            """)

            print(f"  Article body selector: {body_info.get('selector', 'N/A')}")
            print(f"  Formula count in body: {body_info.get('formulaCount', 0)}")
            print(f"  Parent of formula: {body_info.get('parentOfFormula', 'N/A')}")

            # Most important: Check if KaTeX has rendered
            print("\n🎨 Checking KaTeX rendering status...")

            render_status = await page.evaluate("""
            () => {
                const formulas = document.querySelectorAll('nwc-formula');
                const results = [];

                formulas.forEach((f, i) => {
                    const katex = f.querySelector('.katex');
                    const katexHtml = f.querySelector('.katex-html');
                    const shadowRoot = f.shadowRoot;

                    results.push({
                        index: i,
                        hasKatex: !!katex,
                        hasKatexHtml: !!katexHtml,
                        hasShadowRoot: !!shadowRoot,
                        innerHTML: f.innerHTML.substring(0, 100),
                        childCount: f.childNodes.length,
                    });
                });

                return results;
            }
            """)

            for status in render_status:
                print(f"\n  Formula #{status['index']}:")
                print(f"    hasKatex: {status['hasKatex']}")
                print(f"    hasKatexHtml: {status['hasKatexHtml']}")
                print(f"    hasShadowRoot: {status['hasShadowRoot']}")
                print(f"    childCount: {status['childCount']}")
                print(f"    innerHTML preview: {status['innerHTML']}")

            # Take screenshot
            await page.screenshot(path=Path("/tmp/formula_article_source.png"), full_page=True)
            print("\n📸 Screenshot saved to /tmp/formula_article_source.png")

            print("\n⏸️ Browser open for 10 seconds...")
            await asyncio.sleep(10)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
