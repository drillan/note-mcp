"""Unit tests for typing helpers module."""

from unittest.mock import AsyncMock

import pytest

from note_mcp.browser.typing_helpers import (
    _BLOCKQUOTE_PATTERN,
    _CITATION_PATTERN,
    _CITATION_URL_PATTERN,
    _CODE_FENCE_PATTERN,
    _ORDERED_LIST_PATTERN,
    _STRIKETHROUGH_PATTERN,
    _UNORDERED_LIST_PATTERN,
    _type_with_strikethrough,
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


class TestCodeFencePattern:
    """Tests for code fence pattern detection."""

    def test_matches_plain_code_fence(self) -> None:
        """Test that plain code fence is detected."""
        match = _CODE_FENCE_PATTERN.match("```")
        assert match is not None
        assert match.group(1) == ""

    def test_matches_code_fence_with_language(self) -> None:
        """Test that code fence with language is detected."""
        match = _CODE_FENCE_PATTERN.match("```python")
        assert match is not None
        assert match.group(1) == "python"

    def test_matches_code_fence_with_javascript(self) -> None:
        """Test that code fence with javascript is detected."""
        match = _CODE_FENCE_PATTERN.match("```javascript")
        assert match is not None
        assert match.group(1) == "javascript"

    def test_no_match_with_text_after_language(self) -> None:
        """Test that code fence with text after language is not matched."""
        match = _CODE_FENCE_PATTERN.match("```python code here")
        assert match is None

    def test_no_match_for_inline_code(self) -> None:
        """Test that inline code is not matched."""
        match = _CODE_FENCE_PATTERN.match("`code`")
        assert match is None

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _CODE_FENCE_PATTERN.match("Regular text")
        assert match is None

    def test_no_match_with_leading_space(self) -> None:
        """Test that code fence with leading space is not matched."""
        match = _CODE_FENCE_PATTERN.match(" ```")
        assert match is None


class TestStrikethroughPattern:
    """Tests for strikethrough pattern detection."""

    def test_matches_strikethrough(self) -> None:
        """Test that strikethrough is detected."""
        match = _STRIKETHROUGH_PATTERN.search("~~deleted~~")
        assert match is not None
        assert match.group(1) == "deleted"

    def test_matches_strikethrough_in_text(self) -> None:
        """Test that strikethrough in text is detected."""
        match = _STRIKETHROUGH_PATTERN.search("This is ~~deleted~~ text")
        assert match is not None
        assert match.group(1) == "deleted"

    def test_matches_multiple_strikethroughs(self) -> None:
        """Test that multiple strikethroughs are detected."""
        matches = _STRIKETHROUGH_PATTERN.findall("~~first~~ and ~~second~~")
        assert matches == ["first", "second"]

    def test_matches_japanese_strikethrough(self) -> None:
        """Test that Japanese text in strikethrough is detected."""
        match = _STRIKETHROUGH_PATTERN.search("~~削除されたテキスト~~")
        assert match is not None
        assert match.group(1) == "削除されたテキスト"

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _STRIKETHROUGH_PATTERN.search("Regular text")
        assert match is None

    def test_no_match_for_single_tilde(self) -> None:
        """Test that single tilde is not matched."""
        match = _STRIKETHROUGH_PATTERN.search("~text~")
        assert match is None

    def test_no_match_for_empty_strikethrough(self) -> None:
        """Test that empty strikethrough is not matched."""
        match = _STRIKETHROUGH_PATTERN.search("~~~~")
        assert match is None


class TestTypeWithStrikethrough:
    """Tests for _type_with_strikethrough function."""

    @pytest.mark.asyncio
    async def test_empty_text_does_nothing(self) -> None:
        """Test that empty text results in no keyboard actions."""
        mock_page = AsyncMock()
        await _type_with_strikethrough(mock_page, "")
        mock_page.keyboard.type.assert_not_called()

    @pytest.mark.asyncio
    async def test_plain_text_types_directly(self) -> None:
        """Test that plain text without strikethrough is typed directly."""
        mock_page = AsyncMock()
        await _type_with_strikethrough(mock_page, "plain text")
        mock_page.keyboard.type.assert_called_once_with("plain text")

    @pytest.mark.asyncio
    async def test_strikethrough_with_trigger_space(self) -> None:
        """Test that strikethrough patterns trigger space for ProseMirror conversion."""
        mock_page = AsyncMock()
        await _type_with_strikethrough(mock_page, "~~deleted~~")

        # Verify: ~~deleted~~ typed, then space for trigger
        calls = mock_page.keyboard.type.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "~~deleted~~"
        assert calls[1][0][0] == " "

    @pytest.mark.asyncio
    async def test_strikethrough_with_text_before(self) -> None:
        """Test strikethrough with text before it."""
        mock_page = AsyncMock()
        await _type_with_strikethrough(mock_page, "text ~~deleted~~")

        calls = mock_page.keyboard.type.call_args_list
        # Should type: "text ", then "~~deleted~~", then " "
        assert len(calls) == 3
        assert calls[0][0][0] == "text "
        assert calls[1][0][0] == "~~deleted~~"
        assert calls[2][0][0] == " "

    @pytest.mark.asyncio
    async def test_strikethrough_with_text_after_removes_space(self) -> None:
        """Test strikethrough with text after removes extra space."""
        mock_page = AsyncMock()
        await _type_with_strikethrough(mock_page, "~~deleted~~more")

        # Should type ~~deleted~~, space to trigger, then backspace, then "more"
        calls = mock_page.keyboard.type.call_args_list
        assert calls[0][0][0] == "~~deleted~~"
        assert calls[1][0][0] == " "

        # Verify backspace was pressed to remove extra space
        mock_page.keyboard.press.assert_called_with("Backspace")

    @pytest.mark.asyncio
    async def test_strikethrough_with_text_after_starting_with_space(self) -> None:
        """Test strikethrough followed by space doesn't add backspace."""
        mock_page = AsyncMock()
        await _type_with_strikethrough(mock_page, "~~deleted~~ more")

        # The trigger space is already there in input, no backspace needed
        calls = mock_page.keyboard.type.call_args_list
        assert calls[0][0][0] == "~~deleted~~"
        assert calls[1][0][0] == " "
        assert calls[2][0][0] == " more"

        # No backspace should be called
        mock_page.keyboard.press.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_strikethroughs(self) -> None:
        """Test multiple strikethrough patterns in same text."""
        mock_page = AsyncMock()
        await _type_with_strikethrough(mock_page, "~~first~~ and ~~second~~")

        calls = mock_page.keyboard.type.call_args_list
        # Should be: "~~first~~", " ", " and ", "~~second~~", " "
        typed_texts = [call[0][0] for call in calls]
        assert "~~first~~" in typed_texts
        assert "~~second~~" in typed_texts

    @pytest.mark.asyncio
    async def test_japanese_strikethrough(self) -> None:
        """Test strikethrough with Japanese text."""
        mock_page = AsyncMock()
        await _type_with_strikethrough(mock_page, "これは~~削除~~です")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "これは" in typed_texts
        assert "~~削除~~" in typed_texts
