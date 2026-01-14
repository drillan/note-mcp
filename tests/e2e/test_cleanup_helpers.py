"""Tests for E2E cleanup helper functions.

Tests for the delete_draft_with_retry helper and preview_page_context
with cleanup_article parameter.

Issue #200: E2E tests were not cleaning up created articles.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from note_mcp.api.articles import create_draft, get_article
from note_mcp.models import Article, ArticleInput, NoteAPIError, Session
from tests.e2e.helpers import preview_page_context
from tests.e2e.helpers.cleanup import delete_draft_with_retry

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


class TestDeleteDraftWithRetry:
    """Tests for delete_draft_with_retry helper."""

    @pytest_asyncio.fixture
    async def test_article(self, real_session: Session) -> str:
        """Create a test article and return its key (no auto-cleanup)."""
        import time

        title = f"[E2E-TEST-{int(time.time())}] Cleanup Test"
        article_input = ArticleInput(
            title=title,
            body="# Test Article\n\nThis is a test article for cleanup testing.",
            tags=["e2e-test", "cleanup-test"],
        )
        article = await create_draft(real_session, article_input)
        return article.key

    async def test_delete_draft_with_retry_success(
        self,
        real_session: Session,
        test_article: str,
    ) -> None:
        """delete_draft_with_retry successfully deletes an article."""
        # Act
        await delete_draft_with_retry(real_session, test_article)

        # Assert: Article should no longer exist
        with pytest.raises(NoteAPIError):
            await get_article(real_session, test_article)

    async def test_delete_draft_with_retry_nonexistent(
        self,
        real_session: Session,
    ) -> None:
        """delete_draft_with_retry does not raise for non-existent article."""
        # Act & Assert: Should not raise, just log warning
        await delete_draft_with_retry(real_session, "n_nonexistent_key")


class TestPreviewPageContextWithCleanup:
    """Tests for preview_page_context with cleanup_article parameter."""

    async def test_preview_page_context_cleanup_article(
        self,
        real_session: Session,
    ) -> None:
        """preview_page_context with cleanup_article=True deletes article."""
        import time

        from note_mcp.api.articles import create_draft

        # Create test article
        title = f"[E2E-TEST-{int(time.time())}] Preview Cleanup Test"
        article_input = ArticleInput(
            title=title,
            body="# Test\n\nCleanup test content.",
            tags=["e2e-test"],
        )
        article = await create_draft(real_session, article_input)
        article_key = article.key

        # Act: Use preview_page_context with cleanup
        async with preview_page_context(
            real_session,
            article_key,
            cleanup_article=True,
        ) as preview_page:
            # Verify preview page loaded
            assert preview_page is not None

        # Assert: Article should be deleted after context exit
        with pytest.raises(NoteAPIError):
            await get_article(real_session, article_key)

    async def test_preview_page_context_no_cleanup_by_default(
        self,
        real_session: Session,
        draft_article: Article,  # Use fixture for auto-cleanup
    ) -> None:
        """preview_page_context does not delete article by default."""
        # Act: Use preview_page_context without cleanup_article
        async with preview_page_context(
            real_session,
            draft_article.key,
        ) as preview_page:
            assert preview_page is not None

        # Assert: Article should still exist (draft_article fixture will clean up)
        article = await get_article(real_session, draft_article.key)
        assert article.key == draft_article.key
