"""Helper modules for E2E testing.

This package provides utilities for validating Markdown-to-HTML
conversion on note.com's preview pages, and for stable ProseMirror
editor interactions.

Modules:
    validation: ValidationResult dataclass and PreviewValidator class
    prosemirror: ProseMirrorStabilizer for reliable editor interactions
    image_utils: Test image creation and image validation utilities
"""

from .image_utils import ImageValidationResult, ImageValidator, create_test_png
from .prosemirror import ProseMirrorStabilizer
from .validation import PreviewValidator, ValidationResult

__all__ = [
    "create_test_png",
    "ImageValidationResult",
    "ImageValidator",
    "PreviewValidator",
    "ProseMirrorStabilizer",
    "ValidationResult",
]
