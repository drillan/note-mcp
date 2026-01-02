"""Unit tests for file_parser module.

Tests for parsing Markdown files with YAML frontmatter,
extracting titles from H1/H2 headings, and detecting local images.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestParsedArticle:
    """Tests for ParsedArticle dataclass."""

    def test_parsed_article_creation(self) -> None:
        """ParsedArticle should store all fields correctly."""
        from note_mcp.utils.file_parser import LocalImage, ParsedArticle

        local_images = [
            LocalImage(
                markdown_path="./images/test.png",
                absolute_path=Path("/path/to/images/test.png"),
                alt_text="Test image",
            )
        ]
        article = ParsedArticle(
            title="Test Title",
            body="Test body content",
            tags=["tag1", "tag2"],
            local_images=local_images,
            source_path=Path("/path/to/file.md"),
        )

        assert article.title == "Test Title"
        assert article.body == "Test body content"
        assert article.tags == ["tag1", "tag2"]
        assert len(article.local_images) == 1
        assert article.local_images[0].markdown_path == "./images/test.png"
        assert article.source_path == Path("/path/to/file.md")

    def test_parsed_article_defaults(self) -> None:
        """ParsedArticle should have sensible defaults."""
        from note_mcp.utils.file_parser import ParsedArticle

        article = ParsedArticle(title="Title", body="Body")

        assert article.tags == []
        assert article.local_images == []
        assert article.source_path is None


class TestLocalImage:
    """Tests for LocalImage dataclass."""

    def test_local_image_creation(self) -> None:
        """LocalImage should store all fields correctly."""
        from note_mcp.utils.file_parser import LocalImage

        image = LocalImage(
            markdown_path="./images/test.png",
            absolute_path=Path("/path/to/images/test.png"),
            alt_text="Test alt text",
        )

        assert image.markdown_path == "./images/test.png"
        assert image.absolute_path == Path("/path/to/images/test.png")
        assert image.alt_text == "Test alt text"

    def test_local_image_default_alt_text(self) -> None:
        """LocalImage should have empty alt_text by default."""
        from note_mcp.utils.file_parser import LocalImage

        image = LocalImage(
            markdown_path="./images/test.png",
            absolute_path=Path("/path/to/images/test.png"),
        )

        assert image.alt_text == ""


class TestParseMarkdownFile:
    """Tests for parse_markdown_file function."""

    def test_parse_with_yaml_frontmatter(self, tmp_path: Path) -> None:
        """Should extract title and tags from YAML frontmatter."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """---
title: YAML Title
tags:
  - tag1
  - tag2
---

This is the body content.

More body text here.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert result.title == "YAML Title"
        assert result.tags == ["tag1", "tag2"]
        assert "This is the body content." in result.body
        assert "More body text here." in result.body
        assert "---" not in result.body  # Frontmatter should be stripped
        assert "title:" not in result.body  # Frontmatter should be stripped

    def test_parse_with_h1_title(self, tmp_path: Path) -> None:
        """Should extract title from first H1 and remove it from body."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Article Title

This is the body content.

## Section 1

Some section content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert result.title == "Article Title"
        assert "# Article Title" not in result.body  # H1 should be removed
        assert "This is the body content." in result.body
        assert "## Section 1" in result.body  # H2 should remain

    def test_parse_with_h2_title_fallback(self, tmp_path: Path) -> None:
        """Should use first H2 as title if no H1 exists."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """## First Section Title

This is the body content.

### Subsection

Some content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert result.title == "First Section Title"
        # H2 used for title should be removed from body
        assert "## First Section Title" not in result.body
        assert "This is the body content." in result.body

    def test_parse_with_yaml_and_h1(self, tmp_path: Path) -> None:
        """YAML title takes precedence over H1, and H1 is NOT removed."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """---
title: YAML Title
---

# H1 Title

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert result.title == "YAML Title"
        # H1 should remain in body since title is from YAML
        assert "# H1 Title" in result.body
        assert "Body content." in result.body

    def test_parse_without_title_raises_error(self, tmp_path: Path) -> None:
        """Should raise ValueError if no title can be extracted."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """Just some body content without any title.

No headings here.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match="タイトルが見つかりません"):
            parse_markdown_file(md_file)

    def test_parse_nonexistent_file_raises_error(self) -> None:
        """Should raise FileNotFoundError for non-existent file."""
        from note_mcp.utils.file_parser import parse_markdown_file

        with pytest.raises(FileNotFoundError):
            parse_markdown_file(Path("/nonexistent/file.md"))

    def test_parse_with_string_path(self, tmp_path: Path) -> None:
        """Should accept string path as well as Path object."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Title

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(str(md_file))

        assert result.title == "Title"
        assert result.source_path == md_file


class TestLocalImageDetection:
    """Tests for detecting local images in Markdown content."""

    def test_detect_relative_image(self, tmp_path: Path) -> None:
        """Should detect relative image paths."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Title

![Alt text](./images/test.png)

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert len(result.local_images) == 1
        assert result.local_images[0].markdown_path == "./images/test.png"
        assert result.local_images[0].alt_text == "Alt text"
        assert result.local_images[0].absolute_path == tmp_path / "images" / "test.png"

    def test_detect_multiple_images(self, tmp_path: Path) -> None:
        """Should detect multiple local images."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Title

![First image](./images/first.png)

Some text here.

![Second image](../shared/second.jpg)
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert len(result.local_images) == 2
        assert result.local_images[0].markdown_path == "./images/first.png"
        assert result.local_images[1].markdown_path == "../shared/second.jpg"

    def test_ignore_url_images(self, tmp_path: Path) -> None:
        """Should ignore images with http/https URLs."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Title

![Online image](https://example.com/image.png)

![Another online](http://example.com/image.jpg)

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert len(result.local_images) == 0

    def test_ignore_data_uri_images(self, tmp_path: Path) -> None:
        """Should ignore data URI images."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Title

![Data image](data:image/png;base64,iVBORw0KGgo...)

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert len(result.local_images) == 0

    def test_mixed_local_and_url_images(self, tmp_path: Path) -> None:
        """Should only capture local images, ignoring URL images."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Title

![Local image](./images/local.png)

![URL image](https://example.com/remote.png)

![Another local](../other/image.jpg)
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert len(result.local_images) == 2
        assert result.local_images[0].markdown_path == "./images/local.png"
        assert result.local_images[1].markdown_path == "../other/image.jpg"

    def test_empty_alt_text(self, tmp_path: Path) -> None:
        """Should handle images with empty alt text."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Title

![](./images/no-alt.png)
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert len(result.local_images) == 1
        assert result.local_images[0].alt_text == ""


class TestYAMLFrontmatterEdgeCases:
    """Tests for edge cases in YAML frontmatter parsing."""

    def test_malformed_yaml_fallback_to_h1(self, tmp_path: Path) -> None:
        """Should fallback to H1 title when YAML is malformed."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """---
title: [unclosed bracket
invalid: yaml: here
---

# Fallback Title

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert result.title == "Fallback Title"
        assert result.tags == []

    def test_yaml_with_single_tag_as_string(self, tmp_path: Path) -> None:
        """Should handle tags as single string in YAML."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """---
title: Test Title
tags: single-tag
---

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert result.tags == ["single-tag"]

    def test_yaml_with_empty_title(self, tmp_path: Path) -> None:
        """Should fallback to H1 when YAML title is empty."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """---
title: ""
---

# Actual Title

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert result.title == "Actual Title"

    def test_yaml_without_ending_delimiter(self, tmp_path: Path) -> None:
        """Should handle YAML without ending ---."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """---
title: Missing End

# Another Title

Body content.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        # This should not parse as YAML (no ending ---), so fallback to H1
        result = parse_markdown_file(md_file)

        assert result.title == "Another Title"


class TestBodyNormalization:
    """Tests for body content normalization."""

    def test_strip_leading_trailing_whitespace(self, tmp_path: Path) -> None:
        """Body should not have excessive leading/trailing whitespace."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """---
title: Test Title
---


Body with leading blank lines.


"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        # Body should be stripped
        assert result.body == "Body with leading blank lines."

    def test_preserve_internal_blank_lines(self, tmp_path: Path) -> None:
        """Internal blank lines in body should be preserved."""
        from note_mcp.utils.file_parser import parse_markdown_file

        content = """# Title

First paragraph.

Second paragraph.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        result = parse_markdown_file(md_file)

        assert "First paragraph." in result.body
        assert "Second paragraph." in result.body
        # There should be a blank line between paragraphs
        assert "First paragraph.\n\nSecond paragraph." in result.body
