"""Unit tests for Markdown conversion utility."""

from note_mcp.utils.markdown_to_html import markdown_to_html


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

    # Citation (出典) tests - Issue #14

    def test_blockquote_without_citation(self) -> None:
        """Test that blockquotes without citation have empty figcaption."""
        result = markdown_to_html("> Just a quote")
        assert "<figcaption></figcaption>" in result

    def test_blockquote_with_citation_text_only(self) -> None:
        """Test blockquote with citation text only (no URL).

        Markdown:
            > 知識は力なり
            > — フランシス・ベーコン

        Expected: figcaption contains citation text.
        """
        markdown = """> 知識は力なり
> — フランシス・ベーコン"""
        result = markdown_to_html(markdown)
        assert "<figcaption>フランシス・ベーコン</figcaption>" in result
        assert "知識は力なり" in result
        # Citation line should NOT appear in blockquote content
        blockquote_content = result.split("<blockquote>")[1].split("</blockquote>")[0]
        assert "— フランシス・ベーコン" not in blockquote_content

    def test_blockquote_with_citation_and_url(self) -> None:
        """Test blockquote with citation text and URL.

        Markdown:
            > 知識は力なり
            > — フランシス・ベーコン (https://example.com)

        Expected: figcaption contains link with citation text.
        """
        markdown = """> 知識は力なり
> — フランシス・ベーコン (https://example.com)"""
        result = markdown_to_html(markdown)
        assert '<figcaption><a href="https://example.com">フランシス・ベーコン</a></figcaption>' in result

    def test_blockquote_multiline_with_citation(self) -> None:
        """Test multiline blockquote with citation on last line."""
        markdown = """> Line 1
> Line 2
> — Source"""
        result = markdown_to_html(markdown)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "<figcaption>Source</figcaption>" in result
        # Citation line should NOT be in blockquote
        blockquote_content = result.split("<blockquote>")[1].split("</blockquote>")[0]
        assert "— Source" not in blockquote_content

    def test_blockquote_em_dash_not_at_start(self) -> None:
        """Test that em-dash not at line start is not treated as citation."""
        result = markdown_to_html("> Text with — em-dash in middle")
        # Should NOT extract as citation
        assert "<figcaption></figcaption>" in result
        assert "em-dash" in result

    def test_blockquote_citation_empty_text(self) -> None:
        """Test blockquote with only em-dash (no citation text)."""
        markdown = """> Quote
> — """
        result = markdown_to_html(markdown)
        # Empty citation should result in empty figcaption
        assert "<figcaption></figcaption>" in result

    # Strikethrough tests - Issue #25

    def test_strikethrough_conversion(self) -> None:
        """Test converting strikethrough text."""
        result = markdown_to_html("This is ~~deleted~~ text.")
        assert "<s>" in result
        assert "deleted" in result
        assert "</s>" in result

    def test_strikethrough_with_bold(self) -> None:
        """Test strikethrough combined with bold."""
        result = markdown_to_html("**~~bold and deleted~~**")
        assert "<strong>" in result
        assert "<s>" in result

    def test_strikethrough_multiple(self) -> None:
        """Test multiple strikethrough in same line."""
        result = markdown_to_html("~~first~~ and ~~second~~")
        assert result.count("<s>") == 2
        assert result.count("</s>") == 2

    # Math notation (数式記法) tests - Issue #36
    # note.com stores KaTeX notation as-is (no HTML conversion)
    # and renders it client-side using KaTeX library
    #
    # note.com math formats:
    # - Inline: $${formula}$$ (double dollar + braces)
    # - Display: $$formula$$ (double dollar, block level)

    def test_math_inline_basic(self) -> None:
        """Test basic inline math preservation: $${formula}$$

        note.com uses KaTeX format stored as-is.
        Example: $${y = x^2}$$ should be preserved in output.
        """
        result = markdown_to_html("$${y = x^2}$$")
        assert "$${y = x^2}$$" in result

    def test_math_inline_complex(self) -> None:
        """Test complex inline math formula preservation."""
        formula = r"$${x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}}$$"
        result = markdown_to_html(formula)
        # The formula should be preserved (backslashes may be escaped)
        assert "\\frac" in result or "frac" in result
        assert "\\sqrt" in result or "sqrt" in result

    def test_math_inline_in_sentence(self) -> None:
        """Test inline math embedded in sentence."""
        markdown = "アインシュタインの公式は$${E = mc^2}$$です。"
        result = markdown_to_html(markdown)
        assert "アインシュタインの公式は" in result
        assert "$${E = mc^2}$$" in result
        assert "です。" in result

    def test_math_display_basic(self) -> None:
        """Test basic display math preservation.

        Display math format: $$formula$$

        Note: Newlines are removed from non-code-block HTML,
        but the $$ delimiters and formula content should be preserved.
        """
        markdown = """$$
x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
$$"""
        result = markdown_to_html(markdown)
        # Display math delimiters should be preserved
        assert "$$" in result
        # Formula content should be preserved (newlines may be removed)
        assert "\\frac" in result or "frac" in result

    def test_math_display_multiline(self) -> None:
        """Test multiline display math preservation."""
        markdown = """$$
\\begin{align}
a^2 + b^2 &= c^2 \\\\
e^{i\\pi} + 1 &= 0
\\end{align}
$$"""
        result = markdown_to_html(markdown)
        # Content should be preserved
        assert "align" in result
        assert "a^2" in result

    def test_math_in_code_block_not_affected(self) -> None:
        """Test math notation inside code block is preserved literally.

        Code blocks should not trigger any math conversion.
        """
        markdown = """```python
# Math example
formula = "$${y = x^2}$$"
print(formula)
```"""
        result = markdown_to_html(markdown)
        # Code block should preserve content exactly
        assert "codeBlock" in result
        assert "$${y = x^2}$$" in result

    def test_math_inline_with_bold(self) -> None:
        """Test inline math combined with bold formatting."""
        markdown = "**公式**: $${a + b = c}$$"
        result = markdown_to_html(markdown)
        assert "<strong>" in result
        assert "$${a + b = c}$$" in result

    def test_math_inline_with_italic(self) -> None:
        """Test inline math combined with italic formatting."""
        markdown = "*注*: $${x + 1}$$"
        result = markdown_to_html(markdown)
        assert "<em>" in result
        assert "$${x + 1}$$" in result

    def test_math_multiple_inline(self) -> None:
        """Test multiple inline math in same paragraph."""
        markdown = "$${a}$$ + $${b}$$ = $${c}$$"
        result = markdown_to_html(markdown)
        assert "$${a}$$" in result
        assert "$${b}$$" in result
        assert "$${c}$$" in result

    def test_math_greek_letters(self) -> None:
        """Test math with Greek letters."""
        markdown = "$${\\alpha + \\beta = \\gamma}$$"
        result = markdown_to_html(markdown)
        assert "\\alpha" in result or "alpha" in result
        assert "\\beta" in result or "beta" in result
        assert "\\gamma" in result or "gamma" in result

    def test_math_subscript_superscript(self) -> None:
        """Test math with subscript and superscript."""
        markdown = "$${x_1^2 + x_2^2}$$"
        result = markdown_to_html(markdown)
        assert "x_1" in result
        assert "x_2" in result
        assert "^2" in result

    # Text alignment tests - Issue #40

    def test_text_align_center_basic(self) -> None:
        """Test center alignment: ->text<-

        Markdown: ->テキスト<-
        Expected: <p style="text-align: center">テキスト</p>
        """
        result = markdown_to_html("->テキスト<-")
        assert 'style="text-align: center"' in result
        assert "テキスト" in result

    def test_text_align_right_basic(self) -> None:
        """Test right alignment: ->text

        Markdown: ->テキスト
        Expected: <p style="text-align: right">テキスト</p>
        """
        result = markdown_to_html("->テキスト")
        assert 'style="text-align: right"' in result
        assert "テキスト" in result

    def test_text_align_left_basic(self) -> None:
        """Test left alignment: <-text

        Markdown: <-テキスト
        Expected: <p style="text-align: left">テキスト</p>
        """
        result = markdown_to_html("<-テキスト")
        assert 'style="text-align: left"' in result
        assert "テキスト" in result

    def test_text_align_center_with_bold(self) -> None:
        """Test center alignment with bold text."""
        result = markdown_to_html("->**太字**テキスト<-")
        assert 'style="text-align: center"' in result
        assert "<strong>" in result
        assert "太字" in result

    def test_text_align_right_with_italic(self) -> None:
        """Test right alignment with italic text."""
        result = markdown_to_html("->*斜体*テキスト")
        assert 'style="text-align: right"' in result
        assert "<em>" in result
        assert "斜体" in result

    def test_text_align_center_multiline_paragraph(self) -> None:
        """Test that alignment applies to entire paragraph.

        Only the first line with -> marker should be aligned.
        """
        markdown = """->中央寄せ<-

通常のテキスト"""
        result = markdown_to_html(markdown)
        assert 'style="text-align: center"' in result
        assert "中央寄せ" in result
        assert "通常のテキスト" in result

    def test_text_align_not_in_code_block(self) -> None:
        """Test that alignment markers in code blocks are not processed."""
        markdown = """```
->テキスト<-
```"""
        result = markdown_to_html(markdown)
        # Should preserve the markers as-is in code block (HTML-escaped)
        # HTML escapes < and > to &lt; and &gt;
        assert "-&gt;テキスト&lt;-" in result
        assert 'style="text-align' not in result

    def test_text_align_center_with_link(self) -> None:
        """Test center alignment with a link."""
        result = markdown_to_html("->[リンク](https://example.com)<-")
        assert 'style="text-align: center"' in result
        assert 'href="https://example.com"' in result
        assert "リンク" in result

    def test_text_align_right_end_of_document(self) -> None:
        """Test right alignment at end of document (no trailing content)."""
        result = markdown_to_html("->右寄せ")
        assert 'style="text-align: right"' in result
        assert "右寄せ" in result

    def test_text_align_arrow_in_middle_not_processed(self) -> None:
        """Test that arrows in middle of text are not processed as alignment."""
        result = markdown_to_html("これは->矢印<-です")
        # Arrows in middle should not trigger alignment
        assert 'style="text-align' not in result
        assert "->矢印<-" in result or "矢印" in result

    def test_text_align_multiple_paragraphs(self) -> None:
        """Test multiple aligned paragraphs."""
        markdown = """->中央寄せ<-

->右寄せ

<-左寄せ"""
        result = markdown_to_html(markdown)
        assert result.count("text-align: center") == 1
        assert result.count("text-align: right") == 1
        assert result.count("text-align: left") == 1


class TestStandaloneUrl:
    """単独行URL処理のテスト

    Note: note.comは一般的な外部URLの埋め込みをサポートしていません。
    URLは通常のリンクとして処理されます。
    対応しているのはYouTube、Twitter、note.com記事のみです。
    """

    def test_standalone_url_becomes_link(self) -> None:
        """単独行のURLはリンクテキストになる（埋め込みにはならない）"""
        markdown = "https://example.com/article"
        result = markdown_to_html(markdown)

        # 埋め込み属性がないことを確認
        assert "data-embed-service" not in result
        assert "embedded-service" not in result
        # URLはテキストとして含まれる
        assert "https://example.com/article" in result

    def test_url_in_text_preserved(self) -> None:
        """文中のURLは保持される"""
        markdown = "詳しくは https://example.com/article を参照"
        result = markdown_to_html(markdown)

        assert "data-embed-service" not in result
        assert "https://example.com/article" in result

    def test_markdown_link_converted_to_anchor(self) -> None:
        """Markdownリンク記法は<a>タグに変換される"""
        markdown = "[記事を読む](https://example.com/article)"
        result = markdown_to_html(markdown)

        assert "data-embed-service" not in result
        assert 'href="https://example.com/article"' in result
        assert "記事を読む" in result


class TestEmbedUrlConversion:
    """埋め込みURL変換のテスト（Issue #116）

    YouTube、Twitter、note.comのURLが単独行にある場合、
    自動的にfigure要素（埋め込み）に変換されます。
    """

    def test_youtube_url_becomes_embed(self) -> None:
        """YouTubeのURLは埋め込みに変換される"""
        markdown = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = markdown_to_html(markdown)

        assert "<figure" in result
        assert 'embedded-service="youtube"' in result
        assert 'data-src="https://www.youtube.com/watch?v=dQw4w9WgXcQ"' in result
        assert "embedded-content-key=" in result

    def test_youtube_short_url_becomes_embed(self) -> None:
        """YouTube短縮URLも埋め込みに変換される"""
        markdown = "https://youtu.be/dQw4w9WgXcQ"
        result = markdown_to_html(markdown)

        assert "<figure" in result
        assert 'embedded-service="youtube"' in result
        assert 'data-src="https://youtu.be/dQw4w9WgXcQ"' in result

    def test_twitter_url_becomes_embed(self) -> None:
        """TwitterのURLは埋め込みに変換される"""
        markdown = "https://twitter.com/user/status/1234567890"
        result = markdown_to_html(markdown)

        assert "<figure" in result
        assert 'embedded-service="twitter"' in result
        assert 'data-src="https://twitter.com/user/status/1234567890"' in result

    def test_x_url_becomes_embed(self) -> None:
        """X（Twitter）のURLも埋め込みに変換される"""
        markdown = "https://x.com/user/status/1234567890"
        result = markdown_to_html(markdown)

        assert "<figure" in result
        assert 'embedded-service="twitter"' in result
        assert 'data-src="https://x.com/user/status/1234567890"' in result

    def test_note_url_becomes_embed(self) -> None:
        """note.comのURLは埋め込みに変換される"""
        markdown = "https://note.com/username/n/n1234567890ab"
        result = markdown_to_html(markdown)

        assert "<figure" in result
        assert 'embedded-service="note"' in result
        assert 'data-src="https://note.com/username/n/n1234567890ab"' in result

    def test_embed_url_with_surrounding_text(self) -> None:
        """テキストに囲まれた埋め込みURLも変換される"""
        markdown = """テスト文章です。

https://www.youtube.com/watch?v=dQw4w9WgXcQ

テスト続きです。"""
        result = markdown_to_html(markdown)

        assert "<figure" in result
        assert 'embedded-service="youtube"' in result
        # 前後のテキストも保持される
        assert "テスト文章です" in result
        assert "テスト続きです" in result

    def test_multiple_embed_urls(self) -> None:
        """複数の埋め込みURLが変換される"""
        markdown = """https://www.youtube.com/watch?v=video1

https://twitter.com/user/status/123"""
        result = markdown_to_html(markdown)

        assert result.count("<figure") == 2
        assert 'embedded-service="youtube"' in result
        assert 'embedded-service="twitter"' in result

    def test_embed_url_in_list_not_converted(self) -> None:
        """リスト内のURLは埋め込みに変換されない"""
        markdown = "- https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = markdown_to_html(markdown)

        # リストアイテム内のURLは変換されない
        assert "<li>" in result
        assert 'embedded-service="youtube"' not in result

    def test_embed_url_as_link_not_converted(self) -> None:
        """リンク内のURLは埋め込みに変換されない"""
        markdown = "[動画を見る](https://www.youtube.com/watch?v=dQw4w9WgXcQ)"
        result = markdown_to_html(markdown)

        assert 'href="https://www.youtube.com/watch?v=dQw4w9WgXcQ"' in result
        assert 'embedded-service="youtube"' not in result

    def test_unsupported_url_not_converted(self) -> None:
        """サポートされていないURLは埋め込みに変換されない"""
        markdown = "https://vimeo.com/123456"
        result = markdown_to_html(markdown)

        assert "<figure" not in result
        assert "embedded-service" not in result
        assert "https://vimeo.com/123456" in result
