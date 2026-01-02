"""E2E tests for note_create_from_file MCP tool.

Tests creating note.com articles from Markdown files.
Covers frontmatter, H1-based titles, local image handling, and error cases.

Run with: uv run pytest tests/e2e/test_create_from_file.py -v
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from note_mcp.server import note_create_from_file

if TYPE_CHECKING:
    from note_mcp.models import Session

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_auth,
    pytest.mark.asyncio,
]


@pytest.fixture
def md_with_frontmatter(tmp_path: Path) -> Path:
    """YAMLフロントマター付きMarkdownファイルを作成。

    タイトルとタグがフロントマターから抽出される。
    """
    content = """---
title: "[E2E-TEST] Frontmatter Title"
tags:
  - e2e-test
  - frontmatter
---

This is the body content from frontmatter test.

## Section 1

Some section content.
"""
    md_file = tmp_path / "frontmatter_test.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture
def md_with_h1_only(tmp_path: Path) -> Path:
    """H1タイトルのみのMarkdownファイルを作成。

    タイトルがH1見出しから抽出され、H1は本文から削除される。
    """
    content = """# [E2E-TEST] H1 Title Only

This is the body content from H1 test.

The H1 heading should be removed from the body.

## Section 1

Some section content.
"""
    md_file = tmp_path / "h1_only_test.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture
def md_with_toc(tmp_path: Path) -> Path:
    """[TOC]プレースホルダー付きMarkdownファイルを作成。

    [TOC]を含む記事はブラウザ経由で作成される。
    """
    content = """---
title: "[E2E-TEST] TOC Article"
tags:
  - e2e-test
  - toc
---

[TOC]

## Section 1

First section content.

## Section 2

Second section content.

## Section 3

Third section content.
"""
    md_file = tmp_path / "toc_test.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture
def md_with_local_image(tmp_path: Path, test_image_path: Path) -> Path:
    """ローカル画像参照付きMarkdownファイルを作成。

    画像ファイルをコピーし、相対パスで参照するMarkdownを作成。
    """
    # Create images directory and copy test image
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    local_image = images_dir / "test.png"
    local_image.write_bytes(test_image_path.read_bytes())

    content = """---
title: "[E2E-TEST] Article with Image"
tags:
  - e2e-test
  - image
---

This article has a local image.

![Test image](./images/test.png)

More content after the image.
"""
    md_file = tmp_path / "image_test.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


class TestCreateFromFile:
    """note_create_from_file MCP tool E2E tests."""

    async def test_create_from_frontmatter_file(
        self,
        real_session: Session,
        md_with_frontmatter: Path,
    ) -> None:
        """YAMLフロントマター付きファイルから記事を作成できる。"""
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_frontmatter),
        )

        # Assert
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] Frontmatter Title" in result
        assert "記事ID:" in result
        assert "記事キー:" in result

    async def test_create_from_h1_only_file(
        self,
        real_session: Session,
        md_with_h1_only: Path,
    ) -> None:
        """H1タイトルのみのファイルから記事を作成できる。"""
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_h1_only),
        )

        # Assert
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] H1 Title Only" in result
        assert "記事ID:" in result

    async def test_create_from_toc_file(
        self,
        real_session: Session,
        md_with_toc: Path,
    ) -> None:
        """[TOC]付きファイルから記事を作成できる（ブラウザ経由）。"""
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_toc),
        )

        # Assert
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] TOC Article" in result
        assert "記事ID:" in result

    async def test_create_with_local_image_upload(
        self,
        real_session: Session,
        md_with_local_image: Path,
    ) -> None:
        """ローカル画像付きファイルから記事を作成し画像をアップロードできる。"""
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_local_image),
            upload_images=True,
        )

        # Assert
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] Article with Image" in result
        assert "アップロードした画像: 1件" in result

    async def test_create_without_image_upload(
        self,
        real_session: Session,
        md_with_local_image: Path,
    ) -> None:
        """upload_images=Falseで画像アップロードをスキップできる。"""
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_local_image),
            upload_images=False,
        )

        # Assert
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] Article with Image" in result
        # Should NOT contain image upload message
        assert "アップロードした画像" not in result


class TestCreateFromFileErrors:
    """note_create_from_file error handling E2E tests."""

    async def test_file_not_found(
        self,
        real_session: Session,
    ) -> None:
        """存在しないファイルでエラーメッセージが返される。"""
        # Act
        result = await note_create_from_file.fn(
            file_path="/nonexistent/path/article.md",
        )

        # Assert
        assert "ファイルが見つかりません" in result

    async def test_file_without_title(
        self,
        real_session: Session,
        tmp_path: Path,
    ) -> None:
        """タイトルなしファイルでエラーメッセージが返される。"""
        # Arrange: Create file without title
        content = """Just some body content without any title.

No headings here at all.
"""
        md_file = tmp_path / "no_title.md"
        md_file.write_text(content, encoding="utf-8")

        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_file),
        )

        # Assert
        assert "ファイル解析エラー" in result or "タイトル" in result

    async def test_missing_local_image(
        self,
        real_session: Session,
        tmp_path: Path,
    ) -> None:
        """存在しないローカル画像を参照した場合の警告。"""
        # Arrange: Create file referencing non-existent image
        content = """---
title: "[E2E-TEST] Missing Image"
---

![Missing](./images/nonexistent.png)

Body content.
"""
        md_file = tmp_path / "missing_image.md"
        md_file.write_text(content, encoding="utf-8")

        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_file),
            upload_images=True,
        )

        # Assert
        assert "下書きを作成しました" in result
        assert "画像アップロード失敗" in result or "ファイルが見つかりません" in result


class TestCreateFromFileNotAuthenticated:
    """Authentication required tests."""

    async def test_not_authenticated(
        self,
        tmp_path: Path,
    ) -> None:
        """未認証状態でログイン要求メッセージが返される。"""
        from note_mcp.auth.session import SessionManager

        # Arrange: Clear session
        session_manager = SessionManager()
        original_session = session_manager.load()
        session_manager.clear()

        try:
            # Create a minimal test file
            content = """# Test Title

Body content.
"""
            md_file = tmp_path / "auth_test.md"
            md_file.write_text(content, encoding="utf-8")

            # Act
            result = await note_create_from_file.fn(
                file_path=str(md_file),
            )

            # Assert
            assert "ログイン" in result

        finally:
            # Restore original session
            if original_session:
                session_manager.save(original_session)
