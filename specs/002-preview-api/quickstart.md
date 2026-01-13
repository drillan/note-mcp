# Quickstart: プレビューAPI対応

**Feature**: 002-preview-api
**Date**: 2025-01-13

## Overview

note.com MCP Serverのプレビュー機能をAPI経由に改善する機能の実装ガイド。

## Prerequisites

- Python 3.11+
- uv (パッケージマネージャー)
- note.comアカウント（認証用）

## Setup

```bash
# リポジトリクローン
cd /home/driller/repo/note-mcp

# 依存関係インストール
uv sync --all-groups

# テスト実行
uv run pytest tests/unit/ -v
```

## Implementation Steps

### Step 1: Preview API Module

`src/note_mcp/api/preview.py`を作成:

```python
"""Preview API functions for note.com.

Provides functionality to get preview access tokens
and fetch preview page HTML.
"""

from note_mcp.api.client import NoteAPIClient
from note_mcp.models import Session, NoteAPIError


async def get_preview_access_token(session: Session, article_key: str) -> str:
    """Get preview access token from note.com API.

    Args:
        session: Authenticated session
        article_key: Article key (e.g., "n1234567890ab")

    Returns:
        Preview access token (32-char hex string)

    Raises:
        NoteAPIError: If API request fails
    """
    async with NoteAPIClient(session) as client:
        response = await client.post(
            f"/v2/notes/{article_key}/access_tokens",
            json={"key": article_key},
        )
    data = response.get("data", {})
    return data.get("preview_access_token", "")


def build_preview_url(article_key: str, access_token: str) -> str:
    """Build preview URL with access token.

    Args:
        article_key: Article key
        access_token: Preview access token

    Returns:
        Full preview URL
    """
    return f"https://note.com/preview/{article_key}?prev_access_key={access_token}"
```

### Step 2: Update browser/preview.py

`src/note_mcp/browser/preview.py`を改修:

```python
"""Browser-based article preview using API access token."""

from note_mcp.api.preview import get_preview_access_token, build_preview_url
from note_mcp.browser.manager import BrowserManager
from note_mcp.models import Session


async def show_preview(session: Session, article_key: str) -> None:
    """Show article preview in browser via API.

    Gets preview access token via API and navigates directly
    to preview URL. Faster and more stable than editor-based approach.

    Args:
        session: Authenticated session
        article_key: Article key (e.g., "n1234567890ab")

    Raises:
        NoteAPIError: If token fetch fails
        RuntimeError: If browser navigation fails
    """
    # Get preview access token via API
    access_token = await get_preview_access_token(session, article_key)

    # Build preview URL
    preview_url = build_preview_url(article_key, access_token)

    # Get browser page
    manager = BrowserManager.get_instance()
    page = await manager.get_page()

    # Inject session cookies
    await _inject_session_cookies(page, session)

    # Navigate directly to preview URL
    await page.goto(preview_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")
```

### Step 3: Add note_get_preview_html Tool

`src/note_mcp/server.py`に追加:

```python
@mcp.tool()
async def note_get_preview_html(
    article_key: Annotated[str, "取得する記事のキー（例: n1234567890ab）"],
) -> str:
    """プレビューページのHTMLを取得します。

    指定した記事のプレビューページのHTMLを文字列として取得します。
    E2Eテストやコンテンツ検証のために使用します。

    Args:
        article_key: 取得する記事のキー

    Returns:
        プレビューページのHTML
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    try:
        html = await get_preview_html(session, article_key)
        return html
    except NoteAPIError as e:
        return f"エラー: {e}"
```

## Testing

### Unit Tests

```bash
# プレビューAPI単体テスト
uv run pytest tests/unit/test_preview_api.py -v
```

### Integration Tests

```bash
# 認証が必要なE2Eテスト
uv run pytest tests/integration/test_preview_e2e.py -v -m requires_auth
```

## Usage Examples

### MCP Client (Claude等)

```
ユーザー: 記事のプレビューを表示して
AI: note_show_preview(article_key="n1234567890ab")
→ ブラウザでプレビューページが開く

ユーザー: 記事のHTMLを取得して
AI: note_get_preview_html(article_key="n1234567890ab")
→ HTMLが文字列として返される
```

### Python Direct

```python
from note_mcp.api.preview import get_preview_access_token, get_preview_html
from note_mcp.auth.session import SessionManager

# セッション取得
session_manager = SessionManager()
session = session_manager.load()

# プレビューHTML取得
html = await get_preview_html(session, "n1234567890ab")
print(f"HTML length: {len(html)} bytes")

# トークン単独取得
token = await get_preview_access_token(session, "n1234567890ab")
print(f"Token: {token[:8]}...")
```

## Performance Expectations

| Operation | Target | Measurement |
|-----------|--------|-------------|
| note_show_preview | < 3秒 | ツール呼び出し〜ブラウザ表示 |
| note_get_preview_html | < 5秒 | ツール呼び出し〜HTML返却 |
| get_preview_access_token | < 500ms | API呼び出し〜レスポンス |

## Automatic Retry

`get_preview_html`は認証エラー（401/403）発生時に自動リトライします：

1. プレビューアクセストークンを取得
2. HTMLを取得（失敗時）
3. 401/403の場合、新しいトークンを再取得して1回リトライ
4. それでも失敗した場合はエラーを返す

これにより、トークン期限切れ時も自動的に復旧します。

## Troubleshooting

### 認証エラー

```
エラー: セッションが無効です。note_loginでログインしてください。
```

→ `note_login`でログインしてください。

### 記事が見つからない

```
エラー: 記事が見つかりませんでした。
```

→ 記事キーが正しいか確認してください（`n`で始まる英数字）。

### 権限エラー

```
エラー: アクセス権がありません。
```

→ 自分の記事のみプレビュー可能です。他ユーザーの記事にはアクセスできません。
