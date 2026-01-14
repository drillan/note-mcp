"""Unit tests for delete_draft function.

Tests for the single article deletion functionality:
- T021: delete_draft with confirm=False returns preview
- T022: delete_draft with confirm=True executes deletion
- T023: delete_draft when unauthenticated returns error
- T028: delete_draft for published article returns error
- T039: delete_draft for non-existent article returns 404 error
- T040: delete_draft for access denied returns 403 error
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from note_mcp.api.articles import delete_draft
from note_mcp.models import (
    ArticleStatus,
    DeletePreview,
    DeleteResult,
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


def create_mock_article_data(
    article_id: str = "12345678",
    article_key: str = "n1234567890ab",
    title: str = "テスト記事",
    status: str = "draft",
) -> dict[str, Any]:
    """Create mock article data for API responses."""
    return {
        "id": article_id,
        "key": article_key,
        "name": title,
        "body": "<p>Test content</p>",
        "status": status,
    }


class TestDeleteDraftConfirmFalse:
    """T021: Unit tests for delete_draft with confirm=False."""

    @pytest.mark.asyncio
    async def test_delete_draft_confirm_false_returns_preview(self) -> None:
        """Test that confirm=False returns a DeletePreview without deleting."""
        session = create_mock_session()
        article_data = create_mock_article_data()

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client_cls.return_value = mock_client

            result = await delete_draft(session, "n1234567890ab", confirm=False)

            # Verify preview is returned
            assert isinstance(result, DeletePreview)
            assert result.article_id == "12345678"
            assert result.article_key == "n1234567890ab"
            assert result.article_title == "テスト記事"
            assert result.status == ArticleStatus.DRAFT
            assert "confirm=True" in result.message

            # Verify delete was NOT called
            mock_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_draft_confirm_false_message_content(self) -> None:
        """Test that preview message includes article title and confirmation prompt."""
        session = create_mock_session()
        article_data = create_mock_article_data(title="重要な下書き")

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client_cls.return_value = mock_client

            result = await delete_draft(session, "n1234567890ab", confirm=False)

            assert isinstance(result, DeletePreview)
            assert "重要な下書き" in result.message
            assert "削除しますか" in result.message


class TestDeleteDraftConfirmTrue:
    """T022: Unit tests for delete_draft with confirm=True."""

    @pytest.mark.asyncio
    async def test_delete_draft_confirm_true_executes_deletion(self) -> None:
        """Test that confirm=True actually deletes the article."""
        session = create_mock_session()
        article_data = create_mock_article_data()

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client.delete.return_value = {"success": True}
            mock_client_cls.return_value = mock_client

            result = await delete_draft(session, "n1234567890ab", confirm=True)

            # Verify DeleteResult is returned
            assert isinstance(result, DeleteResult)
            assert result.success is True
            assert result.article_id == "12345678"
            assert result.article_key == "n1234567890ab"
            assert result.article_title == "テスト記事"
            assert "削除しました" in result.message

            # Verify delete WAS called with correct path
            mock_client.delete.assert_called_once_with("/v1/notes/n/n1234567890ab")

    @pytest.mark.asyncio
    async def test_delete_draft_success_message_includes_article_info(self) -> None:
        """Test that success message includes article title and key."""
        session = create_mock_session()
        article_data = create_mock_article_data(
            article_key="n9876543210dc",
            title="完成した下書き",
        )

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client.delete.return_value = {"success": True}
            mock_client_cls.return_value = mock_client

            result = await delete_draft(session, "n9876543210dc", confirm=True)

            assert isinstance(result, DeleteResult)
            assert "完成した下書き" in result.message
            assert "n9876543210dc" in result.message


class TestDeleteDraftUnauthenticated:
    """T023: Unit tests for delete_draft when unauthenticated."""

    @pytest.mark.asyncio
    async def test_delete_draft_unauthenticated_raises_error(self) -> None:
        """Test that unauthenticated requests raise NoteAPIError."""
        session = create_mock_session()

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = NoteAPIError(
                code=ErrorCode.NOT_AUTHENTICATED,
                message="Authentication required. Please log in first.",
                details={"status_code": 401},
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await delete_draft(session, "n1234567890ab", confirm=True)

            assert exc_info.value.code == ErrorCode.NOT_AUTHENTICATED


class TestDeleteDraftPublishedArticle:
    """T028: Unit tests for delete_draft with published article."""

    @pytest.mark.asyncio
    async def test_delete_draft_published_article_raises_error(self) -> None:
        """Test that attempting to delete a published article raises an error."""
        session = create_mock_session()
        article_data = create_mock_article_data(status="published")

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client_cls.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await delete_draft(session, "n1234567890ab", confirm=True)

            assert exc_info.value.code == ErrorCode.API_ERROR
            assert "公開済み記事は削除できません" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_delete_draft_published_article_no_delete_call(self) -> None:
        """Test that delete API is NOT called for published articles."""
        session = create_mock_session()
        article_data = create_mock_article_data(status="published")

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client_cls.return_value = mock_client

            with pytest.raises(NoteAPIError):
                await delete_draft(session, "n1234567890ab", confirm=True)

            # Verify delete was NOT called
            mock_client.delete.assert_not_called()


class TestDeleteDraftDeletedArticle:
    """Unit tests for delete_draft with deleted article.

    Issue #209: delete_draft should raise an error when attempting to
    delete an already deleted article.
    """

    @pytest.mark.asyncio
    async def test_delete_draft_deleted_article_raises_error(self) -> None:
        """Test that attempting to delete a deleted article raises an error."""
        session = create_mock_session()
        article_data = create_mock_article_data(status="deleted")

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client_cls.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await delete_draft(session, "n1234567890ab", confirm=True)

            assert exc_info.value.code == ErrorCode.ARTICLE_NOT_FOUND
            assert "deleted" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_delete_draft_deleted_article_no_delete_call(self) -> None:
        """Test that delete API is NOT called for deleted articles."""
        session = create_mock_session()
        article_data = create_mock_article_data(status="deleted")

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client_cls.return_value = mock_client

            with pytest.raises(NoteAPIError):
                await delete_draft(session, "n1234567890ab", confirm=True)

            # Verify delete was NOT called
            mock_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_draft_deleted_article_preview_mode(self) -> None:
        """Test that confirm=False also raises error for deleted article."""
        session = create_mock_session()
        article_data = create_mock_article_data(status="deleted")

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = {"data": article_data}
            mock_client_cls.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await delete_draft(session, "n1234567890ab", confirm=False)

            assert exc_info.value.code == ErrorCode.ARTICLE_NOT_FOUND


class TestDeleteDraftNotFound:
    """T039: Unit tests for delete_draft when article not found."""

    @pytest.mark.asyncio
    async def test_delete_draft_not_found_raises_error(self) -> None:
        """Test that deleting non-existent article raises ARTICLE_NOT_FOUND error."""
        session = create_mock_session()

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = NoteAPIError(
                code=ErrorCode.ARTICLE_NOT_FOUND,
                message="Resource not found.",
                details={"status_code": 404},
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await delete_draft(session, "n0000000000xx", confirm=True)

            assert exc_info.value.code == ErrorCode.ARTICLE_NOT_FOUND


class TestDeleteDraftAccessDenied:
    """T040: Unit tests for delete_draft when access denied."""

    @pytest.mark.asyncio
    async def test_delete_draft_access_denied_raises_error(self) -> None:
        """Test that deleting another user's article raises API_ERROR."""
        session = create_mock_session()

        with patch("note_mcp.api.articles.NoteAPIClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="Access denied.",
                details={"status_code": 403},
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(NoteAPIError) as exc_info:
                await delete_draft(session, "nother_users_article", confirm=True)

            assert exc_info.value.code == ErrorCode.API_ERROR
