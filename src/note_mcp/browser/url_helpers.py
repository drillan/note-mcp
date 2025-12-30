"""URL helper utilities for browser automation.

Provides common URL validation and manipulation functions.
"""


def validate_article_edit_url(current_url: str, article_id: str) -> bool:
    """Validate that the current URL is a valid article edit page.

    Args:
        current_url: The current browser URL
        article_id: The expected article ID

    Returns:
        True if the URL is a valid article edit page, False otherwise
    """
    valid_patterns = [f"/notes/{article_id}", f"/n/{article_id}", "editor.note.com"]
    return any(pattern in current_url for pattern in valid_patterns)
