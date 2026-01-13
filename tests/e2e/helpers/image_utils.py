"""Image utilities for E2E testing.

Provides utilities for creating test images and validating image insertion
on note.com's preview pages.
"""

from __future__ import annotations

import struct
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.async_api import Error as PlaywrightError

if TYPE_CHECKING:
    from playwright.async_api import Page


def create_test_png(
    path: Path | None = None,
    width: int = 100,
    height: int = 100,
    color: tuple[int, int, int] = (255, 0, 0),
) -> Path:
    """Create a minimal valid PNG file for testing.

    Creates a simple solid-color PNG image without requiring PIL/Pillow.

    Args:
        path: Output path. If None, creates temp file.
        width: Image width in pixels
        height: Image height in pixels
        color: RGB color tuple (default: red)

    Returns:
        Path to the created PNG file
    """
    if path is None:
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        path = Path(temp_path)
        import os

        os.close(fd)

    # PNG signature
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk (image header)
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)

    # IDAT chunk (image data)
    # Create raw image data: for each row, filter byte (0) + RGB pixels
    raw_data = b""
    for _ in range(height):
        raw_data += b"\x00"  # Filter type: None
        for _ in range(width):
            raw_data += bytes(color)

    compressed = zlib.compress(raw_data, 9)
    idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
    idat_chunk = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)

    # IEND chunk (image end)
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    # Write PNG file
    with open(path, "wb") as f:
        f.write(signature + ihdr_chunk + idat_chunk + iend_chunk)

    return path


@dataclass
class ImageValidationResult:
    """Result of image validation.

    Attributes:
        success: Whether validation passed
        image_count: Number of images found
        has_caption: Whether caption was found (if expected)
        caption_text: Actual caption text found (if any)
        message: Detailed result message
    """

    success: bool
    image_count: int
    has_caption: bool
    caption_text: str | None
    message: str


class ImageValidator:
    """Validates image insertion on note.com preview pages.

    Provides methods to verify images are correctly inserted
    and displayed with optional captions.

    Attributes:
        page: Playwright Page instance
    """

    def __init__(self, page: Page) -> None:
        """Initialize validator with a Playwright page.

        Args:
            page: Playwright Page instance to validate
        """
        self.page = page

    async def validate_image_exists(self, expected_count: int = 1) -> ImageValidationResult:
        """Validate that expected number of images exist.

        Args:
            expected_count: Expected number of images

        Returns:
            ImageValidationResult with validation details
        """
        try:
            result = await self.page.evaluate(
                """
                (expectedCount) => {
                    // Look for images in various containers
                    const images = document.querySelectorAll(
                        'article img, .note-body img, figure img, [class*="body"] img'
                    );

                    const visibleImages = Array.from(images).filter(
                        img => img.offsetParent !== null && img.naturalHeight > 0
                    );

                    return {
                        count: visibleImages.length,
                        matches: visibleImages.length >= expectedCount
                    };
                }
                """,
                expected_count,
            )

            count = result.get("count", 0)
            matches = result.get("matches", False)

            if matches:
                return ImageValidationResult(
                    success=True,
                    image_count=count,
                    has_caption=False,
                    caption_text=None,
                    message=f"Found {count} image(s), expected >= {expected_count}",
                )
            return ImageValidationResult(
                success=False,
                image_count=count,
                has_caption=False,
                caption_text=None,
                message=f"Expected >= {expected_count} images, found {count}",
            )

        except PlaywrightError as e:
            return ImageValidationResult(
                success=False,
                image_count=0,
                has_caption=False,
                caption_text=None,
                message=f"Playwright error: {e}",
            )

    async def validate_image_with_caption(
        self,
        expected_caption: str,
    ) -> ImageValidationResult:
        """Validate that an image exists with the expected caption.

        Args:
            expected_caption: Expected caption text

        Returns:
            ImageValidationResult with validation details
        """
        try:
            result = await self.page.evaluate(
                """
                (expectedCaption) => {
                    // Find figures with images and figcaptions
                    const figures = document.querySelectorAll('figure');

                    for (const figure of figures) {
                        const img = figure.querySelector('img');
                        const caption = figure.querySelector('figcaption');

                        if (img && caption) {
                            const captionText = caption.textContent.trim();
                            if (captionText.includes(expectedCaption)) {
                                return {
                                    found: true,
                                    captionText: captionText,
                                    imageCount: figures.length
                                };
                            }
                        }
                    }

                    // If not found in figures, check for standalone images
                    // with nearby caption-like elements
                    const allImages = document.querySelectorAll('img');
                    for (const img of allImages) {
                        const parent = img.parentElement;
                        const sibling = img.nextElementSibling || parent?.nextElementSibling;
                        if (sibling && sibling.textContent?.includes(expectedCaption)) {
                            return {
                                found: true,
                                captionText: sibling.textContent.trim(),
                                imageCount: allImages.length
                            };
                        }
                    }

                    return {
                        found: false,
                        captionText: null,
                        imageCount: document.querySelectorAll('figure img, article img').length
                    };
                }
                """,
                expected_caption,
            )

            if result.get("found"):
                return ImageValidationResult(
                    success=True,
                    image_count=result.get("imageCount", 0),
                    has_caption=True,
                    caption_text=result.get("captionText"),
                    message=f"Found image with caption: {result.get('captionText')}",
                )

            return ImageValidationResult(
                success=False,
                image_count=result.get("imageCount", 0),
                has_caption=False,
                caption_text=None,
                message=f"Image with caption '{expected_caption}' not found",
            )

        except PlaywrightError as e:
            return ImageValidationResult(
                success=False,
                image_count=0,
                has_caption=False,
                caption_text=None,
                message=f"Playwright error: {e}",
            )

    async def validate_image_src_contains(
        self,
        expected_substring: str,
    ) -> ImageValidationResult:
        """Validate that at least one image src contains the expected substring.

        This is useful for verifying that local image paths have been
        replaced with CDN URLs (e.g., "assets.st-note.com").

        Args:
            expected_substring: Expected substring in image src

        Returns:
            ImageValidationResult with validation details
        """
        try:
            result = await self.page.evaluate(
                """
                (expectedSubstring) => {
                    const images = document.querySelectorAll(
                        'article img, .note-body img, figure img, [class*="body"] img'
                    );
                    const visibleImages = Array.from(images).filter(
                        img => img.offsetParent !== null
                    );
                    const matchingImages = visibleImages.filter(
                        img => img.src && img.src.includes(expectedSubstring)
                    );
                    return {
                        count: matchingImages.length,
                        totalImages: visibleImages.length,
                        matches: matchingImages.length > 0,
                        sampleSrc: visibleImages.length > 0 ? visibleImages[0].src : null
                    };
                }
                """,
                expected_substring,
            )

            count = result.get("count", 0)
            total = result.get("totalImages", 0)
            matches = result.get("matches", False)
            sample_src = result.get("sampleSrc")

            if matches:
                return ImageValidationResult(
                    success=True,
                    image_count=count,
                    has_caption=False,
                    caption_text=None,
                    message=f"Found {count}/{total} image(s) with '{expected_substring}' in src",
                )
            return ImageValidationResult(
                success=False,
                image_count=total,
                has_caption=False,
                caption_text=None,
                message=f"No images found with '{expected_substring}' in src. Sample src: {sample_src}",
            )

        except PlaywrightError as e:
            return ImageValidationResult(
                success=False,
                image_count=0,
                has_caption=False,
                caption_text=None,
                message=f"Playwright error: {e}",
            )
