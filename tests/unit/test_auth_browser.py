"""Unit tests for auth/browser.py.

Tests for Article 6 compliance in browser-based authentication.
"""

from __future__ import annotations


class TestLoginArticle6Compliance:
    """Tests for Article 6 compliance in login function.

    Article 6 (Data Accuracy Mandate) requires:
    - No placeholder values like "unknown"
    - Missing required data must raise an error
    """

    def test_no_unknown_placeholder_in_source_code(self) -> None:
        """Verify that 'unknown' placeholder is not used in browser.py.

        Article 6: Placeholder values violate data accuracy requirements.
        This test ensures the code doesn't fall back to 'unknown' for user info.
        """
        from pathlib import Path

        browser_py = Path(__file__).parent.parent.parent / "src" / "note_mcp" / "auth" / "browser.py"
        content = browser_py.read_text()

        # Check that "unknown" placeholder pattern is not present
        # The old pattern was: user_id = "unknown" / username = "unknown"
        assert 'user_id = "unknown"' not in content, "Article 6 violation: 'user_id = \"unknown\"' placeholder found"
        assert 'username = "unknown"' not in content, "Article 6 violation: 'username = \"unknown\"' placeholder found"

    def test_error_raised_on_user_info_failure(self) -> None:
        """Verify that ValueError is raised instead of using placeholders.

        Article 6: Missing required data must raise an error, not use defaults.
        """
        from pathlib import Path

        browser_py = Path(__file__).parent.parent.parent / "src" / "note_mcp" / "auth" / "browser.py"
        content = browser_py.read_text()

        # Verify that the error is raised with meaningful message
        assert "raise ValueError" in content, "Expected ValueError to be raised when user info cannot be retrieved"
        assert "Failed to retrieve user information" in content, (
            "Expected meaningful error message about user info retrieval failure"
        )
