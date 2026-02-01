"""Unit tests for server module functions."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.models import (
    Article,
    ArticleListResult,
    ArticleStatus,
    ErrorCode,
    Image,
    ImageType,
    NoteAPIError,
)
from note_mcp.utils.file_parser import LocalImage, ParsedArticle


class TestNoteListArticles:
    """Tests for note_list_articles function."""

    @pytest.mark.asyncio
    async def test_output_includes_article_key(self) -> None:
        """記事一覧の出力にキーが含まれることを確認する.

        Issue #137: note_list_articlesの出力に記事キー（key）を追加する。
        note_get_preview_htmlやnote_show_previewはarticle_keyを必要とするため、
        記事一覧からキーを確認できるようにする。
        """
        mock_session = MagicMock()
        mock_articles = [
            Article(
                id="123456789",
                key="n1234567890ab",
                title="テスト記事1",
                status=ArticleStatus.DRAFT,
                body="",
            ),
            Article(
                id="987654321",
                key="nfedcba098765",
                title="テスト記事2",
                status=ArticleStatus.PUBLISHED,
                body="",
            ),
        ]
        mock_result = ArticleListResult(
            articles=mock_articles,
            total=2,
            page=1,
            has_more=False,
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.list_articles", new_callable=AsyncMock) as mock_list,
        ):
            mock_session.is_expired.return_value = False
            mock_session_manager.load.return_value = mock_session
            mock_list.return_value = mock_result

            from note_mcp.server import note_list_articles

            fn = note_list_articles.fn
            result = await fn()

            # 出力にキーが含まれることを確認
            assert "キー: n1234567890ab" in result
            assert "キー: nfedcba098765" in result

            # IDも引き続き含まれることを確認
            assert "ID: 123456789" in result
            assert "ID: 987654321" in result


class TestNoteCreateFromFile:
    """Tests for note_create_from_file function."""

    @pytest.mark.asyncio
    async def test_update_article_receives_article_key_not_id(
        self,
        tmp_path: Path,
    ) -> None:
        """update_article should receive article.key, not article.id.

        This is critical because the update_article API requires the key format
        (e.g., 'n1234567890ab'), not the numeric ID. Using the wrong format
        causes 400 errors from the API.
        """
        # Create a test markdown file with a local image
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\n![image](./test.png)")

        # Create a test image file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake png data")

        # Mock objects
        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",  # Numeric ID
            key="n1234567890ab",  # Key format (different from ID)
            title="Test",
            status=ArticleStatus.DRAFT,
            body="",
        )
        mock_parsed = ParsedArticle(
            title="Test",
            body="![image](./test.png)",
            tags=[],
            local_images=[
                LocalImage(
                    markdown_path="./test.png",
                    absolute_path=test_image,
                )
            ],
        )
        mock_upload_result = Image(
            key="uploaded_key",
            url="https://assets.st-note.com/uploaded.png",
            original_path=str(test_image),
            uploaded_at=1234567890,
            image_type=ImageType.BODY,
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.parse_markdown_file") as mock_parse,
            patch("note_mcp.server.create_draft", new_callable=AsyncMock) as mock_create,
            patch("note_mcp.server.upload_body_image", new_callable=AsyncMock) as mock_upload,
            patch("note_mcp.server.update_article", new_callable=AsyncMock) as mock_update,
        ):
            mock_session_manager.load.return_value = mock_session
            mock_parse.return_value = mock_parsed
            mock_create.return_value = mock_article
            mock_upload.return_value = mock_upload_result

            # Import after patching
            from note_mcp.server import note_create_from_file

            # Access the underlying function (not the FunctionTool wrapper)
            fn = note_create_from_file.fn

            # Execute
            result = await fn(str(md_file), upload_images=True)

            # Verify update_article was called with article.key, not article.id
            mock_update.assert_called_once()
            call_args = mock_update.call_args

            # First positional argument is session, second is article_id
            article_id_arg = call_args[0][1]

            # CRITICAL: Must use article.key format, not numeric ID
            assert article_id_arg == "n1234567890ab", (
                f"update_article should receive article.key ('n1234567890ab'), "
                f"not article.id ('123456789'). Got: {article_id_arg}"
            )
            assert article_id_arg != "123456789", "update_article must NOT receive numeric article.id"

            # Verify the result indicates success
            assert "✅" in result
            assert "アップロードした画像: 1件" in result

    @pytest.mark.asyncio
    async def test_no_update_when_no_images_uploaded(
        self,
        tmp_path: Path,
    ) -> None:
        """update_article should not be called when no images are uploaded."""
        # Create a test markdown file without images
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nNo images here.")

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="Test",
            status=ArticleStatus.DRAFT,
            body="",
        )
        mock_parsed = ParsedArticle(
            title="Test",
            body="No images here.",
            tags=[],
            local_images=[],  # No local images
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.parse_markdown_file") as mock_parse,
            patch("note_mcp.server.create_draft", new_callable=AsyncMock) as mock_create,
            patch("note_mcp.server.update_article", new_callable=AsyncMock) as mock_update,
        ):
            mock_session_manager.load.return_value = mock_session
            mock_parse.return_value = mock_parsed
            mock_create.return_value = mock_article

            from note_mcp.server import note_create_from_file

            # Access the underlying function (not the FunctionTool wrapper)
            fn = note_create_from_file.fn
            result = await fn(str(md_file), upload_images=True)

            # update_article should NOT be called when no images uploaded
            mock_update.assert_not_called()

            # Verify the result indicates success without image info
            assert "✅" in result
            assert "アップロードした画像" not in result

    @pytest.mark.asyncio
    async def test_eyecatch_image_upload(
        self,
        tmp_path: Path,
    ) -> None:
        """eyecatch画像が指定されている場合、アップロードされる。"""
        # Create a test markdown file with eyecatch
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Test\neyecatch: ./header.png\n---\n\nBody")

        # Create a test eyecatch image file
        eyecatch_image = tmp_path / "header.png"
        eyecatch_image.write_bytes(b"fake png data")

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="Test",
            status=ArticleStatus.DRAFT,
            body="",
        )
        mock_parsed = ParsedArticle(
            title="Test",
            body="Body",
            tags=[],
            local_images=[],
            eyecatch=eyecatch_image,
        )
        mock_eyecatch_result = Image(
            key="eyecatch_key",
            url="https://assets.st-note.com/eyecatch.png",
            original_path=str(eyecatch_image),
            uploaded_at=1234567890,
            image_type=ImageType.EYECATCH,
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.parse_markdown_file") as mock_parse,
            patch("note_mcp.server.create_draft", new_callable=AsyncMock) as mock_create,
            patch("note_mcp.server.upload_eyecatch_image", new_callable=AsyncMock) as mock_upload_eyecatch,
        ):
            mock_session_manager.load.return_value = mock_session
            mock_parse.return_value = mock_parsed
            mock_create.return_value = mock_article
            mock_upload_eyecatch.return_value = mock_eyecatch_result

            from note_mcp.server import note_create_from_file

            fn = note_create_from_file.fn
            result = await fn(str(md_file), upload_images=True)

            # upload_eyecatch_imageが呼ばれることを確認
            mock_upload_eyecatch.assert_called_once()
            call_args = mock_upload_eyecatch.call_args[0]
            assert call_args[1] == str(eyecatch_image)  # file_path
            assert call_args[2] == "123456789"  # note_id

            # 結果にアイキャッチ成功メッセージが含まれる
            assert "✅" in result
            assert "アイキャッチ画像: アップロード完了" in result

    @pytest.mark.asyncio
    async def test_eyecatch_not_uploaded_when_upload_images_false(
        self,
        tmp_path: Path,
    ) -> None:
        """upload_images=Falseの場合、eyecatch画像もアップロードされない。"""
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Test\neyecatch: ./header.png\n---\n\nBody")

        eyecatch_image = tmp_path / "header.png"
        eyecatch_image.write_bytes(b"fake png data")

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="Test",
            status=ArticleStatus.DRAFT,
            body="",
        )
        mock_parsed = ParsedArticle(
            title="Test",
            body="Body",
            tags=[],
            local_images=[],
            eyecatch=eyecatch_image,
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.parse_markdown_file") as mock_parse,
            patch("note_mcp.server.create_draft", new_callable=AsyncMock) as mock_create,
            patch("note_mcp.server.upload_eyecatch_image", new_callable=AsyncMock) as mock_upload_eyecatch,
        ):
            mock_session_manager.load.return_value = mock_session
            mock_parse.return_value = mock_parsed
            mock_create.return_value = mock_article

            from note_mcp.server import note_create_from_file

            fn = note_create_from_file.fn
            result = await fn(str(md_file), upload_images=False)

            # upload_eyecatch_imageが呼ばれないことを確認
            mock_upload_eyecatch.assert_not_called()

            # 結果にアイキャッチメッセージが含まれない
            assert "✅" in result
            assert "アイキャッチ画像" not in result

    @pytest.mark.asyncio
    async def test_eyecatch_file_not_found(
        self,
        tmp_path: Path,
    ) -> None:
        """eyecatchファイルが存在しない場合、エラーメッセージが表示される。"""
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Test\neyecatch: ./missing.png\n---\n\nBody")

        # eyecatchファイルは作成しない（存在しない）
        missing_eyecatch = tmp_path / "missing.png"

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="Test",
            status=ArticleStatus.DRAFT,
            body="",
        )
        mock_parsed = ParsedArticle(
            title="Test",
            body="Body",
            tags=[],
            local_images=[],
            eyecatch=missing_eyecatch,  # 存在しないファイル
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.parse_markdown_file") as mock_parse,
            patch("note_mcp.server.create_draft", new_callable=AsyncMock) as mock_create,
            patch("note_mcp.server.upload_eyecatch_image", new_callable=AsyncMock) as mock_upload_eyecatch,
        ):
            mock_session_manager.load.return_value = mock_session
            mock_parse.return_value = mock_parsed
            mock_create.return_value = mock_article

            from note_mcp.server import note_create_from_file

            fn = note_create_from_file.fn
            result = await fn(str(md_file), upload_images=True)

            # upload_eyecatch_imageが呼ばれないことを確認
            mock_upload_eyecatch.assert_not_called()

            # 結果にエラーメッセージが含まれる
            assert "✅" in result  # 記事作成自体は成功
            assert "⚠️ アイキャッチ画像アップロード失敗" in result
            assert "ファイルが見つかりません" in result

    @pytest.mark.asyncio
    async def test_eyecatch_api_error_shows_filename(
        self,
        tmp_path: Path,
    ) -> None:
        """eyecatchアップロードでAPIエラーが発生した場合、ファイル名付きエラーが表示される。"""
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Test\neyecatch: ./header.png\n---\n\nBody")

        eyecatch_image = tmp_path / "header.png"
        eyecatch_image.write_bytes(b"fake png data")

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="Test",
            status=ArticleStatus.DRAFT,
            body="",
        )
        mock_parsed = ParsedArticle(
            title="Test",
            body="Body",
            tags=[],
            local_images=[],
            eyecatch=eyecatch_image,
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.parse_markdown_file") as mock_parse,
            patch("note_mcp.server.create_draft", new_callable=AsyncMock) as mock_create,
            patch("note_mcp.server.upload_eyecatch_image", new_callable=AsyncMock) as mock_upload_eyecatch,
        ):
            mock_session_manager.load.return_value = mock_session
            mock_parse.return_value = mock_parsed
            mock_create.return_value = mock_article
            # APIエラーをシミュレート
            mock_upload_eyecatch.side_effect = NoteAPIError(ErrorCode.API_ERROR, "Server error")

            from note_mcp.server import note_create_from_file

            fn = note_create_from_file.fn
            result = await fn(str(md_file), upload_images=True)

            # 記事作成自体は成功
            assert "✅" in result
            # エラーメッセージにファイル名が含まれる
            assert "⚠️ アイキャッチ画像アップロード失敗" in result
            assert "header.png" in result
            assert "Server error" in result


class TestNotePublishArticle:
    """Tests for note_publish_article function."""

    @pytest.mark.asyncio
    async def test_file_path_provides_tags_when_tags_not_specified(
        self,
        tmp_path: Path,
    ) -> None:
        """file_path指定時、タグがファイルから取得されて公開される。"""
        # Create a test markdown file with tags
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Test Article\ntags:\n  - Python\n  - MCP\n---\n\nBody content")

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="Test Article",
            status=ArticleStatus.PUBLISHED,
            body="Body content",
            url="https://note.com/user/n/n1234567890ab",
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.publish_article", new_callable=AsyncMock) as mock_publish,
        ):
            mock_session.is_expired.return_value = False
            mock_session_manager.load.return_value = mock_session
            mock_publish.return_value = mock_article

            from note_mcp.server import note_publish_article

            fn = note_publish_article.fn
            result = await fn(article_id="123456789", file_path=str(md_file))

            # publish_article should be called with tags from file
            mock_publish.assert_called_once()
            call_kwargs = mock_publish.call_args[1]
            assert call_kwargs["tags"] == ["Python", "MCP"]

            # Result should indicate success
            assert "公開しました" in result
            assert "123456789" in result

    @pytest.mark.asyncio
    async def test_tags_parameter_takes_precedence_over_file_path(
        self,
        tmp_path: Path,
    ) -> None:
        """tagsとfile_path両方指定時、tagsが優先される。"""
        # Create a test markdown file with tags
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Test Article\ntags:\n  - FileTag1\n  - FileTag2\n---\n\nBody")

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="Test Article",
            status=ArticleStatus.PUBLISHED,
            body="Body",
            url="https://note.com/user/n/n1234567890ab",
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.publish_article", new_callable=AsyncMock) as mock_publish,
            patch("note_mcp.server.parse_markdown_file") as mock_parse,
        ):
            mock_session.is_expired.return_value = False
            mock_session_manager.load.return_value = mock_session
            mock_publish.return_value = mock_article

            from note_mcp.server import note_publish_article

            fn = note_publish_article.fn
            # Specify both tags and file_path
            result = await fn(
                article_id="123456789",
                tags=["ExplicitTag1", "ExplicitTag2"],
                file_path=str(md_file),
            )

            # publish_article should be called with explicit tags, not file tags
            mock_publish.assert_called_once()
            call_kwargs = mock_publish.call_args[1]
            assert call_kwargs["tags"] == ["ExplicitTag1", "ExplicitTag2"]

            # parse_markdown_file should NOT be called when tags are provided
            mock_parse.assert_not_called()

            assert "公開しました" in result

    @pytest.mark.asyncio
    async def test_file_path_without_tags_publishes_without_tags(
        self,
        tmp_path: Path,
    ) -> None:
        """file_path指定、タグなしの場合、タグなしで公開される。"""
        # Create a test markdown file without tags
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Test Article\n---\n\nBody without tags")

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="Test Article",
            status=ArticleStatus.PUBLISHED,
            body="Body without tags",
            url="https://note.com/user/n/n1234567890ab",
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.publish_article", new_callable=AsyncMock) as mock_publish,
        ):
            mock_session.is_expired.return_value = False
            mock_session_manager.load.return_value = mock_session
            mock_publish.return_value = mock_article

            from note_mcp.server import note_publish_article

            fn = note_publish_article.fn
            result = await fn(article_id="123456789", file_path=str(md_file))

            # publish_article should be called with empty tags list
            mock_publish.assert_called_once()
            call_kwargs = mock_publish.call_args[1]
            assert call_kwargs["tags"] == []

            assert "公開しました" in result

    @pytest.mark.asyncio
    async def test_file_path_not_found_returns_error(
        self,
        tmp_path: Path,
    ) -> None:
        """file_pathが存在しない場合、適切なエラーメッセージを返す。"""
        non_existent_file = tmp_path / "non_existent.md"

        mock_session = MagicMock()

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.publish_article", new_callable=AsyncMock) as mock_publish,
        ):
            mock_session.is_expired.return_value = False
            mock_session_manager.load.return_value = mock_session

            from note_mcp.server import note_publish_article

            fn = note_publish_article.fn
            result = await fn(article_id="123456789", file_path=str(non_existent_file))

            # publish_article should NOT be called
            mock_publish.assert_not_called()

            # Result should contain error message
            assert "ファイルが見つかりません" in result
            assert str(non_existent_file) in result

    @pytest.mark.asyncio
    async def test_file_path_ignored_for_new_article(
        self,
        tmp_path: Path,
    ) -> None:
        """新規作成時（article_idなし）はfile_pathが無視される。"""
        # Create a test markdown file with tags
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: File Title\ntags:\n  - FileTag\n---\n\nFile Body")

        mock_session = MagicMock()
        mock_article = Article(
            id="123456789",
            key="n1234567890ab",
            title="New Title",
            status=ArticleStatus.PUBLISHED,
            body="New Body",
            url="https://note.com/user/n/n1234567890ab",
        )

        with (
            patch("note_mcp.server._session_manager") as mock_session_manager,
            patch("note_mcp.server.publish_article", new_callable=AsyncMock) as mock_publish,
            patch("note_mcp.server.parse_markdown_file") as mock_parse,
        ):
            mock_session.is_expired.return_value = False
            mock_session_manager.load.return_value = mock_session
            mock_publish.return_value = mock_article

            from note_mcp.server import note_publish_article

            fn = note_publish_article.fn
            # New article creation (no article_id)
            result = await fn(
                title="New Title",
                body="New Body",
                file_path=str(md_file),
            )

            # parse_markdown_file should NOT be called for new article
            mock_parse.assert_not_called()

            # publish_article should be called with article_input (not article_id)
            mock_publish.assert_called_once()
            call_kwargs = mock_publish.call_args[1]
            assert "article_input" in call_kwargs
            assert "article_id" not in call_kwargs

            assert "公開しました" in result
