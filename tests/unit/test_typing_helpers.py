"""Unit tests for typing helpers module."""

from note_mcp.browser.typing_helpers import (
    _BLOCKQUOTE_PATTERN,
    _CITATION_PATTERN,
    _CITATION_URL_PATTERN,
    _ORDERED_LIST_PATTERN,
    _UNORDERED_LIST_PATTERN,
)


class TestUnorderedListPattern:
    """Tests for unordered list pattern detection."""

    def test_matches_dash_list_item(self) -> None:
        """Test that dash list items are detected."""
        match = _UNORDERED_LIST_PATTERN.match("- Item text")
        assert match is not None
        assert match.group(1) == "Item text"

    def test_matches_asterisk_list_item(self) -> None:
        """Test that asterisk list items are detected."""
        match = _UNORDERED_LIST_PATTERN.match("* Item text")
        assert match is not None
        assert match.group(1) == "Item text"

    def test_matches_plus_list_item(self) -> None:
        """Test that plus list items are detected."""
        match = _UNORDERED_LIST_PATTERN.match("+ Item text")
        assert match is not None
        assert match.group(1) == "Item text"

    def test_requires_space_after_marker(self) -> None:
        """Test that space after marker is required."""
        match = _UNORDERED_LIST_PATTERN.match("-Item text")
        assert match is None

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _UNORDERED_LIST_PATTERN.match("Regular text")
        assert match is None


class TestOrderedListPattern:
    """Tests for ordered list pattern detection."""

    def test_matches_numbered_list_item(self) -> None:
        """Test that numbered list items are detected."""
        match = _ORDERED_LIST_PATTERN.match("1. First item")
        assert match is not None
        assert match.group(1) == "1"
        assert match.group(2) == "First item"

    def test_matches_multi_digit_number(self) -> None:
        """Test that multi-digit numbers are detected."""
        match = _ORDERED_LIST_PATTERN.match("123. Item text")
        assert match is not None
        assert match.group(1) == "123"

    def test_requires_period_and_space(self) -> None:
        """Test that period and space are required."""
        match = _ORDERED_LIST_PATTERN.match("1 Item text")
        assert match is None

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _ORDERED_LIST_PATTERN.match("Regular text")
        assert match is None


class TestBlockquotePattern:
    """Tests for blockquote pattern detection."""

    def test_matches_blockquote_line(self) -> None:
        """Test that blockquote lines are detected."""
        match = _BLOCKQUOTE_PATTERN.match("> Quote text")
        assert match is not None
        assert match.group(1) == "Quote text"

    def test_matches_empty_blockquote(self) -> None:
        """Test that empty blockquotes are detected."""
        match = _BLOCKQUOTE_PATTERN.match("> ")
        assert match is not None
        assert match.group(1) == ""

    def test_matches_blockquote_without_space(self) -> None:
        """Test that blockquote without space after > is detected."""
        match = _BLOCKQUOTE_PATTERN.match(">Quote text")
        assert match is not None
        assert match.group(1) == "Quote text"

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _BLOCKQUOTE_PATTERN.match("Regular text")
        assert match is None


class TestCitationPattern:
    """Tests for citation pattern detection (em-dash at start)."""

    def test_matches_citation_with_text(self) -> None:
        """Test that citation with text is detected."""
        match = _CITATION_PATTERN.match("— フランシス・ベーコン")
        assert match is not None
        assert match.group(1) == "フランシス・ベーコン"

    def test_matches_citation_with_url(self) -> None:
        """Test that citation with URL is detected."""
        match = _CITATION_PATTERN.match("— Source (https://example.com)")
        assert match is not None
        assert match.group(1) == "Source (https://example.com)"

    def test_requires_em_dash_at_start(self) -> None:
        """Test that em-dash must be at the start."""
        match = _CITATION_PATTERN.match("Text — Author")
        assert match is None

    def test_requires_space_after_em_dash(self) -> None:
        """Test that space after em-dash is required."""
        match = _CITATION_PATTERN.match("—Author")
        assert match is None

    def test_no_match_for_regular_dash(self) -> None:
        """Test that regular dash is not matched."""
        match = _CITATION_PATTERN.match("- Author")
        assert match is None


class TestCitationUrlPattern:
    """Tests for citation URL extraction pattern."""

    def test_extracts_text_and_url(self) -> None:
        """Test that text and URL are extracted."""
        match = _CITATION_URL_PATTERN.match("Source (https://example.com)")
        assert match is not None
        assert match.group(1) == "Source"
        assert match.group(2) == "https://example.com"

    def test_extracts_text_with_spaces(self) -> None:
        """Test that text with spaces is extracted."""
        match = _CITATION_URL_PATTERN.match("Francis Bacon (https://example.com)")
        assert match is not None
        assert match.group(1) == "Francis Bacon"
        assert match.group(2) == "https://example.com"

    def test_handles_japanese_text(self) -> None:
        """Test that Japanese text is handled."""
        match = _CITATION_URL_PATTERN.match("フランシス・ベーコン (https://example.com)")
        assert match is not None
        assert match.group(1) == "フランシス・ベーコン"

    def test_no_match_without_url(self) -> None:
        """Test that text without URL is not matched."""
        match = _CITATION_URL_PATTERN.match("Plain text")
        assert match is None

    def test_no_match_with_empty_parens(self) -> None:
        """Test that empty parentheses are not matched."""
        match = _CITATION_URL_PATTERN.match("Text ()")
        assert match is None

    def test_no_match_with_spaces_in_parens(self) -> None:
        """Test that spaces in parentheses are not matched as URL."""
        match = _CITATION_URL_PATTERN.match("Text (not a url)")
        assert match is None


class TestCitationExtractionWorkflow:
    """Integration-style tests for citation extraction workflow."""

    def test_blockquote_with_citation_detection(self) -> None:
        """Test detecting citation in blockquote content."""
        blockquote_content = "— フランシス・ベーコン"
        match = _CITATION_PATTERN.match(blockquote_content)
        assert match is not None
        citation_text = match.group(1)
        assert citation_text == "フランシス・ベーコン"

    def test_citation_with_url_extraction(self) -> None:
        """Test extracting URL from citation."""
        citation = "フランシス・ベーコン (https://example.com)"
        url_match = _CITATION_URL_PATTERN.match(citation)
        assert url_match is not None
        text = url_match.group(1).strip()
        url = url_match.group(2)
        assert text == "フランシス・ベーコン"
        assert url == "https://example.com"

    def test_citation_without_url_extraction(self) -> None:
        """Test citation without URL returns text only."""
        citation = "フランシス・ベーコン"
        url_match = _CITATION_URL_PATTERN.match(citation)
        assert url_match is None
        # When no URL, use citation text as-is
        assert citation == "フランシス・ベーコン"
