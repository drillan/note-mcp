"""Pydantic data models for note-mcp.

This module defines all data models used throughout the note-mcp server,
including session management, article handling, and error types.
"""

from __future__ import annotations

import time
from enum import Enum

from pydantic import BaseModel


class Session(BaseModel):
    """User authentication session.

    Stores authentication state including cookies, user information,
    and session expiration.

    Attributes:
        cookies: note.com authentication cookies (note_gql_auth_token, _note_session_v5)
        user_id: note.com user ID
        username: note.com username (used in URL paths)
        expires_at: Session expiration timestamp (Unix timestamp), None if no expiry
        created_at: Session creation timestamp (Unix timestamp)
    """

    cookies: dict[str, str]
    user_id: str
    username: str
    expires_at: int | None = None
    created_at: int

    def is_expired(self) -> bool:
        """Check if the session has expired.

        Returns:
            True if session has expired, False otherwise.
            Returns False if expires_at is None (no expiry set).
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class ArticleStatus(str, Enum):
    """Article publication status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    PRIVATE = "private"


class ImageType(str, Enum):
    """Image upload type.

    Determines which note.com API endpoint to use for image upload.
    """

    EYECATCH = "eyecatch"  # Header/eyecatch image (見出し画像)
    BODY = "body"  # Inline/body image (記事内埋め込み画像)


class Article(BaseModel):
    """A note.com article.

    Represents an article with all its metadata as stored on note.com.

    Attributes:
        id: Article ID (note.com internal ID)
        key: Article key (used in URL path)
        title: Article title
        body: Article body content (HTML format)
        status: Publication status
        tags: List of hashtags (without # prefix)
        eyecatch_image_key: Eyecatch image key (if set)
        prev_access_key: Preview access key for draft articles
        created_at: Creation timestamp (ISO 8601)
        updated_at: Last update timestamp (ISO 8601)
        published_at: Publication timestamp (ISO 8601)
        url: Full article URL
    """

    id: str
    key: str
    title: str
    body: str
    status: ArticleStatus
    tags: list[str] = []
    eyecatch_image_key: str | None = None
    prev_access_key: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    published_at: str | None = None
    url: str | None = None


class ArticleInput(BaseModel):
    """Input data for creating or updating an article.

    Attributes:
        title: Article title
        body: Article body content (Markdown format)
        tags: List of hashtags (# prefix optional, will be normalized)
        eyecatch_image_path: Local path to eyecatch image (optional)
    """

    title: str
    body: str
    tags: list[str] = []
    eyecatch_image_path: str | None = None


class Image(BaseModel):
    """An uploaded image.

    Attributes:
        key: note.com image key
        url: Image URL on note.com
        original_path: Original local file path
        size_bytes: File size in bytes (optional)
        uploaded_at: Upload timestamp (Unix timestamp)
        image_type: Type of image (eyecatch or body)
    """

    key: str
    url: str
    original_path: str
    size_bytes: int | None = None
    uploaded_at: int
    image_type: ImageType = ImageType.EYECATCH


class Tag(BaseModel):
    """A hashtag for articles.

    Attributes:
        name: Tag name (without # prefix)
    """

    name: str

    @classmethod
    def normalize(cls, tag: str) -> str:
        """Normalize a tag by removing leading # characters.

        Args:
            tag: Tag string, possibly with # prefix

        Returns:
            Tag string without # prefix
        """
        return tag.lstrip("#")


class ArticleListResult(BaseModel):
    """Result of listing articles.

    Attributes:
        articles: List of articles
        total: Total number of articles matching the query
        page: Current page number (1-indexed)
        has_more: Whether there are more articles to fetch
    """

    articles: list[Article]
    total: int
    page: int
    has_more: bool


class BrowserArticleResult(BaseModel):
    """Result of browser-based article creation/update.

    Includes the article and optional TOC/alignment/embed/image insertion results for user notification.

    Attributes:
        article: The created/updated article
        toc_inserted: True if TOC was successfully inserted, False if failed, None if not attempted
        toc_error: Error message if TOC insertion failed
        alignments_applied: Number of text alignments successfully applied, None if not attempted
        alignment_error: Error message if text alignment application failed
        embeds_inserted: Number of embeds successfully inserted, None if not attempted
        embed_error: Error message if embed insertion failed
        images_inserted: Number of images successfully inserted, None if not attempted
        image_error: Error message if image insertion failed
        debug_info: Debug information for troubleshooting (temporary)
    """

    article: Article
    toc_inserted: bool | None = None
    toc_error: str | None = None
    alignments_applied: int | None = None
    alignment_error: str | None = None
    embeds_inserted: int | None = None
    embed_error: str | None = None
    images_inserted: int | None = None
    image_error: str | None = None
    debug_info: str | None = None


class ErrorCode(str, Enum):
    """Error codes for note-mcp API errors."""

    NOT_AUTHENTICATED = "not_authenticated"
    SESSION_EXPIRED = "session_expired"
    ARTICLE_NOT_FOUND = "article_not_found"
    RATE_LIMITED = "rate_limited"
    API_ERROR = "api_error"
    UPLOAD_FAILED = "upload_failed"
    INVALID_INPUT = "invalid_input"


class NoteAPIError(Exception):
    """Exception for note.com API errors.

    Attributes:
        code: Error code
        message: Human-readable error message
        details: Additional error details
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            code: Error code from ErrorCode enum
            message: Human-readable error message
            details: Additional context (e.g., status code, response body)
        """
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class LoginError(Exception):
    """ログイン処理でのエラー。

    reCAPTCHA検出、2FA要求、認証情報エラー時に送出される。
    手動ログインへのフォールバックは行わず、明確なエラーで通知する。

    Attributes:
        code: エラーコード（RECAPTCHA_DETECTED, TWO_FACTOR_REQUIRED,
              INVALID_CREDENTIALS, LOGIN_TIMEOUT）
        message: エラーメッセージ
        resolution: 推奨される対処法
    """

    def __init__(
        self,
        code: str,
        message: str,
        resolution: str | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            code: エラーコード
            message: エラーメッセージ
            resolution: 推奨される対処法（オプション）
        """
        self.code = code
        self.message = message
        self.resolution = resolution
        super().__init__(message)


def from_api_response(data: dict[str, object]) -> Article:
    """Create an Article from note.com API response.

    Args:
        data: Raw API response dictionary

    Returns:
        Article instance
    """
    # Extract hashtag names from the hashtags array
    hashtags = data.get("hashtags", [])
    tags: list[str] = []
    if isinstance(hashtags, list):
        for ht in hashtags:
            if isinstance(ht, dict):
                hashtag_obj = ht.get("hashtag", {})
                if isinstance(hashtag_obj, dict):
                    name = hashtag_obj.get("name", "")
                    if name:
                        tags.append(str(name))

    # Map API field names to our model
    status_str = data.get("status", "draft")
    if not isinstance(status_str, str) or not status_str:
        status_str = "draft"

    # Extract title: use "name" field, fallback to "noteDraft.name" for drafts
    title = data.get("name")
    if not title:
        note_draft = data.get("noteDraft")
        if isinstance(note_draft, dict):
            title = note_draft.get("name")
    title_str = str(title) if title else ""

    return Article(
        id=str(data.get("id", "")),
        key=str(data.get("key", "")),
        title=title_str,
        body=str(data.get("body", "")),
        status=ArticleStatus(status_str),
        tags=tags,
        eyecatch_image_key=str(data.get("eyecatch_image_key")) if data.get("eyecatch_image_key") else None,
        prev_access_key=str(data.get("prev_access_key")) if data.get("prev_access_key") else None,
        created_at=str(data.get("created_at")) if data.get("created_at") else None,
        updated_at=str(data.get("updated_at")) if data.get("updated_at") else None,
        published_at=str(data.get("publish_at")) if data.get("publish_at") else None,
        url=str(data.get("noteUrl")) if data.get("noteUrl") else None,
    )


def to_api_request(article_input: ArticleInput, html_body: str) -> dict[str, object]:
    """Convert ArticleInput to note.com API request format.

    Args:
        article_input: Input data from user
        html_body: HTML-converted body content

    Returns:
        Dictionary suitable for note.com API request
    """
    return {
        "name": article_input.title,
        "body": html_body,
        "status": "draft",
    }
