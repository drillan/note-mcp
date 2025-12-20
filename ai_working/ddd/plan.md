# DDD Phase 1 Plan: note.com MCP Server

**Feature Branch**: `001-note-mcp`
**Date**: 2025-12-20
**Status**: Phase 1 Complete

---

## 1. Problem Statement

### What We're Solving

note.com（日本の人気ブログプラットフォーム）の記事管理を、AIアシスタント（Claude等）から直接行えるようにするMCPサーバーの構築。

### User Pain Points

1. **手動操作の煩雑さ**: 記事の下書き→編集→公開のワークフローが手動で時間がかかる
2. **コンテキストスイッチ**: Claude Codeで記事を書いた後、別途ブラウザでnote.comを操作する必要がある
3. **繰り返し作業**: 画像アップロード→URL取得→記事への挿入が手作業

### Core Value Proposition

- AIアシスタントとの会話の中で、シームレスにnote.comの記事を作成・編集・公開
- Playwrightによるブラウザ自動化で、認証とプレビュー表示を実現
- **ハイブリッドアプローチ**: API-first（高速）+ ブラウザUI（認証・プレビュー・ユーザー選択時）

### Constraints

- **非公式API依存**: note.comの仕様変更により動作しなくなる可能性
- **自己責任・無保証**: オープンソース公開時に明記
- **デスクトップ限定**: Playwrightが動作する環境が必要

---

## 2. Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code / MCP Client                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastMCP Server                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  MCP Tools                                           │    │
│  │  • note_login      • note_create_draft              │    │
│  │  • note_check_auth • note_update_article            │    │
│  │  • note_logout     • note_publish_article           │    │
│  │  • note_list_articles • note_upload_image           │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│         ┌────────────────────┼────────────────────┐         │
│         ▼                    ▼                    ▼         │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │   Auth      │      │   API       │      │   Browser   │ │
│  │  (Session)  │      │  (httpx)    │      │ (Playwright)│ │
│  └─────────────┘      └─────────────┘      └─────────────┘ │
│         │                    │                    │         │
│         ▼                    │                    │         │
│  ┌─────────────┐             │                    │         │
│  │   keyring   │             │                    │         │
│  │ (Secure     │             │                    │         │
│  │  Storage)   │             ▼                    ▼         │
│  └─────────────┘      ┌─────────────────────────────────┐  │
│                       │         note.com                 │  │
│                       │   (API + Web UI)                 │  │
│                       └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| MCP Framework | FastMCP | シンプル、デコレーターベース、型ヒント自動スキーマ生成 |
| 認証方式 | Playwright + Cookie | ブラウザ認証でCookie取得、API呼び出しに再利用 |
| セッション保存 | keyring | OSネイティブのセキュアストレージ |
| API Client | httpx | 非同期対応、Cookie管理が容易 |
| Markdown変換 | markdown-it-py | CommonMark準拠、軽量 |
| ブラウザ管理 | シングルトン + asyncio.Lock | リソース効率、並行制御 |

### Operation Mode (API vs Browser)

**ユーザー選択制**（フォールバックなし）

| 操作 | 利用可能モード | デフォルト | 備考 |
|------|---------------|-----------|------|
| ログイン | ブラウザのみ | ブラウザ | Cookie取得必須 |
| 認証確認 | APIのみ | API | 高速 |
| 下書き作成 | API / ブラウザ | API | `use_browser=True`で選択可 |
| 記事更新 | API / ブラウザ | API | `use_browser=True`で選択可 |
| 記事公開 | API / ブラウザ | API | `use_browser=True`で選択可 |
| 記事一覧 | APIのみ | API | ブラウザでは非効率 |
| 画像アップ | APIのみ | API | multipart送信 |
| プレビュー | ブラウザのみ | ブラウザ | 視覚確認 |

**エラー処理方針**: APIモードで失敗した場合はエラーを返す（自動フォールバックなし）

---

## 3. Alternatives Considered

### A1: 完全ブラウザ自動化（Rejected）

**アプローチ**: すべての操作をPlaywrightで実行
**Pros**: 安定性（公式UIを使用）
**Cons**: 遅い、リソース消費大
**却下理由**: 記事作成に数十秒かかり、インタラクティブな執筆に不向き

### A2: 完全API（Rejected）

**アプローチ**: ブラウザを使わずAPIのみ
**Pros**: 高速、軽量
**Cons**: 認証困難（CAPTCHA等）、プレビュー不可
**却下理由**: ログインにブラウザが必要、プレビュー表示もユーザー要件

### A3: ハイブリッド（Adopted）

**アプローチ**: API-first + ブラウザ（認証・プレビュー）
**Pros**: 高速な操作 + 必要な場面でブラウザ利用
**Cons**: 実装複雑度がやや上昇
**採用理由**: ユーザー要件（プレビュー表示）を満たしつつ、快適な操作性

---

## 4. Architecture & Design

### Module Structure

```
src/note_mcp/
├── __init__.py
├── server.py           # FastMCP サーバー定義（エントリーポイント）
├── auth/
│   ├── __init__.py
│   ├── browser.py      # Playwright認証フロー
│   └── session.py      # keyringセッション管理
├── api/
│   ├── __init__.py
│   ├── client.py       # note.com APIクライアント（httpx）
│   ├── articles.py     # 記事操作（CRUD）
│   └── images.py       # 画像アップロード
├── browser/
│   ├── __init__.py
│   ├── manager.py      # BrowserManager（シングルトン）
│   ├── preview.py      # プレビュー表示
│   └── editor.py       # ブラウザUIエディタ操作（use_browser=True時）
└── utils/
    ├── __init__.py
    ├── markdown.py     # Markdown→HTML変換
    └── logging.py      # セキュアログ（Cookie秘匿）
```

### Data Models

```python
# Session（セッション）
class Session(BaseModel):
    cookies: dict[str, str]  # note_gql_auth_token, _note_session_v5
    user_id: str
    username: str
    expires_at: Optional[int] = None
    created_at: int

# Article（記事）
class Article(BaseModel):
    id: str
    key: str
    title: str
    body: str  # HTML形式
    status: ArticleStatus  # draft, published, private
    tags: list[str] = []
    eyecatch_image_key: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    url: Optional[str] = None
```

### Key Patterns

**BrowserManager Singleton**:
```python
class BrowserManager:
    _instance: Optional["BrowserManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "BrowserManager":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def get_page(self) -> Page:
        async with self._lock:
            # 既存ページを返すか、なければ新規作成
            ...
```

**Session Lifecycle**:
```
[未認証] ──login──> [認証中] ──success──> [認証済み]
    ^                                         │
    │                                         v
    └────────────────────────────── [期限切れ検知]
```

---

## 5. Files to Change

### Non-Code Files

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Create | 依存関係、Python 3.11+設定 |
| `README.md` | Create | インストール手順、使用方法 |
| `DISCLAIMER.md` | Create | 自己責任・無保証の免責事項 |
| `.github/workflows/test.yml` | Create | CI設定（E2Eはスキップ） |

### Code Files

| File | Action | Priority | FR Coverage |
|------|--------|----------|-------------|
| `src/note_mcp/__init__.py` | Create | P0 | - |
| `src/note_mcp/server.py` | Create | P1 | All tools entry |
| `src/note_mcp/auth/session.py` | Create | P1 | FR-002, FR-008, FR-011 |
| `src/note_mcp/auth/browser.py` | Create | P1 | FR-001 |
| `src/note_mcp/api/client.py` | Create | P1 | FR-009, FR-010 |
| `src/note_mcp/api/articles.py` | Create | P1 | FR-003, FR-004, FR-005, FR-006 |
| `src/note_mcp/api/images.py` | Create | P1 | FR-007 |
| `src/note_mcp/browser/manager.py` | Create | P1 | FR-013 |
| `src/note_mcp/browser/preview.py` | Create | P1 | FR-012 |
| `src/note_mcp/browser/editor.py` | Create | P2 | FR-009 use_browser option |
| `src/note_mcp/utils/markdown.py` | Create | P1 | FR-009 |
| `src/note_mcp/utils/logging.py` | Create | P1 | Security |

### Test Files

| File | Action | Category |
|------|--------|----------|
| `tests/conftest.py` | Create | Fixtures |
| `tests/unit/test_session.py` | Create | Unit |
| `tests/unit/test_markdown.py` | Create | Unit |
| `tests/unit/test_api_client.py` | Create | Unit |
| `tests/integration/test_auth_flow.py` | Create | Integration |
| `tests/integration/test_article_operations.py` | Create | Integration |
| `tests/contract/test_mcp_tools.py` | Create | MCP Contract |

---

## 6. Philosophy Alignment

### Ruthless Simplicity ✅

- **FastMCP**: 最小限のボイラープレート
- **Single Project**: モノリシックMCPサーバー、分離不要
- **Direct API Usage**: httpxを直接使用、過度なラッパーなし

### YAGNI ✅

- **Phase分割**: P1機能を先に実装、P2は後回し
- **ユーザー選択制**: ブラウザモードは`use_browser=True`で明示的に選択
- **設定オプション最小**: デフォルト値で動作

### Zero-BS ✅

- **No Stubs**: 各フェーズで動作するコードを作成
- **実E2Eテスト**: ローカルで実際のnote.comでテスト

### Test-First ✅

- **Unit Tests先行**: 各モジュール実装前にテスト作成
- **Mocked Integration**: CI用にモック化された統合テスト

---

## 7. Test Strategy

### Testing Matrix

| Category | Scope | CI | Local |
|----------|-------|-----|-------|
| Unit | Session, Markdown, Utils | ✅ | ✅ |
| Integration (Mock) | API Client, Auth Flow | ✅ | ✅ |
| MCP Contract | Tool schema, responses | ✅ | ✅ |
| E2E (Browser) | Playwright操作 | ❌ | ✅ (手動) |
| E2E (Full) | 実note.com | ❌ | ✅ (手動) |

### CI Design (No Secrets)

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests
        run: uv run pytest tests/unit -v
      - name: Run integration tests (mocked)
        run: uv run pytest tests/integration -v -m "not requires_auth"
      - name: Run MCP contract tests
        run: uv run pytest tests/contract -v
```

### Key Test Scenarios

1. **Session Persistence**: keyring保存→読み込み→有効性確認
2. **Markdown Conversion**: 各種Markdown要素のHTML変換
3. **API Error Handling**: 401/403/5xx/レート制限
4. **Browser Reuse**: 既存ウィンドウの再利用確認

---

## 8. Implementation Approach

### Phase 0: 基盤構築

**目標**: プロジェクト構造セットアップ
**成果物**: pyproject.toml, ディレクトリ構造
**完了条件**:
- [ ] `uv sync` 成功
- [ ] `uv run playwright install chromium` 成功
- [ ] `uv run pytest` 実行可能

### Phase 1: 認証基盤 (P1)

**目標**: ログイン/ログアウト/認証確認
**成果物**: auth/, tests/unit/test_session.py
**完了条件**:
- [ ] `note_login` ツール動作
- [ ] `note_check_auth` ツール動作
- [ ] `note_logout` ツール動作
- [ ] keyringエラー時の診断情報実装
- [ ] Unit tests合格

### Phase 2: 記事操作 (P1)

**目標**: 下書き作成・更新
**成果物**: api/articles.py, browser/preview.py, utils/markdown.py
**完了条件**:
- [ ] `note_create_draft` ツール動作
- [ ] `note_update_article` ツール動作
- [ ] Markdown→HTML変換正常
- [ ] ブラウザプレビュー表示
- [ ] Unit/Integration tests合格

### Phase 3: 画像アップロード (P1)

**目標**: 画像アップロード
**成果物**: api/images.py
**完了条件**:
- [ ] `note_upload_image` ツール動作
- [ ] JPEG/PNG/GIF/WebP対応
- [ ] ファイルサイズ検証
- [ ] Unit tests合格

### Phase 4: 追加機能 (P2)

**目標**: 記事公開・一覧取得
**成果物**: articles.py拡張
**完了条件**:
- [ ] `note_publish_article` ツール動作
- [ ] `note_list_articles` ツール動作
- [ ] ステータスフィルタ正常

### Phase 5: 仕上げ

**目標**: ドキュメント・CI・リリース準備
**成果物**: README.md, DISCLAIMER.md, CI設定
**完了条件**:
- [ ] 全テスト合格
- [ ] ドキュメント完備
- [ ] CI設定完了

---

## 9. Success Criteria

### Measurable Outcomes

| Metric | Target | Measurement |
|--------|--------|-------------|
| 初回ログイン→下書き作成 | 5分以内 | E2Eテストで計測 |
| セッション有効期間 | 24時間+ | 実運用で確認 |
| 記事操作レイテンシ | 30秒以内 | E2Eテストで計測 |
| 記事一覧取得 | 10秒以内 | E2Eテストで計測 |
| 画像アップロード (1MB) | 15秒以内 | E2Eテストで計測 |
| エラーメッセージ明確性 | 100% | レビューで確認 |

### Quality Gates

- [ ] 全Unit testsが合格
- [ ] 全Integration testsが合格（mock）
- [ ] MCP Contract testsが合格
- [ ] ローカルE2Eテスト成功
- [ ] README.mdに使用方法記載
- [ ] DISCLAIMER.mdに免責事項記載
- [ ] CIがSecrets無しで成功

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| note.com API仕様変更 | Medium | High | バージョン固定、エラー検知充実 |
| セッション期限短縮 | Low | Medium | 期限検知と再認証導線 |
| レート制限強化 | Low | Medium | バックオフ戦略実装 |
| Playwright環境依存 | Low | Medium | ドキュメントで要件明記 |
| keyring非対応環境 | Medium | Low | 明確なエラーメッセージで設定手順を案内 |

---

## 11. Phase 6: note_get_article 実装 (P1追加)

**追加日**: 2025-12-20
**理由**: 既存の `note_update_article` が完全上書きのため、「一部修正」「追記」などの編集操作に対応できない

### Problem Statement

現在の `note_update_article` は既存記事の内容を読み取らずに完全上書きするため、AIが適切な編集を行えない。

**ユーザー価値**:
- 「この記事の末尾に追記して」という指示に対応可能
- 「タイトルだけ変更して」という指示で本文を維持できる
- 既存記事の内容を確認してから編集できる

### Proposed Solution

ブラウザベースのアプローチで `note_get_article` を実装。

**推奨ワークフロー**:
```
1. note_get_article(article_id) で既存内容を取得
2. AI/ユーザーが編集内容を決定（追記、修正、置換など）
3. note_update_article(article_id, title, body, tags) で保存
```

**実装方式**:
- `https://editor.note.com/notes/{article_id}/edit/` に移動
- DOM からタイトルと本文を抽出
- プレーンテキストとして返す（innerText）

### Files to Change

| File | Action | Purpose |
|------|--------|---------|
| `src/note_mcp/browser/get_article.py` | Create | ブラウザベースの記事取得 |
| `src/note_mcp/api/articles.py` | Modify | `get_article()` 関数追加 |
| `src/note_mcp/server.py` | Modify | `note_get_article` MCPツール追加 |
| `tests/integration/test_article_operations.py` | Modify | テスト追加 |
| `README.md` | Modify | ツール説明追加 |

### Implementation Chunks

**Chunk 1**: `browser/get_article.py`
```python
"""Browser-based article retrieval for note.com."""

async def get_article_via_browser(
    session: Session,
    article_id: str,
) -> Article:
    manager = BrowserManager.get_instance()
    page = await manager.get_page()

    # Cookie インジェクション
    # エディタページに移動
    # ネットワーク安定待機
    # タイトル取得: input[placeholder*="タイトル"]
    # 本文取得: .ProseMirror の innerText
    # Article オブジェクト構築
```

**Chunk 2**: `api/articles.py`
```python
async def get_article(session: Session, article_id: str) -> Article:
    from note_mcp.browser.get_article import get_article_via_browser
    return await get_article_via_browser(session, article_id)
```

**Chunk 3**: `server.py`
```python
@mcp.tool()
async def note_get_article(
    article_id: Annotated[str, "取得する記事のID"],
) -> str:
    """記事の内容を取得します。"""
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    article = await get_article(session, article_id)
    return f"""記事を取得しました。

タイトル: {article.title}
ステータス: {article.status.value}
タグ: {', '.join(article.tags) if article.tags else 'なし'}

本文:
{article.body}
"""
```

### Success Criteria

- [ ] `note_get_article(article_id)` で記事内容が取得できる
- [ ] 取得した内容をそのまま `note_update_article` に渡しても内容が維持される
- [ ] 「末尾に追記」のワークフローが動作する
- [ ] コード品質チェック通過（ruff, mypy）
- [ ] テスト通過

### Philosophy Alignment

- **Ruthless Simplicity**: 既存パターン（update_article）を踏襲、APIフォールバック不要
- **Modular Design**: `get_article.py` は自己完結モジュール
- **Clear Interfaces**: `Article` モデルを共通インターフェースとして使用

---

## Appendix: Reference Documents

- [Feature Specification](../../specs/001-note-mcp/spec.md)
- [Implementation Plan](../../specs/001-note-mcp/plan.md)
- [Research Notes](../../specs/001-note-mcp/research.md)
- [Data Model](../../specs/001-note-mcp/data-model.md)
- [MCP Tools Contract](../../specs/001-note-mcp/contracts/mcp-tools.yaml)
- [Quickstart Guide](../../specs/001-note-mcp/quickstart.md)
