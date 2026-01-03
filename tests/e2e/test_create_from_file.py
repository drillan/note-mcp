"""E2E tests for note_create_from_file MCP tool.

Tests creating note.com articles from Markdown files.
Covers frontmatter, H1-based titles, local image handling, and error cases.

Each test validates:
1. API response contains expected success message
2. Preview page shows correctly converted HTML

Run with: uv run pytest tests/e2e/test_create_from_file.py -v
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.async_api import async_playwright

from note_mcp.server import note_create_from_file
from tests.e2e.conftest import _inject_session_cookies
from tests.e2e.helpers import (
    ImageValidator,
    PreviewValidator,
    extract_article_key,
    open_preview_for_article_key,
)

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


@pytest.fixture
def md_with_math(tmp_path: Path) -> Path:
    """数式を含むMarkdownファイルを作成。

    インライン数式とディスプレイ数式の両方を含む。
    """
    content = """---
title: "[E2E-TEST] Article with Math"
tags:
  - e2e-test
  - math
---

This article demonstrates math formulas.

## Inline Math

The famous equation $${E = mc^2}$$ shows mass-energy equivalence.

## Display Math

The quadratic formula:

$$
x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
$$

More content after math.
"""
    md_file = tmp_path / "math_test.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture
def md_with_toc_and_image(tmp_path: Path, test_image_path: Path) -> Path:
    """[TOC]と画像を含むMarkdownファイルを作成。

    目次生成と画像アップロードの組み合わせをテスト。
    """
    # Create images directory and copy test image
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    local_image = images_dir / "test.png"
    local_image.write_bytes(test_image_path.read_bytes())

    content = """---
title: "[E2E-TEST] TOC with Image"
tags:
  - e2e-test
  - toc
  - image
---

[TOC]

## Section 1

First section content.

![Test image](./images/test.png)

## Section 2

Second section content.

## Section 3

Third section content.
"""
    md_file = tmp_path / "toc_image_test.md"
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
        """[TOC]付きファイルから記事を作成できる（ブラウザ経由）。

        プレビューページで目次HTMLが正しく生成されることを検証。
        """
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_toc),
        )

        # Assert API response
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] TOC Article" in result
        assert "記事ID:" in result

        # Validate preview page
        article_key = extract_article_key(result)

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await _inject_session_cookies(page, real_session)
            preview_page = await open_preview_for_article_key(page, article_key)

            validator = PreviewValidator(preview_page)
            toc_result = await validator.validate_toc()
            assert toc_result.success, f"TOC validation failed: {toc_result.message}"
        finally:
            await context.close()
            await browser.close()
            await playwright.stop()

    async def test_create_from_math_file(
        self,
        real_session: Session,
        md_with_math: Path,
    ) -> None:
        """数式付きファイルから記事を作成し、KaTeXレンダリングを検証。"""
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_math),
        )

        # Assert API response
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] Article with Math" in result
        assert "記事ID:" in result

        # Validate preview page
        article_key = extract_article_key(result)

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await _inject_session_cookies(page, real_session)
            preview_page = await open_preview_for_article_key(page, article_key)

            validator = PreviewValidator(preview_page)

            # Verify math is rendered by KaTeX
            math_result = await validator.validate_math()
            assert math_result.success, f"Math validation failed: {math_result.message}"

            # Verify specific formulas are present
            inline_result = await validator.validate_math("E = mc")
            assert inline_result.success, f"Inline math validation failed: {inline_result.message}"

        finally:
            await context.close()
            await browser.close()
            await playwright.stop()

    async def test_create_with_local_image_upload(
        self,
        real_session: Session,
        md_with_local_image: Path,
    ) -> None:
        """ローカル画像付きファイルから記事を作成し画像をアップロードできる。

        プレビューページで画像が正しく表示されることを検証。
        """
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_local_image),
            upload_images=True,
        )

        # Assert API response
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] Article with Image" in result
        assert "アップロードした画像: 1件" in result

        # Validate preview page
        article_key = extract_article_key(result)

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await _inject_session_cookies(page, real_session)
            preview_page = await open_preview_for_article_key(page, article_key)

            image_validator = ImageValidator(preview_page)

            # Verify image is displayed on preview page
            image_result = await image_validator.validate_image_exists(expected_count=1)
            assert image_result.success, f"Image validation failed: {image_result.message}"

        finally:
            await context.close()
            await browser.close()
            await playwright.stop()

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

    async def test_create_from_toc_and_image_file(
        self,
        real_session: Session,
        md_with_toc_and_image: Path,
    ) -> None:
        """[TOC]と画像を含むファイルから記事を作成し、両方を検証。

        目次生成と画像アップロードの組み合わせをテスト。
        プレビューページで両方が正しく表示されることを検証。
        """
        # Act
        result = await note_create_from_file.fn(
            file_path=str(md_with_toc_and_image),
            upload_images=True,
        )

        # Assert API response
        assert "下書きを作成しました" in result
        assert "[E2E-TEST] TOC with Image" in result
        assert "アップロードした画像: 1件" in result

        # Validate preview page
        article_key = extract_article_key(result)

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await _inject_session_cookies(page, real_session)
            preview_page = await open_preview_for_article_key(page, article_key)

            preview_validator = PreviewValidator(preview_page)
            image_validator = ImageValidator(preview_page)

            # Verify TOC is displayed
            toc_result = await preview_validator.validate_toc()
            assert toc_result.success, f"TOC validation failed: {toc_result.message}"

            # Verify image is displayed
            image_result = await image_validator.validate_image_exists(expected_count=1)
            assert image_result.success, f"Image validation failed: {image_result.message}"

        finally:
            await context.close()
            await browser.close()
            await playwright.stop()


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
