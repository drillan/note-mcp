# Code Implementation Plan: note.com MCP Server

**Generated**: 2025-12-20
**Based on**: Phase 1 plan + Phase 2 documentation
**Feature Branch**: `001-note-mcp`

---

## Summary

note.com MCPサーバーをゼロから実装します。現在は`main.py`のプレースホルダーのみ存在し、全モジュール構造を新規作成します。

**実装範囲**:
- 8つのMCPツール（認証3、記事4、画像1）
- ハイブリッドアプローチ（API + ブラウザUI）
- keyringによるセキュアセッション管理
- Playwrightによるブラウザ自動化

---

## Files to Create

### Core Package Structure

#### File: `src/note_mcp/__init__.py`

**Purpose**: パッケージ初期化、公開APIのエクスポート
**Exports**: `mcp`, `__version__`
**Dependencies**: なし
**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/__main__.py`

**Purpose**: `python -m note_mcp`でサーバー起動可能にする
**Exports**: なし（エントリーポイント）
**Dependencies**: `server.py`
**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/server.py`

**Purpose**: FastMCPサーバー定義、全MCPツールの登録
**FR Coverage**: All tools entry point
**Exports**: `mcp` (FastMCPインスタンス)
**Dependencies**:
- `auth/session.py`
- `auth/browser.py`
- `api/articles.py`
- `api/images.py`
- `browser/preview.py`
**Agent Suggestion**: modular-builder

**Specific Implementation**:
```python
from fastmcp import FastMCP
mcp = FastMCP("note-mcp")

# Register all tools:
# - note_login, note_check_auth, note_logout
# - note_create_draft, note_update_article, note_publish_article, note_list_articles
# - note_upload_image
```

---

### Auth Module

#### File: `src/note_mcp/auth/__init__.py`

**Purpose**: authモジュールの公開インターフェース
**Exports**: `Session`, `SessionManager`, `login_with_browser`
**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/auth/session.py`

**Purpose**: セッション管理（keyring使用、エラー時は明確な診断情報）
**FR Coverage**: FR-002, FR-008, FR-011
**Exports**: `Session`, `SessionManager`
**Dependencies**:
- `keyring`
- `pydantic`

**Specific Implementation**:
- `Session` Pydanticモデル（data-model.mdから）
- `SessionManager.save()` - keyringに保存
- `SessionManager.load()` - keyringから読み込み
- `SessionManager.clear()` - セッション削除
- `is_expired()` - 有効期限チェック
- keyring未設定時は明確なエラーメッセージ（環境名、設定手順を含む）

**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/auth/browser.py`

**Purpose**: Playwrightによるログインフロー
**FR Coverage**: FR-001
**Exports**: `login_with_browser`
**Dependencies**:
- `playwright.async_api`
- `auth/session.py`

**Specific Implementation**:
- ブラウザ起動（headless=False）
- note.comログインページへ遷移
- ユーザー手動ログイン待機（最大5分）
- Cookie抽出
- セッション作成・保存

**Agent Suggestion**: modular-builder

---

### API Module

#### File: `src/note_mcp/api/__init__.py`

**Purpose**: apiモジュールの公開インターフェース
**Exports**: `NoteAPIClient`, `create_draft`, `update_article`, `publish_article`, `list_articles`, `upload_image`
**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/api/client.py`

**Purpose**: note.com APIクライアント（httpx）
**FR Coverage**: FR-009, FR-010
**Exports**: `NoteAPIClient`
**Dependencies**:
- `httpx`
- `auth/session.py`

**Specific Implementation**:
- `NoteAPIClient` クラス（AsyncClient wrapper）
- Cookie認証ヘッダー設定
- レート制限管理（10リクエスト/分）
- エラーハンドリング（401/403/5xx）
- 共通リクエスト/レスポンス処理

**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/api/articles.py`

**Purpose**: 記事操作（CRUD）
**FR Coverage**: FR-003, FR-004, FR-005, FR-006
**Exports**: `create_draft`, `update_article`, `publish_article`, `list_articles`
**Dependencies**:
- `api/client.py`
- `utils/markdown.py`
- `models.py`

**Specific Implementation**:
- `create_draft(title, body, tags)` - 下書き作成
- `update_article(article_id, title, body, tags)` - 記事更新
- `publish_article(article_id?, title?, body?, tags?)` - 記事公開
- `list_articles(status, page, limit)` - 一覧取得
- APIレスポンスからArticleモデルへの変換

**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/api/images.py`

**Purpose**: 画像アップロード
**FR Coverage**: FR-007
**Exports**: `upload_image`
**Dependencies**:
- `api/client.py`
- `models.py`

**Specific Implementation**:
- `upload_image(file_path)` - 画像アップロード
- ファイル形式検証（JPEG, PNG, GIF, WebP）
- ファイルサイズ検証
- multipart/form-data送信

**Agent Suggestion**: modular-builder

---

### Browser Module

#### File: `src/note_mcp/browser/__init__.py`

**Purpose**: browserモジュールの公開インターフェース
**Exports**: `BrowserManager`, `show_preview`
**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/browser/manager.py`

**Purpose**: ブラウザインスタンス管理（シングルトン）
**FR Coverage**: FR-013
**Exports**: `BrowserManager`
**Dependencies**:
- `playwright.async_api`
- `asyncio`

**Specific Implementation**:
- シングルトンパターン
- asyncio.Lock による排他制御
- 既存ページの再利用
- アイドルタイムアウト（5分）
- atexitフックでクリーンアップ

**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/browser/preview.py`

**Purpose**: 記事プレビュー表示
**FR Coverage**: FR-012
**Exports**: `show_preview`
**Dependencies**:
- `browser/manager.py`

**Specific Implementation**:
- `show_preview(article_id, session)` - プレビューページを開く
  - article_id: note_create_draft/note_update_article の戻り値から取得
  - session: SessionManagerから取得（usernameを含む）
  - note_create_draftはarticle_keyも返すが、note_update_articleはarticle_idのみ返すため、article_idで統一
- 既存ウィンドウの再利用
- note.comプレビューURLへの遷移（`https://note.com/{username}/n/{article_id}/edit`）

**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/browser/editor.py`

**Purpose**: ブラウザUIエディタ操作（use_browser=True時）
**FR Coverage**: FR-009 (browser mode)
**Exports**: `create_draft_via_browser`, `update_article_via_browser`
**Dependencies**:
- `browser/manager.py`

**Specific Implementation**:
- note.comエディタページでの操作
- タイトル・本文入力
- 保存ボタンクリック
- DOM操作でのMarkdown→リッチテキスト変換

**Agent Suggestion**: modular-builder

---

### Utils Module

#### File: `src/note_mcp/utils/__init__.py`

**Purpose**: utilsモジュールの公開インターフェース
**Exports**: `markdown_to_html`, `setup_logging`
**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/utils/markdown.py`

**Purpose**: Markdown→HTML変換
**FR Coverage**: FR-009
**Exports**: `markdown_to_html`
**Dependencies**:
- `markdown_it`

**Specific Implementation**:
- CommonMark準拠の変換
- 軽量実装（拡張機能は最小限）

**Agent Suggestion**: modular-builder

---

#### File: `src/note_mcp/utils/logging.py`

**Purpose**: セキュアログ設定（Cookie秘匿）
**FR Coverage**: Security
**Exports**: `setup_logging`, `get_logger`
**Dependencies**:
- `logging`

**Specific Implementation**:
- Cookie値の完全マスキング（`[MASKED]`で置換）
- デバッグログでもCookie非表示
- 値は一切表示しない（セキュリティ優先）

**Agent Suggestion**: modular-builder

---

### Models

#### File: `src/note_mcp/models.py`

**Purpose**: Pydanticデータモデル
**FR Coverage**: All entities
**Exports**: `Session`, `Article`, `ArticleInput`, `ArticleStatus`, `Image`, `ErrorCode`, `NoteAPIError`
**Dependencies**:
- `pydantic`
- `enum`

**Specific Implementation**:
- data-model.mdの全エンティティを実装
- バリデーションルール
- APIレスポンスマッピングヘルパー

**Agent Suggestion**: modular-builder

---

## Files to Delete

#### File: `main.py`

**Reason**: プレースホルダー。`src/note_mcp/__main__.py`に置き換え
**Migration**: 不要（プレースホルダーのみ）

---

## Test Files to Create

### Unit Tests

#### File: `tests/__init__.py`

**Purpose**: テストパッケージ初期化

---

#### File: `tests/conftest.py`

**Purpose**: pytest fixtures
**Contents**:
- モックセッション
- モックAPIクライアント
- テスト用データ

---

#### File: `tests/unit/test_session.py`

**Purpose**: SessionManager のユニットテスト
**Test Cases**:
- セッション保存・読み込み
- 有効期限チェック
- keyringエラー時の明確な診断情報（OS、バックエンド、設定手順）

---

#### File: `tests/unit/test_markdown.py`

**Purpose**: Markdown変換のユニットテスト
**Test Cases**:
- 各種Markdown要素（見出し、リスト、コード等）
- 空文字列
- 大きなドキュメント

---

#### File: `tests/unit/test_api_client.py`

**Purpose**: NoteAPIClient のユニットテスト（httpxモック）
**Test Cases**:
- 認証ヘッダー設定
- エラーレスポンスハンドリング
- レート制限

---

#### File: `tests/unit/test_models.py`

**Purpose**: Pydanticモデルのバリデーションテスト
**Test Cases**:
- Session, Article, ArticleInput, Image
- バリデーションエラー

---

### Integration Tests

#### File: `tests/integration/test_auth_flow.py`

**Purpose**: 認証フローの統合テスト（モック）
**Test Cases**:
- ログイン→セッション保存→読み込み
- セッション期限切れ検知
- ログアウト

---

#### File: `tests/integration/test_article_operations.py`

**Purpose**: 記事操作の統合テスト（モック）
**Test Cases**:
- 下書き作成
- 記事更新
- 記事公開
- 一覧取得

---

### Contract Tests

#### File: `tests/contract/test_mcp_tools.py`

**Purpose**: MCPツールのコントラクトテスト
**Test Cases**:
- 各ツールのスキーマ検証
- 入力バリデーション
- エラーレスポンス形式

---

### E2E Tests (Manual)

#### File: `tests/e2e/test_full_workflow.py`

**Purpose**: 完全なワークフローE2Eテスト
**Test Cases**:
- ログイン→下書き作成→更新→画像アップロード→公開
- 実際のnote.comでの動作確認

---

## Implementation Chunks

### Chunk 1: Core Models & Utils

**Files**:
- `src/note_mcp/models.py`
- `src/note_mcp/utils/__init__.py`
- `src/note_mcp/utils/markdown.py`
- `src/note_mcp/utils/logging.py`

**Description**: データモデルとユーティリティの実装。他の全モジュールが依存する基盤。

**Why first**: 他のChunkがこれらに依存する。

**Test strategy**:
- `tests/unit/test_models.py`
- `tests/unit/test_markdown.py`

**Dependencies**: None

**Commit point**: After unit tests pass

```
feat: Add core models and utils for note-mcp

- Add Pydantic models (Session, Article, ArticleStatus, etc.)
- Add Markdown→HTML conversion utility
- Add secure logging with cookie masking
- All unit tests passing
```

---

### Chunk 2: Session Management

**Files**:
- `src/note_mcp/auth/__init__.py`
- `src/note_mcp/auth/session.py`

**Description**: keyringを使用したセッション管理の実装。エラー時は原因究明可能な診断情報を提供。

**Why second**: 認証フロー（Chunk 3）とAPIクライアント（Chunk 4）が依存する。

**Test strategy**:
- `tests/unit/test_session.py`

**Dependencies**: Chunk 1 (models)

**Commit point**: After unit tests pass

```
feat: Add session management with keyring storage

- Add SessionManager with keyring backend
- Add clear error diagnostics for keyring issues
- Add session expiration checking
- All unit tests passing
```

---

### Chunk 3: Browser Manager & Login

**Files**:
- `src/note_mcp/browser/__init__.py`
- `src/note_mcp/browser/manager.py`
- `src/note_mcp/auth/browser.py`

**Description**: Playwrightブラウザ管理とログインフローの実装。

**Why third**: ログイン機能は他の全操作の前提。

**Test strategy**:
- `tests/integration/test_auth_flow.py`（モック）

**Dependencies**: Chunk 1 (models), Chunk 2 (session)

**Commit point**: After integration tests pass

```
feat: Add Playwright browser management and login flow

- Add BrowserManager singleton with page reuse
- Add browser-based login flow with cookie extraction
- Add session persistence after login
- All integration tests passing
```

---

### Chunk 4: API Client

**Files**:
- `src/note_mcp/api/__init__.py`
- `src/note_mcp/api/client.py`

**Description**: httpxベースのnote.com APIクライアント実装。

**Why fourth**: 記事操作（Chunk 5）が依存する。

**Test strategy**:
- `tests/unit/test_api_client.py`

**Dependencies**: Chunk 1 (models), Chunk 2 (session)

**Commit point**: After unit tests pass

```
feat: Add note.com API client with httpx

- Add NoteAPIClient with cookie authentication
- Add rate limiting support (10 req/min)
- Add error handling for 401/403/5xx
- All unit tests passing
```

---

### Chunk 5: Article Operations (API Mode) - P1

**Files**:
- `src/note_mcp/api/articles.py`
- `src/note_mcp/browser/preview.py`

**Description**: 記事作成・更新（APIモード）とプレビュー表示の実装。P1機能のみ。

**Why fifth**: P1機能（下書き作成、更新）の中核。

**Scope (P1 only)**:
- `create_draft` - 下書き作成
- `update_article` - 記事更新
- `show_preview` - プレビュー表示
- ※ `list_articles`, `publish_article` はP2（Chunk 8）

**Test strategy**:
- `tests/integration/test_article_operations.py`

**Dependencies**: Chunk 1 (models), Chunk 3 (browser), Chunk 4 (api client)

**Commit point**: After integration tests pass

```
feat: Add article operations and preview display (P1)

- Add create_draft, update_article
- Add show_preview with browser reuse
- Add Markdown→HTML conversion in article creation
- All integration tests passing
```

---

### Chunk 6: Image Upload

**Files**:
- `src/note_mcp/api/images.py`

**Description**: 画像アップロード機能の実装。

**Why sixth**: P1機能だがChunk 5より独立性が高い。

**Test strategy**:
- `tests/unit/test_images.py`（追加）

**Dependencies**: Chunk 4 (api client)

**Commit point**: After unit tests pass

```
feat: Add image upload functionality

- Add upload_image with multipart/form-data
- Add file format validation (JPEG, PNG, GIF, WebP)
- Add file size validation
- All unit tests passing
```

---

### Chunk 7: MCP Server Integration

**Files**:
- `src/note_mcp/__init__.py`
- `src/note_mcp/__main__.py`
- `src/note_mcp/server.py`

**Description**: FastMCPサーバー定義と全ツールの統合。

**Why seventh**: 全コンポーネントを統合する最終ステップ。

**Test strategy**:
- `tests/contract/test_mcp_tools.py`

**Dependencies**: All previous chunks

**Commit point**: After contract tests pass

```
feat: Add FastMCP server with all tools integrated

- Add FastMCP server definition
- Register all 8 MCP tools
- Add __main__.py for CLI execution
- All contract tests passing
```

---

### Chunk 8: P2 Features (Browser Editor, Publish, List)

**Files**:
- `src/note_mcp/browser/editor.py`
- `src/note_mcp/api/articles.py` (update for publish, list_articles)

**Description**: P2機能の実装：ブラウザUIモード操作、記事公開、記事一覧取得。

**Why eighth**: P2機能、P1完成後に実装。

**Scope (P2)**:
- `publish_article` - 記事公開
- `list_articles` - 記事一覧取得
- `create_draft_via_browser` - ブラウザUIでの下書き作成
- `update_article_via_browser` - ブラウザUIでの記事更新
- `use_browser` パラメータ対応

**Test strategy**:
- `tests/integration/test_article_operations.py`（拡張）

**Dependencies**: Chunk 5 (articles)

**Commit point**: After integration tests pass

```
feat: Add P2 features (browser editor, publish, list)

- Add browser-based article creation/editing
- Add publish_article functionality
- Add list_articles functionality
- Add use_browser parameter support
- All integration tests passing
```

---

### Chunk 9: Test Infrastructure & CI Adjustment

**Files**:
- `tests/__init__.py`
- `tests/conftest.py`
- `.github/workflows/test.yml` (既存ファイルを必要に応じて拡張)

**Description**: テストインフラ整備と既存CIの調整（必要な場合のみ）。

**Why ninth**: 全テストを統合実行可能にする。

**Note**: `.github/workflows/test.yml` は既に存在するため、新規作成ではなく必要に応じた拡張・調整を行う。

**Test strategy**:
- 全テストの実行確認

**Dependencies**: All chunks

**Commit point**: After all tests pass in CI

```
chore: Add test infrastructure and adjust CI workflow

- Add pytest fixtures and conftest
- Adjust existing GitHub Actions CI workflow if needed
- All tests passing in CI
```

---

### Chunk 10: Documentation & Cleanup

**Files**:
- `README.md` (update)
- `DISCLAIMER.md` (update if needed)
- Delete `main.py`

**Description**: ドキュメント更新とクリーンアップ。

**Why last**: 実装完了後の仕上げ。

**Test strategy**:
- ドキュメント内のコマンド実行確認

**Dependencies**: All chunks

**Commit point**: Final commit

```
docs: Update README and cleanup placeholder files

- Update README with usage instructions
- Remove placeholder main.py
- Final cleanup
```

---

## Agent Orchestration Strategy

### Primary Agents

**modular-builder** - For module implementation:
```
Task modular-builder: "Implement [module] according to spec in
code_plan.md and Phase 2 documentation (spec.md, data-model.md,
mcp-tools.yaml)"
```

**bug-hunter** - If issues arise:
```
Task bug-hunter: "Debug issue with [specific problem]"
```

**test-coverage** - For test planning:
```
Task test-coverage: "Suggest comprehensive tests for [module]"
```

### Execution Strategy

**Sequential Execution** (dependencies between chunks):
```
Chunk 1 → Chunk 2 → Chunk 3 → Chunk 4 → Chunk 5 → Chunk 6 → Chunk 7 → Chunk 8 → Chunk 9 → Chunk 10
```

**Reason for Sequential**:
- 各ChunkがPrevious Chunksに依存
- テスト駆動開発（TDD）で各Chunk完了を確認
- 段階的な動作確認が可能

### Parallel Opportunities

限定的に並列化可能：
- Chunk 5 (Articles) と Chunk 6 (Images) は Chunk 4 完了後に並列可能
- Chunk 9 (Test Infra) は Chunk 7 と並列で開始可能

---

## Testing Strategy

### Unit Tests to Add

**File: tests/unit/test_models.py**
- Test Session validation
- Test Article validation
- Test ArticleStatus enum
- Test Image validation
- Test ErrorCode enum

**File: tests/unit/test_session.py**
- Test `SessionManager.save()` with mock keyring
- Test `SessionManager.load()` with mock keyring
- Test `SessionManager.clear()` with mock keyring
- Test `Session.is_expired()` logic
- Test keyring error diagnostics

**File: tests/unit/test_markdown.py**
- Test heading conversion
- Test list conversion
- Test code block conversion
- Test link conversion
- Test image conversion
- Test empty string

**File: tests/unit/test_api_client.py**
- Test cookie header setup
- Test 401 response handling
- Test 403 response handling
- Test 5xx response handling
- Test rate limiting logic

**File: tests/unit/test_images.py**
- Test file format validation
- Test file size validation
- Test multipart encoding

### Integration Tests to Add

**File: tests/integration/test_auth_flow.py**
- Test login → session save → session load
- Test session expiration detection
- Test logout clears session

**File: tests/integration/test_article_operations.py**
- Test create_draft with mock API
- Test update_article with mock API
- Test publish_article with mock API
- Test list_articles with mock API

### Contract Tests to Add

**File: tests/contract/test_mcp_tools.py**
- Test note_login schema
- Test note_check_auth schema
- Test note_logout schema
- Test note_create_draft schema
- Test note_update_article schema
- Test note_publish_article schema
- Test note_list_articles schema
- Test note_upload_image schema
- Test error response format

### User Testing Plan

**Commands to run**:
```bash
# Install and setup
uv sync
uv run playwright install chromium

# Run unit tests
uv run pytest tests/unit -v

# Run integration tests
uv run pytest tests/integration -v

# Run contract tests
uv run pytest tests/contract -v

# Manual E2E test (requires real note.com account)
NOTE_MCP_TEST_MODE=e2e uv run pytest tests/e2e -v --headed

# Start MCP server manually
uv run python -m note_mcp
```

**Expected behavior**:
- All automated tests pass
- MCP server starts without errors
- Claude Desktop can connect and list tools

---

## Philosophy Compliance

### Ruthless Simplicity

- **FastMCP使用**: ボイラープレート最小化
- **単一プロジェクト構成**: 不要な分割なし
- **直接的なhttpx使用**: 過度なラッパーなし
- **最小限の抽象化**: 各レイヤーが明確な目的を持つ

### YAGNI (You Aren't Gonna Need It)

- **use_browser**: 明示的なオプトイン（デフォルトはAPIモード）
- **エラー時は明確化**: APIエラー、keyringエラーは診断情報付きで報告
- **P2機能は後回し**: P1機能完成後に実装

### Zero-BS (No Stubs)

- **各Chunkで動作するコードを作成**
- **プレースホルダーなし**
- **TDDで確実に動作を確認**

### Modular Design (Bricks & Studs)

- **明確なモジュール境界**: auth, api, browser, utils
- **公開インターフェース**: `__init__.py`でexports定義
- **独立したテスト**: 各モジュールのユニットテスト

---

## Commit Strategy

### Commit 1: Chunk 1 - Core Models & Utils
```
feat: Add core models and utils for note-mcp

- Add Pydantic models (Session, Article, ArticleStatus, etc.)
- Add Markdown→HTML conversion utility
- Add secure logging with cookie masking
- All unit tests passing

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 2: Chunk 2 - Session Management
```
feat: Add session management with keyring storage

- Add SessionManager with keyring backend
- Add clear error diagnostics for keyring issues
- Add session expiration checking
- All unit tests passing

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 3: Chunk 3 - Browser Manager & Login
```
feat: Add Playwright browser management and login flow

- Add BrowserManager singleton with page reuse
- Add browser-based login flow with cookie extraction
- Add session persistence after login
- All integration tests passing

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 4: Chunk 4 - API Client
```
feat: Add note.com API client with httpx

- Add NoteAPIClient with cookie authentication
- Add rate limiting support (10 req/min)
- Add error handling for 401/403/5xx
- All unit tests passing

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 5: Chunk 5 - Article Operations
```
feat: Add article operations and preview display

- Add create_draft, update_article, list_articles
- Add show_preview with browser reuse
- Add Markdown→HTML conversion in article creation
- All integration tests passing

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 6: Chunk 6 - Image Upload
```
feat: Add image upload functionality

- Add upload_image with multipart/form-data
- Add file format validation (JPEG, PNG, GIF, WebP)
- Add file size validation
- All unit tests passing

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 7: Chunk 7 - MCP Server Integration
```
feat: Add FastMCP server with all tools integrated

- Add FastMCP server definition
- Register all 8 MCP tools
- Add __main__.py for CLI execution
- All contract tests passing

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 8: Chunk 8 - Browser Editor & Publish
```
feat: Add browser editor mode and publish functionality

- Add browser-based article creation/editing
- Add publish_article functionality
- Add use_browser parameter support
- All integration tests passing

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 9: Chunk 9 - Test Infrastructure & CI Adjustment
```
chore: Add test infrastructure and adjust CI workflow

- Add pytest fixtures and conftest
- Adjust existing GitHub Actions CI workflow if needed
- All tests passing in CI

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

### Commit 10: Chunk 10 - Documentation & Cleanup
```
docs: Update README and cleanup placeholder files

- Update README with usage instructions
- Remove placeholder main.py
- Final cleanup

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

---

## Risk Assessment

### High Risk Changes

| Change | Risk | Mitigation |
|--------|------|------------|
| note.com API呼び出し | API仕様変更 | エラーハンドリング充実、手動E2Eテスト |
| Playwrightブラウザ操作 | DOM変更 | 堅牢なセレクタ使用、タイムアウト設定 |
| keyring使用 | 環境依存 | 明確なエラーメッセージで設定手順を案内 |

### Dependencies to Watch

| Dependency | Version | Constraint |
|------------|---------|------------|
| fastmcp | >=2.0.0 | Breaking changes in major versions |
| playwright | >=1.40.0 | Browser compatibility |
| keyring | >=25.0.0 | Backend availability |
| httpx | >=0.27.0 | Async API stability |

### Breaking Changes

なし（新規プロジェクト）

---

## Success Criteria

Code is ready when:

- [ ] All documented behavior implemented (8 MCP tools)
- [ ] All tests passing (`make check` equivalent)
- [ ] User testing works as documented (Quickstart guide)
- [ ] No regressions (N/A - new project)
- [ ] Code follows philosophy principles (simplicity, modularity)
- [ ] Ready for Phase 4 implementation

---

## Next Steps

✅ Code plan complete and detailed
➡️ Get user approval
➡️ When approved, run: `/ddd:4-code`

---

# Phase 6: note_get_article Implementation Plan

**Added**: 2025-12-20
**Based on**: Phase 1 plan.md Section 11 + Phase 2 README.md updates

---

## Summary

`note_get_article` MCPツールを追加し、既存記事の内容（タイトル、本文、タグ、ステータス）を取得可能にする。これにより、`note_update_article`の前に既存内容を確認し、「追記」「一部修正」などの編集操作が可能になる。

**推奨ワークフロー**:
1. `note_get_article(article_id)` で既存内容を取得
2. AI/ユーザーが編集内容を決定
3. `note_update_article(article_id, ...)` で保存

---

## Files to Change

### File: `src/note_mcp/browser/get_article.py` (NEW)

**Purpose**: ブラウザベースの記事内容取得
**Current State**: 存在しない（新規作成）
**Required Changes**: 新規作成

**Specific Implementation**:
```python
"""Browser-based article retrieval for note.com."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

from note_mcp.browser.manager import BrowserManager
from note_mcp.models import Article, ArticleStatus

if TYPE_CHECKING:
    from note_mcp.models import Session

NOTE_EDITOR_URL = "https://editor.note.com"


async def get_article_via_browser(
    session: Session,
    article_id: str,
) -> Article:
    """Get article content via browser automation.

    Navigates to the article's edit page and extracts content.

    Args:
        session: Authenticated session
        article_id: ID of the article to retrieve

    Returns:
        Article object with content

    Raises:
        RuntimeError: If article retrieval fails
    """
    manager = BrowserManager.get_instance()
    page = await manager.get_page()

    # Inject session cookies
    playwright_cookies: list[dict[str, Any]] = []
    for name, value in session.cookies.items():
        playwright_cookies.append({
            "name": name,
            "value": value,
            "domain": ".note.com",
            "path": "/",
        })
    await page.context.add_cookies(playwright_cookies)

    # Navigate to edit page
    edit_url = f"{NOTE_EDITOR_URL}/notes/{article_id}/edit/"
    await page.goto(edit_url, wait_until="domcontentloaded")

    # Wait for network idle
    with contextlib.suppress(Exception):
        await page.wait_for_load_state("networkidle", timeout=10000)

    await asyncio.sleep(2)  # Wait for JS initialization

    # Verify navigation
    if article_id not in page.url:
        raise RuntimeError(f"Failed to navigate to article. URL: {page.url}")

    # Wait for editor
    with contextlib.suppress(Exception):
        await page.wait_for_selector(".ProseMirror", state="visible", timeout=10000)

    await asyncio.sleep(1)

    # Extract title
    title = ""
    title_selectors = [
        'input[placeholder*="タイトル"]',
        'textarea[placeholder*="タイトル"]',
    ]
    for selector in title_selectors:
        try:
            title_el = page.locator(selector).first
            if await title_el.count() > 0:
                title = await title_el.input_value()
                break
        except Exception:
            continue

    # Extract body (plain text via innerText)
    body = ""
    try:
        body_el = page.locator(".ProseMirror").first
        if await body_el.count() > 0:
            body = await body_el.inner_text()
    except Exception:
        pass

    return Article(
        id=article_id,
        key=article_id,
        title=title,
        body=body,
        status=ArticleStatus.DRAFT,  # Default, actual status unknown from editor
        tags=[],  # Tags not easily extractable from editor UI
    )
```

**Dependencies**: `browser/manager.py`, `models.py`
**Agent Suggestion**: modular-builder

---

### File: `src/note_mcp/api/articles.py` (MODIFY)

**Purpose**: 記事操作API
**Current State**: `create_draft`, `update_article`, `list_articles`, `publish_article` が存在
**Required Changes**: `get_article()` 関数を追加

**Specific Modifications**:

1. **Add import**:
```python
# 既存importに追加なし（browser importはget_article内で遅延import）
```

2. **Add function** (既存関数の後に追加):
```python
async def get_article(
    session: Session,
    article_id: str,
) -> Article:
    """Get article content by ID.

    Retrieves article content via browser automation.

    Args:
        session: Authenticated session
        article_id: ID of the article to retrieve

    Returns:
        Article object with content

    Raises:
        RuntimeError: If article retrieval fails
    """
    from note_mcp.browser.get_article import get_article_via_browser

    return await get_article_via_browser(session, article_id)
```

**Dependencies**: `browser/get_article.py`
**Agent Suggestion**: modular-builder

---

### File: `src/note_mcp/server.py` (MODIFY)

**Purpose**: MCPサーバー定義
**Current State**: 10個のMCPツールが登録済み
**Required Changes**: `note_get_article` ツールを追加

**Specific Modifications**:

1. **Add import** (line 13あたり):
```python
from note_mcp.api.articles import create_draft, get_article, list_articles, publish_article, update_article
```

2. **Add tool** (line 161あたり、`note_update_article`の前に追加):
```python
@mcp.tool()
async def note_get_article(
    article_id: Annotated[str, "取得する記事のID"],
) -> str:
    """記事の内容を取得します。

    指定したIDの記事のタイトル、本文、ステータスを取得します。
    記事の編集前に既存内容を確認する際に使用します。

    Args:
        article_id: 取得する記事のID

    Returns:
        記事の内容（タイトル、本文、ステータス）
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    try:
        article = await get_article(session, article_id)
    except RuntimeError as e:
        return f"記事の取得に失敗しました: {e}"

    return f"""記事を取得しました。

タイトル: {article.title}
ステータス: {article.status.value}
タグ: {', '.join(article.tags) if article.tags else 'なし'}

本文:
{article.body}"""
```

**Dependencies**: `api/articles.py`
**Agent Suggestion**: modular-builder

---

### File: `tests/integration/test_article_operations.py` (MODIFY)

**Purpose**: 記事操作の統合テスト
**Current State**: `TestCreateDraft`, `TestUpdateArticle`, `TestShowPreview`, `TestListArticles`, `TestPublishArticle` が存在
**Required Changes**: `TestGetArticle` クラスを追加

**Specific Modifications**:

Add test class (line 201あたり、`TestListArticles`の前に追加):
```python
class TestGetArticle:
    """Tests for get_article function."""

    @pytest.mark.asyncio
    async def test_get_article_success(self) -> None:
        """Test successful article retrieval via browser."""
        from note_mcp.api.articles import get_article
        from note_mcp.models import Article

        session = create_mock_session()

        mock_article = Article(
            id="123456",
            key="n1234567890ab",
            title="Existing Article",
            body="This is the existing content.\n\nWith multiple paragraphs.",
            status=ArticleStatus.DRAFT,
            tags=[],
        )

        with patch("note_mcp.browser.get_article.get_article_via_browser") as mock_get:
            mock_get.return_value = mock_article

            article = await get_article(session, "123456")

            assert article.id == "123456"
            assert article.title == "Existing Article"
            assert "existing content" in article.body
            mock_get.assert_called_once_with(session, "123456")

    @pytest.mark.asyncio
    async def test_get_article_preserves_newlines(self) -> None:
        """Test that article body preserves newlines."""
        from note_mcp.api.articles import get_article
        from note_mcp.models import Article

        session = create_mock_session()

        mock_article = Article(
            id="123",
            key="n123",
            title="Test",
            body="Line 1\n\nLine 2\n\nLine 3",
            status=ArticleStatus.DRAFT,
            tags=[],
        )

        with patch("note_mcp.browser.get_article.get_article_via_browser") as mock_get:
            mock_get.return_value = mock_article

            article = await get_article(session, "123")

            assert article.body.count("\n") >= 2
```

**Dependencies**: なし
**Agent Suggestion**: test-coverage

---

## Implementation Chunks

### Chunk 1: Browser Get Article Module

**Files**:
- `src/note_mcp/browser/get_article.py` (NEW)

**Description**: ブラウザベースの記事取得機能を実装。既存の`update_article.py`のパターンを踏襲。

**Why first**: 他のファイルがこのモジュールに依存する。

**Test strategy**: Chunk 3でモックを使った統合テストを追加

**Dependencies**: None (uses existing browser/manager.py)

**Commit point**: After file creation with basic structure

---

### Chunk 2: API Layer Integration

**Files**:
- `src/note_mcp/api/articles.py` (MODIFY)
- `src/note_mcp/server.py` (MODIFY)

**Description**: `get_article()` 関数と `note_get_article` MCPツールを追加。

**Why second**: Chunk 1の実装に依存。

**Test strategy**: Chunk 3でテストを追加

**Dependencies**: Chunk 1

**Commit point**: After integration complete

---

### Chunk 3: Tests

**Files**:
- `tests/integration/test_article_operations.py` (MODIFY)

**Description**: `get_article` のテストを追加。

**Why third**: 実装完了後にテストを追加。

**Test strategy**:
- `pytest tests/integration/test_article_operations.py -v`

**Dependencies**: Chunk 1, 2

**Commit point**: After all tests pass

---

## Agent Orchestration Strategy

### Primary Agent

**modular-builder** - For all implementation:
```
Task modular-builder: "Implement note_get_article according to
Phase 6 code plan. Create browser/get_article.py, modify
api/articles.py and server.py"
```

### Execution Strategy

**Sequential Execution**:
```
Chunk 1 (browser module) → Chunk 2 (API + server) → Chunk 3 (tests)
```

**Reason**: Each chunk depends on the previous one.

---

## Testing Strategy

### Unit Tests

なし（ブラウザ操作は統合テストでモック）

### Integration Tests

**File: tests/integration/test_article_operations.py**
- Test `get_article()` with mocked browser
- Test newline preservation in body

### User Testing Plan

**Commands to run**:
```bash
# Run all article operation tests
uv run pytest tests/integration/test_article_operations.py -v

# Run only get_article tests
uv run pytest tests/integration/test_article_operations.py::TestGetArticle -v

# Run full check
uv run ruff check --fix . && uv run ruff format . && uv run mypy .
```

**Manual E2E test**:
```
1. note_login でログイン
2. note_create_draft でテスト記事を作成
3. note_get_article で内容を取得
4. 取得した内容を確認
5. 末尾に追記して note_update_article で更新
6. note_get_article で更新後の内容を確認
```

---

## Philosophy Compliance

### Ruthless Simplicity

- 既存パターン（update_article.py）を踏襲
- 1つのファイル追加、2つのファイル修正のみ
- APIフォールバックなし（ブラウザベースのみ）

### Modular Design

- `browser/get_article.py` は自己完結モジュール
- `Article` モデルを共通インターフェースとして使用

---

## Commit Strategy

### Single Commit

```
feat: Add note_get_article tool for retrieving article content

- Add browser/get_article.py for browser-based content extraction
- Add get_article() function to api/articles.py
- Add note_get_article MCP tool to server.py
- Add tests for get_article functionality

This enables the recommended edit workflow:
1. note_get_article() to retrieve existing content
2. User/AI decides on edits
3. note_update_article() to save changes

🤖 Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

---

## Success Criteria

Phase 6 is ready when:

- [ ] `note_get_article(article_id)` で記事内容が取得できる
- [ ] 取得した本文がプレーンテキスト（改行維持）
- [ ] コード品質チェック通過（ruff, mypy）
- [ ] テスト通過
- [ ] README.mdが更新済み（Phase 2で完了）

---

## Next Steps

✅ Phase 6 code plan complete
➡️ Get user approval
➡️ When approved, run: `/ddd:4-code`
