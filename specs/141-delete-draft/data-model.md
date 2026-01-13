# Data Model: 下書き記事の削除機能

**Created**: 2026-01-13
**Related Spec**: [spec.md](./spec.md)
**Related Plan**: [plan.md](./plan.md)

## Entities

### Existing Entities (from parent spec)

#### Article

記事エンティティ。親仕様（001-note-mcp）で定義済み。削除対象の判定に使用。

| Field | Type | Description |
|-------|------|-------------|
| id | str | 記事ID（note.com内部ID） |
| key | str | 記事キー（URL用） |
| title | str | 記事タイトル |
| body | str | 記事本文（HTML） |
| status | ArticleStatus | 公開状態（draft/published/private） |
| tags | list[str] | ハッシュタグリスト |
| created_at | str \| None | 作成日時 |
| updated_at | str \| None | 更新日時 |

**Validation Rules**:
- id: 非空文字列
- status: ArticleStatus enumの値

**State Transitions**:
- draft → deleted（削除操作）
- published → _(削除不可)_

#### ArticleStatus

記事の公開状態を表すEnum。

| Value | Description |
|-------|-------------|
| DRAFT | 下書き（削除可能） |
| PUBLISHED | 公開済み（削除不可） |
| PRIVATE | 非公開（削除可否は要確認） |

### New Entities

#### DeleteResult

単一記事の削除結果を表すPydanticモデル。

```python
class DeleteResult(BaseModel):
    """Result of a single delete operation.

    Attributes:
        success: Whether the deletion was successful
        article_id: ID of the deleted article
        article_key: Key of the deleted article
        article_title: Title of the deleted article
        message: Result message for the user
    """
    success: bool
    article_id: str
    article_key: str
    article_title: str
    message: str
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| success | bool | Yes | 削除成功フラグ |
| article_id | str | Yes | 削除対象の記事ID |
| article_key | str | Yes | 削除対象の記事キー |
| article_title | str | Yes | 削除対象の記事タイトル |
| message | str | Yes | 結果メッセージ（成功/エラー） |

**Validation Rules**:
- article_id: 非空文字列
- article_key: 非空文字列

#### DeletePreview

削除確認時のプレビュー情報を表すモデル。confirm=False時に返される。

```python
class DeletePreview(BaseModel):
    """Preview information before deletion.

    Used when confirm=False to show what will be deleted.

    Attributes:
        article_id: ID of the article to be deleted
        article_key: Key of the article to be deleted
        article_title: Title of the article to be deleted
        status: Current status of the article
        message: Confirmation prompt message
    """
    article_id: str
    article_key: str
    article_title: str
    status: ArticleStatus
    message: str
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| article_id | str | Yes | 削除対象の記事ID |
| article_key | str | Yes | 削除対象の記事キー |
| article_title | str | Yes | 削除対象の記事タイトル |
| status | ArticleStatus | Yes | 記事の現在の状態 |
| message | str | Yes | 確認プロンプトメッセージ |

#### BulkDeletePreview

一括削除確認時のプレビュー情報を表すモデル。

```python
class BulkDeletePreview(BaseModel):
    """Preview information for bulk deletion.

    Used when confirm=False to show all drafts that will be deleted.

    Attributes:
        total_count: Total number of drafts to be deleted
        articles: List of articles to be deleted
        message: Confirmation prompt message
    """
    total_count: int
    articles: list[ArticleSummary]
    message: str
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| total_count | int | Yes | 削除対象の総件数 |
| articles | list[ArticleSummary] | Yes | 削除対象記事のサマリリスト |
| message | str | Yes | 確認プロンプトメッセージ |

#### ArticleSummary

記事のサマリ情報（一括削除のプレビュー/結果用）。

```python
class ArticleSummary(BaseModel):
    """Summary information of an article.

    Attributes:
        article_id: Article ID
        article_key: Article key
        title: Article title
    """
    article_id: str
    article_key: str
    title: str
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| article_id | str | Yes | 記事ID |
| article_key | str | Yes | 記事キー |
| title | str | Yes | 記事タイトル |

#### BulkDeleteResult

一括削除の結果を表すモデル。

```python
class BulkDeleteResult(BaseModel):
    """Result of bulk delete operation.

    Attributes:
        success: Whether all deletions were successful
        total_count: Total number of articles targeted
        deleted_count: Number of successfully deleted articles
        failed_count: Number of failed deletions
        deleted_articles: List of successfully deleted articles
        failed_articles: List of articles that failed to delete
        message: Summary message
    """
    success: bool
    total_count: int
    deleted_count: int
    failed_count: int
    deleted_articles: list[ArticleSummary]
    failed_articles: list[FailedArticle]
    message: str
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| success | bool | Yes | 全削除成功フラグ |
| total_count | int | Yes | 削除対象の総件数 |
| deleted_count | int | Yes | 削除成功件数 |
| failed_count | int | Yes | 削除失敗件数 |
| deleted_articles | list[ArticleSummary] | Yes | 成功した記事リスト |
| failed_articles | list[FailedArticle] | Yes | 失敗した記事リスト |
| message | str | Yes | サマリメッセージ |

#### FailedArticle

削除に失敗した記事の情報。

```python
class FailedArticle(BaseModel):
    """Information about a failed deletion.

    Attributes:
        article_id: Article ID
        article_key: Article key
        title: Article title
        error: Error message
    """
    article_id: str
    article_key: str
    title: str
    error: str
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| article_id | str | Yes | 記事ID |
| article_key | str | Yes | 記事キー |
| title | str | Yes | 記事タイトル |
| error | str | Yes | エラーメッセージ |

## Relationships

```text
┌─────────────────────┐
│     Session         │
│   (既存/認証用)      │
└──────────┬──────────┘
           │ uses
           ▼
┌─────────────────────┐
│      Article        │
│   (既存/記事本体)    │──────────────────┐
└──────────┬──────────┘                  │
           │ determines                   │
           ▼                              │
┌─────────────────────┐                  │
│   ArticleStatus     │                  │
│ DRAFT → 削除可能    │                  │
│ PUBLISHED → 拒否    │                  │
└─────────────────────┘                  │
                                         │
┌─────────────────────┐                  │
│   DeleteResult      │◄─────────────────┤
│   (単一削除結果)     │   success        │
└─────────────────────┘                  │
                                         │
┌─────────────────────┐                  │
│   DeletePreview     │◄─────────────────┤
│ (削除確認プレビュー) │   confirm=False  │
└─────────────────────┘                  │
                                         │
┌─────────────────────┐   contains       │
│   BulkDeleteResult  │◄─────────────────┘
│   (一括削除結果)     │
│   ├─ ArticleSummary │
│   └─ FailedArticle  │
└─────────────────────┘
```

## Error Codes (additions to existing ErrorCode enum)

既存のErrorCode enumを拡張せず、既存コードを再利用:

| Code | Description | 用途 |
|------|-------------|------|
| NOT_AUTHENTICATED | 未認証 | 削除API呼び出し時に認証切れ |
| ARTICLE_NOT_FOUND | 記事が見つからない | 存在しないIDを指定 |
| API_ERROR | APIエラー | 公開済み記事の削除試行、アクセス権なし |
| INVALID_INPUT | 不正な入力 | 無効なIDフォーマット |

**新規エラーメッセージ定数（models.pyに追加）**:

```python
# Delete operation error messages
DELETE_ERROR_PUBLISHED_ARTICLE = "公開済み記事は削除できません。下書きのみ削除可能です。"
DELETE_ERROR_NO_ACCESS = "この記事へのアクセス権がありません。"
DELETE_ERROR_NOT_FOUND = "記事が見つかりません。キー: {article_key}"
DELETE_CONFIRM_REQUIRED = "削除を実行するには confirm=True を指定してください。"
```

## Input Models (for MCP tools)

### DeleteDraftInput

単一記事削除のMCPツール入力。

```python
class DeleteDraftInput(BaseModel):
    """Input for note_delete_draft tool.

    Attributes:
        article_key: Key of the article to delete (format: nXXXXXXXXXXXX)
        confirm: Confirmation flag (must be True to execute deletion)
    """
    article_key: str
    confirm: bool = False
```

**Note**: 検証により、削除APIは記事キー（`nXXXXXXXX`形式）のみを受け付けることが確認されています。
数値ID（`12345678`形式）ではなく、記事キーを使用する必要があります。

### DeleteAllDraftsInput

一括削除のMCPツール入力。

```python
class DeleteAllDraftsInput(BaseModel):
    """Input for note_delete_all_drafts tool.

    Attributes:
        confirm: Confirmation flag (must be True to execute deletion)
    """
    confirm: bool = False
```

## State Machine: Delete Operation

```text
                    ┌───────────────────────────┐
                    │        START              │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    Check Authentication   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
           ┌────────────────┐         ┌────────────────┐
           │  Authenticated │         │ NOT_AUTHENTICATED │
           └───────┬────────┘         └────────────────┘
                   │                          │
                   │                          ▼
                   │                   [Return Error]
                   ▼
     ┌───────────────────────────┐
     │    Fetch Article Info     │
     └─────────────┬─────────────┘
                   │
     ┌─────────────┴─────────────┐
     │                           │
     ▼                           ▼
┌────────────┐           ┌────────────────┐
│  Found     │           │ ARTICLE_NOT_FOUND │
└─────┬──────┘           └────────────────┘
      │                          │
      │                          ▼
      │                   [Return Error]
      ▼
┌───────────────────────────┐
│   Check Article Status    │
└─────────────┬─────────────┘
              │
┌─────────────┴─────────────┐
│                           │
▼                           ▼
┌────────┐            ┌────────────┐
│ DRAFT  │            │ PUBLISHED  │
└────┬───┘            └─────┬──────┘
     │                      │
     │                      ▼
     │              [Return Error:
     │               公開済み記事は削除不可]
     ▼
┌───────────────────────────┐
│   Check Confirm Flag      │
└─────────────┬─────────────┘
              │
┌─────────────┴─────────────┐
│                           │
▼                           ▼
┌────────────────┐    ┌────────────────┐
│ confirm=False  │    │ confirm=True   │
└───────┬────────┘    └───────┬────────┘
        │                     │
        ▼                     ▼
[Return DeletePreview] ┌───────────────────┐
                       │ Execute DELETE API │
                       └─────────┬─────────┘
                                 │
                   ┌─────────────┴─────────────┐
                   │                           │
                   ▼                           ▼
           ┌──────────────┐           ┌────────────────┐
           │   Success    │           │   API Error    │
           └──────┬───────┘           └───────┬────────┘
                  │                           │
                  ▼                           ▼
         [Return DeleteResult]        [Return Error]
```

## Notes

- すべてのモデルはPydantic v2を使用
- 型注釈はConstitution Article 9に準拠
- 既存のArticle, ArticleStatus, ErrorCodeを最大限活用（DRY原則）
