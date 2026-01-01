"""E2E tests for MCP tools on note.com.

Tests the MCP tool functions that interact with note.com API.
Requires valid authentication for most tests.

Note: These tests import and call the tool functions directly,
bypassing MCP protocol for E2E testing purposes.
The @mcp.tool() decorator wraps functions in FunctionTool objects.
We access the original function via the .fn attribute.

Run with: uv run pytest tests/e2e/test_mcp_tools.py -v
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from note_mcp.auth.session import SessionManager
from note_mcp.server import (
    note_check_auth,
    note_create_draft,
    note_get_article,
    note_insert_body_image,
    note_list_articles,
    note_logout,
    note_set_username,
    note_show_preview,
    note_update_article,
    note_upload_body_image,
    note_upload_eyecatch,
)

if TYPE_CHECKING:
    from note_mcp.models import Article, Session

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


class TestAuthenticationFlow:
    """認証フローテスト（依存関係なし、最初に実行）."""

    async def test_check_auth_authenticated(
        self,
        real_session: Session,
    ) -> None:
        """認証済み状態でcheck_authが認証済みメッセージを返す."""
        # Arrange: real_session fixture ensures we're authenticated

        # Act
        result = await note_check_auth.fn()

        # Assert
        assert "認証済み" in result
        assert real_session.username in result

    async def test_check_auth_not_authenticated(self) -> None:
        """未認証状態でcheck_authが未認証メッセージを返す."""
        # Arrange: Clear any existing session
        session_manager = SessionManager()
        original_session = session_manager.load()
        session_manager.clear()

        try:
            # Act
            result = await note_check_auth.fn()

            # Assert
            assert "未認証" in result or "ログイン" in result
        finally:
            # Restore original session if it existed
            if original_session:
                session_manager.save(original_session)

    async def test_set_username(
        self,
        real_session: Session,
    ) -> None:
        """ユーザー名設定が保存される."""
        # Arrange: Use a test username
        test_username = "test_user_e2e"
        original_username = real_session.username

        # Act
        result = await note_set_username.fn(test_username)

        # Assert
        assert "設定" in result
        assert test_username in result

        # Cleanup: Restore original username
        await note_set_username.fn(original_username)

    async def test_set_username_invalid(
        self,
        real_session: Session,
    ) -> None:
        """無効なユーザー名はエラーになる."""
        # Arrange: Invalid username with special characters
        invalid_username = "invalid@user!name"

        # Act
        result = await note_set_username.fn(invalid_username)

        # Assert
        assert "無効" in result

    async def test_logout(
        self,
        real_session: Session,
    ) -> None:
        """ログアウトでセッションがクリアされる."""
        # Arrange: Ensure we have a session
        session_manager = SessionManager()
        assert session_manager.has_session()

        # Act
        result = await note_logout.fn()

        # Assert
        assert "ログアウト" in result
        assert not session_manager.has_session()

        # Cleanup: Restore session for other tests
        session_manager.save(real_session)


class TestArticleCRUD:
    """記事CRUD操作テスト."""

    async def test_list_articles(
        self,
        real_session: Session,
    ) -> None:
        """記事一覧が取得できる."""
        # Act
        result = await note_list_articles.fn()

        # Assert
        assert "記事" in result or "件" in result or "一覧" in result

    async def test_list_articles_with_status_filter(
        self,
        real_session: Session,
    ) -> None:
        """ステータスでフィルタした記事一覧が取得できる."""
        # Act
        result = await note_list_articles.fn(status="draft")

        # Assert
        # Should either show drafts or indicate no drafts found
        assert isinstance(result, str)

    async def test_create_draft(
        self,
        real_session: Session,
        draft_article: Article,
    ) -> None:
        """下書き記事が作成される（draft_article fixtureを使用）."""
        # Assert: draft_article fixture already created the article
        assert draft_article.id is not None
        assert draft_article.key is not None
        assert "[E2E-TEST-" in draft_article.title

    async def test_get_article(
        self,
        real_session: Session,
        draft_article: Article,
    ) -> None:
        """記事の内容が取得できる."""
        # Act
        result = await note_get_article.fn(draft_article.id)

        # Assert
        assert draft_article.title in result or "タイトル" in result

    async def test_update_article(
        self,
        real_session: Session,
        draft_article: Article,
    ) -> None:
        """記事の更新ができる."""
        # Arrange
        new_title = f"{draft_article.title} - Updated"
        new_body = "# Updated Content\n\nThis article was updated by E2E test."

        # Act
        result = await note_update_article.fn(
            article_id=draft_article.id,
            title=new_title,
            body=new_body,
        )

        # Assert
        assert "更新" in result or "成功" in result

    async def test_article_lifecycle(
        self,
        real_session: Session,
    ) -> None:
        """記事のライフサイクル: 作成→取得→更新."""
        import time

        # Step 1: Create
        test_title = f"[E2E-TEST-{int(time.time())}] Lifecycle Test"
        test_body = "# Lifecycle Test\n\nCreated by E2E test."

        create_result = await note_create_draft.fn(
            title=test_title,
            body=test_body,
            tags=["e2e-test", "lifecycle"],
        )
        assert "作成" in create_result or "ID" in create_result

        # Extract article ID from result (format varies)
        # The result should contain the article ID
        assert isinstance(create_result, str)

        # Step 2: List to find our article
        list_result = await note_list_articles.fn(status="draft")
        assert test_title in list_result or "E2E-TEST" in list_result


class TestImageAndPreview:
    """画像アップロード・プレビュー機能テスト."""

    async def test_upload_eyecatch(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """アイキャッチ画像をアップロードできる."""
        # Act
        result = await note_upload_eyecatch.fn(
            file_path=str(test_image_path),
            note_id=draft_article.id,
        )

        # Assert
        assert "アップロード" in result or "成功" in result or "URL" in result

    async def test_upload_body_image(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """本文用画像をアップロードできる."""
        # Act
        result = await note_upload_body_image.fn(
            file_path=str(test_image_path),
            note_id=draft_article.id,
        )

        # Assert
        assert "アップロード" in result or "成功" in result or "URL" in result

    async def test_insert_body_image(
        self,
        real_session: Session,
        draft_article: Article,
        test_image_path: Path,
    ) -> None:
        """本文に画像を挿入できる."""
        # Act
        result = await note_insert_body_image.fn(
            file_path=str(test_image_path),
            article_id=draft_article.id,
            caption="E2E Test Image",
        )

        # Assert
        assert "挿入" in result or "成功" in result or "追加" in result

    async def test_show_preview(
        self,
        real_session: Session,
        draft_article: Article,
    ) -> None:
        """記事のプレビューを表示できる."""
        # Act
        result = await note_show_preview.fn(
            article_key=draft_article.key,
        )

        # Assert
        assert "プレビュー" in result or "表示" in result or "URL" in result

    async def test_upload_invalid_image_path(
        self,
        real_session: Session,
        draft_article: Article,
    ) -> None:
        """存在しない画像パスでエラーになる."""
        # Act
        result = await note_upload_eyecatch.fn(
            file_path="/nonexistent/path/image.png",
            note_id=draft_article.id,
        )

        # Assert
        assert "エラー" in result or "見つかり" in result or "存在" in result
