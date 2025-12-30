"""Unit tests for HTML to Markdown conversion utility.

Tests for html_to_markdown function that converts note.com HTML format back to Markdown.
"""

from note_mcp.utils.html_to_markdown import html_to_markdown
from note_mcp.utils.markdown_to_html import markdown_to_html


class TestHtmlToMarkdown:
    """Tests for html_to_markdown function."""

    # === Basic Conversion Tests ===

    def test_code_block_conversion(self) -> None:
        """Test converting code blocks to fenced markdown."""
        html = """<pre name="abc12345" id="abc12345" class="codeBlock"><code>def hello():
    print("Hello")</code></pre>"""
        result = html_to_markdown(html)
        assert "```" in result
        assert "def hello():" in result
        assert 'print("Hello")' in result

    def test_code_block_preserves_newlines(self) -> None:
        """Test that code blocks preserve internal newlines."""
        html = """<pre class="codeBlock"><code>line1
line2
line3</code></pre>"""
        result = html_to_markdown(html)
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result
        # Verify newlines are preserved
        assert "line1\nline2\nline3" in result or "line1\nline2\nline3" in result.replace("\r\n", "\n")

    def test_heading_conversion(self) -> None:
        """Test converting headings (h1-h6) to markdown."""
        html = '<h1 name="abc" id="abc">Heading 1</h1>'
        result = html_to_markdown(html)
        assert "# Heading 1" in result

        html = '<h2 name="abc" id="abc">Heading 2</h2>'
        result = html_to_markdown(html)
        assert "## Heading 2" in result

        html = '<h3 name="abc" id="abc">Heading 3</h3>'
        result = html_to_markdown(html)
        assert "### Heading 3" in result

    def test_paragraph_conversion(self) -> None:
        """Test converting paragraphs."""
        html = '<p name="abc" id="abc">This is a paragraph.</p>'
        result = html_to_markdown(html)
        assert "This is a paragraph." in result
        assert "<p" not in result

    # === List Tests ===

    def test_unordered_list_conversion(self) -> None:
        """Test converting unordered lists."""
        html = """<ul name="abc" id="abc">
            <li><p name="def">Item 1</p></li>
            <li><p name="ghi">Item 2</p></li>
            <li><p name="jkl">Item 3</p></li>
        </ul>"""
        result = html_to_markdown(html)
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result

    def test_ordered_list_conversion(self) -> None:
        """Test converting ordered lists."""
        html = """<ol name="abc" id="abc">
            <li><p name="def">First</p></li>
            <li><p name="ghi">Second</p></li>
            <li><p name="jkl">Third</p></li>
        </ol>"""
        result = html_to_markdown(html)
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result

    def test_nested_list_conversion(self) -> None:
        """Test converting nested lists."""
        html = """<ul name="abc" id="abc">
            <li><p name="def">Item A</p>
                <ul name="nested">
                    <li><p name="sub1">Sub-item A1</p></li>
                    <li><p name="sub2">Sub-item A2</p></li>
                </ul>
            </li>
            <li><p name="ghi">Item B</p></li>
        </ul>"""
        result = html_to_markdown(html)
        assert "- Item A" in result
        assert "Sub-item A1" in result
        assert "Sub-item A2" in result
        assert "- Item B" in result
        # Nested items should be indented
        lines = result.strip().split("\n")
        sub_items = [line for line in lines if "Sub-item" in line]
        for line in sub_items:
            assert line.startswith("  ") or line.startswith("    ")

    # === Blockquote Tests ===

    def test_blockquote_conversion(self) -> None:
        """Test converting simple blockquotes."""
        html = """<figure name="abc" id="abc">
            <blockquote><p name="def">This is a quote</p></blockquote>
            <figcaption></figcaption>
        </figure>"""
        result = html_to_markdown(html)
        assert "> This is a quote" in result

    def test_blockquote_with_citation(self) -> None:
        """Test converting blockquotes with citation text."""
        html = """<figure name="abc" id="abc">
            <blockquote><p name="def">知識は力なり</p></blockquote>
            <figcaption>フランシス・ベーコン</figcaption>
        </figure>"""
        result = html_to_markdown(html)
        assert "> 知識は力なり" in result
        assert "フランシス・ベーコン" in result
        # Citation should be prefixed with em-dash
        assert "— フランシス・ベーコン" in result or "フランシス・ベーコン" in result

    def test_blockquote_with_citation_url(self) -> None:
        """Test converting blockquotes with citation link."""
        html = """<figure name="abc" id="abc">
            <blockquote><p name="def">引用テキスト</p></blockquote>
            <figcaption><a href="https://example.com">出典名</a></figcaption>
        </figure>"""
        result = html_to_markdown(html)
        assert "> 引用テキスト" in result
        assert "出典名" in result
        assert "https://example.com" in result

    def test_blockquote_multiline(self) -> None:
        """Test converting multiline blockquotes with <br> tags."""
        html = """<figure name="abc" id="abc">
            <blockquote><p name="def">Line 1<br>Line 2<br>Line 3</p></blockquote>
            <figcaption></figcaption>
        </figure>"""
        result = html_to_markdown(html)
        assert "> Line 1" in result
        assert "> Line 2" in result
        assert "> Line 3" in result

    # === Image Tests ===

    def test_image_conversion(self) -> None:
        """Test converting images."""
        html = """<figure name="abc" id="abc">
            <img src="https://example.com/image.png" alt="Alt text" width="620" height="457">
            <figcaption></figcaption>
        </figure>"""
        result = html_to_markdown(html)
        assert "![Alt text](https://example.com/image.png)" in result

    def test_image_with_caption(self) -> None:
        """Test converting images with caption."""
        html = """<figure name="abc" id="abc">
            <img src="https://example.com/image.png" alt="Alt text" width="620" height="457">
            <figcaption>Caption text</figcaption>
        </figure>"""
        result = html_to_markdown(html)
        assert '![Alt text](https://example.com/image.png "Caption text")' in result

    # === Inline Element Tests ===

    def test_link_conversion(self) -> None:
        """Test converting links."""
        html = '<p name="abc"><a href="https://example.com">Example</a></p>'
        result = html_to_markdown(html)
        assert "[Example](https://example.com)" in result

    def test_bold_conversion(self) -> None:
        """Test converting bold text."""
        html = '<p name="abc">This is <strong>bold</strong> text.</p>'
        result = html_to_markdown(html)
        assert "**bold**" in result

    def test_italic_conversion(self) -> None:
        """Test converting italic text."""
        html = '<p name="abc">This is <em>italic</em> text.</p>'
        result = html_to_markdown(html)
        assert "*italic*" in result

    def test_inline_code_conversion(self) -> None:
        """Test converting inline code."""
        html = '<p name="abc">Use <code>code</code> here.</p>'
        result = html_to_markdown(html)
        assert "`code`" in result

    # === Edge Case Tests ===

    def test_uuid_attributes_removed(self) -> None:
        """Test that UUID name/id attributes are removed."""
        html = '<p name="abc12345-6789-abcd-ef01-234567890abc" id="abc12345-6789-abcd-ef01-234567890abc">Text</p>'
        result = html_to_markdown(html)
        assert "abc12345-6789-abcd-ef01-234567890abc" not in result
        assert "Text" in result

    def test_html_entities_decoded(self) -> None:
        """Test that HTML entities are decoded."""
        html = '<p name="abc">&lt;tag&gt; &amp; &quot;quoted&quot;</p>'
        result = html_to_markdown(html)
        assert "<tag>" in result
        assert "&" in result
        assert '"quoted"' in result

    def test_empty_input(self) -> None:
        """Test empty input returns empty string."""
        assert html_to_markdown("") == ""
        assert html_to_markdown("   ") == ""
        assert html_to_markdown("\n\n") == ""

    def test_horizontal_rule_conversion(self) -> None:
        """Test converting horizontal rules."""
        html = '<hr name="abc" id="abc">'
        result = html_to_markdown(html)
        assert "---" in result

    # === Roundtrip Tests ===

    def test_roundtrip_simple(self) -> None:
        """Test that simple markdown survives roundtrip conversion.

        markdown -> html -> markdown should preserve meaning.
        """
        original = "# Heading\n\nThis is a paragraph."
        html = markdown_to_html(original)
        result = html_to_markdown(html)
        assert "# Heading" in result or "Heading" in result
        assert "This is a paragraph" in result

    def test_roundtrip_complex(self) -> None:
        """Test that complex markdown survives roundtrip conversion."""
        original = """# Title

This is a **bold** and *italic* paragraph.

- Item 1
- Item 2

```
code block
```

> Quote text"""
        html = markdown_to_html(original)
        result = html_to_markdown(html)
        # Key elements should be preserved
        assert "Title" in result
        assert "bold" in result
        assert "italic" in result
        assert "Item 1" in result
        assert "code block" in result
        assert "Quote" in result

    # === Real note.com HTML Pattern Tests ===

    def test_code_block_without_codeblock_class(self) -> None:
        """Test code block without class='codeBlock' (actual note.com format)."""
        html = """<pre name="abc"><code>
def hello():
    print("Hello")
```</code></pre>"""
        result = html_to_markdown(html)
        assert "```" in result
        assert "def hello():" in result
        assert 'print("Hello")' in result
        # Fence markers inside code should be removed
        lines = result.strip().split("\n")
        # Should have opening ```, code lines, closing ```
        assert lines[0] == "```"
        assert lines[-1] == "```"
        # No extra ``` in the middle
        middle_lines = lines[1:-1]
        assert not any(line.strip() == "```" for line in middle_lines)

    def test_code_block_with_remaining_fence_markers(self) -> None:
        """Test that remaining fence markers are properly cleaned."""
        html = """<pre><code>```python
x = 1
y = 2
```</code></pre>"""
        result = html_to_markdown(html)
        # Should have clean code block
        assert "x = 1" in result
        assert "y = 2" in result
        # Count fence markers - should be exactly 2 (opening and closing)
        fence_count = result.count("```")
        assert fence_count == 2, f"Expected 2 fence markers, got {fence_count}"

    def test_code_block_pre_without_code_tag(self) -> None:
        """Test <pre> without <code> tag (some note.com ProseMirror formats)."""
        html = """<pre>def hello():
    print("Hello")
</pre>"""
        result = html_to_markdown(html)
        # Should have fence markers
        assert "```" in result
        assert "def hello():" in result
        assert 'print("Hello")' in result
        # Count fence markers - should be exactly 2 (opening and closing)
        fence_count = result.count("```")
        assert fence_count == 2, f"Expected 2 fence markers, got {fence_count}"

    # Strikethrough tests - Issue #25

    def test_strikethrough_conversion(self) -> None:
        """Test converting strikethrough HTML to markdown."""
        html = '<p name="abc">This is <s>deleted</s> text.</p>'
        result = html_to_markdown(html)
        assert "~~deleted~~" in result

    def test_roundtrip_strikethrough(self) -> None:
        """Test strikethrough survives roundtrip conversion."""
        original = "This is ~~deleted~~ text."
        html = markdown_to_html(original)
        result = html_to_markdown(html)
        assert "~~deleted~~" in result
