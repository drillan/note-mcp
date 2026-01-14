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
    delete_draft_with_retry,
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
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present (in raw HTML)
            assert 'embedded-service="youtube"' in article_html
            assert f'data-src="{youtube_url}"' in article_html
            assert "embedded-content-key=" in article_html
        finally:
            # Issue #210: Clean up created article
            await delete_draft_with_retry(real_session, article_key)

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
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present (in raw HTML)
            assert 'embedded-service="twitter"' in article_html
            assert f'data-src="{twitter_url}"' in article_html
        finally:
            # Issue #210: Clean up created article
            await delete_draft_with_retry(real_session, article_key)

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
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present (X URLs use twitter service, in raw HTML)
            assert 'embedded-service="twitter"' in article_html
            assert f'data-src="{x_url}"' in article_html
        finally:
            # Issue #210: Clean up created article
            await delete_draft_with_retry(real_session, article_key)

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
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present (in raw HTML)
            assert 'embedded-service="note"' in article_html
            assert f'data-src="{note_url}"' in article_html
        finally:
            # Issue #210: Clean up created article
            await delete_draft_with_retry(real_session, article_key)

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
        try:
            article_html = await get_article_html(article_key)

            # Verify both embeds are present (in raw HTML)
            assert 'embedded-service="youtube"' in article_html
            assert 'embedded-service="twitter"' in article_html
            assert article_html.count('embedded-service="') >= 2
        finally:
            # Issue #210: Clean up created article
            await delete_draft_with_retry(real_session, article_key)

    async def test_embed_in_paragraph_not_converted(
        self,
        real_session: Session,
    ) -> None:
        """テキストに埋め込まれたURLは変換されない.

        - 段落内のURLはプレーンテキストとして保持される
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
        try:
            article_html = await get_article_html(article_key)

            # Issue #171: URL in paragraph should remain as plain text (not converted)
            # URL should remain as plain text, not figure (in raw HTML)
            assert 'embedded-service="youtube"' not in article_html
            # URL should be in the paragraph as plain text (not converted to anchor)
            assert youtube_url in article_html
            # Explicitly verify NOT in anchor tag
            assert f'href="{youtube_url}"' not in article_html
        finally:
            # Issue #210: Clean up created article
            await delete_draft_with_retry(real_session, article_key)

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
        try:
            article_html = await get_article_html(article_key)

            # URL should be in anchor tag, not figure (in raw HTML)
            assert 'embedded-service="youtube"' not in article_html
            assert "Watch this video" in article_html
        finally:
            # Issue #210: Clean up created article
            await delete_draft_with_retry(real_session, article_key)


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
        # Issue #210: Use cleanup_article=True to delete draft after test
        async with preview_page_context(real_session, article_key, cleanup_article=True) as page:
            # Wait for embed to render (note.com renders iframes client-side)
            embed_figure = page.locator('figure[embedded-service="youtube"]')
            await embed_figure.wait_for(timeout=10000)

            # Verify figure has correct attributes
            assert await embed_figure.count() >= 1

            # Note: iframe may or may not be present depending on client-side JS
            # The figure element presence is sufficient to verify API conversion worked


class TestMoneyEmbedApiConversion:
    """Test noteマネー (stock chart) embed conversion via API."""

    async def test_money_companies_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """noteマネー日本株URLがAPIでfigure要素に変換される.

        - ブラウザを起動せずにAPIのみで下書き作成
        - noteマネーURLがfigure要素に変換される
        - embedded-service="money"属性が設定される
        """
        # Arrange - Use note社 (証券コード: 5243) as test URL
        money_url = "https://money.note.com/companies/5243"
        body = f"""株価チャート埋め込みテスト

{money_url}

上記にnote社の株価チャートが表示されます。"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] noteマネー Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result
        assert "ID:" in result

        # Verify embed figure is present in raw HTML
        article_key = extract_article_key(result)
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present (in raw HTML)
            assert 'embedded-service="money"' in article_html
            assert f'data-src="{money_url}"' in article_html
            assert "embedded-content-key=" in article_html
        finally:
            # Clean up created article
            await delete_draft_with_retry(real_session, article_key)

    async def test_money_indices_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """noteマネー指数URLがAPIでfigure要素に変換される.

        - 指数（日経平均: NKY）のURLがfigure要素に変換される
        - embedded-service="money"属性が設定される
        """
        # Arrange - Use 日経平均 (NKY) as test URL
        money_url = "https://money.note.com/indices/NKY"
        body = f"""指数チャート埋め込みテスト

{money_url}

上記に日経平均の株価チャートが表示されます。"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] noteマネー Index Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Verify embed figure is present in raw HTML
        article_key = extract_article_key(result)
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present
            assert 'embedded-service="money"' in article_html
            assert f'data-src="{money_url}"' in article_html
        finally:
            # Clean up created article
            await delete_draft_with_retry(real_session, article_key)

    async def test_money_investments_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """noteマネー投資信託URLがAPIでfigure要素に変換される.

        - 投資信託（eMAXIS Slim: 0331418A）のURLがfigure要素に変換される
        - embedded-service="money"属性が設定される
        """
        # Arrange - Use eMAXIS Slim as test URL
        money_url = "https://money.note.com/investments/0331418A"
        body = f"""投資信託チャート埋め込みテスト

{money_url}

上記に投資信託のチャートが表示されます。"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] noteマネー Investment Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Verify embed figure is present in raw HTML
        article_key = extract_article_key(result)
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present
            assert 'embedded-service="money"' in article_html
            assert f'data-src="{money_url}"' in article_html
        finally:
            # Clean up created article
            await delete_draft_with_retry(real_session, article_key)


class TestStockNotationEmbedApiConversion:
    """Test stock notation (^5243, $GOOG) embed conversion via API."""

    async def test_jp_stock_notation_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """日本株記法 (^5243) がAPIでfigure要素に変換される.

        - 株価記法 ^5243 がURLに変換される
        - noteマネーURLがfigure要素に変換される
        - embedded-service="money"属性が設定される
        """
        # Arrange - Use Japanese stock notation for note社 (証券コード: 5243)
        body = """株価記法埋め込みテスト

^5243

上記にnote社の株価チャートが表示されます。"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] 日本株記法 Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result
        assert "ID:" in result

        # Verify embed figure is present in raw HTML
        article_key = extract_article_key(result)
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present (notation converted to URL then embedded)
            assert 'embedded-service="money"' in article_html
            assert 'data-src="https://money.note.com/companies/5243"' in article_html
            assert "embedded-content-key=" in article_html
        finally:
            # Clean up created article
            await delete_draft_with_retry(real_session, article_key)

    async def test_us_stock_notation_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """米国株記法 ($GOOG) がAPIでfigure要素に変換される.

        - 株価記法 $GOOG がURLに変換される
        - noteマネーURLがfigure要素に変換される
        - embedded-service="money"属性が設定される
        """
        # Arrange - Use US stock notation for Google
        body = """米国株記法埋め込みテスト

$GOOG

上記にGoogleの株価チャートが表示されます。"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] 米国株記法 Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Verify embed figure is present in raw HTML
        article_key = extract_article_key(result)
        try:
            article_html = await get_article_html(article_key)

            # Verify embed figure is present
            assert 'embedded-service="money"' in article_html
            assert 'data-src="https://money.note.com/us_companies/GOOG"' in article_html
        finally:
            # Clean up created article
            await delete_draft_with_retry(real_session, article_key)

    async def test_mixed_stock_notations_embed_via_api(
        self,
        real_session: Session,
    ) -> None:
        """日本株と米国株の記法が混在しても変換される.

        - 複数の株価記法がそれぞれURLに変換される
        - 各URLがfigure要素に変換される
        """
        # Arrange - Mix Japanese and US stock notations
        body = """# 注目銘柄

## note社 (日本株)

^5243

## Google (米国株)

$GOOG

どちらも株価チャートとして表示されます。"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] 複合株価記法 Embed via API",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Verify both embed figures are present
        article_key = extract_article_key(result)
        try:
            article_html = await get_article_html(article_key)

            # Both should be converted
            assert article_html.count('embedded-service="money"') >= 2
            assert 'data-src="https://money.note.com/companies/5243"' in article_html
            assert 'data-src="https://money.note.com/us_companies/GOOG"' in article_html
        finally:
            # Clean up created article
            await delete_draft_with_retry(real_session, article_key)

    async def test_stock_notation_in_code_block_not_converted(
        self,
        real_session: Session,
    ) -> None:
        """コードブロック内の株価記法は変換されない.

        - コードブロック内の記法はそのまま保持される
        - figure要素には変換されない
        """
        # Arrange - Stock notation inside code block
        body = """株価記法の使い方

```
日本株: ^5243
米国株: $GOOG
```

上記はコードブロック内なので変換されません。"""

        # Act
        result = await note_create_draft.fn(
            title="[E2E-TEST] コードブロック内株価記法",
            body=body,
            tags=["e2e-test", "embed-api"],
        )

        # Assert - API response
        assert "下書きを作成しました" in result

        # Verify no embed figures are present
        article_key = extract_article_key(result)
        try:
            article_html = await get_article_html(article_key)

            # Code block content should NOT be converted to embeds
            assert 'embedded-service="money"' not in article_html
            # Original notation should be preserved in code block
            assert "^5243" in article_html
            assert "$GOOG" in article_html
        finally:
            # Clean up created article
            await delete_draft_with_retry(real_session, article_key)
