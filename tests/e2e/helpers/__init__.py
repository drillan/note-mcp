"""Helper modules for E2E testing.

This package provides utilities for validating Markdown-to-HTML
conversion on note.com's preview pages, and for stable ProseMirror
editor interactions.

Modules:
    validation: ValidationResult dataclass and PreviewValidator class
    prosemirror: ProseMirrorStabilizer for reliable editor interactions
    image_utils: Test image creation and image validation utilities
    typing_helpers: Keyboard input helpers for ProseMirror
"""

from .image_utils import ImageValidationResult, ImageValidator, create_test_png
from .prosemirror import ProseMirrorStabilizer
from .typing_helpers import save_and_open_preview, type_code_block, type_markdown_pattern
from .validation import PreviewValidator, ValidationResult

__all__ = [
    "create_test_png",
    "ImageValidationResult",
    "ImageValidator",
    "PreviewValidator",
    "ProseMirrorStabilizer",
    "ValidationResult",
    "save_and_open_preview",
    "type_code_block",
    "type_markdown_pattern",
]
