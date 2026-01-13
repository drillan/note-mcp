"""Unit tests for delete draft models.

Tests for the Pydantic models used in the delete draft feature:
- ArticleSummary
- FailedArticle
- DeleteResult
- DeletePreview
- BulkDeletePreview
- BulkDeleteResult
- DeleteDraftInput
- DeleteAllDraftsInput
"""

import pytest
from pydantic import ValidationError

from note_mcp.models import (
    ArticleStatus,
    ArticleSummary,
    BulkDeletePreview,
    BulkDeleteResult,
    DeleteAllDraftsInput,
    DeleteDraftInput,
    DeletePreview,
    DeleteResult,
    FailedArticle,
)


class TestArticleSummary:
    """T004: Unit tests for ArticleSummary model."""

    def test_valid_article_summary(self) -> None:
        """Test creating a valid ArticleSummary."""
        summary = ArticleSummary(
            article_id="12345678",
            article_key="n1234567890ab",
            title="テスト記事",
        )
        assert summary.article_id == "12345678"
        assert summary.article_key == "n1234567890ab"
        assert summary.title == "テスト記事"

    def test_article_summary_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ArticleSummary(article_id="12345678")  # type: ignore[call-arg]

    def test_article_summary_empty_title(self) -> None:
        """Test that empty title is allowed."""
        summary = ArticleSummary(
            article_id="12345678",
            article_key="n1234567890ab",
            title="",
        )
        assert summary.title == ""


class TestFailedArticle:
    """T005: Unit tests for FailedArticle model."""

    def test_valid_failed_article(self) -> None:
        """Test creating a valid FailedArticle."""
        failed = FailedArticle(
            article_id="12345678",
            article_key="n1234567890ab",
            title="失敗した記事",
            error="削除に失敗しました",
        )
        assert failed.article_id == "12345678"
        assert failed.article_key == "n1234567890ab"
        assert failed.title == "失敗した記事"
        assert failed.error == "削除に失敗しました"

    def test_failed_article_missing_error(self) -> None:
        """Test that missing error field raises ValidationError."""
        with pytest.raises(ValidationError):
            FailedArticle(
                article_id="12345678",
                article_key="n1234567890ab",
                title="失敗した記事",
            )  # type: ignore[call-arg]


class TestDeleteResult:
    """T006: Unit tests for DeleteResult model."""

    def test_valid_delete_result_success(self) -> None:
        """Test creating a successful DeleteResult."""
        result = DeleteResult(
            success=True,
            article_id="12345678",
            article_key="n1234567890ab",
            article_title="削除された記事",
            message="下書き記事「削除された記事」(n1234567890ab)を削除しました。",
        )
        assert result.success is True
        assert result.article_id == "12345678"
        assert result.article_key == "n1234567890ab"
        assert result.article_title == "削除された記事"
        assert "削除しました" in result.message

    def test_valid_delete_result_failure(self) -> None:
        """Test creating a failed DeleteResult."""
        result = DeleteResult(
            success=False,
            article_id="12345678",
            article_key="n1234567890ab",
            article_title="削除失敗記事",
            message="削除に失敗しました。",
        )
        assert result.success is False

    def test_delete_result_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            DeleteResult(
                success=True,
                article_id="12345678",
            )  # type: ignore[call-arg]


class TestDeletePreview:
    """T007: Unit tests for DeletePreview model."""

    def test_valid_delete_preview(self) -> None:
        """Test creating a valid DeletePreview."""
        preview = DeletePreview(
            article_id="12345678",
            article_key="n1234567890ab",
            article_title="削除対象記事",
            status=ArticleStatus.DRAFT,
            message="下書き記事「削除対象記事」を削除しますか？confirm=True を指定して再度呼び出してください。",
        )
        assert preview.article_id == "12345678"
        assert preview.article_key == "n1234567890ab"
        assert preview.article_title == "削除対象記事"
        assert preview.status == ArticleStatus.DRAFT
        assert "confirm=True" in preview.message

    def test_delete_preview_with_published_status(self) -> None:
        """Test DeletePreview with published status."""
        preview = DeletePreview(
            article_id="12345678",
            article_key="n1234567890ab",
            article_title="公開済み記事",
            status=ArticleStatus.PUBLISHED,
            message="公開済み記事は削除できません。",
        )
        assert preview.status == ArticleStatus.PUBLISHED


class TestBulkDeletePreview:
    """T008: Unit tests for BulkDeletePreview model."""

    def test_valid_bulk_delete_preview(self) -> None:
        """Test creating a valid BulkDeletePreview."""
        articles = [
            ArticleSummary(
                article_id="12345678",
                article_key="n1234567890ab",
                title="下書き1",
            ),
            ArticleSummary(
                article_id="12345679",
                article_key="n2345678901bc",
                title="下書き2",
            ),
        ]
        preview = BulkDeletePreview(
            total_count=2,
            articles=articles,
            message="2件の下書き記事を削除しますか？confirm=True を指定して再度呼び出してください。",
        )
        assert preview.total_count == 2
        assert len(preview.articles) == 2
        assert preview.articles[0].title == "下書き1"
        assert "2件" in preview.message

    def test_bulk_delete_preview_empty(self) -> None:
        """Test BulkDeletePreview with no articles."""
        preview = BulkDeletePreview(
            total_count=0,
            articles=[],
            message="削除対象の下書きがありません。",
        )
        assert preview.total_count == 0
        assert len(preview.articles) == 0


class TestBulkDeleteResult:
    """T009: Unit tests for BulkDeleteResult model."""

    def test_valid_bulk_delete_result_all_success(self) -> None:
        """Test BulkDeleteResult with all successful deletions."""
        deleted = [
            ArticleSummary(
                article_id="12345678",
                article_key="n1234567890ab",
                title="下書き1",
            ),
            ArticleSummary(
                article_id="12345679",
                article_key="n2345678901bc",
                title="下書き2",
            ),
        ]
        result = BulkDeleteResult(
            success=True,
            total_count=2,
            deleted_count=2,
            failed_count=0,
            deleted_articles=deleted,
            failed_articles=[],
            message="2件の下書き記事を削除しました。",
        )
        assert result.success is True
        assert result.total_count == 2
        assert result.deleted_count == 2
        assert result.failed_count == 0
        assert len(result.deleted_articles) == 2
        assert len(result.failed_articles) == 0

    def test_valid_bulk_delete_result_partial_failure(self) -> None:
        """Test BulkDeleteResult with partial failures."""
        deleted = [
            ArticleSummary(
                article_id="12345678",
                article_key="n1234567890ab",
                title="下書き1",
            ),
        ]
        failed = [
            FailedArticle(
                article_id="12345679",
                article_key="n2345678901bc",
                title="下書き2",
                error="削除に失敗しました",
            ),
        ]
        result = BulkDeleteResult(
            success=False,
            total_count=2,
            deleted_count=1,
            failed_count=1,
            deleted_articles=deleted,
            failed_articles=failed,
            message="2件中1件の下書き記事を削除しました。1件の削除に失敗しました。",
        )
        assert result.success is False
        assert result.total_count == 2
        assert result.deleted_count == 1
        assert result.failed_count == 1
        assert len(result.deleted_articles) == 1
        assert len(result.failed_articles) == 1


class TestDeleteDraftInput:
    """T010: Unit tests for DeleteDraftInput model."""

    def test_valid_delete_draft_input(self) -> None:
        """Test creating a valid DeleteDraftInput."""
        input_data = DeleteDraftInput(
            article_key="n1234567890ab",
            confirm=True,
        )
        assert input_data.article_key == "n1234567890ab"
        assert input_data.confirm is True

    def test_delete_draft_input_default_confirm(self) -> None:
        """Test that confirm defaults to False."""
        input_data = DeleteDraftInput(
            article_key="n1234567890ab",
        )
        assert input_data.confirm is False

    def test_delete_draft_input_missing_article_key(self) -> None:
        """Test that missing article_key raises ValidationError."""
        with pytest.raises(ValidationError):
            DeleteDraftInput(confirm=True)  # type: ignore[call-arg]


class TestDeleteAllDraftsInput:
    """T011: Unit tests for DeleteAllDraftsInput model."""

    def test_valid_delete_all_drafts_input(self) -> None:
        """Test creating a valid DeleteAllDraftsInput."""
        input_data = DeleteAllDraftsInput(
            confirm=True,
        )
        assert input_data.confirm is True

    def test_delete_all_drafts_input_default_confirm(self) -> None:
        """Test that confirm defaults to False."""
        input_data = DeleteAllDraftsInput()
        assert input_data.confirm is False
