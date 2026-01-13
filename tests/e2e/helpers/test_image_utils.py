"""Unit tests for image_utils module."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Error as PlaywrightError

from tests.e2e.helpers.image_utils import ImageValidator


class TestImageValidator:
    """Tests for ImageValidator class."""

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        """Create a mock Playwright page."""
        page = MagicMock()
        page.evaluate = AsyncMock()
        return page

    @pytest.mark.asyncio
    async def test_validate_image_src_contains_success(
        self,
        mock_page: MagicMock,
    ) -> None:
        """Validation should succeed when image src contains expected substring."""
        mock_page.evaluate.return_value = {
            "count": 2,
            "totalImages": 3,
            "matches": True,
            "sampleSrc": "https://assets.st-note.com/image.png",
        }

        validator = ImageValidator(mock_page)
        result = await validator.validate_image_src_contains("assets.st-note.com")

        assert result.success is True
        assert result.image_count == 2
        assert "assets.st-note.com" in result.message

    @pytest.mark.asyncio
    async def test_validate_image_src_contains_failure_no_matching_images(
        self,
        mock_page: MagicMock,
    ) -> None:
        """Validation should fail when no images contain the expected substring.

        This is a negative case test to ensure the validator correctly reports
        failure when images exist but don't match the expected pattern.
        """
        mock_page.evaluate.return_value = {
            "count": 0,
            "totalImages": 2,
            "matches": False,
            "sampleSrc": "https://other-cdn.com/image.png",
        }

        validator = ImageValidator(mock_page)
        result = await validator.validate_image_src_contains("assets.st-note.com")

        assert result.success is False
        assert result.image_count == 2  # Total images found
        assert "No images found with 'assets.st-note.com' in src" in result.message
        assert "other-cdn.com" in result.message  # Shows sample src for debugging

    @pytest.mark.asyncio
    async def test_validate_image_src_contains_failure_no_images(
        self,
        mock_page: MagicMock,
    ) -> None:
        """Validation should fail when no images exist on the page."""
        mock_page.evaluate.return_value = {
            "count": 0,
            "totalImages": 0,
            "matches": False,
            "sampleSrc": None,
        }

        validator = ImageValidator(mock_page)
        result = await validator.validate_image_src_contains("assets.st-note.com")

        assert result.success is False
        assert result.image_count == 0
        assert "No images found" in result.message

    @pytest.mark.asyncio
    async def test_validate_image_src_contains_playwright_error(
        self,
        mock_page: MagicMock,
    ) -> None:
        """Validation should handle Playwright errors gracefully."""
        mock_page.evaluate.side_effect = PlaywrightError("Page navigation failed")

        validator = ImageValidator(mock_page)
        result = await validator.validate_image_src_contains("assets.st-note.com")

        assert result.success is False
        assert result.image_count == 0
        assert "Playwright error" in result.message
