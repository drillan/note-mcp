# Quick Start: ネイティブHTML変換検証テスト

**Feature**: `001-e2e-native-html-validation`
**Date**: 2026-01-01

## 前提条件

1. **Python 3.11+** がインストールされている
2. **uv** パッケージマネージャがインストールされている
3. **note.com アカウント** でログイン済み（セッションファイルが存在）
4. **Playwright ブラウザ** がインストールされている

## セットアップ

```bash
# リポジトリのルートに移動
cd /path/to/note-mcp

# 依存関係のインストール
uv sync --group dev

# Playwrightブラウザのインストール
uv run playwright install chromium
```

## セッション準備

```bash
# note.comにログイン（初回のみ）
uv run python -c "from note_mcp.tools.auth import note_login; import asyncio; asyncio.run(note_login())"
```

ブラウザが開くので、note.comにログインしてください。
セッションは自動的に保存されます。

## テスト実行

### 全テスト実行

```bash
# ネイティブHTML変換テストを実行
uv run pytest tests/e2e/test_native_html_validation.py -v
```

### 個別テスト実行

```bash
# 見出し変換テストのみ
uv run pytest tests/e2e/test_native_html_validation.py::TestNativeHeadingConversion -v

# 打消し線テストのみ
uv run pytest tests/e2e/test_native_html_validation.py::TestNativeStrikethroughConversion -v

# コードブロックテストのみ
uv run pytest tests/e2e/test_native_html_validation.py::TestNativeCodeBlockConversion -v
```

### 特定のテストケース

```bash
# H2見出しのみ
uv run pytest tests/e2e/test_native_html_validation.py::TestNativeHeadingConversion::test_h2_native_conversion -v
```

## テスト構造

```
tests/e2e/
├── conftest.py                    # fixturesの定義
│   ├── real_session              # 認証済みセッション
│   ├── draft_article             # テスト用下書き記事
│   └── editor_page               # 🆕 エディタページ
├── helpers/
│   ├── validation.py              # PreviewValidator
│   └── typing_helpers.py          # 🆕 キーボード入力ヘルパー
├── test_markdown_conversion.py    # 既存: API経由テスト
└── test_native_html_validation.py # 🆕 ネイティブHTML検証テスト
```

## テストフロー

1. **editor_page fixture**
   - ブラウザを起動
   - セッションCookieを注入
   - エディタページを開く
   - ProseMirrorの表示を待機

2. **テスト実行**
   ```python
   async def test_h2_native_conversion(self, editor_page, preview_page):
       # Step 1: エディタに直接Markdown入力
       await type_markdown_pattern(editor_page, "## テスト見出し")

       # Step 2: プレビューページに遷移
       await navigate_to_preview(editor_page)

       # Step 3: ネイティブHTMLを検証
       validator = PreviewValidator(preview_page)
       result = await validator.validate_heading(2, "テスト見出し")
       assert result.success
   ```

3. **クリーンアップ**
   - ブラウザを閉じる
   - テスト用記事はそのまま（再利用可能）

## トラブルシューティング

### セッション期限切れ

```
Error: 認証が必要です
```

**解決**: 再度ログインコマンドを実行

```bash
uv run python -c "from note_mcp.tools.auth import note_login; import asyncio; asyncio.run(note_login())"
```

### エディタ要素が見つからない

```
TimeoutError: Timeout 30000ms exceeded waiting for selector ".ProseMirror"
```

**解決**:
1. ネットワーク接続を確認
2. note.comの障害情報を確認
3. タイムアウト値を増やして再実行

### 変換が発動しない

```
AssertionError: expected <h2> but got plain text
```

**解決**: ProseMirrorのトリガーパターンを確認

- 見出し: `## text ` (スペースで変換)
- 打消し線: `~~text~~ ` (スペースで変換)
- コードブロック: ```` ``` ```` + スペース

## 既存テストとの違い

| 観点 | 既存テスト | ネイティブHTML検証テスト |
|-----|----------|------------------------|
| **入力方法** | API (`update_article`) | キーボード入力 |
| **HTML生成** | `markdown_to_html()` | ProseMirror（note.comネイティブ） |
| **検証対象** | 自己生成HTML | プラットフォーム生成HTML |
| **トートロジー** | あり | なし ✅ |

## 次のステップ

1. すべてのP1テストケースが通ることを確認
2. P2テストケース（コードブロック、配置）を追加
3. CI/CDパイプラインに統合
