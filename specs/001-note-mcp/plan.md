# Implementation Plan: note.com MCP Server

**Branch**: `001-note-mcp` | **Date**: 2025-12-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-note-mcp/spec.md`

## Summary

note.com（日本の人気ブログプラットフォーム）の記事管理を可能にするMCPサーバーを構築する。Playwrightによるブラウザ自動化で認証とプレビューを実現し、ハイブリッドアプローチ（API + ブラウザUI）で記事操作を行う。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- FastMCP (MCPサーバーフレームワーク)
- Playwright (ブラウザ自動化)
- keyring (セッション情報のセキュア保存)
- httpx (HTTP APIクライアント)
- markdown-it-py (Markdown→HTML変換)

**Storage**:
- OSキーチェーン/資格情報マネージャー（セッション情報）
- ローカルファイル（セッション補助データ、必要に応じて）

**Testing**: pytest + pytest-asyncio（pytest-mcpはオプション、後述）
**Target Platform**: デスクトップ（Windows/macOS/Linux）- Playwrightが動作する環境
**Project Type**: single (MCPサーバー単独プロジェクト)
**Performance Goals**:
- 記事操作（下書き作成・更新・公開）30秒以内
- 記事一覧取得10秒以内
- 画像アップロード（1MB以下）15秒以内

**Constraints**:
- レート制限: 10リクエスト/分
- note.com非公式API依存（仕様変更リスクあり）
- 自己責任・無保証での公開

**Scale/Scope**: 個人利用〜小規模チーム

---

## Tool Surface（MCPツール一覧）

FR（Functional Requirements）との対応付け。

| Tool Name | FR | Priority | Args | Returns | Main Errors |
|-----------|-----|----------|------|---------|-------------|
| `note_login` | FR-001 | P1 | `timeout_seconds?: int` | `{success, username, message}` | `BROWSER_TIMEOUT`, `LOGIN_FAILED` |
| `note_check_auth` | FR-008 | P1 | (none) | `{authenticated, username, expires_at}` | `KEYRING_ERROR` |
| `note_logout` | FR-002 | P2 | (none) | `{success, message}` | `KEYRING_ERROR` |
| `note_create_draft` | FR-003, FR-012 | P1 | `title: str, body: str, tags?: list[str], use_browser?: bool` | `{success, article_id, article_key, preview_url}` | `NOT_AUTHENTICATED`, `API_ERROR`, `RATE_LIMITED` |
| `note_update_article` | FR-005, FR-012 | P1 | `article_id: str, title?: str, body?: str, tags?: list[str], use_browser?: bool` | `{success, article_id, preview_url}` | `NOT_AUTHENTICATED`, `ARTICLE_NOT_FOUND`, `API_ERROR` |
| `note_publish_article` | FR-004 | P2 | `article_id?: str, title?: str, body?: str, tags?: list[str], use_browser?: bool` | `{success, article_id, published_url}` | `NOT_AUTHENTICATED`, `API_ERROR` |
| `note_list_articles` | FR-006 | P2 | `status?: enum, page?: int, limit?: int` | `{success, articles[], total, has_more}` | `NOT_AUTHENTICATED`, `API_ERROR` |
| `note_upload_image` | FR-007 | P1 | `file_path: str` | `{success, image_key, image_url}` | `NOT_AUTHENTICATED`, `UPLOAD_FAILED`, `FILE_NOT_FOUND` |

**`use_browser`パラメータ**:
- デフォルト: `false`（APIモード）
- `true`を指定するとブラウザUIモードで操作
- APIが不安定な場合やブラウザでの確認が必要な場合に使用

**Error Codes (共通)**:
- `NOT_AUTHENTICATED`: 未認証 → `note_login`を実行
- `SESSION_EXPIRED`: セッション期限切れ → 再ログイン必要
- `RATE_LIMITED`: レート制限 → 1分待機してリトライ
- `API_ERROR`: note.com APIエラー → 詳細メッセージ参照
- `KEYRING_ERROR`: keyringアクセス失敗 → 環境設定確認

---

## Operation Mode Decision Table（API vs ブラウザ選択表）

FR-009（ハイブリッドアプローチ）の具体化。**ユーザーがモードを選択**し、フォールバックは行わない。

| 操作 | 利用可能モード | デフォルト | 備考 |
|------|---------------|-----------|------|
| **ログイン** | ブラウザのみ | ブラウザ | Cookie取得にはブラウザ認証が必須 |
| **認証確認** | APIのみ | API | Cookie有効性をAPI呼び出しで確認 |
| **下書き作成** | API / ブラウザ | API | `use_browser=True`でブラウザモード |
| **記事更新** | API / ブラウザ | API | `use_browser=True`でブラウザモード |
| **記事公開** | API / ブラウザ | API | `use_browser=True`でブラウザモード |
| **記事一覧取得** | APIのみ | API | ブラウザUIでは非効率 |
| **画像アップロード** | APIのみ | API | multipart/form-dataで送信 |
| **プレビュー表示** | ブラウザのみ | ブラウザ | ユーザーが視覚確認するため |

**エラー処理方針（フォールバックなし）**:
- APIモードで失敗した場合は**エラーを返す**（ブラウザへの自動フォールバックなし）
- ブラウザモードで失敗した場合も**エラーを返す**
- ユーザーは明示的に`use_browser=True`を指定してリトライ可能
- これにより予測可能な動作を保証し、デバッグを容易にする

---

## Auth/Session Lifecycle

### セッション状態遷移

```
[未認証] ──login──> [認証中] ──success──> [認証済み]
    ^                  │                      │
    │                  v                      v
    │              [失敗]              [期限切れ検知]
    │                                         │
    └─────────────────────────────────────────┘
```

### 期限切れ検知

1. **事前チェック**: 各ツール実行前にセッションの`expires_at`を確認
2. **APIレスポンス検知**: 401/403応答を受けた場合はセッション無効化
3. **自動通知**: 期限切れ検知時は`SESSION_EXPIRED`エラーと再ログイン手順を返す

### 再ログイン導線

```python
# エラーレスポンス例
{
    "success": false,
    "error": "SESSION_EXPIRED",
    "message": "セッションの有効期限が切れました。note_loginツールを実行して再ログインしてください。"
}
```

### keyring未設定環境の扱い

| 環境 | keyringバックエンド | 対応 |
|------|-------------------|------|
| macOS | Keychain | 標準対応 |
| Windows | Credential Vault | 標準対応 |
| Linux (GNOME) | Secret Service | 標準対応 |
| Linux (headless/no-GUI) | なし | **エラー: 明確な診断情報と設定手順を案内** |
| WSL | Windows Credential経由 | 要追加設定（設定手順をエラーに含める） |

**エラー処理方針（フォールバックなし）**:
```python
try:
    import keyring
    keyring.get_password("test", "test")  # バックエンド確認
except keyring.errors.NoKeyringError as e:
    # 明確なエラーメッセージで原因究明を支援
    raise KeyringNotConfiguredError(
        f"keyringが設定されていません。\n"
        f"OS: {platform.system()}\n"
        f"バックエンド: {keyring.get_keyring()}\n"
        f"設定手順: https://github.com/xxx/note-mcp#keyring-setup"
    ) from e
```

**設計理由**: フォールバックは複雑性を増し、問題の隠蔽につながる。明確なエラーで原因究明を容易にする。

### ログへの秘匿方針

- **Cookieは絶対にログ出力しない**
- ログにはマスク済み情報のみ: `session_id=***abc`（末尾3文字のみ）
- デバッグログレベルでもCookie値は出力禁止
- エラースタックトレースからもCookie値をフィルタ

---

## Browser Concurrency（ブラウザ並行制御）

FR-013（既存ウィンドウ再利用）の実装方針。

### 設計方針

**単一ブラウザインスタンス管理**:
- MCPサーバープロセス内で1つのPlaywrightブラウザインスタンスを保持
- 同一プロセス内の複数ツール呼び出しは同じブラウザを共有

### 実装パターン

```python
class BrowserManager:
    _instance: Optional["BrowserManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @classmethod
    async def get_instance(cls) -> "BrowserManager":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def get_page(self) -> Page:
        """既存ページを返すか、なければ新規作成"""
        async with self._lock:
            if self._page is None or self._page.is_closed():
                if self._browser is None:
                    self._browser = await playwright.chromium.launch(headless=False)
                if self._context is None:
                    self._context = await self._browser.new_context()
                self._page = await self._context.new_page()
            return self._page
```

### 多重起動時の挙動

| シナリオ | 挙動 |
|---------|------|
| 同一MCPサーバープロセス内 | ロックで排他制御、順次実行 |
| 複数MCPサーバープロセス（異なるクライアント） | 独立したブラウザインスタンス（衝突なし） |
| ツール実行中に別ツール呼び出し | 前のツール完了まで待機（タイムアウト30秒） |

### クリーンアップ

- MCPサーバー終了時にブラウザを閉じる（`atexit`フック）
- 長時間アイドル（5分）後はブラウザを閉じてリソース解放
- ブラウザクラッシュ時は自動再起動

---

## Testing Matrix

### テスト分類と自動化方針

| カテゴリ | 対象 | 自動化 | CI実行 | 備考 |
|---------|------|--------|--------|------|
| **Unit** | Markdown変換、データモデル、ユーティリティ | ✅ 必須 | ✅ 必須 | 外部依存なし |
| **Integration (Mock)** | APIクライアント（httpx）、keyring操作 | ✅ 必須 | ✅ 必須 | モック使用 |
| **Integration (MCP)** | MCPツール呼び出し（FastMCPインメモリ） | ✅ 必須 | ✅ 必須 | 認証はモック |
| **E2E (Browser)** | Playwrightブラウザ操作 | ⚠️ 任意 | ❌ スキップ | ローカル手動実行 |
| **E2E (Full)** | 実際のnote.com API | ❌ 手動 | ❌ スキップ | 認証情報必要 |

### CI設計（Secretsなしで落ちない）

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: uv sync
      - name: Run unit tests
        run: uv run pytest tests/unit -v
      - name: Run integration tests (mocked)
        run: uv run pytest tests/integration -v -m "not requires_auth"
      - name: Run MCP contract tests
        run: uv run pytest tests/contract -v
```

### E2Eテストのローカル実行

```bash
# 認証情報を設定（手動ログイン済み前提）
NOTE_MCP_TEST_MODE=e2e uv run pytest tests/e2e -v --headed
```

### pytest-mcpの採用判断

| オプション | 採用 | 理由 |
|-----------|------|------|
| **pytest + FastMCPインメモリテスト** | ✅ 採用 | シンプル、依存少ない |
| **pytest-mcp（PyPI）** | ⚠️ オプション | メトリクス収集が必要な場合のみ |

**採用理由**: FastMCPの組み込みテスト機能（`FastMCPClient`）で十分。pytest-mcpは将来的なメトリクス分析が必要になった場合に追加検討。

---

## Phases & Milestones

### Phase 0: 基盤構築

**目標**: プロジェクト構造とコア依存関係のセットアップ

**完了条件チェックリスト**:
- [ ] `pyproject.toml`でPython 3.11+、全依存関係を定義
- [ ] `uv sync`でインストール成功
- [ ] `uv run playwright install chromium`でブラウザインストール成功
- [ ] 基本ディレクトリ構造（`src/note_mcp/`, `tests/`）作成
- [ ] `uv run pytest`で空のテストスイートが実行可能
- [ ] `research.md`作成完了

**成果物**: pyproject.toml, 基本ディレクトリ構造, research.md

---

### Phase 1: 認証基盤（P1: FR-001, FR-002, FR-008）

**目標**: ログイン/ログアウト/認証確認の実装

**完了条件チェックリスト**:
- [ ] `note_login`ツール: ブラウザ起動→ユーザーログイン→Cookie取得→keyring保存
- [ ] `note_check_auth`ツール: keyringからセッション読み込み→有効性確認
- [ ] `note_logout`ツール: keyringからセッション削除
- [ ] keyringエラー時の診断情報実装（OS、バックエンド、設定手順）
- [ ] Unit tests: session.py（モック使用）
- [ ] Integration tests: 認証フロー（モック使用）
- [ ] 手動E2Eテスト: 実際のnote.comログイン成功

**成果物**: `auth/browser.py`, `auth/session.py`, 関連テスト

---

### Phase 2: 記事操作（P1: FR-003, FR-005, FR-009）

**目標**: 下書き作成・更新の実装

**完了条件チェックリスト**:
- [ ] `note_create_draft`ツール: Markdown→HTML変換→API呼び出し→プレビュー表示
- [ ] `note_update_article`ツール: 既存記事の更新→プレビュー表示
- [ ] Markdown→HTML変換ユーティリティ
- [ ] APIクライアント（httpx）実装
- [ ] ブラウザプレビュー表示（既存ウィンドウ再利用）
- [ ] Unit tests: markdown.py, client.py
- [ ] Integration tests: MCPツール呼び出し（モック）
- [ ] 手動E2Eテスト: 実際の下書き作成・更新成功

**成果物**: `api/client.py`, `api/articles.py`, `browser/preview.py`, `utils/markdown.py`, 関連テスト

---

### Phase 3: 画像アップロード（P1: FR-007）

**目標**: 画像アップロードの実装

**完了条件チェックリスト**:
- [ ] `note_upload_image`ツール: ファイル読み込み→multipart/form-data送信→URL取得
- [ ] サポート形式チェック（JPEG, PNG, GIF, WebP）
- [ ] ファイルサイズ検証
- [ ] Unit tests: images.py
- [ ] 手動E2Eテスト: 実際の画像アップロード成功

**成果物**: `api/images.py`, 関連テスト

---

### Phase 4: 追加機能（P2: FR-004, FR-006）

**目標**: 記事公開・一覧取得の実装

**完了条件チェックリスト**:
- [ ] `note_publish_article`ツール: 新規公開 or 下書き→公開
- [ ] `note_list_articles`ツール: 一覧取得（ステータスフィルタ対応）
- [ ] Unit tests
- [ ] Integration tests（モック）
- [ ] 手動E2Eテスト

**成果物**: articles.py拡張, 関連テスト

---

### Phase 5: 仕上げ

**目標**: ドキュメント・CI・リリース準備

**完了条件チェックリスト**:
- [ ] README.md（インストール手順、使用方法、免責事項）
- [ ] DISCLAIMER.md（自己責任・無保証の明記）
- [ ] GitHub Actions CI設定
- [ ] 全Unitテスト合格
- [ ] 全Integrationテスト合格
- [ ] ローカルE2Eテスト成功（手動確認）
- [ ] PyPIパッケージ設定（オプション）

**成果物**: README.md, DISCLAIMER.md, .github/workflows/test.yml

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

プロジェクト固有のConstitutionが未定義のため、AGENTS.mdの原則に従う:

| Gate | Status | Notes |
|------|--------|-------|
| Ruthless Simplicity | ✅ PASS | FastMCP + 単一プロジェクト構成 |
| Library-First | ✅ PASS | MCPサーバーとして独立したライブラリ |
| Test-First (TDD) | ✅ PASS | pytest + FastMCPインメモリテスト |
| Zero-BS (No Stubs) | ✅ PASS | 実際に動作するコードのみ作成 |
| Single Source of Truth | ✅ PASS | pyproject.tomlで設定一元管理 |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-note-mcp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── note_mcp/
│   ├── __init__.py
│   ├── server.py           # FastMCP サーバー定義
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── browser.py      # Playwright認証フロー
│   │   └── session.py      # keyringセッション管理
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py       # note.com APIクライアント
│   │   ├── articles.py     # 記事操作（CRUD）
│   │   └── images.py       # 画像アップロード
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── manager.py      # ブラウザインスタンス管理
│   │   ├── preview.py      # プレビュー表示
│   │   └── editor.py       # ブラウザUIエディタ操作（use_browser=True時）
│   └── utils/
│       ├── __init__.py
│       ├── markdown.py     # Markdown→HTML変換
│       └── logging.py      # セキュアログ（Cookie秘匿）

tests/
├── conftest.py
├── unit/
│   ├── test_session.py
│   ├── test_markdown.py
│   └── test_api_client.py
├── integration/
│   ├── test_auth_flow.py
│   └── test_article_operations.py
├── contract/
│   └── test_mcp_tools.py
└── e2e/                    # 手動実行、CIスキップ
    └── test_full_workflow.py
```

**Structure Decision**: Single project構成を選択。MCPサーバーとして独立して動作し、フロントエンド/バックエンド分離は不要。

---

## Complexity Tracking

> 現時点で Constitution Check に違反はないため、この表は空。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
