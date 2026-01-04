#!/usr/bin/env python3
"""Inspect editor UI for math insertion options.

Analyzes the editor toolbar, menus, and any hidden UI elements
that might allow math/formula insertion.
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
    """Inspect editor UI for math insertion options."""
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

            # Analyze toolbar buttons
            print("\n📊 Analyzing editor toolbar...")

            toolbar_analysis = await page.evaluate("""
            () => {
                // Find all toolbar-like elements
                const toolbars = document.querySelectorAll('[class*="toolbar"], [class*="Toolbar"], [role="toolbar"]');
                const buttons = document.querySelectorAll('button');

                const toolbarInfo = [...toolbars].map(t => ({
                    className: t.className,
                    childCount: t.children.length,
                    innerHTML: t.innerHTML.substring(0, 500),
                }));

                // Find buttons with math-related attributes or content
                const mathButtons = [...buttons].filter(b => {
                    const text = b.textContent?.toLowerCase() || '';
                    const title = b.title?.toLowerCase() || '';
                    const ariaLabel = b.getAttribute('aria-label')?.toLowerCase() || '';
                    const className = b.className?.toLowerCase() || '';

                    return text.includes('math') ||
                           text.includes('formula') ||
                           text.includes('数式') ||
                           title.includes('math') ||
                           title.includes('formula') ||
                           ariaLabel.includes('math') ||
                           ariaLabel.includes('formula') ||
                           className.includes('math') ||
                           className.includes('formula');
                }).map(b => ({
                    text: b.textContent?.substring(0, 50),
                    title: b.title,
                    ariaLabel: b.getAttribute('aria-label'),
                    className: b.className,
                }));

                // Find all buttons with aria-labels (often toolbar buttons)
                const labeledButtons = [...buttons]
                    .filter(b => b.getAttribute('aria-label'))
                    .map(b => ({
                        ariaLabel: b.getAttribute('aria-label'),
                        title: b.title,
                        className: b.className?.substring(0, 50),
                    }));

                return {
                    toolbarCount: toolbars.length,
                    toolbarInfo: toolbarInfo.slice(0, 3),
                    mathButtons: mathButtons,
                    labeledButtonsCount: labeledButtons.length,
                    labeledButtons: labeledButtons.slice(0, 20),
                };
            }
            """)

            print(f"  Toolbars found: {toolbar_analysis['toolbarCount']}")
            print(f"  Math-related buttons: {len(toolbar_analysis['mathButtons'])}")
            for btn in toolbar_analysis['mathButtons']:
                print(f"    - {btn}")

            print(f"\n  Labeled buttons ({toolbar_analysis['labeledButtonsCount']} total):")
            for btn in toolbar_analysis['labeledButtons']:
                print(f"    - {btn['ariaLabel']}")

            # Now focus editor and check floating toolbar
            print("\n📝 Checking floating toolbar after text selection...")

            editor = page.locator(".ProseMirror")
            await editor.click()
            await asyncio.sleep(0.5)

            # Type some text
            await page.keyboard.type("Test text for selection")
            await asyncio.sleep(0.3)

            # Select all
            await page.keyboard.press("Control+a")
            await asyncio.sleep(0.5)

            floating_toolbar = await page.evaluate("""
            () => {
                // Look for floating toolbars that appear on selection
                const floatingElements = document.querySelectorAll(
                    '[class*="floating"], [class*="bubble"], [class*="popup"], [class*="tooltip"], [class*="selection"]'
                );

                // Also check for any newly visible elements
                const visibleButtons = [...document.querySelectorAll('button')]
                    .filter(b => {
                        const rect = b.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    })
                    .map(b => ({
                        text: b.textContent?.substring(0, 30),
                        ariaLabel: b.getAttribute('aria-label'),
                        title: b.title,
                    }));

                return {
                    floatingCount: floatingElements.length,
                    floatingClasses: [...floatingElements].map(e => e.className).slice(0, 5),
                    visibleButtonCount: visibleButtons.length,
                };
            }
            """)

            print(f"  Floating elements: {floating_toolbar['floatingCount']}")
            print(f"  Visible buttons: {floating_toolbar['visibleButtonCount']}")

            # Check the + menu (insert menu)
            print("\n➕ Checking insert (+) menu...")

            # Deselect
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)

            # Go to new line
            await page.keyboard.press("Control+End")
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.5)

            # Look for + button
            plus_button = await page.evaluate("""
            () => {
                // Find the + button for inserting blocks
                const buttons = document.querySelectorAll('button');
                const plusButtons = [...buttons].filter(b => {
                    const text = b.textContent?.trim();
                    const ariaLabel = b.getAttribute('aria-label') || '';
                    const title = b.title || '';

                    return text === '+' ||
                           text === '＋' ||
                           ariaLabel.includes('add') ||
                           ariaLabel.includes('insert') ||
                           ariaLabel.includes('追加') ||
                           title.includes('add') ||
                           title.includes('insert');
                });

                return plusButtons.map(b => ({
                    text: b.textContent?.substring(0, 20),
                    ariaLabel: b.getAttribute('aria-label'),
                    title: b.title,
                    className: b.className,
                    isVisible: b.getBoundingClientRect().width > 0,
                }));
            }
            """)

            print(f"  Plus buttons found: {len(plus_button)}")
            for btn in plus_button:
                print(f"    - {btn}")

            # Try clicking the + button if found
            add_button = page.locator('button[aria-label*="追加"], button:has-text("+"):visible').first
            if await add_button.count() > 0:
                print("\n  Clicking + button...")
                await add_button.click()
                await asyncio.sleep(0.5)

                menu_items = await page.evaluate("""
                () => {
                    // Get all menu items that appeared
                    const items = document.querySelectorAll(
                        '[role="menuitem"], [role="option"], [class*="menu"] button, [class*="menu"] li'
                    );

                    return [...items].map(item => ({
                        text: item.textContent?.substring(0, 50),
                        ariaLabel: item.getAttribute('aria-label'),
                        role: item.getAttribute('role'),
                    })).slice(0, 20);
                }
                """)

                print(f"  Menu items found: {len(menu_items)}")
                for item in menu_items:
                    text = item['text']
                    if text and ('math' in text.lower() or
                                'formula' in text.lower() or
                                '数式' in text or
                                'tex' in text.lower()):
                        print(f"    ⭐ MATH OPTION: {text}")
                    else:
                        print(f"    - {text}")

            # Check for ProseMirror node types
            print("\n🔧 Checking ProseMirror schema for formula support...")

            schema_info = await page.evaluate("""
            () => {
                // Try to access ProseMirror view/state
                const editor = document.querySelector('.ProseMirror');
                if (!editor) return { error: 'No editor found' };

                // Check for pmViewDesc (ProseMirror internal)
                const pmView = editor.pmViewDesc?.view || window.view;

                if (pmView && pmView.state && pmView.state.schema) {
                    const schema = pmView.state.schema;
                    const nodeTypes = Object.keys(schema.nodes.content || schema.nodes);
                    const markTypes = Object.keys(schema.marks.content || schema.marks);

                    return {
                        hasSchema: true,
                        nodeTypes: nodeTypes,
                        markTypes: markTypes,
                        hasFormulaNode: nodeTypes.includes('formula') || nodeTypes.includes('nwc-formula') || nodeTypes.includes('math'),
                    };
                }

                // Alternative: check for node views
                const nodeViews = editor.querySelectorAll('[data-node-view-wrapper], [pm-node-view]');

                return {
                    hasSchema: false,
                    nodeViewCount: nodeViews.length,
                };
            }
            """)

            print(f"  Schema access: {schema_info.get('hasSchema', False)}")
            if schema_info.get('nodeTypes'):
                print(f"  Node types: {schema_info['nodeTypes']}")
                print(f"  Has formula node: {schema_info.get('hasFormulaNode', False)}")
            if schema_info.get('markTypes'):
                print(f"  Mark types: {schema_info['markTypes']}")

            # Save detailed analysis
            output_path = Path("/tmp/editor_ui_analysis.json")
            output_path.write_text(json.dumps({
                "toolbar": toolbar_analysis,
                "floating": floating_toolbar,
                "plusButton": plus_button,
                "schema": schema_info,
            }, ensure_ascii=False, indent=2))
            print(f"\n💾 Detailed analysis saved to {output_path}")

            # Take screenshot
            await page.screenshot(path=Path("/tmp/editor_ui_analysis.png"))
            print("📸 Screenshot saved to /tmp/editor_ui_analysis.png")

            print("\n⏸️ Browser open for 15 seconds for inspection...")
            await asyncio.sleep(15)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
