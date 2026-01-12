"""Embed URL detection and HTML generation for note.com.

This module provides functions for detecting embed URLs (YouTube, Twitter, note.com)
and generating the required HTML structure for note.com embeds.

This is the single source of truth for embed URL patterns (DRY principle).
"""

from __future__ import annotations

import html
import re
import uuid

# Embed URL patterns (single source of truth - DRY principle)
# YouTube: youtube.com/watch?v=xxx or youtu.be/xxx
YOUTUBE_PATTERN = re.compile(r"^https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+$")

# Twitter/X: twitter.com/user/status/xxx or x.com/user/status/xxx
TWITTER_PATTERN = re.compile(r"^https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+$")

# note.com: note.com/user/n/xxx
NOTE_PATTERN = re.compile(r"^https?://note\.com/\w+/n/\w+$")


def get_embed_service(url: str) -> str | None:
    """Get embed service type from URL.

    Args:
        url: The URL to check.

    Returns:
        Service type ('youtube', 'twitter', 'note') or None if unsupported.
    """
    if YOUTUBE_PATTERN.match(url):
        return "youtube"
    if TWITTER_PATTERN.match(url):
        return "twitter"
    if NOTE_PATTERN.match(url):
        return "note"
    return None


def is_embed_url(url: str) -> bool:
    """Check if URL is a supported embed URL.

    Args:
        url: The URL to check.

    Returns:
        True if the URL is a supported embed URL, False otherwise.
    """
    return get_embed_service(url) is not None


def generate_embed_html(url: str, service: str | None = None) -> str:
    """Generate embed HTML for note.com.

    Creates a figure element with the required attributes for note.com
    to render the embed (iframe is rendered client-side by note.com frontend).

    Args:
        url: Original URL (YouTube, Twitter, note.com).
        service: Service type ('youtube', 'twitter', 'note').
                 If None, auto-detected from URL.

    Returns:
        HTML figure element string.

    Raises:
        ValueError: If URL is not a supported embed URL.
    """
    if service is None:
        service = get_embed_service(url)

    if service is None:
        raise ValueError(f"Unsupported embed URL: {url}")

    element_id = str(uuid.uuid4())
    embed_key = f"emb{uuid.uuid4().hex[:13]}"
    escaped_url = html.escape(url, quote=True)

    return (
        f'<figure name="{element_id}" id="{element_id}" '
        f'data-src="{escaped_url}" '
        f'embedded-service="{service}" '
        f'embedded-content-key="{embed_key}" '
        f'contenteditable="false"></figure>'
    )
