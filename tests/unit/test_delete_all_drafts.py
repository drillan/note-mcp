"""Unit tests for delete_all_drafts function.

Tests for the bulk draft deletion functionality:
- T031: delete_all_drafts with confirm=False returns preview
- T032: delete_all_drafts with confirm=True executes bulk deletion
- T033: delete_all_drafts when no drafts returns empty message
- T034: delete_all_drafts with partial failure returns detailed result
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.api.articles import delete_all_drafts
from note_mcp.models import (
    BulkDeletePreview,
    BulkDeleteResult,
    ErrorCode,
    NoteAPIError,
    Session,
)


def create_mock_session() -> Session:
    """Create a mock session for testing."""
    return Session(
        cookies={"note_gql_auth_token": "test_token", "XSRF-TOKEN": "test_xsrf"},
        user_id="test_user_123",
        username="testuser",
        created_at=1700000000,
    )


def create_mock_article_list_response(
    articles: list[dict[str, Any]],
    total_count: int | None = None,
    is_last_page: bool = True,
) -> dict[str, Any]:
    """Create mock list_articles response."""
    return {
        "data": {
            "notes": articles,
            "totalCount": total_count if total_count is not None else len(articles),
            "isLastPage": is_last_page,
        }
    }


def create_paginated_get_side_effect(
    first_page_articles: list[dict[str, Any]],
) -> Any:
    """Create a side_effect function for paginated GET responses.

    Returns articles on page 1, empty list on subsequent pages.
    """
    first_response = create_mock_article_list_response(first_page_articles)
    empty_response = create_mock_article_list_response([])

    def side_effect(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if params and params.get("page", 1) == 1:
            return first_response
        return empty_response

    return side_effect


def create_mock_draft_article(
    article_id: str,
    article_key: str,
    title: str,
) -> dict[str, Any]:
    """Create mock draft article data."""
    return {
        "id": article_id,
        "key": article_key,
        "name": title,
        "body": "<p>Test content</p>",
        "status": "draft",
    }


class TestDeleteAllDraftsConfirmFalse:
    """T031: Unit tests for delete_all_drafts with confirm=False."""

    @pytest.mark.asyncio
    async def test_delete_all_drafts_confirm_false_returns_preview(self) -> None:
        """Test that confirm=False returns a BulkDeletePreview without deleting."""
        session = create_mock_session()
        drafts = [
            create_mock_draft_article("111", "n1111111111aa", "下書き1"),
            create_mock_draft_article("222", "n2222222222bb", "下書き2"),
            create_mock_draft_article("333", "n3333333333cc", "下書き3"),
        ]

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = create_paginated_get_side_effect(drafts)
            mock_client_cls.return_value = mock_client

            result = await delete_all_drafts(session, confirm=False)

            # Verify preview is returned
            assert isinstance(result, BulkDeletePreview)
            assert result.total_count == 3
            assert len(result.articles) == 3
            assert result.articles[0].title == "下書き1"
            assert result.articles[1].title == "下書き2"
            assert result.articles[2].title == "下書き3"
            assert "3件" in result.message
            assert "confirm=True" in result.message

            # Verify delete was NOT called
            mock_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_all_drafts_confirm_false_includes_article_details(
        self,
    ) -> None:
        """Test that preview includes article details."""
        session = create_mock_session()
        drafts = [
            create_mock_draft_article("123", "nabc123def456", "重要な下書き"),
        ]

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = create_paginated_get_side_effect(drafts)
            mock_client_cls.return_value = mock_client

            result = await delete_all_drafts(session, confirm=False)

            assert isinstance(result, BulkDeletePreview)
            assert result.articles[0].article_id == "123"
            assert result.articles[0].article_key == "nabc123def456"
            assert result.articles[0].title == "重要な下書き"


class TestDeleteAllDraftsConfirmTrue:
    """T032: Unit tests for delete_all_drafts with confirm=True."""

    @pytest.mark.asyncio
    async def test_delete_all_drafts_confirm_true_executes_bulk_deletion(self) -> None:
        """Test that confirm=True actually deletes all drafts."""
        session = create_mock_session()
        drafts = [
            create_mock_draft_article("111", "n1111111111aa", "下書き1"),
            create_mock_draft_article("222", "n2222222222bb", "下書き2"),
        ]

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = create_paginated_get_side_effect(drafts)
            mock_client.delete.return_value = {"success": True}
            mock_client_cls.return_value = mock_client

            result = await delete_all_drafts(session, confirm=True)

            # Verify BulkDeleteResult is returned
            assert isinstance(result, BulkDeleteResult)
            assert result.success is True
            assert result.total_count == 2
            assert result.deleted_count == 2
            assert result.failed_count == 0
            assert len(result.deleted_articles) == 2
            assert len(result.failed_articles) == 0
            assert "2件" in result.message

            # Verify delete was called for each draft
            assert mock_client.delete.call_count == 2
            mock_client.delete.assert_any_call("/v1/notes/n/n1111111111aa")
            mock_client.delete.assert_any_call("/v1/notes/n/n2222222222bb")


class TestDeleteAllDraftsNoDrafts:
    """T033: Unit tests for delete_all_drafts when no drafts exist."""

    @pytest.mark.asyncio
    async def test_delete_all_drafts_no_drafts_returns_empty_preview(self) -> None:
        """Test that having no drafts returns appropriate preview."""
        session = create_mock_session()

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = create_paginated_get_side_effect([])
            mock_client_cls.return_value = mock_client

            result = await delete_all_drafts(session, confirm=False)

            assert isinstance(result, BulkDeletePreview)
            assert result.total_count == 0
            assert len(result.articles) == 0
            assert "削除対象の下書きがありません" in result.message

    @pytest.mark.asyncio
    async def test_delete_all_drafts_no_drafts_confirm_true_returns_empty_result(
        self,
    ) -> None:
        """Test that trying to delete when no drafts returns empty result."""
        session = create_mock_session()

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = create_paginated_get_side_effect([])
            mock_client_cls.return_value = mock_client

            result = await delete_all_drafts(session, confirm=True)

            assert isinstance(result, BulkDeleteResult)
            assert result.success is True  # Nothing to fail
            assert result.total_count == 0
            assert result.deleted_count == 0
            assert result.failed_count == 0


class TestDeleteAllDraftsPartialFailure:
    """T034: Unit tests for delete_all_drafts with partial failures."""

    @pytest.mark.asyncio
    async def test_delete_all_drafts_partial_failure_returns_detailed_result(
        self,
    ) -> None:
        """Test that partial failures are reported in result."""
        session = create_mock_session()
        drafts = [
            create_mock_draft_article("111", "n1111111111aa", "成功する下書き"),
            create_mock_draft_article("222", "n2222222222bb", "失敗する下書き"),
            create_mock_draft_article("333", "n3333333333cc", "もう一つ成功"),
        ]

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = create_paginated_get_side_effect(drafts)

            # First and third succeed, second fails
            def delete_side_effect(path: str) -> dict[str, bool]:
                if "n2222222222bb" in path:
                    raise NoteAPIError(
                        code=ErrorCode.API_ERROR,
                        message="削除に失敗しました",
                        details={"status_code": 500},
                    )
                return {"success": True}

            mock_client.delete.side_effect = delete_side_effect
            mock_client_cls.return_value = mock_client

            result = await delete_all_drafts(session, confirm=True)

            # Verify partial success result
            assert isinstance(result, BulkDeleteResult)
            assert result.success is False  # Not all succeeded
            assert result.total_count == 3
            assert result.deleted_count == 2
            assert result.failed_count == 1
            assert len(result.deleted_articles) == 2
            assert len(result.failed_articles) == 1

            # Check failed article details
            failed = result.failed_articles[0]
            assert failed.article_id == "222"
            assert failed.article_key == "n2222222222bb"
            assert failed.title == "失敗する下書き"
            assert "削除に失敗しました" in failed.error

    @pytest.mark.asyncio
    async def test_delete_all_drafts_all_fail_returns_failure_result(self) -> None:
        """Test that complete failure is properly reported."""
        session = create_mock_session()
        drafts = [
            create_mock_draft_article("111", "n1111111111aa", "失敗1"),
            create_mock_draft_article("222", "n2222222222bb", "失敗2"),
        ]

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = create_paginated_get_side_effect(drafts)
            mock_client.delete.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="サーバーエラー",
                details={"status_code": 500},
            )
            mock_client_cls.return_value = mock_client

            result = await delete_all_drafts(session, confirm=True)

            assert isinstance(result, BulkDeleteResult)
            assert result.success is False
            assert result.total_count == 2
            assert result.deleted_count == 0
            assert result.failed_count == 2
            assert len(result.deleted_articles) == 0
            assert len(result.failed_articles) == 2
