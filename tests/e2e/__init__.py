"""E2E tests for note-mcp Markdown conversion verification.

This package contains end-to-end tests that verify Markdown-to-HTML
conversion on note.com's actual preview pages using Playwright.

Tests in this package require:
- Valid note.com authentication (session)
- Network connectivity to note.com
- Browser automation via Playwright

Usage:
    pytest tests/e2e/ -v --tb=short

Note:
    Tests are marked with @pytest.mark.e2e and @pytest.mark.requires_auth.
    They are skipped by default unless explicitly run.
"""
