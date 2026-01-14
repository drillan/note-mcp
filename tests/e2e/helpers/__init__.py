"""Helper modules for E2E testing.

This package provides utilities for validating Markdown-to-HTML
conversion on note.com's preview pages.

Modules:
    article_helpers: Extract article metadata from MCP tool results
    preview_helpers: Preview page navigation utilities
    validation: ValidationResult dataclass and PreviewValidator class
    image_utils: Test image creation and image validation utilities
"""

from .article_helpers import extract_article_id, extract_article_key, get_article_html
from .cleanup import delete_draft_with_retry
from .constants import (
    DEFAULT_ELEMENT_WAIT_TIMEOUT_MS,
    DEFAULT_NAVIGATION_TIMEOUT_MS,
    LOGIN_TIMEOUT_SECONDS,
    NOTE_EDITOR_URL,
)
from .html_validator import HtmlValidator
from .image_utils import ImageValidationResult, ImageValidator, create_test_png
from .preview_helpers import open_preview_for_article_key, preview_page_context
from .retry import with_retry
from .validation import PreviewValidator, ValidationResult

__all__ = [
    "create_test_png",
    "DEFAULT_ELEMENT_WAIT_TIMEOUT_MS",
    "DEFAULT_NAVIGATION_TIMEOUT_MS",
    "delete_draft_with_retry",
    "extract_article_id",
    "extract_article_key",
    "get_article_html",
    "HtmlValidator",
    "ImageValidationResult",
    "ImageValidator",
    "LOGIN_TIMEOUT_SECONDS",
    "NOTE_EDITOR_URL",
    "open_preview_for_article_key",
    "preview_page_context",
    "PreviewValidator",
    "ValidationResult",
    "with_retry",
]
