#!/usr/bin/env python3
"""Investigate ProseMirror schema and math insertion capability.

This script examines note.com's ProseMirror editor to understand:
1. Available node types in the schema
2. If nwc-formula is a valid node type
3. How to programmatically insert math formulas
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
    """Investigate ProseMirror schema for math support."""
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

            # Investigate ProseMirror schema and view
            result = await page.evaluate("""
            () => {
                const editor = document.querySelector('.ProseMirror');
                if (!editor) return { error: 'No ProseMirror editor found' };

                // Try to access ProseMirror view
                const pmView = editor.pmView || editor.__vue__?.pmView;

                if (!pmView) {
                    // Alternative: look for global PM objects
                    const pmKeys = Object.keys(window).filter(k =>
                        k.toLowerCase().includes('prosemirror') ||
                        k.toLowerCase().includes('editor') ||
                        k === 'view'
                    );

                    return {
                        error: 'Cannot access ProseMirror view',
                        possiblePmKeys: pmKeys.slice(0, 20),
                        editorAttributes: Object.keys(editor).filter(k => !k.startsWith('__')).slice(0, 30),
                        editorClassName: editor.className,
                    };
                }

                // Get schema info
                const schema = pmView.state?.schema;
                if (!schema) return { error: 'No schema found', hasView: true };

                const nodeTypes = Object.keys(schema.nodes || {});
                const markTypes = Object.keys(schema.marks || {});

                // Check for formula-related types
                const formulaNode = schema.nodes?.nwc_formula || schema.nodes?.formula || schema.nodes?.math;

                return {
                    nodeTypes: nodeTypes,
                    markTypes: markTypes,
                    hasFormulaNode: !!formulaNode,
                    formulaNodeName: formulaNode ? formulaNode.name : null,
                    formulaSpec: formulaNode ? JSON.stringify(formulaNode.spec, null, 2) : null,
                };
            }
            """)

            print("\n📊 ProseMirror Investigation Results:")
            print("=" * 50)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("=" * 50)

            # If we couldn't access view, try alternative approach
            if result.get("error"):
                print("\n🔍 Trying alternative approach to find ProseMirror...")

                # Try to find via React/Vue internals
                result2 = await page.evaluate("""
                () => {
                    // Look for React fiber
                    const editor = document.querySelector('.ProseMirror');
                    if (!editor) return { error: 'No editor' };

                    // Check for React internals
                    const reactKey = Object.keys(editor).find(k => k.startsWith('__reactFiber'));
                    const vueKey = Object.keys(editor).find(k => k.startsWith('__vue'));

                    // Try to find the view through DOM traversal
                    let current = editor;
                    let depth = 0;
                    const searchResults = [];

                    while (current && depth < 10) {
                        const keys = Object.keys(current).filter(k =>
                            typeof current[k] === 'object' &&
                            current[k] !== null &&
                            !k.startsWith('__')
                        );

                        for (const key of keys) {
                            try {
                                const obj = current[key];
                                if (obj && obj.state && obj.state.schema) {
                                    searchResults.push({
                                        found: true,
                                        path: key,
                                        nodeTypes: Object.keys(obj.state.schema.nodes || {}),
                                        markTypes: Object.keys(obj.state.schema.marks || {}),
                                    });
                                }
                            } catch (e) {}
                        }

                        current = current.parentElement;
                        depth++;
                    }

                    // Also check window for editor instances
                    const windowKeys = Object.keys(window).filter(k => {
                        try {
                            const v = window[k];
                            return v && typeof v === 'object' && v.state && v.state.schema;
                        } catch { return false; }
                    });

                    return {
                        reactKey: !!reactKey,
                        vueKey: !!vueKey,
                        searchResults: searchResults,
                        windowEditorKeys: windowKeys,
                    };
                }
                """)

                print("\n📊 Alternative Investigation Results:")
                print(json.dumps(result2, indent=2, ensure_ascii=False))

            # Try inserting a formula via JS command
            print("\n🧪 Testing direct DOM insertion of nwc-formula...")

            insert_result = await page.evaluate("""
            () => {
                const editor = document.querySelector('.ProseMirror');
                if (!editor) return { error: 'No editor' };

                // First, let's see if nwc-formula is a registered custom element
                const isCustomElement = customElements.get('nwc-formula') !== undefined;

                // Try direct DOM insertion at the end
                const formula = document.createElement('nwc-formula');
                formula.setAttribute('is-block', 'false');
                formula.textContent = 'E=mc^2';

                // Find a paragraph to insert into
                const paragraphs = editor.querySelectorAll('p');
                if (paragraphs.length > 0) {
                    const lastP = paragraphs[paragraphs.length - 1];
                    lastP.appendChild(document.createTextNode(' Test: '));
                    lastP.appendChild(formula);

                    // Trigger input event to notify ProseMirror
                    editor.dispatchEvent(new InputEvent('input', { bubbles: true }));

                    return {
                        success: true,
                        isCustomElement: isCustomElement,
                        message: 'Inserted nwc-formula via DOM',
                        insertedHtml: formula.outerHTML,
                    };
                }

                return {
                    success: false,
                    isCustomElement: isCustomElement,
                    error: 'No paragraphs found',
                };
            }
            """)

            print("\n📊 DOM Insertion Result:")
            print(json.dumps(insert_result, indent=2, ensure_ascii=False))

            # Take screenshot
            await page.screenshot(path=Path("/tmp/prosemirror_investigation.png"))
            print("\n📸 Screenshot saved to /tmp/prosemirror_investigation.png")

            # Check if the formula survived
            await asyncio.sleep(1)

            check_result = await page.evaluate("""
            () => {
                const editor = document.querySelector('.ProseMirror');
                const formulas = editor?.querySelectorAll('nwc-formula') || [];
                const katex = editor?.querySelectorAll('.katex') || [];

                return {
                    formulaCount: formulas.length,
                    katexCount: katex.length,
                    editorHtml: editor?.innerHTML.substring(0, 2000) || 'No editor',
                };
            }
            """)

            print("\n📊 Post-Insertion Check:")
            print(f"  nwc-formula count: {check_result['formulaCount']}")
            print(f"  katex count: {check_result['katexCount']}")

            # Try clicking save to see if formula persists
            print("\n💾 Attempting to save draft...")

            save_button = page.locator('button:has-text("下書き保存")')
            if await save_button.count() > 0:
                await save_button.click()
                await asyncio.sleep(2)

                # Reload and check
                await page.reload(wait_until="networkidle")
                await asyncio.sleep(2)

                after_save = await page.evaluate("""
                () => {
                    const editor = document.querySelector('.ProseMirror');
                    const formulas = editor?.querySelectorAll('nwc-formula') || [];
                    const katex = editor?.querySelectorAll('.katex') || [];
                    const text = editor?.textContent || '';

                    return {
                        formulaCount: formulas.length,
                        katexCount: katex.length,
                        hasTestText: text.includes('Test:'),
                        hasFormula: text.includes('E=mc^2'),
                    };
                }
                """)

                print("\n📊 After Save & Reload:")
                print(json.dumps(after_save, indent=2, ensure_ascii=False))

                if after_save['formulaCount'] > 0:
                    print("\n✅ SUCCESS: nwc-formula PERSISTS after save!")
                else:
                    print("\n❌ FAILURE: nwc-formula was stripped on save")

            print("\n⏸️ Browser open for 10 seconds for inspection...")
            await asyncio.sleep(10)

            return 0

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
