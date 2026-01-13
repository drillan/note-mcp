# Data Model: プレビューAPI対応

**Feature**: 002-preview-api
**Date**: 2025-01-13
**Status**: Complete

## Overview

プレビューAPI機能に関連するエンティティとデータ構造の定義。

## Entities

### PreviewAccessToken

プレビューアクセストークン。下書き記事のプレビューにアクセスするための一時的なトークン。

**Purpose**: API経由で取得し、プレビューURLの認証に使用

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| token | str | Yes | 32文字の16進数文字列（APIレスポンスから取得） |
| article_key | str | Yes | 対象記事のキー（例: "n1234567890ab"） |
| created_at | int | Yes | トークン取得時刻（Unixタイムスタンプ） |

**Validation Rules**:
- `token`: 32文字の16進数文字列（`[0-9a-f]{32}`）
- `article_key`: "n"で始まる英数字（`n[a-z0-9]+`）
- `created_at`: 正の整数

**Pydantic Model**:
```python
class PreviewAccessToken(BaseModel):
    """Preview access token for draft articles.

    Attributes:
        token: 32-character hex string from API
        article_key: Article key (e.g., "n1234567890ab")
        created_at: Token creation timestamp (Unix timestamp)
    """
    token: str
    article_key: str
    created_at: int

    @field_validator("token")
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{32}$", v):
            raise ValueError("Token must be 32 hex characters")
        return v
```

### PreviewURL

プレビューURL。記事のプレビューページにアクセスするためのURL。

**Purpose**: プレビュートークンを含む完全なプレビューURLを構築

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| base_url | str | Yes | 固定値: "https://note.com/preview" |
| article_key | str | Yes | 記事キー |
| access_token | str | Yes | プレビューアクセストークン |

**Constructed URL Format**:
```
https://note.com/preview/{article_key}?prev_access_key={access_token}
```

**Helper Function**:
```python
def build_preview_url(article_key: str, access_token: str) -> str:
    """Build preview URL with access token.

    Args:
        article_key: Article key (e.g., "n1234567890ab")
        access_token: Preview access token from API

    Returns:
        Full preview URL
    """
    return f"https://note.com/preview/{article_key}?prev_access_key={access_token}"
```

### PreviewHTMLResult

プレビューHTML取得結果。

**Purpose**: プログラム用のHTML取得結果を格納

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| html | str | Yes | プレビューページのHTML |
| article_key | str | Yes | 記事キー |
| fetched_at | int | Yes | 取得時刻（Unixタイムスタンプ） |
| content_length | int | Yes | HTMLのバイト長 |

**Pydantic Model**:
```python
class PreviewHTMLResult(BaseModel):
    """Result of preview HTML fetch.

    Attributes:
        html: Preview page HTML content
        article_key: Article key
        fetched_at: Fetch timestamp (Unix timestamp)
        content_length: HTML content length in bytes
    """
    html: str
    article_key: str
    fetched_at: int
    content_length: int
```

## Existing Entities (Reference)

### Session (既存、変更なし)

認証セッション。既存の`src/note_mcp/models.py`で定義済み。

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| cookies | dict[str, str] | Yes | 認証Cookie |
| user_id | str | Yes | ユーザーID |
| username | str | Yes | ユーザー名 |
| expires_at | int \| None | No | セッション有効期限 |
| created_at | int | Yes | セッション作成時刻 |

**Usage in Preview API**:
- プレビューアクセストークン取得時の認証に使用
- httpxリクエストのCookieヘッダーに注入

### NoteAPIError (既存、変更なし)

APIエラー。既存の`src/note_mcp/models.py`で定義済み。

**Relevant Error Codes**:
| Code | Usage |
|------|-------|
| NOT_AUTHENTICATED | 未認証時のプレビューAPI呼び出し |
| SESSION_EXPIRED | セッション期限切れ |
| ARTICLE_NOT_FOUND | 存在しない記事キー |
| API_ERROR | APIエラー（権限なし等） |

## State Transitions

### Preview Access Token Lifecycle

```
[No Token] --get_token()--> [Valid Token] --expire()/invalidate()--> [Expired Token]
                                 |
                                 v
                          [Used for Preview]
```

**States**:
1. **No Token**: 初期状態、トークン未取得
2. **Valid Token**: API経由で取得したトークン（有効期限あり、具体的な期限は不明だが数分〜数十分と推定）
3. **Expired Token**: 有効期限切れ（再取得が必要）

**Transitions**:
- `get_token()`: APIを呼び出してトークンを取得
- `expire()`: 時間経過による期限切れ
- `invalidate()`: 記事更新等による無効化

## Relationships

```
Session (1) ----uses----> (N) PreviewAccessToken
    |                           |
    |                           v
    +----> NoteAPIClient ----> Preview API Endpoint
                                    |
                                    v
                              PreviewURL --fetch--> PreviewHTMLResult
```

## API Response Mapping

### Access Token API Response

**Endpoint**: `POST /api/v2/notes/{article_key}/access_tokens`

**Request**:
```json
{
  "key": "{article_key}"
}
```

**Response**:
```json
{
  "data": {
    "preview_access_token": "32文字hex文字列"
  }
}
```

**Mapping to PreviewAccessToken**:
```python
def from_api_response(article_key: str, response: dict[str, Any]) -> PreviewAccessToken:
    """Create PreviewAccessToken from API response.

    Args:
        article_key: Article key used in request
        response: API response dictionary

    Returns:
        PreviewAccessToken instance
    """
    data = response.get("data", {})
    token = data.get("preview_access_token", "")
    return PreviewAccessToken(
        token=token,
        article_key=article_key,
        created_at=int(time.time()),
    )
```
