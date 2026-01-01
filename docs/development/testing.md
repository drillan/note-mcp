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

# noVNCでアクセス
# http://localhost:6080/vnc.html
```

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
