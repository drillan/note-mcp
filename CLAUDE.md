# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Constitution

このプロジェクトは `.specify/memory/constitution.md` で定義された原則に従います。

**非交渉的原則（例外なし）**:
- **Article 1**: Test-First Imperative - すべての実装はTDDに従う
- **Article 5**: Code Quality Standards - 品質基準の完全遵守
- **Article 6**: Data Accuracy Mandate - 推測・ハードコード禁止
- **Article 7**: DRY Principle - コード重複禁止
- **Article 9**: Python Type Safety Mandate - 包括的な型注釈必須
- **Article 11**: SpecKit Naming Convention - 標準化された命名規則

実装前に必ず constitution を確認してください。

## Development Environment

### Package Management

```bash
# 依存関係のインストール
uv sync

# 開発用依存関係のインストール
uv sync --group dev

# ドキュメント用依存関係のインストール
uv sync --group docs

# すべてのグループをインストール
uv sync --all-groups
```

### Running Tests

```bash
# すべてのテストを実行
uv run pytest

# 特定のテストファイルを実行
uv run pytest tests/path/to/test_file.py

# 詳細出力付きで実行
uv run pytest -v

# 特定のテストを実行
uv run pytest tests/test_file.py::TestClass::test_function -v
```

### Code Quality

```bash
# Linterの実行（自動修正あり）
uv run ruff check --fix .

# フォーマッターの実行
uv run ruff format .

# 型チェックの実行
uv run mypy .

# コミット前の完全チェック（必須）
uv run ruff check --fix . && uv run ruff format . && uv run mypy .
```

設定は `pyproject.toml` に記載されています。

### Type Safety

**Constitution Article 9** に基づき、型安全性は非交渉的要件です。

必須要件:
- すべての関数、メソッド、変数に型アノテーションを付与
- コミット前に `uv run mypy .` を実行
- `Any`型の使用を避け、具体的な型を使用
- 型エラーは無視せず、必ず解決

## MCP Server Development

このプロジェクトはnote.com用のMCPサーバーです。**Constitution Article 3** に従います。

### MCP Protocol Requirements

- MCPツールは明確なスキーマ定義を持つこと
- 入力パラメータはPydanticモデルで検証すること
- エラーレスポンスは適切なMCPエラー形式で返すこと

### Playwright Integration

note.comへのコンテンツ操作は完全にAPI経由で行われます。
Playwright/ブラウザ自動化は**ログイン**と**プレビュー表示**にのみ使用されます。

- ブラウザインスタンスは適切にライフサイクル管理すること
- 作業ウィンドウの再利用を優先すること
- セッション情報はOSのセキュアストレージに保存すること

### ProseMirror Markdown Trigger Pattern

note.comのエディタ（ProseMirror）でMarkdownパターンをHTMLに変換するには、**パターンの後にスペースが必要**です。

**サポートされるMarkdown機能（11種類）:**

| # | 機能 | 入力パターン | トリガー | 出力HTML |
|---|------|------------|---------|----------|
| 1 | 見出しH2 | `## text` | スペース | `<h2>` |
| 2 | 見出しH3 | `### text` | スペース | `<h3>` |
| 3 | 打消し線 | `~~text~~` | スペース | `<s>` |
| 4 | 太字 | `**text**` | スペース | `<strong>` |
| 5 | コードブロック | ` ``` ` | Enter | `<pre><code>` |
| 6 | 中央揃え | `->text<-` | - | `text-align: center` |
| 7 | 右揃え | `->text` | - | `text-align: right` |
| 8 | 目次 | `[TOC]` | - | 目次HTML |
| 9 | 引用 | `> text` | - | `<blockquote>` |
| 10 | 箇条書き | `- text` | - | `<ul><li>` |
| 11 | 番号付き | `1. text` | - | `<ol><li>` |

**サポートされない機能（プラットフォーム制限）:**

| 機能 | 入力パターン | 理由 |
|------|------------|------|
| 斜体 | `*text*` | note.comのProseMirrorスキーマに`em`マークがない |
| インラインコード | `` `code` `` | 同上、`code`マークがない |

**検証済みの動作（2025-12-30）:**

| 入力パターン | 結果 |
|-------------|------|
| `~~text~~ ` (スペースあり) | ✅ `<s>text</s>` に変換 |
| `~~text~~` + Enter | ❌ 変換されない |
| `~~text~~.` (句読点) | ❌ 変換されない |
| `~~text~~` (トリガーなし) | ❌ 変換されない |

**現在のアーキテクチャ:**

note.comへのコンテンツ送信はAPI経由（`markdown_to_html.py`）で行われます。
ブラウザ自動化によるタイピング（旧`typing_helpers.py`）は削除されました。

上記のトリガーパターンは、**ブラウザエディタでの手動入力時の挙動**として
参考情報として残しています。API経由での送信では、HTMLを直接生成するため
これらのトリガーパターンは関係しません。

### Session Management

- 認証状態はセッション管理で適切に維持すること
- セッション期限切れ時は適切なエラーメッセージを返すこと

### Test URLs (実在するURL)

テスト・動作確認時は**必ず以下の実在するURL**を使用すること。架空のURLを生成してはならない。

| サービス | URL |
|---------|-----|
| YouTube | https://www.youtube.com/watch?v=NMHcEDcympM |
| X (Twitter) | https://x.com/patraqushe/status/1326880858007990275 |
| note.com | https://note.com/drillan/n/n7379c02632c9 |

## Available Skills

プロジェクト固有のスキルが `.claude/skills/` に用意されています。

### API Investigation (`api-investigator`)

note.com APIの調査・解析を支援するスキルです。mitmproxyとPlaywrightを使用してHTTPトラフィックをキャプチャ・分析します。

**主な用途:**
- 未ドキュメントのAPIエンドポイント調査
- リクエスト/レスポンスパターンの分析
- 新機能実装前のAPI動作確認

**クイックスタート:**
```bash
# Docker環境で起動
docker compose up --build

# MCPツール経由で使用
# investigator_start_capture → investigator_navigate → investigator_get_traffic
```

**詳細:** `.claude/skills/api-investigator/SKILL.md` を参照

### Other Skills

- **issue-reporter** - 作業進捗をGitHub issueに自動報告
- **code-quality-gate** - コード品質基準の完全遵守を保証
- **constitution-checker** - プロジェクト憲法への準拠を検証
- **tdd-workflow** - TDDワークフローを強制
- **doc-updater** - コード変更時にドキュメントを自動更新
- **mcp-development** - MCPサーバー開発のベストプラクティス

## Development Principles

開発原則の詳細は **Constitution** を参照してください。以下は主要な原則の概要です：

### Issue Workflow

issue対応の指示を受けた場合は、作業開始前に適切なブランチに切り替えること。

**ブランチ命名規則:**
- 機能追加: `feat/<issue番号>-<説明>`
- バグ修正: `fix/<issue番号>-<説明>`
- リファクタリング: `refactor/<issue番号>-<説明>`
- ドキュメント: `docs/<issue番号>-<説明>`

**例:**
```bash
# Issue #123 の機能追加
git checkout -b feat/123-add-user-authentication

# Issue #456 のバグ修正
git checkout -b fix/456-fix-login-error
```

**注意:**
- 既存のブランチがある場合はそちらを使用
- `<説明>`は英語で、ハイフン区切りの短い説明（2-4語）

### Test-Driven Development (Article 1)

1. ユニットテストを先に作成
2. テストをユーザーに承認してもらう
3. テストが失敗する（Redフェーズ）ことを確認
4. 実装してテストを通す（Greenフェーズ）
5. リファクタリング

### Documentation Integrity (Article 2)

- 実装前に仕様を確認
- 仕様が曖昧な場合は実装を停止し、明確化を要求
- ドキュメント変更時はユーザー承認を取得

### Code Quality (Article 5)

- コミット前に品質ツールを実行
- すべてのエラーを解消してからコミット
- 時間制約を理由とした品質妥協は禁止

### Data Accuracy (Article 6)

禁止事項:
- マジックナンバーや固定文字列の直接埋め込み
- 環境依存値の埋め込み
- データ取得失敗時の自動デフォルト値割り当て

### DRY Principle (Article 7)

- 実装前に既存コードを検索・確認
- 3回以上の繰り返しパターンは関数化・モジュール化
- 重複検出時は作業を停止し、リファクタリング計画を立案

## Key Development Guidelines

### Code Style

- **命名規則**: クラスはPascalCase、関数/変数はsnake_case、定数はUPPER_SNAKE_CASE
- **型ヒント**: すべての関数・メソッドに型アノテーション（Article 9）
- **Docstrings**: Google-style形式を推奨（Article 10）
- **行の長さ**: ruff設定に従う
- **インポート**: ruffによる自動ソート

### Documentation Standards

- 公開関数、クラス、モジュールには包括的なdocstringを記載
- Google-style形式を採用
- Docstringは型アノテーションと一致させる

## Documentation

詳細なガイドラインは `@.claude/docs.md` を参照。

### File Locations

- すべてのドキュメント: `docs/*.md`
- ドキュメント設定: `docs/conf.py`
- ビルドシステム: `docs/Makefile`

## Technology Stack

- **Runtime**: Python >= 3.11
- **Package Manager**: uv
- **Testing**: pytest >= 8.4.1
- **Linting/Formatting**: ruff >= 0.12.4
- **Type Checking**: mypy >= 1.19.1
- **Documentation**: Sphinx >= 8.2.3, MyST-Parser >= 4.0.1

## Active Technologies
- Python 3.11+ (pyproject.toml: requires-python = ">=3.11") (001-e2e-native-html-validation)
- N/A (テストコードのみ) (001-e2e-native-html-validation)
- keyring (OS secure storage for session cookies) (002-preview-api)

- Python 3.11+ (001-note-mcp)

## Recent Changes

- 2026-01-13: Removed Playwright-based editor helpers (Issue #131), content operations now API-only
- 2026-01-13: Added Issue Workflow section with branch naming conventions
- 2025-12-31: Added Available Skills section with api-investigator導線
- 001-note-mcp: Added Python 3.11+
- 2025-12-20: Updated CLAUDE.md based on Constitution v1.0.0
