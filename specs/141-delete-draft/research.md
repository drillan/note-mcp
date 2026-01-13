# Research: 下書き記事の削除機能

**Created**: 2026-01-13
**Related Spec**: [spec.md](./spec.md)
**Related Plan**: [plan.md](./plan.md)

## Research Questions

### RQ-1: note.com削除APIエンドポイントの特定

**Question**: note.comで記事を削除するためのAPIエンドポイントは何か？

**Investigation**:
1. 既存コードベースのAPI呼び出しパターンを分析
2. RESTful規約に基づく推測
3. note.com APIのバージョニングパターンを確認
4. **[2026-01-13 検証済み]** note-investigatorでブラウザ操作をキャプチャ

**Findings**:

既存のnote.com APIエンドポイントパターン:
| 操作 | エンドポイント | メソッド |
|------|---------------|---------|
| 下書き作成 | `/v1/text_notes` | POST |
| 下書き保存 | `/v1/text_notes/draft_save?id={id}` | POST |
| 記事取得 | `/v3/notes/{article_id}` | GET |
| 記事一覧 | `/v2/note_list/contents` | GET |
| 記事公開 | `/v3/notes/{article_id}/publish` | POST |
| **記事削除** | **`/v1/notes/n/{article_key}`** | **DELETE** |

**[2026-01-13 検証結果]**:

ブラウザでの削除操作をキャプチャした結果、以下のAPIエンドポイントが確認された:

```
DELETE https://note.com/api/v1/notes/n/{article_key}
```

実際のキャプチャ例:
```
DELETE https://note.com/api/v1/notes/n/n9056511e87fc → 200 OK
```

**重要な発見**:
- パスに `/n/` プレフィックスが必要（`/v1/notes/n/{article_key}`）
- 記事キー（`n9056511e87fc`形式）を使用
- 数値ID（`142151705`形式）ではなくキーを使用
- 成功時はHTTPステータス200を返す

**Decision**: `DELETE /v1/notes/n/{article_key}` を使用

**Rationale**:
- 実際のブラウザ操作から確認された正確なエンドポイント
- v1系統だが、パスに `/n/` プレフィックスが必要という独自仕様
- 記事キー形式（`nXXXXXXX`）を使用

**Alternatives Considered**:
- `DELETE /v3/notes/{article_id}` - 404エラー（存在しないエンドポイント）
- `DELETE /v1/text_notes/{article_id}` - 405 Method Not Allowed
- `DELETE /v1/notes/{article_key}` - `/n/` プレフィックスなしでは動作しない可能性

### RQ-2: NoteAPIClientのdelete()メソッド実装状況

**Question**: 既存のNoteAPIClientはDELETEリクエストをサポートしているか？

**Investigation**: `src/note_mcp/api/client.py` を分析

**Findings**:
```python
async def delete(self, path: str) -> dict[str, Any]:
    """Make a DELETE request to the API."""
    return await self._request("DELETE", path, include_xsrf=True)
```

**Decision**: 既存のdelete()メソッドをそのまま使用可能

**Rationale**:
- XSRFトークン対応済み（`include_xsrf=True`）
- 適切なエラーハンドリング（401, 403, 404, 429, 5xx）
- httpxベースの非同期実装

### RQ-3: 記事ステータス判定ロジック

**Question**: 下書きと公開済み記事をどのように判別するか？

**Investigation**: `src/note_mcp/models.py` のArticleStatusを分析

**Findings**:
```python
class ArticleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PRIVATE = "private"
```

**Decision**: `Article.status == ArticleStatus.DRAFT` で判定

**Rationale**:
- 既存のArticleモデルにstatus属性あり
- APIレスポンスから自動的にパースされる
- 公開済み記事は`PUBLISHED`として識別可能

### RQ-4: 確認フラグの設計パターン

**Question**: 確認フラグ（confirm）パラメータはどのように実装すべきか？

**Investigation**: 仕様書のFR-141-002を分析

**Findings**:
- FR-141-002: 「削除ツールは確認フラグ（confirm）を必須パラメータとして受け取り、confirm=Trueの場合のみ削除を実行」

**Decision**:
- `confirm: bool` を必須パラメータとして定義
- `confirm=False`の場合は削除を実行せず、確認メッセージを返す
- `confirm=True`の場合のみ実際に削除を実行

**Rationale**:
- 明示的な確認により誤操作を防止
- AIアシスタントが確認プロセスを挟むことでユーザーに再考の機会を提供
- 取り消し不可能な操作には二重確認が適切

### RQ-5: 一括削除の実装戦略

**Question**: すべての下書きを一括削除する機能はどのように実装すべきか？

**Investigation**:
- 仕様書のFR-141-007, FR-141-008を分析
- 既存のlist_articles関数を確認

**Findings**:
- `list_articles(session, status=ArticleStatus.DRAFT)` で下書き一覧を取得可能
- 個別削除を順次実行する方式が最もシンプル
- 部分的失敗時のエラーハンドリングが必要

**Decision**:
1. 下書き一覧を取得（list_articles）
2. confirm=Falseの場合: 件数とタイトル一覧を返す
3. confirm=Trueの場合: 各記事を順次削除、成功/失敗を追跡
4. 結果サマリを返す（削除成功件数、失敗件数、失敗詳細）

**Rationale**:
- 既存のlist_articles関数を活用（DRY原則）
- 順次実行によりレート制限を自然に回避
- 部分的失敗に対応し、成功した削除は維持

**Alternatives Considered**:
- バッチAPI（存在確認が必要）: note.comにバッチ削除APIがあるか不明
- 並列実行: レート制限超過のリスク、順次実行で十分な速度

### RQ-6: エラーハンドリング戦略

**Question**: 削除操作で発生し得るエラーとその対応は？

**Investigation**: 仕様書のEdge CasesとAcceptance Scenariosを分析

**Findings**:
| エラー種別 | HTTPステータス | 対応 |
|-----------|---------------|------|
| 未認証 | 401 | ErrorCode.NOT_AUTHENTICATED |
| 公開済み記事の削除試行 | - | 削除前にステータスチェック |
| 記事が見つからない | 404 | ErrorCode.ARTICLE_NOT_FOUND |
| アクセス権なし | 403 | ErrorCode.API_ERROR（メッセージ調整） |
| レート制限 | 429 | ErrorCode.RATE_LIMITED |

**Decision**:
- 削除前にget_article()で記事情報を取得し、ステータスを確認
- 公開済み記事は削除APIを呼び出さず、明確なエラーを返す
- 404/403は既存のclientエラーハンドリングを活用

**Rationale**:
- 事前チェックにより不正な削除を防止
- ユーザーに明確なエラーメッセージを提供
- 既存のエラー処理パターンを再利用

## Technology Decisions

### TD-1: 削除結果モデル（DeleteResult）

**Decision**: 新しいPydanticモデル`DeleteResult`を追加

```python
class DeleteResult(BaseModel):
    """削除操作の結果を表す。

    Attributes:
        success: 削除が成功したかどうか
        article_id: 削除対象の記事ID
        article_title: 削除対象の記事タイトル
        message: 結果メッセージ
    """
    success: bool
    article_id: str
    article_title: str
    message: str
```

**Rationale**: 仕様FR-141-006に対応し、削除された記事情報を含む成功メッセージを構造化

### TD-2: 一括削除結果モデル（BulkDeleteResult）

**Decision**: 一括削除用の結果モデルを追加

```python
class BulkDeleteResult(BaseModel):
    """一括削除操作の結果を表す。

    Attributes:
        success: 全削除が成功したかどうか
        total_count: 削除対象の総件数
        deleted_count: 削除成功件数
        failed_count: 削除失敗件数
        deleted_articles: 削除成功した記事情報リスト
        failed_articles: 削除失敗した記事情報リスト
        message: 結果サマリメッセージ
    """
    success: bool
    total_count: int
    deleted_count: int
    failed_count: int
    deleted_articles: list[DeletedArticleInfo]
    failed_articles: list[FailedArticleInfo]
    message: str
```

**Rationale**: 部分的成功に対応し、詳細な結果を提供

### TD-3: MCPツール実装方針

**Decision**: 2つの独立したMCPツールとして実装

1. `note_delete_draft`: 単一記事削除
2. `note_delete_all_drafts`: 一括削除

**Rationale**:
- 仕様FR-141-007に従い別ツールとして提供
- 機能の明確な分離
- AIアシスタントが適切なツールを選択可能

## Dependencies

| ライブラリ | バージョン | 用途 | 新規/既存 |
|-----------|----------|------|---------|
| mcp | >=1.9.2 | MCPツール定義 | 既存 |
| pydantic | >=2.0 | データモデル | 既存 |
| httpx | - | HTTP通信 | 既存（NoteAPIClient経由） |
| pytest | >=8.4.1 | テスト | 既存 |
| pytest-asyncio | - | 非同期テスト | 既存 |

## Open Questions (Resolved)

1. ~~削除APIの正確なエンドポイントは？~~ → **検証済み: `DELETE /v1/notes/n/{article_key}`**
2. ~~削除後のレスポンス形式は？~~ → **検証済み: HTTP 200 OK（レスポンスボディは要確認）**

## Implementation Notes

### note.com API挙動の検証結果（2026-01-13）

| 検証項目 | 結果 |
|---------|------|
| 削除エンドポイント | `DELETE /v1/notes/n/{article_key}` |
| 成功時ステータス | HTTP 200 OK |
| 識別子形式 | 記事キー（`nXXXXXXX`形式）を使用 |

### 残りの検証項目

1. **公開済み記事の削除試行時のレスポンス**: 403か特定のエラーメッセージか確認
2. **削除成功時のレスポンスボディ**: 空か、データ付きか確認
3. **存在しない記事キーに対するDELETE**: 404を確認

### 実装時の注意点

- 記事キー形式（`nXXXXXXX`）を使用すること
- パスに `/n/` プレフィックスが必要
- 数値IDから記事キーへの変換が必要な場合は、`get_article()` で取得可能

## References

- [spec.md](./spec.md) - 機能仕様
- [parent spec](../001-note-mcp/spec.md) - 親仕様
- [constitution.md](/.specify/memory/constitution.md) - プロジェクト憲法
