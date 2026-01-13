# 開発ガイド

note-mcpへのコントリビューション方法を説明します。

## 開発環境のセットアップ

### 前提条件

- Python 3.11以上
- uv（パッケージマネージャー）

### セットアップ手順

```bash
# リポジトリのクローン
git clone https://github.com/drillan/note-mcp.git
cd note-mcp

# 依存関係のインストール
uv sync --all-groups

# Playwrightブラウザのインストール
uv run playwright install chromium
```

## コード品質

### Linter・フォーマッター

ruffを使用してコードスタイルを統一しています。

```bash
# Lintチェック
uv run ruff check .

# 自動修正
uv run ruff check --fix .

# フォーマット
uv run ruff format .
```

### 型チェック

mypyで型チェックを行います。

```bash
uv run mypy .
```

### コミット前のチェック

すべてのコードはコミット前に以下のチェックを通過する必要があります：

```bash
uv run ruff check --fix . && uv run ruff format . && uv run mypy .
```

## テスト

### テストの実行

```bash
# 全テストを実行
uv run pytest

# 詳細出力
uv run pytest -v

# 特定のテストを実行
uv run pytest tests/test_file.py::test_function -v
```

### テストのマーカー

特定のテストにはマーカーが付いています：

```bash
# 認証が必要なテストをスキップ
uv run pytest -m "not requires_auth"

# E2Eテストのみ実行
uv run pytest -m e2e

# Dockerが必要なテストをスキップ
uv run pytest -m "not docker"
```

## Docker環境

Investigatorモードの開発にはDocker環境を使用します。

### 起動

```bash
cd docker
docker compose up --build
```

### 環境変数

Docker環境用の環境変数：

| 変数 | 説明 |
|------|------|
| `INVESTIGATOR_MODE=1` | Investigatorモード有効化 |
| `USE_FILE_SESSION=1` | ファイルベースセッション |
| `NOTE_MCP_HEADLESS=true` | ヘッドレスモード |

## プロジェクト構造

```
note-mcp/
├── src/note_mcp/      # ソースコード
├── tests/             # テストコード
├── docs/              # ドキュメント
├── docker/            # Docker設定
├── pyproject.toml     # プロジェクト設定
└── uv.lock            # 依存関係ロック
```

## コントリビューションの流れ

### 1. Issueの確認

- 既存のIssueを確認
- 新しいIssueがあれば作成

### 2. ブランチの作成

```bash
git checkout -b feature/your-feature-name
```

### 3. 開発

- コードを変更
- テストを追加
- ドキュメントを更新

### 4. コミット

```bash
# 品質チェック
uv run ruff check --fix . && uv run ruff format . && uv run mypy .

# テスト
uv run pytest

# コミット
git commit -m "feat: add your feature"
```

### 5. プルリクエスト

- プルリクエストを作成
- レビューを待つ
- 必要に応じて修正

## コミットメッセージ

Conventional Commits形式を使用します：

| プレフィックス | 用途 |
|--------------|------|
| `feat:` | 新機能 |
| `fix:` | バグ修正 |
| `docs:` | ドキュメント |
| `refactor:` | リファクタリング |
| `test:` | テスト |
| `chore:` | その他 |

例：
```
feat: add table of contents support
fix: handle session expiration
docs: update authentication guide
```

## コードスタイル

### 命名規則

| 種類 | 形式 | 例 |
|------|------|-----|
| クラス | PascalCase | `SessionManager` |
| 関数・変数 | snake_case | `get_article` |
| 定数 | UPPER_SNAKE_CASE | `MAX_FILE_SIZE` |

### 型アノテーション

すべての関数・メソッドに型アノテーションを付けます：

```python
def get_article(article_id: str) -> dict[str, Any]:
    ...
```

### Docstring

Google-style形式を使用します：

```python
def create_draft(title: str, body: str) -> str:
    """下書き記事を作成します。

    Args:
        title: 記事のタイトル
        body: 記事の本文（Markdown形式）

    Returns:
        作成された記事のID

    Raises:
        NoteAPIError: API呼び出しに失敗した場合
    """
    ...
```

## ドキュメント

### ドキュメントのビルド

```bash
cd docs
make html
```

ビルドされたドキュメントは`docs/_build/html/`に出力されます。

### ドキュメント構造

```
docs/
├── index.md           # トップページ
├── quickstart.md      # クイックスタート
├── guide/             # ガイド
├── api/               # APIリファレンス
├── features/          # 機能詳細
└── development/       # 開発者向け
```
