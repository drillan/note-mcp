#!/usr/bin/env python3
"""Check Shadow DOM inside nwc-formula elements.

Since nwc-formula uses Shadow DOM for rendering KaTeX,
we need to query inside the shadow root.
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> int:
    """Check Shadow DOM inside nwc-formula."""
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

            # Check Shadow DOM contents
            shadow_analysis = await page.evaluate("""
            () => {
                const formulas = document.querySelectorAll('nwc-formula');
                const results = [];

                formulas.forEach((formula, i) => {
                    const shadowRoot = formula.shadowRoot;
                    if (!shadowRoot) {
                        results.push({ index: i, error: 'No shadow root' });
                        return;
                    }

                    // Query inside shadow root
                    const katex = shadowRoot.querySelector('.katex');
                    const katexHtml = shadowRoot.querySelector('.katex-html');
                    const katexDisplay = shadowRoot.querySelector('.katex-display');

                    // Get shadow root HTML
                    const shadowHtml = shadowRoot.innerHTML;

                    results.push({
                        index: i,
                        hasShadowRoot: true,
                        shadowHtmlLength: shadowHtml.length,
                        shadowHtmlPreview: shadowHtml.substring(0, 500),
                        hasKatexInShadow: !!katex,
                        hasKatexHtmlInShadow: !!katexHtml,
                        hasKatexDisplayInShadow: !!katexDisplay,
                        // Get the rendered text
                        renderedText: katex?.textContent?.substring(0, 100) || '',
                    });
                });

                return results;
            }
            """)

            print("\n📊 Shadow DOM Analysis:")
            print("=" * 60)

            for result in shadow_analysis:
                print(f"\nFormula #{result['index']}:")
                if result.get("error"):
                    print(f"  ❌ Error: {result['error']}")
                    continue

                print(f"  hasShadowRoot: {result['hasShadowRoot']}")
                print(f"  Shadow HTML length: {result['shadowHtmlLength']} chars")
                print(f"  hasKatexInShadow: {result['hasKatexInShadow']}")
                print(f"  hasKatexHtmlInShadow: {result['hasKatexHtmlInShadow']}")
                print(f"  hasKatexDisplayInShadow: {result['hasKatexDisplayInShadow']}")
                print(f"  renderedText: {result['renderedText']}")
                print(f"\n  Shadow HTML preview:")
                print(f"  {result['shadowHtmlPreview'][:300]}...")

            # Most importantly - check HOW formulas were created
            print("\n\n🔍 Checking how nwc-formula is defined (custom element)...")

            element_definition = await page.evaluate("""
            () => {
                const formulaElement = customElements.get('nwc-formula');

                if (!formulaElement) {
                    return { error: 'nwc-formula not registered' };
                }

                // Get constructor info
                const constructor = formulaElement.toString().substring(0, 500);

                // Check if there's a template or slot
                const testFormula = document.querySelector('nwc-formula');
                const shadowRoot = testFormula?.shadowRoot;

                // Get all styles in shadow root
                const styles = shadowRoot ? [...shadowRoot.querySelectorAll('style')].map(s => s.textContent?.substring(0, 200) || '') : [];

                // Check for katex script loading
                const scripts = shadowRoot ? [...shadowRoot.querySelectorAll('script')].length : 0;

                return {
                    isRegistered: true,
                    constructorPreview: constructor,
                    shadowStyles: styles.length,
                    shadowScripts: scripts,
                };
            }
            """)

            print(f"  nwc-formula registered: {element_definition.get('isRegistered', False)}")
            print(f"  Shadow styles count: {element_definition.get('shadowStyles', 0)}")
            print(f"  Shadow scripts count: {element_definition.get('shadowScripts', 0)}")

            # Take screenshot of rendered formulas
            # First formula
            first_formula = page.locator("nwc-formula").first
            if await first_formula.count() > 0:
                await first_formula.screenshot(path=Path("/tmp/formula_rendered.png"))
                print("\n📸 Formula screenshot saved to /tmp/formula_rendered.png")

            print("\n⏸️ Browser open for 10 seconds...")
            await asyncio.sleep(10)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
