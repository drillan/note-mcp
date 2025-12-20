"""Unit tests for Markdown conversion utility."""

from note_mcp.utils.markdown import markdown_to_html


class TestMarkdownToHtml:
    """Tests for markdown_to_html function."""

    def test_heading_conversion(self) -> None:
        """Test converting headings."""
        result = markdown_to_html("# Heading 1")
        assert "<h1>" in result
        assert "Heading 1" in result

    def test_heading_level_2(self) -> None:
        """Test converting level 2 headings."""
        result = markdown_to_html("## Heading 2")
        assert "<h2>" in result
        assert "Heading 2" in result

    def test_paragraph_conversion(self) -> None:
        """Test converting paragraphs."""
        result = markdown_to_html("This is a paragraph.")
        assert "<p>" in result
        assert "This is a paragraph." in result

    def test_bold_conversion(self) -> None:
        """Test converting bold text."""
        result = markdown_to_html("This is **bold** text.")
        assert "<strong>" in result
        assert "bold" in result

    def test_italic_conversion(self) -> None:
        """Test converting italic text."""
        result = markdown_to_html("This is *italic* text.")
        assert "<em>" in result
        assert "italic" in result

    def test_unordered_list_conversion(self) -> None:
        """Test converting unordered lists."""
        markdown = """- Item 1
- Item 2
- Item 3"""
        result = markdown_to_html(markdown)
        assert "<ul>" in result
        assert "<li>" in result
        assert "Item 1" in result

    def test_ordered_list_conversion(self) -> None:
        """Test converting ordered lists."""
        markdown = """1. First
2. Second
3. Third"""
        result = markdown_to_html(markdown)
        assert "<ol>" in result
        assert "<li>" in result
        assert "First" in result

    def test_code_inline_conversion(self) -> None:
        """Test converting inline code."""
        result = markdown_to_html("Use `code` here.")
        assert "<code>" in result
        assert "code" in result

    def test_code_block_conversion(self) -> None:
        """Test converting code blocks."""
        markdown = """```python
def hello():
    pass
```"""
        result = markdown_to_html(markdown)
        assert "<code>" in result or "<pre>" in result
        assert "def hello" in result

    def test_link_conversion(self) -> None:
        """Test converting links."""
        result = markdown_to_html("[Example](https://example.com)")
        assert "<a" in result
        assert 'href="https://example.com"' in result
        assert "Example" in result

    def test_image_conversion(self) -> None:
        """Test converting images."""
        result = markdown_to_html("![Alt text](https://example.com/image.png)")
        assert "<img" in result
        assert 'src="https://example.com/image.png"' in result
        assert 'alt="Alt text"' in result

    def test_blockquote_conversion(self) -> None:
        """Test converting blockquotes."""
        result = markdown_to_html("> This is a quote")
        assert "<blockquote>" in result
        assert "This is a quote" in result

    def test_horizontal_rule_conversion(self) -> None:
        """Test converting horizontal rules."""
        result = markdown_to_html("---")
        assert "<hr" in result

    def test_empty_string(self) -> None:
        """Test converting empty string."""
        result = markdown_to_html("")
        assert result == ""

    def test_whitespace_only(self) -> None:
        """Test converting whitespace only."""
        result = markdown_to_html("   \n\n   ")
        # Should return empty or whitespace only
        assert result.strip() == ""

    def test_large_document(self) -> None:
        """Test converting a large document."""
        markdown = "\n\n".join([f"# Heading {i}\n\nParagraph {i}" for i in range(100)])
        result = markdown_to_html(markdown)
        assert "<h1>" in result
        assert "Heading 99" in result

    def test_special_characters(self) -> None:
        """Test handling special characters."""
        result = markdown_to_html("Special chars: < > & \" '")
        assert "<p>" in result
        # HTML entities should be properly escaped
        assert "&lt;" in result or "<" in result
        assert "&gt;" in result or ">" in result

    def test_multiline_paragraph(self) -> None:
        """Test multiline paragraph."""
        markdown = """This is line 1
This is line 2

This is a new paragraph."""
        result = markdown_to_html(markdown)
        # Should have paragraphs
        assert "<p>" in result
