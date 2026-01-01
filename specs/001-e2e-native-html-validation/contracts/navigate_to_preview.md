# Contract: navigate_to_preview()

**Feature**: `001-e2e-native-html-validation`
**Type**: ヘルパー関数
**Location**: `tests/e2e/helpers/typing_helpers.py`

## 概要

エディタページからプレビューページに遷移し、プレビューが表示されるまで待機。
記事を保存してからプレビューを開く。

## 署名

```python
async def navigate_to_preview(
    editor_page: Page,
    article_key: str,
    timeout: float = 30.0,
) -> Page:
    """エディタからプレビューページに遷移。

    Args:
        editor_page: エディタを表示しているPage
        article_key: 記事キー（例: "n1234567890ab"）
        timeout: ページ読み込みタイムアウト（秒）

    Returns:
        Page: プレビューページを表示しているPage

    Raises:
        TimeoutError: プレビューページが読み込めない場合
    """
```

## 前提条件

1. `editor_page` はエディタを表示している
2. 記事内容がエディタに入力されている
3. `article_key` は有効な記事キー

## 事後条件

1. 記事が下書き保存されている
2. プレビューページが表示されている
3. 記事本文が表示されている

## 動作仕様

### 遷移フロー

```
1. 下書き保存ボタンをクリック
2. 保存完了を待機
3. プレビューURLに遷移
4. 記事本文の表示を待機
```

## 実装例

```python
import asyncio
from playwright.async_api import Page


async def navigate_to_preview(
    editor_page: Page,
    article_key: str,
    timeout: float = 30.0,
) -> Page:
    """エディタからプレビューページに遷移。"""
    # 下書き保存（Ctrl+S または保存ボタン）
    await editor_page.keyboard.press("Control+s")
    await asyncio.sleep(1.0)  # 保存完了待機

    # プレビューURLに遷移
    preview_url = f"https://note.com/api/v1/notes/{article_key}/preview"
    # 実際のプレビューURLは記事のアクセスキーを使用
    # ここでは note_show_preview MCP ツールを使用することも可能

    # 新しいタブでプレビューを開くパターン
    async with editor_page.context.expect_page() as page_info:
        # プレビューボタンをクリック（または直接遷移）
        await editor_page.goto(preview_url)

    preview_page = await page_info.value

    # 記事本文が表示されるまで待機
    await preview_page.wait_for_selector(
        "article, .note-common-styles__textnote-body",
        timeout=timeout * 1000,
    )

    return preview_page
```

## 代替実装: MCP経由

```python
async def navigate_to_preview_via_mcp(
    editor_page: Page,
    article_key: str,
    real_session: Session,
) -> Page:
    """MCP note_show_preview ツール経由でプレビューに遷移。"""
    from note_mcp.tools.articles import note_show_preview

    # 下書き保存
    await editor_page.keyboard.press("Control+s")
    await asyncio.sleep(1.0)

    # MCP経由でプレビュー表示
    result = await note_show_preview(article_key)

    # ブラウザコンテキストから新しいページを取得
    pages = editor_page.context.pages
    preview_page = pages[-1]  # 最後に開かれたページ

    return preview_page
```

## エラー処理

| エラー条件 | 期待される動作 |
|-----------|---------------|
| 保存失敗 | 保存エラー表示、テスト失敗 |
| プレビューページ読み込み失敗 | `TimeoutError` 発生 |
| 記事が存在しない | 404エラー、テスト失敗 |

## テスト

```python
async def test_navigate_to_preview(
    editor_page: Page,
    draft_article: Article,
) -> None:
    """プレビュー遷移が正しく動作することを確認。"""
    # テスト用コンテンツを入力
    await type_markdown_pattern(editor_page, "## テスト見出し")

    # プレビューに遷移
    preview_page = await navigate_to_preview(
        editor_page,
        draft_article.key,
    )

    # プレビューページが表示されている
    assert preview_page is not None
    assert "preview" in preview_page.url or "note.com" in preview_page.url
```
