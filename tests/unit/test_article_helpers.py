"""Unit tests for article helper functions.

Tests for extract_article_id() and extract_article_key() which parse
MCP tool output text.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add e2e helpers to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent / "e2e" / "helpers"))
from article_helpers import (  # type: ignore[import-not-found]  # noqa: E402
    extract_article_id,
    extract_article_key,
)


class TestExtractArticleId:
    """Tests for extract_article_id function."""

    def test_extract_id_short_format(self) -> None:
        """'ID: 123456789' format should be matched."""
        result = "下書きを作成しました。ID: 123456789、キー: n1234567890ab"
        assert extract_article_id(result) == "123456789"

    def test_extract_id_japanese_format(self) -> None:
        """'記事ID: 123456789' format should be matched."""
        result = "✅ 下書きを作成しました\n   記事ID: 123456789\n"
        assert extract_article_id(result) == "123456789"

    def test_extract_id_full_success_message(self) -> None:
        """Full success message with all fields should be parsed correctly."""
        result = "✅ 下書きを作成しました\n   タイトル: Test Article\n   記事ID: 987654321\n   記事キー: n1234567890ab"
        assert extract_article_id(result) == "987654321"

    def test_extract_id_rejects_non_numeric_suffix(self) -> None:
        """Only numeric characters should be captured (not following text)."""
        result = "ID: 123456789abc"
        assert extract_article_id(result) == "123456789"

    def test_extract_id_not_found_raises_error(self) -> None:
        """ValueError should be raised when pattern is not found."""
        with pytest.raises(ValueError, match="Could not extract article ID"):
            extract_article_id("No ID here")

    def test_extract_id_with_extra_whitespace(self) -> None:
        """ID followed by multiple spaces should be handled."""
        result = "ID:   555555555"
        assert extract_article_id(result) == "555555555"


class TestExtractArticleKey:
    """Tests for extract_article_key function."""

    def test_extract_key_standard_format(self) -> None:
        """'記事キー: n1234567890ab' format should be matched."""
        result = "✅ 下書きを作成しました\n   記事キー: n1234567890ab"
        assert extract_article_key(result) == "n1234567890ab"

    def test_extract_key_from_full_message(self) -> None:
        """Full success message should be parsed correctly."""
        result = "✅ 下書きを作成しました\n   タイトル: Test Article\n   記事ID: 123456789\n   記事キー: nabcdef123456"
        assert extract_article_key(result) == "nabcdef123456"

    def test_extract_key_not_found_raises_error(self) -> None:
        """ValueError should be raised when pattern is not found."""
        with pytest.raises(ValueError, match="Could not extract article key"):
            extract_article_key("No key here")

    def test_extract_key_old_format_not_supported(self) -> None:
        """Old format '、キー: n...' is not supported by current regex.

        The current implementation only matches '記事キー:' format.
        This test documents the limitation.
        """
        result = "下書きを作成しました。ID: 123456789、キー: n1234567890ab"
        # Current regex uses 記事キー, so this will fail
        with pytest.raises(ValueError, match="Could not extract article key"):
            extract_article_key(result)
