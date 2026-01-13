# Tasks: プレビューAPI対応

**Feature**: 002-preview-api
**Branch**: `002-preview-api`
**Date**: 2025-01-13
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

## Overview

note.com MCP Serverのプレビュー機能をAPI経由に改善するタスク一覧。
TDD（テストファースト）に従い、各タスクはテスト作成→実装の順で進行。

## Task Legend

- `[P1]` = Priority 1 (Must have)
- `[P2]` = Priority 2 (Should have)
- `[US1]` = User Story 1: ブラウザプレビュー表示
- `[US2]` = User Story 2: HTML取得（プログラム用）
- `[US3]` = User Story 3: 認証エラーハンドリング

## Phase 1: Setup

- [x] [T1.1] [P1] プレビューAPI用テストディレクトリ作成: `tests/unit/test_preview_api.py`
- [x] [T1.2] [P1] E2Eテスト用ファイル作成: `tests/integration/test_preview_e2e.py`

## Phase 2: Foundational - Preview API Infrastructure

### 2.1 Preview API Module

- [x] [T2.1] [P1] [US1,US2] テスト作成: `get_preview_access_token`関数の単体テスト (`tests/unit/test_preview_access.py`に既存)
- [x] [T2.2] [P1] [US1,US2] 実装: `src/note_mcp/api/articles.py`に`get_preview_access_token`関数が既存
- [x] [T2.3] [P1] [US1,US2] テスト作成: `build_preview_url`関数の単体テスト (`tests/unit/test_preview_access.py`に既存)
- [x] [T2.4] [P1] [US1,US2] 実装: `src/note_mcp/api/articles.py`に`build_preview_url`関数が既存

### 2.2 Data Models (Optional)

- [x] [T2.5] [P2] テスト作成: `PreviewAccessToken`モデルのバリデーションテスト - 不要（単純な文字列トークンを使用）
- [x] [T2.6] [P2] 実装: `src/note_mcp/models.py`に`PreviewAccessToken`クラスを追加 - 不要（単純な文字列トークンを使用）

## Phase 3: User Story 1 - Browser Preview Display

### 3.1 Browser Preview Module Update

- [x] [T3.1] [P1] [US1] テスト作成: `show_preview`関数のテスト（API経由トークン取得） (`tests/unit/test_preview_api.py`)
- [x] [T3.2] [P1] [US1] 実装: `src/note_mcp/browser/preview.py`の`show_preview`関数をAPI経由に改修
- [x] [T3.3] [P1] [US1] テスト作成: Cookie注入機能のテスト (`tests/unit/test_preview_api.py`)
- [x] [T3.4] [P1] [US1] 実装: Cookie注入はshow_preview関数内にインライン実装

### 3.2 MCP Tool Update

- [x] [T3.5] [P1] [US1] テスト作成: `note_show_preview`ツールのE2Eテスト (`tests/integration/test_preview_e2e.py`)
- [x] [T3.6] [P1] [US1] 実装: `src/note_mcp/server.py`の`note_show_preview`ツールが新APIを使用することを確認

## Phase 4: User Story 2 - HTML Retrieval

### 4.1 HTML Fetch Function

- [x] [T4.1] [P1] [US2] テスト作成: `get_preview_html`関数の単体テスト (`tests/unit/test_preview_api.py`)
- [x] [T4.2] [P1] [US2] 実装: `src/note_mcp/api/preview.py`に`get_preview_html`関数を作成

### 4.2 MCP Tool Addition

- [x] [T4.3] [P1] [US2] テスト作成: `note_get_preview_html`ツールの単体テスト (`tests/unit/test_preview_api.py`)
- [x] [T4.4] [P1] [US2] 実装: `src/note_mcp/server.py`に`note_get_preview_html`ツールを追加
- [x] [T4.5] [P1] [US2] E2Eテスト: `note_get_preview_html`ツールの統合テスト (`tests/integration/test_preview_e2e.py`)

## Phase 5: User Story 3 - Error Handling

### 5.1 Authentication Errors

- [x] [T5.1] [P2] [US3] テスト作成: 未認証時のエラーハンドリングテスト (`tests/unit/test_preview_api.py` - test_tool_returns_error_on_no_session)
- [x] [T5.2] [P2] [US3] 実装: 未認証時に適切なエラーメッセージを返す (`note_get_preview_html`ツールで実装済み)
- [x] [T5.3] [P2] [US3] テスト作成: セッション期限切れ時のエラーハンドリングテスト (`tests/unit/test_preview_api.py` - test_tool_returns_error_on_expired_session)
- [x] [T5.4] [P2] [US3] 実装: セッション期限切れ時に適切なエラーメッセージを返す (`note_get_preview_html`ツールで実装済み)

### 5.2 API Errors

- [x] [T5.5] [P2] [US3] テスト作成: 記事が見つからない場合のエラーテスト (`tests/unit/test_preview_api.py` - test_tool_returns_error_message_on_api_error)
- [x] [T5.6] [P2] [US3] 実装: 404エラー時に適切なエラーメッセージを返す (NoteAPIErrorで処理)
- [x] [T5.7] [P2] [US3] テスト作成: 権限エラー時のテスト (`tests/unit/test_preview_api.py` - test_get_preview_html_handles_http_errors)
- [x] [T5.8] [P2] [US3] 実装: 403エラー時に適切なエラーメッセージを返す (get_preview_htmlで実装済み)

### 5.3 Edge Cases

- [ ] [T5.9] [P2] テスト作成: 公開済み記事のプレビュー要求時の動作テスト (`tests/unit/test_preview_api.py`)
- [ ] [T5.10] [P2] 実装: 公開済み記事に対する適切なレスポンスを返す（プレビュー優先、失敗時は公開URL）
- [ ] [T5.11] [P2] テスト作成: トークン期限切れ時の再取得テスト (`tests/unit/test_preview_api.py`)
- [ ] [T5.12] [P2] 実装: トークン期限切れ時に自動再取得してリトライ

## Phase 6: Polish

### 6.1 Code Quality

- [x] [T6.1] [P1] ruff check実行とエラー修正
- [x] [T6.2] [P1] ruff format実行
- [x] [T6.3] [P1] mypy実行と型エラー修正

### 6.2 Documentation

- [x] [T6.4] [P2] docstring確認と更新（完了 - 全関数にdocstringあり）
- [ ] [T6.5] [P2] quickstart.mdの最終確認

### 6.3 Final Verification

- [x] [T6.6] [P1] 全ユニットテスト実行: `uv run pytest tests/unit/ -v` (349 passed)
- [x] [T6.7] [P1] E2Eテスト実行: `uv run pytest tests/integration/test_preview_e2e.py -v` (6 passed)
- [x] [T6.8] [P1] Constitution Check: `/constitution-checker`スキル実行 - PASS

### 6.4 Performance Verification (SC-002)

- [ ] [T6.9] [P1] ベースライン計測: 現行エディター経由方式のプレビュー表示時間を記録
- [ ] [T6.10] [P1] 新方式計測: API経由方式のプレビュー表示時間を記録
- [ ] [T6.11] [P1] SC-002検証: 80%以上の高速化が達成されていることを確認

## Dependencies

```
T1.1, T1.2 (Setup)
    ↓
T2.1 → T2.2 → T2.3 → T2.4 (API Infrastructure)
    ↓
T3.1 → T3.2 → T3.3 → T3.4 → T3.5 → T3.6 (US1: Browser Preview)
    ↓
T4.1 → T4.2 → T4.3 → T4.4 → T4.5 (US2: HTML Retrieval)
    ↓
T5.1-T5.8 (US3: Error Handling - can be parallel)
    ↓
T5.9-T5.12 (Edge Cases - can be parallel)
    ↓
T6.1 → T6.2 → T6.3 (Code Quality)
    ↓
T6.4, T6.5 (Documentation - can be parallel)
    ↓
T6.6 → T6.7 → T6.8 (Final Verification)
    ↓
T6.9 → T6.10 → T6.11 (Performance Verification)
```

## Acceptance Criteria Summary

| User Story | Criteria | Verification |
|------------|----------|--------------|
| US1 | プレビュー表示が3秒以内 | E2Eテストでタイミング計測 |
| US1 | エディター経由しない | コードレビューで確認 |
| US2 | HTML取得が5秒以内 | ユニットテストでタイミング計測 |
| US2 | 完全なHTMLが返却される | テストでHTML構造検証 |
| US3 | 未認証時に明確なエラー | ユニットテストで検証 |
| US3 | セッション期限切れ時に明確なエラー | ユニットテストで検証 |

## Notes

- TDD必須: テスト作成（T*.1, T*.3, T*.5等）を先に実行し、ユーザー承認後に実装タスクを進行
- Constitution Article 1に従い、すべての実装はテストファースト
- Constitution Article 5に従い、Phase 6の品質チェックは必須
