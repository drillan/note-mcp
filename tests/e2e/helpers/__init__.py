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
from .retry import with_retry
from .typing_helpers import (
    insert_toc_placeholder,
    save_and_open_preview,
    type_alignment,
    type_blockquote,
    type_code_block,
    type_horizontal_line,
    type_link,
    type_markdown_pattern,
    type_ordered_list,
    type_unordered_list,
)
from .validation import PreviewValidator, ValidationResult

__all__ = [
    "create_test_png",
    "ImageValidationResult",
    "ImageValidator",
    "insert_toc_placeholder",
    "PreviewValidator",
    "ProseMirrorStabilizer",
    "ValidationResult",
    "save_and_open_preview",
    "type_alignment",
    "type_blockquote",
    "type_code_block",
    "type_horizontal_line",
    "type_link",
    "type_markdown_pattern",
    "type_ordered_list",
    "type_unordered_list",
    "with_retry",
]
