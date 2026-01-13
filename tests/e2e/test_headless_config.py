"""Tests for Playwright headless configuration.

Verifies that the headless mode default is correctly set to True
and can be overridden via environment variable.

Issue #160: Playwrightテストをデフォルトheadlessに変更
"""

from __future__ import annotations

import os
from unittest.mock import patch


class TestIsHeadlessTest:
    """Tests for _is_headless_test() function in conftest.py."""

    def test_default_returns_true(self) -> None:
        """Default (no env var) should return True for headless mode."""
        from tests.e2e.conftest import _is_headless_test

        # Remove env var if set
        with patch.dict(os.environ, {}, clear=True):
            # Ensure the specific var is not set
            os.environ.pop("NOTE_MCP_TEST_HEADLESS", None)
            result = _is_headless_test()

        assert result is True, "Default should be headless (True)"

    def test_env_false_returns_false(self) -> None:
        """NOTE_MCP_TEST_HEADLESS=false should return False (headed mode)."""
        from tests.e2e.conftest import _is_headless_test

        with patch.dict(os.environ, {"NOTE_MCP_TEST_HEADLESS": "false"}):
            result = _is_headless_test()

        assert result is False, "false should return headed mode"

    def test_env_true_returns_true(self) -> None:
        """NOTE_MCP_TEST_HEADLESS=true should return True (headless mode)."""
        from tests.e2e.conftest import _is_headless_test

        with patch.dict(os.environ, {"NOTE_MCP_TEST_HEADLESS": "true"}):
            result = _is_headless_test()

        assert result is True, "true should return headless mode"

    def test_env_case_insensitive(self) -> None:
        """Environment variable should be case-insensitive."""
        from tests.e2e.conftest import _is_headless_test

        # Test FALSE (uppercase)
        with patch.dict(os.environ, {"NOTE_MCP_TEST_HEADLESS": "FALSE"}):
            result = _is_headless_test()
        assert result is False, "FALSE should return headed mode"

        # Test True (mixed case)
        with patch.dict(os.environ, {"NOTE_MCP_TEST_HEADLESS": "True"}):
            result = _is_headless_test()
        assert result is True, "True should return headless mode"


class TestPreviewPageContextHeadless:
    """Tests for preview_page_context() headless default in preview_helpers.py."""

    def test_get_headless_default_returns_true(self) -> None:
        """Default (no env var) should return True for headless mode."""
        from tests.e2e.helpers.preview_helpers import _get_headless_default

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NOTE_MCP_TEST_HEADLESS", None)
            result = _get_headless_default()

        assert result is True, "Default should be headless (True)"

    def test_get_headless_default_env_false(self) -> None:
        """NOTE_MCP_TEST_HEADLESS=false should return False."""
        from tests.e2e.helpers.preview_helpers import _get_headless_default

        with patch.dict(os.environ, {"NOTE_MCP_TEST_HEADLESS": "false"}):
            result = _get_headless_default()

        assert result is False, "false should return headed mode"

    def test_get_headless_default_env_true(self) -> None:
        """NOTE_MCP_TEST_HEADLESS=true should return True."""
        from tests.e2e.helpers.preview_helpers import _get_headless_default

        with patch.dict(os.environ, {"NOTE_MCP_TEST_HEADLESS": "true"}):
            result = _get_headless_default()

        assert result is True, "true should return headless mode"


class TestBrowserManagerHeadless:
    """Tests for BrowserManager headless configuration in manager.py."""

    def test_headless_env_var_name(self) -> None:
        """BrowserManager should use NOTE_MCP_TEST_HEADLESS env var."""
        # This test verifies the env var name is consistent with test fixtures
        # by checking the actual implementation
        import inspect

        from note_mcp.browser.manager import BrowserManager

        source = inspect.getsource(BrowserManager._ensure_browser)
        assert "NOTE_MCP_TEST_HEADLESS" in source, "BrowserManager should use NOTE_MCP_TEST_HEADLESS env var"

    def test_headless_default_is_true(self) -> None:
        """BrowserManager should default to headless=True."""
        import inspect

        from note_mcp.browser.manager import BrowserManager

        source = inspect.getsource(BrowserManager._ensure_browser)
        # Check that default is "true" (headless by default)
        assert '"true"' in source.lower() or "'true'" in source.lower(), (
            "BrowserManager should default to headless=True"
        )
