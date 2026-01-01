# Contract: type_markdown_pattern()

**Feature**: `001-e2e-native-html-validation`
**Type**: ヘルパー関数
**Location**: `tests/e2e/helpers/typing_helpers.py`

## 概要

Markdownパターンをエディタに入力し、ProseMirror変換をトリガーする。
既存の`src/note_mcp/browser/typing_helpers.py`のパターンを参考に、テスト用に簡素化。

## 署名

```python
async def type_markdown_pattern(
    page: Page,
    pattern: str,
    trigger: str = " ",
    wait_time: float = 0.1,
) -> None:
    """Markdownパターンをエディタに入力しProseMirror変換をトリガー。

    Args:
        page: Playwright Pageインスタンス
        pattern: 入力するMarkdownパターン（例: "## 見出し", "~~打消し~~"）
        trigger: 変換トリガー（デフォルトはスペース）
        wait_time: 変換待機時間（秒）

    Raises:
        ValueError: patternが空の場合
        TimeoutError: エディタ要素が見つからない場合
    """
```

## 前提条件

1. `page` はエディタページを表示している
2. `.ProseMirror` 要素が表示されフォーカス可能
3. `pattern` は空でない文字列

## 事後条件

1. `pattern` がエディタに入力されている
2. `trigger` が入力されている（変換をトリガー）
3. `wait_time` 秒待機し変換完了を待つ

## 動作仕様

### 見出し変換

```python
# 入力: "## テスト見出し"
# 動作:
#   1. "## テスト見出し" をタイプ
#   2. " " をタイプ（トリガー）
#   3. 0.1秒待機
# 結果: <h2>テスト見出し</h2>

await type_markdown_pattern(page, "## テスト見出し")
```

### 打消し線変換

```python
# 入力: "~~打消しテキスト~~"
# 動作:
#   1. "~~打消しテキスト~~" をタイプ
#   2. " " をタイプ（トリガー）
#   3. 0.1秒待機
# 結果: <s>打消しテキスト</s>

await type_markdown_pattern(page, "~~打消しテキスト~~")
```

### コードブロック変換

```python
# 入力: "```"
# 動作:
#   1. "```" をタイプ
#   2. " " をタイプ（トリガー）
#   3. 0.1秒待機
# 結果: <pre><code></code></pre> ブロック開始

await type_markdown_pattern(page, "```")
# その後、コード内容を入力
await page.keyboard.type("console.log('test')")
```

## 実装例

```python
import asyncio
from playwright.async_api import Page


async def type_markdown_pattern(
    page: Page,
    pattern: str,
    trigger: str = " ",
    wait_time: float = 0.1,
) -> None:
    """Markdownパターンをエディタに入力しProseMirror変換をトリガー。"""
    if not pattern:
        raise ValueError("pattern cannot be empty")

    # エディタにフォーカス
    editor = page.locator(".ProseMirror").first
    await editor.click()

    # パターンを入力
    await page.keyboard.type(pattern)

    # トリガーを入力（スペースでMarkdown変換発動）
    if trigger:
        await page.keyboard.type(trigger)

    # 変換完了を待機
    await asyncio.sleep(wait_time)
```

## エラー処理

| エラー条件 | 期待される動作 |
|-----------|---------------|
| patternが空 | `ValueError` 発生 |
| エディタ要素なし | `TimeoutError` 発生 |
| フォーカス失敗 | Playwright例外 |

## テスト

```python
async def test_type_markdown_pattern_heading(editor_page: Page) -> None:
    """見出しパターンが正しく入力されることを確認。"""
    await type_markdown_pattern(editor_page, "## テスト見出し")

    # エディタ内のHTMLを確認
    editor = editor_page.locator(".ProseMirror").first
    html = await editor.inner_html()
    assert "<h2>" in html or "テスト見出し" in html


async def test_type_markdown_pattern_strikethrough(editor_page: Page) -> None:
    """打消し線パターンが正しく入力されることを確認。"""
    await type_markdown_pattern(editor_page, "~~打消し~~")

    editor = editor_page.locator(".ProseMirror").first
    html = await editor.inner_html()
    assert "<s>" in html or "打消し" in html
```

## 既存コードとの関係

| 既存関数 | 本関数との違い |
|---------|---------------|
| `_type_with_strikethrough()` | 打消し線専用、後続コンテンツ処理あり |
| `type_markdown_content()` | 複数行対応、リスト・blockquote対応 |

本関数は単一パターンのテスト用に簡素化。
