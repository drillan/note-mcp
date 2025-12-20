# Research: note.com MCP Server

**Date**: 2025-12-20
**Feature**: 001-note-mcp

## Overview

このドキュメントはnote.com MCPサーバー実装のための技術調査結果をまとめたものです。

---

## 1. note.com 非公式API

### Decision
note.com非公式APIを使用し、ハイブリッドアプローチ（API + ブラウザUI）で実装する。

### Rationale
- APIは高速な操作が可能
- ブラウザUIはプレビュー表示や複雑なエディタ操作に適している
- Cookie認証によりPlaywrightでのログイン後にAPIを使用可能

### Key Findings

#### ベースURL
```
https://note.com/api
```

#### 記事作成 (POST)
```
POST https://note.com/api/v1/text_notes
```

**リクエスト**:
```json
{
  "body": "<HTML形式のコンテンツ>",
  "name": "<記事タイトル>",
  "template_key": null,
  "status": "draft"
}
```

**注意**: bodyフィールドはHTML形式が必須

#### 記事更新 (PUT)
```
PUT https://note.com/api/v1/text_notes/{article_id}
```

**リクエスト**:
```json
{
  "body": "<HTML形式のコンテンツ>",
  "name": "<記事タイトル>",
  "status": "draft",
  "eyecatch_image_key": "<画像キー>"
}
```

#### 記事一覧取得 (GET)
```
GET https://note.com/api/v2/creators/{ユーザー名}/contents?kind=note&page={ページ番号}
```

**制限**: 1回のリクエストで最大10記事

#### 画像アップロード (POST)
```
POST https://note.com/api/v1/upload_image
```

**リクエスト**: multipart/form-data形式で`file`フィールドに画像データ

**レスポンス**: `image_key`が返される（アイキャッチ画像設定に使用）

#### 認証Cookie
必要なCookie:
- `note_gql_auth_token`
- `_note_session_v5`

### Alternatives Considered
1. **完全ブラウザ自動化**: 遅いが安定
2. **完全API**: 高速だがプレビュー不可
3. **ハイブリッド（選択）**: 両方の利点を活かす

---

## 2. FastMCP フレームワーク

### Decision
FastMCP 2.0を使用してMCPサーバーを構築する。

### Rationale
- デコレーターベースのシンプルなAPI
- 型ヒントから自動スキーマ生成
- 非同期処理のネイティブサポート
- テスティングフレームワーク内蔵

### Installation
```bash
uv add fastmcp
```

### Key Patterns

#### ツール定義
```python
from fastmcp import FastMCP

mcp = FastMCP("note-mcp")

@mcp.tool()
def create_draft(title: str, body: str, tags: list[str] | None = None) -> dict:
    """Create a new draft article on note.com

    Args:
        title: Article title
        body: Article content in Markdown format
        tags: Optional list of hashtags
    """
    # Implementation
    return {"article_id": "xxx", "preview_url": "https://..."}
```

#### エラーハンドリング
```python
from fastmcp import ClientError

@mcp.tool()
def update_article(article_id: str, body: str) -> dict:
    """Update an existing article"""
    try:
        # Implementation
        return result
    except AuthenticationError:
        raise ClientError("Not authenticated. Please run login tool first.")
```

#### コンテキストアクセス
```python
from fastmcp import FastMCP, Context

@mcp.tool()
async def process_article(uri: str, ctx: Context):
    await ctx.info("Processing article...")
    # Implementation
```

### Alternatives Considered
1. **公式MCP SDK（低レベル）**: より細かい制御可能だがボイラープレート多い
2. **FastMCP（選択）**: シンプルで十分な機能

---

## 3. Playwright ブラウザ自動化

### Decision
Playwrightを使用し、Storage State APIでセッション永続化を行う。

### Rationale
- クロスブラウザサポート
- 非同期APIのネイティブサポート
- Storage State APIでCookie/セッション永続化が容易
- 自動待機機能で安定した操作

### Installation
```bash
uv add playwright
playwright install chromium
```

### Key Patterns

#### 認証フロー
```python
from playwright.async_api import async_playwright

async def login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # ユーザーが見える
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto('https://note.com/login')
        # ユーザーが手動でログイン
        await page.wait_for_url('**/dashboard', timeout=300000)  # 5分待機

        # セッション保存
        await context.storage_state(path='session.json')
        await browser.close()
```

#### セッション再利用
```python
async def with_session():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state='session.json')
        page = await context.new_page()
        # すでにログイン済み
```

#### Cookie抽出（API用）
```python
cookies = await context.cookies()
cookie_dict = {c['name']: c['value'] for c in cookies}
# httpxに渡す
```

### Alternatives Considered
1. **Selenium**: 古いが広く使われている
2. **Puppeteer (Node.js)**: Python連携が複雑
3. **Playwright（選択）**: モダンで非同期サポートが優れている

---

## 4. keyring セッション管理

### Decision
keyringライブラリを使用してセッション情報をOSキーチェーンに保存する。

### Rationale
- OSネイティブの安全なストレージを使用
- クロスプラットフォーム対応（macOS Keychain, Windows Credential Vault, Linux Secret Service）
- 平文ファイル保存よりセキュア

### Installation
```bash
uv add keyring
```

### Key Patterns

#### セッション保存
```python
import keyring
import json

SERVICE_NAME = "note-mcp"

def save_session(session_data: dict) -> None:
    """セッションデータをkeychainに保存"""
    keyring.set_password(
        SERVICE_NAME,
        "session",
        json.dumps(session_data)
    )

def load_session() -> dict | None:
    """keychainからセッションデータを読み込み"""
    stored = keyring.get_password(SERVICE_NAME, "session")
    if stored is None:
        return None
    return json.loads(stored)

def clear_session() -> None:
    """keychainからセッションデータを削除"""
    try:
        keyring.delete_password(SERVICE_NAME, "session")
    except keyring.errors.PasswordDeleteError:
        pass  # 存在しない場合は無視
```

#### 保存するセッションデータ
```python
session_data = {
    "cookies": {
        "note_gql_auth_token": "xxx",
        "_note_session_v5": "yyy"
    },
    "user_id": "user123",
    "username": "example_user",
    "expires_at": 1234567890
}
```

### Alternatives Considered
1. **環境変数**: セッションの動的更新が困難
2. **ファイル保存（暗号化）**: 自前で暗号化が必要
3. **keyring（選択）**: OS標準のセキュアストレージを活用

---

## 5. Markdown→HTML変換

### Decision
markdown-it-pyを使用してMarkdownをHTMLに変換する。

### Rationale
- CommonMark準拠
- 拡張可能
- Pythonで軽量

### Installation
```bash
uv add markdown-it-py
```

### Key Pattern
```python
from markdown_it import MarkdownIt

def markdown_to_html(content: str) -> str:
    """MarkdownをHTMLに変換"""
    md = MarkdownIt()
    return md.render(content)
```

### Alternatives Considered
1. **Python-Markdown**: 十分だが設定が複雑
2. **mistune**: 高速だがCommonMark非準拠
3. **markdown-it-py（選択）**: CommonMark準拠で拡張可能

---

## 6. HTTP APIクライアント

### Decision
httpxを使用してnote.com APIを呼び出す。

### Rationale
- 非同期サポート
- requestsと互換性のあるAPI
- Cookie管理が容易

### Installation
```bash
uv add httpx
```

### Key Pattern
```python
import httpx

async def api_client(cookies: dict):
    async with httpx.AsyncClient(
        base_url="https://note.com/api",
        cookies=cookies,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    ) as client:
        response = await client.post(
            "/v1/text_notes",
            json={"name": "Title", "body": "<p>Content</p>", "status": "draft"}
        )
        return response.json()
```

---

## 7. テスティング戦略

### Decision
pytest + pytest-asyncio + pytest-mcpを使用する。

### Rationale
- FastMCPのインメモリテスト機能を活用
- 非同期テストをネイティブサポート
- MCPプロトコル準拠テストが可能

### Installation
```bash
uv add --dev pytest pytest-asyncio pytest-mcp
```

### Key Patterns

#### ユニットテスト
```python
import pytest
from note_mcp.utils.markdown import markdown_to_html

def test_markdown_to_html():
    result = markdown_to_html("# Hello")
    assert "<h1>Hello</h1>" in result
```

#### MCPツールテスト
```python
import pytest
from fastmcp.client import FastMCPClient
from note_mcp.server import mcp

@pytest.mark.asyncio
async def test_create_draft():
    async with FastMCPClient(mcp) as client:
        result = await client.call_tool(
            "create_draft",
            title="Test",
            body="# Content"
        )
        assert "article_id" in result
```

---

## Version Summary

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.11+ | Runtime |
| fastmcp | latest | MCP server framework |
| playwright | latest | Browser automation |
| keyring | 25.7.0+ | Secure credential storage |
| httpx | latest | HTTP API client |
| markdown-it-py | latest | Markdown→HTML conversion |
| pytest | latest | Testing framework |
| pytest-asyncio | latest | Async test support |
| pytest-mcp | latest | MCP protocol testing |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| note.com API変更 | エラーハンドリングを充実させ、API変更を検知しやすくする |
| セッション期限切れ | 有効期限を監視し、再認証を促す |
| レート制限 | リクエスト間隔を制御（10リクエスト/分目安） |
| Playwright認証失敗 | タイムアウトを長めに設定、リトライ機能を実装 |
