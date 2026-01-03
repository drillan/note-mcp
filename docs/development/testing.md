# テスト

note-mcpのテスト戦略と実行方法について説明します。

## テストの種類

| 種類 | 場所 | 説明 |
|------|------|------|
| ユニットテスト | `tests/unit/` | 個別モジュールの単体テスト |
| 統合テスト | `tests/integration/` | 複数モジュール間の結合テスト |
| E2Eテスト | `tests/e2e/` | 実環境でのエンドツーエンドテスト |

## テストの実行

### 基本的な実行

```bash
# すべてのテストを実行
uv run pytest

# 詳細出力で実行
uv run pytest -v

# 特定のテストを実行
uv run pytest tests/unit/test_markdown.py::test_heading -v
```

### マーカーによるフィルタリング

```bash
# E2Eテストのみ実行
uv run pytest -m e2e

# 認証が必要なテストをスキップ
uv run pytest -m "not requires_auth"

# Dockerが必要なテストをスキップ
uv run pytest -m "not docker"
```

## E2Eテスト

E2Eテストは実際のnote.com環境で記事操作とMarkdown変換を検証します。

### セットアップ

#### 1. 環境変数の設定

プロジェクトルートに`.env`ファイルを作成し、認証情報を設定します：

```bash
# .env
NOTE_USERNAME=your_username
NOTE_PASSWORD=your_password
```

> **重要**: `.env`ファイルはgitにコミットしないでください。`.gitignore`で除外されています。

#### 2. dotenvxの使用（推奨）

[dotenvx](https://dotenvx.com/)を使用すると、環境変数を暗号化して安全に管理できます：

```bash
# dotenvxのインストール
npm install -g @dotenvx/dotenvx

# .envを暗号化
dotenvx encrypt

# テスト実行時に復号化
dotenvx run -- uv run pytest tests/e2e/ -v
```

### 自動ログイン動作

E2Eテストの`real_session`フィクスチャは以下の優先順位でセッションを取得します：

1. **保存済みセッション**: 有効期限内のセッションがあれば使用
2. **自動ログイン**: 環境変数（`NOTE_USERNAME`, `NOTE_PASSWORD`）があれば自動ログイン
3. **手動ログイン**: どちらもない場合は手動ログイン待機（300秒タイムアウト）

CI/CD環境では環境変数を設定することで、完全自動でE2Eテストを実行できます。

#### LoginError発生時の動作

自動ログイン中にreCAPTCHAや2FAが検出されると、`LoginError`例外が発生し、テストはスキップされます：

```
SKIPPED: E2Eテスト用セッション取得失敗: reCAPTCHAが検出されました
```

この場合は、手動でログインしてセッションを保存してください。詳細は[認証ガイド](../guide/authentication.md#loginerror例外)を参照してください。

### E2Eテストの実行

```bash
# すべてのE2Eテストを実行
uv run pytest tests/e2e/ -v

# 特定のテストを実行
uv run pytest tests/e2e/test_markdown_conversion.py -v

# 失敗時に詳細情報を表示
uv run pytest tests/e2e/ -v --tb=short
```

### テスト記事のライフサイクル

E2Eテストは以下のパターンで記事を管理します：

1. **作成**: テスト開始時に`[E2E-TEST-{timestamp}]`プレフィックス付きで下書き作成
2. **検証**: プレビューページのHTML要素でMarkdown変換を検証
3. **削除**: テスト終了後に自動クリーンアップ（ベストエフォート）

### Markdown変換テスト

Markdown変換テストは以下の要素を検証します：

| 要素 | 入力例 | 検証内容 |
|------|--------|----------|
| 見出しH2 | `## 見出し` | `<h2>`要素として変換される |
| 見出しH3 | `### 見出し` | `<h3>`要素として変換される |
| 打消し線 | `~~text~~` | `<s>`要素として変換される |
| コードブロック | ` ```code``` ` | `<pre><code>`要素として変換される |
| 中央配置 | `->text<-` | `text-align: center`スタイルが適用される |
| 右配置 | `->text` | `text-align: right`スタイルが適用される |

### ネイティブHTML検証テスト

通常のMarkdown変換テストに加えて、ネイティブHTML検証テストを提供しています。

#### 背景：トートロジー問題

従来のE2Eテストには「トートロジー」問題がありました：

- `update_article()` が内部で `markdown_to_html()` を使用してHTMLを生成
- 生成されたHTMLがそのままプレビューページに表示される
- つまり「自己生成HTMLを自己検証している」状態

これではnote.comプラットフォームが実際に生成するHTMLを検証できません。

#### ネイティブ検証アプローチ

ネイティブHTML検証テストは、この問題を解決します：

1. **エディタに直接入力**: キーボード操作でMarkdown記法をエディタに入力
2. **ProseMirror変換**: スペースをトリガーにProseMirrorがMarkdownを変換
3. **保存とプレビュー**: 変換結果を保存し、プレビューページを開く
4. **ネイティブHTML検証**: note.comが生成したHTMLを検証

これにより、実際のユーザー体験を反映したテストが可能になります。

#### ネイティブ検証テストの実行

```bash
# 見出し変換テスト
uv run pytest tests/e2e/test_native_html_validation.py::TestNativeHeadingConversion -v

# 打消し線変換テスト
uv run pytest tests/e2e/test_native_html_validation.py::TestNativeStrikethroughConversion -v

# すべてのネイティブ検証テスト
uv run pytest tests/e2e/test_native_html_validation.py -v
```

#### テストケース一覧

| テストケース | 優先度 | 入力 | 期待結果 |
|-------------|--------|------|----------|
| H2見出し | P1 | `## text` + スペース | `<h2>text</h2>` |
| H3見出し | P1 | `### text` + スペース | `<h3>text</h3>` |
| 打消し線 | P1 | `~~text~~` + スペース | `<s>text</s>` |
| コードブロック | P2 | ` ``` ` | `<pre><code>` |
| 中央揃え | P2 | `->text<-` | `text-align: center` |
| 右揃え | P2 | `->text` | `text-align: right` |

## MCPツールテスト

MCPツールテストは、note-mcpが提供する11個のMCPツールの動作を検証するE2Eテストです。

### 対象ツール

| カテゴリ | ツール | 説明 |
|----------|--------|------|
| 認証フロー | `note_login` | ブラウザでnote.comにログイン |
| | `note_check_auth` | 認証状態を確認 |
| | `note_logout` | セッションをクリア |
| | `note_set_username` | ユーザー名を設定 |
| 記事CRUD | `note_create_draft` | 下書き記事を作成 |
| | `note_get_article` | 記事の内容を取得 |
| | `note_update_article` | 記事を更新 |
| | `note_list_articles` | 記事一覧を取得 |
| 画像操作 | `note_upload_eyecatch` | アイキャッチ画像をアップロード |
| | `note_upload_body_image` | 本文用画像をアップロード |
| プレビュー | `note_show_preview` | 記事のプレビューを表示 |

> **Note**: `note_insert_body_image`はProseMirror状態への複雑な依存があるため、[別issue #53](https://github.com/drillan/note-mcp/issues/53)で対応しています。

### MCPツールテストの実行

```bash
# すべてのMCPツールテストを実行
uv run pytest tests/e2e/test_mcp_tools.py -v

# 認証フローテストのみ
uv run pytest tests/e2e/test_mcp_tools.py::TestAuthenticationFlow -v

# 記事CRUDテストのみ
uv run pytest tests/e2e/test_mcp_tools.py::TestArticleCRUD -v

# 画像操作テストのみ
uv run pytest tests/e2e/test_mcp_tools.py::TestImageOperations -v

# プレビューテストのみ
uv run pytest tests/e2e/test_mcp_tools.py::TestPreviewOperations -v
```

### テストの依存関係

MCPツールテストは以下の順序で実行する必要があります：

1. **認証フロー** (`TestAuthenticationFlow`)
   - 他のすべてのテストの前提条件
   - `note_login` → `note_check_auth` → `note_logout` の順で検証

2. **記事CRUD** (`TestArticleCRUD`)
   - 認証済み状態が必要
   - `note_create_draft` → `note_get_article` → `note_update_article` → `note_list_articles`

3. **画像操作** (`TestImageOperations`)
   - 認証済み状態と下書き記事が必要
   - テスト用画像ファイルが必要

4. **プレビュー** (`TestPreviewOperations`)
   - 認証済み状態と下書き記事が必要

### テストデータ

テストで使用するサンプルデータ：

```python
# tests/e2e/conftest.py で定義
test_image_path = Path(__file__).parent / "assets" / "test_image.png"  # 100x100 PNG画像
```

### 技術詳細

#### FunctionToolオブジェクトについて

`@mcp.tool()`デコレータは関数を`FunctionTool`オブジェクトにラップします。テストでMCPツール関数を直接呼び出す場合は、`.fn`属性経由で元の関数にアクセスする必要があります：

```python
# ❌ 動作しない（FunctionToolは直接呼び出せない）
result = await note_check_auth()

# ✅ 正しい呼び出し方法
result = await note_check_auth.fn()
```

詳細は`tests/e2e/test_mcp_tools.py`のdocstringを参照してください。

### トラブルシューティング

#### 認証エラー

**症状**:
```
セッションが無効です
```

**解決方法**:
- 環境変数が正しく設定されているか確認
- dotenvxを使用している場合は`dotenvx run --`を付けて実行

#### テスト記事が残る

**症状**:
- テスト後に`[E2E-TEST-...]`プレフィックスの下書きが残っている

**解決方法**:
- テストが中断された場合、手動でダッシュボードから削除
- 正常終了時は自動削除されるが、ネットワークエラー等でスキップされる場合がある

#### プレビュー検証の失敗

**症状**:
```
Expected element not found: h2#heading-text
```

**解決方法**:
- note.comのエディタ仕様変更の可能性
- プレビューURLをログで確認し、ブラウザで目視確認
- セレクタが最新のDOM構造と一致しているか確認

## Docker環境でのテスト

### Headlessモード

```bash
docker compose run --rm test
```

### Headedモード（Xvfb使用）

```bash
docker compose run --rm test-headed
```

### VNC経由での視覚確認

```bash
# VNC環境起動
docker compose up -d test-vnc

# VNCクライアントでアクセス
vncviewer localhost:5900
```

> **Note**: `test-vnc`サービスはVNCポート(5900)のみ公開しています。
> noVNC (http://localhost:6080) を使用する場合は`dev`サービスを利用してください。

詳細は[README.md](../../README.md#docker)を参照してください。

## カバレッジ

```bash
# カバレッジレポート生成
uv run pytest --cov=src/note_mcp --cov-report=html

# レポートを表示
open htmlcov/index.html
```

## CI環境

GitHub Actionsでは以下の構成でテストが実行されます：

- ユニットテスト・統合テスト: 毎コミット
- E2Eテスト: 手動トリガーまたはリリース前

> **Note**: E2EテストはCI環境で実行するには認証情報のSecrets設定が必要です。
