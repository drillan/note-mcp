"""Helper modules for E2E testing.

This package provides utilities for validating Markdown-to-HTML
conversion on note.com's preview pages.

Modules:
    validation: ValidationResult dataclass and PreviewValidator class
    typing_helpers: Keyboard input helpers for ProseMirror
"""

from .typing_helpers import save_and_open_preview, type_code_block, type_markdown_pattern
from .validation import PreviewValidator, ValidationResult

__all__ = [
    "PreviewValidator",
    "ValidationResult",
    "save_and_open_preview",
    "type_code_block",
    "type_markdown_pattern",
]
