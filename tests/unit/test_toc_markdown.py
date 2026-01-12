"""Unit tests for TOC markdown conversion."""

from note_mcp.utils.markdown_to_html import (
    _convert_toc_to_placeholder,
    _has_toc_placeholder,
    markdown_to_html,
)


class TestTocPatternDetection:
    """Tests for [TOC] pattern detection."""

    def test_detects_toc_at_start(self) -> None:
        """[TOC] at start of content is detected."""
        content = "[TOC]\n## Heading"
        assert _has_toc_placeholder(content) is True

    def test_detects_toc_in_middle(self) -> None:
        """[TOC] in middle of content is detected."""
        content = "# Title\n\n[TOC]\n\n## Section"
        assert _has_toc_placeholder(content) is True

    def test_no_toc_returns_false(self) -> None:
        """Content without [TOC] returns False."""
        content = "# Title\n## Section"
        assert _has_toc_placeholder(content) is False

    def test_partial_toc_not_detected(self) -> None:
        """Partial [TOC patterns are not detected."""
        content = "[TOC and more text"
        assert _has_toc_placeholder(content) is False

    def test_toc_must_be_alone_on_line(self) -> None:
        """[TOC] with other text on same line is not detected."""
        content = "[TOC] some text after"
        assert _has_toc_placeholder(content) is False

    def test_toc_with_text_before_not_detected(self) -> None:
        """[TOC] with text before on same line is not detected."""
        content = "Some text [TOC]"
        assert _has_toc_placeholder(content) is False


class TestTocPlaceholderConversion:
    """Tests for [TOC] to placeholder conversion."""

    def test_converts_single_toc(self) -> None:
        """Single [TOC] is converted to placeholder."""
        content = "# Title\n\n[TOC]\n\n## Section"
        result = _convert_toc_to_placeholder(content)
        assert "§§TOC§§" in result
        assert "[TOC]" not in result

    def test_only_first_toc_converted(self) -> None:
        """Only first [TOC] is converted, rest removed."""
        content = "[TOC]\n## A\n[TOC]\n## B"
        result = _convert_toc_to_placeholder(content)
        assert result.count("§§TOC§§") == 1
        assert "[TOC]" not in result

    def test_toc_in_code_block_preserved(self) -> None:
        """[TOC] inside code blocks is not processed."""
        content = "```\n[TOC]\n```\n\n[TOC]"
        result = _convert_toc_to_placeholder(content)
        assert "```\n[TOC]\n```" in result
        assert "§§TOC§§" in result

    def test_toc_in_inline_code_preserved(self) -> None:
        """[TOC] inside inline code is not processed."""
        content = "Use `[TOC]` marker\n\n[TOC]"
        result = _convert_toc_to_placeholder(content)
        assert "`[TOC]`" in result
        assert "§§TOC§§" in result

    def test_no_toc_unchanged(self) -> None:
        """Content without [TOC] is unchanged."""
        content = "# Title\n## Section"
        result = _convert_toc_to_placeholder(content)
        assert result == content

    def test_toc_at_document_start(self) -> None:
        """[TOC] at the very start of document is converted."""
        content = "[TOC]\n# Title"
        result = _convert_toc_to_placeholder(content)
        assert result.startswith("§§TOC§§")
        assert "[TOC]" not in result

    def test_toc_at_document_end(self) -> None:
        """[TOC] at the end of document is converted."""
        content = "# Title\n[TOC]"
        result = _convert_toc_to_placeholder(content)
        assert result.endswith("§§TOC§§")
        assert "[TOC]" not in result


class TestMarkdownToHtmlWithToc:
    """Tests for markdown_to_html with TOC support.

    Issue #117: TOC is now converted directly to <table-of-contents> element
    instead of placeholder, enabling API-based article creation without browser.
    """

    def test_toc_converted_to_custom_element(self) -> None:
        """[TOC] is converted to <table-of-contents> custom element."""
        content = "# Title\n\n[TOC]\n\n## Section\nText"
        result = markdown_to_html(content)
        assert "<table-of-contents" in result
        assert "</table-of-contents>" in result
        assert "[TOC]" not in result
        assert "§§TOC§§" not in result
        assert "<h1 " in result or "<h1>" in result
        assert "<h2 " in result or "<h2>" in result

    def test_toc_element_has_uuid_attributes(self) -> None:
        """TOC element has name and id attributes with UUID."""
        content = "# Title\n\n[TOC]\n\n## Section"
        result = markdown_to_html(content)
        assert '<table-of-contents name="' in result
        assert 'id="' in result
        # Verify it's a valid UUID format (8-4-4-4-12 hex chars)
        import re

        uuid_pattern = r'name="([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"'
        assert re.search(uuid_pattern, result) is not None

    def test_toc_with_other_features(self) -> None:
        """[TOC] works alongside other markdown features."""
        content = "# Title\n\n[TOC]\n\n**bold** and *italic*\n\n## Section"
        result = markdown_to_html(content)
        assert "<table-of-contents" in result
        assert "<strong>" in result
        assert "<em>" in result

    def test_empty_content_with_only_toc(self) -> None:
        """Content with only [TOC] is converted to custom element."""
        content = "[TOC]"
        result = markdown_to_html(content)
        assert "<table-of-contents" in result
        assert "</table-of-contents>" in result
        assert "§§TOC§§" not in result
