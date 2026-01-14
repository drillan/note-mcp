"""Embed URL detection and HTML generation for note.com.

This module provides functions for detecting embed URLs (YouTube, Twitter, note.com,
GitHub Gist, GitHub Repository, noteマネー, Zenn.dev, Google Slides) and generating
the required HTML structure for note.com embeds.

This is the single source of truth for embed URL patterns (DRY principle).

Issue #116: Server-registered embed keys are required for proper iframe rendering.
Random keys generated locally will not work - note.com frontend only renders embeds
with keys registered via the embed_by_external_api endpoint.

Issue #195: GitHub Gist embed support added. Gist URLs use the same
/v2/embed_by_external_api endpoint as YouTube and Twitter.

Issue #222: Zenn.dev article embed support added. Zenn URLs use
'external-article' service type via the same /v2/embed_by_external_api endpoint.

Issue #226: GitHub Repository embed support added. Repository URLs use
'githubRepository' service type via the same /v2/embed_by_external_api endpoint.
"""

from __future__ import annotations

import html
import logging
import re
import uuid
from typing import TYPE_CHECKING

from note_mcp.api.client import NoteAPIClient
from note_mcp.models import ErrorCode, NoteAPIError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from note_mcp.models import Session

# Embed URL patterns (single source of truth - DRY principle)
# YouTube: youtube.com/watch?v=xxx or youtu.be/xxx
YOUTUBE_PATTERN = re.compile(r"^https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+$")

# Twitter/X: twitter.com/user/status/xxx or x.com/user/status/xxx
TWITTER_PATTERN = re.compile(r"^https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+$")

# note.com: note.com/user/n/xxx
NOTE_PATTERN = re.compile(r"^https?://note\.com/\w+/n/\w+$")

# GitHub Gist: gist.github.com/user/gist_id (with optional trailing slash and file fragment)
GIST_PATTERN = re.compile(r"^https?://gist\.github\.com/[\w-]+/[\w]+/?(?:#[\w-]+)?$")

# noteマネー (stock chart): money.note.com/companies|us-companies|indices|investments/xxx
# Supports Japanese stocks, US stocks, indices, and investment trusts
MONEY_PATTERN = re.compile(r"^https?://money\.note\.com/(companies|us-companies|indices|investments)/[\w-]+/?$")

# Zenn.dev: zenn.dev/username/articles/article-slug
# Example: https://zenn.dev/zenn/articles/markdown-guide (Issue #222)
ZENN_PATTERN = re.compile(r"^https?://zenn\.dev/[\w-]+/articles/[\w-]+$")

# GitHub Repository: github.com/owner/repo (with optional trailing slash)
# Example: https://github.com/anthropics/claude-code (Issue #226)
# Note: This pattern must NOT match gist.github.com (handled by GIST_PATTERN)
# Note: This pattern must NOT match subpaths like /issues, /pull, /blob
GITHUB_REPO_PATTERN = re.compile(r"^https?://(?:www\.)?github\.com/[\w-]+/[\w.-]+/?$")

# Google Slides: docs.google.com/presentation/d/{id}/...
# Example: https://docs.google.com/presentation/d/1W543BSd-hHANrJOzCPyNf-r3x0s5s7ljc9xA7a7x960/edit (Issue #224)
# Supports: /edit, /pub, /view, /embed, or no suffix
# Supports: query parameters and fragment identifiers (#slide=id.xxx)
GOOGLE_SLIDES_PATTERN = re.compile(
    r"^https?://docs\.google\.com/presentation/d/[\w-]+(?:/[^?#]*)?(?:\?[^#]*)?(?:#.*)?$"
)


def get_embed_service(url: str) -> str | None:
    """Get embed service type from URL.

    Args:
        url: The URL to check.

    Returns:
        Service type ('youtube', 'twitter', 'note', 'gist', 'githubRepository',
        'googlepresentation', 'oembed', 'external-article') or None if unsupported.
    """
    if YOUTUBE_PATTERN.match(url):
        return "youtube"
    if TWITTER_PATTERN.match(url):
        return "twitter"
    if NOTE_PATTERN.match(url):
        return "note"
    # GIST_PATTERN is checked before GITHUB_REPO_PATTERN for clarity,
    # though the patterns are mutually exclusive (gist.github.com vs github.com)
    if GIST_PATTERN.match(url):
        return "gist"
    if GITHUB_REPO_PATTERN.match(url):
        return "githubRepository"
    if GOOGLE_SLIDES_PATTERN.match(url):
        return "googlepresentation"
    if MONEY_PATTERN.match(url):
        return "oembed"
    if ZENN_PATTERN.match(url):
        return "external-article"
    return None


def is_embed_url(url: str) -> bool:
    """Check if URL is a supported embed URL.

    Args:
        url: The URL to check.

    Returns:
        True if the URL is a supported embed URL, False otherwise.
    """
    return get_embed_service(url) is not None


def _build_embed_figure_html(
    url: str,
    embed_key: str,
    service: str,
) -> str:
    """Build the HTML figure element for an embed.

    Internal helper to generate the figure HTML structure.
    This is the single source of truth for embed figure HTML format (DRY).

    Args:
        url: Original URL (YouTube, Twitter, note.com, GitHub Gist, GitHub Repository,
             noteマネー, Zenn.dev, Google Slides).
        embed_key: Embed key (random for placeholder, server-registered for final).
        service: Service type ('youtube', 'twitter', 'note', 'gist', 'githubRepository',
                 'googlepresentation', 'oembed', 'external-article').

    Returns:
        HTML figure element string.
    """
    element_id = str(uuid.uuid4())
    escaped_url = html.escape(url, quote=True)

    return (
        f'<figure name="{element_id}" id="{element_id}" '
        f'data-src="{escaped_url}" '
        f'embedded-service="{service}" '
        f'embedded-content-key="{embed_key}" '
        f'contenteditable="false"></figure>'
    )


def generate_embed_html(url: str, service: str | None = None) -> str:
    """Generate embed HTML for note.com with a random key.

    Creates a figure element with the required attributes for note.com
    to render the embed (iframe is rendered client-side by note.com frontend).

    NOTE: This generates a random embed key which will NOT work for rendering.
    Use fetch_embed_key() to get a server-registered key, then use
    generate_embed_html_with_key() for proper rendering.

    This function is kept for backward compatibility and as a placeholder
    during markdown-to-html conversion (key is replaced later via API).

    Args:
        url: Original URL (YouTube, Twitter, note.com, GitHub Gist, GitHub Repository,
             noteマネー, Zenn.dev, Google Slides).
        service: Service type ('youtube', 'twitter', 'note', 'gist', 'githubRepository',
                 'googlepresentation', 'oembed', 'external-article'). If None, auto-detected from URL.

    Returns:
        HTML figure element string.

    Raises:
        ValueError: If URL is not a supported embed URL.
    """
    if service is None:
        service = get_embed_service(url)

    if service is None:
        raise ValueError(f"Unsupported embed URL: {url}")

    embed_key = f"emb{uuid.uuid4().hex[:13]}"
    return _build_embed_figure_html(url, embed_key, service)


async def _fetch_note_embed_key(
    session: Session,
    url: str,
    article_key: str,
) -> tuple[str, str]:
    """Fetch embed key for note.com article via /v1/embed endpoint.

    This internal function handles note.com article embeds which require
    a different API endpoint than external services (YouTube, Twitter).

    Issue #121: note.com articles must use POST /v1/embed instead of
    GET /v2/embed_by_external_api which returns 500 error.

    Args:
        session: Authenticated session with valid cookies.
        url: note.com article URL (e.g., https://note.com/user/n/xxx).
        article_key: Article key where embed will be inserted
                     (e.g., "n1234567890ab").

    Returns:
        Tuple of (embed_key, html_for_embed):
        - embed_key: Server-registered key (e.g., "emb0076d44f4f7f")
        - html_for_embed: HTML snippet for rendering the embed

    Raises:
        NoteAPIError: If API request fails or returns empty response.
    """
    payload = {
        "url": url,
        "embeddable_key": article_key,
        "embeddable_type": "Note",
    }

    async with NoteAPIClient(session) as client:
        response = await client.post("/v1/embed", json=payload)

    # Response structure: {"data": {"embedded_content": {"key": ..., "html_for_embed": ...}}}
    data = response.get("data", {})
    embedded_content = data.get("embedded_content", {})
    embed_key = embedded_content.get("key")
    html_for_embed = embedded_content.get("html_for_embed")

    # Article 6: Validate required fields - no implicit fallbacks
    if not embed_key or not html_for_embed:
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message="Failed to fetch note embed key: API response missing required field(s) 'key' or 'html_for_embed'",
            details={"url": url, "article_key": article_key, "response": response},
        )

    return embed_key, html_for_embed


async def fetch_embed_key(
    session: Session,
    url: str,
    article_key: str,
) -> tuple[str, str]:
    """Fetch server-registered embed key from note.com API.

    This function calls the appropriate API endpoint to register
    the embed URL with note.com's server and obtain a valid embed key.

    The server-registered key is required for note.com's frontend to
    render the iframe. Random keys generated locally will not work.

    Issue #121: Different endpoints are used for different services:
    - note.com articles: POST /v1/embed
    - YouTube/Twitter/GitHub Gist/GitHub Repository/noteマネー/Zenn.dev/Google Slides: GET /v2/embed_by_external_api

    Args:
        session: Authenticated session with valid cookies.
        url: Embed URL (YouTube, Twitter, note.com, GitHub Gist, GitHub Repository,
             noteマネー, Zenn.dev, Google Slides).
        article_key: Article key where the embed will be inserted
                     (e.g., "n1234567890ab").

    Returns:
        Tuple of (embed_key, html_for_embed):
        - embed_key: Server-registered key (e.g., "emb0076d44f4f7f")
        - html_for_embed: HTML snippet for rendering the embed

    Raises:
        ValueError: If URL is not a supported embed URL.
        NoteAPIError: If API request fails or returns empty response.
    """
    service = get_embed_service(url)
    if service is None:
        raise ValueError(f"Unsupported embed URL: {url}")

    # Issue #121: note.com articles use a different API endpoint
    if service == "note":
        return await _fetch_note_embed_key(session, url, article_key)

    # YouTube/Twitter/Gist/GitHub Repo/noteマネー/Zenn.dev/Google Slides: use /v2/embed_by_external_api endpoint
    params = {
        "url": url,
        "service": service,
        "embeddable_key": article_key,
        "embeddable_type": "Note",
    }

    async with NoteAPIClient(session) as client:
        response = await client.get("/v2/embed_by_external_api", params=params)

    # Validate response
    data = response.get("data", {})
    embed_key = data.get("key")
    html_for_embed = data.get("html_for_embed")

    if not embed_key or not html_for_embed:
        raise NoteAPIError(
            code=ErrorCode.API_ERROR,
            message=f"Failed to fetch {service} embed key: API returned empty response",
            details={"url": url, "article_key": article_key, "response": response},
        )

    return embed_key, html_for_embed


def generate_embed_html_with_key(
    url: str,
    embed_key: str,
    service: str | None = None,
) -> str:
    """Generate embed HTML with a server-registered key.

    Unlike generate_embed_html(), this uses a server-registered key
    which enables proper iframe rendering by note.com's frontend.

    Args:
        url: Original URL (YouTube, Twitter, note.com, GitHub Gist, GitHub Repository,
             noteマネー, Zenn.dev, Google Slides).
        embed_key: Server-registered embed key from fetch_embed_key().
        service: Service type ('youtube', 'twitter', 'note', 'gist', 'githubRepository',
                 'googlepresentation', 'oembed', 'external-article'). If None, auto-detected from URL.

    Returns:
        HTML figure element string with server-registered key.

    Raises:
        ValueError: If URL is not a supported embed URL.
    """
    if service is None:
        service = get_embed_service(url)

    if service is None:
        raise ValueError(f"Unsupported embed URL: {url}")

    return _build_embed_figure_html(url, embed_key, service)


# Pattern to find embed figure elements with their keys and URLs
# Uses non-greedy matching to handle any attribute order
_EMBED_FIGURE_PATTERN = re.compile(
    r"<figure\s+"
    r"(?=(?:[^>]*?data-src=\"([^\"]+)\"))"  # Lookahead for data-src
    r"(?=(?:[^>]*?embedded-content-key=\"([^\"]+)\"))"  # Lookahead for embedded-content-key
    r"[^>]*>",
    re.IGNORECASE,
)


async def resolve_embed_keys(
    session: Session,
    html_body: str,
    article_key: str,
) -> str:
    """Replace random embed keys with server-registered keys.

    Finds all <figure> elements with embedded-content-key attribute and
    replaces their keys with server-registered keys obtained via API.

    This function should be called after markdown_to_html() conversion
    and before saving the article body to note.com.

    Issue #121: API errors for individual embeds are logged and skipped,
    allowing other embeds to be processed successfully.

    Args:
        session: Authenticated session with valid cookies.
        html_body: HTML body containing figure elements with random embed keys.
        article_key: Article key where embeds will be inserted
                     (e.g., "n1234567890ab").

    Returns:
        HTML body with embed keys replaced by server-registered keys.
        Embeds that fail to resolve keep their original placeholder keys.
    """
    # Find all embed figures in the HTML
    matches = list(_EMBED_FIGURE_PATTERN.finditer(html_body))

    if not matches:
        # No embeds found, return unchanged
        return html_body

    result = html_body

    # Process each embed figure
    for match in matches:
        data_src = match.group(1)
        old_key = match.group(2)

        # Unescape the URL (it was escaped when generating HTML)
        url = html.unescape(data_src)

        # Skip if URL is not a supported embed URL
        if get_embed_service(url) is None:
            continue

        # Fetch server-registered key with error handling (Issue #121)
        try:
            server_key, _ = await fetch_embed_key(session, url, article_key)

            # Replace the old key with the server key
            result = result.replace(
                f'embedded-content-key="{old_key}"',
                f'embedded-content-key="{server_key}"',
            )
        except NoteAPIError as e:
            # Log warning and continue processing other embeds
            logger.warning("Embed key fetch failed for %s: %s", url, e.message)
            # Original placeholder key is preserved

    return result
