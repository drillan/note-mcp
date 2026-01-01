# Research: E2Eテスト - ネイティブHTML変換検証

**Feature**: `001-e2e-native-html-validation`
**Date**: 2026-01-01
**Phase**: 0 - Research

## Executive Summary

既存のE2Eテストインフラは成熟しており、**ネイティブHTML検証テストの実装に必要な基盤がすでに存在する**。主な作業は既存コンポーネントの組み合わせと、エディタ直接入力のためのfixtureの追加のみ。

## 1. トートロジー問題の詳細分析

### 現状（tests/e2e/test_markdown_conversion.py）

```python
# 現在のテスト構造（トートロジー）
async def test_h2_conversion(self, ...):
    # Step 1: update_article() → 内部で markdown_to_html() が呼ばれる
    await update_article(real_session, draft_article.id, article_input)

    # Step 2: プレビューページのHTMLを検証
    validator = PreviewValidator(preview_page)
    result = await validator.validate_heading(2, test_text)
```

**問題点**:
- `update_article()` は内部で `markdown_to_html()` を呼び出してHTMLを生成
- プレビューページには `markdown_to_html()` が生成したHTMLがそのまま表示される
- これは「自分で生成したHTMLを自分で検証する」トートロジー

### 解決策

```python
# ネイティブHTML検証テスト（新アプローチ）
async def test_h2_native_conversion(self, ...):
    # Step 1: エディタに直接Markdown入力（キーボード操作）
    await editor_page.keyboard.type("## テスト見出し ")

    # Step 2: ProseMirrorがネイティブにHTMLを生成

    # Step 3: プレビューページでnote.com生成HTMLを検証
    validator = PreviewValidator(preview_page)
    result = await validator.validate_heading(2, "テスト見出し")
```

## 2. 既存インフラの評価

### 2.1 再利用可能なコンポーネント

| コンポーネント | 場所 | 再利用方法 |
|--------------|------|-----------|
| **SessionManager** | `src/note_mcp/auth/session.py` | ✅ そのまま使用 |
| **real_session fixture** | `tests/e2e/conftest.py` | ✅ そのまま使用 |
| **draft_article fixture** | `tests/e2e/conftest.py` | ✅ そのまま使用 |
| **PreviewValidator** | `tests/e2e/helpers/validation.py` | ✅ そのまま使用 |
| **typing_helpers** | `src/note_mcp/browser/typing_helpers.py` | 🔧 参照パターンとして活用 |

### 2.2 追加が必要なコンポーネント

| コンポーネント | 用途 | 複雑度 |
|--------------|------|--------|
| **editor_page fixture** | エディタページへのアクセス | 中 |
| **type_markdown_to_editor()** | キーボードでMarkdown入力 | 低 |
| **wait_for_prosemirror_conversion()** | 変換完了待機 | 低 |

## 3. ProseMirrorトリガーパターン詳細

### 3.1 検証済みパターン（CLAUDE.mdから）

| 入力 | トリガー | 結果 |
|-----|---------|------|
| `~~text~~` + スペース | ✅ | `<s>text</s>` |
| `~~text~~` + Enter | ❌ | プレーンテキスト |
| `## text` + スペース | ✅ | `<h2>text</h2>` |
| `### text` + スペース | ✅ | `<h3>text</h3>` |
| ``` ` ` ` ``` + スペース | ✅ | `<pre><code>` |

### 3.2 既存実装からの知見

`typing_helpers.py` の `_type_with_strikethrough()` から:

```python
# スペースでトリガー
await page.keyboard.type(f"~~{part}~~")
await page.keyboard.type(" ")  # 変換トリガー
await asyncio.sleep(0.1)  # 変換待機
# 不要なスペースを削除
if has_more_content:
    await page.keyboard.press("Backspace")
```

## 4. テスト設計

### 4.1 テストケース一覧

| カテゴリ | 記法 | 期待HTML | 優先度 |
|---------|------|----------|--------|
| 見出し | `## text` | `<h2>text</h2>` | P1 |
| 見出し | `### text` | `<h3>text</h3>` | P1 |
| 打消し線 | `~~text~~` | `<s>text</s>` | P1 |
| コードブロック | ``` ` ` ` ``` | `<pre><code>` | P2 |
| 中央揃え | `->text<-` | `text-align: center` | P2 |
| 右揃え | `->text` | `text-align: right` | P2 |

### 4.2 テストファイル構造

```python
# tests/e2e/test_native_html_validation.py

class TestNativeHeadingConversion:
    """ネイティブ見出し変換テスト"""

    async def test_h2_native_conversion(self, editor_page, preview_page):
        # エディタに直接入力
        await type_markdown_pattern(editor_page, "## テスト見出し")

        # プレビューで検証
        await navigate_to_preview(editor_page)
        result = await validator.validate_heading(2, "テスト見出し")
        assert result.success

class TestNativeStrikethroughConversion:
    """ネイティブ打消し線変換テスト"""
    ...

class TestNativeCodeBlockConversion:
    """ネイティブコードブロック変換テスト"""
    ...

class TestNativeAlignmentConversion:
    """ネイティブテキスト配置変換テスト"""
    ...
```

## 5. 実装アプローチ

### 5.1 editor_page fixture

```python
@pytest_asyncio.fixture
async def editor_page(
    real_session: Session,
    draft_article: Article,
) -> AsyncGenerator[Page, None]:
    """エディタページを開いた状態のブラウザページ。"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # セッション注入
        await _inject_session_cookies(page, real_session)

        # エディタページへ移動
        editor_url = f"https://editor.note.com/notes/{draft_article.key}/edit/"
        await page.goto(editor_url)

        # ProseMirrorエディタ要素を待機
        await page.locator(".ProseMirror").wait_for(state="visible")

        yield page

        await context.close()
        await browser.close()
```

### 5.2 キーボード入力ヘルパー

```python
async def type_markdown_pattern(
    page: Page,
    pattern: str,
    trigger: str = " ",  # デフォルトはスペーストリガー
) -> None:
    """Markdownパターンをエディタに入力しProseMirror変換をトリガー。"""
    await page.keyboard.type(pattern)
    await page.keyboard.type(trigger)
    await asyncio.sleep(0.1)  # 変換待機
```

## 6. リスク評価

### 6.1 技術的リスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| ProseMirror変換タイミング | 中 | 適切な待機時間（0.1-0.3秒） |
| エディタフォーカス喪失 | 低 | .ProseMirror.click()で再フォーカス |
| ネットワーク遅延 | 低 | 既存のタイムアウト設定を使用 |

### 6.2 テスト安定性

既存E2Eテストが安定稼働しているため、同じインフラを使用することで安定性を確保。

## 7. 成果物一覧

Phase 0完了時点で確認済み:

1. ✅ 既存インフラで十分対応可能
2. ✅ ProseMirrorトリガーパターン検証済み
3. ✅ テストケース設計完了
4. ✅ 実装アプローチ確定

## 8. Phase 1への引き継ぎ事項

- **data-model.md**: テストケース・検証結果のデータモデル定義
- **contracts/**: editor_page fixture、type_markdown_pattern()の契約定義
- **quickstart.md**: テスト実行手順のクイックスタートガイド
