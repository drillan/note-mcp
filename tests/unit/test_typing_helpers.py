"""Unit tests for typing helpers module."""

from unittest.mock import AsyncMock

import pytest

from note_mcp.browser.typing_helpers import (
    _ALIGN_CENTER_PATTERN,
    _ALIGN_CENTER_PLACEHOLDER,
    _ALIGN_END_PLACEHOLDER,
    _ALIGN_LEFT_PATTERN,
    _ALIGN_LEFT_PLACEHOLDER,
    _ALIGN_RIGHT_PATTERN,
    _ALIGN_RIGHT_PLACEHOLDER,
    _BLOCKQUOTE_PATTERN,
    _BOLD_PATTERN,
    _CITATION_PATTERN,
    _CITATION_URL_PATTERN,
    _CODE_FENCE_PATTERN,
    _EMBED_NOTE_PATTERN,
    _EMBED_PLACEHOLDER_END,
    _EMBED_PLACEHOLDER_START,
    _EMBED_TWITTER_PATTERN,
    _EMBED_YOUTUBE_PATTERN,
    _HEADING_PATTERN,
    _ORDERED_LIST_PATTERN,
    _STRIKETHROUGH_PATTERN,
    _TOC_PATTERN,
    _TOC_PLACEHOLDER,
    _UNORDERED_LIST_PATTERN,
    _is_embed_url,
    _type_with_bold,
    _type_with_inline_formatting,
    _type_with_inline_pattern,
    _type_with_link,
    _type_with_strikethrough,
    type_markdown_content,
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


class TestTocPattern:
    """Tests for TOC pattern detection."""

    def test_matches_toc_marker(self) -> None:
        """Test that [TOC] marker is detected."""
        match = _TOC_PATTERN.match("[TOC]")
        assert match is not None

    def test_no_match_for_lowercase_toc(self) -> None:
        """Test that lowercase [toc] is not matched."""
        match = _TOC_PATTERN.match("[toc]")
        assert match is None

    def test_no_match_for_toc_with_text_before(self) -> None:
        """Test that text before [TOC] is not matched."""
        match = _TOC_PATTERN.match("Text [TOC]")
        assert match is None

    def test_no_match_for_toc_with_text_after(self) -> None:
        """Test that text after [TOC] is not matched."""
        match = _TOC_PATTERN.match("[TOC] text")
        assert match is None

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _TOC_PATTERN.match("Regular text")
        assert match is None

    def test_no_match_for_toc_in_sentence(self) -> None:
        """Test that [TOC] in a sentence is not matched."""
        match = _TOC_PATTERN.match("Add a [TOC] here")
        assert match is None


class TestTocPlaceholderConstant:
    """Tests for TOC placeholder constant."""

    def test_placeholder_is_text_marker(self) -> None:
        """Placeholder should be a unique text marker with section signs."""
        assert "§§" in _TOC_PLACEHOLDER

    def test_placeholder_contains_toc(self) -> None:
        """Placeholder should contain TOC identifier."""
        assert "TOC" in _TOC_PLACEHOLDER


class TestTypeMarkdownContentToc:
    """Tests for type_markdown_content with TOC handling."""

    @pytest.mark.asyncio
    async def test_toc_types_placeholder(self) -> None:
        """Test that [TOC] types placeholder instead of raw text."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "[TOC]")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert _TOC_PLACEHOLDER in typed_texts
        assert "[TOC]" not in typed_texts

    @pytest.mark.asyncio
    async def test_toc_with_content_before(self) -> None:
        """Test [TOC] with content before it."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "# Title\n\n[TOC]")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "# Title" in typed_texts
        assert _TOC_PLACEHOLDER in typed_texts

    @pytest.mark.asyncio
    async def test_toc_with_content_after(self) -> None:
        """Test [TOC] with content after it."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "[TOC]\n\n## Section 1")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert _TOC_PLACEHOLDER in typed_texts
        # With heading handling, "## Section 1" is typed as "## " (trigger) + "Section 1" (content)
        assert "## " in typed_texts
        assert "Section 1" in typed_texts

    @pytest.mark.asyncio
    async def test_toc_presses_enter_when_more_content(self) -> None:
        """Test that Enter is pressed after [TOC] when more content follows."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "[TOC]\nMore text")

        press_calls = mock_page.keyboard.press.call_args_list
        pressed_keys = [call[0][0] for call in press_calls]
        assert "Enter" in pressed_keys

    @pytest.mark.asyncio
    async def test_toc_in_middle_of_document(self) -> None:
        """Test [TOC] in the middle of a document."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """# Title

[TOC]

## Section 1
Content here

## Section 2
More content"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "# Title" in typed_texts
        assert _TOC_PLACEHOLDER in typed_texts
        assert "Content here" in typed_texts


class TestHeadingPattern:
    """Tests for heading pattern detection (## h2, ### h3, etc.)."""

    def test_matches_h2_heading(self) -> None:
        """Test that h2 heading (##) is detected."""
        match = _HEADING_PATTERN.match("## Section Title")
        assert match is not None
        assert match.group(1) == "##"
        assert match.group(2) == "Section Title"

    def test_matches_h3_heading(self) -> None:
        """Test that h3 heading (###) is detected."""
        match = _HEADING_PATTERN.match("### Subsection Title")
        assert match is not None
        assert match.group(1) == "###"
        assert match.group(2) == "Subsection Title"

    def test_matches_h4_heading(self) -> None:
        """Test that h4 heading (####) is detected."""
        match = _HEADING_PATTERN.match("#### Deep Section")
        assert match is not None
        assert match.group(1) == "####"
        assert match.group(2) == "Deep Section"

    def test_matches_h5_heading(self) -> None:
        """Test that h5 heading (#####) is detected."""
        match = _HEADING_PATTERN.match("##### Very Deep Section")
        assert match is not None
        assert match.group(1) == "#####"
        assert match.group(2) == "Very Deep Section"

    def test_matches_h6_heading(self) -> None:
        """Test that h6 heading (######) is detected."""
        match = _HEADING_PATTERN.match("###### Deepest Section")
        assert match is not None
        assert match.group(1) == "######"
        assert match.group(2) == "Deepest Section"

    def test_no_match_for_h1_heading(self) -> None:
        """Test that h1 heading (#) is NOT matched (note.com uses title for h1)."""
        match = _HEADING_PATTERN.match("# Title")
        assert match is None

    def test_requires_space_after_hashes(self) -> None:
        """Test that space after # marks is required."""
        match = _HEADING_PATTERN.match("##NoSpace")
        assert match is None

    def test_matches_japanese_heading(self) -> None:
        """Test that Japanese heading text is matched."""
        match = _HEADING_PATTERN.match("## 大見出し（h2）")
        assert match is not None
        assert match.group(1) == "##"
        assert match.group(2) == "大見出し（h2）"

    def test_matches_heading_with_special_characters(self) -> None:
        """Test heading with special characters."""
        match = _HEADING_PATTERN.match("### Section: Important!")
        assert match is not None
        assert match.group(2) == "Section: Important!"

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _HEADING_PATTERN.match("Regular text")
        assert match is None

    def test_no_match_for_code_with_hashes(self) -> None:
        """Test that code comments with # are not matched."""
        match = _HEADING_PATTERN.match("# This is a code comment")
        assert match is None


class TestTypeMarkdownContentHeadings:
    """Tests for type_markdown_content with heading handling."""

    @pytest.mark.asyncio
    async def test_h2_heading_triggers_prosemirror(self) -> None:
        """Test that h2 heading types prefix with space to trigger ProseMirror."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "## Section Title")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # Should type "## " to trigger ProseMirror, then "Section Title"
        assert "## " in typed_texts
        assert "Section Title" in typed_texts

    @pytest.mark.asyncio
    async def test_h3_heading_triggers_prosemirror(self) -> None:
        """Test that h3 heading types prefix with space to trigger ProseMirror."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "### Subsection")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "### " in typed_texts
        assert "Subsection" in typed_texts

    @pytest.mark.asyncio
    async def test_multiple_headings(self) -> None:
        """Test multiple headings in a document."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """## 大見出し（h2）

### 小見出し（h3）

## もう一つの大見出し"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "## " in typed_texts
        assert "大見出し（h2）" in typed_texts
        assert "### " in typed_texts
        assert "小見出し（h3）" in typed_texts
        assert "もう一つの大見出し" in typed_texts

    @pytest.mark.asyncio
    async def test_headings_with_toc(self) -> None:
        """Test headings with TOC marker."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """[TOC]

## Section 1

Some content

### Subsection 1.1

## Section 2"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # Verify TOC placeholder and headings are typed correctly
        assert _TOC_PLACEHOLDER in typed_texts
        assert "## " in typed_texts
        assert "Section 1" in typed_texts
        assert "### " in typed_texts
        assert "Subsection 1.1" in typed_texts
        assert "Section 2" in typed_texts

    @pytest.mark.asyncio
    async def test_heading_resets_list_state(self) -> None:
        """Test that heading resets list state."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """- List item 1
- List item 2

## New Section

More content"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # Verify both list items and heading are processed
        assert "- " in typed_texts or "List item 1" in typed_texts
        assert "## " in typed_texts
        assert "New Section" in typed_texts

    @pytest.mark.asyncio
    async def test_heading_presses_enter_for_next_line(self) -> None:
        """Test that Enter is pressed after heading when more content follows."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "## Heading\nContent")

        press_calls = mock_page.keyboard.press.call_args_list
        pressed_keys = [call[0][0] for call in press_calls]
        assert "Enter" in pressed_keys


class TestAlignCenterPattern:
    """Tests for center alignment pattern detection (->text<-)."""

    def test_matches_center_aligned_text(self) -> None:
        """Test that center alignment pattern is detected."""
        match = _ALIGN_CENTER_PATTERN.match("->centered text<-")
        assert match is not None
        assert match.group(1) == "centered text"

    def test_matches_center_with_japanese(self) -> None:
        """Test that center alignment with Japanese is detected."""
        match = _ALIGN_CENTER_PATTERN.match("->中央寄せテキスト<-")
        assert match is not None
        assert match.group(1) == "中央寄せテキスト"

    def test_requires_both_markers(self) -> None:
        """Test that both opening and closing markers are required."""
        # Only opening marker
        match = _ALIGN_CENTER_PATTERN.match("->text")
        assert match is None

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _ALIGN_CENTER_PATTERN.match("Regular text")
        assert match is None


class TestAlignRightPattern:
    """Tests for right alignment pattern detection (->text)."""

    def test_matches_right_aligned_text(self) -> None:
        """Test that right alignment pattern is detected."""
        match = _ALIGN_RIGHT_PATTERN.match("->right aligned text")
        assert match is not None
        assert match.group(1) == "right aligned text"

    def test_matches_right_with_japanese(self) -> None:
        """Test that right alignment with Japanese is detected."""
        match = _ALIGN_RIGHT_PATTERN.match("->右寄せテキスト")
        assert match is not None
        assert match.group(1) == "右寄せテキスト"

    def test_also_matches_center_pattern(self) -> None:
        """Test that center pattern (->text<-) also matches right pattern.

        Note: Center pattern is checked first in the code to handle this overlap.
        """
        match = _ALIGN_RIGHT_PATTERN.match("->centered<-")
        assert match is not None
        # Full match includes <-
        assert match.group(1) == "centered<-"

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _ALIGN_RIGHT_PATTERN.match("Regular text")
        assert match is None


class TestAlignLeftPattern:
    """Tests for left alignment pattern detection (<-text)."""

    def test_matches_left_aligned_text(self) -> None:
        """Test that left alignment pattern is detected."""
        match = _ALIGN_LEFT_PATTERN.match("<-left aligned text")
        assert match is not None
        assert match.group(1) == "left aligned text"

    def test_matches_left_with_japanese(self) -> None:
        """Test that left alignment with Japanese is detected."""
        match = _ALIGN_LEFT_PATTERN.match("<-左寄せテキスト")
        assert match is not None
        assert match.group(1) == "左寄せテキスト"

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        match = _ALIGN_LEFT_PATTERN.match("Regular text")
        assert match is None

    def test_no_match_for_arrow_in_middle(self) -> None:
        """Test that <- in middle of text is not matched."""
        match = _ALIGN_LEFT_PATTERN.match("text <- more")
        assert match is None


class TestAlignmentPlaceholderConstants:
    """Tests for alignment placeholder constants used in typing helpers."""

    def test_center_placeholder_contains_marker(self) -> None:
        """Test that center placeholder contains section sign markers."""
        assert "§§" in _ALIGN_CENTER_PLACEHOLDER
        assert "CENTER" in _ALIGN_CENTER_PLACEHOLDER

    def test_right_placeholder_contains_marker(self) -> None:
        """Test that right placeholder contains section sign markers."""
        assert "§§" in _ALIGN_RIGHT_PLACEHOLDER
        assert "RIGHT" in _ALIGN_RIGHT_PLACEHOLDER

    def test_left_placeholder_contains_marker(self) -> None:
        """Test that left placeholder contains section sign markers."""
        assert "§§" in _ALIGN_LEFT_PLACEHOLDER
        assert "LEFT" in _ALIGN_LEFT_PLACEHOLDER

    def test_end_placeholder_contains_marker(self) -> None:
        """Test that end placeholder contains section sign markers."""
        assert "§§" in _ALIGN_END_PLACEHOLDER
        assert "/ALIGN" in _ALIGN_END_PLACEHOLDER

    def test_all_placeholders_unique(self) -> None:
        """Test that all placeholders are unique."""
        placeholders = [
            _ALIGN_CENTER_PLACEHOLDER,
            _ALIGN_RIGHT_PLACEHOLDER,
            _ALIGN_LEFT_PLACEHOLDER,
            _ALIGN_END_PLACEHOLDER,
        ]
        assert len(placeholders) == len(set(placeholders))


class TestTypeMarkdownContentAlignment:
    """Tests for type_markdown_content with text alignment handling."""

    @pytest.mark.asyncio
    async def test_center_alignment_types_placeholder(self) -> None:
        """Test that center alignment notation types placeholder."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "->centered text<-")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # Should contain placeholder with content
        expected = f"{_ALIGN_CENTER_PLACEHOLDER}centered text{_ALIGN_END_PLACEHOLDER}"
        assert expected in typed_texts

    @pytest.mark.asyncio
    async def test_right_alignment_types_placeholder(self) -> None:
        """Test that right alignment notation types placeholder."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "->right aligned")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        expected = f"{_ALIGN_RIGHT_PLACEHOLDER}right aligned{_ALIGN_END_PLACEHOLDER}"
        assert expected in typed_texts

    @pytest.mark.asyncio
    async def test_left_alignment_types_placeholder(self) -> None:
        """Test that left alignment notation types placeholder."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "<-left aligned")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        expected = f"{_ALIGN_LEFT_PLACEHOLDER}left aligned{_ALIGN_END_PLACEHOLDER}"
        assert expected in typed_texts

    @pytest.mark.asyncio
    async def test_alignment_with_other_content(self) -> None:
        """Test alignment mixed with other content."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """Normal text

->centered text<-

More normal text"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "Normal text" in typed_texts
        expected_center = f"{_ALIGN_CENTER_PLACEHOLDER}centered text{_ALIGN_END_PLACEHOLDER}"
        assert expected_center in typed_texts
        assert "More normal text" in typed_texts

    @pytest.mark.asyncio
    async def test_multiple_alignments(self) -> None:
        """Test multiple alignment notations in same document."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """->center text<-
->right text
<-left text"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]

        expected_center = f"{_ALIGN_CENTER_PLACEHOLDER}center text{_ALIGN_END_PLACEHOLDER}"
        expected_right = f"{_ALIGN_RIGHT_PLACEHOLDER}right text{_ALIGN_END_PLACEHOLDER}"
        expected_left = f"{_ALIGN_LEFT_PLACEHOLDER}left text{_ALIGN_END_PLACEHOLDER}"

        assert expected_center in typed_texts
        assert expected_right in typed_texts
        assert expected_left in typed_texts

    @pytest.mark.asyncio
    async def test_alignment_presses_enter_for_next_line(self) -> None:
        """Test that Enter is pressed after alignment when more content follows."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        await type_markdown_content(mock_page, "->centered<-\nMore text")

        press_calls = mock_page.keyboard.press.call_args_list
        pressed_keys = [call[0][0] for call in press_calls]
        assert "Enter" in pressed_keys

    @pytest.mark.asyncio
    async def test_alignment_resets_list_state(self) -> None:
        """Test that alignment resets list state."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """- List item 1
- List item 2

->centered<-

More content"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        expected_center = f"{_ALIGN_CENTER_PLACEHOLDER}centered{_ALIGN_END_PLACEHOLDER}"
        assert expected_center in typed_texts

    @pytest.mark.asyncio
    async def test_alignment_with_headings(self) -> None:
        """Test alignment with headings."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """## Section Title

->centered text<-

More content"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "## " in typed_texts
        assert "Section Title" in typed_texts
        expected_center = f"{_ALIGN_CENTER_PLACEHOLDER}centered text{_ALIGN_END_PLACEHOLDER}"
        assert expected_center in typed_texts


class TestEmbedYouTubePattern:
    """Tests for YouTube embed URL pattern detection."""

    def test_matches_youtube_watch_url(self) -> None:
        """Test that YouTube watch URLs are detected."""
        match = _EMBED_YOUTUBE_PATTERN.match("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert match is not None

    def test_matches_youtube_watch_url_without_www(self) -> None:
        """Test that YouTube watch URLs without www are detected."""
        match = _EMBED_YOUTUBE_PATTERN.match("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert match is not None

    def test_matches_youtu_be_short_url(self) -> None:
        """Test that youtu.be short URLs are detected."""
        match = _EMBED_YOUTUBE_PATTERN.match("https://youtu.be/dQw4w9WgXcQ")
        assert match is not None

    def test_matches_http_youtube_url(self) -> None:
        """Test that HTTP YouTube URLs are detected."""
        match = _EMBED_YOUTUBE_PATTERN.match("http://www.youtube.com/watch?v=abc123XYZ")
        assert match is not None

    def test_matches_video_id_with_hyphens(self) -> None:
        """Test that video IDs with hyphens are matched."""
        match = _EMBED_YOUTUBE_PATTERN.match("https://youtu.be/abc-123_XYZ")
        assert match is not None

    def test_no_match_for_channel_url(self) -> None:
        """Test that channel URLs are not matched."""
        match = _EMBED_YOUTUBE_PATTERN.match("https://www.youtube.com/channel/UC123")
        assert match is None

    def test_no_match_for_playlist_url(self) -> None:
        """Test that playlist URLs are not matched."""
        match = _EMBED_YOUTUBE_PATTERN.match("https://www.youtube.com/playlist?list=PL123")
        assert match is None

    def test_no_match_for_homepage(self) -> None:
        """Test that YouTube homepage is not matched."""
        match = _EMBED_YOUTUBE_PATTERN.match("https://www.youtube.com/")
        assert match is None

    def test_no_match_without_protocol(self) -> None:
        """Test that URLs without protocol are not matched."""
        match = _EMBED_YOUTUBE_PATTERN.match("youtube.com/watch?v=abc123")
        assert match is None


class TestEmbedTwitterPattern:
    """Tests for Twitter/X embed URL pattern detection."""

    def test_matches_twitter_status_url(self) -> None:
        """Test that Twitter status URLs are detected."""
        match = _EMBED_TWITTER_PATTERN.match("https://twitter.com/user/status/1234567890")
        assert match is not None

    def test_matches_twitter_with_www(self) -> None:
        """Test that Twitter URLs with www are detected."""
        match = _EMBED_TWITTER_PATTERN.match("https://www.twitter.com/user/status/1234567890")
        assert match is not None

    def test_matches_x_com_status_url(self) -> None:
        """Test that X.com status URLs are detected."""
        match = _EMBED_TWITTER_PATTERN.match("https://x.com/user/status/1234567890")
        assert match is not None

    def test_matches_x_com_with_www(self) -> None:
        """Test that X.com URLs with www are detected."""
        match = _EMBED_TWITTER_PATTERN.match("https://www.x.com/user/status/1234567890")
        assert match is not None

    def test_matches_http_twitter_url(self) -> None:
        """Test that HTTP Twitter URLs are detected."""
        match = _EMBED_TWITTER_PATTERN.match("http://twitter.com/user/status/9876543210")
        assert match is not None

    def test_no_match_for_profile_url(self) -> None:
        """Test that profile URLs are not matched."""
        match = _EMBED_TWITTER_PATTERN.match("https://twitter.com/user")
        assert match is None

    def test_no_match_for_likes_url(self) -> None:
        """Test that likes URLs are not matched."""
        match = _EMBED_TWITTER_PATTERN.match("https://twitter.com/user/likes")
        assert match is None

    def test_no_match_for_homepage(self) -> None:
        """Test that Twitter homepage is not matched."""
        match = _EMBED_TWITTER_PATTERN.match("https://twitter.com/")
        assert match is None

    def test_no_match_without_protocol(self) -> None:
        """Test that URLs without protocol are not matched."""
        match = _EMBED_TWITTER_PATTERN.match("twitter.com/user/status/123")
        assert match is None


class TestEmbedNotePattern:
    """Tests for note.com embed URL pattern detection."""

    def test_matches_note_article_url(self) -> None:
        """Test that note.com article URLs are detected."""
        match = _EMBED_NOTE_PATTERN.match("https://note.com/username/n/n1234567890ab")
        assert match is not None

    def test_matches_http_note_url(self) -> None:
        """Test that HTTP note.com URLs are detected."""
        match = _EMBED_NOTE_PATTERN.match("http://note.com/user123/n/nabc123def456")
        assert match is not None

    def test_matches_note_with_underscore_username(self) -> None:
        """Test that note.com URLs with underscore in username are detected."""
        match = _EMBED_NOTE_PATTERN.match("https://note.com/user_name/n/n12345")
        assert match is not None

    def test_no_match_for_profile_url(self) -> None:
        """Test that profile URLs are not matched."""
        match = _EMBED_NOTE_PATTERN.match("https://note.com/username")
        assert match is None

    def test_no_match_for_magazine_url(self) -> None:
        """Test that magazine URLs are not matched."""
        match = _EMBED_NOTE_PATTERN.match("https://note.com/username/m/m123")
        assert match is None

    def test_no_match_for_homepage(self) -> None:
        """Test that note.com homepage is not matched."""
        match = _EMBED_NOTE_PATTERN.match("https://note.com/")
        assert match is None

    def test_no_match_for_old_domain(self) -> None:
        """Test that old note.mu domain is not matched."""
        match = _EMBED_NOTE_PATTERN.match("https://note.mu/user/n/n123")
        assert match is None

    def test_no_match_without_protocol(self) -> None:
        """Test that URLs without protocol are not matched."""
        match = _EMBED_NOTE_PATTERN.match("note.com/user/n/n123")
        assert match is None


class TestEmbedPlaceholderConstants:
    """Tests for embed placeholder constant definitions."""

    def test_placeholder_start_marker(self) -> None:
        """Placeholder start marker should be §§EMBED:"""
        assert _EMBED_PLACEHOLDER_START == "§§EMBED:"

    def test_placeholder_end_marker(self) -> None:
        """Placeholder end marker should be §§"""
        assert _EMBED_PLACEHOLDER_END == "§§"

    def test_placeholder_markers_are_distinct(self) -> None:
        """Start and end markers should be different."""
        assert _EMBED_PLACEHOLDER_START != _EMBED_PLACEHOLDER_END

    def test_placeholder_format_example(self) -> None:
        """Placeholder format should be §§EMBED:url§§"""
        url = "https://www.youtube.com/watch?v=abc123"
        placeholder = f"{_EMBED_PLACEHOLDER_START}{url}{_EMBED_PLACEHOLDER_END}"
        assert placeholder == "§§EMBED:https://www.youtube.com/watch?v=abc123§§"


class TestIsEmbedUrl:
    """Tests for _is_embed_url function."""

    def test_returns_true_for_youtube_url(self) -> None:
        """Should return True for YouTube URLs."""
        assert _is_embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_returns_true_for_youtu_be_url(self) -> None:
        """Should return True for youtu.be URLs."""
        assert _is_embed_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_returns_true_for_twitter_url(self) -> None:
        """Should return True for Twitter URLs."""
        assert _is_embed_url("https://twitter.com/user/status/1234567890") is True

    def test_returns_true_for_x_com_url(self) -> None:
        """Should return True for X.com URLs."""
        assert _is_embed_url("https://x.com/user/status/1234567890") is True

    def test_returns_true_for_note_url(self) -> None:
        """Should return True for note.com article URLs."""
        assert _is_embed_url("https://note.com/username/n/n1234567890ab") is True

    def test_returns_false_for_generic_url(self) -> None:
        """Should return False for generic URLs."""
        assert _is_embed_url("https://example.com/page") is False

    def test_returns_false_for_github_url(self) -> None:
        """Should return False for GitHub URLs."""
        assert _is_embed_url("https://github.com/user/repo") is False

    def test_returns_false_for_vimeo_url(self) -> None:
        """Should return False for Vimeo URLs."""
        assert _is_embed_url("https://vimeo.com/123456") is False

    def test_returns_false_for_empty_string(self) -> None:
        """Should return False for empty string."""
        assert _is_embed_url("") is False

    def test_returns_false_for_plain_text(self) -> None:
        """Should return False for plain text."""
        assert _is_embed_url("not a url") is False

    def test_returns_false_for_youtube_channel(self) -> None:
        """Should return False for YouTube channel URLs."""
        assert _is_embed_url("https://www.youtube.com/channel/UC123") is False

    def test_returns_false_for_twitter_profile(self) -> None:
        """Should return False for Twitter profile URLs."""
        assert _is_embed_url("https://twitter.com/user") is False

    def test_returns_false_for_note_profile(self) -> None:
        """Should return False for note.com profile URLs."""
        assert _is_embed_url("https://note.com/username") is False


class TestTypeMarkdownContentEmbeds:
    """Tests for type_markdown_content with embed URL handling."""

    @pytest.mark.asyncio
    async def test_embed_url_types_placeholder(self) -> None:
        """Test that embed URLs are converted to placeholders."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        await type_markdown_content(mock_page, url)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        expected = f"{_EMBED_PLACEHOLDER_START}{url}{_EMBED_PLACEHOLDER_END}"
        assert expected in typed_texts

    @pytest.mark.asyncio
    async def test_youtube_url_in_text_types_placeholder(self) -> None:
        """Test YouTube URL embedded in text is converted to placeholder."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = "Check this video:\nhttps://www.youtube.com/watch?v=abc123"
        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        expected = f"{_EMBED_PLACEHOLDER_START}https://www.youtube.com/watch?v=abc123{_EMBED_PLACEHOLDER_END}"
        assert expected in typed_texts
        assert "Check this video:" in typed_texts

    @pytest.mark.asyncio
    async def test_twitter_url_types_placeholder(self) -> None:
        """Test Twitter URL is converted to placeholder."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        url = "https://twitter.com/user/status/1234567890"
        await type_markdown_content(mock_page, url)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        expected = f"{_EMBED_PLACEHOLDER_START}{url}{_EMBED_PLACEHOLDER_END}"
        assert expected in typed_texts

    @pytest.mark.asyncio
    async def test_x_com_url_types_placeholder(self) -> None:
        """Test X.com URL is converted to placeholder."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        url = "https://x.com/user/status/9876543210"
        await type_markdown_content(mock_page, url)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        expected = f"{_EMBED_PLACEHOLDER_START}{url}{_EMBED_PLACEHOLDER_END}"
        assert expected in typed_texts

    @pytest.mark.asyncio
    async def test_note_url_types_placeholder(self) -> None:
        """Test note.com article URL is converted to placeholder."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        url = "https://note.com/username/n/n1234567890ab"
        await type_markdown_content(mock_page, url)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        expected = f"{_EMBED_PLACEHOLDER_START}{url}{_EMBED_PLACEHOLDER_END}"
        assert expected in typed_texts

    @pytest.mark.asyncio
    async def test_non_embed_url_types_directly(self) -> None:
        """Test non-embed URLs are typed directly without placeholder."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        url = "https://example.com/page"
        await type_markdown_content(mock_page, url)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # Should NOT contain embed placeholder
        for text in typed_texts:
            assert _EMBED_PLACEHOLDER_START not in text
        # Should type the URL directly
        assert url in typed_texts

    @pytest.mark.asyncio
    async def test_multiple_embed_urls(self) -> None:
        """Test multiple embed URLs in same document."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """Check out these videos:

https://www.youtube.com/watch?v=abc123

And this tweet:

https://twitter.com/user/status/456"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]

        yt_placeholder = f"{_EMBED_PLACEHOLDER_START}https://www.youtube.com/watch?v=abc123{_EMBED_PLACEHOLDER_END}"
        tw_placeholder = f"{_EMBED_PLACEHOLDER_START}https://twitter.com/user/status/456{_EMBED_PLACEHOLDER_END}"

        assert yt_placeholder in typed_texts
        assert tw_placeholder in typed_texts

    @pytest.mark.asyncio
    async def test_embed_url_with_headings(self) -> None:
        """Test embed URL works with headings."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """## Video Section

https://www.youtube.com/watch?v=abc123

## Text Section"""

        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]

        assert "## " in typed_texts
        assert "Video Section" in typed_texts
        expected = f"{_EMBED_PLACEHOLDER_START}https://www.youtube.com/watch?v=abc123{_EMBED_PLACEHOLDER_END}"
        assert expected in typed_texts

    @pytest.mark.asyncio
    async def test_embed_url_presses_enter_for_next_line(self) -> None:
        """Test that Enter is pressed after embed URL when more content follows."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = "https://www.youtube.com/watch?v=abc123\nMore text"
        await type_markdown_content(mock_page, content)

        press_calls = mock_page.keyboard.press.call_args_list
        pressed_keys = [call[0][0] for call in press_calls]
        assert "Enter" in pressed_keys


class TestTypeWithInlinePattern:
    """Tests for _type_with_inline_pattern generic function."""

    @pytest.mark.asyncio
    async def test_no_match_types_text_directly(self) -> None:
        """Test that text without pattern is typed directly."""
        mock_page = AsyncMock()
        remaining = await _type_with_inline_pattern(
            mock_page,
            "plain text",
            _BOLD_PATTERN,
            lambda m: f"**{m.group(1)}**",
        )
        mock_page.keyboard.type.assert_called_once_with("plain text")
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_pattern_match_types_with_trigger(self) -> None:
        """Test that pattern match types formatted text with space trigger."""
        mock_page = AsyncMock()
        remaining = await _type_with_inline_pattern(
            mock_page,
            "**bold**",
            _BOLD_PATTERN,
            lambda m: f"**{m.group(1)}**",
        )

        calls = mock_page.keyboard.type.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "**bold**"
        assert calls[1][0][0] == " "
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_pattern_with_text_before(self) -> None:
        """Test pattern with text before it."""
        mock_page = AsyncMock()
        remaining = await _type_with_inline_pattern(
            mock_page,
            "text **bold**",
            _BOLD_PATTERN,
            lambda m: f"**{m.group(1)}**",
        )

        calls = mock_page.keyboard.type.call_args_list
        assert calls[0][0][0] == "text "
        assert calls[1][0][0] == "**bold**"
        assert calls[2][0][0] == " "
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_pattern_returns_remaining_text(self) -> None:
        """Test that remaining text is returned after pattern."""
        mock_page = AsyncMock()
        remaining = await _type_with_inline_pattern(
            mock_page,
            "**bold** more text",
            _BOLD_PATTERN,
            lambda m: f"**{m.group(1)}**",
        )

        assert remaining == " more text"

    @pytest.mark.asyncio
    async def test_pattern_removes_extra_space_when_not_followed_by_space(self) -> None:
        """Test that backspace is pressed when remaining text doesn't start with space."""
        mock_page = AsyncMock()
        remaining = await _type_with_inline_pattern(
            mock_page,
            "**bold**more",
            _BOLD_PATTERN,
            lambda m: f"**{m.group(1)}**",
        )

        mock_page.keyboard.press.assert_called_with("Backspace")
        assert remaining == "more"


class TestTypeWithLink:
    """Tests for _type_with_link function.

    Note: Links are inserted via UI automation (insert_link_at_cursor),
    not by typing markdown syntax, because ProseMirror has no InputRule
    for [text](url) conversion.
    """

    @pytest.mark.asyncio
    async def test_no_link_types_directly(self) -> None:
        """Test that text without links is typed directly."""
        mock_page = AsyncMock()
        remaining = await _type_with_link(mock_page, "plain text")
        mock_page.keyboard.type.assert_called_once_with("plain text")
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_link_pattern_uses_ui_automation(self) -> None:
        """Test that link pattern uses insert_link_at_cursor via UI."""
        from unittest.mock import patch

        from note_mcp.browser.insert_link import LinkResult

        mock_page = AsyncMock()
        with patch(
            "note_mcp.browser.insert_link.insert_link_at_cursor",
            new_callable=AsyncMock,
        ) as mock_insert:
            mock_insert.return_value = (LinkResult.SUCCESS, "S1:OK")
            remaining = await _type_with_link(mock_page, "[example](https://example.com)")

            # UI automation called with correct args
            mock_insert.assert_called_once_with(mock_page, "example", "https://example.com")
            assert remaining == ""

    @pytest.mark.asyncio
    async def test_link_with_text_before(self) -> None:
        """Test link with text before it types text first, then inserts link."""
        from unittest.mock import patch

        from note_mcp.browser.insert_link import LinkResult

        mock_page = AsyncMock()
        with patch(
            "note_mcp.browser.insert_link.insert_link_at_cursor",
            new_callable=AsyncMock,
        ) as mock_insert:
            mock_insert.return_value = (LinkResult.SUCCESS, "S1:OK")
            await _type_with_link(mock_page, "Visit [site](https://example.com)")

            # Text before link is typed
            mock_page.keyboard.type.assert_called_once_with("Visit ")
            # Then link is inserted via UI
            mock_insert.assert_called_once_with(mock_page, "site", "https://example.com")

    @pytest.mark.asyncio
    async def test_link_with_text_after(self) -> None:
        """Test link with text after returns remaining."""
        from unittest.mock import patch

        from note_mcp.browser.insert_link import LinkResult

        mock_page = AsyncMock()
        with patch(
            "note_mcp.browser.insert_link.insert_link_at_cursor",
            new_callable=AsyncMock,
        ) as mock_insert:
            mock_insert.return_value = (LinkResult.SUCCESS, "S1:OK")
            remaining = await _type_with_link(mock_page, "[link](url) and more")

            assert remaining == " and more"

    @pytest.mark.asyncio
    async def test_link_insertion_failure_falls_back_to_plain_text(self) -> None:
        """Test that failed link insertion falls back to typing plain text."""
        from unittest.mock import patch

        from note_mcp.browser.insert_link import LinkResult

        mock_page = AsyncMock()
        with patch(
            "note_mcp.browser.insert_link.insert_link_at_cursor",
            new_callable=AsyncMock,
        ) as mock_insert:
            mock_insert.return_value = (LinkResult.TIMEOUT, "S1:FAIL")
            remaining = await _type_with_link(mock_page, "[link](url)")

            # Falls back to typing plain markdown
            calls = mock_page.keyboard.type.call_args_list
            assert calls[0][0][0] == "[link](url)"
            assert remaining == ""


class TestTypeWithBold:
    """Tests for _type_with_bold function."""

    @pytest.mark.asyncio
    async def test_no_bold_types_directly(self) -> None:
        """Test that text without bold is typed directly."""
        mock_page = AsyncMock()
        remaining = await _type_with_bold(mock_page, "plain text")
        mock_page.keyboard.type.assert_called_once_with("plain text")
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_bold_pattern_types_with_trigger(self) -> None:
        """Test that bold pattern is typed with space trigger."""
        mock_page = AsyncMock()
        remaining = await _type_with_bold(mock_page, "**important**")

        calls = mock_page.keyboard.type.call_args_list
        assert calls[0][0][0] == "**important**"
        assert calls[1][0][0] == " "
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_bold_with_text_before(self) -> None:
        """Test bold with text before it."""
        mock_page = AsyncMock()
        await _type_with_bold(mock_page, "This is **important**")

        calls = mock_page.keyboard.type.call_args_list
        assert calls[0][0][0] == "This is "
        assert calls[1][0][0] == "**important**"

    @pytest.mark.asyncio
    async def test_bold_with_text_after(self) -> None:
        """Test bold with text after returns remaining."""
        mock_page = AsyncMock()
        remaining = await _type_with_bold(mock_page, "**bold** text")

        assert remaining == " text"


class TestTypeWithInlineFormatting:
    """Tests for _type_with_inline_formatting function."""

    @pytest.mark.asyncio
    async def test_empty_text_does_nothing(self) -> None:
        """Test that empty text results in no keyboard actions."""
        mock_page = AsyncMock()
        await _type_with_inline_formatting(mock_page, "")
        mock_page.keyboard.type.assert_not_called()

    @pytest.mark.asyncio
    async def test_plain_text_types_directly(self) -> None:
        """Test that plain text is typed directly."""
        mock_page = AsyncMock()
        await _type_with_inline_formatting(mock_page, "plain text")
        mock_page.keyboard.type.assert_called_with("plain text")

    @pytest.mark.asyncio
    async def test_link_is_processed(self) -> None:
        """Test that link patterns are processed via UI automation."""
        from unittest.mock import patch

        from note_mcp.browser.insert_link import LinkResult

        mock_page = AsyncMock()
        with patch(
            "note_mcp.browser.insert_link.insert_link_at_cursor",
            new_callable=AsyncMock,
        ) as mock_insert:
            mock_insert.return_value = (LinkResult.SUCCESS, "S1:OK")
            await _type_with_inline_formatting(mock_page, "[link](url)")

            # Link is inserted via UI, not typed as markdown
            mock_insert.assert_called_once_with(mock_page, "link", "url")

    @pytest.mark.asyncio
    async def test_bold_is_processed(self) -> None:
        """Test that bold patterns are processed."""
        mock_page = AsyncMock()
        await _type_with_inline_formatting(mock_page, "**bold**")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "**bold**" in typed_texts

    @pytest.mark.asyncio
    async def test_strikethrough_is_processed(self) -> None:
        """Test that strikethrough patterns are processed."""
        mock_page = AsyncMock()
        await _type_with_inline_formatting(mock_page, "~~deleted~~")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "~~deleted~~" in typed_texts

    @pytest.mark.asyncio
    async def test_multiple_patterns_are_processed(self) -> None:
        """Test that multiple patterns in text are all processed."""
        mock_page = AsyncMock()
        await _type_with_inline_formatting(mock_page, "**bold** and ~~deleted~~")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "**bold**" in typed_texts
        assert "~~deleted~~" in typed_texts

    @pytest.mark.asyncio
    async def test_link_processed_before_bold(self) -> None:
        """Test that links are processed before bold (priority order)."""
        from unittest.mock import patch

        from note_mcp.browser.insert_link import LinkResult

        mock_page = AsyncMock()
        with patch(
            "note_mcp.browser.insert_link.insert_link_at_cursor",
            new_callable=AsyncMock,
        ) as mock_insert:
            mock_insert.return_value = (LinkResult.SUCCESS, "S1:OK")
            await _type_with_inline_formatting(mock_page, "[**link**](url)")

            # The link pattern should be matched first, containing **link**
            # Link text includes the ** markers (not processed as bold inside link)
            mock_insert.assert_called_once_with(mock_page, "**link**", "url")

    @pytest.mark.asyncio
    async def test_japanese_text_with_formatting(self) -> None:
        """Test inline formatting with Japanese text."""
        mock_page = AsyncMock()
        await _type_with_inline_formatting(mock_page, "これは**太字**です")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        assert "これは" in typed_texts
        assert "**太字**" in typed_texts


# =============================================================================
# Issue #110 Tests: ブラウザパスでのMarkdown変換に3つの問題
# =============================================================================


class TestImagePattern:
    """Tests for image pattern detection (![alt](url)) - Issue #110 Problem 1."""

    def test_matches_image_syntax(self) -> None:
        """Test that image syntax is detected."""
        from note_mcp.browser.typing_helpers import _IMAGE_PATTERN

        match = _IMAGE_PATTERN.search("![alt text](https://example.com/image.png)")
        assert match is not None
        assert match.group(1) == "alt text"
        assert match.group(2) == "https://example.com/image.png"

    def test_matches_image_with_local_path(self) -> None:
        """Test that image with local path is detected."""
        from note_mcp.browser.typing_helpers import _IMAGE_PATTERN

        match = _IMAGE_PATTERN.search("![サンプル画像](./images/sample_image.png)")
        assert match is not None
        assert match.group(1) == "サンプル画像"
        assert match.group(2) == "./images/sample_image.png"

    def test_matches_image_in_text(self) -> None:
        """Test that image in middle of text is detected."""
        from note_mcp.browser.typing_helpers import _IMAGE_PATTERN

        match = _IMAGE_PATTERN.search("前テキスト![alt](url)後テキスト")
        assert match is not None
        assert match.group(1) == "alt"
        assert match.group(2) == "url"

    def test_distinguishes_from_link(self) -> None:
        """Test that image pattern is distinct from link pattern."""
        from note_mcp.browser.typing_helpers import _IMAGE_PATTERN

        # Image pattern should NOT match regular link (no !)
        match = _IMAGE_PATTERN.search("[not image](url)")
        assert match is None

    def test_matches_image_with_empty_alt(self) -> None:
        """Test that image with empty alt text is detected."""
        from note_mcp.browser.typing_helpers import _IMAGE_PATTERN

        match = _IMAGE_PATTERN.search("![](https://example.com/image.png)")
        assert match is not None
        assert match.group(1) == ""

    def test_no_match_for_plain_text(self) -> None:
        """Test that plain text is not matched."""
        from note_mcp.browser.typing_helpers import _IMAGE_PATTERN

        match = _IMAGE_PATTERN.search("Regular text without images")
        assert match is None


class TestTypeWithImage:
    """Tests for _type_with_image function - Issue #110 Problem 1."""

    @pytest.mark.asyncio
    async def test_no_image_types_directly(self) -> None:
        """Test that text without images is typed directly."""
        from note_mcp.browser.typing_helpers import _type_with_image

        mock_page = AsyncMock()
        remaining = await _type_with_image(mock_page, "plain text")
        mock_page.keyboard.type.assert_called_once_with("plain text")
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_image_types_placeholder(self) -> None:
        """Test that image is converted to placeholder."""
        from note_mcp.browser.typing_helpers import (
            _IMAGE_PLACEHOLDER_END,
            _IMAGE_PLACEHOLDER_START,
            _type_with_image,
        )

        mock_page = AsyncMock()
        remaining = await _type_with_image(mock_page, "![サンプル画像](./images/sample_image.png)")

        calls = mock_page.keyboard.type.call_args_list
        typed_text = calls[0][0][0]
        # Should contain placeholder markers
        assert _IMAGE_PLACEHOLDER_START in typed_text
        assert _IMAGE_PLACEHOLDER_END in typed_text
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_image_with_text_before(self) -> None:
        """Test image with text before types text first."""
        from note_mcp.browser.typing_helpers import (
            _IMAGE_PLACEHOLDER_START,
            _type_with_image,
        )

        mock_page = AsyncMock()
        remaining = await _type_with_image(mock_page, "Text before ![alt](url) after")

        calls = mock_page.keyboard.type.call_args_list
        # First call should be text before image
        assert calls[0][0][0] == "Text before "
        # Second call should contain image placeholder
        assert _IMAGE_PLACEHOLDER_START in calls[1][0][0]
        # Remaining should be " after"
        assert remaining == " after"

    @pytest.mark.asyncio
    async def test_image_preserves_alt_and_url(self) -> None:
        """Test that image placeholder preserves alt text and URL."""
        from note_mcp.browser.typing_helpers import _type_with_image

        mock_page = AsyncMock()
        await _type_with_image(mock_page, "![代替テキスト](https://example.com/img.png)")

        calls = mock_page.keyboard.type.call_args_list
        typed_text = calls[0][0][0]
        # Placeholder should contain alt and URL info
        assert "代替テキスト" in typed_text
        assert "https://example.com/img.png" in typed_text


class TestTypeWithInlineFormattingImage:
    """Tests for _type_with_inline_formatting with image handling - Issue #110."""

    @pytest.mark.asyncio
    async def test_image_processed_before_link(self) -> None:
        """Test that images are processed before links (priority order)."""
        from note_mcp.browser.typing_helpers import (
            _IMAGE_PLACEHOLDER_START,
            _type_with_inline_formatting,
        )

        mock_page = AsyncMock()
        await _type_with_inline_formatting(mock_page, "![alt](url)")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # Should be processed as image, not link
        found_image_placeholder = any(_IMAGE_PLACEHOLDER_START in text for text in typed_texts)
        assert found_image_placeholder, f"Image placeholder not found in {typed_texts}"

    @pytest.mark.asyncio
    async def test_exclamation_not_typed_separately(self) -> None:
        """Test that ! is not typed separately from image syntax."""
        from note_mcp.browser.typing_helpers import _type_with_inline_formatting

        mock_page = AsyncMock()
        await _type_with_inline_formatting(mock_page, "![サンプル](./images/sample.png)")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # The "!" should NOT appear alone
        assert "!" not in typed_texts, f"! typed separately: {typed_texts}"


class TestCodeBlockEmptyLines:
    """Tests for code block empty line handling - Issue #110 Problem 2."""

    @pytest.mark.asyncio
    async def test_code_block_preserves_empty_lines(self) -> None:
        """Test that empty lines inside code blocks are preserved."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        # Python code with empty line (simpler case)
        content = """```python
line1

line3
```"""
        await type_markdown_content(mock_page, content)

        # Empty line should trigger Enter press
        press_calls = mock_page.keyboard.press.call_args_list
        pressed_keys = [call[0][0] for call in press_calls]
        # Count Enter presses during code block (should include one for empty line)
        enter_count = pressed_keys.count("Enter")
        # Expect: Enter after line1, Enter for empty line, Enter after line3 = 3 minimum
        # (plus possible ArrowDown presses for exiting code block)
        assert enter_count >= 2, f"Expected at least 2 Enter presses, got {enter_count}"

    @pytest.mark.asyncio
    async def test_code_block_with_comment_line(self) -> None:
        """Test that comment lines (# ...) in code blocks are typed."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """```python
# This is a comment
code = "value"
```"""
        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # Comment line should be typed
        assert "# This is a comment" in typed_texts

    @pytest.mark.asyncio
    async def test_code_block_empty_line_types_enter(self) -> None:
        """Test that empty lines in code blocks type Enter key."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """```
line1

line3
```"""
        await type_markdown_content(mock_page, content)

        # Check that Enter was pressed for the empty line
        press_calls = mock_page.keyboard.press.call_args_list
        pressed_keys = [call[0][0] for call in press_calls]
        # Should have multiple Enter presses including one for empty line
        assert pressed_keys.count("Enter") >= 2


class TestRubyPattern:
    """Tests for ruby notation pattern - Issue #110 Problem 3."""

    def test_ruby_pattern_matches_full_width_bar(self) -> None:
        """Test ruby pattern with full-width vertical bar."""
        from note_mcp.browser.typing_helpers import _RUBY_PATTERN

        match = _RUBY_PATTERN.search("｜漢字《かんじ》")
        assert match is not None

    def test_ruby_pattern_matches_half_width_bar(self) -> None:
        """Test ruby pattern with half-width vertical bar."""
        from note_mcp.browser.typing_helpers import _RUBY_PATTERN

        match = _RUBY_PATTERN.search("|漢字《かんじ》")
        assert match is not None

    def test_ruby_pattern_matches_without_bar(self) -> None:
        """Test ruby pattern without vertical bar (just kanji+ruby)."""
        from note_mcp.browser.typing_helpers import _RUBY_PATTERN

        match = _RUBY_PATTERN.search("漢字《かんじ》")
        assert match is not None


class TestTypeWithRuby:
    """Tests for _type_with_ruby function - Issue #110 Problem 3."""

    @pytest.mark.asyncio
    async def test_no_ruby_types_directly(self) -> None:
        """Test that text without ruby is typed directly."""
        from note_mcp.browser.typing_helpers import _type_with_ruby

        mock_page = AsyncMock()
        remaining = await _type_with_ruby(mock_page, "普通のテキスト")
        mock_page.keyboard.type.assert_called_once_with("普通のテキスト")
        assert remaining == ""

    @pytest.mark.asyncio
    async def test_ruby_types_with_vertical_bar(self) -> None:
        """Test that ruby notation is typed with required vertical bar."""
        from note_mcp.browser.typing_helpers import _type_with_ruby

        mock_page = AsyncMock()
        # Input without bar
        await _type_with_ruby(mock_page, "漢字《かんじ》")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        # Output should contain vertical bar (required by note.com)
        typed_all = "".join(typed_texts)
        assert "｜" in typed_all or "|" in typed_all

    @pytest.mark.asyncio
    async def test_ruby_preserves_existing_bar(self) -> None:
        """Test that ruby notation preserves existing vertical bar."""
        from note_mcp.browser.typing_helpers import _type_with_ruby

        mock_page = AsyncMock()
        await _type_with_ruby(mock_page, "｜東京《とうきょう》")

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        typed_all = "".join(typed_texts)
        # Should preserve the bar and contain the text
        assert "東京" in typed_all
        assert "とうきょう" in typed_all

    @pytest.mark.asyncio
    async def test_ruby_with_text_before_and_after(self) -> None:
        """Test ruby notation with surrounding text."""
        from note_mcp.browser.typing_helpers import _type_with_ruby

        mock_page = AsyncMock()
        remaining = await _type_with_ruby(mock_page, "前の｜漢字《かんじ》後の")

        # Should type text before ruby, then ruby, and return remaining
        calls = mock_page.keyboard.type.call_args_list
        assert len(calls) >= 1
        # Remaining text should be "後の"
        assert remaining == "後の"


class TestTypeMarkdownContentRuby:
    """Tests for type_markdown_content with ruby handling - Issue #110 Problem 3."""

    @pytest.mark.asyncio
    async def test_ruby_does_not_break_subsequent_content(self) -> None:
        """Test that ruby notation doesn't break subsequent content."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = """｜漢字《かんじ》のテキスト

## 次の見出し

通常の段落"""
        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]

        # Heading should be processed correctly
        assert "## " in typed_texts
        assert "次の見出し" in typed_texts
        # Paragraph should be typed
        assert "通常の段落" in typed_texts

    @pytest.mark.asyncio
    async def test_multiple_ruby_in_same_line(self) -> None:
        """Test multiple ruby notations in the same line."""
        mock_page = AsyncMock()
        mock_page.locator.return_value.first.click = AsyncMock()

        content = "｜東京《とうきょう》の｜天気《てんき》は晴れです。"
        await type_markdown_content(mock_page, content)

        calls = mock_page.keyboard.type.call_args_list
        typed_texts = [call[0][0] for call in calls]
        typed_all = "".join(typed_texts)

        # Both ruby notations should be typed
        assert "東京" in typed_all
        assert "天気" in typed_all
        assert "晴れです" in typed_all
