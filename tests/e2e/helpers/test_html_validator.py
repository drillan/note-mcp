"""Unit tests for HtmlValidator.

Tests the BeautifulSoup-based static HTML validation without Playwright.
"""

from __future__ import annotations

from tests.e2e.helpers.html_validator import HtmlValidator


class TestHtmlValidatorHeading:
    """Tests for validate_heading method."""

    async def test_h2_found(self) -> None:
        """Test H2 heading detection."""
        html = "<html><body><h2>テスト見出し</h2></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_heading(2, "テスト見出し")

        assert result.success
        assert "h2" in result.expected.lower()
        assert result.actual == "テスト見出し"

    async def test_h3_found(self) -> None:
        """Test H3 heading detection."""
        html = "<html><body><h3>H3見出し</h3></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_heading(3, "H3見出し")

        assert result.success
        assert "h3" in result.expected.lower()

    async def test_heading_not_found(self) -> None:
        """Test when heading is not present."""
        html = "<html><body><p>通常テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_heading(2, "存在しない見出し")

        assert not result.success
        assert result.actual is None

    async def test_heading_with_different_text(self) -> None:
        """Test when heading exists but with different text."""
        html = "<html><body><h2>別の見出し</h2></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_heading(2, "期待する見出し")

        assert not result.success


class TestHtmlValidatorBold:
    """Tests for validate_bold method."""

    async def test_strong_tag_found(self) -> None:
        """Test <strong> tag detection."""
        html = "<html><body><p>通常 <strong>太字テキスト</strong> 後続</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_bold("太字テキスト")

        assert result.success
        assert "strong" in result.expected.lower()

    async def test_b_tag_fallback(self) -> None:
        """Test <b> tag as fallback."""
        html = "<html><body><p>通常 <b>太字テキスト</b> 後続</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_bold("太字テキスト")

        assert result.success
        assert "[FALLBACK]" in result.message

    async def test_bold_not_found(self) -> None:
        """Test when bold text is not present."""
        html = "<html><body><p>通常テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_bold("太字テキスト")

        assert not result.success


class TestHtmlValidatorStrikethrough:
    """Tests for validate_strikethrough method."""

    async def test_s_tag_found(self) -> None:
        """Test <s> tag detection."""
        html = "<html><body><p>通常 <s>削除テキスト</s> 後続</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_strikethrough("削除テキスト")

        assert result.success
        assert "<s>" in result.expected

    async def test_strikethrough_not_found(self) -> None:
        """Test when strikethrough is not present."""
        html = "<html><body><p>通常テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_strikethrough("削除テキスト")

        assert not result.success


class TestHtmlValidatorCodeBlock:
    """Tests for validate_code_block method."""

    async def test_code_block_found(self) -> None:
        """Test <pre><code> detection."""
        html = "<html><body><pre><code>print('hello')</code></pre></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_code_block("print('hello')")

        assert result.success
        assert "<pre><code>" in result.expected

    async def test_code_block_partial_match(self) -> None:
        """Test partial code match."""
        html = "<html><body><pre><code>def foo():\n    return 42</code></pre></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_code_block("return 42")

        assert result.success

    async def test_code_block_not_found(self) -> None:
        """Test when code block is not present."""
        html = "<html><body><p>テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_code_block("print('hello')")

        assert not result.success


class TestHtmlValidatorAlignment:
    """Tests for validate_alignment method."""

    async def test_center_alignment(self) -> None:
        """Test center alignment detection."""
        html = '<html><body><p style="text-align: center">中央テキスト</p></body></html>'
        validator = HtmlValidator(html)
        result = await validator.validate_alignment("中央テキスト", "center")

        assert result.success

    async def test_right_alignment(self) -> None:
        """Test right alignment detection."""
        html = '<html><body><p style="text-align: right">右揃えテキスト</p></body></html>'
        validator = HtmlValidator(html)
        result = await validator.validate_alignment("右揃えテキスト", "right")

        assert result.success

    async def test_alignment_not_found(self) -> None:
        """Test when alignment is not present."""
        html = "<html><body><p>通常テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_alignment("通常テキスト", "center")

        assert not result.success


class TestHtmlValidatorBlockquote:
    """Tests for validate_blockquote method."""

    async def test_blockquote_found(self) -> None:
        """Test <blockquote> detection."""
        html = "<html><body><blockquote>引用テキスト</blockquote></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_blockquote("引用テキスト")

        assert result.success
        assert "<blockquote>" in result.expected

    async def test_blockquote_not_found(self) -> None:
        """Test when blockquote is not present."""
        html = "<html><body><p>通常テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_blockquote("引用テキスト")

        assert not result.success


class TestHtmlValidatorLink:
    """Tests for validate_link method."""

    async def test_link_found(self) -> None:
        """Test <a href> detection."""
        html = '<html><body><a href="https://example.com">リンクテキスト</a></body></html>'
        validator = HtmlValidator(html)
        result = await validator.validate_link("リンクテキスト", "https://example.com")

        assert result.success

    async def test_link_wrong_url(self) -> None:
        """Test link with wrong URL."""
        html = '<html><body><a href="https://other.com">リンクテキスト</a></body></html>'
        validator = HtmlValidator(html)
        result = await validator.validate_link("リンクテキスト", "https://example.com")

        assert not result.success

    async def test_link_not_found(self) -> None:
        """Test when link is not present."""
        html = "<html><body><p>テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_link("リンクテキスト", "https://example.com")

        assert not result.success


class TestHtmlValidatorHorizontalLine:
    """Tests for validate_horizontal_line method."""

    async def test_hr_found(self) -> None:
        """Test <hr> detection."""
        html = "<html><body><p>前</p><hr><p>後</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_horizontal_line()

        assert result.success
        assert "<hr>" in result.expected

    async def test_hr_multiple(self) -> None:
        """Test multiple <hr> elements."""
        html = "<html><body><hr><hr><hr></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_horizontal_line()

        assert result.success
        assert "3" in result.message

    async def test_hr_not_found(self) -> None:
        """Test when <hr> is not present."""
        html = "<html><body><p>テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_horizontal_line()

        assert not result.success


class TestHtmlValidatorUnorderedList:
    """Tests for validate_unordered_list method."""

    async def test_ul_single_item(self) -> None:
        """Test <ul> with single item."""
        html = "<html><body><ul><li>項目1</li></ul></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_unordered_list(["項目1"])

        assert result.success

    async def test_ul_multiple_items(self) -> None:
        """Test <ul> with multiple items."""
        html = "<html><body><ul><li>項目1</li><li>項目2</li><li>項目3</li></ul></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_unordered_list(["項目1", "項目2", "項目3"])

        assert result.success

    async def test_ul_missing_item(self) -> None:
        """Test <ul> with missing item."""
        html = "<html><body><ul><li>項目1</li><li>項目2</li></ul></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_unordered_list(["項目1", "項目3"])

        assert not result.success
        assert "項目3" in result.message

    async def test_ul_not_found(self) -> None:
        """Test when <ul> is not present."""
        html = "<html><body><p>テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_unordered_list(["項目1"])

        assert not result.success

    async def test_ul_empty_items(self) -> None:
        """Test with empty items list."""
        html = "<html><body><ul><li>項目1</li></ul></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_unordered_list([])

        assert not result.success


class TestHtmlValidatorOrderedList:
    """Tests for validate_ordered_list method."""

    async def test_ol_single_item(self) -> None:
        """Test <ol> with single item."""
        html = "<html><body><ol><li>項目1</li></ol></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_ordered_list(["項目1"])

        assert result.success

    async def test_ol_multiple_items(self) -> None:
        """Test <ol> with multiple items."""
        html = "<html><body><ol><li>第一</li><li>第二</li><li>第三</li></ol></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_ordered_list(["第一", "第二", "第三"])

        assert result.success

    async def test_ol_missing_item(self) -> None:
        """Test <ol> with missing item."""
        html = "<html><body><ol><li>第一</li></ol></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_ordered_list(["第一", "第二"])

        assert not result.success

    async def test_ol_not_found(self) -> None:
        """Test when <ol> is not present."""
        html = "<html><body><p>テキスト</p></body></html>"
        validator = HtmlValidator(html)
        result = await validator.validate_ordered_list(["項目1"])

        assert not result.success
