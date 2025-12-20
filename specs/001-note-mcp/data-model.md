# Data Model: note.com MCP Server

**Date**: 2025-12-20
**Feature**: 001-note-mcp

## Overview

このドキュメントはnote.com MCPサーバーのデータモデルを定義します。

---

## Entities

### 1. Session（セッション）

ユーザーの認証状態を管理するエンティティ。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| cookies | dict[str, str] | Yes | note.com認証Cookie（note_gql_auth_token, _note_session_v5） |
| user_id | str | Yes | note.comユーザーID |
| username | str | Yes | note.comユーザー名（URLパスに使用） |
| expires_at | int | No | セッション有効期限（Unix timestamp） |
| created_at | int | Yes | セッション作成日時（Unix timestamp） |

**State Transitions**:
- `unauthenticated` → `authenticating` → `authenticated`
- `authenticated` → `expired` → `unauthenticated`

**Validation Rules**:
- cookiesは`note_gql_auth_token`と`_note_session_v5`を含む必要がある
- expires_atが現在時刻を過ぎている場合はexpired状態

**Storage**: keyring (OS keychain/credential manager)

```python
from pydantic import BaseModel
from typing import Optional

class Session(BaseModel):
    cookies: dict[str, str]
    user_id: str
    username: str
    expires_at: Optional[int] = None
    created_at: int

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        import time
        return time.time() > self.expires_at
```

---

### 2. Article（記事）

note.comの記事を表すエンティティ。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | Yes | 記事ID（note.com内部ID） |
| key | str | Yes | 記事キー（URLパスに使用） |
| title | str | Yes | 記事タイトル |
| body | str | Yes | 記事本文（HTML形式） |
| status | ArticleStatus | Yes | 記事ステータス |
| tags | list[str] | No | ハッシュタグ |
| eyecatch_image_key | str | No | アイキャッチ画像キー |
| created_at | str | No | 作成日時（ISO 8601） |
| updated_at | str | No | 更新日時（ISO 8601） |
| published_at | str | No | 公開日時（ISO 8601） |
| url | str | No | 記事URL |

**ArticleStatus Enum**:
```python
from enum import Enum

class ArticleStatus(str, Enum):
    DRAFT = "draft"           # 下書き
    PUBLISHED = "published"   # 公開済み
    PRIVATE = "private"       # 非公開
```

**Validation Rules**:
- titleは必須で空文字不可
- bodyはHTML形式
- statusは有効なArticleStatus値

**Storage**: note.com API（永続化はnote.com側）

```python
from pydantic import BaseModel
from typing import Optional

class Article(BaseModel):
    id: str
    key: str
    title: str
    body: str
    status: ArticleStatus
    tags: list[str] = []
    eyecatch_image_key: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    published_at: Optional[str] = None
    url: Optional[str] = None
```

---

### 3. ArticleInput（記事入力）

記事作成・更新時の入力データ。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | str | Yes | 記事タイトル |
| body | str | Yes | 記事本文（Markdown形式） |
| tags | list[str] | No | ハッシュタグ |
| eyecatch_image_path | str | No | アイキャッチ画像のローカルパス |

**Validation Rules**:
- titleは1文字以上
- bodyは空文字可（下書きとして保存）
- tagsは各タグが#で始まる必要はない（自動付与）

```python
from pydantic import BaseModel
from typing import Optional

class ArticleInput(BaseModel):
    title: str
    body: str
    tags: list[str] = []
    eyecatch_image_path: Optional[str] = None
```

---

### 4. Image（画像）

アップロードされた画像を表すエンティティ。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| key | str | Yes | note.com画像キー |
| url | str | Yes | 画像URL |
| original_path | str | Yes | アップロード元のローカルパス |
| size_bytes | int | No | ファイルサイズ（バイト） |
| uploaded_at | int | Yes | アップロード日時（Unix timestamp） |

**Validation Rules**:
- keyはnote.comから返される値
- urlは有効なHTTPS URL
- size_bytesは画像サイズ制限内（note.comの制限に従う）

```python
from pydantic import BaseModel
from typing import Optional

class Image(BaseModel):
    key: str
    url: str
    original_path: str
    size_bytes: Optional[int] = None
    uploaded_at: int
```

---

### 5. Tag（タグ）

記事に付与するハッシュタグ。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | Yes | タグ名（#なし） |

**Validation Rules**:
- nameは1文字以上
- 先頭の#は自動的に除去される

```python
from pydantic import BaseModel

class Tag(BaseModel):
    name: str

    @classmethod
    def normalize(cls, tag: str) -> str:
        """タグを正規化（#を除去）"""
        return tag.lstrip('#')
```

---

## Relationships

```
Session 1 ──── * Article (ユーザーは複数の記事を持つ)
Article 1 ──── * Tag (記事は複数のタグを持つ)
Article 1 ──── 0..1 Image (アイキャッチ画像)
```

---

## API Response Mapping

### note.com API → Article

```python
def from_api_response(data: dict) -> Article:
    """note.com APIレスポンスからArticleを生成"""
    return Article(
        id=str(data.get("id", "")),
        key=data.get("key", ""),
        title=data.get("name", ""),
        body=data.get("body", ""),
        status=ArticleStatus(data.get("status", "draft")),
        tags=[t.get("hashtag", {}).get("name", "") for t in data.get("hashtags", [])],
        eyecatch_image_key=data.get("eyecatch_image_key"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        published_at=data.get("publish_at"),
        url=data.get("noteUrl")
    )
```

### ArticleInput → note.com API Request

```python
def to_api_request(input: ArticleInput, html_body: str) -> dict:
    """ArticleInputをnote.com APIリクエスト形式に変換"""
    return {
        "name": input.title,
        "body": html_body,  # Markdown→HTML変換済み
        "status": "draft",
        # tags and eyecatch are handled separately
    }
```

---

## Error Types

```python
from enum import Enum

class ErrorCode(str, Enum):
    NOT_AUTHENTICATED = "not_authenticated"
    SESSION_EXPIRED = "session_expired"
    ARTICLE_NOT_FOUND = "article_not_found"
    RATE_LIMITED = "rate_limited"
    API_ERROR = "api_error"
    UPLOAD_FAILED = "upload_failed"
    INVALID_INPUT = "invalid_input"
```

```python
class NoteAPIError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)
```
