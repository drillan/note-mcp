"""Helper modules for E2E testing.

This package provides utilities for validating Markdown-to-HTML
conversion on note.com's preview pages, and for stable ProseMirror
editor interactions.

Modules:
    article_helpers: Extract article metadata from MCP tool results
    preview_helpers: Preview page navigation utilities
    validation: ValidationResult dataclass and PreviewValidator class
    prosemirror: ProseMirrorStabilizer for reliable editor interactions
    image_utils: Test image creation and image validation utilities
    typing_helpers: Keyboard input helpers for ProseMirror
"""

from .article_helpers import extract_article_id, extract_article_key
from .constants import (
    DEFAULT_ELEMENT_WAIT_TIMEOUT_MS,
    DEFAULT_NAVIGATION_TIMEOUT_MS,
    LOGIN_TIMEOUT_SECONDS,
    NOTE_EDITOR_URL,
)
from .image_utils import ImageValidationResult, ImageValidator, create_test_png
from .preview_helpers import open_preview_for_article_key, preview_page_context
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
    "DEFAULT_ELEMENT_WAIT_TIMEOUT_MS",
    "DEFAULT_NAVIGATION_TIMEOUT_MS",
    "extract_article_id",
    "extract_article_key",
    "ImageValidationResult",
    "ImageValidator",
    "insert_toc_placeholder",
    "LOGIN_TIMEOUT_SECONDS",
    "NOTE_EDITOR_URL",
    "open_preview_for_article_key",
    "preview_page_context",
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
