# Quickstart: 下書き記事の削除機能

**Created**: 2026-01-13
**Related Spec**: [spec.md](./spec.md)

## Overview

note-mcp MCPサーバーに2つの削除ツールを追加します:

1. **note_delete_draft**: 単一の下書き記事を削除
2. **note_delete_all_drafts**: すべての下書き記事を一括削除

両ツールとも確認フラグ（confirm）による誤操作防止機能を備えています。

## Prerequisites

- note-mcpがインストール済み
- note.comにログイン済み（`note_login`ツール実行済み）

## Usage Examples

### 単一記事の削除

#### Step 1: 削除前の確認（confirm=False）

```
ツール: note_delete_draft
入力:
  article_id: "n1234567890ab"
  confirm: false
```

**出力例**:
```json
{
  "article_id": "12345678",
  "article_key": "n1234567890ab",
  "article_title": "テスト記事",
  "status": "draft",
  "message": "下書き記事「テスト記事」を削除しますか？confirm=True を指定して再度呼び出してください。"
}
```

#### Step 2: 削除の実行（confirm=True）

```
ツール: note_delete_draft
入力:
  article_id: "n1234567890ab"
  confirm: true
```

**成功時の出力例**:
```json
{
  "success": true,
  "article_id": "12345678",
  "article_key": "n1234567890ab",
  "article_title": "テスト記事",
  "message": "下書き記事「テスト記事」(n1234567890ab)を削除しました。"
}
```

### 一括削除

#### Step 1: 削除対象の確認（confirm=False）

```
ツール: note_delete_all_drafts
入力:
  confirm: false
```

**出力例**:
```json
{
  "total_count": 3,
  "articles": [
    {"article_id": "12345678", "article_key": "n1234567890ab", "title": "下書き1"},
    {"article_id": "12345679", "article_key": "n2345678901bc", "title": "下書き2"},
    {"article_id": "12345680", "article_key": "n3456789012cd", "title": "下書き3"}
  ],
  "message": "3件の下書き記事を削除しますか？confirm=True を指定して再度呼び出してください。"
}
```

#### Step 2: 一括削除の実行（confirm=True）

```
ツール: note_delete_all_drafts
入力:
  confirm: true
```

**成功時の出力例**:
```json
{
  "success": true,
  "total_count": 3,
  "deleted_count": 3,
  "failed_count": 0,
  "deleted_articles": [
    {"article_id": "12345678", "article_key": "n1234567890ab", "title": "下書き1"},
    {"article_id": "12345679", "article_key": "n2345678901bc", "title": "下書き2"},
    {"article_id": "12345680", "article_key": "n3456789012cd", "title": "下書き3"}
  ],
  "failed_articles": [],
  "message": "3件の下書き記事を削除しました。"
}
```

## Error Handling

### 公開済み記事の削除試行

```
ツール: note_delete_draft
入力:
  article_id: "npublished123"
  confirm: true
```

**エラー出力**:
```json
{
  "success": false,
  "error_code": "api_error",
  "message": "公開済み記事は削除できません。下書きのみ削除可能です。"
}
```

### 存在しない記事の削除試行

```json
{
  "success": false,
  "error_code": "article_not_found",
  "message": "記事が見つかりません。ID: n0000000000xx"
}
```

### 未認証状態での削除試行

```json
{
  "success": false,
  "error_code": "not_authenticated",
  "message": "認証が必要です。note_loginツールでログインしてください。"
}
```

### 下書きが0件の状態での一括削除

```json
{
  "total_count": 0,
  "articles": [],
  "message": "削除対象の下書きがありません。"
}
```

## Typical AI Assistant Workflow

AIアシスタント（Claude等）がこの機能を使用する典型的なフロー:

### 単一記事削除のワークフロー

1. ユーザー: 「下書きの"テスト記事"を削除して」
2. AI: `note_list_articles(status="draft")` で下書き一覧を取得
3. AI: 該当記事を特定 → `note_delete_draft(article_id=..., confirm=false)`
4. AI: ユーザーに確認 → 「"テスト記事"を削除しますか？」
5. ユーザー: 「はい」
6. AI: `note_delete_draft(article_id=..., confirm=true)` で削除実行
7. AI: 「"テスト記事"を削除しました。」

### 一括削除のワークフロー

1. ユーザー: 「すべての下書きを削除して」
2. AI: `note_delete_all_drafts(confirm=false)` で対象一覧を取得
3. AI: ユーザーに確認 → 「3件の下書きを削除しますか？[一覧表示]」
4. ユーザー: 「はい」
5. AI: `note_delete_all_drafts(confirm=true)` で削除実行
6. AI: 「3件の下書きを削除しました。」

## Important Notes

- **取り消し不可**: 削除は取り消しできません
- **下書きのみ**: 公開済み記事は削除できません（安全のため）
- **確認必須**: confirm=Trueを指定しないと削除は実行されません
- **レート制限**: 1分間に10リクエストまで（一括削除時は自動的に順次実行）
