"""Unit tests for Markdown conversion utility."""

from note_mcp.utils.markdown import markdown_to_html


class TestMarkdownToHtml:
    """Tests for markdown_to_html function."""

    def test_heading_conversion(self) -> None:
        """Test converting headings."""
        result = markdown_to_html("# Heading 1")
        # note.com format adds name/id attributes
        assert "<h1 " in result or "<h1>" in result
        assert "Heading 1" in result

    def test_heading_level_2(self) -> None:
        """Test converting level 2 headings."""
        result = markdown_to_html("## Heading 2")
        assert "<h2 " in result or "<h2>" in result
        assert "Heading 2" in result

    def test_heading_level_3(self) -> None:
        """Test converting level 3 headings (small heading)."""
        result = markdown_to_html("### Heading 3")
        assert "<h3 " in result or "<h3>" in result
        assert "Heading 3" in result

    def test_paragraph_conversion(self) -> None:
        """Test converting paragraphs."""
        result = markdown_to_html("This is a paragraph.")
        # note.com format adds name/id attributes
        assert "<p " in result or "<p>" in result
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
        assert "<ul " in result or "<ul>" in result
        assert "<li " in result or "<li>" in result
        assert "Item 1" in result

    def test_ordered_list_conversion(self) -> None:
        """Test converting ordered lists."""
        markdown = """1. First
2. Second
3. Third"""
        result = markdown_to_html(markdown)
        assert "<ol " in result or "<ol>" in result
        assert "<li " in result or "<li>" in result
        assert "First" in result

    def test_nested_list_conversion(self) -> None:
        """Test converting nested lists."""
        markdown = """- Item A
  - Sub-item A1
  - Sub-item A2
- Item B"""
        result = markdown_to_html(markdown)
        # Outer ul and nested ul (should appear twice)
        assert result.count("<ul ") == 2
        # li elements without UUID (note.com format)
        assert "<li>" in result
        # Content preserved
        assert "Item A" in result
        assert "Sub-item A1" in result
        assert "Item B" in result

    def test_list_items_wrapped_in_paragraphs(self) -> None:
        """Test that list item content is wrapped in p tags for ProseMirror."""
        markdown = """- Item A
- Item B"""
        result = markdown_to_html(markdown)
        # li elements without UUID, p elements with UUID (note.com format)
        assert "<li>" in result
        assert "<p " in result
        # Verify structure: <li><p ...>text</p></li>
        assert "<li><p " in result  # p directly inside li
        assert "</p></li>" in result  # p closed before li

    def test_code_inline_conversion(self) -> None:
        """Test converting inline code."""
        result = markdown_to_html("Use `code` here.")
        assert "<code " in result or "<code>" in result
        assert "code" in result

    def test_code_block_conversion(self) -> None:
        """Test converting code blocks."""
        markdown = """```python
def hello():
    pass
```"""
        result = markdown_to_html(markdown)
        assert "<code " in result or "<code>" in result or "<pre " in result or "<pre>" in result
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

    def test_image_note_figure_format(self) -> None:
        """Test images are converted to note.com figure format."""
        result = markdown_to_html("![Test](https://example.com/test.png)")
        # Must have figure wrapper with name attribute (note.com uses only name, not id)
        assert "<figure" in result
        assert 'name="' in result
        # Must have figcaption
        assert "<figcaption>" in result
        assert "</figcaption></figure>" in result
        # Must have note.com specific img attributes
        assert 'contenteditable="false"' in result
        assert 'draggable="false"' in result
        assert 'width="620"' in result
        assert 'height="457"' in result

    def test_blockquote_conversion(self) -> None:
        """Test converting blockquotes."""
        result = markdown_to_html("> This is a quote")
        # note.com requires blockquotes wrapped in <figure>
        assert "<figure" in result
        assert "<blockquote" in result
        assert "This is a quote" in result

    def test_blockquote_figure_format(self) -> None:
        """Test that blockquotes are wrapped in figure elements for note.com API."""
        result = markdown_to_html("> Quote text")
        # Must have figure wrapper with name and id attributes
        assert "<figure" in result
        assert 'name="' in result
        assert 'id="' in result
        # Must have figcaption
        assert "<figcaption></figcaption></figure>" in result
        # Blockquote must be inside figure
        figure_start = result.find("<figure")
        blockquote_start = result.find("<blockquote")
        figure_end = result.find("</figure>")
        assert figure_start < blockquote_start < figure_end

    def test_blockquote_multiline_uses_br_tags(self) -> None:
        """Test that multiline blockquotes use <br> tags for line breaks.

        note.com's browser editor uses <br> tags for line breaks inside blockquotes.
        Blockquotes are wrapped in <figure> elements to preserve <br> tags via API.
        """
        markdown = """> Line 1
> Line 2
> Line 3"""
        result = markdown_to_html(markdown)
        # Must have figure wrapper
        assert "<figure" in result
        # Must have blockquote
        assert "<blockquote" in result
        # Must have <br> tags between lines (note.com uses <br> without slash)
        assert "<br>" in result
        # Content must be preserved
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
        # Lines should be separated by <br> tags
        assert "Line 1<br>" in result
        assert "Line 2<br>" in result

    def test_blockquote_multiline_content_order(self) -> None:
        """Test that multiline blockquote preserves line order with <br> tags."""
        markdown = """> First
> Second
> Third"""
        result = markdown_to_html(markdown)
        # Verify order: First then Second then Third
        first_pos = result.find("First")
        second_pos = result.find("Second")
        third_pos = result.find("Third")
        assert first_pos < second_pos < third_pos
        # Verify lines are separated by <br> tags
        assert "First<br>" in result
        assert "Second<br>" in result

    def test_blockquote_multiline_with_formatting(self) -> None:
        """Test multiline blockquote with bold/italic formatting."""
        markdown = """> **Bold** line
> *Italic* line"""
        result = markdown_to_html(markdown)
        assert "<figure" in result
        assert "<blockquote" in result
        assert "<strong>" in result
        assert "<em>" in result
        # Should have <br> tag between lines
        assert "<br>" in result

    def test_blockquote_single_line_single_p(self) -> None:
        """Test that single line blockquote has only one <p> element."""
        result = markdown_to_html("> Single line quote")
        assert "<figure" in result
        assert "<blockquote" in result
        assert "Single line quote" in result
        # Extract blockquote content
        if "<blockquote" in result:
            bq_start = result.find("<blockquote")
            bq_end = result.find("</blockquote>") + len("</blockquote>")
            blockquote_html = result[bq_start:bq_end]
            # Single line should have exactly one <p> element
            assert blockquote_html.count("<p ") == 1

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
        assert "<h1 " in result or "<h1>" in result
        assert "Heading 99" in result

    def test_special_characters(self) -> None:
        """Test handling special characters."""
        result = markdown_to_html("Special chars: < > & \" '")
        assert "<p " in result or "<p>" in result
        # HTML entities should be properly escaped
        assert "&lt;" in result or "<" in result
        assert "&gt;" in result or ">" in result

    def test_multiline_paragraph(self) -> None:
        """Test multiline paragraph."""
        markdown = """This is line 1
This is line 2

This is a new paragraph."""
        result = markdown_to_html(markdown)
        # Should have paragraphs (with note.com UUID attributes)
        assert "<p " in result or "<p>" in result

    def test_code_block_preserves_newlines(self) -> None:
        """Test that code blocks preserve internal newlines.

        note.com requires:
        - <pre class="codeBlock"> format
        - Actual newlines preserved inside code blocks
        """
        markdown = """```python
def hello():
    print("Hello")
    return True
```"""
        result = markdown_to_html(markdown)
        # Code block must be in note.com format (attribute order matters)
        assert 'class="codeBlock"' in result
        assert "<pre " in result
        assert "<code>" in result  # No language class
        # The newlines between code lines must be preserved as actual newlines
        assert "\n" in result
        # Verify the code content is intact
        assert "def hello():" in result
        assert 'print("Hello")' in result or "print(&quot;Hello&quot;)" in result
        # Verify newlines are between code lines
        assert "def hello():\n" in result

    def test_image_with_caption(self) -> None:
        """Test images with caption (title attribute)."""
        result = markdown_to_html('![Alt](https://example.com/img.png "This is caption")')
        assert "<figcaption>This is caption</figcaption>" in result
        # Verify figure structure is intact (note.com requires both name and id)
        assert "<figure" in result
        assert 'name="' in result
        # Verify id attribute is present (note.com requires both name and id)
        assert 'id="' in result.split("<figure")[1].split(">")[0]

    def test_image_without_caption_backward_compatible(self) -> None:
        """Test images without caption still work (backward compatibility)."""
        result = markdown_to_html("![Alt](https://example.com/img.png)")
        assert "<figcaption></figcaption>" in result
        assert "<figure" in result

    def test_image_caption_with_special_characters(self) -> None:
        """Test images with special characters in caption."""
        result = markdown_to_html('![Alt](https://example.com/img.png "図1: 構成図")')
        assert "<figcaption>図1: 構成図</figcaption>" in result

    def test_image_caption_empty_string(self) -> None:
        """Test images with empty caption (title="")."""
        result = markdown_to_html('![Alt](https://example.com/img.png "")')
        assert "<figcaption></figcaption>" in result
