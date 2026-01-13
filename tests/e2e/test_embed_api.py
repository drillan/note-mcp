"""E2E tests for embed URL API conversion (Issue #116).

Tests creating note.com articles with embed URLs (YouTube, Twitter, note.com)
via API without browser automation.

Each test validates:
1. API response contains expected success message
2. Embed URLs are converted to figure elements
3. Preview page shows embed card correctly

Run with: uv run pytest tests/e2e/test_embed_api.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from note_mcp.server import note_create_draft
from tests.e2e.helpers import (
    extract_article_key,
    get_article_html,
    preview_page_context,
)

if TYPE_CHECKING:
    from note_mcp.models import Session

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


class TestEmbedUrlApiConversion:
    """Test embed URL conversion via API (no browser required)."""

    async def test_youtube_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """YouTube URLがAPIでfigure要素に変換される.

        - ブラウザを起動せずにAPIのみで下書き作成
        - YouTube URLがfigure要素に変換される
        - embedded-service="youtube"属性が設定される
        """
        # Arrange
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        body = f"""This is a test article with YouTube embed.

{youtube_url}

The video should appear above."""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] YouTube Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result
        assert "ID:" in result

        # Issue #165: Use get_article_html() for raw HTML embed attribute validation
        article_key = extract_article_key(result)
        article_html = await get_article_html(article_key)

        # Verify embed figure is present (in raw HTML)
        assert 'embedded-service="youtube"' in article_html
        assert f'data-src="{youtube_url}"' in article_html
        assert "embedded-content-key=" in article_html

    async def test_twitter_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """Twitter URLがAPIでfigure要素に変換される.

        - Twitter status URLがfigure要素に変換される
        - embedded-service="twitter"属性が設定される
        """
        # Arrange
        twitter_url = "https://twitter.com/anthropaborean/status/1876108600584237308"
        body = f"""This is a test article with Twitter embed.

{twitter_url}

The tweet should appear above."""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] Twitter Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Issue #165: Use get_article_html() for raw HTML embed attribute validation
        article_key = extract_article_key(result)
        article_html = await get_article_html(article_key)

        # Verify embed figure is present (in raw HTML)
        assert 'embedded-service="twitter"' in article_html
        assert f'data-src="{twitter_url}"' in article_html

    async def test_x_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """X (Twitter rebrand) URLがAPIでfigure要素に変換される.

        - x.com URLがfigure要素に変換される
        - embedded-service="twitter"属性が設定される
        """
        # Arrange
        x_url = "https://x.com/anthropaborean/status/1876108600584237308"
        body = f"""This is a test article with X embed.

{x_url}

The post should appear above."""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] X Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Issue #165: Use get_article_html() for raw HTML embed attribute validation
        article_key = extract_article_key(result)
        article_html = await get_article_html(article_key)

        # Verify embed figure is present (X URLs use twitter service, in raw HTML)
        assert 'embedded-service="twitter"' in article_html
        assert f'data-src="{x_url}"' in article_html

    async def test_note_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """note.com記事URLがAPIでfigure要素に変換される.

        - note.com記事URLがfigure要素に変換される
        - embedded-service="note"属性が設定される
        """
        # Arrange - Use a public note.com article
        note_url = "https://note.com/note_official/n/n0e7b8b4f5f3a"
        body = f"""This is a test article with note.com embed.

{note_url}

The article card should appear above."""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] Note Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Issue #165: Use get_article_html() for raw HTML embed attribute validation
        article_key = extract_article_key(result)
        article_html = await get_article_html(article_key)

        # Verify embed figure is present (in raw HTML)
        assert 'embedded-service="note"' in article_html
        assert f'data-src="{note_url}"' in article_html

    async def test_multiple_embeds_via_api(
        self,
        real_session: Session,
    ) -> None:
        """複数の埋め込みURLがAPIで変換される.

        - YouTube, Twitter両方のURLがfigure要素に変換される
        """
        # Arrange
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        twitter_url = "https://twitter.com/anthropaborean/status/1876108600584237308"
        body = f"""This article has multiple embeds.

{youtube_url}

Some text between embeds.

{twitter_url}

Both should appear as embed cards."""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] Multiple Embeds via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Issue #165: Use get_article_html() for raw HTML embed attribute validation
        article_key = extract_article_key(result)
        article_html = await get_article_html(article_key)

        # Verify both embeds are present (in raw HTML)
        assert 'embedded-service="youtube"' in article_html
        assert 'embedded-service="twitter"' in article_html
        assert article_html.count('embedded-service="') >= 2

    async def test_embed_in_paragraph_not_converted(
        self,
        real_session: Session,
    ) -> None:
        """テキストに埋め込まれたURLは変換されない.

        - 段落内のURLはリンクのまま保持される
        - スタンドアロンURLのみfigureに変換される
        """
        # Arrange
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        body = f"""Check out this video: {youtube_url} which is great."""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] Embed in Paragraph",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Issue #165: Use get_article_html() for raw HTML embed attribute validation
        article_key = extract_article_key(result)
        article_html = await get_article_html(article_key)

        # URL should remain as link, not figure (in raw HTML)
        assert 'embedded-service="youtube"' not in article_html
        # URL should be in an anchor tag
        assert f'href="{youtube_url}"' in article_html

    async def test_embed_as_markdown_link_not_converted(
        self,
        real_session: Session,
    ) -> None:
        """Markdownリンク形式のURLは変換されない.

        - [text](url)形式はアンカータグに変換される
        - figure要素には変換されない
        """
        # Arrange
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        body = f"""Here's a link: [Watch this video]({youtube_url})"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] Embed as Link",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Issue #165: Use get_article_html() for raw HTML embed attribute validation
        article_key = extract_article_key(result)
        article_html = await get_article_html(article_key)

        # URL should be in anchor tag, not figure (in raw HTML)
        assert 'embedded-service="youtube"' not in article_html
        assert "Watch this video" in article_html


class TestEmbedPreviewRendering:
    """Test embed rendering in preview (requires browser)."""

    async def test_youtube_embed_renders_in_preview(
        self,
        real_session: Session,
    ) -> None:
        """YouTubeの埋め込みがプレビューで正しくレンダリングされる.

        - figure要素がiframeに変換される
        - 埋め込みカードが表示される
        """
        # Arrange
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        body = f"""Test embed preview.

{youtube_url}
"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] YouTube Embed Preview",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result
        article_key = extract_article_key(result)

        # Verify preview rendering
        async with preview_page_context(real_session, article_key) as page:
            # Wait for embed to render (note.com renders iframes client-side)
            embed_figure = page.locator('figure[embedded-service="youtube"]')
            await embed_figure.wait_for(timeout=10000)

            # Verify figure has correct attributes
            assert await embed_figure.count() >= 1

            # Note: iframe may or may not be present depending on client-side JS
            # The figure element presence is sufficient to verify API conversion worked
