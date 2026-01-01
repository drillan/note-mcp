"""Helper modules for E2E testing.

This package provides utilities for validating Markdown-to-HTML
conversion on note.com's preview pages.

Modules:
    validation: ValidationResult dataclass and PreviewValidator class
"""

from .validation import PreviewValidator, ValidationResult

__all__ = ["PreviewValidator", "ValidationResult"]
