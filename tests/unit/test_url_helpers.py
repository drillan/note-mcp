"""Unit tests for URL helper utilities."""

from __future__ import annotations

import pytest

from note_mcp.browser.url_helpers import validate_article_edit_url


class TestValidateArticleEditUrl:
    """Test cases for validate_article_edit_url function.

    Current implementation validates URLs based on:
    1. /notes/{article_key} pattern in URL
    2. /n/{article_key} pattern in URL
    3. editor.note.com domain (allows any path)

    Note: Domain validation is intentionally relaxed to handle redirects
    and various note.com URL patterns during browser automation.
    """

    def test_valid_notes_path(self) -> None:
        """Test URL with /notes/{key}/edit/ path pattern."""
        assert validate_article_edit_url(
            "https://editor.note.com/notes/n12345abcdef/edit/",
            "n12345abcdef",
        )

    def test_valid_n_path(self) -> None:
        """Test URL with /n/{key} path pattern."""
        assert validate_article_edit_url(
            "https://note.com/n/n12345abcdef",
            "n12345abcdef",
        )

    def test_valid_editor_domain_with_key(self) -> None:
        """Test URL on editor.note.com domain with article key."""
        assert validate_article_edit_url(
            "https://editor.note.com/notes/n12345abcdef/edit/",
            "n12345abcdef",
        )

    def test_valid_editor_domain_only(self) -> None:
        """Test URL on editor.note.com domain without key pattern.

        Current implementation treats editor.note.com as valid even without key.
        This handles redirect scenarios during browser automation.
        """
        assert validate_article_edit_url(
            "https://editor.note.com/some/other/path",
            "n12345abcdef",
        )

    def test_valid_notes_pattern_any_domain(self) -> None:
        """Test that /notes/{key} pattern matches regardless of domain.

        Current implementation checks pattern presence, not domain.
        """
        # This is valid per current implementation (pattern-based)
        assert validate_article_edit_url(
            "https://other.com/notes/n12345abcdef",
            "n12345abcdef",
        )

    def test_invalid_wrong_key(self) -> None:
        """Test URL with wrong article key is invalid."""
        assert not validate_article_edit_url(
            "https://note.com/n/nwrongkey12345",
            "n12345abcdef",
        )

    def test_invalid_key_not_in_url(self) -> None:
        """Test URL without the article key is invalid."""
        assert not validate_article_edit_url(
            "https://note.com/some/other/path",
            "n12345abcdef",
        )

    def test_invalid_empty_url(self) -> None:
        """Test empty URL is invalid."""
        assert not validate_article_edit_url("", "n12345abcdef")

    @pytest.mark.parametrize(
        "url,article_key",
        [
            ("https://editor.note.com/notes/nabc123def456/edit/", "nabc123def456"),
            ("https://note.com/n/nabc123def456", "nabc123def456"),
            ("https://editor.note.com/drafts/nabc123def456", "nabc123def456"),
        ],
    )
    def test_various_valid_patterns(self, url: str, article_key: str) -> None:
        """Test various valid URL patterns."""
        assert validate_article_edit_url(url, article_key)

    @pytest.mark.parametrize(
        "url,article_key",
        [
            ("https://example.com/other/path", "n12345"),
            ("", "n12345"),
            ("https://note.com/user/articles", "nabc123"),
        ],
    )
    def test_various_invalid_patterns(self, url: str, article_key: str) -> None:
        """Test various invalid URL patterns (no key or editor.note.com)."""
        assert not validate_article_edit_url(url, article_key)
