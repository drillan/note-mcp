"""Unit tests for image_helpers module.

Tests the image placeholder processing for note.com editor.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from note_mcp.browser.image_helpers import (
    _IMAGE_PLACEHOLDER_END,
    _IMAGE_PLACEHOLDER_SEPARATOR,
    _IMAGE_PLACEHOLDER_START,
    _get_image_extension,
    has_image_placeholders,
)


class TestImagePlaceholderConstants:
    """Test placeholder constant values."""

    def test_placeholder_start_is_unique(self) -> None:
        """Placeholder start marker should be unique and unlikely in normal text."""
        assert _IMAGE_PLACEHOLDER_START == "§§IMAGE:"
        assert "§§" in _IMAGE_PLACEHOLDER_START

    def test_placeholder_separator_is_pipe(self) -> None:
        """Placeholder separator should be double pipe."""
        assert _IMAGE_PLACEHOLDER_SEPARATOR == "||"

    def test_placeholder_end_is_unique(self) -> None:
        """Placeholder end marker should match start pattern."""
        assert _IMAGE_PLACEHOLDER_END == "§§"


class TestGetImageExtension:
    """Test _get_image_extension function."""

    def test_extracts_jpg_from_url(self) -> None:
        """Should extract .jpg extension from URL."""
        result = _get_image_extension("https://example.com/image.jpg", "")
        assert result == ".jpg"

    def test_extracts_jpeg_from_url(self) -> None:
        """Should extract .jpeg extension from URL."""
        result = _get_image_extension("https://example.com/photo.jpeg", "")
        assert result == ".jpeg"

    def test_extracts_png_from_url(self) -> None:
        """Should extract .png extension from URL."""
        result = _get_image_extension("https://example.com/logo.png", "")
        assert result == ".png"

    def test_extracts_gif_from_url(self) -> None:
        """Should extract .gif extension from URL."""
        result = _get_image_extension("https://example.com/anim.gif", "")
        assert result == ".gif"

    def test_extracts_webp_from_url(self) -> None:
        """Should extract .webp extension from URL."""
        result = _get_image_extension("https://example.com/modern.webp", "")
        assert result == ".webp"

    def test_ignores_query_string(self) -> None:
        """Should extract extension ignoring query string."""
        result = _get_image_extension("https://example.com/image.png?size=large", "")
        assert result == ".png"

    def test_uses_content_type_jpeg(self) -> None:
        """Should use content-type when URL has no extension."""
        result = _get_image_extension("https://example.com/image", "image/jpeg")
        assert result == ".jpg"

    def test_uses_content_type_png(self) -> None:
        """Should use content-type when URL has no extension."""
        result = _get_image_extension("https://example.com/image", "image/png")
        assert result == ".png"

    def test_uses_content_type_gif(self) -> None:
        """Should use content-type when URL has no extension."""
        result = _get_image_extension("https://example.com/image", "image/gif")
        assert result == ".gif"

    def test_uses_content_type_webp(self) -> None:
        """Should use content-type when URL has no extension."""
        result = _get_image_extension("https://example.com/image", "image/webp")
        assert result == ".webp"

    def test_defaults_to_jpg(self) -> None:
        """Should default to .jpg when no extension found."""
        result = _get_image_extension("https://example.com/image", "application/octet-stream")
        assert result == ".jpg"

    def test_case_insensitive_url(self) -> None:
        """Should handle uppercase extensions in URL."""
        result = _get_image_extension("https://example.com/IMAGE.PNG", "")
        assert result == ".png"

    def test_case_insensitive_content_type(self) -> None:
        """Should handle uppercase content-type."""
        result = _get_image_extension("https://example.com/image", "IMAGE/PNG")
        assert result == ".png"


class TestHasImagePlaceholders:
    """Test has_image_placeholders function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_placeholder_exists(self) -> None:
        """Should return True when image placeholder exists in editor."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.text_content = AsyncMock(
            return_value="Some text §§IMAGE:alt||https://example.com/img.jpg§§ more text"
        )
        mock_page.locator.return_value = mock_locator

        result = await has_image_placeholders(mock_page)

        assert result is True
        mock_page.locator.assert_called_once_with(".ProseMirror")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_placeholder(self) -> None:
        """Should return False when no image placeholder exists."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.text_content = AsyncMock(return_value="Just normal text without placeholders")
        mock_page.locator.return_value = mock_locator

        result = await has_image_placeholders(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_text_is_none(self) -> None:
        """Should return False when editor text is None."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.text_content = AsyncMock(return_value=None)
        mock_page.locator.return_value = mock_locator

        result = await has_image_placeholders(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_partial_marker(self) -> None:
        """Should return False for incomplete placeholder marker."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.text_content = AsyncMock(return_value="Text with §§ but not image placeholder")
        mock_page.locator.return_value = mock_locator

        result = await has_image_placeholders(mock_page)

        assert result is False


class TestImagePlaceholderFormat:
    """Test the image placeholder format matches typing_helpers.py."""

    def test_placeholder_format(self) -> None:
        """Placeholder should follow §§IMAGE:alt||url§§ format."""
        alt_text = "test image"
        image_url = "https://example.com/test.jpg"

        placeholder = (
            f"{_IMAGE_PLACEHOLDER_START}{alt_text}{_IMAGE_PLACEHOLDER_SEPARATOR}{image_url}{_IMAGE_PLACEHOLDER_END}"
        )

        assert placeholder == "§§IMAGE:test image||https://example.com/test.jpg§§"

    def test_placeholder_format_with_empty_alt(self) -> None:
        """Placeholder should work with empty alt text."""
        alt_text = ""
        image_url = "https://example.com/test.jpg"

        placeholder = (
            f"{_IMAGE_PLACEHOLDER_START}{alt_text}{_IMAGE_PLACEHOLDER_SEPARATOR}{image_url}{_IMAGE_PLACEHOLDER_END}"
        )

        assert placeholder == "§§IMAGE:||https://example.com/test.jpg§§"

    def test_placeholder_format_with_local_path(self) -> None:
        """Placeholder should work with local file paths."""
        alt_text = "local image"
        image_path = "/path/to/image.png"

        placeholder = (
            f"{_IMAGE_PLACEHOLDER_START}{alt_text}{_IMAGE_PLACEHOLDER_SEPARATOR}{image_path}{_IMAGE_PLACEHOLDER_END}"
        )

        assert placeholder == "§§IMAGE:local image||/path/to/image.png§§"
